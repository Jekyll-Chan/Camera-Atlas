#!/usr/bin/env python3
"""Camera Atlas Skill v2: read-only doctor, isolated setup and verified public demo.

Standard library only. Compatible with Python 3.9+ for diagnosis; rendering/setup
requires Python 3.11+. Safe to execute unchanged from an Agensi temporary file.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_VERSION = "2.0.0"
CORE_MODULES = ("PIL", "numpy", "shapely", "pyproj", "pydantic", "typer", "httpx")
EXTRA_MODULES = {"terrain": ("rasterio", "contourpy"), "repair": ("cv2",), "heic": ("pillow_heif",)}
REPOSITORY = "https://github.com/Jekyll-Chan/Camera-Atlas"


class OnboardingError(ValueError):
    pass


def read_lock(path):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    revision = lock.get("revision", "")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise OnboardingError("Engine revision must be an immutable 40-character commit")
    expected = "https://codeload.github.com/Jekyll-Chan/Camera-Atlas/zip/" + revision
    if lock.get("source_url") != expected:
        raise OnboardingError("Only the pinned official Camera-Atlas source URL is allowed")
    if not re.fullmatch(r"[a-f0-9]{64}", lock.get("sha256", "")):
        raise OnboardingError("A verified source SHA256 is required")
    if lock.get("engine_version") != "0.1.0":
        raise OnboardingError("This adapter supports engine 0.1.0")
    for asset in lock.get("demo_files", []):
        rel = Path(asset["path"])
        if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 1:
            raise OnboardingError("Invalid demo asset path")
        expected = (
            f"https://raw.githubusercontent.com/Jekyll-Chan/Camera-Atlas/{revision}/examples/data/{rel.name}"
        )
        if asset.get("url") != expected or not re.fullmatch(r"[a-f0-9]{64}", asset.get("sha256", "")):
            raise OnboardingError("Demo source URL or checksum is invalid")
    return lock


def env_python(workspace):
    return workspace / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def probe(python):
    code = """import importlib.metadata, importlib.util, json, sys
try:
    version = importlib.metadata.version('camera-atlas')
except importlib.metadata.PackageNotFoundError:
    version = None
modules = %r
print(json.dumps({'python_version': list(sys.version_info[:3]), 'engine_version': version,
    'modules': {name: importlib.util.find_spec(name) is not None for name in modules}}))
""" % (list(CORE_MODULES) + [m for names in EXTRA_MODULES.values() for m in names],)
    try:
        result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise OnboardingError("The selected Python interpreter could not inspect its environment")
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise OnboardingError(
            "Python interpreter is unavailable; use planning mode or a code-enabled agent"
        ) from exc


def doctor(workspace, python=None):
    if python is not None:
        python = Path(python)
        if not python.is_file():
            raise OnboardingError("The explicitly selected interpreter does not exist")
    else:
        python = env_python(workspace)
        if not python.is_file():
            python = Path(sys.executable)
    report = probe(python)
    supported = report["python_version"] >= [3, 11, 0]
    missing = [name for name in CORE_MODULES if not report["modules"][name]]
    ready = supported and not missing and report["engine_version"] == "0.1.0"
    return {
        "skill_version": SKILL_VERSION,
        "engine_version": report["engine_version"],
        "python": str(python.absolute()),
        "python_version": report["python_version"],
        "ready": ready,
        "recommended_mode": "render" if ready else "setup" if supported else "plan",
        "missing_modules": missing,
        "optional_features": {
            name: all(report["modules"][module] for module in modules)
            for name, modules in EXTRA_MODULES.items()
        },
        "note": "Rendering also needs photo file access. Visual review needs image inspection tools. "
        "No shell or supported Python: deliver a clearly labeled plan, not an image.",
    }


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, target, expected_hash, max_bytes):
    request = urllib.request.Request(url, headers={"User-Agent": "CameraAtlasSkill/2.0.0"})
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=45) as response, target.open("wb") as handle:
            if response.geturl().split("/", 3)[2] not in ("codeload.github.com", "raw.githubusercontent.com"):
                raise OnboardingError("Download redirected away from the official source host")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise OnboardingError("Download exceeds the approved size limit")
                handle.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OnboardingError(
            "Public source download unavailable. Keep the photo unchanged and offer planning mode"
        ) from exc
    if digest(target) != expected_hash:
        raise OnboardingError("Source checksum mismatch; nothing will be installed or executed")


def run_checked(args, message, timeout=600):
    try:
        result = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OnboardingError(message) from exc
    if result.returncode:
        raise OnboardingError(message)
    return result


def setup(workspace, lock, extras=(), archive=None):
    if sys.version_info < (3, 11):
        raise OnboardingError(
            "Setup needs Python 3.11+. Switch to a supported interpreter or use planning mode"
        )
    marker = workspace / ".camera-atlas-env.json"
    python = env_python(workspace)
    if (workspace / ".venv").exists():
        if not marker.is_file():
            raise OnboardingError(
                "An unmanaged .venv already exists. Choose another workspace; it will not be changed"
            )
        state = json.loads(marker.read_text())
        if state.get("revision") != lock["revision"]:
            raise OnboardingError("Workspace belongs to another engine revision; choose a fresh workspace")
        report = doctor(workspace)
        if report["ready"] and all(report["optional_features"][x] for x in extras):
            return {**report, "status": "ready", "reused": True}
    if archive:
        archive = Path(archive)
        if not archive.is_file() or digest(archive) != lock["sha256"]:
            raise OnboardingError("Local source archive checksum mismatch; nothing was installed")
    with tempfile.TemporaryDirectory(prefix="camera-atlas-setup-") as directory:
        source = Path(directory) / "camera-atlas-source.zip"
        if archive:
            source = archive
        else:
            print(
                "Downloading verified public engine source; first setup also downloads Python dependencies.",
                file=sys.stderr,
            )
            download(lock["source_url"], source, lock["sha256"], 160 * 1024 * 1024)
        workspace.mkdir(parents=True, exist_ok=True)
        if not python.is_file():
            print("Preparing an isolated Camera Atlas environment…", file=sys.stderr)
            run_checked(
                [sys.executable, "-m", "venv", workspace / ".venv"],
                "Could not create the isolated environment",
            )
            marker.write_text(json.dumps({"revision": lock["revision"], "state": "preparing"}))
        package = str(source.resolve())
        if extras:
            package += "[" + ",".join(extras) + "]"
        print("Installing the pinned engine and required dependencies…", file=sys.stderr)
        run_checked(
            [python, "-m", "pip", "install", "--disable-pip-version-check", package],
            "Dependency installation failed. Try a supported network/code environment or use planning mode",
        )
        run_checked([python, "-m", "pip", "check"], "Installed dependencies have a compatibility conflict")
        marker.write_text(
            json.dumps(
                {
                    "revision": lock["revision"],
                    "engine_version": lock["engine_version"],
                    "source_sha256": lock["sha256"],
                    "state": "ready",
                },
                indent=2,
            )
        )
    report = doctor(workspace)
    if not report["ready"]:
        raise OnboardingError(
            "Setup finished but the engine is not ready; use planning mode and report the missing capability"
        )
    return {**report, "status": "ready", "reused": False, "revision": lock["revision"]}


def demo(workspace, lock, output=None):
    report = doctor(workspace)
    if not report["ready"]:
        raise OnboardingError("The engine is not ready. Run setup first or choose planning mode")
    names = {x["path"] for x in lock["demo_files"]}
    if not {"lake_photo.jpg", "lucerne.geojson", "photos.sources.json"} <= names:
        raise OnboardingError("The verified public demo manifest is incomplete")
    destination = workspace / "demo-inputs"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="camera-atlas-demo-") as directory:
        for asset in lock["demo_files"]:
            target = destination / asset["path"]
            if target.exists():
                if digest(target) != asset["sha256"]:
                    raise OnboardingError(
                        "Existing demo input differs; choose a fresh workspace rather than overwrite it"
                    )
                continue
            temp = Path(directory) / asset["path"]
            download(asset["url"], temp, asset["sha256"], 5 * 1024 * 1024)
            # Exclusive create: never replace an input if another process created it.
            with target.open("xb") as handle:
                handle.write(temp.read_bytes())
    output = (
        Path(output)
        if output
        else workspace / "results" / ("demo-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    )
    run_checked(
        [
            report["python"],
            "-m",
            "camera_atlas.cli",
            "render",
            "--input",
            destination / "lake_photo.jpg",
            "--geojson",
            destination / "lucerne.geojson",
            "--location",
            "Lake Lucerne",
            "--radius-km",
            "45",
            "--offline",
            "--svg",
            "--cache",
            workspace / ".cache",
            "--output",
            output,
        ],
        "Demo render failed. Check that the output is empty and that the environment has enough memory",
    )
    metadata = json.loads((output / "metadata.json").read_text())
    (output / "photo_sources.json").write_bytes((destination / "photos.sources.json").read_bytes())
    return {
        "status": "rendered",
        "skill_version": SKILL_VERSION,
        "engine_version": metadata["camera_atlas_version"],
        "final": str((output / "final.png").resolve()),
        "overlay": str((output / "map_overlay.png").resolve()),
        "provenance": str((output / "provenance.json").resolve()),
        "photo_sources": str((output / "photo_sources.json").absolute()),
        "quality": metadata["quality"],
        "warnings": metadata["warnings"],
        "note": "Public NASA aerial photograph + real Natural Earth overview lake. "
        "The location is a locality, not the astronaut's camera GPS. No private photo is uploaded.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Camera Atlas Skill v2: beginner onboarding helper")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "setup", "demo"):
        item = sub.add_parser(name)
        item.add_argument("--workspace", type=Path, default=Path.cwd() / "camera-atlas-work")
        if name == "doctor":
            item.add_argument("--python", type=Path)
        else:
            item.add_argument("--lock", type=Path, required=True, help="Fetched references/engine-lock.json")
        if name == "setup":
            item.add_argument("--extra", action="append", choices=sorted(EXTRA_MODULES), default=[])
            item.add_argument(
                "--source-archive", type=Path, help="Optional already-downloaded checksum-matching source ZIP"
            )
        if name == "demo":
            item.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        workspace = args.workspace.resolve()
        if args.command == "doctor":
            result = doctor(workspace, args.python)
        else:
            lock = read_lock(args.lock)
            if args.command == "setup":
                result = setup(workspace, lock, args.extra, args.source_archive)
            else:
                result = demo(workspace, lock, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OnboardingError, OSError, ValueError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "skill_version": SKILL_VERSION,
                    "recommended_mode": "plan",
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
