"""Analytical MVT fixtures test projection, not authentic geographic content."""

import json
import math

import httpx
import mapbox_vector_tile
import pytest
from shapely.geometry import shape

from camera_atlas.geography.http import ProviderError
from camera_atlas.geography.tiles import STYLE, OpenFreeMap, decode_tile, tile_lonlat, tile_plan


def encoded(layers=None):
    return mapbox_vector_tile.encode(
        layers
        or [
            {
                "name": "transportation",
                "features": [{"geometry": "LINESTRING(0 0,4096 4096)", "properties": {"class": "primary"}}],
            }
        ],
        default_options={"y_coord_down": True},
    )


def mock_transport(pbf=None, fail_at=None, template=None):
    seen = []

    def handle(request):
        seen.append(request)
        if str(request.url) == STYLE:
            return httpx.Response(
                200,
                json={
                    "sources": {
                        "openmaptiles": {"type": "vector", "url": "https://tiles.openfreemap.org/planet"}
                    }
                },
            )
        if request.url.path == "/planet":
            return httpx.Response(
                200,
                json={
                    "maxzoom": 14,
                    "version": "analytical-test",
                    "tiles": [template or "https://tiles.openfreemap.org/planet/test/{z}/{x}/{y}.pbf"],
                },
            )
        if fail_at and len([r for r in seen if r.url.path.endswith(".pbf")]) == fail_at:
            return httpx.Response(503)
        return httpx.Response(200, content=pbf if pbf is not None else encoded())

    return httpx.MockTransport(handle), seen


def test_tile_axes_are_north_down_and_east_right():
    data, omitted = decode_tile(encoded(), (2, 2, 1), "analytic", "https://example.org/analytical.pbf")
    assert omitted == 0 and len(data) == 1
    a, b = data[0]["geometry"]["coordinates"]
    assert a == pytest.approx((0, 66.51326044311186))
    assert b == pytest.approx((90, 0))
    assert a[0] < b[0] and a[1] > b[1]


def test_tile_buffer_is_clipped_without_false_water_frame():
    body = encoded(
        [
            {
                "name": "transportation",
                "features": [
                    {"geometry": "LINESTRING(-100 2048,4196 2048)", "properties": {"class": "primary"}}
                ],
            },
            {
                "name": "water",
                "features": [
                    {
                        "geometry": "POLYGON((0 0,4096 0,4096 2048,0 2048,0 0))",
                        "properties": {"class": "lake"},
                    }
                ],
            },
        ]
    )
    features, omitted = decode_tile(body, (2, 2, 1), "analytic", "https://example.org/analytical.pbf")
    assert omitted == 0
    roads = [shape(f["geometry"]) for f in features if f["properties"]["kind"] == "road"]
    water = [shape(f["geometry"]) for f in features if f["properties"]["kind"] == "water"]
    assert len(roads) == len(water) == 1
    assert roads[0].bounds[0] == pytest.approx(0)
    assert roads[0].bounds[2] == pytest.approx(90)
    assert water[0].bounds[1] == water[0].bounds[3]  # Only actual horizontal shore; no tile edges.
    assert water[0].geom_type == "LineString"


def test_entire_tile_of_water_has_no_invented_shoreline():
    body = encoded(
        [
            {
                "name": "water",
                "features": [
                    {
                        "geometry": "POLYGON((0 0,4096 0,4096 4096,0 4096,0 0))",
                        "properties": {"class": "ocean"},
                    }
                ],
            }
        ]
    )
    assert decode_tile(body, (2, 2, 1), "analytic", "https://example.org/tile")[0] == []


def test_water_subdivision_does_not_create_internal_shoreline():
    body = encoded(
        [
            {
                "name": "water",
                "features": [
                    {
                        "geometry": "POLYGON((0 0,2048 0,2048 4096,0 4096,0 0))",
                        "properties": {"class": "ocean"},
                    },
                    {
                        "geometry": "POLYGON((2048 0,4096 0,4096 4096,2048 4096,2048 0))",
                        "properties": {"class": "ocean"},
                    },
                ],
            }
        ]
    )
    assert decode_tile(body, (2, 2, 1), "analytic", "https://example.org/tile")[0] == []


def test_plan_covers_full_bounds_without_exceeding_budget():
    bounds = (139.0, 35.0, 140.0, 36.0)
    zoom, tiles, covered = tile_plan(bounds)
    assert 9 <= zoom < 14 and len(tiles) <= 16
    assert covered[0] <= bounds[0] and covered[1] <= bounds[1]
    assert covered[2] >= bounds[2] and covered[3] >= bounds[3]
    for z, x, y in tiles:
        assert z == zoom and 0 <= x < 2**z and 0 <= y < 2**z
    with pytest.raises(ProviderError, match="budget"):
        tile_plan((-90, -80, 90, 80))


@pytest.mark.parametrize("bounds", [(170, -5, -170, 5), (-5, 84, 5, 86), (0, 0, math.nan, 1)])
def test_invalid_polar_and_dateline_regions_rejected(bounds):
    with pytest.raises(ProviderError):
        tile_plan(bounds)


def test_all_tiles_and_provenance_present_then_offline_reuse(tmp_path):
    transport, seen = mock_transport()
    bounds = (-0.001, -0.001, 0.001, 0.001)
    with OpenFreeMap(tmp_path, transport=transport) as provider:
        data = provider.fetch(bounds)
    assert data.coverage["all_tiles_fetched"]
    assert data.coverage["geometry_complete"]
    assert data.coverage["tile_count"] == data.coverage["tiles_received"] == 4
    assert len(data.sources) == 4
    assert all(r.headers["User-Agent"].startswith("CameraAtlas/") for r in seen)
    assert all(
        f["properties"]["source_url"].startswith("https://tiles.openfreemap.org/") for f in data.features
    )
    assert all(s.sha256 and "test/" in s.version and s.retrieved_at for s in data.sources)
    assert json.loads(json.dumps(data.geojson()))["coverage"]["zoom"] == 14
    calls = len(seen)
    with OpenFreeMap(tmp_path, offline=True, transport=transport) as provider:
        cached = provider.fetch(bounds)
    assert len(seen) == calls
    assert cached.sources == data.sources


def test_missing_tile_never_returns_partial_coverage(tmp_path):
    transport, _ = mock_transport(fail_at=2)
    with OpenFreeMap(tmp_path, transport=transport) as provider:
        with pytest.raises(ProviderError, match="unavailable"):
            provider.fetch((-0.001, -0.001, 0.001, 0.001))


def test_tile_bytes_bounded_before_decoding(tmp_path):
    transport, _ = mock_transport(pbf=b"x" * (2 * 1024 * 1024 + 1))
    with OpenFreeMap(tmp_path, transport=transport) as provider:
        with pytest.raises(ProviderError, match="budget"):
            provider.fetch((139.76, 35.68, 139.77, 35.69))


def test_source_cannot_redirect_fetches_to_untrusted_host(tmp_path):
    transport, seen = mock_transport(template="https://private.example/{z}/{x}/{y}.pbf")
    with OpenFreeMap(tmp_path, transport=transport) as provider:
        with pytest.raises(ProviderError, match="host"):
            provider.fetch((139.76, 35.68, 139.77, 35.69))
    assert len(seen) == 2


@pytest.mark.network
def test_live_tokyo_station_tile_extent(tmp_path):
    # Explicit opt-in only. Actual OpenFreeMap geometry and its acquisition provenance.
    with OpenFreeMap(tmp_path) as provider:
        data = provider.fetch((139.763, 35.678, 139.771, 35.685))
    assert data.coverage["tile_count"] <= 16
    assert data.coverage["all_tiles_fetched"]
    assert any(f["properties"]["kind"] == "road" for f in data.features)
    assert all(s.url.startswith("https://tiles.openfreemap.org/planet/") for s in data.sources)
    west, south = tile_lonlat(0, 2**14, 14)
    assert west == -180 and south < -85
