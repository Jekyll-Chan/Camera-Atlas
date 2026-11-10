from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import shape


def now():
    return datetime.now(timezone.utc).isoformat()


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    version: str = Field(min_length=1)
    url: str = Field(min_length=1)
    license: str = Field(min_length=1)
    attribution: str = Field(min_length=1)
    retrieved_at: datetime
    resolution_m: float | None = Field(None, gt=0)
    min_span_km: float | None = Field(None, gt=0)
    sha256: str | None = None
    units: str | None = None
    uncertainty: str = "Dataset accuracy is not independently certified"


class Location(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: str = "Unresolved"
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    accuracy: Literal["exact_gps", "locality", "regional", "unresolved"] = "unresolved"
    coordinate_source: str = "none"
    source_id: str | None = None
    bounds: tuple[float, float, float, float] | None = None
    conflicts: list[str] = Field(default_factory=list)
    candidates: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def coordinates(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Incomplete location coordinates")
        if self.accuracy != "unresolved" and self.lat is None:
            raise ValueError("Resolved location needs coordinates")
        return self


class GeoData(BaseModel):
    sources: list[Source] = Field(default_factory=list)
    features: list[dict] = Field(default_factory=list)
    location: Location | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_features(self):
        sources = {s.id for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Source IDs must be unique")
        for f in self.features:
            if f.get("type") != "Feature" or f.get("properties", {}).get("source_id") not in sources:
                raise ValueError("Every GeoJSON feature requires a known properties.source_id")
            g = shape(f["geometry"])
            if g.is_empty or not g.is_valid:
                raise ValueError("Empty or invalid geographic geometry")
            if g.geom_type not in {"Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}:
                raise ValueError("Unsupported geographic geometry type")
            x0, y0, x1, y1 = g.bounds
            if not (-180 <= x0 <= x1 <= 180 and -90 <= y0 <= y1 <= 90):
                raise ValueError("GeoJSON must use WGS84 longitude/latitude")
        return self

    def geojson(self):
        return {
            "type": "FeatureCollection",
            "features": self.features,
            "sources": [s.model_dump(mode="json") for s in self.sources],
            "location": self.location.model_dump(mode="json") if self.location else None,
        }
