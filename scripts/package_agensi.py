"""Build a deterministic, text-only Agensi Skill v2 package."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/camera-atlas"
ALLOWED = {".md", ".py", ".json", ".yaml", ".yml"}


def build(output):
    files = {}
    for path in sorted(SKILL.rglob("*")):
        if not path.is_file() or path.suffix not in ALLOWED or "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError("Skill package must not contain symbolic links")
        data = path.read_bytes()
        data.decode("utf-8")
        files[path.relative_to(SKILL).as_posix()] = data
    if "SKILL.md" not in files:
        raise ValueError("Missing skill entrypoint")
    for name in ("lucerne.geojson", "photos.sources.json"):
        data = (ROOT / "examples/data" / name).read_bytes()
        data.decode("utf-8")
        # The MCP uploader validates filename extensions, not only UTF-8 content.
        target = "lucerne.json" if name == "lucerne.geojson" else name
        files[f"sample/{target}"] = data
    files["LICENSE.txt"] = (ROOT / "LICENSE").read_bytes()
    lock = json.loads(files["references/engine-lock.json"])
    region_pinned = all(
        lock.get("capabilities", {}).get(name) is True
        for name in ("agent_bridge", "region_fill", "online_maps")
    )
    manifest = {
        "skill_version": "2.2.1",
        "engine_version": "0.1.0",
        "price": "Free",
        "platform_tested": False,
        "verification_scope": "Building this package does not establish live Agensi execution.",
        "region_fill_release_pinned": region_pinned,
        "renderer_revision": lock["revision"],
        "region_fill_requirement": "Pinned current renderer with verified online_ready capability",
        "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()},
    }
    files["package-manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    if len(files) > 100 or output.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Package exceeds the documented agent-upload limit")
    return {
        "output": str(output),
        "skill_version": "2.2.1",
        "files": len(files),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "status": "built; marketplace review and live execution must be verified separately",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Camera-Atlas-Skill-v2.2.1.zip")
    print(json.dumps(build(parser.parse_args().output), indent=2))
