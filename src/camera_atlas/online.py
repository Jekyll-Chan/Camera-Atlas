"""Opt-in, bounded free-pilot geographic workflow; photos never go to map providers."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .composition.region import prepare_region
from .geography.http import CachedHTTP, ProviderError
from .geography.models import Location, Source
from .geography.projection import MapProjection
from .mobile import MobileWorkspace


class OnlineWorkspace(MobileWorkspace):
    def __init__(self, root, data, geography_cache, photon_url="https://photon.komoot.io/api"):
        super().__init__(root, data)
        self.geography_cache = Path(geography_cache)
        self.photon_url = photon_url
        self.candidates_file = self.root / "places.json"
        if self.candidates_file.exists():
            self.catalogue.update(json.loads(self.candidates_file.read_text()))

    @staticmethod
    def public_place(ident, place):
        return {
            "id": ident,
            "name": place["name"],
            "label": place["label"],
            "aliases": place.get("aliases", place["label"].lower()),
        }

    def search_places(self, query=""):
        with self.lock:
            return self._search_places(query)

    def _search_places(self, query):
        query = query.strip()
        if not query:
            return [self.public_place(k, v) for k, v in self.catalogue.items()]
        if not 2 <= len(query) <= 160:
            raise ValueError("Enter a place name between 2 and 160 characters.")
        if len(self.catalogue) > 95:
            raise ValueError("This session has reached its place-search limit.")
        # Shared cache provides application-wide rate reservations, not one limit per visitor.
        http = CachedHTTP(
            self.geography_cache,
            user_agent="CameraAtlasPilot/0.1 (+https://github.com/Jekyll-Chan/Camera-Atlas)",
        )
        try:
            result = http.json(self.photon_url, params={"q": query, "limit": 5, "lang": "en"}, interval=2)
        finally:
            http.close()
        source = Source(
            id="photon",
            dataset="Photon / OpenStreetMap",
            version="query snapshot",
            url=self.photon_url,
            license="ODbL-1.0",
            attribution="© OpenStreetMap contributors · openstreetmap.org/copyright",
            retrieved_at=datetime.fromtimestamp(result["retrieved_at"], timezone.utc),
            sha256=hashlib.sha256(json.dumps(result["body"], sort_keys=True).encode()).hexdigest(),
        )
        matches = []
        for feature in result["body"].get("features", [])[:5]:
            props, geometry = feature.get("properties", {}), feature.get("geometry", {})
            if geometry.get("type") != "Point" or not props.get("name"):
                continue
            lon, lat = geometry["coordinates"][:2]
            label = " · ".join(
                dict.fromkeys(str(props[k]) for k in ("name", "city", "state", "country") if props.get(k))
            )
            location = Location(
                name=str(props["name"]),
                lat=lat,
                lon=lon,
                accuracy="locality",
                coordinate_source="Photon place centroid; not camera GPS",
                source_id="photon",
            )
            # Search results are candidate identities; only a selected server-issued ID can render.
            ident = uuid.uuid4().hex
            radius = 5 if props.get("osm_value") in ("city", "town") else 0.8
            if props.get("osm_value") in ("water", "lake", "bay"):
                radius = 15
            self.catalogue[ident] = {
                "name": location.name,
                "label": label,
                "aliases": label.lower(),
                "mode": "auto",
                "radius": radius,
                "file": "pending.geojson",
                "location": location.model_dump(mode="json"),
                "geocoder_source": source.model_dump(mode="json"),
            }
            matches.append(self.public_place(ident, self.catalogue[ident]))
        temporary = self.candidates_file.with_suffix(".partial")
        temporary.write_text(json.dumps(self.catalogue, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.candidates_file)
        return matches

    def create_render(self, request, progress=None):
        photo, place, selected, opacity = self.validate_request(request)
        if "location" not in place:
            return self.render_prepared(photo, place, selected, opacity, progress)
        from .geography.tiles import OpenFreeMap

        if progress:
            progress("preparing")
        rect, allowed, anchor = prepare_region(selected)
        location = Location.model_validate(place["location"])
        projection = MapProjection(location.lat, location.lon, place["radius"])
        projection.fit_region(rect[2], rect[3], anchor)
        bounds = projection.bounds_wgs84()
        with OpenFreeMap(self.geography_cache / "tiles") as provider:
            data = provider.fetch(bounds)
        if not data.features:
            raise ProviderError("No supported map geometry in this area; choose another extent.")
        data.location = location
        data.sources.append(Source.model_validate(place["geocoder_source"]))
        geojson = self.root / f"geography-{uuid.uuid4().hex}.geojson"
        geojson.write_text(json.dumps(data.geojson(), ensure_ascii=False), encoding="utf-8")
        place["file"] = str(geojson.resolve())
        result = self.render_prepared(photo, place, selected, opacity, progress)
        output = self.results[result["id"]]
        provenance_path = output / "provenance.json"
        provenance = json.loads(provenance_path.read_text())
        provenance["coverage"] = data.coverage
        provenance["window_plan"] = {
            "bounds": bounds,
            "radius_km": place["radius"],
            "requested_map_mode": place["mode"],
            "rect_px": rect,
            "anchor": anchor,
            "method": "uniform scale; expand geographic extent to selected aspect",
        }
        temporary = provenance_path.with_suffix(".partial")
        temporary.write_text(json.dumps(provenance, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, provenance_path)
        return result
