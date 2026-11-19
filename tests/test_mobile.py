import base64
import io
import json
import sys

import numpy as np
import pytest
from PIL import Image, ImageChops, ImageCms, ImageDraw, ImageOps
from PIL.TiffImagePlugin import IFDRational

from camera_atlas.image.io import read_photo
from camera_atlas.mobile import MobileWorkspace


def payload(size, box):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_upload_confirm_select_render_download_files(tmp_path, photo, data_dir):
    app = MobileWorkspace(tmp_path, data_dir)
    uploaded = app.add_photo(photo.read_bytes())
    request = {
        "photo_id": uploaded["id"],
        "place_id": "san-francisco",
        "confirmed": True,
        "mask": payload((1000, 700), (0, 0, 999, 280)),
        "opacity": 0.7,
    }
    result = app.create_render(request)
    output = app.results[result["id"]]
    for file in ("final.png", "map_overlay.png", "map_region_mask.png", "provenance.json"):
        assert (output / file).is_file()
    base = np.asarray(Image.open(app.photos[uploaded["id"]]))
    final = np.asarray(Image.open(output / "final.png"))
    assert np.array_equal(base[281:], final[281:])
    assert json.loads((output / "provenance.json").read_text())["location"]["accuracy"] == "locality"


@pytest.mark.parametrize("change", [{"confirmed": False}, {"place_id": "tokyo"}, {"photo_id": "unknown"}])
def test_confirmation_and_known_place_required(tmp_path, photo, data_dir, change):
    app = MobileWorkspace(tmp_path, data_dir)
    uploaded = app.add_photo(photo.read_bytes())
    request = {"photo_id": uploaded["id"], "place_id": "san-francisco", "confirmed": True}
    with pytest.raises(ValueError, match="confirm"):
        app.create_render({**request, **change})
    assert not app.results


def test_wrong_size_mask_is_not_silently_rescaled(tmp_path, photo, data_dir):
    app = MobileWorkspace(tmp_path, data_dir)
    uploaded = app.add_photo(photo.read_bytes())
    with pytest.raises(ValueError, match="size"):
        app.create_render(
            {
                "photo_id": uploaded["id"],
                "place_id": "san-francisco",
                "confirmed": True,
                "mask": payload((200, 200), (0, 0, 199, 199)),
            }
        )


def test_phone_photo_keeps_12mp_pixels_orientation_profile_and_source_gps(tmp_path, data_dir):
    original = Image.new("RGB", (4000, 3000), (32, 85, 137))
    ImageDraw.Draw(original).rectangle((0, 0, 100, 100), fill=(190, 65, 40))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    exif = Image.Exif()
    exif[274] = 6
    exif[34853] = {
        1: "N",
        2: (IFDRational(35), IFDRational(30), IFDRational(0)),
        3: "E",
        4: (IFDRational(139), IFDRational(45), IFDRational(0)),
    }
    buffer = io.BytesIO()
    original.save(buffer, "PNG", exif=exif, icc_profile=profile)
    body = buffer.getvalue()
    app = MobileWorkspace(tmp_path, data_dir)
    uploaded = app.add_photo(body)
    assert (uploaded["width"], uploaded["height"]) == (3000, 4000)
    assert uploaded["source_metadata"]["gps"] == {"lat": 35.5, "lon": 139.75}
    assert uploaded["source_metadata"]["orientation"] == 6
    with Image.open(io.BytesIO(body)) as source, Image.open(app.photos[uploaded["id"]]) as result:
        expected = ImageOps.exif_transpose(source).convert("RGBA")
        assert ImageChops.difference(expected, result).getextrema() == ((0, 0),) * 4
        assert result.info["icc_profile"] == profile
        assert not result.getexif().get_ifd(34853)
    assert (tmp_path / f"{uploaded['id']}.input").read_bytes() == body
    restored = MobileWorkspace(tmp_path, data_dir)
    assert restored.photo_info(uploaded["id"])["source_metadata"] == uploaded["source_metadata"]


def test_local_pixel_limit_rejects_before_loading_or_persisting(tmp_path, data_dir, monkeypatch):
    buffer = io.BytesIO()
    Image.new("RGB", (5001, 5000), "blue").save(buffer, "PNG")

    def no_decode(*args, **kwargs):
        pytest.fail("Oversized image reached full image loading")

    monkeypatch.setattr("camera_atlas.mobile.read_photo", no_decode)
    app = MobileWorkspace(tmp_path, data_dir)
    with pytest.raises(ValueError, match="25 megapixels"):
        app.add_photo(buffer.getvalue())
    assert not list(tmp_path.iterdir())


def test_anonymous_heic_without_optional_decoder_has_actionable_error(tmp_path, data_dir, monkeypatch):
    # Only an ISO BMFF header is needed: decoding must stop with a dependency
    # error before trying to interpret this intentionally incomplete test file.
    header = (24).to_bytes(4, "big") + b"ftypheic" + bytes(4) + b"mif1heic"
    monkeypatch.setitem(sys.modules, "pillow_heif", None)
    app = MobileWorkspace(tmp_path, data_dir)
    with pytest.raises(ValueError, match=r"camera-atlas\[heic\]"):
        app.add_photo(header)
    anonymous = tmp_path / "source.input"
    anonymous.write_bytes(header)
    with pytest.raises(ValueError, match=r"camera-atlas\[heic\]"):
        read_photo(anonymous)
    assert not app.photos


def test_heic_upload_without_suffix_matches_decoded_original(tmp_path, data_dir):
    heif = pytest.importorskip("pillow_heif")
    # A synthetic codec fixture, not private photography or geographic data.
    source = Image.new("RGB", (512, 384), (40, 95, 130))
    ImageDraw.Draw(source).rectangle((20, 50, 180, 200), fill=(180, 90, 60))
    buffer = io.BytesIO()
    heif.from_pillow(source).save(buffer, quality=90)
    body = buffer.getvalue()
    app = MobileWorkspace(tmp_path, data_dir)
    uploaded = app.add_photo(body)
    assert uploaded["source_metadata"]["format"] == "HEIF"
    retained = tmp_path / f"{uploaded['id']}.input"
    assert retained.read_bytes() == body
    expected, _ = read_photo(retained)
    with Image.open(app.photos[uploaded["id"]]) as result:
        assert result.size == source.size
        assert ImageChops.difference(expected, result).getextrema() == ((0, 0),) * 4


def test_high_bit_heic_is_not_silently_reduced_to_8bit(tmp_path, data_dir):
    heif = pytest.importorskip("pillow_heif")
    buffer = io.BytesIO()
    heif.from_bytes("RGB;16", (128, 128), np.full((128, 128, 3), 40000, dtype=np.uint16).tobytes()).save(
        buffer, quality=90
    )
    app = MobileWorkspace(tmp_path, data_dir)
    with pytest.raises(ValueError, match="approved SDR export"):
        app.add_photo(buffer.getvalue())
    assert not list(tmp_path.iterdir())
    path = tmp_path / "high-bit.input"
    path.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="approved SDR export"):
        read_photo(path)


@pytest.mark.parametrize("primaries,transfer", [(12, 13), (1, 1)])
def test_nclx_only_non_srgb_heic_is_not_silently_untagged(tmp_path, data_dir, primaries, transfer):
    heif = pytest.importorskip("pillow_heif")
    buffer = io.BytesIO()
    heif.from_pillow(Image.new("RGB", (128, 128), (40, 95, 130))).save(
        buffer,
        quality=90,
        save_nclx_profile=True,
        color_primaries=primaries,
        transfer_characteristics=transfer,
    )
    app = MobileWorkspace(tmp_path, data_dir)
    with pytest.raises(ValueError, match="non-sRGB NCLX"):
        app.add_photo(buffer.getvalue())
    assert not list(tmp_path.iterdir())
    path = tmp_path / "nclx-only.input"
    path.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="non-sRGB NCLX"):
        read_photo(path)
