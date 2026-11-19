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
    assert report["online_ready"] and report["offline_ready"] and report["region_fill_ready"]
    assert report["agent_bridge_supported"] and report["optional_features"]["maps"]
    assert not report["unavailable_capabilities"]
    assert report["skill_version"] == "2.2.0" and report["engine_version"] == "0.1.0"
    assert report["python"] == str(Path(sys.executable).absolute())
    assert not workspace.exists()


def probe_result(helper, *, region=True, bridge=True, maps=True):
    modules = {name: True for name in helper.CORE_MODULES}
    modules.update({name: True for names in helper.EXTRA_MODULES.values() for name in names})
    modules["mapbox_vector_tile"] = maps
    return {
        "python_version": [3, 11, 0],
        "engine_version": "0.1.0",
        "engine_importable": True,
        "region_fill_supported": region,
        "agent_bridge_supported": bridge,
        "modules": modules,
    }


@pytest.mark.parametrize(
    "region,bridge,maps,missing",
    [
        (False, False, False, "region-fill renderer"),
        (True, False, True, "agent bridge"),
        (True, True, False, "online map decoder"),
    ],
)
def test_doctor_never_promises_primary_workflow_for_partial_installs(
    helper, monkeypatch, tmp_path, region, bridge, maps, missing
):
    raw = probe_result(helper, region=region, bridge=bridge, maps=maps)
    monkeypatch.setattr(helper, "probe", lambda python: raw)
    report = helper.doctor(tmp_path / "not-created", Path(sys.executable))
    assert report["offline_ready"] is True
    assert report["region_fill_ready"] is region
    assert report["ready"] is report["online_ready"] is False
    assert report["recommended_mode"] == "setup"
    assert missing in report["note"]
    assert not (tmp_path / "not-created").exists()


def test_probe_checks_imports_not_just_installed_package_names(helper, tmp_path, monkeypatch):
    """An installed decoder whose binary dependency cannot import is not ready."""
    decoder = tmp_path / "mapbox_vector_tile.py"
    decoder.write_text("raise ImportError('test broken decoder dependency')\n")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    report = helper.probe(Path(sys.executable))
    assert report["engine_importable"] and report["region_fill_supported"]
    assert report["agent_bridge_supported"]
    assert report["modules"]["mapbox_vector_tile"] is False


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


@pytest.mark.parametrize("current_engine", [False, True])
def test_setup_installs_online_extra_only_for_declared_current_engine(
    helper, monkeypatch, tmp_path, current_engine
):
    source = tmp_path / "verified-test-archive.zip"
    source.write_bytes(b"test archive; installer is stubbed")
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    lock["sha256"] = helper.digest(source)
    lock.pop("capabilities", None)
    if current_engine:
        lock["capabilities"] = {name: True for name in helper.ONLINE_CAPABILITIES}
    workspace = tmp_path / "installation"
    raw = probe_result(helper, region=current_engine, bridge=current_engine, maps=False)
    monkeypatch.setattr(helper, "probe", lambda python: raw)
    commands = []

    def installer(args, message, timeout=600):
        commands.append([str(arg) for arg in args])
        if args[1:3] == ["-m", "venv"]:
            python = helper.env_python(workspace)
            python.parent.mkdir(parents=True)
            python.touch()
        if "install" in args and str(args[-1]).endswith("[maps]"):
            raw["modules"]["mapbox_vector_tile"] = True

    monkeypatch.setattr(helper, "run_checked", installer)
    result = helper.setup(workspace, lock, archive=source)
    package = next(command[-1] for command in commands if "install" in command)
    assert package.endswith("[maps]") is current_engine
    assert result["ready"] is current_engine
    assert result["offline_ready"] is True
    assert result["status"] == ("ready" if current_engine else "offline_ready")
    assert json.loads((workspace / ".camera-atlas-env.json").read_text())["state"] == result["status"]
    calls_before_reuse = len(commands)
    assert helper.setup(workspace, lock, archive=source)["reused"] is True
    assert len(commands) == calls_before_reuse


def test_current_setup_fails_if_declared_online_capabilities_are_missing(helper, monkeypatch, tmp_path):
    source = tmp_path / "verified-test-archive.zip"
    source.write_bytes(b"test archive; installer is stubbed")
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    lock["sha256"] = helper.digest(source)
    lock["capabilities"] = {name: True for name in helper.ONLINE_CAPABILITIES}
    monkeypatch.setattr(helper, "probe", lambda python: probe_result(helper, maps=False))
    monkeypatch.setattr(helper, "run_checked", lambda *args, **kwargs: None)
    workspace = tmp_path / "installation"
    with pytest.raises(ValueError, match="online map decoder"):
        helper.setup(workspace, lock, archive=source)
    assert json.loads((workspace / ".camera-atlas-env.json").read_text())["state"] == "installed"


@pytest.mark.parametrize(
    "change",
    [
        {"source_url": "https://other.example/engine.zip"},
        {"revision": "main"},
        {"sha256": "unverified"},
        {"capabilities": {"agent_bridge": True}},
        {"capabilities": {"agent_bridge": "true"}},
    ],
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


def test_legacy_demo_can_render_when_primary_agent_route_is_unavailable(helper, monkeypatch, tmp_path):
    lock = helper.read_lock(SKILL / "references/engine-lock.json")
    originals = tmp_path / "demo-inputs"
    originals.mkdir()
    for asset in lock["demo_files"]:
        (originals / asset["path"]).write_bytes((ROOT / "examples/data" / asset["path"]).read_bytes())
    report = helper.doctor(tmp_path, Path(sys.executable))
    report.update(ready=False, online_ready=False, region_fill_ready=False, agent_bridge_supported=False)
    monkeypatch.setattr(helper, "doctor", lambda workspace: report)
    monkeypatch.setattr(helper, "download", lambda *args: pytest.fail("Verified sample was already present"))
    result = helper.demo(tmp_path, lock, tmp_path / "legacy-demo")
    assert result["status"] == "rendered"
    assert Path(result["final"]).is_file()
    assert result["quality"]["passed"]


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
    assert json.loads(result.stdout)["skill_version"] == "2.2.0"
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
        assert "SKILL.md" in names
        assert "references/START-HERE.en.md" in names
        assert "references/START-HERE.zh-CN.md" in names
        assert "references/public-sample.md" in names
        assert archive.read("sample/lucerne.json") == (ROOT / "examples/data/lucerne.geojson").read_bytes()
        assert archive.read("LICENSE.txt") == (ROOT / "LICENSE").read_bytes()
        assert all(Path(name).suffix in {".md", ".txt", ".json", ".yaml", ".py"} for name in names)
        assert (
            archive.read("sample/photos.sources.json")
            == (ROOT / "examples/data/photos.sources.json").read_bytes()
        )
        manifest = json.loads(archive.read("package-manifest.json"))
        assert manifest["skill_version"] == "2.2.0"
        assert manifest["price"] == "Free" and not manifest["platform_tested"]
        for name, data_hash in manifest["files"].items():
            content = archive.read(name)
            content.decode("utf-8")
            assert hashlib.sha256(content).hexdigest() == data_hash
        assert not any(name.endswith((".jpg", ".png", ".tif", ".whl")) for name in names)
