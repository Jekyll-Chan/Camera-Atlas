"""Bounded OpenFreeMap vector extracts, with explicit tile coverage.

The source is a zoom-generalized cartographic dataset, not raw OSM or a DEM.
https://openfreemap.org/ permits small extracts with an identifying User-Agent.
"""

import hashlib
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np
from pydantic import Field
from shapely import transform
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from .http import ProviderError
from .models import GeoData, Source

STYLE = "https://tiles.openfreemap.org/styles/liberty"
HOST = "tiles.openfreemap.org"
MAX_TILES = 16
MAX_BYTES = 8 * 1024 * 1024
MAX_FEATURES = 25000
ATTRIBUTION = "© OpenMapTiles · © OpenStreetMap contributors · openstreetmap.org/copyright"
LAYERS = {"transportation", "water", "waterway", "boundary", "place", "water_name"}


class TileGeoData(GeoData):
    coverage: dict = Field(default_factory=dict)

    def geojson(self):
        return {**super().geojson(), "coverage": self.coverage}


def validate_bounds(bounds):
    if len(bounds) != 4 or not all(math.isfinite(float(v)) for v in bounds):
        raise ProviderError("Invalid geographic bounds")
    west, south, east, north = map(float, bounds)
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85) or east - west > 180:
        raise ProviderError("Polar or antimeridian regions need a dedicated dataset")
    return west, south, east, north


def tile_position(lon, lat, zoom):
    n = 2**zoom
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def tile_lonlat(x, y, zoom):
    n = 2**zoom
    return x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def tile_plan(bounds, max_zoom=14, min_zoom=9, max_tiles=MAX_TILES):
    west, south, east, north = validate_bounds(bounds)
    if not 9 <= min_zoom <= max_zoom <= 14 or not 1 <= max_tiles <= MAX_TILES:
        raise ProviderError("Unsupported tile budget or zoom")
    for zoom in range(max_zoom, min_zoom - 1, -1):
        left, top = tile_position(west, north, zoom)
        right, bottom = tile_position(east, south, zoom)
        n = 2**zoom
        x0, y0 = max(0, math.floor(left)), max(0, math.floor(top))
        x1, y1 = min(n - 1, math.floor(right)), min(n - 1, math.floor(bottom))
        if (x1 - x0 + 1) * (y1 - y0 + 1) <= max_tiles:
            tiles = [(zoom, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
            w, s = tile_lonlat(x0, y1 + 1, zoom)
            e, no = tile_lonlat(x1 + 1, y0, zoom)
            return zoom, tiles, (w, s, e, no)
    raise ProviderError("This region exceeds the free preview's tile budget. Choose a smaller region.")


def safe_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != HOST
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ProviderError("Map metadata referenced an unsupported host")
    return url


def line_parts(geometry):
    if geometry.geom_type in {"Point", "LineString"}:
        return [geometry] if not geometry.is_empty else []
    if hasattr(geometry, "geoms"):
        return [part for g in geometry.geoms for part in line_parts(g)]
    return []


def decode_tile(body, tile, source_id, url):
    """Decode screen-y-down MVT and retain only real linework, never tile frames."""
    import mapbox_vector_tile

    zoom, tx, ty = tile
    try:
        layers = mapbox_vector_tile.decode(body, default_options={"y_coord_down": True})
    except Exception as exc:
        raise ProviderError("Could not decode a complete map tile") from exc
    features, omitted = [], 0
    for layer_name, layer in layers.items():
        if layer_name not in LAYERS:
            continue
        extent = layer.get("extent", 4096)
        if not isinstance(extent, int) or not 1 <= extent <= 65536:
            raise ProviderError("Invalid map tile coordinate extent")
        frame = box(0, 0, extent, extent)
        selected_features = layer.get("features", [])
        if layer_name == "water":
            # OpenMapTiles can subdivide water polygons inside a single tile.
            # Union first so those artificial internal edges cannot become shores.
            polygons = []
            for f in selected_features:
                polygon = shape(f["geometry"])
                if not polygon.is_valid or polygon.is_empty:
                    raise ProviderError("Invalid water geometry in map tile")
                if polygon.geom_type not in {"Polygon", "MultiPolygon"}:
                    raise ProviderError("Unsupported water geometry in map tile")
                polygons.append(polygon)
            selected_features = (
                [
                    {
                        "geometry": mapping(unary_union(polygons)),
                        "properties": {
                            "class": "ocean"
                            if any(f.get("properties", {}).get("class") == "ocean" for f in selected_features)
                            else "lake"
                        },
                        "id": "merged-water",
                    }
                ]
                if polygons
                else []
            )
        for index, feature in enumerate(selected_features):
            properties = feature.get("properties", {})
            kind = {
                "transportation": "trail" if properties.get("class") in {"path", "track"} else "road",
                "water": "coastline" if properties.get("class") == "ocean" else "water",
                "waterway": "river",
                "boundary": "boundary",
                "place": "place",
                "water_name": "place",
            }[layer_name]
            try:
                geometry = shape(feature["geometry"])
                if not geometry.is_valid or geometry.is_empty:
                    omitted += 1
                    continue
                if geometry.geom_type in {"Polygon", "MultiPolygon"}:
                    if layer_name != "water":
                        # Area roads and administrative polygons are not linework.
                        continue
                    # Get the original boundary BEFORE clipping; clipping a polygon
                    # first would invent straight shores along every tile border.
                    geometry = geometry.boundary.intersection(frame)
                    geometry = geometry.difference(frame.boundary.buffer(1e-7))
                else:
                    geometry = geometry.intersection(frame)
                for part in line_parts(geometry):
                    if part.geom_type == "Point" and layer_name not in {"place", "water_name"}:
                        continue

                    def project(xy):
                        n = 2**zoom
                        x, y = tx + xy[:, 0] / extent, ty + xy[:, 1] / extent
                        return np.column_stack(
                            (x / n * 360 - 180, np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * y / n)))))
                        )

                    projected = transform(part, project)
                    if projected.is_empty or not projected.is_valid:
                        omitted += 1
                        continue
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": mapping(projected),
                            "properties": {
                                **{
                                    k: v
                                    for k, v in properties.items()
                                    if k
                                    in {
                                        "name",
                                        "name:en",
                                        "name_en",
                                        "class",
                                        "subclass",
                                        "admin_level",
                                        "ref",
                                        "disputed",
                                        "claimed_by",
                                        "maritime",
                                        "brunnel",
                                        "intermittent",
                                    }
                                },
                                "kind": kind,
                                "source_id": source_id,
                                "source_url": url,
                                "tile_layer": layer_name,
                                "tile_feature_id": feature.get("id", index),
                                "name:en": properties.get("name:en", properties.get("name_en", "")),
                            },
                        }
                    )
            except (ValueError, TypeError, KeyError):
                omitted += 1
            if len(features) > MAX_FEATURES:
                raise ProviderError("Map geometry exceeds the preview budget")
    return features, omitted


class OpenFreeMap:
    def __init__(self, cache: Path, offline=False, transport=None):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.database = self.cache / "openfreemap.sqlite3"
        self.offline = offline
        self.client = httpx.Client(
            timeout=httpx.Timeout(20),
            transport=transport,
            follow_redirects=False,
            headers={"User-Agent": "CameraAtlas/0.2 (+https://github.com/Jekyll-Chan/Camera-Atlas)"},
        )
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS tiles (url TEXT PRIMARY KEY, body BLOB, stamp REAL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def read(self, url, limit, metadata=False):
        safe_url(url)
        with self.connect() as db:
            row = db.execute("SELECT body, stamp FROM tiles WHERE url=?", (url,)).fetchone()
        if row and (not metadata or self.offline or row[1] > time.time() - 3600):
            if len(row[0]) > limit:
                raise ProviderError("Map data exceeds the download budget")
            return row
        if self.offline:
            raise ProviderError("Offline map tile cache miss")
        destination = url
        try:
            for _ in range(4):
                with self.client.stream("GET", safe_url(destination)) as response:
                    if response.is_redirect:
                        destination = safe_url(urljoin(destination, response.headers.get("location", "")))
                        continue
                    response.raise_for_status()
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        if len(data) + len(chunk) > limit:
                            raise ProviderError("Map data exceeds the download budget")
                        data.extend(chunk)
                    body, stamp = bytes(data), time.time()
                    with self.connect() as db:
                        db.execute("INSERT OR REPLACE INTO tiles VALUES (?,?,?)", (url, body, stamp))
                        # Bounded local cache; URLs contain the immutable data version.
                        total = db.execute("SELECT COALESCE(SUM(length(body)),0) FROM tiles").fetchone()[0]
                        while total > 64 * 1024 * 1024:
                            oldest = db.execute(
                                "SELECT url, length(body) FROM tiles ORDER BY stamp LIMIT 1"
                            ).fetchone()
                            db.execute("DELETE FROM tiles WHERE url=?", (oldest[0],))
                            total -= oldest[1]
                    return body, stamp
        except httpx.HTTPError as exc:
            raise ProviderError("Map tiles are temporarily unavailable. Please retry later.") from exc
        raise ProviderError("Too many map metadata redirects")

    def metadata(self, url):
        body, _ = self.read(url, 1024 * 1024, metadata=True)
        self.metadata_bytes += len(body)
        try:
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError("not an object")
            return value
        except ValueError as exc:
            raise ProviderError("Invalid map metadata") from exc

    def fetch(self, bounds):
        bounds = validate_bounds(bounds)
        self.metadata_bytes = 0
        style = self.metadata(STYLE)
        source = style.get("sources", {}).get("openmaptiles", {})
        if source.get("type") != "vector" or not source.get("url"):
            raise ProviderError("The map style has no supported vector source")
        tilejson = self.metadata(safe_url(source["url"]))
        templates = tilejson.get("tiles", [])
        if not templates or not isinstance(templates[0], str):
            raise ProviderError("The map source has no tile template")
        template = safe_url(templates[0])
        if not all("{" + key + "}" in template for key in ("z", "x", "y")):
            raise ProviderError("Unsupported tile addressing")
        if tilejson.get("scheme", "xyz") != "xyz":
            raise ProviderError("Unsupported tile coordinate convention")
        zoom, tiles, tile_bounds = tile_plan(bounds, min(14, int(tilejson.get("maxzoom", 14))))
        sources, features, warnings = [], [], []
        used, omitted = self.metadata_bytes, 0
        for tile in tiles:
            url = template.format(z=tile[0], x=tile[1], y=tile[2])
            body, stamp = self.read(url, min(2 * 1024 * 1024, MAX_BYTES - used))
            used += len(body)
            ident = f"ofm-{tile[0]}-{tile[1]}-{tile[2]}"
            sources.append(
                Source(
                    id=ident,
                    dataset="OpenFreeMap / OpenMapTiles / OpenStreetMap",
                    version=template + f"; schema={tilejson.get('version', 'unspecified')}",
                    url=url,
                    license="ODbL-1.0 (map data); CC-BY-4.0 (OpenMapTiles schema)",
                    attribution=ATTRIBUTION,
                    retrieved_at=datetime.fromtimestamp(stamp, timezone.utc),
                    sha256=hashlib.sha256(body).hexdigest(),
                    uncertainty=f"Zoom {zoom} generalized vector tiles. Not raw OSM or elevation contours.",
                )
            )
            decoded, invalid = decode_tile(body, tile, ident, url)
            features.extend(decoded)
            omitted += invalid
            if len(features) > MAX_FEATURES:
                raise ProviderError("Map geometry exceeds the preview budget")
        if omitted:
            # No partial success: the caller must not call geometry_complete=True
            # after invalid selected-layer shapes were silently dropped.
            raise ProviderError("Map data contains invalid geometry; no complete overlay can be produced")
        warnings.append(
            "Map tiles are generalized at their source zoom; missing small features are not invented."
        )
        if zoom < 14:
            warnings.append(
                f"Map detail reduced to zoom {zoom} to cover the full region within the tile budget."
            )
        return TileGeoData(
            sources=sources,
            features=features,
            warnings=warnings,
            coverage={
                "provider": "OpenFreeMap",
                "requested_bounds": bounds,
                "tile_bounds": tile_bounds,
                "zoom": zoom,
                "tile_count": len(tiles),
                "tiles_received": len(tiles),
                "all_tiles_fetched": True,
                "geometry_complete": True,
                "missing_tiles": [],
                "source_generalized": True,
                "bytes": used,
                "layers": sorted(LAYERS),
                "meaning": "All required tiles decoded for selected layers; not completeness of real-world OSM.",
                "tile_urls": [s.url for s in sources],
            },
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
