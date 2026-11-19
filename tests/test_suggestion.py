"""Analytical colour/shape fixtures, not real photographs or geographic data."""

import numpy as np
from PIL import Image, ImageDraw

from camera_atlas.composition.suggestion import suggest_region


def scene():
    image = Image.new("RGB", (400, 300), (70, 145, 210))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 200, 399, 299), fill=(65, 48, 35))
    # Contrasting subject surrounded by background: must remain a hole.
    draw.rectangle((140, 50, 205, 170), fill=(185, 50, 45))
    # A thin branch at full resolution, partly lost in thumbnail sampling.
    draw.line((40, 5, 110, 170), fill=(35, 30, 20), width=2)
    return image


def test_suggests_connected_background_and_protects_subjects():
    image = scene()
    before = np.asarray(image).copy()
    result = suggest_region(image)
    mask = np.asarray(result.mask)
    assert result.mask.mode == "L" and result.mask.size == image.size
    assert set(np.unique(mask)) == {0, 255}
    assert (mask[10:180, 230:390] == 255).mean() > 0.95
    assert not mask[60:160, 150:195].any()
    assert not mask[220:].any()
    assert not mask[87:90, 75:78].any()
    assert result.requires_review is True
    assert 0 < result.confidence <= 0.75
    assert np.array_equal(before, np.asarray(image))
    assert "not semantic" in result.method


def test_sideways_orientation_is_preserved_and_side_region_found():
    image = scene().transpose(Image.Transpose.ROTATE_90)
    result = suggest_region(image)
    mask = np.asarray(result.mask)
    assert result.mask.size == (300, 400)
    assert (mask[10:150, 10:180] == 255).mean() > 0.9
    assert not mask[:, 220:].any()
    assert not mask[205:240, 65:150].any()
    assert result.requires_review


def test_flat_image_has_no_supported_background_boundary():
    result = suggest_region(Image.new("RGB", (400, 300), (100, 160, 220)))
    assert result.mask.getbbox() is None
    assert result.confidence == 0
    assert result.requires_review


def test_busy_checkerboard_has_no_fake_rectangle():
    yy, xx = np.indices((240, 320))
    values = (((yy // 4 + xx // 4) % 2) * 255).astype(np.uint8)
    image = Image.fromarray(np.repeat(values[:, :, None], 3, axis=2))
    result = suggest_region(image)
    assert result.mask.getbbox() is None
    assert result.requires_review


def test_transparent_pixels_are_excluded():
    image = scene().convert("RGBA")
    ImageDraw.Draw(image).rectangle((240, 10, 280, 180), fill=(70, 145, 210, 0))
    result = suggest_region(image)
    assert not np.asarray(result.mask)[10:180, 240:280].any()


def test_sky_parts_separated_by_wires_are_not_dropped():
    image = scene()
    ImageDraw.Draw(image).line((0, 100, 399, 100), fill=(20, 20, 20), width=3)
    mask = np.asarray(suggest_region(image).mask)
    assert (mask[20:80, 230:390] == 255).mean() > 0.95
    assert (mask[120:170, 230:390] == 255).mean() > 0.95
    assert not mask[99:102].any()


def test_small_photo_requests_manual_input():
    result = suggest_region(Image.new("RGB", (80, 90)))
    assert result.mask.size == (80, 90)
    assert result.mask.getbbox() is None
