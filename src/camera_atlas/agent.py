"""Small JSON operations for an agent that can execute Python and inspect images.

The agent owns the conversation, location disambiguation and visual review.
These commands do the file/data work without launching a web service. They do
not establish that a particular chat application supplies the required tools.
"""

import argparse
import base64
import json
from pathlib import Path

from PIL import Image

from .composition.suggestion import suggest_region
from .geography.http import ProviderError
from .mobile import MAX_BYTES, MAX_PIXELS
from .online import OnlineWorkspace


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def workspace_at(directory, data=None):
    directory = Path(directory).expanduser().resolve()
    if data is None:
        # A normal wheel does not carry the repository's licensed photo samples.
        # In the portable kit, the agent runs from the extracted project root.
        local = Path.cwd() / "examples/data"
        data = local if local.is_dir() else Path(__file__).resolve().parents[2] / "examples/data"
    return OnlineWorkspace(directory, Path(data).expanduser().resolve(), directory / "geography-cache")


def prepare(input_path, directory, data=None):
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("Photo not found. Supply an existing local file.")
    if source.stat().st_size > MAX_BYTES:
        raise ValueError("Choose a photo under 18 MB; the original will not be resized automatically.")
    workspace = workspace_at(directory, data)
    photo = workspace.add_photo(source.read_bytes())
    base = workspace.photos[photo["id"]]
    preparation = workspace.root / (photo["id"] + "-preparation")
    preparation.mkdir()
    with Image.open(base) as image:
        suggestion = suggest_region(image)
    region = preparation / "suggested_region.png"
    suggestion.mask.save(region)
    report = {
        "status": "prepared",
        "photo_id": photo["id"],
        "base_path": str(base),
        "original_path": str(workspace.root / (photo["id"] + ".input")),
        "region_path": str(region),
        "width": photo["width"],
        "height": photo["height"],
        "requires_review": suggestion.requires_review,
        "has_suggestion": suggestion.mask.getbbox() is not None,
        "confidence": suggestion.confidence,
        "method": suggestion.method,
        "reason": suggestion.reason,
        "max_pixels": MAX_PIXELS,
        "source_metadata": photo.get("source_metadata"),
    }
    (preparation / "preparation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def search(place, directory, data=None):
    candidates = workspace_at(directory, data).search_places(place)
    return {
        "status": "needs_place_confirmation" if candidates else "needs_location",
        "candidates": candidates,
        "accuracy": "locality",
        "note": "Choose the matching place; a place centroid is not the camera position.",
    }


def render(
    photo_id,
    place_id,
    region_path,
    reviewed_region,
    directory,
    opacity=0.7,
    data=None,
    radius_km=None,
    map_mode=None,
    location_label=None,
):
    if not reviewed_region:
        raise ValueError("Inspect the photo and region first, then pass --reviewed-region.")
    region = Path(region_path).expanduser().resolve()
    if not region.is_file() or region.stat().st_size > MAX_BYTES:
        raise ValueError("Supply an existing region mask under 18 MB.")
    workspace = workspace_at(directory, data)
    request = {
        "photo_id": photo_id,
        "place_id": place_id,
        "mask": base64.b64encode(region.read_bytes()).decode(),
        "confirmed": True,
        "opacity": opacity,
    }
    if radius_km is not None:
        request["radius_km"] = radius_km
    if map_mode is not None:
        request["map_mode"] = map_mode
    if location_label is not None:
        request["location_label"] = location_label
    # The underlying validator checks dimensions and an existing persisted place
    # identity before any network request or render output is created.
    workspace.validate_request(request)
    delivery = workspace.create_render(request)
    output = workspace.results[delivery["id"]]
    return {
        "status": "rendered",
        "id": delivery["id"],
        "final": str(output / "final.png"),
        "overlay": str(output / "map_overlay.png"),
        "mask": str(output / "map_region_mask.png"),
        "sources": str(output / "provenance.json"),
        "clean_base": str(output / "clean_base.png"),
        "warnings": delivery["warnings"],
        "distribution": delivery["distribution"],
        "review_required": delivery["review_required"],
    }


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        photo = commands.add_parser("prepare", help="Retain the photo and suggest an editable region")
        photo.add_argument("--input", required=True, type=Path)
        places = commands.add_parser("search", help="Find sourced location candidates")
        places.add_argument("--place", required=True)
        create = commands.add_parser("render", help="Render a reviewed region at a selected place")
        create.add_argument("--photo-id", required=True)
        create.add_argument("--place-id", required=True)
        create.add_argument("--region", required=True, type=Path)
        create.add_argument("--reviewed-region", action="store_true")
        create.add_argument("--opacity", type=float, default=0.7)
        create.add_argument(
            "--radius-km", type=float, help="Half the short-axis geographic span; expands the real data query"
        )
        create.add_argument("--map-mode", help="Map content mode, such as urban, coastline or auto")
        create.add_argument("--location-label", help="Verified display name without changing map coordinates")
        for command in (photo, places, create):
            command.add_argument("--workspace", required=True, type=Path)
            command.add_argument("--data", type=Path, help="Repository examples/data (for offline samples)")
        args = parser.parse_args(argv)
        if args.command == "prepare":
            result = prepare(args.input, args.workspace, args.data)
        elif args.command == "search":
            result = search(args.place, args.workspace, args.data)
        else:
            result = render(
                args.photo_id,
                args.place_id,
                args.region,
                args.reviewed_region,
                args.workspace,
                args.opacity,
                args.data,
                args.radius_km,
                args.map_mode,
                args.location_label,
            )
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, ProviderError, ImportError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
