import csv
import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from .config import RenderConfig
from .pipeline import render as render_photo

app = typer.Typer(no_args_is_help=True, help="Camera Atlas — Photography First. Geography Verified.")


def execute(values):
    try:
        result = render_photo(RenderConfig(**values))
    except (ValueError, OSError, ValidationError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(str(result.final))
    for warning in result.metadata["warnings"]:
        typer.echo("Warning: " + warning, err=True)
    return result


@app.command()
def render(
    input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
    location: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    confirmed_region: bool = False,
    geojson: Path | None = None,
    dem: Path | None = None,
    dem_source: Path | None = None,
    contour_interval: float = 100,
    map_mode: str = "auto",
    style: str = "editorial-minimal",
    map_enabled: Annotated[bool, typer.Option("--map/--no-map")] = True,
    map_area: float = 0.20,
    opacity: float = 0.65,
    position: str = "auto",
    label_language: str = "en",
    labels: bool = True,
    font: Path | None = None,
    svg: bool = False,
    layers: bool = True,
    preserve_metadata: bool = False,
    offline: bool = False,
    cache: Path = Path.home() / ".cache" / "camera-atlas",
    radius_km: float = 10,
    scale: bool = False,
    north: bool = False,
    remove_text: bool = False,
    text_mask: Path | None = None,
    exclusion_mask: Path | None = None,
    nominatim_url: str | None = None,
    accept_public_nominatim_policy: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    user_agent: str = "CameraAtlas/0.1 (local photography tool)",
    subject: str = "unknown",
):
    """Render a photo. Ambiguous/absent geography yields an unchanged clean photograph."""
    execute(locals())


@app.command()
def batch(
    input: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    manifest: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
    offline: bool = True,
    cache: Path = Path.home() / ".cache" / "camera-atlas",
):
    """CSV rows: file,lat,lon,location,geojson,dem,dem_source,confirmed_region.

    Deliberately serial and offline by default; public bulk geocoding is not enabled.
    """
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    success = []
    seen = set()
    try:
        with manifest.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if "file" not in (reader.fieldnames or []):
                raise ValueError("Batch manifest needs a file column")
            for n, row in enumerate(reader, 2):
                try:
                    file = Path(row["file"])
                    path = (input / file).resolve()
                    if file.is_absolute() or not path.is_relative_to(input.resolve()):
                        raise ValueError("Batch paths must stay inside the input directory")
                    target = output / file.with_suffix("")
                    if target in seen:
                        raise ValueError("Duplicate batch output target")
                    seen.add(target)
                    values = {"input": path, "output": target, "offline": offline, "cache": cache}
                    for key in ("lat", "lon", "location", "geojson", "dem", "dem_source"):
                        if row.get(key):
                            values[key] = row[key]
                    for key in ("geojson", "dem", "dem_source"):
                        if key in values:
                            values[key] = (manifest.parent / values[key]).resolve()
                    if row.get("confirmed_region"):
                        value = row["confirmed_region"].lower()
                        if value not in ("true", "false", "1", "0"):
                            raise ValueError("confirmed_region must be true/false or 1/0")
                        values["confirmed_region"] = value in ("true", "1")
                    result = render_photo(RenderConfig(**values))
                    success.append(str(result.final.relative_to(output)))
                    typer.echo(str(result.final))
                except (ValueError, OSError) as exc:
                    failures.append({"row": n, "file": row.get("file"), "error": str(exc)})
    except (ValueError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc
    (output / "batch_report.json").write_text(
        json.dumps({"success": success, "failures": failures}, indent=2)
    )
    if failures:
        typer.echo(f"{len(failures)} batch rows failed; see batch_report.json", err=True)
        raise typer.Exit(1)


@app.command("detect-text")
def detect_text(
    input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
):
    """Create a candidate OCR mask for review. Never repairs automatically."""
    from .image.io import read_photo
    from .image.text import detect_text as detect

    try:
        image, _ = read_photo(input)
        if output.exists() and any(output.iterdir()):
            raise ValueError("OCR output must be empty")
        output.mkdir(parents=True, exist_ok=True)
        # OCR runs against normalized pixels, preserving alignment on EXIF-oriented images.
        normalized = output / "ocr_input.png"
        image.save(normalized)
        mask, boxes = detect(normalized, image.size)
        mask.save(output / "candidate_text_mask.png")
        (output / "review.json").write_text(json.dumps(boxes, indent=2))
        typer.echo("Review candidate_text_mask.png before passing --remove-text --text-mask")
    except (ValueError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc


if __name__ == "__main__":
    app()
