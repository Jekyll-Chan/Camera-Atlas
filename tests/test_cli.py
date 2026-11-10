import json
import shutil

from typer.testing import CliRunner

from camera_atlas.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["render", "--help"])
    assert result.exit_code == 0 and "--geojson" in result.output


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
