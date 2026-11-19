import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from camera_atlas import agent


def test_separate_agent_commands_render_offline_without_a_server(tmp_path, photo, data_dir):
    original = photo.read_bytes()
    workspace = tmp_path / "agent workspace"
    prepared = agent.prepare(photo, workspace, data_dir)
    assert prepared["requires_review"] is True
    assert prepared["max_pixels"] == 25_000_000
    assert Path(prepared["original_path"]).read_bytes() == original
    region = tmp_path / "reviewed.png"
    mask = Image.new("L", (prepared["width"], prepared["height"]))
    ImageDraw.Draw(mask).rectangle((0, 0, 999, 280), fill=255)
    mask.save(region)
    # Run in a separate process: no Python object or web session is retained.
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "camera_atlas.agent",
            "render",
            "--photo-id",
            prepared["photo_id"],
            "--place-id",
            "san-francisco",
            "--region",
            str(region),
            "--reviewed-region",
            "--radius-km",
            "0.08",
            "--map-mode",
            "urban",
            "--location-label",
            "San Francisco",
            "--workspace",
            str(workspace),
            "--data",
            str(data_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert result["status"] == "rendered" and result["review_required"] is True
    for name in ("final", "overlay", "mask", "sources", "clean_base"):
        assert Path(result[name]).is_absolute() and Path(result[name]).is_file()
    with Image.open(result["final"]) as final, Image.open(prepared["base_path"]) as base:
        assert final.size == base.size
        assert np.array_equal(np.asarray(final)[281:], np.asarray(base)[281:])
    assert photo.read_bytes() == original
    assert json.loads(Path(result["sources"]).read_text())["location"]["accuracy"] == "locality"
    assert json.loads(Path(result["final"]).with_name("metadata.json").read_text())["map_mode"] == "urban"


def test_region_review_required_before_side_effects(tmp_path):
    root = tmp_path / "not-created"
    with pytest.raises(ValueError, match="reviewed-region"):
        agent.render("missing", "missing", tmp_path / "missing.png", False, root)
    assert not root.exists()


def test_wrong_mask_size_and_unknown_place_fail_without_output(tmp_path, photo, data_dir):
    root = tmp_path / "workspace"
    prepared = agent.prepare(photo, root, data_dir)
    mask = tmp_path / "wrong.png"
    Image.new("L", (128, 128), 255).save(mask)
    with pytest.raises(ValueError, match="confirm"):
        agent.render(prepared["photo_id"], "invented-location", mask, True, root, data=data_dir)
    with pytest.raises(ValueError, match="size"):
        agent.render(prepared["photo_id"], "san-francisco", mask, True, root, data=data_dir)
    assert not list(root.glob("*/final.png"))


def test_unknown_photo_is_not_silently_reimported(tmp_path, data_dir):
    mask = tmp_path / "region.png"
    Image.new("L", (128, 128), 255).save(mask)
    with pytest.raises(ValueError, match="confirm"):
        agent.render("missing-photo", "san-francisco", mask, True, tmp_path / "work", data=data_dir)


def test_search_returns_persisted_candidates_not_an_assumed_exact_location(tmp_path, monkeypatch):
    def candidates(self, query):
        assert query == "Kyoto"
        return [{"id": "server-id", "name": "Kyoto", "label": "Kyoto · Japan", "aliases": "kyoto"}]

    monkeypatch.setattr(agent.OnlineWorkspace, "search_places", candidates)
    result = agent.search("Kyoto", tmp_path / "work")
    assert result["status"] == "needs_place_confirmation"
    assert result["accuracy"] == "locality"
    assert result["candidates"][0]["id"] == "server-id"


def test_cli_errors_are_json_and_do_not_claim_success(capsys, tmp_path):
    code = agent.main(
        ["prepare", "--input", str(tmp_path / "missing.png"), "--workspace", str(tmp_path / "new")]
    )
    assert code == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not (tmp_path / "new").exists()
    assert agent.main(["render"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
