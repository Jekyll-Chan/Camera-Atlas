import numpy as np


def verify(original, clean, overlay, final, repair_mask=None, exclusion=None):
    if not (original.size == clean.size == overlay.size == final.size):
        raise ValueError("Image dimensions changed unexpectedly")
    a, b, o, f = (np.asarray(x) for x in (original, clean, overlay, final))
    approved = np.asarray(repair_mask) > 0 if repair_mask else np.zeros(a.shape[:2], bool)
    repair_changed = np.any(a != b, axis=2)
    if np.any(repair_changed & ~approved):
        raise ValueError("Base pixels modified outside approved repair mask")
    changed = np.any(f != b, axis=2)
    covered = o[:, :, 3] > 0
    if np.any(changed & ~covered):
        raise ValueError("Composition changed pixels outside overlay alpha")
    if exclusion is not None and np.any(covered & (np.asarray(exclusion) > 0)):
        raise ValueError("Overlay intersects a user-protected subject")
    if not np.any(o[:, :, 3] == 0):
        raise ValueError("Map layer has no transparent pixels")
    # Pixel-level legibility proxy. It is not a semantic or print-contrast guarantee.
    delta = np.abs(f[:, :, :3].astype(float) - b[:, :, :3].astype(float)).mean(axis=2)
    substantial = o[:, :, 3] >= 64
    contrast = float(np.median(delta[substantial])) if np.any(substantial) else None
    low_fraction = float((delta[substantial] < 12).mean()) if np.any(substantial) else None
    return {
        "passed": True,
        "median_overlay_rgb_delta": contrast,
        "low_contrast_fraction": low_fraction,
        "dimensions": list(original.size),
        "aspect_ratio_preserved": True,
        "unexpected_base_pixels": 0,
        "unexpected_composite_pixels": 0,
        "repair_changed_pixels": int(repair_changed.sum()),
        "overlay_coverage": float(covered.mean()),
        "alpha_max": int(o[:, :, 3].max()),
        "edge_alpha_pixels": int(
            np.count_nonzero(np.concatenate((o[0, :, 3], o[-1, :, 3], o[:, 0, 3], o[:, -1, 3])))
        ),
    }
