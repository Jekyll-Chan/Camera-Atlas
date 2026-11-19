import base64
import io
import json
import sqlite3
import threading
import time

import numpy as np
import pytest
from PIL import Image, ImageDraw

from camera_atlas.jobs import JobQueue
from camera_atlas.mobile import MobileWorkspace


def finished(jobs, ident):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        job = jobs.get(ident)
        if job["state"] in ("ready", "failed"):
            return job
        time.sleep(0.02)
    pytest.fail("Worker did not finish within the test deadline")


def test_real_render_and_inputs_survive_restart(tmp_path, data_dir, photo):
    directory = tmp_path / "workspace"
    workspace = MobileWorkspace(directory, data_dir)
    uploaded = workspace.add_photo(photo.read_bytes())
    mask = Image.new("L", (1000, 700))
    ImageDraw.Draw(mask).rectangle((0, 0, 999, 280), fill=255)
    data = io.BytesIO()
    mask.save(data, "PNG")
    request = {
        "photo_id": uploaded["id"],
        "place_id": "san-francisco",
        "confirmed": True,
        "mask": base64.b64encode(data.getvalue()).decode(),
        "opacity": 0.7,
    }
    with JobQueue(directory, workspace.create_render) as jobs:
        ident = jobs.submit(request, "one-upload")["id"]
        job = finished(jobs, ident)
        assert job["state"] == "ready", job
        assert job["result"]["review_required"] is True
    restarted = MobileWorkspace(directory, data_dir)
    with JobQueue(directory, restarted.create_render) as jobs:
        recovered = jobs.get(ident, include_input=True)
        assert recovered["state"] == "ready"
        assert recovered["attempts"] == 1
        assert recovered["input"] == request
        assert jobs.submit(request, "one-upload")["id"] == ident
        assert restarted.photo_info(uploaded["id"]) == uploaded
        result = restarted.results[recovered["result"]["id"]]
        with Image.open(result / "final.png") as image, Image.open(restarted.photos[uploaded["id"]]) as base:
            assert image.size == base.size
            assert np.array_equal(np.asarray(image)[281:], np.asarray(base)[281:])
        assert (directory / (uploaded["id"] + ".input")).read_bytes() == photo.read_bytes()


def test_failure_retry_reuses_snapshot_and_hides_internal_error(tmp_path):
    requests = []

    def processor(request, progress):
        requests.append(request)
        progress("rendering")
        if len(requests) == 1:
            raise RuntimeError("provider credential and private filesystem path")
        progress("verifying")
        return {"final": "verified.png"}

    with JobQueue(tmp_path, processor) as jobs:
        ident = jobs.submit({"photo_id": "unchanged"})["id"]
        failure = finished(jobs, ident)
        assert failure["state"] == "failed"
        assert failure["result"] is None
        assert "credential" not in json.dumps(failure)
        jobs.retry(ident)
        ready = finished(jobs, ident)
        assert ready["state"] == "ready" and ready["attempts"] == 2
        assert ready["error"] is None
        assert requests == [{"photo_id": "unchanged"}] * 2


def test_bounded_queue_idempotency_and_single_owner(tmp_path):
    gate, started = threading.Event(), threading.Event()

    def processor(request, progress):
        started.set()
        assert gate.wait(5)
        return request

    with JobQueue(tmp_path, processor, capacity=1) as jobs:
        try:
            ident = jobs.submit({"value": 1}, "same-request")["id"]
            assert started.wait(5)
            assert jobs.submit({"value": 1}, "same-request")["id"] == ident
            with pytest.raises(ValueError, match="different inputs"):
                jobs.submit({"value": 2}, "same-request")
            with pytest.raises(ValueError, match="queue is full"):
                jobs.submit({"value": 2}, "new-request")
            with pytest.raises(ValueError, match="already has"):
                JobQueue(tmp_path, processor)
        finally:
            gate.set()
        assert finished(jobs, ident)["state"] == "ready"


def test_interrupted_job_needs_explicit_retry(tmp_path):
    with JobQueue(tmp_path, lambda request, progress: request) as jobs:
        ident = jobs.submit({"original": True})["id"]
        assert finished(jobs, ident)["state"] == "ready"
    # Simulate persisted state at the instant a worker was killed.
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as db:
        db.execute("UPDATE jobs SET state='rendering', result=NULL WHERE id=?", (ident,))
    with JobQueue(tmp_path, lambda request, progress: request) as restarted:
        job = restarted.get(ident, include_input=True)
        assert job["state"] == "failed"
        assert job["error"]["code"] == "interrupted"
        assert job["result"] is None
        assert job["input"] == {"original": True}
        restarted.retry(ident)
        assert finished(restarted, ident)["result"] == {"original": True}


@pytest.mark.parametrize("opacity", [float("nan"), float("inf"), 0.01, 2])
def test_invalid_ink_does_not_create_render_files(tmp_path, photo, data_dir, opacity):
    workspace = MobileWorkspace(tmp_path / "workspace", data_dir)
    uploaded = workspace.add_photo(photo.read_bytes())
    buffer = io.BytesIO()
    Image.new("L", (1000, 700), 255).save(buffer, "PNG")
    with pytest.raises(ValueError, match="ink"):
        workspace.validate_request(
            {
                "photo_id": uploaded["id"],
                "place_id": "san-francisco",
                "confirmed": True,
                "opacity": opacity,
                "mask": base64.b64encode(buffer.getvalue()).decode(),
            }
        )
    assert not workspace.results
