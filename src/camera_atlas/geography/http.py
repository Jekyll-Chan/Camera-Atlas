"""Bounded HTTP retries, persistent cache and cross-process rate limiting."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import httpx


class ProviderError(RuntimeError):
    pass


class CachedHTTP:
    def __init__(self, cache: Path, offline=False, user_agent="CameraAtlas/0.1", transport=None):
        cache.mkdir(parents=True, exist_ok=True)
        self.db = cache / "http.sqlite3"
        self.offline = offline
        self.client = httpx.Client(timeout=45, headers={"User-Agent": user_agent}, transport=transport)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, stored REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS limits (host TEXT PRIMARY KEY, stamp REAL)")

    def connect(self):
        return sqlite3.connect(self.db, timeout=30)

    def close(self):
        self.client.close()

    def _reserve(self, host, interval):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT stamp FROM limits WHERE host=?", (host,)).fetchone()
            delay = max(0, (row[0] if row else 0) + interval - time.time())
            db.execute("INSERT OR REPLACE INTO limits VALUES (?,?)", (host, time.time() + delay))
        if delay:
            time.sleep(delay)

    def json(self, url, params=None, data=None, interval=1.1):
        key = hashlib.sha256(json.dumps([url, params, data], sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
        # Immutable cache: acquisition time is retained inside provider payload metadata.
        if row:
            return json.loads(row[0])
        if self.offline:
            raise ProviderError("Offline cache miss")
        error = ""
        for attempt in range(3):
            self._reserve(httpx.URL(url).host, interval)
            try:
                response = self.client.request("POST" if data else "GET", url, params=params, data=data)
                if response.status_code not in (429, 500, 502, 503, 504):
                    response.raise_for_status()
                    payload = {"body": response.json(), "retrieved_at": time.time()}
                    with self.connect() as db:
                        db.execute(
                            "INSERT OR REPLACE INTO cache VALUES (?,?,?)",
                            (key, json.dumps(payload), time.time()),
                        )
                    return payload
                error = f"HTTP {response.status_code}"
                retry = response.headers.get("Retry-After", "0")
                try:
                    wait = float(retry)
                except ValueError:
                    wait = 0
                if wait > 30:
                    raise ProviderError("Server asks for a later retry; try again later")
            except (httpx.HTTPError, ValueError) as exc:
                error = str(exc)
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    break
                wait = 0
            if attempt < 2:
                time.sleep(max(2**attempt, wait))
        raise ProviderError(f"Geographic request failed: {error}")
