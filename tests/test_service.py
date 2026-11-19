import base64
import io
import threading
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from camera_atlas.mobile import MobileWorkspace
from camera_atlas.service import COOKIE, Limits, create_app

ORIGIN = "https://atlas.test"


def client(app):
    return TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})


def render_input(photo_id):
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle((0, 0, 999, 280), fill=255)
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    return {
        "photo_id": photo_id,
        "place_id": "san-francisco",
        "confirmed": True,
        "mask": base64.b64encode(buffer.getvalue()).decode(),
        "opacity": 0.7,
    }


def wait_result(browser, ident):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = browser.get(f"/api/jobs/{ident}")
        assert response.status_code == 200, response.text
        result = response.json()
        if result["state"] in ("ready", "failed"):
            return result
        time.sleep(0.02)
    pytest.fail("Job did not finish")


def test_anonymous_render_download_and_session_isolation(tmp_path, data_dir, photo):
    app = create_app(tmp_path, data_dir, ORIGIN, workspace_factory=MobileWorkspace)
    with client(app) as owner:
        bootstrap = owner.get("/api/places")
        cookie = bootstrap.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        uploaded = owner.post("/api/photo", content=photo.read_bytes()).json()
        submitted = owner.post(
            "/api/jobs", json=render_input(uploaded["id"]), headers={"Idempotency-Key": "one-photo"}
        )
        assert submitted.status_code == 202, submitted.text
        ident = submitted.json()["id"]
        ready = wait_result(owner, ident)
        assert ready["state"] == "ready", ready
        assert "input" not in ready
        download = owner.get(ready["result"]["final"] + "?download=1")
        assert download.status_code == 200 and "attachment" in download.headers["content-disposition"]
        with Image.open(io.BytesIO(download.content)) as result:
            assert result.size == (1000, 700)
        duplicate = owner.post(
            "/api/jobs", json=render_input(uploaded["id"]), headers={"Idempotency-Key": "one-photo"}
        )
        assert duplicate.json()["id"] == ident
        saved_input = owner.get(f"/api/jobs/{ident}/input").json()["input"]
        assert saved_input["photo_id"] == uploaded["id"] and "owner" not in saved_input
        with client_without_lifespan(app) as stranger:
            assert stranger.get(uploaded["url"]).status_code == 404
            assert stranger.get(f"/api/photo/{uploaded['id']}").status_code == 404
            assert stranger.get(f"/api/jobs/{ident}").status_code == 404
            assert stranger.get(f"/api/jobs/{ident}/input").status_code == 404
            assert stranger.post(f"/api/jobs/{ident}/retry", json={}).status_code == 404
            assert stranger.get(ready["result"]["final"]).status_code == 404
        assert owner.get(f"/files/{uploaded['id']}/photo.input").status_code == 404


class client_without_lifespan:
    """Separate cookie jar without starting a second worker on the same app."""

    def __init__(self, app):
        self.browser = client(app)

    def __enter__(self):
        return self.browser

    def __exit__(self, *args):
        self.browser.close()


def test_bad_origin_unknown_host_and_invalid_image(tmp_path, data_dir):
    app = create_app(tmp_path, data_dir, ORIGIN)
    with client(app) as browser:
        assert (
            browser.post(
                "/api/sample", json={"place_id": "lucerne"}, headers={"Origin": "https://attacker.test"}
            ).status_code
            == 403
        )
        assert browser.get("/api/places", headers={"Host": "attacker.test"}).status_code == 421
        assert browser.post("/api/photo", content=b"not an image").status_code == 400
        assert browser.post("/api/jobs", json=[]).status_code == 400


def test_upload_and_session_caps(tmp_path, data_dir, photo):
    app = create_app(tmp_path, data_dir, ORIGIN, Limits(sessions=1))
    with client(app) as browser:
        assert browser.post("/api/photo", content=photo.read_bytes()).status_code == 200
        assert browser.post("/api/photo", content=photo.read_bytes()).status_code == 429
        with client_without_lifespan(app) as stranger:
            assert stranger.get("/api/places").status_code == 503


def test_pixel_limit_before_normalization(tmp_path, data_dir, photo):
    app = create_app(tmp_path, data_dir, ORIGIN, Limits(max_pixels=1000))
    with client(app) as browser:
        assert browser.post("/api/photo", content=photo.read_bytes()).status_code == 413
        assert not list((tmp_path / "sessions").rglob("*.input"))


def test_expiry_removes_private_files_and_jobs(tmp_path, data_dir, photo):
    app = create_app(tmp_path, data_dir, ORIGIN)
    with client(app) as browser:
        uploaded = browser.post("/api/photo", content=photo.read_bytes()).json()
        app.state.service.cleanup(time.time() + 3700)
        assert not list((tmp_path / "sessions").rglob("*.input"))
        assert browser.get(uploaded["url"]).status_code == 404


def test_expiry_preserves_running_job_inputs(tmp_path, data_dir, photo):
    started, release = threading.Event(), threading.Event()

    class SlowWorkspace(MobileWorkspace):
        def create_render(self, request, progress=None):
            started.set()
            assert release.wait(10)
            return super().create_render(request, progress)

    app = create_app(tmp_path, data_dir, ORIGIN, workspace_factory=SlowWorkspace)
    with client(app) as browser:
        uploaded = browser.post("/api/photo", content=photo.read_bytes()).json()
        ident = browser.post(
            "/api/jobs", json=render_input(uploaded["id"]), headers={"Idempotency-Key": "active-request"}
        ).json()["id"]
        try:
            assert started.wait(5)
            duplicate = browser.post(
                "/api/jobs", json=render_input(uploaded["id"]), headers={"Idempotency-Key": "active-request"}
            )
            assert duplicate.status_code == 202 and duplicate.json()["id"] == ident
            assert browser.post(f"/api/jobs/{ident}/retry", json={}).status_code == 202
            app.state.service.cleanup(time.time() + 3700)
            assert list((tmp_path / "sessions").rglob("*.input"))
            assert browser.get(uploaded["url"]).status_code == 200
        finally:
            release.set()
        assert wait_result(browser, ident)["state"] == "ready"


def test_failed_job_retry_and_restart_authentication(tmp_path, data_dir, photo):
    class FailsOnce(MobileWorkspace):
        calls = 0

        def create_render(self, request, progress=None):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("private detail")
            return super().create_render(request, progress)

    app = create_app(tmp_path, data_dir, ORIGIN, workspace_factory=FailsOnce)
    with client(app) as browser:
        uploaded = browser.post("/api/photo", content=photo.read_bytes()).json()
        ident = browser.post("/api/jobs", json=render_input(uploaded["id"])).json()["id"]
        failed = wait_result(browser, ident)
        assert failed["state"] == "failed" and "private detail" not in str(failed)
        assert browser.post(f"/api/jobs/{ident}/retry", json={}).status_code == 202
        assert wait_result(browser, ident)["state"] == "ready"
        token = browser.cookies.get(COOKIE)
    restarted = create_app(tmp_path, data_dir, ORIGIN, workspace_factory=MobileWorkspace)
    with client(restarted) as browser:
        browser.cookies.set(COOKIE, token)
        response = browser.get(f"/api/jobs/{ident}")
        assert response.status_code == 200 and response.json()["state"] == "ready"
        assert browser.get(response.json()["result"]["final"]).status_code == 200
