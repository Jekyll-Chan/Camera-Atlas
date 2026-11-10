import json
import os
import shutil
import subprocess
import sys

import pytest
from click import unstyle
from typer.testing import CliRunner

from camera_atlas.cli import app

runner = CliRunner()


@pytest.mark.parametrize("colored", [False, True], ids=["plain", "colored"])
def test_cli_help(colored):
    # Run fresh processes: Rich reads terminal/color settings during import.
    env = dict(os.environ)
    if colored:
        env.pop("NO_COLOR", None)
        env.update(FORCE_COLOR="1", TERM="xterm-256color")
    else:
        env.pop("FORCE_COLOR", None)
        env.update(NO_COLOR="1", TERM="dumb")
    result = subprocess.run(
        [sys.executable, "-m", "camera_atlas.cli", "render", "--help"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--geojson" in unstyle(result.stdout)
    if colored:
        assert "\x1b[" in result.stdout


def test_cli_render(values):
    result = runner.invoke(
        app,
        [
            "render",
            "--input",
            str(values["input"]),
            "--output",
            str(values["output"]),
            "--geojson",
            str(values["geojson"]),
            "--location",
            "Lake Lucerne",
            "--radius-km",
            "45",
            "--offline",
            "--svg",
            "--cache",
            str(values["cache"]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (values["output"] / "map_overlay.svg").exists()


def test_cli_invalid_coordinate(values):
    result = runner.invoke(
        app,
        [
            "render",
            "--input",
            str(values["input"]),
            "--output",
            str(values["output"]),
            "--lat",
            "100",
            "--lon",
            "0",
            "--offline",
        ],
    )
    assert result.exit_code == 2 and "less than or equal to 90" in result.output


def test_batch(values, tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    shutil.copy(values["input"], photos / "one.png")
    shutil.copy(values["input"], photos / "two.png")
    manifest = tmp_path / "locations.csv"
    manifest.write_text(
        "file,location,geojson\none.png,Lake Lucerne," + str(values["geojson"]) + "\ntwo.png,,\n"
    )
    out = tmp_path / "batch"
    result = runner.invoke(
        app,
        [
            "batch",
            "--input",
            str(photos),
            "--manifest",
            str(manifest),
            "--output",
            str(out),
            "--cache",
            str(values["cache"]),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads((out / "batch_report.json").read_text())
    assert len(report["success"]) == 2 and not report["failures"]


def test_batch_path_traversal(values, tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    manifest = tmp_path / "locations.csv"
    manifest.write_text("file\n../outside.png\n")
    out = tmp_path / "batch"
    result = runner.invoke(
        app, ["batch", "--input", str(photos), "--manifest", str(manifest), "--output", str(out)]
    )
    assert result.exit_code == 1
    assert "inside" in json.loads((out / "batch_report.json").read_text())["failures"][0]["error"]
