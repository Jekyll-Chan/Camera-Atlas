"""Render one geographic scene to a transparent PNG and editable SVG."""

import html
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Geod
from shapely.geometry import box, shape

from ..composition.region import ink_distribution
from .design import KINDS, THEMES

BUNDLED_FONT = Path(__file__).resolve().parents[1] / "assets/fonts/EBGaramond.ttf"


def label_for(properties, language):
    en = properties.get("name:en")
    local = properties.get("name")
    if language == "local":
        return local
    if language == "bilingual":
        return " / ".join(dict.fromkeys(x for x in (en, local) if x))
    # Do not claim an untranslated local name is English.
    return en or (local if local and local.isascii() else None)


class Canvas:
    def __init__(self, size, font=None):
        self.size = size
        self.ratio = 2
        self.image = Image.new("RGBA", (size[0] * 2, size[1] * 2))
        self.draw = ImageDraw.Draw(self.image)
        self.custom_font = font is not None
        self.font_path = font or (BUNDLED_FONT if BUNDLED_FONT.is_file() else None)
        self.fonts = {}
        self.svg = []
        self.text_boxes = []
        self.text_records = []
        self.allowed = None

    def color(self, rgba):
        return f"rgb({rgba[0]},{rgba[1]},{rgba[2]})", rgba[3] / 255

    def line(self, points, color, width=1):
        if len(points) < 2:
            return
        self.draw.line(
            [(x * 2, y * 2) for x, y in points], fill=color, width=max(1, round(width * 2)), joint="curve"
        )
        ink, opacity = self.color(color)
        pts = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
        self.svg.append(
            f'<polyline points="{pts}" fill="none" stroke="{ink}" stroke-opacity="{opacity}" '
            f'stroke-width="{width}" stroke-linejoin="round"/>'
        )

    def circle(self, cx, cy, r, color, filled=True):
        b = ((cx - r) * 2, (cy - r) * 2, (cx + r) * 2, (cy + r) * 2)
        self.draw.ellipse(b, fill=color if filled else None, outline=color, width=2)
        ink, opacity = self.color(color)
        fill = ink if filled else "none"
        self.svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{ink}" '
            f'opacity="{opacity}" stroke-width="1"/>'
        )

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = (
                ImageFont.truetype(str(self.font_path), round(size * 2))
                if self.font_path
                else ImageFont.load_default(size=round(size * 2))
            )
        return self.fonts[size]

    def supports(self, text):
        # The bundled serif covers Latin/Greek/Cyrillic, not CJK. A user-supplied
        # font may cover additional scripts; never substitute missing-glyph boxes.
        return self.custom_font or all(
            ord(c) <= (0x052F if self.font_path else 255) or c in "–—‘’“”…" for c in text
        )

    def text_bounds(self, xy, text, size):
        x, y = xy
        return tuple(
            v / 2 for v in self.draw.textbbox((x * 2, y * 2), text, font=self.font(size), anchor="lt")
        )

    def text_fits(self, xy, text, size, avoid=True, margin=3):
        if not text or not self.supports(text):
            return False
        b = self.text_bounds(xy, text, size)
        if b[0] < 0 or b[1] < 0 or b[2] > self.size[0] or b[3] > self.size[1]:
            return False
        if self.allowed is not None:
            area = self.allowed[
                max(0, math.floor(b[1]) - margin) : min(self.size[1], math.ceil(b[3]) + margin),
                max(0, math.floor(b[0]) - margin) : min(self.size[0], math.ceil(b[2]) + margin),
            ]
            if not area.size or not area.all():
                return False
        if avoid and any(
            b[0] < p[2] + 5 and b[2] + 5 > p[0] and b[1] < p[3] + 5 and b[3] + 5 > p[1]
            for p in self.text_boxes
        ):
            return False
        return True

    def text(self, xy, text, size, color, avoid=True):
        if not self.text_fits(xy, text, size, avoid=avoid):
            return False
        x, y = xy
        b = self.text_bounds(xy, text, size)
        self.draw.text((x * 2, y * 2), text, font=self.font(size), fill=color, anchor="lt")
        self.text_boxes.append(b)
        self.text_records.append({"text": text, "size_px": size, "bounds": b})
        ink, opacity = self.color(color)
        family = "EB Garamond, serif" if self.font_path and not self.custom_font else "serif"
        self.svg.append(
            f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" '
            f'font-family="{family}" font-size="{size}" fill="{ink}" fill-opacity="{opacity}">'
            f"{html.escape(text)}</text>"
        )
        return True

    def finish(self):
        return self.image.resize(self.size, Image.Resampling.LANCZOS)


def compact_credits(credits):
    """Deduplicate exact middle-dot clauses, never paraphrase source obligations."""
    return " · ".join(dict.fromkeys(part.strip() for credit in credits for part in credit.split(" · ")))


def pixel_wrap(c, text, size, width):
    """Wrap by measured ink width, keeping every character including long URLs."""
    lines, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        bounds = c.text_bounds((0, 0), candidate, size)
        if bounds[2] - bounds[0] <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ""
        for char in word:
            candidate = line + char
            bounds = c.text_bounds((0, 0), candidate, size)
            if bounds[2] - bounds[0] > width:
                if not line:
                    raise ValueError("Required attribution cannot fit at a readable size")
                lines.append(line)
                line = char
            else:
                line = candidate
    if line:
        lines.append(line)
    return lines


def region_credit(c, credits, ink):
    """Measure the whole credit block before drawing any of it."""
    blocked = np.pad((~c.allowed).astype("int32"), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    w, h = c.size
    margin, size, leading = 10, 10, 14
    text = compact_credits(credits)
    for width in range(min(w - margin * 2, 480), 59, -24):
        lines = pixel_wrap(c, text, size, width)
        bounds = [c.text_bounds((0, 0), line, size) for line in lines]
        actual_w = math.ceil(max(b[2] - b[0] for b in bounds)) + margin * 2
        actual_h = math.ceil(max(b[3] - b[1] for b in bounds)) + leading * (len(lines) - 1) + margin * 2
        if actual_w > w or actual_h > h or not c.supports(text):
            continue
        for yy in range(h - actual_h, -1, -4):
            xx = np.arange(0, w - actual_w + 1, 4)
            sums = (
                blocked[yy + actual_h, xx + actual_w]
                - blocked[yy, xx + actual_w]
                - blocked[yy + actual_h, xx]
                + blocked[yy, xx]
            )
            fits = xx[sums == 0]
            if not len(fits):
                continue
            for xx in reversed(fits):
                layout = [
                    ((int(xx) + margin, yy + margin + i * leading), line) for i, line in enumerate(lines)
                ]
                # This is a read-only pass: a rejected candidate leaves no ink,
                # SVG nodes or text boxes from a partially drawn first line.
                if all(c.text_fits(pos, line, size, avoid=True) for pos, line in layout):
                    for pos, line in layout:
                        c.text(pos, line, size, ink, avoid=False)
                    return
    raise ValueError(
        "Selected region has no room for readable source credit; widen a clear part of the selection"
    )


def render_map(size, rect, projection, data, location, mode, config, exclusion=None, allowed=None):
    x, y, w, h = rect
    # Small local supersampled canvas avoids a full-frame 4x allocation.
    c = Canvas((w, h), config.font)
    theme = THEMES[config.style]
    alpha = round(config.opacity * 255)
    ink = (*theme.ink, alpha)
    accent = (*theme.accent, 245)
    gutter = max(12, int(w * 0.07))
    footer = max(55, int(h * 0.18))
    usable = min(w - 2 * gutter, h - footer - 2 * gutter)
    r = projection.radius
    factor = usable / (2 * r)
    ox, oy = w / 2, (h - footer) / 2
    if allowed is not None:
        left, bottom, right, top = projection.extent
        factor = w / (right - left)
        if not math.isclose(factor, h / (top - bottom), rel_tol=1e-9):
            raise ValueError("Region projection must preserve uniform geographic scale")
        ox, oy = -left * factor, top * factor
        c.allowed = np.asarray(allowed.crop((x, y, x + w, y + h))) > 0

    def pixel(px, py):
        return ox + px * factor, oy - py * factor

    viewport = box(*projection.extent)
    sources = {s.id: s for s in data.sources}
    drawn = []
    omitted = []
    candidates = []

    def lines(g):
        if g.geom_type in ("LineString", "LinearRing"):
            yield list(g.coords)
        elif g.geom_type == "Polygon":
            yield list(g.exterior.coords)
            for ring in g.interiors:
                yield list(ring.coords)
        elif hasattr(g, "geoms"):
            for part in g.geoms:
                yield from lines(part)

    for index, f in enumerate(data.features):
        p = f["properties"]
        if p.get("kind") not in KINDS[mode]:
            continue
        source = sources[p["source_id"]]
        if source.min_span_km and 2 * r / 1000 < source.min_span_km:
            omitted.append({"index": index, "reason": "dataset resolution too coarse for map span"})
            continue
        g = projection.project(shape(f["geometry"]))
        if not g.is_valid or not g.intersects(viewport):
            continue
        g = g.intersection(viewport)
        drawn_geometry = False
        width = theme.line * (0.65 if p.get("kind") == "contour" else 1)
        for points in lines(g):
            c.line([pixel(*point[:2]) for point in points], ink, width)
            drawn_geometry = True
        name = label_for(p, config.label_language)
        if name:
            center = g.representative_point()
            candidates.append((pixel(center.x, center.y), name, index))
        if drawn_geometry:
            drawn.append(
                {
                    "index": index,
                    "source_id": source.id,
                    "kind": p.get("kind"),
                    "label": None,
                    "elevation_m": p.get("elevation_m"),
                }
            )
    geometry_alpha = c.finish().getchannel("A") if allowed is not None else None
    visible_geometry = (np.asarray(geometry_alpha) > 0) & c.allowed if allowed is not None else None
    # Neither labels nor credits may disguise geometry missing from the selected region.
    if not drawn or (visible_geometry is not None and not visible_geometry.any()):
        return (
            Image.new("RGBA", size),
            None,
            {
                "drawn_features": [],
                "omitted_features": omitted,
                "reason": "No verified geometry available for selected mode",
            },
        )
    marker = {
        "accuracy": location.accuracy,
        "coordinates": [location.lon, location.lat],
        "art_position": list(pixel(0, 0)),
        "meaning": "map location, never camera heading",
    }
    mx, my = pixel(0, 0)
    marker_radius = (
        max(3, min(4.5, min(w, h) * 0.006))
        if location.accuracy == "exact_gps"
        else max(5, min(7, min(w, h) * 0.008))
    )
    c.circle(
        mx,
        my,
        marker_radius,
        accent,
        filled=location.accuracy == "exact_gps",
    )
    marker.update({"radius_px": marker_radius, "filled": location.accuracy == "exact_gps", "rgba": accent})
    if config.labels:
        primary = config.location_label or location.name
        primary_size = max(11, min(18, round(min(w, h) * 0.019)))
        marker["label"] = None
        if primary and c.supports(primary):
            primary_bounds = c.text_bounds((0, 0), primary, primary_size)
            pw, ph = primary_bounds[2] - primary_bounds[0], primary_bounds[3] - primary_bounds[1]
            for pos in (
                (mx + marker_radius + 8, my - ph / 2),
                (mx - marker_radius - 8 - pw, my - ph / 2),
                (mx - pw / 2, my + marker_radius + 8),
                (mx - pw / 2, my - marker_radius - 8 - ph),
            ):
                if c.text(pos, primary, primary_size, (*theme.ink, max(205, alpha))):
                    marker["label"] = primary
                    break
        count = 0
        used_names = {primary.casefold()} if primary else set()
        positions = [(mx, my)]
        label_size = max(9, min(13, round(min(w, h) * 0.014)))
        spacing = max(55, min(w, h) * 0.20)
        # Greedily choose the farthest candidate each time. Provider ordering
        # must not bunch every incidental label into one neighbourhood.
        while candidates and count < min(3, theme.max_labels):
            choice = max(
                range(len(candidates)),
                key=lambda i: min(math.dist(candidates[i][0], p) for p in positions),
            )
            pos, name, index = candidates.pop(choice)
            if min(math.dist(pos, p) for p in positions) < spacing:
                break
            if name.casefold() in used_names:
                continue
            if c.text((pos[0] + 7, pos[1] + 3), name, label_size, ink):
                count += 1
                positions.append(pos)
                used_names.add(name.casefold())
                drawn.append(
                    {
                        "index": index,
                        "source_id": data.features[index]["properties"]["source_id"],
                        "kind": "label",
                        "label": name,
                    }
                )
    scale = None
    if config.scale and config.labels:
        length = projection.nice_scale(r * 0.6)
        yy = -r * 0.8
        # Verify length using inverse projection and ellipsoidal geodesic distance.
        start, end = (
            projection.inverse.transform(-length / 2, yy),
            projection.inverse.transform(length / 2, yy),
        )
        measured = Geod(ellps="WGS84").inv(*start, *end)[2]
        a, b = pixel(-length / 2, yy), pixel(length / 2, yy)
        c.line([a, b], ink, 1)
        text = f"{measured / 1000:.2g} km" if measured >= 1000 else f"{measured:.0f} m"
        c.text((a[0], a[1] + 4), text, max(9, int(w * 0.023)), ink)
        scale = {
            "geodesic_m": measured,
            "projected_m": length,
            "pixel_length": length * factor,
            "endpoints_wgs84": [start, end],
        }
    if config.north and config.labels:
        lon, lat, _ = Geod(ellps="WGS84").fwd(location.lon, location.lat, 0, 1000)
        nx, ny = projection.forward.transform(lon, lat)
        angle = math.atan2(ny, nx)
        origin = (w - gutter - 10, gutter + 20)
        end = (origin[0] + math.cos(angle) * 18, origin[1] - math.sin(angle) * 18)
        c.line([origin, end], ink, 1)
        c.text((end[0] - 3, end[1] - 13), "N", 9, ink)
    used_ids = {f["source_id"] for f in drawn}
    # Geocoded coordinates are OSM data too and require attribution.
    if location.source_id:
        used_ids.add(location.source_id)
    credits = list(dict.fromkeys(sources[s].attribution for s in sorted(used_ids)))
    # Attribution remains visible when optional geographic labels are disabled.
    credit_text = compact_credits(credits)
    credit_start = len(c.text_boxes)
    if allowed is not None:
        region_credit(c, credits, (*theme.ink, max(alpha, 190)))
    else:
        credit_lines = pixel_wrap(c, credit_text, 8, max(40, w - 2 * gutter))
        layout = [((gutter, h - footer + 4 + i * 12), credit) for i, credit in enumerate(credit_lines)]
        if not all(c.text_fits(pos, credit, 8, avoid=False) for pos, credit in layout):
            raise ValueError(
                "Map too small for required attribution; increase --map-area or shorten approved attribution"
            )
        for pos, credit in layout:
            c.text(pos, credit, 8, (*theme.ink, max(alpha, 190)), avoid=False)
    if exclusion is not None:
        # Excluding legally required credit cannot yield a distributable attributed map.
        protected = np.asarray(exclusion)
        for bounds in c.text_boxes[credit_start:]:
            bx0, by0, bx1, by1 = bounds
            if np.any(protected[y + int(by0) : y + int(by1) + 1, x + int(bx0) : x + int(bx1) + 1]):
                return (
                    Image.new("RGBA", size),
                    None,
                    {
                        "drawn_features": [],
                        "omitted_features": omitted,
                        "reason": "Subject exclusion would obscure required attribution",
                    },
                )
    local = c.finish()
    overlay = Image.new("RGBA", size)
    overlay.paste(local, (x, y))
    mask_svg = ""
    if exclusion is not None or allowed is not None:
        import base64
        import io

        allowed = (
            allowed if allowed is not None else Image.fromarray(255 - np.asarray(exclusion)).convert("L")
        )
        arr = np.asarray(overlay).copy()
        arr[:, :, 3] = np.rint(arr[:, :, 3].astype(float) * np.asarray(allowed) / 255).astype("uint8")
        overlay = Image.fromarray(arr)
        buffer = io.BytesIO()
        allowed.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode()
        mask_svg = (
            f'<defs><mask id="exclude" maskUnits="userSpaceOnUse" x="0" y="0" '
            f'width="{size[0]}" height="{size[1]}"><image width="{size[0]}" height="{size[1]}" '
            f'href="data:image/png;base64,{encoded}"/></mask></defs>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" '
        f'viewBox="0 0 {size[0]} {size[1]}">{mask_svg}'
        + ('<g mask="url(#exclude)">' if exclusion is not None or config.region_mask else "<g>")
        + f'<g transform="translate({x} {y})">'
        + "".join(c.svg)
        + "</g></g></svg>"
    )
    return (
        overlay,
        svg,
        {
            "drawn_features": drawn,
            "omitted_features": omitted,
            "marker": marker,
            "projection": projection.crs.to_string(),
            "extent_projected_m": projection.extent,
            "art_rect_px": rect,
            "scale": scale,
            "north_is_camera_heading": False,
            "attribution": credits,
            "display_attribution": credit_text,
            "text_boxes_local_px": c.text_boxes,
            "text_records": c.text_records,
            "svg_note": "Font metrics depend on SVG viewer; PNG is the reference rendering",
            "region_distribution": ink_distribution(geometry_alpha, Image.fromarray(c.allowed))
            if geometry_alpha is not None
            else None,
        },
    )
