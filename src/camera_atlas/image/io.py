from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def read_photo(path: Path):
    if path.suffix.lower() in (".heic", ".heif"):
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except ImportError as exc:
            raise ValueError("Install camera-atlas[heic] for HEIC input") from exc
    with Image.open(path) as image:
        gps = read_gps(image)
        exif = image.getexif()
        info = {
            "format": image.format,
            "icc_profile": image.info.get("icc_profile"),
            "exif": exif.tobytes(),
            "gps": gps,
            "orientation": exif.get(274, 1),
        }
        # ICC is retained; no conversion, enhancement, resizing or tone mapping.
        base = ImageOps.exif_transpose(image).convert("RGBA")
    return base, info


def read_gps(image):
    try:
        gps = image.getexif().get_ifd(34853)

        def degrees(v):
            return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600

        lat, lon = degrees(gps[2]), degrees(gps[4])
        lat *= -1 if gps.get(1) in ("S", b"S") else 1
        lon *= -1 if gps.get(3) in ("W", b"W") else 1
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return {"lat": lat, "lon": lon}
    except (KeyError, ValueError, TypeError, ZeroDivisionError, IndexError):
        return None


def load_mask(path, size):
    with Image.open(path) as image:
        if image.size != size:
            raise ValueError("Mask must match the EXIF-normalized image dimensions")
        return Image.fromarray(np.where(np.asarray(image.convert("L")) > 0, 255, 0).astype("uint8"))


def png_info(info, preserve=False):
    result = {}
    if info.get("icc_profile"):
        result["icc_profile"] = info["icc_profile"]
    if preserve:
        exif = Image.Exif()
        exif.load(info["exif"])
        # Orientation was already applied. Dimensions refer to the encoded source and are removed.
        for key in (274, 256, 257):
            if key in exif:
                del exif[key]
        result["exif"] = exif.tobytes()
    return result
