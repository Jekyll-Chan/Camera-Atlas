import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .cartography.design import select_mode
from .cartography.renderer import render_map
from .composition.analyzer import analyze, place
from .config import RenderConfig
from .geography.dem import contours
from .geography.http import CachedHTTP, ProviderError
from .geography.location import resolve
from .geography.models import GeoData, now
from .geography.projection import MapProjection
from .geography.providers import OfflineGeoJSON, Overpass
from .image.io import load_mask, png_info, read_photo
from .image.text import repair
from .validation.integrity import verify


@dataclass
class RenderResult:
    output: Path
    final: Path
    metadata: dict


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def render(config: RenderConfig | dict) -> RenderResult:
    config = RenderConfig.model_validate(config)
    if config.output.exists() and any(config.output.iterdir()):
        raise ValueError("Output directory is not empty; choose a new directory to preserve existing work")
    original, info = read_photo(config.input)
    if min(original.size) < 128:
        raise ValueError("Photo must be at least 128 pixels on each side")
    clean = original.copy()
    warnings = []
    mask = None
    repair_report = None
    if config.remove_text:
        mask = load_mask(config.text_mask, original.size)
        clean, repair_report = repair(original, mask)
        warnings.append("Local text repair needs human review; hidden detail is not recoverable")
    exclusion = load_mask(config.exclusion_mask, original.size) if config.exclusion_mask else None
    saliency, hints = analyze(clean, exclusion)
    warnings.extend(hints)
    data = OfflineGeoJSON(config.geojson).fetch() if config.geojson else GeoData()
    if config.dem:
        terrain = contours(config.dem, config.dem_source, config.contour_interval)
        if {s.id for s in data.sources} & {s.id for s in terrain.sources}:
            raise ValueError("DEM and vector source IDs must be distinct")
        data = GeoData(
            sources=data.sources + terrain.sources,
            features=data.features + terrain.features,
            location=data.location,
            warnings=data.warnings + terrain.warnings,
        )
    http = CachedHTTP(config.cache, config.offline, config.user_agent)
    try:
        location, location_warnings = resolve(config, info["gps"], data, http)
        warnings.extend(location_warnings)
        projection = None
        if config.map_enabled and location.lat is not None and location.accuracy != "unresolved":
            try:
                projection = MapProjection(location.lat, location.lon, config.radius_km)
                bounds = projection.bounds_wgs84()
            except ValueError as exc:
                warnings.append(str(exc))
                projection = None
            if projection and not data.features:
                try:
                    vectors = Overpass(http, config.overpass_url).fetch(bounds)
                    data.sources.extend(vectors.sources)
                    data.features.extend(vectors.features)
                    warnings.extend(vectors.warnings)
                except ProviderError as exc:
                    warnings.append(str(exc))
    finally:
        http.close()
    data = GeoData(sources=data.sources, features=data.features, location=location, warnings=data.warnings)
    warnings.extend(data.warnings)
    # Mode selection uses actual data in the visible geographic extent, not remote features.
    visible = data.features
    if projection:
        from shapely.geometry import box, shape

        viewport = box(*projection.extent)
        visible = [f for f in data.features if projection.project(shape(f["geometry"])).intersects(viewport)]
    mode = select_mode(visible, config.map_mode, config.subject)
    rect, placement = place(clean.size, saliency, config.map_area, config.position)
    overlay = Image.new("RGBA", clean.size)
    svg = None
    cartography = {"drawn_features": []}
    if config.map_enabled and projection:
        overlay, svg, cartography = render_map(
            clean.size, rect, projection, data, location, mode, config, exclusion
        )
    if config.map_enabled and not cartography["drawn_features"]:
        warnings.append(
            "No verified map rendered; returned a clean photograph. Supply location and suitable data"
        )
    if location.candidates:
        warnings.append("Ambiguous location; choose a candidate and confirm locality before rendering")
    if placement["texture_risk"] > 0.24:
        warnings.append("Limited negative space: review map placement and supply a subject exclusion mask")
    final = Image.alpha_composite(clean, overlay)
    quality = verify(original, clean, overlay, final, mask, exclusion)
    if quality["low_contrast_fraction"] is not None and quality["low_contrast_fraction"] > 0.4:
        warnings.append(
            "Low overlay contrast; review placement, theme and opacity at the intended viewing size"
        )
    if cartography.get("reason"):
        warnings.append(cartography["reason"])
    provenance = {
        "schema_version": "1.0",
        "created_at": now(),
        "location": location.model_dump(mode="json"),
        "sources": [s.model_dump(mode="json") for s in data.sources],
        "cartography": cartography,
        "warnings": warnings,
        "camera_heading": None,
        "trust_boundary": "Provider declarations are auditable claims, not independent certification",
    }
    metadata = {
        "camera_atlas_version": "0.1.0",
        "input_sha256": hashlib.sha256(config.input.read_bytes()).hexdigest(),
        "normalized_mode": "RGBA 8-bit",
        "geographic_input_sha256": {
            str(p.name): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (config.geojson, config.dem, config.dem_source)
            if p
        },
        "map_mode": mode,
        "style": config.style,
        "location": location.model_dump(mode="json"),
        "quality": quality,
        "placement": placement,
        "repair": repair_report,
        "warnings": warnings,
        "metadata_preserved": config.preserve_metadata,
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    # Stage files beside target so interrupted renders never expose a half-written final directory.
    with tempfile.TemporaryDirectory(prefix=".camera-atlas-", dir=config.output.parent) as tmp:
        stage = Path(tmp) / "result"
        stage.mkdir()
        options = png_info(info, config.preserve_metadata)
        final.save(stage / "final.png", **options)
        if config.layers:
            original.save(stage / "original.png", **options)
            clean.save(stage / "clean_base.png", **options)
            overlay.save(stage / "map_overlay.png")
            saliency.save(stage / "saliency_mask.png")
            if mask:
                mask.save(stage / "text_removal_mask.png")
        if config.svg and svg:
            (stage / "map_overlay.svg").write_text(svg, encoding="utf-8")
        _json(stage / "location.geojson", data.geojson())
        _json(stage / "metadata.json", metadata)
        _json(stage / "provenance.json", provenance)
        if config.output.exists():
            config.output.rmdir()
        os.replace(stage, config.output)
    return RenderResult(config.output, config.output / "final.png", metadata)
