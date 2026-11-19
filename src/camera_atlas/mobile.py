"""Loopback-only mobile interaction prototype using curated, sourced offline maps.

Not a hosted service. Uploads/results persist in the selected workspace. No
geocoding, cloud upload, or inferred location is performed by this prototype.
"""

import argparse
import base64
import binascii
import io
import json
import math
import mimetypes
import os
import re
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import get_args
from urllib.parse import urlparse

from PIL import Image

from .config import Mode
from .image.io import check_photo_colour, png_info, prepare_photo_decoder, read_photo
from .jobs import JobQueue
from .pipeline import render

MAX_BYTES = 18 * 1024 * 1024
# Local workflows accept typical 12/24 MP phone photos without resizing. The
# public service applies its own much smaller limit before this local decoder.
MAX_PIXELS = 25_000_000
CATALOGUE = {
    "san-francisco": {
        "name": "San Francisco",
        "label": "San Francisco · California, USA",
        "aliases": "旧金山 美国 san francisco california sf",
        "file": "san_francisco.geojson",
        "photo": "city_photo.jpg",
        "mode": "urban",
        "radius": 0.08,
    },
    "lucerne": {
        "name": "Lake Lucerne",
        "label": "Lake Lucerne · Switzerland",
        "aliases": "卢塞恩湖 琉森湖 瑞士 lake lucerne switzerland",
        "file": "lucerne.geojson",
        "photo": "lake_photo.jpg",
        "mode": "coastline",
        "radius": 45,
    },
}


class MobileWorkspace:
    def __init__(self, root, data):
        self.root, self.data = Path(root), Path(data)
        self.catalogue = dict(CATALOGUE)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.photos = {p.stem: p for p in self.root.glob("*.png") if re.fullmatch(r"[a-f0-9]{32}", p.stem)}
        self.results = {
            p.parent.name: p.parent
            for p in self.root.glob("*/delivery.json")
            if re.fullmatch(r"[a-f0-9]{32}", p.parent.name)
        }
        self.lock = threading.Lock()

    def photo_info(self, ident):
        photo = self.photos.get(ident)
        if photo is None:
            raise KeyError("Photo not found")
        metadata = self.root / f"{ident}.metadata.json"
        with Image.open(photo) as image:
            result = {
                "id": ident,
                "width": image.width,
                "height": image.height,
                "url": f"/files/{ident}/photo.png",
            }
        if metadata.is_file():
            result["source_metadata"] = json.loads(metadata.read_text(encoding="utf-8"))
        return result

    def add_photo(self, body):
        if not body or len(body) > MAX_BYTES:
            raise ValueError("Choose a photo under 18 MB.")
        # Decode before read_photo so dimensions are bounded before allocating RGBA.
        prepare_photo_decoder(body[:4096])
        with Image.open(io.BytesIO(body)) as image:
            check_photo_colour(image)
            if image.width * image.height > MAX_PIXELS or min(image.size) < 128:
                raise ValueError(
                    "Use a photo up to 25 megapixels, at least 128 pixels on each side. "
                    "The original will not be resized automatically."
                )
            image.verify()
        ident = uuid.uuid4().hex
        source = self.root / f"{ident}.input"
        source.write_bytes(body)
        clean, info = read_photo(source)
        path = self.root / f"{ident}.png"
        temporary = self.root / f"{ident}.partial"
        clean.save(temporary, format="PNG", **png_info(info))
        os.replace(temporary, path)
        clean.close()
        # Preserve the source's location separately from the normalized PNG so
        # an agent can resolve a supplied place against actual camera GPS. This
        # private workspace metadata is never added to public output/repositories.
        metadata = {key: info[key] for key in ("format", "gps", "orientation")}
        (self.root / f"{ident}.metadata.json").write_text(
            json.dumps(metadata, allow_nan=False), encoding="utf-8"
        )
        # Retain the original input locally for recoverable processing. It is not
        # a public download route and is never included in the code repository.
        self.photos[ident] = path
        return self.photo_info(ident)

    def validate_request(self, request):
        if not isinstance(request, dict):
            raise ValueError("Invalid request. Please try again.")
        photo = self.photos.get(request.get("photo_id"))
        place = self.catalogue.get(request.get("place_id"))
        if not photo or not place or request.get("confirmed") is not True:
            raise ValueError("Choose a photo and confirm its place first.")
        encoded = request.get("mask", "")
        if not isinstance(encoded, str) or len(encoded) > MAX_BYTES:
            raise ValueError("Invalid selection. Please select the area again.")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid selection. Please select the area again.") from exc
        with Image.open(io.BytesIO(decoded)) as mask, Image.open(photo) as original:
            if mask.size != original.size:
                raise ValueError("Selection size does not match the photo. Please select again.")
            selected = mask.convert("L").point(lambda value: 255 if value > 127 else 0)
        bounds = selected.getbbox()
        if bounds is None or min(bounds[2] - bounds[0], bounds[3] - bounds[1]) < 64:
            raise ValueError("Select an area at least 64 pixels wide and high.")
        opacity = float(request.get("opacity", 0.7))
        if not math.isfinite(opacity) or not 0.2 <= opacity <= 1:
            raise ValueError("Choose an ink level between 20 and 100 percent.")
        # A render's extent and style belong to that request, not the shared
        # place catalogue. Queued retries retain these values in their payload.
        place = dict(place)
        if "radius_km" in request:
            radius = request["radius_km"]
            if isinstance(radius, bool) or not isinstance(radius, (float, int)):
                raise ValueError("Map radius must be a number greater than 0 and at most 100 km.")
            if not math.isfinite(radius) or not 0 < radius <= 100:
                raise ValueError("Map radius must be greater than 0 and at most 100 km.")
            place["radius"] = float(radius)
        if "map_mode" in request:
            if request["map_mode"] not in get_args(Mode):
                raise ValueError("Choose a supported map mode.")
            place["mode"] = request["map_mode"]
        if "location_label" in request:
            label = request["location_label"]
            if (
                not isinstance(label, str)
                or not 1 <= len(label.strip()) <= 80
                or any(ord(char) < 32 for char in label)
            ):
                raise ValueError("Location label must be one readable line, at most 80 characters.")
            place["location_label"] = label.strip()
        return photo, place, selected, opacity

    def create_render(self, request, progress=None):
        photo, place, selected, opacity = self.validate_request(request)
        return self.render_prepared(photo, place, selected, opacity, progress)

    def render_prepared(self, photo, place, selected, opacity, progress=None):
        """Render validated inputs without re-reading mutable place defaults."""
        report = progress or (lambda stage: None)
        ident = uuid.uuid4().hex
        region = self.root / f"{ident}-region.png"
        selected.save(region)
        with self.lock:
            report("rendering")
            result = render(
                {
                    "input": photo,
                    "output": self.root / ident,
                    "geojson": self.data / place["file"],
                    "location": place["name"],
                    "location_label": place.get("location_label"),
                    "region_mask": region,
                    "radius_km": place["radius"],
                    "opacity": opacity,
                    "offline": True,
                    "map_mode": place["mode"],
                    "cache": self.root / "cache",
                }
            )
        report("verifying")
        if not result.metadata["quality"]["overlay_coverage"]:
            raise ValueError(
                "No map lines in this selection. Adjust the area; preview map coverage is limited."
            )
        provenance = json.loads((result.output / "provenance.json").read_text())
        for name in ("final.png", "map_overlay.png", "map_region_mask.png", "provenance.json"):
            if not (result.output / name).is_file():
                raise ValueError("The output is incomplete. Please retry.")
        delivery = {
            "id": ident,
            "final": f"/files/{ident}/final.png",
            "overlay": f"/files/{ident}/map_overlay.png",
            "mask": f"/files/{ident}/map_region_mask.png",
            "sources": f"/files/{ident}/provenance.json",
            "distribution": provenance["cartography"].get("region_distribution"),
            "warnings": result.metadata["warnings"],
            "review_required": True,
        }
        temporary = result.output / "delivery.partial"
        temporary.write_text(json.dumps(delivery, allow_nan=False), encoding="utf-8")
        os.replace(temporary, result.output / "delivery.json")
        self.results[ident] = result.output
        return delivery


def serve(host="127.0.0.1", port=8765, data=None, open_browser=False, storage=None):
    # Restrict preview to this computer until a production storage/auth design exists.
    if host != "127.0.0.1":
        raise ValueError("This preview only binds to 127.0.0.1")
    assets = Path(__file__).parent / "web"
    data = Path(data) if data else Path(__file__).resolve().parents[2] / "examples/data"
    if not all((data / item["file"]).is_file() for item in CATALOGUE.values()):
        raise ValueError("Public example data not found; supply --data with examples/data")
    directory = Path(storage) if storage else Path.home() / ".local/share/camera-atlas/mobile"
    workspace = MobileWorkspace(directory, data)
    with JobQueue(directory, workspace.create_render) as jobs:

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, body, status=200, mime="application/json; charset=utf-8", attachment=None):
                if not isinstance(body, bytes):
                    body = json.dumps(body, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                if attachment:
                    self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
                self.end_headers()
                self.wfile.write(body)

            def local_request(self):
                valid = {f"127.0.0.1:{port}", f"localhost:{port}"}
                origin = self.headers.get("Origin")
                return self.headers.get("Host") in valid and (
                    origin is None or urlparse(origin).netloc in valid
                )

            def do_GET(self):
                if not self.local_request():
                    return self.respond({"error": "Local preview only"}, 403)
                url = urlparse(self.path)
                path = url.path
                if path == "/api/health":
                    return self.respond(
                        {
                            "application": "camera-atlas",
                            "ready": True,
                            "durable_jobs": True,
                            "global_places": False,
                            "automatic_selection": False,
                        }
                    )
                match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})(/input)?", path)
                if match:
                    try:
                        return self.respond(jobs.get(match[1], include_input=bool(match[2])))
                    except KeyError:
                        return self.respond({"error": "Job not found"}, 404)
                match = re.fullmatch(r"/api/photo/([a-f0-9]{32})", path)
                if match:
                    try:
                        return self.respond(workspace.photo_info(match[1]))
                    except KeyError:
                        return self.respond({"error": "Photo not found"}, 404)
                if path == "/api/places":
                    return self.respond(
                        [
                            {
                                "id": key,
                                "name": value["name"],
                                "label": value["label"],
                                "aliases": value["aliases"],
                            }
                            for key, value in CATALOGUE.items()
                        ]
                    )
                if path in ("/", "/index.html", "/app.js", "/style.css"):
                    file = assets / ("index.html" if path == "/" else path[1:])
                    mime = {
                        ".html": "text/html; charset=utf-8",
                        ".css": "text/css; charset=utf-8",
                        ".js": "text/javascript; charset=utf-8",
                    }[file.suffix]
                    return self.respond(file.read_bytes(), mime=mime)
                match = re.fullmatch(
                    r"/files/([a-f0-9]{32})/(photo.png|final.png|map_overlay.png|map_region_mask.png|provenance.json)",
                    path,
                )
                if match:
                    ident, name = match.groups()
                    file = (
                        workspace.photos.get(ident)
                        if name == "photo.png"
                        else (workspace.results[ident] / name if ident in workspace.results else None)
                    )
                    if file and file.is_file():
                        return self.respond(
                            file.read_bytes(),
                            mime=mimetypes.guess_type(file)[0],
                            attachment=name if url.query == "download=1" else None,
                        )
                return self.respond({"error": "File not found"}, 404)

            def do_POST(self):
                if not self.local_request():
                    return self.respond({"error": "Local preview only"}, 403)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_BYTES:
                        raise ValueError("The file is empty or too large.")
                    body = self.rfile.read(length)
                    if self.path == "/api/photo":
                        result = workspace.add_photo(body)
                    elif self.path == "/api/sample":
                        item = CATALOGUE.get(json.loads(body).get("place_id"))
                        if not item:
                            raise ValueError("Choose an available sample place.")
                        result = workspace.add_photo((data / item["photo"]).read_bytes())
                    elif self.path == "/api/render":
                        result = workspace.create_render(json.loads(body))
                    elif self.path == "/api/jobs":
                        request = json.loads(body)
                        workspace.validate_request(request)
                        result = jobs.submit(request, self.headers.get("Idempotency-Key"))
                        return self.respond(result, 202)
                    elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})/retry", self.path):
                        return self.respond(jobs.retry(match[1]), 202)
                    else:
                        return self.respond({"error": "Not found"}, 404)
                    self.respond(result)
                except (ValueError, OSError, TypeError, KeyError) as exc:
                    self.respond({"error": str(exc)}, 400)

        server = ThreadingHTTPServer((host, port), Handler)
        print(f"Camera Atlas local preview: http://{host}:{port}", flush=True)
        if open_browser:
            webbrowser.open(f"http://{host}:{port}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--storage", type=Path, help="Private persistent workspace; one server per directory")
    args = parser.parse_args()
    serve(port=args.port, data=args.data, open_browser=args.open_browser, storage=args.storage)
