"""Bounded, anonymous-session HTTP adapter for a single small CPU instance.

Run with ``uvicorn camera_atlas.service:create_app --factory --port 7860``.
Set ATLAS_PUBLIC_ORIGIN to the exact HTTPS origin before public deployment.
This adapter does not make the example catalogue a global geography service.
"""

import asyncio
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from starlette.concurrency import run_in_threadpool

from .jobs import JobQueue
from .mobile import CATALOGUE, MAX_BYTES, MobileWorkspace

COOKIE = "atlas_session"
FILES = {"photo.png", "final.png", "map_overlay.png", "map_region_mask.png", "provenance.json"}
ID = re.compile(r"[a-f0-9]{32}")


@dataclass(frozen=True)
class Limits:
    sessions: int = 16
    uploads_per_session: int = 1
    jobs_per_session: int = 2
    queue: int = 2
    max_pixels: int = 1_500_000
    session_bytes: int = 72 * 1024 * 1024
    total_bytes: int = 100 * 1024 * 1024
    ttl_seconds: int = 3600
    ingress: int = 1


def directory_size(path):
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except FileNotFoundError:
            # The renderer atomically promotes a staging directory.
            pass
    return total


class ServiceState:
    def __init__(self, root, data, limits, workspace_factory=MobileWorkspace):
        self.root, self.data, self.limits = Path(root), Path(data), limits
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.sessions_root = self.root / "sessions"
        self.sessions_root.mkdir(exist_ok=True, mode=0o700)
        self.database = self.root / "service.sqlite3"
        self.lock = threading.RLock()
        self.workspaces = {}
        self.workspace_factory = workspace_factory
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
                created REAL NOT NULL, last_seen REAL NOT NULL
            )""")
        self.jobs = JobQueue(self.root / "queue", self.process, capacity=limits.queue)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def process(self, envelope, progress):
        workspace = self.workspace(envelope["owner"])
        return workspace.create_render(envelope["request"], progress)

    def workspace(self, owner):
        with self.lock:
            if owner not in self.workspaces:
                self.workspaces[owner] = self.workspace_factory(self.sessions_root / owner, self.data)
            return self.workspaces[owner]

    def cleanup(self, now=None):
        """Expire idle sessions; never delete queued/running input or output."""
        now = time.time() if now is None else now
        with self.lock, self.jobs.condition, self.connect() as db, self.jobs.connect() as jobs:
            expired = db.execute(
                "SELECT id FROM sessions WHERE last_seen < ?", (now - self.limits.ttl_seconds,)
            ).fetchall()
            for row in expired:
                owner = row["id"]
                active = jobs.execute(
                    """SELECT COUNT(*) FROM jobs WHERE json_extract(input, '$.owner')=?
                    AND state IN ('queued','preparing','rendering','verifying')""",
                    (owner,),
                ).fetchone()[0]
                if active:
                    continue
                shutil.rmtree(self.sessions_root / owner, ignore_errors=True)
                jobs.execute("DELETE FROM jobs WHERE json_extract(input, '$.owner')=?", (owner,))
                db.execute("DELETE FROM sessions WHERE id=?", (owner,))
                self.workspaces.pop(owner, None)

    def session(self, token):
        now = time.time()
        with self.lock, self.connect() as db:
            if token and len(token) <= 128:
                digest = hashlib.sha256(token.encode()).hexdigest()
                row = db.execute("SELECT * FROM sessions WHERE token_hash=?", (digest,)).fetchone()
                if row and row["last_seen"] >= now - self.limits.ttl_seconds:
                    db.execute("UPDATE sessions SET last_seen=? WHERE id=?", (now, row["id"]))
                    return row["id"], None
            count = db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            if count >= self.limits.sessions:
                raise HTTPException(503, "The free preview is busy. Please try later.")
            token, owner = secrets.token_urlsafe(32), uuid.uuid4().hex
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                (owner, hashlib.sha256(token.encode()).hexdigest(), now, now),
            )
            return owner, token

    def owned_job(self, owner, ident, include_input=False):
        if not ID.fullmatch(ident):
            raise HTTPException(404, "Job not found")
        try:
            result = self.jobs.get(ident, include_input=True)
        except KeyError:
            raise HTTPException(404, "Job not found") from None
        if result["input"].get("owner") != owner:
            raise HTTPException(404, "Job not found")
        envelope = result.pop("input")
        if include_input:
            result["input"] = envelope["request"]
        return result

    def storage_check(self, owner, reserve=0):
        workspace = self.workspace(owner)
        with self.jobs.connect() as db:
            active = db.execute("""SELECT json_extract(input, '$.owner') AS owner FROM jobs
                WHERE state IN ('queued','preparing','rendering','verifying')""").fetchall()
        render_reserve = self.limits.max_pixels * 24
        own_reserved = sum(row["owner"] == owner for row in active) * render_reserve
        if directory_size(workspace.root) + reserve + own_reserved > self.limits.session_bytes:
            raise HTTPException(429, "This session has reached its storage limit.")
        if directory_size(self.root) + reserve + len(active) * render_reserve > self.limits.total_bytes:
            raise HTTPException(503, "The free preview storage is full. Please try later.")

    def upload(self, owner, body):
        with self.lock:
            workspace = self.workspace(owner)
            if len(workspace.photos) >= self.limits.uploads_per_session:
                raise HTTPException(429, "This session has reached its photo limit.")
            with Image.open(io.BytesIO(body)) as image:
                if image.width * image.height > self.limits.max_pixels:
                    raise HTTPException(
                        413, "Use a smaller photo for this free preview (up to 1.5 megapixels)."
                    )
            # Original plus worst-case normalized RGBA PNG for the bounded decoder.
            self.storage_check(owner, len(body) + self.limits.max_pixels * 5)
            return workspace.add_photo(body)

    def submit(self, owner, payload, key):
        with self.lock:
            workspace = self.workspace(owner)
            workspace.validate_request(payload)
            with self.jobs.connect() as db:
                count = db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE json_extract(input, '$.owner')=?", (owner,)
                ).fetchone()[0]
                existing = (
                    db.execute("SELECT id FROM jobs WHERE request_key=?", (key,)).fetchone() if key else None
                )
            if existing:
                # Reconnecting to the same operation consumes no extra quota.
                # JobQueue still rejects reuse of the key with different inputs.
                result = self.jobs.submit({"owner": owner, "request": payload}, key)
                return self.owned_job(owner, result["id"])
            # Rendering stages several images. Reserve conservative disk headroom.
            self.storage_check(owner, self.limits.max_pixels * 24)
            if count >= self.limits.jobs_per_session and not existing:
                raise HTTPException(429, "This session has reached its map limit.")
            result = self.jobs.submit({"owner": owner, "request": payload}, key)
            return self.owned_job(owner, result["id"])

    def close(self):
        self.jobs.close()


def create_app(
    root=None, data=None, public_origin=None, limits=None, workspace_factory=MobileWorkspace, online=False
):
    root = root or os.environ.get("ATLAS_STORAGE", "/tmp/camera-atlas-service")
    data = data or Path(__file__).resolve().parents[2] / "examples/data"
    public_origin = (
        public_origin or os.environ.get("ATLAS_PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL")
    )
    if public_origin:
        parsed = urlsplit(public_origin)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
            raise ValueError("ATLAS_PUBLIC_ORIGIN must be an exact HTTPS origin")
        public_origin = f"https://{parsed.netloc}"
    limits = limits or Limits()
    assets = Path(__file__).parent / "web"

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = ServiceState(root, data, limits, workspace_factory)
        app.state.ingress = asyncio.Queue(maxsize=limits.ingress)
        for _ in range(limits.ingress):
            app.state.ingress.put_nowait(True)

        async def expire():
            while True:
                await run_in_threadpool(app.state.service.cleanup)
                await asyncio.sleep(60)

        cleanup_task = asyncio.create_task(expire())
        try:
            yield
        finally:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            await run_in_threadpool(app.state.service.close)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(ValueError)
    @app.exception_handler(OSError)
    @app.exception_handler(TypeError)
    async def value_error(request, exc):
        # Input validation details are useful, but never expose server paths.
        return JSONResponse(
            {"error": "Check the photo, place and selected area, then try again."}, status_code=400
        )

    @app.middleware("http")
    async def boundary(request, call_next):
        host = request.headers.get("host", "")
        expected_host = urlsplit(public_origin).netloc if public_origin else None
        if (expected_host and host != expected_host) or (
            not expected_host and host.split(":")[0] not in ("127.0.0.1", "localhost", "testserver")
        ):
            return JSONResponse({"error": "Unknown host"}, status_code=421)
        acquired = False
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            expected = public_origin or f"{request.url.scheme}://{host}"
            if request.headers.get("origin") != expected:
                return JSONResponse({"error": "Open the app before submitting a photo."}, status_code=403)
            try:
                app.state.ingress.get_nowait()
                acquired = True
            except asyncio.QueueEmpty:
                return JSONResponse({"error": "The preview is busy. Please retry."}, status_code=429)
        try:
            token = None
            if request.url.path.startswith(("/api/", "/files/")) and request.url.path != "/api/health":
                try:
                    owner, token = await run_in_threadpool(
                        app.state.service.session, request.cookies.get(COOKIE)
                    )
                    request.state.owner = owner
                except HTTPException as exc:
                    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "same-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
            )
            if token:
                response.set_cookie(
                    COOKIE,
                    token,
                    max_age=limits.ttl_seconds,
                    httponly=True,
                    secure=bool(public_origin),
                    samesite="lax",
                    path="/",
                )
            return response
        finally:
            if acquired:
                app.state.ingress.put_nowait(True)

    async def body(request):
        output = bytearray()
        async for chunk in request.stream():
            if len(output) + len(chunk) > MAX_BYTES:
                raise HTTPException(413, "Choose a file under 18 MB.")
            output.extend(chunk)
        if not output:
            raise HTTPException(400, "The request is empty.")
        return bytes(output)

    async def payload(request):
        value = json.loads(await body(request))
        if not isinstance(value, dict):
            raise HTTPException(400, "Invalid request")
        return value

    @app.get("/api/health")
    async def health():
        return {
            "application": "camera-atlas",
            "ready": True,
            "session_isolation": True,
            "global_places": online,
            "automatic_selection": False,
            "retention_hours": limits.ttl_seconds / 3600,
            "max_pixels": limits.max_pixels,
            "region_suggestions": True,
            "ephemeral": True,
        }

    @app.get("/api/places")
    async def places(request: Request, q: str = ""):
        workspace = app.state.service.workspace(request.state.owner)
        if q.strip() and hasattr(workspace, "search_places"):
            if len(q) > 160:
                raise HTTPException(400, "Use a shorter place name.")
            return await run_in_threadpool(workspace.search_places, q.strip())
        return [
            {"id": key, "name": item["name"], "label": item["label"], "aliases": item["aliases"]}
            for key, item in CATALOGUE.items()
        ]

    @app.post("/api/region-suggestion")
    async def suggestion(request: Request):
        import base64

        from .composition.suggestion import suggest_region

        values = await payload(request)
        workspace = app.state.service.workspace(request.state.owner)
        photo = workspace.photos.get(values.get("photo_id"))
        if photo is None:
            raise HTTPException(404, "Photo not found")

        def analyze():
            with Image.open(photo) as image:
                result = suggest_region(image)
            buffer = io.BytesIO()
            result.mask.save(buffer, "PNG")
            return {
                "mask": base64.b64encode(buffer.getvalue()).decode(),
                "confidence": result.confidence,
                "requires_review": result.requires_review,
                "method": result.method,
                "reason": result.reason,
            }

        return await run_in_threadpool(analyze)

    @app.post("/api/photo")
    async def photo(request: Request):
        value = await body(request)
        return await run_in_threadpool(app.state.service.upload, request.state.owner, value)

    @app.post("/api/sample")
    async def sample(request: Request):
        item = CATALOGUE.get((await payload(request)).get("place_id"))
        if not item:
            raise HTTPException(400, "Choose an available sample place.")
        return await run_in_threadpool(
            app.state.service.upload, request.state.owner, (Path(data) / item["photo"]).read_bytes()
        )

    @app.get("/api/photo/{ident}")
    async def photo_info(request: Request, ident: str):
        try:
            return app.state.service.workspace(request.state.owner).photo_info(ident)
        except KeyError:
            raise HTTPException(404, "Photo not found") from None

    @app.post("/api/jobs", status_code=202)
    async def submit(request: Request):
        key = request.headers.get("Idempotency-Key")
        if key and len(key) > 80:
            raise HTTPException(400, "Invalid request key")
        key = f"{request.state.owner}:{key}" if key else None
        return await run_in_threadpool(
            app.state.service.submit, request.state.owner, await payload(request), key
        )

    @app.get("/api/jobs/{ident}")
    async def job(request: Request, ident: str):
        return app.state.service.owned_job(request.state.owner, ident)

    @app.get("/api/jobs/{ident}/input")
    async def job_input(request: Request, ident: str):
        return app.state.service.owned_job(request.state.owner, ident, include_input=True)

    @app.post("/api/jobs/{ident}/retry", status_code=202)
    async def retry(request: Request, ident: str):
        await payload(request)
        service = app.state.service
        existing = service.owned_job(request.state.owner, ident)
        if existing["state"] != "failed":
            return existing
        if existing["attempts"] >= 3:
            raise HTTPException(429, "Retry limit reached. Please edit the selection.")
        service.storage_check(request.state.owner, limits.max_pixels * 24)
        service.jobs.retry(ident)
        return service.owned_job(request.state.owner, ident)

    @app.get("/files/{ident}/{name}")
    async def file(request: Request, ident: str, name: str):
        if name not in FILES or not ID.fullmatch(ident):
            raise HTTPException(404, "File not found")
        workspace = app.state.service.workspace(request.state.owner)
        path = (
            workspace.photos.get(ident)
            if name == "photo.png"
            else (workspace.results[ident] / name if ident in workspace.results else None)
        )
        if path is None or not path.is_file():
            raise HTTPException(404, "File not found")
        return FileResponse(path, filename=name if request.query_params.get("download") == "1" else None)

    @app.get("/")
    @app.get("/index.html")
    async def index():
        return FileResponse(assets / "index.html", media_type="text/html")

    @app.get("/{asset}")
    async def static(asset: str):
        if asset not in ("app.js", "style.css"):
            raise HTTPException(404, "Not found")
        return FileResponse(assets / asset)

    return app
