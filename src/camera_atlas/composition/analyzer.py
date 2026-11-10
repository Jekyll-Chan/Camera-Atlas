"""Conservative texture/contrast heuristic, not semantic subject recognition."""

import numpy as np
from PIL import Image, ImageFilter


def analyze(image, exclusion=None):
    thumb = image.convert("L")
    thumb.thumbnail((384, 384))
    a = np.asarray(thumb, dtype=float) / 255
    blur = np.asarray(thumb.filter(ImageFilter.GaussianBlur(4)), dtype=float) / 255
    gx = np.abs(np.diff(a, axis=1, prepend=a[:, :1]))
    gy = np.abs(np.diff(a, axis=0, prepend=a[:1, :]))
    score = np.clip((gx + gy) * 3 + np.abs(a - blur) * 3, 0, 1)
    protected = Image.fromarray((score * 255).astype("uint8")).resize(image.size, Image.Resampling.BILINEAR)
    if exclusion is not None:
        protected = Image.fromarray(np.maximum(np.asarray(protected), np.asarray(exclusion)))
    # Only a screenshot hint: no irreversible crop or inference of hidden content.
    edges = np.concatenate([a[0], a[-1]])
    hints = []
    if float((edges < 0.025).mean()) > 0.65:
        hints.append("Possible black player bars; review source frame and any embedded UI")
    return protected, hints


def place(size, saliency, area, requested="auto"):
    w, h = size
    # Square local map; target area is capped by margins and real negative space.
    side = int(min((w * h * area) ** 0.5, w * 0.70, h * 0.70))
    margin = max(8, int(min(size) * 0.045))
    a = np.asarray(saliency, dtype=float) / 255

    def candidates(s):
        return {
            "top-left": (margin, margin, s, s),
            "top-right": (w - margin - s, margin, s, s),
            "bottom-left": (margin, h - margin - s, s, s),
            "bottom-right": (w - margin - s, h - margin - s, s, s),
        }

    def density(rect):
        x, y, rw, rh = rect
        return float(a[y : y + rh, x : x + rw].mean())

    boxes = candidates(side)
    key = min(boxes, key=lambda k: density(boxes[k])) if requested == "auto" else requested
    if requested == "auto" and density(boxes[key]) > 0.24:
        side = max(32, int(side * 0.72))
        boxes = candidates(side)
        key = min(boxes, key=lambda k: density(boxes[k]))
    rect = boxes[key]
    return rect, {
        "position": key,
        "texture_risk": density(rect),
        "method": "edge density and local contrast; manual subject masks recommended",
    }
