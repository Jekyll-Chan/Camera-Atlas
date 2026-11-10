from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Mode = Literal["auto", "coastline", "topographic", "urban", "trail", "river", "regional", "minimal"]
Style = Literal[
    "editorial-minimal", "topographic-fine", "coastal-atlas", "urban-documentary", "monochrome-print"
]


class RenderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    input: Path
    output: Path
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    location: str | None = None
    confirmed_region: bool = False
    geojson: Path | None = None
    dem: Path | None = None
    dem_source: Path | None = None
    contour_interval: float = Field(100, gt=0, le=10000)
    map_mode: Mode = "auto"
    style: Style = "editorial-minimal"
    map_enabled: bool = True
    map_area: float = Field(0.20, ge=0.03, le=0.30)
    opacity: float = Field(0.65, ge=0, le=1)
    position: Literal["auto", "top-left", "top-right", "bottom-left", "bottom-right"] = "auto"
    label_language: Literal["en", "local", "bilingual"] = "en"
    labels: bool = True
    font: Path | None = None
    svg: bool = False
    layers: bool = True
    preserve_metadata: bool = False
    offline: bool = False
    cache: Path = Field(default_factory=lambda: Path.home() / ".cache" / "camera-atlas")
    radius_km: float = Field(10, gt=0, le=100)
    scale: bool = False
    north: bool = False
    remove_text: bool = False
    text_mask: Path | None = None
    exclusion_mask: Path | None = None
    nominatim_url: str | None = None
    accept_public_nominatim_policy: bool = False
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "CameraAtlas/0.1 (local photography tool)"
    subject: Literal["unknown", "lake", "mountain", "city", "trail", "river", "coast"] = "unknown"

    @field_validator("overpass_url", "nominatim_url")
    @classmethod
    def endpoint_url(cls, value):
        if value is None:
            return value
        from urllib.parse import urlparse

        url = urlparse(value)
        if url.scheme not in ("http", "https") or not url.hostname:
            raise ValueError("Provider endpoint must be an HTTP(S) URL")
        return value

    @model_validator(mode="after")
    def validate_inputs(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("--lat and --lon must be supplied together")
        if self.remove_text and self.text_mask is None:
            raise ValueError("Text repair requires a reviewed --text-mask; OCR alone is not approval")
        if self.dem and not self.dem_source:
            raise ValueError("DEM requires --dem-source provenance JSON with units=m")
        if self.geojson and not self.geojson.is_file():
            raise ValueError("GeoJSON file does not exist")
        if not self.input.is_file():
            raise ValueError("Input image does not exist")
        if self.output.resolve() == self.input.parent.resolve():
            raise ValueError("Output must be a separate directory from the input image")
        return self
