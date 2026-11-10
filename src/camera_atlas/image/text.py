"""Explicitly masked local repair; optional system Tesseract detection."""

import csv
import io
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw


def detect_text(path, size):
    if not shutil.which("tesseract"):
        raise ValueError("OCR requires the optional system tesseract executable")
    try:
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "tsv"], capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("Tesseract could not read the normalized image: " + exc.stderr[:300]) from exc
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    boxes = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        if float(row.get("conf", -1)) < 60 or not row.get("text", "").strip():
            continue
        x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
        draw.rectangle(
            (max(0, x - 2), max(0, y - 2), min(size[0] - 1, x + w + 2), min(size[1] - 1, y + h + 2)), fill=255
        )
        boxes.append({"text": row["text"], "bbox": [x, y, w, h], "requires_review": True})
    return mask, boxes


def repair(image, mask):
    try:
        import cv2
    except ImportError as exc:
        raise ValueError("Install camera-atlas[repair] for local text repair") from exc
    pixels = np.asarray(image).copy()
    selected = np.asarray(mask) > 0
    if selected.mean() > 0.1:
        raise ValueError("Repair mask exceeds 10% of the photo; review and reduce it")
    # Inpaint is an interpolation, never represented as a recovery of hidden photography.
    fixed = cv2.inpaint(pixels[:, :, :3], np.asarray(mask), 3, cv2.INPAINT_TELEA)
    pixels[selected, :3] = fixed[selected]
    return Image.fromarray(pixels), {
        "method": "OpenCV TELEA local interpolation",
        "requires_review": True,
        "masked_pixels": int(selected.sum()),
        "warning": "Occluded detail cannot be verified or recovered",
    }
