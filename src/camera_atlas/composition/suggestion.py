"""Low-cost editable negative-space suggestions, not semantic segmentation.

The heuristic searches every image edge, so a deliberately sideways photograph
is never rotated. Smooth, similarly coloured pixels connected to an edge form a
candidate. Contrasting interiors remain holes, including at full resolution.
Confidence is a ranking score, NOT a calibrated subject-protection probability.
Every suggestion requires review; this cannot reliably recognise sky, people,
buildings, screenshot UI, or objects sharing the background's colour.
"""

from collections import deque
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

METHOD = "boundary-connected colour and texture; not semantic segmentation"


@dataclass
class RegionSuggestion:
    mask: Image.Image
    confidence: float
    reason: str
    requires_review: bool = True
    method: str = METHOD


def _empty(size, reason):
    return RegionSuggestion(Image.new("L", size), 0.0, reason)


def _edge_components(allowed):
    """Keep edge-connected areas across wires; never fill holes or convex hulls."""
    height, width = allowed.shape
    seen = np.zeros_like(allowed)
    edges = (
        [(0, x) for x in range(width)]
        + [(height - 1, x) for x in range(width)]
        + [(y, 0) for y in range(height)]
        + [(y, width - 1) for y in range(height)]
    )
    for y, x in edges:
        if seen[y, x] or not allowed[y, x]:
            continue
        queue = deque([(y, x)])
        seen[y, x] = True
        while queue:
            py, px = queue.popleft()
            for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                if 0 <= ny < height and 0 <= nx < width and allowed[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
    return seen


def _colour_match(rgb, colour):
    # Use per-channel temporaries to avoid a float64 full-resolution RGB copy.
    total = np.zeros(rgb.shape[:2], dtype=np.int16)
    matches = np.ones(rgb.shape[:2], dtype=bool)
    for channel in range(3):
        delta = np.abs(rgb[:, :, channel].astype(np.int16) - int(colour[channel]))
        matches &= delta <= 58
        total += delta
    return matches & (total <= 108)


def suggest_region(image: Image.Image) -> RegionSuggestion:
    """Return an exact-size binary editable mask, or an empty review fallback.

    No network, model download, original-image mutation, or per-image API charge.
    A whole-image flat colour is rejected because there is no supported contrast
    boundary to distinguish a photograph's subject from background.
    """
    if min(image.size) < 128:
        return _empty(image.size, "Choose a larger photo or select an area manually.")
    rgb_image = image.convert("RGB")
    thumb = rgb_image.copy()
    thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)
    rgb = np.asarray(thumb)
    blurred = np.asarray(thumb.filter(ImageFilter.GaussianBlur(2)))
    residual = np.abs(rgb.astype(np.int16) - blurred.astype(np.int16)).max(axis=2)
    signed = rgb.astype(np.int16)
    horizontal = np.abs(np.diff(signed, axis=1, prepend=signed[:, :1])).max(axis=2)
    vertical = np.abs(np.diff(signed, axis=0, prepend=signed[:1])).max(axis=2)
    smooth = (residual < 17) & (horizontal < 27) & (vertical < 27)
    if "A" in image.getbands():
        alpha = image.getchannel("A").resize(thumb.size, Image.Resampling.NEAREST)
        smooth &= np.asarray(alpha) == 255

    edge_colours = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]))
    edge_smooth = np.concatenate((smooth[0], smooth[-1], smooth[:, 0], smooth[:, -1]))
    edge_colours = edge_colours[edge_smooth]
    if len(edge_colours) < 12:
        return _empty(image.size, "No clear quiet area found. Select the map area manually.")
    # Several observed border palettes handle sky, water and neutral backgrounds.
    # They are candidates only; no colour is labelled as a semantic class.
    bins, inverse, counts = np.unique(edge_colours // 32, axis=0, return_inverse=True, return_counts=True)
    del bins
    best, best_colour, best_score = None, None, 0.0
    for index in np.argsort(counts)[-6:]:
        if counts[index] < 8:
            continue
        colour = np.median(edge_colours[inverse == index], axis=0)
        candidate = _edge_components(smooth & _colour_match(rgb, colour))
        fraction = float(candidate.mean())
        if not 0.08 <= fraction <= 0.85:
            continue
        ys, xs = np.nonzero(candidate)
        if (
            min(
                (xs.max() - xs.min() + 1) / thumb.width * image.width,
                (ys.max() - ys.min() + 1) / thumb.height * image.height,
            )
            < 64
        ):
            continue
        score = fraction * (1 - float(residual[candidate].mean()) / 20)
        if score > best_score:
            best, best_colour, best_score = candidate, colour, score
    if best is None:
        return _empty(image.size, "No distinct quiet area found. Select the map area manually.")

    # Full-resolution colour refinement restores narrow contrasting branches and
    # objects lost by thumbnail sampling. It does not guarantee semantic safety.
    mask = Image.fromarray(best.astype(np.uint8) * 255).resize(image.size, Image.Resampling.NEAREST)
    selected = (np.asarray(mask) > 0) & _colour_match(np.asarray(rgb_image), best_colour)
    if "A" in image.getbands():
        selected &= np.asarray(image.getchannel("A")) == 255
    mask = Image.fromarray(selected.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))
    fraction = float((np.asarray(mask) > 0).mean())
    if fraction < 0.06:
        return _empty(image.size, "The suggested area is too fragmented. Select an area manually.")
    return RegionSuggestion(
        mask=mask,
        confidence=round(min(0.75, 0.35 + best_score * 0.5), 3),
        reason="Review the suggested area, especially buildings, people and branches.",
    )
