import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from .http import CachedHTTP, ProviderError
from .models import GeoData, Source

OSM_LICENSE = "ODbL-1.0"
OSM_ATTRIBUTION = "© OpenStreetMap contributors · openstreetmap.org/copyright"


class Provider(ABC):
    @abstractmethod
    def fetch(self, bounds: tuple[float, float, float, float]) -> GeoData:
        """Return WGS84 features with complete source metadata."""


class OfflineGeoJSON(Provider):
    def __init__(self, path: Path):
        self.path = path

    def fetch(self, bounds=None):
        raw = json.loads(self.path.read_text())
        if raw.get("type") != "FeatureCollection" or raw.get("crs"):
            raise ValueError("Expected RFC7946 WGS84 FeatureCollection without a custom CRS")
        return GeoData(
            sources=raw.get("sources", []), features=raw.get("features", []), location=raw.get("location")
        )


class NaturalEarth(OfflineGeoJSON):
    """Locally supplied Natural Earth extracts; intentionally no high-detail upscaling."""

    def fetch(self, bounds=None):
        data = super().fetch(bounds)
        for s in data.sources:
            if "natural earth" not in s.dataset.lower() or not s.min_span_km:
                raise ValueError("Natural Earth sources require dataset identity and min_span_km")
        return data


class Overpass(Provider):
    def __init__(self, http: CachedHTTP, url="https://overpass-api.de/api/interpreter"):
        self.http, self.url = http, url

    def fetch(self, bounds):
        west, south, east, north = bounds
        if east - west > 1 or north - south > 1:
            raise ProviderError("Overpass area too large; supply a regional offline extract")
        bbox = f"{south},{west},{north},{east}"
        query = f"""[out:json][timeout:25];(way["highway"]({bbox});way["waterway"]({bbox});
way["natural"="water"]({bbox});way["natural"="coastline"]({bbox});
way["boundary"="administrative"]({bbox});node["place"]({bbox}););out geom;"""
        result = self.http.json(self.url, data={"data": query}, interval=2)
        raw = result["body"]
        if raw.get("remark"):
            raise ProviderError("Overpass returned incomplete data: " + raw["remark"])
        stamp = datetime.fromtimestamp(result["retrieved_at"], timezone.utc)
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        source = Source(
            id="osm",
            dataset="OpenStreetMap",
            version=raw.get("osm3s", {}).get("timestamp_osm_base", stamp.isoformat()),
            url=self.url,
            license=OSM_LICENSE,
            attribution=OSM_ATTRIBUTION,
            retrieved_at=stamp,
            sha256=digest,
            uncertainty="Incomplete ways and relations are omitted; OSM coverage varies",
        )
        features = []
        for item in raw.get("elements", []):
            tags = item.get("tags", {})
            if item["type"] == "node":
                geometry = {"type": "Point", "coordinates": [item["lon"], item["lat"]]}
            else:
                coords = [[p["lon"], p["lat"]] for p in item.get("geometry", []) if "lon" in p]
                if len(coords) < 2:
                    continue
                is_area = tags.get("natural") == "water" and len(coords) > 3 and coords[0] == coords[-1]
                geometry = {
                    "type": "Polygon" if is_area else "LineString",
                    "coordinates": [coords] if is_area else coords,
                }
            kind = (
                "water"
                if tags.get("natural") == "water"
                else "coastline"
                if tags.get("natural") == "coastline"
                else "trail"
                if tags.get("highway") in ("path", "footway", "track")
                else "road"
                if "highway" in tags
                else "river"
                if "waterway" in tags
                else "boundary"
                if "boundary" in tags
                else "place"
            )
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        **tags,
                        "kind": kind,
                        "source_id": "osm",
                        "osm_id": f"{item['type']}/{item['id']}",
                        "source_url": f"https://www.openstreetmap.org/{item['type']}/{item['id']}",
                    },
                }
            )
        # Fail safely on invalid geometry rather than repair it into invented topology.
        valid = []
        warnings = []
        for f in features:
            try:
                GeoData(sources=[source], features=[f])
                valid.append(f)
            except ValueError:
                warnings.append(f"Omitted invalid OSM geometry: {f['properties']['osm_id']}")
        return GeoData(sources=[source], features=valid, warnings=warnings)


class ProviderChain(Provider):
    """Explicit ordered fallback for caller-selected, authorized providers."""

    def __init__(self, providers: list[Provider]):
        if not providers:
            raise ValueError("ProviderChain needs at least one provider")
        self.providers = providers

    def fetch(self, bounds):
        warnings = []
        for provider in self.providers:
            try:
                data = provider.fetch(bounds)
                if data.features:
                    data.warnings = warnings + data.warnings
                    return data
                warnings.append(f"{type(provider).__name__}: no geographic features")
            except ProviderError as exc:
                warnings.append(f"{type(provider).__name__}: {exc}")
        return GeoData(warnings=warnings + ["All configured providers unavailable or empty"])
