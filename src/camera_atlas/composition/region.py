"""Explicit artistic regions. These masks do not infer geographic registration."""

import numpy as np
from PIL import Image, ImageFilter


def prepare_region(region, exclusion=None):
    bounds = region.getbbox()
    if bounds is None:
        raise ValueError("Map region is empty; select an area first")
    x, y, right, bottom = bounds
    w, h = right - x, bottom - y
    if min(w, h) < 64:
        raise ValueError("Map region must be at least 64 pixels wide and high")
    allowed = np.asarray(region) > 0
    if exclusion is not None:
        allowed &= np.asarray(exclusion) == 0
    if not allowed.any():
        raise ValueError("Map region is completely protected by the exclusion mask")
    mask = Image.fromarray(allowed.astype("uint8") * 255)
    # Keep the locator inside the allowed region, including regions with holes.
    interior = np.asarray(mask.filter(ImageFilter.MinFilter(17))) > 0
    ys, xs = np.nonzero(interior if interior.any() else allowed)
    nearest = np.argmin((xs - (x + w / 2)) ** 2 + (ys - (y + h / 2)) ** 2)
    anchor = ((float(xs[nearest]) - x) / w, (float(ys[nearest]) - y) / h)
    return (x, y, w, h), mask, anchor


def ink_distribution(geometry_alpha, allowed, divisions=4):
    """Geometry-only diagnostic, NOT a claim that data or a region is complete."""
    a = np.asarray(geometry_alpha) > 0
    m = np.asarray(allowed) > 0
    ys, xs = np.nonzero(m)
    if not len(xs):
        return {"eligible_cells": 0, "cells_with_geometry": 0, "review_required": True}
    xcuts = np.linspace(xs.min(), xs.max() + 1, divisions + 1, dtype=int)
    ycuts = np.linspace(ys.min(), ys.max() + 1, divisions + 1, dtype=int)
    cells = []
    for row in range(divisions):
        for col in range(divisions):
            sl = np.s_[ycuts[row] : ycuts[row + 1], xcuts[col] : xcuts[col + 1]]
            selected = m[sl]
            if not selected.size or selected.mean() < 0.1:
                continue
            pixels = int((a[sl] & selected).sum())
            cells.append({"row": row, "column": col, "geometry_pixels": pixels})
    return {
        "eligible_cells": len(cells),
        "cells_with_geometry": sum(c["geometry_pixels"] > 0 for c in cells),
        "cells": cells,
        "review_required": True,
        "meaning": "Geometry only, excluding text/marker/credits. Sparse real geography can leave empty cells."
        " This does not measure source completeness or aesthetic success.",
    }
