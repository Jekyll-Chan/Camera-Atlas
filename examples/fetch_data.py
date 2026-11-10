"""Explicitly refresh public example inputs, retaining exact acquisition provenance.

Not used by CI. Network access is deliberate; public service policies apply.
"""

import gzip
import hashlib
import json
from pathlib import Path

import httpx

from camera_atlas.geography.http import CachedHTTP
from camera_atlas.geography.models import Location, now
from camera_atlas.geography.providers import Overpass

DATA = Path(__file__).resolve().parent / "data"


def refresh():
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    DATA.mkdir(exist_ok=True)
    cache = DATA.parent / ".download-cache"
    cache.mkdir(exist_ok=True)
    stamp = now()

    def save(name, obj):
        (DATA / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False))

    def get(url):
        response = httpx.get(
            url,
            timeout=90,
            follow_redirects=True,
            headers={"User-Agent": "CameraAtlas/0.1 educational example preparation"},
        )
        response.raise_for_status()
        return response.content

    ne = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_lakes_europe.geojson"
    raw = get(ne)
    features = []
    for f in json.loads(raw)["features"]:
        if "vierwald" in str(f["properties"].get("name", "")).lower():
            features.append(
                {
                    "type": "Feature",
                    "geometry": f["geometry"],
                    "properties": {
                        "kind": "water",
                        "name": f["properties"]["name"],
                        "name:en": f["properties"]["name_en"],
                        "source_id": "ne-lakes",
                        "ne_id": f["properties"]["ne_id"],
                    },
                }
            )
    if len(features) != 1:
        raise ValueError("Upstream lake identity changed; review before replacing fixtures")
    version = (
        get(
            "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/10m_physical/ne_10m_lakes_europe.VERSION.txt"
        )
        .decode()
        .strip()
    )
    source = {
        "id": "ne-lakes",
        "dataset": "Natural Earth 1:10m lakes Europe",
        "version": version,
        "url": ne,
        "license": "Public domain",
        "attribution": "Made with Natural Earth",
        "retrieved_at": stamp,
        "min_span_km": 60,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "uncertainty": "Generalized overview; unsuitable for shoreline navigation",
    }
    save(
        "lucerne.geojson",
        {
            "type": "FeatureCollection",
            "sources": [source],
            "features": features,
            "location": {
                "name": "Lake Lucerne",
                "lat": 46.98,
                "lon": 8.42,
                "accuracy": "locality",
                "coordinate_source": "Declared lake region center, never camera GPS",
                "source_id": "ne-lakes",
            },
        },
    )
    dem_url = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/N46/N46E008.hgt.gz"
    hgt = cache / "N46E008.hgt"
    hgt.write_bytes(gzip.decompress(get(dem_url)))
    with rasterio.open(hgt) as src:
        win = from_bounds(8.45, 46.80, 8.75, 46.99, src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, out_shape=(190, 300), resampling=Resampling.nearest)
        transform = src.window_transform(win) @ rasterio.Affine.scale(win.width / 300, win.height / 190)
        with rasterio.open(
            DATA / "alps_dem.tif",
            "w",
            driver="GTiff",
            width=300,
            height=190,
            count=1,
            dtype=arr.dtype,
            crs=src.crs,
            transform=transform,
            nodata=src.nodata,
            compress="deflate",
        ) as dst:
            dst.write(arr, 1)
    save(
        "alps_dem.source.json",
        {
            "id": "terrain",
            "dataset": "Mapzen Terrain Tiles / Skadi N46E008",
            "version": "download snapshot " + stamp,
            "url": dem_url,
            "license": "Source-dependent: https://github.com/tilezen/joerd/blob/master/docs/attribution.md",
            "attribution": "Terrain: EU-DEM / Copernicus; USGS; Mapzen",
            "retrieved_at": stamp,
            "resolution_m": 120,
            "units": "m",
            "sha256": hashlib.sha256((DATA / "alps_dem.tif").read_bytes()).hexdigest(),
            "uncertainty": "Nearest-neighbor overview subset; mixed terrain sources; vertical datum not transformed",
        },
    )
    (DATA / "TERRAIN-ATTRIBUTION.md").write_bytes(
        get("https://raw.githubusercontent.com/tilezen/joerd/master/docs/attribution.md")
    )
    http = CachedHTTP(cache)
    try:
        data = Overpass(http).fetch((-122.410, 37.793, -122.403, 37.798))
    finally:
        http.close()
    data.location = Location(
        name="San Francisco",
        lat=37.7955,
        lon=-122.4065,
        accuracy="locality",
        coordinate_source="Declared map region, never astronaut camera GPS",
        source_id="osm",
    )
    save("san_francisco.geojson", data.geojson())
    photos = []
    for name, nasa_id in (("lake", "sl3-121-2438"), ("city", "iss022e050559")):
        # Retrieve catalog metadata, not an inferred photo attribution.
        catalog = json.loads(
            get("https://images-api.nasa.gov/search?nasa_id=" + nasa_id + "&media_type=image")
        )
        item = catalog["collection"]["items"][0]
        url = next(link["href"] for link in item["links"] if link.get("render") == "image")
        photo = get(url)
        (DATA / (name + "_photo.jpg")).write_bytes(photo)
        photos.append(
            {
                "file": name + "_photo.jpg",
                "catalog": item["data"][0],
                "url": url,
                "source_page": "https://images.nasa.gov/details/" + nasa_id,
                "usage_guidelines": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                "use": "Factual educational example; no endorsement",
                "sha256": hashlib.sha256(photo).hexdigest(),
            }
        )
    save("photos.sources.json", photos)
    print("Refreshed real data. Review upstream changes and licenses, rerun tests, then update examples.")


if __name__ == "__main__":
    refresh()
