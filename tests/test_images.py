import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from camera_atlas import RenderConfig, render
from camera_atlas.image.io import read_gps, read_photo
from camera_atlas.image.text import repair
from camera_atlas.validation.integrity import verify


def test_exif_gps():
    class Exif:
        def get_ifd(self, key):
            return {1: "S", 2: (12, 30, 0), 3: "W", 4: (70, 15, 0)}

    class FakeImage:
        def getexif(self):
            return Exif()

    assert read_gps(FakeImage()) == {"lat": -12.5, "lon": -70.25}


def test_real_exif_orientation_and_gps(tmp_path):
    from PIL.TiffImagePlugin import IFDRational

    p = tmp_path / "oriented.jpg"
    im = Image.new("RGB", (220, 140), "blue")
    exif = Image.Exif()
    exif[274] = 6
    exif[34853] = {
        1: "N",
        2: (IFDRational(46), IFDRational(30), IFDRational(0)),
        3: "E",
        4: (IFDRational(8), IFDRational(15), IFDRational(0)),
    }
    im.save(p, exif=exif)
    read, info = read_photo(p)
    assert read.size == (140, 220)
    assert info["gps"] == {"lat": 46.5, "lon": 8.25}


def test_no_map_exact_normalized_pixels(values):
    result = render({**values, "map_enabled": False})
    expected, _ = read_photo(values["input"])
    actual = Image.open(result.final)
    assert np.array_equal(np.array(expected), np.array(actual))
    assert result.metadata["quality"]["unexpected_composite_pixels"] == 0


def test_lake_render_transparency_and_integrity(values):
    result = render({**values, "svg": True})
    overlay = Image.open(result.output / "map_overlay.png")
    final = Image.open(result.final)
    base = Image.open(result.output / "clean_base.png")
    a = np.array(overlay)
    assert overlay.mode == "RGBA" and a[:, :, 3].max() > 0 and a[:, :, 3].min() == 0
    assert final.size == base.size == (1000, 700)
    assert np.array_equal(np.array(final)[a[:, :, 3] == 0], np.array(base)[a[:, :, 3] == 0])
    p = json.loads((result.output / "provenance.json").read_text())
    assert p["location"]["accuracy"] == "locality"
    assert p["cartography"]["marker"]["accuracy"] == "locality"
    assert p["cartography"]["north_is_camera_heading"] is False
    assert (result.output / "map_overlay.svg").is_file()
    assert not p["cartography"]["scale"]


def test_exact_marker(values):
    result = render({**values, "lat": 46.98, "lon": 8.42})
    p = json.loads((result.output / "provenance.json").read_text())
    marker = p["cartography"]["marker"]
    assert marker["accuracy"] == "exact_gps"
    assert marker["coordinates"] == [8.42, 46.98]


def test_natural_earth_not_upscaled(values):
    result = render({**values, "radius_km": 10})
    assert np.array(Image.open(result.output / "map_overlay.png"))[:, :, 3].max() == 0
    p = json.loads((result.output / "provenance.json").read_text())
    assert p["cartography"]["omitted_features"]


def test_data_failure_clean_fallback(values, monkeypatch):
    from camera_atlas.geography.http import ProviderError

    def failure(*args):
        raise ProviderError("test outage")

    monkeypatch.setattr("camera_atlas.pipeline.Overpass.fetch", failure)
    result = render({**values, "geojson": None, "location": None, "lat": 40, "lon": 80})
    original, _ = read_photo(values["input"])
    assert np.array_equal(np.array(original), np.array(Image.open(result.final)))
    assert any("outage" in w for w in result.metadata["warnings"])


def test_no_gps_unresolved(values):
    result = render({**values, "geojson": None, "location": None})
    assert result.metadata["location"]["accuracy"] == "unresolved"
    assert result.metadata["quality"]["overlay_coverage"] == 0


def test_approved_repair_only_selected_pixels(values, tmp_path):
    image, _ = read_photo(values["input"])
    draw = ImageDraw.Draw(image)
    draw.text((50, 50), "OLD TEXT", fill="white")
    image.save(values["input"])
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).rectangle((45, 45, 120, 70), fill=255)
    path = tmp_path / "mask.png"
    mask.save(path)
    result = render({**values, "map_enabled": False, "remove_text": True, "text_mask": path})
    final = np.array(Image.open(result.final))
    original = np.array(image)
    assert np.array_equal(final[np.array(mask) == 0], original[np.array(mask) == 0])
    assert result.metadata["repair"]["requires_review"]
    assert result.metadata["quality"]["repair_changed_pixels"] > 0


def test_large_repair_refused():
    im = Image.new("RGBA", (200, 200))
    mask = Image.new("L", im.size, 255)
    with pytest.raises(ValueError, match="10%"):
        repair(im, mask)


def test_repair_requires_mask(values):
    with pytest.raises(ValueError, match="reviewed"):
        RenderConfig(**{**values, "remove_text": True})


def test_subject_exclusion(values, tmp_path):
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle((5, 5, 150, 150), fill=255)
    path = tmp_path / "exclude.png"
    mask.save(path)
    result = render({**values, "position": "top-left", "exclusion_mask": path, "svg": True})
    overlay = np.array(Image.open(result.output / "map_overlay.png"))
    assert not np.any(overlay[:151, :151, 3])
    assert 'mask="url(#exclude)"' in (result.output / "map_overlay.svg").read_text()


def test_wrong_mask_dimensions(values, tmp_path):
    p = tmp_path / "wrong.png"
    Image.new("L", (10, 10)).save(p)
    with pytest.raises(ValueError, match="dimensions"):
        render({**values, "exclusion_mask": p})


def test_existing_output_preserved(values):
    result = render(values)
    before = result.final.read_bytes()
    with pytest.raises(ValueError, match="not empty"):
        render(values)
    assert before == result.final.read_bytes()


def test_integrity_rejects_base_modification():
    original = Image.new("RGBA", (128, 128), "black")
    clean = original.copy()
    clean.putpixel((1, 1), (255, 0, 0, 255))
    overlay = Image.new("RGBA", original.size)
    with pytest.raises(ValueError, match="Base pixels"):
        verify(original, clean, overlay, clean)


def test_metadata_orientation_reset(values, tmp_path):
    p = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (300, 500), "red").save(p, exif=exif)
    result = render({**values, "input": p, "map_enabled": False, "preserve_metadata": True})
    im = Image.open(result.final)
    assert im.size == (500, 300) and im.getexif().get(274, 1) == 1


@pytest.mark.parametrize(
    "theme",
    ["editorial-minimal", "topographic-fine", "coastal-atlas", "urban-documentary", "monochrome-print"],
)
def test_all_themes(values, theme):
    result = render({**values, "style": theme})
    assert result.metadata["quality"]["passed"]


def test_mountain_e2e(values, data_dir):
    result = render(
        {
            **values,
            "geojson": None,
            "location": None,
            "lat": 46.9,
            "lon": 8.6,
            "confirmed_region": True,
            "dem": data_dir / "alps_dem.tif",
            "dem_source": data_dir / "alps_dem.source.json",
            "radius_km": 16,
            "contour_interval": 400,
            "map_mode": "topographic",
            "svg": True,
        }
    )
    assert result.metadata["quality"]["overlay_coverage"] > 0
    p = json.loads((result.output / "provenance.json").read_text())
    assert all(f["kind"] == "contour" for f in p["cartography"]["drawn_features"])
    assert p["cartography"]["marker"]["accuracy"] == "regional"


def test_city_e2e(values, data_dir):
    result = render(
        {
            **values,
            "geojson": data_dir / "san_francisco.geojson",
            "location": "San Francisco",
            "radius_km": 0.45,
            "map_mode": "urban",
            "north": True,
        }
    )
    assert result.metadata["quality"]["overlay_coverage"] > 0
    p = json.loads((result.output / "provenance.json").read_text())
    assert p["cartography"]["attribution"] == ["© OpenStreetMap contributors · openstreetmap.org/copyright"]
    assert any(f["kind"] == "road" for f in p["cartography"]["drawn_features"])


def test_credit_cannot_be_masked(values, tmp_path):
    mask = Image.new("L", (1000, 700), 255)
    p = tmp_path / "everything.png"
    mask.save(p)
    result = render({**values, "exclusion_mask": p})
    assert result.metadata["quality"]["overlay_coverage"] == 0
    assert any("attribution" in w for w in result.metadata["warnings"])
