from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def data_dir():
    return Path(__file__).resolve().parents[1] / "examples/data"


@pytest.fixture
def photo(tmp_path):
    # Deterministic RGB pixel fixture, not a geography or photography authenticity fixture.
    a = np.zeros((700, 1000, 3), dtype="uint8")
    a[:, :, 0] = np.arange(1000, dtype="uint16")[None, :] % 256
    a[:, :, 1] = np.arange(700, dtype="uint16")[:, None] % 256
    a[:, :, 2] = 80
    p = tmp_path / "pixels.png"
    Image.fromarray(a).save(p)
    return p


@pytest.fixture
def values(tmp_path, photo, data_dir):
    return {
        "input": photo,
        "output": tmp_path / "result",
        "offline": True,
        "cache": tmp_path / "cache",
        "geojson": data_dir / "lucerne.geojson",
        "location": "Lake Lucerne",
        "radius_km": 45,
    }
