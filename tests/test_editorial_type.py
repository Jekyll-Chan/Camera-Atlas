"""Typography/credit acceptance checks without modifying photographic geometry."""

import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image, ImageCms

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


def test_transparent_text_clearance_removes_only_linework_and_matches_svg():
    # Analytical drawing primitives, not claimed geographic features.
    canvas = renderer.Canvas((220, 100))
    canvas.line([(0, 25), (219, 25)], (220, 220, 220, 180), 2)
    untouched_geometry = canvas.image.tobytes()
    canvas.begin_annotations()
    canvas.circle(35, 25, 5, (232, 72, 58, 245), filled=False)
    marker_before = canvas.image.copy()
    assert canvas.text((40, 20), "A place", 14, (240, 235, 220, 220))
    assert canvas.geometry_image.tobytes() == untouched_geometry
    left, top, right, bottom = canvas.text_clearances[0]
    cleared = np.asarray(canvas.cleared_geometry())
    assert not cleared[top * 2 : bottom * 2, left * 2 : right * 2, 3].any()
    assert cleared[50, 10, 3] > 0
    # Marker lies partly inside the clearance rectangle but on another layer.
    marker_pixels = np.asarray(marker_before)[:, :, 3] > 0
    assert np.array_equal(np.asarray(canvas.image)[marker_pixels], np.asarray(marker_before)[marker_pixels])
    assert np.any(np.asarray(canvas.finish())[:, :, 3] == 0)
    root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">' + canvas.svg_markup() + "</svg>")
    ns = {"s": "http://www.w3.org/2000/svg"}
    geometry_group = root.find('s:g[@mask="url(#map-geometry-clearance)"]', ns)
    assert geometry_group.find("s:polyline", ns) is not None
    assert geometry_group.find("s:circle", ns) is None
    assert root.find("s:circle", ns) is not None and root.find("s:text", ns) is not None
    knockout = root.find('s:defs/s:mask/s:rect[@fill="black"]', ns)
    assert tuple(int(knockout.attrib[k]) for k in ("x", "y", "width", "height")) == (
        left,
        top,
        right - left,
        bottom - top,
    )


def test_rejected_text_does_not_knock_out_any_geometry():
    canvas = renderer.Canvas((160, 90))
    canvas.line([(0, 25), (159, 25)], (220, 220, 220, 180), 2)
    canvas.begin_annotations()
    before = canvas.finish().tobytes()
    assert not canvas.text((150, 20), "Cannot fit here", 14, (240, 235, 220, 220))
    assert canvas.finish().tobytes() == before and not canvas.text_clearances


def test_overlay_exports_composition_icc_without_photo_exif(values, tmp_path):
    source = tmp_path / "profiled.png"
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    with Image.open(values["input"]) as image:
        exif = Image.Exif()
        exif[270] = "Private photographic description"
        image.save(source, icc_profile=icc, exif=exif)
    result = render({**values, "input": source, "preserve_metadata": True})
    with (
        Image.open(result.output / "clean_base.png") as base,
        Image.open(result.output / "map_overlay.png") as overlay,
        Image.open(result.final) as final,
    ):
        assert base.info["icc_profile"] == overlay.info["icc_profile"] == final.info["icc_profile"] == icc
        assert not overlay.getexif()
        assert np.array_equal(np.asarray(Image.alpha_composite(base, overlay)), np.asarray(final))


def test_region_distribution_excludes_labels_and_counts_cleared_geometry(
    values, data_dir, tmp_path, monkeypatch
):
    captured = []
    original = renderer.ink_distribution

    def observe(geometry, allowed):
        captured.append(np.asarray(geometry).copy())
        return original(geometry, allowed)

    monkeypatch.setattr(renderer, "ink_distribution", observe)
    mask = tmp_path / "full-region.png"
    Image.new("L", (1000, 700), 255).save(mask)
    result = render(
        {
            **values,
            "geojson": data_dir / "san_francisco.geojson",
            "location": "San Francisco",
            "location_label": "San Francisco",
            "radius_km": 0.08,
            "map_mode": "urban",
            "region_mask": mask,
        }
    )
    art = json.loads((result.output / "provenance.json").read_text())["cartography"]
    assert len(captured) == 1 and captured[0].any()
    overlay = np.asarray(Image.open(result.output / "map_overlay.png"))
    for record in art["text_records"]:
        left, top, right, bottom = (round(v) for v in record["bounds"])
        assert not captured[0][top:bottom, left:right].any()
        assert overlay[top:bottom, left:right, 3].any()


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
