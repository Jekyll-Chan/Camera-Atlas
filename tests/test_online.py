"""Offline workflow tests using recorded real OSM geometry and mocked transport.

Coverage declarations below are analytical test doubles. They are not evidence
that the small public OSM fixture covers an arbitrary requested map viewport.
"""

import base64
import io
import json
import math

import numpy as np
import pytest
from PIL import Image, ImageDraw

from camera_atlas.geography.http import ProviderError
from camera_atlas.geography.models import GeoData
from camera_atlas.geography.tiles import TileGeoData
from camera_atlas.online import OnlineWorkspace


def selection(box):
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode(), mask


@pytest.fixture
def online(tmp_path, monkeypatch, data_dir, photo):
    raw = json.loads((data_dir / "san_francisco.geojson").read_text())
    recorded = GeoData.model_validate({k: raw[k] for k in ("sources", "features", "location")})
    point = recorded.location
    calls = {"search": [], "tiles": [], "http_closed": 0, "tile_closed": 0}

    class GeocoderTransport:
        def __init__(self, *args, **kwargs):
            pass

        def json(self, url, **kwargs):
            calls["search"].append((url, kwargs))
            return {
                "retrieved_at": 1700000000,
                "body": {
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"name": point.name, "city": "San Francisco", "country": "USA"},
                            "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
                        }
                    ]
                },
            }

        def close(self):
            calls["http_closed"] += 1

    class TileProvider:
        empty = False

        def __init__(self, cache):
            self.cache = cache

        def fetch(self, bounds):
            calls["tiles"].append(bounds)
            data = recorded.model_copy(deep=True)
            return TileGeoData(
                sources=data.sources,
                features=[] if self.empty else data.features,
                coverage={
                    "provider": "analytical coverage test double",
                    "requested_bounds": list(bounds),
                    "all_tiles_fetched": True,
                    "geometry_complete": True,
                    "source_generalized": True,
                },
            )

        def close(self):
            calls["tile_closed"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr("camera_atlas.online.CachedHTTP", GeocoderTransport)
    monkeypatch.setattr("camera_atlas.geography.tiles.OpenFreeMap", TileProvider)
    workspace = OnlineWorkspace(tmp_path / "session", data_dir, tmp_path / "shared-cache")
    uploaded = workspace.add_photo(photo.read_bytes())
    candidate = workspace.search_places("San Francisco")[0]
    return workspace, uploaded, candidate, calls, point, TileProvider


def test_search_returns_server_candidate_and_retains_locality_source(online, data_dir, tmp_path):
    workspace, _, candidate, calls, point, _ = online
    assert candidate["id"] in workspace.catalogue
    assert candidate["id"] != "san-francisco"
    place = workspace.catalogue[candidate["id"]]
    assert place["location"]["lat"] == point.lat
    assert place["location"]["lon"] == point.lon
    assert place["location"]["accuracy"] == "locality"
    assert place["location"]["source_id"] == "photon"
    assert "not camera GPS" in place["location"]["coordinate_source"]
    assert place["geocoder_source"]["sha256"]
    assert calls["http_closed"] == 1
    assert calls["search"][0][1]["params"]["limit"] == 5
    assert calls["search"][0][1]["interval"] == 2
    restarted = OnlineWorkspace(workspace.root, data_dir, tmp_path / "shared-cache")
    assert restarted.catalogue[candidate["id"]]["location"] == place["location"]


@pytest.mark.parametrize("changes", [{"confirmed": False}, {"place_id": "arbitrary-client-place"}])
def test_confirmation_and_server_candidate_are_required(online, changes):
    workspace, photo, candidate, calls, _, _ = online
    encoded, _ = selection((0, 0, 999, 199))
    request = {"photo_id": photo["id"], "place_id": candidate["id"], "confirmed": True, "mask": encoded}
    with pytest.raises(ValueError, match="confirm"):
        workspace.create_render({**request, **changes})
    assert not calls["tiles"]
    assert not workspace.results


def test_long_selections_expand_geography_and_record_the_actual_window(online):
    workspace, photo, candidate, calls, point, _ = online
    for box in ((0, 0, 999, 199), (600, 0, 799, 699)):
        encoded, mask = selection(box)
        # Browser coordinates are not an authority and must never move the map.
        result = workspace.create_render(
            {
                "photo_id": photo["id"],
                "place_id": candidate["id"],
                "confirmed": True,
                "mask": encoded,
                "lat": 0,
                "lon": 0,
                "opacity": 0.7,
            }
        )
        output = workspace.results[result["id"]]
        provenance = json.loads((output / "provenance.json").read_text())
        assert provenance["location"]["lat"] == point.lat
        assert provenance["location"]["lon"] == point.lon
        assert provenance["location"]["accuracy"] == "locality"
        assert provenance["location"]["source_id"] == "photon"
        assert "photon" in {source["id"] for source in provenance["sources"]}
        assert provenance["coverage"]["requested_bounds"] == list(calls["tiles"][-1])
        assert provenance["window_plan"]["bounds"] == list(calls["tiles"][-1])
        width, height = box[2] - box[0] + 1, box[3] - box[1] + 1
        assert provenance["window_plan"]["rect_px"] == [box[0], box[1], width, height]
        west, south, east, north = calls["tiles"][-1]
        ground_aspect = (east - west) * math.cos(math.radians(point.lat)) / (north - south)
        assert ground_aspect == pytest.approx(width / height, rel=0.01)
        with Image.open(output / "final.png") as final, Image.open(workspace.photos[photo["id"]]) as base:
            protected = np.asarray(mask) == 0
            assert np.array_equal(np.asarray(final)[protected], np.asarray(base)[protected])
    assert calls["tiles"][0] != calls["tiles"][1]


def test_no_geometry_is_not_delivered_as_success(online):
    workspace, photo, candidate, _, _, provider = online
    provider.empty = True
    encoded, _ = selection((0, 0, 999, 199))
    with pytest.raises(ProviderError, match="No supported map geometry"):
        workspace.create_render(
            {"photo_id": photo["id"], "place_id": candidate["id"], "confirmed": True, "mask": encoded}
        )
    assert not workspace.results


@pytest.mark.parametrize(
    "options",
    [
        {"radius_km": 0},
        {"radius_km": -1},
        {"radius_km": 101},
        {"radius_km": float("nan")},
        {"radius_km": float("inf")},
        {"radius_km": True},
        {"radius_km": "2"},
        {"map_mode": "invented"},
        {"map_mode": None},
        {"map_mode": ["urban"]},
        {"location_label": "  "},
        {"location_label": "unreadable\nlabel"},
        {"location_label": "x" * 81},
        {"location_label": None},
    ],
)
def test_invalid_map_options_fail_before_fetching_or_rendering(online, options):
    workspace, photo, candidate, calls, _, _ = online
    encoded, _ = selection((0, 0, 999, 199))
    with pytest.raises(ValueError, match="radius|mode|label"):
        workspace.create_render(
            {
                "photo_id": photo["id"],
                "place_id": candidate["id"],
                "confirmed": True,
                "mask": encoded,
                **options,
            }
        )
    assert not calls["tiles"]
    assert not workspace.results


def test_extent_revision_refetches_real_bounds_without_changing_place_defaults(online, data_dir):
    workspace, photo, candidate, calls, point, _ = online
    encoded, _ = selection((0, 0, 999, 199))
    original_place = dict(workspace.catalogue[candidate["id"]])
    for radius in (0.2, 0.8):
        # JSON round-trip and a new workspace simulate a persisted request being
        # resumed. The underlying queue separately tests durable retry behavior.
        request = json.loads(
            json.dumps(
                {
                    "photo_id": photo["id"],
                    "place_id": candidate["id"],
                    "confirmed": True,
                    "mask": encoded,
                    "radius_km": radius,
                    "map_mode": "urban",
                }
            )
        )
        restarted = OnlineWorkspace(workspace.root, data_dir, workspace.geography_cache)
        result = restarted.create_render(request)
        output = restarted.results[result["id"]]
        provenance = json.loads((output / "provenance.json").read_text())
        metadata = json.loads((output / "metadata.json").read_text())
        assert provenance["window_plan"]["radius_km"] == radius
        assert provenance["window_plan"]["requested_map_mode"] == "urban"
        assert metadata["map_mode"] == "urban"
        assert provenance["location"]["lat"] == point.lat
        assert provenance["location"]["lon"] == point.lon
        assert restarted.catalogue[candidate["id"]] == original_place
    small, large = calls["tiles"]
    assert large[0] < small[0] < small[2] < large[2]
    assert large[1] < small[1] < small[3] < large[3]
    assert (large[2] - large[0]) / (small[2] - small[0]) == pytest.approx(4, rel=0.01)
    assert (large[3] - large[1]) / (small[3] - small[1]) == pytest.approx(4, rel=0.01)
