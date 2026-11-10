"""Render one geographic scene to a transparent PNG and editable SVG."""

import html
import math
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Geod
from shapely.geometry import box, shape

from .design import KINDS, THEMES


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
        self.font_path = font
        self.svg = []
        self.text_boxes = []

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

    def text(self, xy, text, size, color, avoid=True):
        # Pillow's built-in font covers Latin. A supplied font enables other scripts.
        if not self.font_path and any(ord(c) > 255 for c in text):
            return False
        font = (
            ImageFont.truetype(str(self.font_path), size * 2)
            if self.font_path
            else ImageFont.load_default(size=size * 2)
        )
        x, y = xy
        bounds = self.draw.textbbox((x * 2, y * 2), text, font=font)
        b = tuple(v / 2 for v in bounds)
        if b[0] < 0 or b[1] < 0 or b[2] > self.size[0] or b[3] > self.size[1]:
            return False
        if avoid and any(
            b[0] < p[2] + 5 and b[2] + 5 > p[0] and b[1] < p[3] + 5 and b[3] + 5 > p[1]
            for p in self.text_boxes
        ):
            return False
        self.draw.text((x * 2, y * 2), text, font=font, fill=color)
        self.text_boxes.append(b)
        ink, opacity = self.color(color)
        self.svg.append(
            f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" '
            f'font-family="sans-serif" font-size="{size}" fill="{ink}" fill-opacity="{opacity}">'
            f"{html.escape(text)}</text>"
        )
        return True

    def finish(self):
        return self.image.resize(self.size, Image.Resampling.LANCZOS)


def render_map(size, rect, projection, data, location, mode, config, exclusion=None):
    x, y, w, h = rect
    # Small local supersampled canvas avoids a full-frame 4x allocation.
    c = Canvas((w, h), config.font)
    theme = THEMES[config.style]
    alpha = round(config.opacity * 255)
    ink = (*theme.ink, alpha)
    accent = (*theme.accent, alpha)
    gutter = max(12, int(w * 0.07))
    footer = max(55, int(h * 0.18))
    usable = min(w - 2 * gutter, h - footer - 2 * gutter)
    r = projection.radius
    factor = usable / (2 * r)
    ox, oy = w / 2, (h - footer) / 2

    def pixel(px, py):
        return ox + px * factor, oy - py * factor

    viewport = box(-r, -r, r, r)
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
    # No reliable map geometry => clean photograph; do not fabricate a standalone locator.
    if not drawn:
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
    c.circle(
        mx,
        my,
        max(2.5, w * 0.008) if location.accuracy == "exact_gps" else max(6, w * 0.022),
        accent,
        filled=location.accuracy == "exact_gps",
    )
    if config.labels:
        count = 0
        for pos, name, index in candidates:
            if count >= theme.max_labels:
                break
            if c.text((pos[0] + 7, pos[1] + 3), name, max(9, int(w * 0.027)), ink):
                count += 1
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
    credit_lines = [
        line
        for credit in credits
        for line in textwrap.wrap(credit, width=max(16, int((w - 2 * gutter) / 4.6)))
    ]
    credit_start = len(c.text_boxes)
    for i, credit in enumerate(credit_lines):
        if not c.text(
            (gutter, h - footer + 4 + i * 12), credit, 8, (*theme.ink, max(alpha, 190)), avoid=False
        ):
            raise ValueError(
                "Map too small for required attribution; increase --map-area or shorten approved attribution"
            )
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
    if exclusion is not None:
        import base64
        import io

        allowed = Image.fromarray(255 - np.asarray(exclusion)).convert("L")
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
        + ('<g mask="url(#exclude)">' if exclusion is not None else "<g>")
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
            "text_boxes_local_px": c.text_boxes,
            "svg_note": "Font metrics depend on SVG viewer; PNG is the reference rendering",
        },
    )
