"""Region fitting against the real OSM extract; no fabricated geographic lines."""

import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from camera_atlas import render
from camera_atlas.geography.projection import MapProjection


@pytest.mark.parametrize("width,height", [(900, 240), (240, 600)])
def test_region_uniform_scale_expands_long_axis(width, height):
    p = MapProjection(37.795, -122.406, 0.1).fit_region(width, height)
    left, b, r, t = p.extent
    assert (r - left) / (t - b) == pytest.approx(width / height)
    assert min(r - left, t - b) == pytest.approx(200)
    assert width / (r - left) == pytest.approx(height / (t - b))
    west, south, east, north = p.bounds_wgs84()
    for x in np.linspace(left, r, 31):
        for y in (b, t):
            lon, lat = p.inverse.transform(x, y)
            assert west - 1e-6 <= lon <= east + 1e-6
            assert south - 1e-6 <= lat <= north + 1e-6


@pytest.mark.parametrize("rect", [(10, 20, 990, 290), (620, 10, 990, 690)])
def test_region_fills_long_axis_and_preserves_subject(values, data_dir, tmp_path, rect):
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle(rect, fill=255)
    hole = (int((rect[0] + rect[2]) / 2 - 35), rect[1] + 60, int((rect[0] + rect[2]) / 2 + 35), rect[3] - 60)
    ImageDraw.Draw(mask).rectangle(hole, fill=0)
    path = tmp_path / "region.png"
    mask.save(path)
    result = render(
        {
            **values,
            "geojson": data_dir / "san_francisco.geojson",
            "location": "San Francisco",
            "radius_km": 0.08,
            "map_mode": "urban",
            "region_mask": path,
            "map_area": 0.03,
            "position": "bottom-left",
            "svg": True,
        }
    )
    overlay = np.asarray(Image.open(result.output / "map_overlay.png"))
    base = np.asarray(Image.open(result.output / "clean_base.png"))
    final = np.asarray(Image.open(result.final))
    outside = np.asarray(mask) == 0
    assert not overlay[outside, 3].any()
    assert np.array_equal(base[outside], final[outside])
    assert result.metadata["quality"]["outside_region_pixels"] == 0
    p = json.loads((result.output / "provenance.json").read_text())["cartography"]
    x, y, w, h = p["art_rect_px"]
    assert (x, y, w, h) == (rect[0], rect[1], rect[2] - rect[0] + 1, rect[3] - rect[1] + 1)
    left, b, r, t = p["extent_projected_m"]
    assert (r - left) / (t - b) == pytest.approx(w / h)
    cells = p["region_distribution"]["cells"]
    # Map geometry itself reaches both ends, not merely credit or location marker.
    axis = "column" if w > h else "row"
    assert any(c[axis] == 0 and c["geometry_pixels"] > 0 for c in cells)
    assert any(c[axis] == 3 and c["geometry_pixels"] > 0 for c in cells)
    assert 'mask="url(#exclude)"' in (result.output / "map_overlay.svg").read_text()


def test_empty_region_refused(values, tmp_path):
    path = tmp_path / "empty.png"
    Image.new("L", (1000, 700)).save(path)
    with pytest.raises(ValueError, match="empty"):
        render({**values, "region_mask": path})


def test_expanded_extent_used_for_provider(values, tmp_path, monkeypatch):
    from camera_atlas.geography.models import GeoData

    calls = []

    def fetch(self, bounds):
        calls.append(bounds)
        return GeoData()

    monkeypatch.setattr("camera_atlas.pipeline.Overpass.fetch", fetch)
    path = tmp_path / "wide.png"
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle((0, 0, 999, 199), fill=255)
    mask.save(path)
    result = render(
        {**values, "geojson": None, "location": None, "lat": 0, "lon": 0, "radius_km": 1, "region_mask": path}
    )
    west, south, east, north = calls[0]
    assert (east - west) / (north - south) == pytest.approx(5, rel=0.01)
    assert result.metadata["quality"]["overlay_coverage"] == 0


def test_region_exclusion_overrides_selection(values, data_dir, tmp_path):
    region = tmp_path / "region.png"
    protected = tmp_path / "protected.png"
    Image.new("L", (1000, 700), 255).save(region)
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle((400, 50, 600, 650), fill=255)
    mask.save(protected)
    result = render(
        {
            **values,
            "geojson": data_dir / "san_francisco.geojson",
            "location": "San Francisco",
            "radius_km": 0.1,
            "region_mask": region,
            "exclusion_mask": protected,
        }
    )
    overlay = np.asarray(Image.open(result.output / "map_overlay.png"))
    assert not overlay[np.asarray(mask) > 0, 3].any()
    assert result.metadata["quality"]["passed"]
