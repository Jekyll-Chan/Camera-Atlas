import os

import pytest

from camera_atlas.geography.http import CachedHTTP
from camera_atlas.geography.providers import Overpass


@pytest.mark.network
def test_live_overpass(tmp_path):
    if os.environ.get("CAMERA_ATLAS_NETWORK") != "1":
        pytest.skip("Set CAMERA_ATLAS_NETWORK=1 for a live bounded query")
    http = CachedHTTP(tmp_path)
    try:
        data = Overpass(http).fetch((-122.410, 37.793, -122.403, 37.798))
        assert data.features and data.sources[0].license == "ODbL-1.0"
    finally:
        http.close()
