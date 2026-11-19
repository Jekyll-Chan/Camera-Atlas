"""Metadata-only classification tests; these inputs are not geographic geometry."""

import pytest

from camera_atlas.cartography.design import KINDS, select_mode


def feature_kinds(*kinds):
    return [{"properties": {"kind": kind}} for kind in kinds]


def test_urban_pond_does_not_suppress_street_context():
    features = feature_kinds("road", "road", "water", "place")
    mode = select_mode(features, "auto")
    assert mode == "urban"
    assert {"road", "water"} <= KINDS[mode]


@pytest.mark.parametrize("subject", ["lake", "coast"])
def test_inspected_water_scene_overrides_generic_street_preference(subject):
    assert select_mode(feature_kinds("water", "road"), "auto", subject) == "coastline"


def test_explicit_mode_and_actual_terrain_remain_authoritative():
    assert select_mode(feature_kinds("water", "road"), "coastline") == "coastline"
    assert select_mode(feature_kinds("contour", "road"), "auto") == "topographic"
    assert select_mode(feature_kinds("water", "place"), "auto") == "coastline"
