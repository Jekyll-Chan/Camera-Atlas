from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def prepare_photo_decoder(header: bytes, suffix=""):
    """Register optional HEIF support before Pillow probes anonymous uploads.

    Uploads are stored as ``.input`` files, so a filename extension alone cannot
    select their decoder. HEIF declares its brands in the ISO BMFF ftyp box.
    """
    brands = set()
    if len(header) >= 16 and header[4:8] == b"ftyp":
        size = min(int.from_bytes(header[:4], "big"), len(header))
        brands = {header[8:12], *(header[i : i + 4] for i in range(16, size - 3, 4))}
    heif_brands = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs", b"mif1", b"msf1"}
    if suffix.lower() in (".heic", ".heif") or brands & heif_brands:
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except ImportError as exc:
            raise ValueError(
                "HEIC/HEIF input needs the optional camera-atlas[heic] decoder in the renderer's "
                "isolated environment. The original has not been converted or resized."
            ) from exc


def read_photo(path: Path):
    path = Path(path)
    with path.open("rb") as source:
        prepare_photo_decoder(source.read(4096), path.suffix)
    with Image.open(path) as image:
        check_photo_colour(image)
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


def check_photo_colour(image):
    """Reject HEIF inputs this 8-bit compositor cannot preserve faithfully."""
    if image.format != "HEIF":
        return
    profile = image.info.get("nclx_profile") or {}
    high_depth = image.info.get("bit_depth", 8) > 8
    hdr = profile.get("transfer_characteristics") in (16, 18)
    hdr |= bool(image.info.get("mastering_display_colour_volume"))
    hdr |= any("hdrgainmap" in str(key).lower() for key in image.info.get("aux", {}))
    if high_depth or hdr:
        raise ValueError(
            "This HEIC/HEIF contains high-bit-depth or HDR image data. The current renderer only "
            "preserves 8-bit SDR images; provide an approved SDR export. No automatic colour or "
            "tone conversion was applied."
        )
    if (
        profile
        and not image.info.get("icc_profile")
        and (profile.get("color_primaries"), profile.get("transfer_characteristics")) != (1, 13)
    ):
        raise ValueError(
            "This HEIC/HEIF uses a non-sRGB NCLX colour profile without an ICC profile. The current "
            "PNG exporter cannot preserve that profile; provide an approved sRGB export or an "
            "8-bit SDR image with an embedded ICC profile. No automatic colour conversion was applied."
        )


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
