"""Behavioral checks for the standalone, temporary-delivery adapter."""

import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/camera-atlas"


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def helper():
    return load_module(SKILL / "scripts/onboard.py")


def test_doctor_is_read_only_and_preserves_venv_path(helper, tmp_path):
    workspace = tmp_path / "absent"
    report = helper.doctor(workspace, Path(sys.executable))
    assert report["ready"] and report["recommended_mode"] == "render"
    assert report["skill_version"] == "2.0.0" and report["engine_version"] == "0.1.0"
    assert report["python"] == str(Path(sys.executable).absolute())
    assert not workspace.exists()


def test_doctor_rejects_missing_explicit_interpreter(helper, tmp_path):
    with pytest.raises(ValueError, match="interpreter"):
        helper.doctor(tmp_path, tmp_path / "does-not-exist")


def test_probe_failure_offers_honest_planning(helper, tmp_path):
    with pytest.raises(ValueError, match="planning"):
        helper.probe(tmp_path / "missing-python")


def test_managed_environment_is_not_an_arbitrary_venv(helper, tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "keep.txt").write_text("preserve me")
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    with pytest.raises(ValueError, match="unmanaged"):
        helper.setup(tmp_path, lock)
    assert (tmp_path / ".venv" / "keep.txt").read_text() == "preserve me"


def test_source_checksum_failure_before_install(helper, tmp_path):
    source = tmp_path / "not-official.zip"
    source.write_bytes(b"not the official source")
    workspace = tmp_path / "no-install"
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    with pytest.raises(ValueError, match="checksum"):
        helper.setup(workspace, lock, archive=source)
    assert not workspace.exists()


@pytest.mark.parametrize(
    "change",
    [{"source_url": "https://other.example/engine.zip"}, {"revision": "main"}, {"sha256": "unverified"}],
)
def test_lock_refuses_untrusted_source(helper, tmp_path, change):
    lock = json.loads((SKILL / "references/engine-lock.json").read_text())
    lock.update(change)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(lock))
    with pytest.raises(ValueError):
        helper.read_lock(path)


def test_demo_assets_match_real_committed_sources(helper):
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    for asset in lock["demo_files"]:
        assert (
            hashlib.sha256((ROOT / "examples/data" / asset["path"]).read_bytes()).hexdigest()
            == asset["sha256"]
        )


def test_temporary_script_has_no_repository_path_assumption(tmp_path):
    script = tmp_path / "arbitrary-name.py"
    script.write_bytes((SKILL / "scripts/onboard.py").read_bytes())
    workspace = tmp_path / "not-created"
    result = subprocess.run(
        [sys.executable, str(script), "doctor", "--workspace", str(workspace)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["skill_version"] == "2.0.0"
    assert not workspace.exists()


def test_skill_package_is_small_text_only_and_reproducible(tmp_path):
    builder = load_module(ROOT / "scripts/package_agensi.py")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    info = builder.build(first)
    builder.build(second)
    assert first.read_bytes() == second.read_bytes()
    assert info["bytes"] < 5 * 1024 * 1024
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert "camera-atlas/SKILL.md" in names
        assert "camera-atlas/references/START-HERE.en.md" in names
        assert "camera-atlas/references/START-HERE.zh-CN.md" in names
        manifest = json.loads(archive.read("camera-atlas/package-manifest.json"))
        assert manifest["price"] == "Free" and not manifest["platform_tested"]
        for name, data_hash in manifest["files"].items():
            content = archive.read("camera-atlas/" + name)
            content.decode("utf-8")
            assert hashlib.sha256(content).hexdigest() == data_hash
        assert not any(name.endswith((".jpg", ".png", ".tif", ".whl")) for name in names)
