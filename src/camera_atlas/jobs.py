"""Durable, bounded, single-process job runner for the local application.

This is not a public multi-tenant service. One owner per directory; the HTTP
adapter remains loopback-only until session isolation and hosting are added.
"""

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

ACTIVE = ("queued", "preparing", "rendering", "verifying")


class JobQueue:
    def __init__(self, root, processor, capacity=8):
        # macOS/Linux local runner. A deployment adapter must own its worker lease.
        import fcntl

        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.owner = (self.root / "worker.lock").open("a")
        try:
            fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.owner.close()
            raise ValueError("This workspace already has a running worker.") from None
        self.processor = processor
        self.capacity = capacity
        self.condition = threading.Condition()
        self.stopping = False
        self.database = self.root / "jobs.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, request_key TEXT UNIQUE, digest TEXT NOT NULL,
                input TEXT NOT NULL, state TEXT NOT NULL, result TEXT, error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL
            )""")
            # Never silently claim an interrupted render finished, or rerun a paid
            # external operation. Explicit retry preserves the original input.
            db.execute(
                """UPDATE jobs SET state='failed', error=?, updated=?
                WHERE state IN ('preparing', 'rendering', 'verifying')""",
                (
                    json.dumps({"code": "interrupted", "message": "Processing stopped. Retry to continue."}),
                    time.time(),
                ),
            )
        self.thread = threading.Thread(target=self.run, name="camera-atlas-worker", daemon=True)
        self.thread.start()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def public(row):
        return {
            "id": row["id"],
            "state": row["state"],
            "attempts": row["attempts"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": json.loads(row["error"]) if row["error"] else None,
            "created_at": row["created"],
            "updated_at": row["updated"],
        }

    def get(self, ident, include_input=False):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError("Job not found")
        result = self.public(row)
        if include_input:
            result["input"] = json.loads(row["input"])
        return result

    def check_capacity(self, db):
        count = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE state IN ('queued','preparing','rendering','verifying')"
        ).fetchone()[0]
        if count >= self.capacity:
            raise ValueError("The queue is full. Please try again shortly.")

    def submit(self, request, request_key=None):
        serialized = json.dumps(request, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        if request_key is not None and (not isinstance(request_key, str) or not 1 <= len(request_key) <= 128):
            raise ValueError("Invalid request key")
        with self.condition, self.connect() as db:
            if self.stopping:
                raise ValueError("The worker is shutting down. Please try again shortly.")
            if request_key:
                existing = db.execute("SELECT * FROM jobs WHERE request_key=?", (request_key,)).fetchone()
                if existing:
                    if existing["digest"] != digest:
                        raise ValueError("This request key belongs to different inputs.")
                    return self.public(existing)
            self.check_capacity(db)
            ident, timestamp = uuid.uuid4().hex, time.time()
            db.execute(
                """INSERT INTO jobs
                (id, request_key, digest, input, state, created, updated)
                VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
                (ident, request_key, digest, serialized, timestamp, timestamp),
            )
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            self.condition.notify()
            return self.public(row)

    def retry(self, ident):
        with self.condition, self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if row is None:
                raise KeyError("Job not found")
            if row["state"] != "failed":
                return self.public(row)
            self.check_capacity(db)
            db.execute(
                "UPDATE jobs SET state='queued', error=NULL, result=NULL, updated=? WHERE id=?",
                (time.time(), ident),
            )
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            self.condition.notify()
            return self.public(row)

    def update(self, ident, state, result=None, error=None):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET state=?, result=?, error=?, updated=? WHERE id=?",
                (
                    state,
                    json.dumps(result) if result is not None else None,
                    json.dumps(error) if error is not None else None,
                    time.time(),
                    ident,
                ),
            )

    def run(self):
        while True:
            with self.condition:
                if self.stopping:
                    return
                with self.connect() as db:
                    row = db.execute(
                        "SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1"
                    ).fetchone()
                    if row:
                        db.execute(
                            "UPDATE jobs SET state='preparing', attempts=attempts+1, updated=? WHERE id=?",
                            (time.time(), row["id"]),
                        )
                if row is None:
                    self.condition.wait(timeout=1)
                    continue
            ident = row["id"]

            def progress(stage):
                if stage not in ("preparing", "rendering", "verifying"):
                    raise ValueError("Unknown processing stage")
                self.update(ident, stage)

            try:
                result = self.processor(json.loads(row["input"]), progress)
                self.update(ident, "ready", result=result)
            except Exception:
                # Do not expose local paths, credentials or provider responses.
                self.update(
                    ident,
                    "failed",
                    error={
                        "code": "render_failed",
                        "message": "Could not finish this map. Retry or edit the selection.",
                    },
                )

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify()
        self.thread.join()  # Finish the current local render; queued work remains durable.
        self.owner.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
