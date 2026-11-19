import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/package_agent_kit.py"
SPEC = importlib.util.spec_from_file_location("package_agent_kit", SCRIPT)
packager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packager)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    for name in packager.TOP_LEVEL:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Public project text", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname="camera-atlas"\nversion="0.1.0"\n')
    for name in ("__init__.py", "cli.py", "config.py", "pipeline.py"):
        path = root / "src/camera_atlas" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Public engine source\n")
    for name in ("index.html", "app.js", "style.css"):
        path = root / "src/camera_atlas/web" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Public web source")
    skill = root / ".agents/skills/camera-atlas/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: camera-atlas\ndescription: Render photographs\n---\n")
    for name in packager.SAMPLES:
        path = root / "examples/data" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Public example content")
    return root


def test_deterministic_complete_archive_and_hashes(source, tmp_path):
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    result = packager.build(first, source)
    packager.build(second, source)
    assert first.read_bytes() == second.read_bytes()
    assert result["sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert all(name.startswith("Camera-Atlas/") and ".." not in Path(name).parts for name in names)
        manifest = json.loads(archive.read("Camera-Atlas/kit-manifest.json"))
        assert manifest["publication_not_asserted_by_builder"] is True
        assert manifest["publication_status_reference"] in manifest["files"]
        assert len(manifest["files"]) == len(names) - 1
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(archive.read("Camera-Atlas/" + name)).hexdigest() == digest
        extracted = tmp_path / "unpacked"
        archive.extractall(extracted)
    assert (extracted / "Camera-Atlas" / manifest["entrypoint"]).is_file()
    assert (extracted / "Camera-Atlas/pyproject.toml").is_file()
    assert (extracted / "Camera-Atlas/src/camera_atlas/pipeline.py").is_file()
    for name in ("EBGaramond.ttf", "OFL.txt", "source.json"):
        assert (extracted / "Camera-Atlas/src/camera_atlas/assets/fonts" / name).is_file()


def test_runtime_private_and_unlisted_samples_are_excluded(source, tmp_path):
    unwanted = (
        ".env",
        "private/photo.jpg",
        "work/jobs.sqlite3",
        "src/camera_atlas/__pycache__/pipeline.pyc",
        "src/camera_atlas/private/credentials.py",
        "src/camera_atlas/.secrets.py",
        ".agents/skills/camera-atlas/private/token.json",
        ".agents/skills/camera-atlas/.env.json",
        "examples/data/alps_dem.tif",
        "examples/data/private-photo.jpg",
    )
    for name in unwanted:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("PRIVATE SENTINEL DO NOT INCLUDE")
    output = tmp_path / "kit.zip"
    packager.build(output, source)
    with zipfile.ZipFile(output) as archive:
        assert not any(name.removeprefix("Camera-Atlas/") in unwanted for name in archive.namelist())
        assert all(b"PRIVATE SENTINEL" not in archive.read(name) for name in archive.namelist())


def test_missing_required_guide_preserves_previous_deliverable(source, tmp_path):
    output = tmp_path / "kit.zip"
    output.write_bytes(b"previous deliverable")
    (source / "docs/Agent-Quickstart.md").unlink()
    with pytest.raises(ValueError, match="Required kit file is missing"):
        packager.build(output, source)
    assert output.read_bytes() == b"previous deliverable"


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_symbolic_links_cannot_import_external_data(source, tmp_path, kind):
    secret = tmp_path / "external"
    secret.mkdir()
    (secret / "credentials.py").write_text("external private data")
    if kind == "file":
        (source / "src/camera_atlas/leak.py").symlink_to(secret / "credentials.py")
    else:
        (source / "src/camera_atlas/geography").symlink_to(secret, target_is_directory=True)
    with pytest.raises(ValueError, match="Symbolic links"):
        packager.build(tmp_path / "kit.zip", source)
