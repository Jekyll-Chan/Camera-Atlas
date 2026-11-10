"""Reproduce public educational examples; no network or private assets."""

import argparse
import csv
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw
from typer.testing import CliRunner

from camera_atlas import render
from camera_atlas.cli import app

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    common = {"offline": True, "cache": output / ".cache", "svg": True, "map_area": 0.25}

    def run(name, **kwargs):
        result = render({**common, "output": output / name, **kwargs})
        print(name, result.metadata["map_mode"], result.metadata["quality"]["overlay_coverage"])
        return result

    lake = run(
        "01-lake",
        input=DATA / "lake_photo.jpg",
        location="Lake Lucerne",
        geojson=DATA / "lucerne.geojson",
        radius_km=45,
        map_mode="coastline",
        position="top-right",
        scale=True,
    )
    # A regional locator over a NASA aerial view, never an astronaut's ground camera GPS.
    run(
        "02-terrain",
        input=DATA / "lake_photo.jpg",
        lat=46.90,
        lon=8.60,
        confirmed_region=True,
        dem=DATA / "alps_dem.tif",
        dem_source=DATA / "alps_dem.source.json",
        radius_km=16,
        map_mode="topographic",
        style="topographic-fine",
        contour_interval=400,
        position="top-right",
    )
    run(
        "03-city",
        input=DATA / "city_photo.jpg",
        location="San Francisco",
        geojson=DATA / "san_francisco.geojson",
        radius_km=0.45,
        map_mode="urban",
        style="urban-documentary",
        position="top-left",
    )
    run(
        "04-region",
        input=DATA / "lake_photo.jpg",
        lat=46.98,
        lon=8.42,
        confirmed_region=True,
        geojson=DATA / "lucerne.geojson",
        radius_km=45,
        map_mode="regional",
        labels=False,
    )
    run("05-offline-fallback", input=DATA / "lake_photo.jpg", lat=46.98, lon=8.42)
    # Deliberate test annotation on a public image, not a claim that the source contained old text.
    scratch = output / "repair-input"
    scratch.mkdir()
    image = Image.open(DATA / "lake_photo.jpg").convert("RGB")
    ImageDraw.Draw(image).text((30, 30), "DEMO OLD TEXT", fill="white", stroke_width=1)
    annotated = scratch / "annotated.png"
    image.save(annotated)
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).rectangle((26, 26, 140, 46), fill=255)
    mask_path = scratch / "approved_mask.png"
    mask.save(mask_path)
    run("06-local-repair", input=annotated, map_enabled=False, remove_text=True, text_mask=mask_path)
    batch_input = output / "batch-input"
    batch_input.mkdir()
    for name in ("one", "two"):
        shutil.copy(DATA / "lake_photo.jpg", batch_input / f"{name}.jpg")
    manifest = output / "batch.csv"
    with manifest.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["file", "lat", "lon", "confirmed_region"])
        writer.writerows([["one.jpg", 46.98, 8.42, "true"], ["two.jpg", 46.98, 8.42, "true"]])
    cli = CliRunner().invoke(
        app,
        [
            "batch",
            "--input",
            str(batch_input),
            "--manifest",
            str(manifest),
            "--output",
            str(output / "07-batch"),
            "--cache",
            str(output / ".cache"),
        ],
    )
    if cli.exit_code:
        raise RuntimeError(cli.output)
    # Gallery is a presentation of reduced previews only. Rendered final.png dimensions are unchanged.
    thumbs = []
    for name in ("01-lake", "02-terrain", "03-city", "04-region", "05-offline-fallback", "06-local-repair"):
        im = Image.open(output / name / "final.png").convert("RGB")
        im.thumbnail((560, 370))
        card = Image.new("RGB", (600, 420), (244, 242, 236))
        card.paste(im, ((600 - im.width) // 2, 15))
        ImageDraw.Draw(card).text((20, 395), name, fill=(40, 40, 36))
        thumbs.append(card)
    contact = Image.new("RGB", (1800, 840), (244, 242, 236))
    for i, im in enumerate(thumbs):
        contact.paste(im, ((i % 3) * 600, (i // 3) * 420))
    contact.save(output / "gallery.jpg", quality=92)
    (output / "summary.json").write_text(
        json.dumps(
            {
                "scenarios": 7,
                "network": False,
                "lake_source": lake.metadata["location"],
                "note": "Educational NASA aerial photographs; map locators are regional",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "generated")
    build(parser.parse_args().output.resolve())
