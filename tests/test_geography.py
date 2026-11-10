import json

import httpx
import numpy as np
import pytest
from pydantic import ValidationError
from pyproj import Geod
from shapely.geometry import shape

from camera_atlas import RenderConfig
from camera_atlas.geography.dem import contours
from camera_atlas.geography.http import CachedHTTP, ProviderError
from camera_atlas.geography.location import geocode, resolve
from camera_atlas.geography.models import GeoData
from camera_atlas.geography.projection import MapProjection
from camera_atlas.geography.providers import NaturalEarth, OfflineGeoJSON, Overpass


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181), (float("nan"), 1)])
def test_invalid_coordinates(values, lat, lon):
    with pytest.raises(ValidationError):
        RenderConfig(**{**values, "lat": lat, "lon": lon})


def test_incomplete_coordinate(values):
    with pytest.raises(ValidationError):
        RenderConfig(**{**values, "lat": 1})


def test_real_lake_data(data_dir):
    d = NaturalEarth(data_dir / "lucerne.geojson").fetch()
    f = d.features[0]
    g = shape(f["geometry"])
    assert f["properties"]["name:en"] == "Lucerne"
    assert f["properties"]["ne_id"]
    assert 8.28 < g.bounds[0] < 8.30 and 47.07 < g.bounds[3] < 47.08
    assert d.sources[0].version == "5.0.0"
    assert "natural-earth-vector" in d.sources[0].url
    assert d.sources[0].min_span_km == 60


def test_no_untraced_geometry(data_dir):
    d = json.loads((data_dir / "lucerne.geojson").read_text())
    d["features"][0]["properties"].pop("source_id")
    with pytest.raises(ValueError):
        GeoData(sources=d["sources"], features=d["features"])


def test_invalid_geometry(data_dir):
    d = json.loads((data_dir / "lucerne.geojson").read_text())
    d["features"][0]["geometry"] = {"type": "Point", "coordinates": [500, 95]}
    with pytest.raises(ValueError):
        GeoData(sources=d["sources"], features=d["features"])


def test_projection_roundtrip():
    p = MapProjection(46.98, 8.42, 45)
    x, y = p.forward.transform(8.5, 47.0)
    lon, lat = p.inverse.transform(x, y)
    assert abs(lon - 8.5) < 1e-9 and abs(lat - 47) < 1e-9
    assert abs(p.forward.transform(8.42, 46.98)[0]) < 1e-8
    assert p.bounds_wgs84()[0] < 8.42 < p.bounds_wgs84()[2]


def test_projection_antimeridian():
    with pytest.raises(ValueError, match="Antimeridian"):
        MapProjection(0, 179.99, 50).bounds_wgs84()


def test_projection_polar():
    with pytest.raises(ValueError, match="Polar"):
        MapProjection(89, 0, 10)


def test_exact_overrides_exif(values, data_dir, tmp_path):
    d = OfflineGeoJSON(data_dir / "lucerne.geojson").fetch()
    h = CachedHTTP(tmp_path / "cache", offline=True)
    try:
        c = RenderConfig(**{**values, "lat": 40, "lon": 80})
        loc, warnings = resolve(c, {"lat": 45, "lon": 85}, d, h)
        assert loc.accuracy == "exact_gps" and loc.lat == 40
        assert loc.conflicts
    finally:
        h.close()


def test_locality_not_camera(values, data_dir, tmp_path):
    d = OfflineGeoJSON(data_dir / "lucerne.geojson").fetch()
    h = CachedHTTP(tmp_path / "cache", offline=True)
    try:
        loc, _ = resolve(RenderConfig(**values), None, d, h)
        assert loc.accuracy == "locality"
        loc, _ = resolve(
            RenderConfig(**{**values, "lat": 46.98, "lon": 8.42, "confirmed_region": True}), None, d, h
        )
        assert loc.accuracy == "regional"
    finally:
        h.close()


def test_ambiguous_place(tmp_path):
    items = [
        {"display_name": "Canyon A", "lat": "1", "lon": "2"},
        {"display_name": "Canyon B", "lat": "3", "lon": "4"},
    ]
    h = CachedHTTP(tmp_path, transport=httpx.MockTransport(lambda req: httpx.Response(200, json=items)))
    try:
        loc, _ = geocode("Tianshan Canyon", h, "https://geocoder.example", False)
        assert loc.accuracy == "unresolved" and loc.lat is None and len(loc.candidates) == 2
    finally:
        h.close()


def test_public_nominatim_explicit_acceptance(tmp_path):
    h = CachedHTTP(tmp_path, offline=True)
    try:
        with pytest.raises(ProviderError, match="policy"):
            geocode("lake", h, "https://nominatim.openstreetmap.org")
    finally:
        h.close()


def test_cache_and_offline(tmp_path):
    calls = []

    def handle(req):
        calls.append(req)
        return httpx.Response(200, json={"answer": 1})

    h = CachedHTTP(tmp_path, transport=httpx.MockTransport(handle))
    first = h.json("https://test.example/a")
    second = h.json("https://test.example/a")
    h.close()
    assert first == second and len(calls) == 1
    h = CachedHTTP(
        tmp_path,
        offline=True,
        transport=httpx.MockTransport(lambda req: pytest.fail("Network in offline mode")),
    )
    try:
        assert h.json("https://test.example/a") == first
        with pytest.raises(ProviderError, match="Offline"):
            h.json("https://test.example/missing")
    finally:
        h.close()


def test_http_retries_bounded(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("camera_atlas.geography.http.time.sleep", lambda seconds: None)

    def handle(req):
        calls.append(req)
        return httpx.Response(503)

    h = CachedHTTP(tmp_path, transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(ProviderError):
            h.json("https://test.example", interval=0)
        assert len(calls) == 3
    finally:
        h.close()


def test_overpass_incomplete_rejected(tmp_path):
    h = CachedHTTP(
        tmp_path, transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"remark": "timeout"}))
    )
    try:
        with pytest.raises(ProviderError, match="incomplete"):
            Overpass(h).fetch((8, 46, 8.1, 46.1))
    finally:
        h.close()


def test_real_dem_contours(data_dir):
    d = contours(data_dir / "alps_dem.tif", data_dir / "alps_dem.source.json", 200)
    assert len(d.features) > 20
    assert all(f["properties"]["elevation_m"] % 200 == 0 for f in d.features)
    assert all(8.44 <= shape(f["geometry"]).bounds[0] <= 8.76 for f in d.features)
    # Geographic data provenance is a real downloaded raster, never an analytical surface.
    assert "skadi/N46/N46E008" in d.sources[0].url
    assert d.sources[0].sha256


def test_contour_linear_surface_numerics(tmp_path):
    # Analytical plane ONLY tests the contour algorithm. It is not an authenticity fixture.
    import rasterio
    from rasterio.transform import from_origin

    raster = tmp_path / "analytical.tif"
    source = tmp_path / "source.json"
    z = np.tile(np.arange(8, dtype="float32"), (8, 1)) * 100
    with rasterio.open(
        raster,
        "w",
        driver="GTiff",
        width=8,
        height=8,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(8, 47, 0.01, 0.01),
    ) as out:
        out.write(z, 1)
    source.write_text(
        json.dumps(
            {
                "id": "analytical",
                "dataset": "Analytical algorithm test ONLY",
                "version": "1",
                "url": "https://example.org/analytical-test",
                "license": "CC0",
                "attribution": "Analytical numerical test, not real terrain",
                "units": "m",
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        )
    )
    d = contours(raster, source, 100)
    line = next(f for f in d.features if f["properties"]["elevation_m"] == 300)
    assert np.allclose(np.array(line["geometry"]["coordinates"])[:, 0], 8.035)


def test_dem_checksum_failure(data_dir, tmp_path):
    source = json.loads((data_dir / "alps_dem.source.json").read_text())
    source["sha256"] = "0" * 64
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="SHA256"):
        contours(data_dir / "alps_dem.tif", p, 100)


def test_scale_geodesic_not_artistic(values):
    from camera_atlas import render

    r = render({**values, "scale": True, "svg": True})
    p = json.loads((r.output / "provenance.json").read_text())
    scale = p["cartography"]["scale"]
    a, b = scale["endpoints_wgs84"]
    distance = Geod(ellps="WGS84").inv(*a, *b)[2]
    assert abs(distance - scale["geodesic_m"]) < 1e-5
    assert abs(distance - scale["projected_m"]) / distance < 0.001


def test_real_city_provider_snapshot(data_dir, tmp_path):
    data = OfflineGeoJSON(data_dir / "san_francisco.geojson").fetch()
    assert len(data.features) == 580
    assert data.sources[0].license == "ODbL-1.0"
    assert all(f["properties"]["osm_id"].startswith("way/") for f in data.features)
    assert any(f["properties"].get("name") == "Grant Avenue" for f in data.features)
    assert any(f["properties"]["kind"] == "road" for f in data.features)


def test_source_missing_resolution_refused(data_dir):
    raw = json.loads((data_dir / "lucerne.geojson").read_text())
    raw["sources"][0].pop("min_span_km")
    with pytest.raises(ValueError, match="min_span_km"):
        GeoData(sources=raw["sources"], features=raw["features"])
