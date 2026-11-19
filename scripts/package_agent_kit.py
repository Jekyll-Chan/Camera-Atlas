"""Package the current local renderer and its skill for a user's own coding agent.

This direct-download source kit is separate from the text-only Agensi adapter.
It contains no credentials, user photographs, caches, environments or job data.
"""

import argparse
import hashlib
import json
import os
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "Camera-Atlas"
VERSION = "2.2.0"
SOURCE_DIRS = ("", "cartography", "composition", "geography", "image", "validation")
TOP_LEVEL = (
    "pyproject.toml",
    "LICENSE",
    "AGENTS.md",
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "requirements-tested.txt",
    "src/camera_atlas/assets/fonts/EBGaramond.ttf",
    "src/camera_atlas/assets/fonts/OFL.txt",
    "src/camera_atlas/assets/fonts/source.json",
    "examples/README.md",
    "examples/data/TERRAIN-ATTRIBUTION.md",
    "docs/Agent-Quickstart.md",
    "docs/Architecture.md",
    "docs/CLI-Reference.md",
    "docs/Accuracy-and-Provenance.md",
    "docs/Agensi-v2.md",
    "docs/Skill-Usage.md",
    "docs/Geographic-Data-Providers.md",
    "docs/Release.md",
    "docs/Troubleshooting.md",
    "docs/Validation.md",
    "docs/Acceptance.md",
    "docs/Region-Fill.md",
    "docs/Mobile-Experience.md",
    "docs/Kernel-Pipeline.md",
    "docs/Public-Service.md",
    "docs/Free-Hosting-Policy.md",
    "docs/Agensi-Live-Validation.md",
    "docs/Rendering-Pipeline.md",
    "docs/Design-System.md",
)
SAMPLES = (
    "city_photo.jpg",
    "lake_photo.jpg",
    "san_francisco.geojson",
    "lucerne.geojson",
    "photos.sources.json",
)
SKILL_EXTENSIONS = {".md", ".py", ".json", ".yaml", ".yml"}
EXCLUDED_PARTS = {"private", "work", "cache", "outputs", "dist", "__pycache__", "node_modules"}


def collect(root):
    root = Path(root).resolve()
    files = {}

    def add(path):
        relative = path.relative_to(root)
        if any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ValueError(f"Symbolic links are not allowed in the kit: {relative}")
        if not path.is_file():
            raise ValueError(f"Required kit file is missing: {relative}")
        files[relative.as_posix()] = path.read_bytes()

    for name in TOP_LEVEL:
        add(root / name)
    source = root / "src/camera_atlas"
    for folder in SOURCE_DIRS:
        for path in sorted((source / folder).glob("*.py")):
            if not path.name.startswith("."):
                add(path)
    for name in ("index.html", "app.js", "style.css"):
        add(source / "web" / name)
    for required in ("__init__.py", "cli.py", "config.py", "pipeline.py"):
        if f"src/camera_atlas/{required}" not in files:
            raise ValueError(f"Required renderer file is missing: {required}")
    skill = root / ".agents/skills/camera-atlas"
    for path in sorted(skill.rglob("*")):
        relative = path.relative_to(skill)
        if any(part in EXCLUDED_PARTS or part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not allowed in the kit: {relative}")
        if path.is_file() and path.suffix in SKILL_EXTENSIONS:
            path.read_bytes().decode("utf-8")
            add(path)
    if ".agents/skills/camera-atlas/SKILL.md" not in files:
        raise ValueError("Required SKILL.md is missing")
    for name in SAMPLES:
        add(root / "examples/data" / name)
    return files


def build(output, root=ROOT):
    files = collect(root)
    metadata = tomllib.loads(files["pyproject.toml"].decode())
    manifest = {
        "schema_version": "1.0",
        "kit_version": VERSION,
        "engine_version": metadata["project"]["version"],
        "publication_not_asserted_by_builder": True,
        "publication_status_reference": "docs/Agensi-Live-Validation.md",
        "distribution": "Direct-download source kit; not the Agensi text-only package",
        "entrypoint": "docs/Agent-Quickstart.md",
        "not_bundled": [
            "DEM rasters",
            "Generated example gallery and full-resolution example outputs",
            "Developer tests, CI and example reproduction scripts",
            "Private inputs, credentials, environments, caches and runtime data",
        ],
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["kit-manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Validate all inputs before touching a prior deliverable. Atomically publish
    # the new archive only once every member has been written successfully.
    with tempfile.NamedTemporaryFile(
        prefix=".agent-kit-", suffix=".zip", dir=output.parent, delete=False
    ) as tmp:
        temporary = Path(tmp.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(f"{PREFIX}/{name}", date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                info.create_system = 3
                archive.writestr(info, data)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "output": str(output),
        "kit_version": VERSION,
        "files": len(files),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "status": "built; hosting and marketplace status must be verified separately",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Camera-Atlas-Agent-Kit-v2.2.0.zip")
    print(json.dumps(build(parser.parse_args().output), indent=2))
