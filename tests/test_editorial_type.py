"""Typography/credit acceptance checks without modifying photographic geometry."""

import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from camera_atlas import render
from camera_atlas.cartography import renderer


def test_credit_wrap_measures_ink_and_preserves_long_url():
    canvas = renderer.Canvas((200, 100))
    credit = "© OpenStreetMap contributors · openstreetmap.org/copyright"
    lines = renderer.pixel_wrap(canvas, credit, 10, 73)
    assert "".join("".join(lines).split()) == "".join(credit.split())
    assert all(canvas.text_bounds((0, 0), line, 10)[2] <= 73 for line in lines)


def test_failed_credit_candidate_never_leaves_partial_ink(monkeypatch):
    canvas = renderer.Canvas((160, 85))
    canvas.allowed = np.ones((85, 160), dtype=bool)
    before = canvas.image.tobytes()
    original = canvas.text_fits

    def reject_last_line(xy, text, size, **kwargs):
        return "FORBIDDEN" not in text and original(xy, text, size, **kwargs)

    monkeypatch.setattr(canvas, "text_fits", reject_last_line)
    with pytest.raises(ValueError, match="source credit"):
        renderer.region_credit(canvas, ["FIRST LINE · SECOND LINE · FORBIDDEN"], (255, 255, 255, 200))
    assert canvas.image.tobytes() == before
    assert not canvas.svg and not canvas.text_boxes and not canvas.text_records


def test_credit_is_inside_irregular_region_with_margin_and_exact_deduplication():
    canvas = renderer.Canvas((320, 160))
    canvas.allowed = np.zeros((160, 320), dtype=bool)
    canvas.allowed[15:145, 10:180] = True
    canvas.allowed[15:80, 180:310] = True
    credits = [
        "© OpenMapTiles · © OpenStreetMap contributors · openstreetmap.org/copyright",
        "© OpenStreetMap contributors · openstreetmap.org/copyright",
        "Another provider: keep this exact required credit",
    ]
    compact = renderer.compact_credits(credits)
    assert compact.count("© OpenStreetMap contributors") == 1
    assert compact.count("openstreetmap.org/copyright") == 1
    assert "© OpenMapTiles" in compact and credits[2] in compact
    renderer.region_credit(canvas, credits, (255, 255, 255, 230))
    alpha = np.asarray(canvas.finish().getchannel("A"))
    assert alpha.any() and not alpha[~canvas.allowed].any()
    for x0, y0, x1, y1 in canvas.text_boxes:
        assert x0 >= 10 and y0 >= 10 and x1 <= 310 and y1 <= 150


def test_bundled_serif_has_original_license_and_verified_download_hash():
    font = renderer.BUNDLED_FONT
    metadata = json.loads(font.with_name("source.json").read_text())
    assert "SIL OPEN FONT LICENSE Version 1.1" in font.with_name("OFL.txt").read_text()
    assert metadata["files"]["EBGaramond.ttf"]["sha256"] == hashlib.sha256(font.read_bytes()).hexdigest()
    assert renderer.Canvas((200, 100)).font(12).getname()[0] == "EB Garamond"


def test_missing_bundled_font_has_working_latin_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(renderer, "BUNDLED_FONT", tmp_path / "not-installed.ttf")
    canvas = renderer.Canvas((200, 100))
    assert canvas.text((10, 10), "San Francisco", 12, (255, 255, 255, 200))
    assert not canvas.text((10, 40), "京都", 12, (255, 255, 255, 200))
    assert canvas.finish().getbbox() is not None


@pytest.mark.parametrize("exact", [False, True])
def test_primary_location_survives_incidental_labels_and_marker_stays_truthful(
    values, data_dir, tmp_path, exact
):
    mask = tmp_path / "region.png"
    Image.new("L", (1000, 700), 255).save(mask)
    location = {"lat": 37.795, "lon": -122.406} if exact else {}
    result = render(
        {
            **values,
            **location,
            "geojson": data_dir / "san_francisco.geojson",
            "location": "San Francisco",
            "location_label": "San Francisco",
            "radius_km": 0.08,
            "map_mode": "urban",
            "region_mask": mask,
            "opacity": 0.2,
            "svg": True,
        }
    )
    art = json.loads((result.output / "provenance.json").read_text())["cartography"]
    marker = art["marker"]
    assert marker["label"] == "San Francisco"
    assert marker["filled"] is exact
    assert marker["rgba"][0] > 200 and marker["rgba"][1] < 100 and marker["rgba"][3] >= 240
    assert 3 <= marker["radius_px"] <= 7
    assert art["text_records"][0]["text"] == "San Francisco"
    assert art["text_records"][0]["size_px"] <= 18
    secondary = [f["label"] for f in art["drawn_features"] if f["kind"] == "label"]
    assert len(secondary) <= 3
    assert all(r["size_px"] <= 13 for r in art["text_records"] if r["text"] in secondary)
    tree = ET.fromstring((result.output / "map_overlay.svg").read_text())
    circle = tree.find(".//{http://www.w3.org/2000/svg}circle")
    assert (circle.attrib["fill"] != "none") is exact
    assert "serif" in (result.output / "map_overlay.svg").read_text()
