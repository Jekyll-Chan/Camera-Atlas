# Camera Atlas

**Photography First. Geography Verified.**

Camera Atlas adds auditable vector geography to original travel photographs using independent transparent layers. It never regenerates or grades the photograph. Python 3.11+, local CLI, reusable API and Codex Agent Skill. Version 0.1.0 is an initial release; read the accuracy limits below.

[中文说明](README.zh-CN.md) · [Architecture](docs/Architecture.md) · [CLI](docs/CLI-Reference.md) · [Accuracy](docs/Accuracy-and-Provenance.md)

## Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install '.[terrain,repair]'
camera-atlas --help
```

Core installation is `pip install .`. Optional extras: `terrain` (rasterio/contourpy), `repair` (OpenCV), `heic` (pillow-heif), `dev` (tests/build/lint). No model service or API key is required for offline rendering. TIFF and HEIC normalize to 8-bit RGBA; high-bit-depth/HDR preservation is not supported.

## Quick start

```bash
camera-atlas render --input photo.jpg --lat 46.98 --lon 8.60 \
  --geojson examples/data/lucerne.geojson --offline --radius-km 45 \
  --svg --scale --output render-output/lake
```

Replace the illustrative coordinates with the actual camera GPS. To use a known locality instead of claiming an exact camera position:

```bash
camera-atlas render --input photo.jpg --location 'Lake Lucerne' \
  --geojson examples/data/lucerne.geojson --radius-km 45 --offline \
  --output render-output/locality
```

A configured Nominatim-compatible endpoint can resolve place names. No public geocoder is enabled by default. Multiple candidates remain unresolved until the user confirms one. A lake centroid is a locality, never a precise camera point. `--confirmed-region --lat ... --lon ...` declares only a region center.

```bash
camera-atlas render --input photo.jpg --location 'Sayram Lake, Xinjiang, China' \
  --nominatim-url https://YOUR-APPROVED-NOMINATIM-SERVICE \
  --output render-output/sayram
camera-atlas render --input photo.jpg --lat 46.98 --lon 8.60 \
  --dem terrain.tif --dem-source terrain.source.json --map-mode topographic \
  --contour-interval 100 --offline --output render-output/terrain
camera-atlas batch --input photos --manifest locations.csv --output render-output/batch
```

Coordinate-based online requests use Overpass, bounded to a small area, with persistent cache and bounded retries. Hosted or high-volume applications must use their own service or legal regional extracts. Offline mode can reuse cached responses, but never makes HTTP requests.

## Python API

```python
from camera_atlas import RenderConfig, render

result = render(
    RenderConfig(
        input="photo.jpg",
        output="render-output/api",
        location="Lake Lucerne",
        geojson="examples/data/lucerne.geojson",
        offline=True,
        radius_km=45,
        svg=True,
    )
)
print(result.final, result.metadata["quality"])
```

Each render writes `final.png`, normalized `original.png`, `clean_base.png`, full-frame transparent `map_overlay.png`, saliency mask, `location.geojson`, `metadata.json`, and `provenance.json`. `--svg` adds editable SVG when geography is available. An approved text mask adds `text_removal_mask.png`. `--no-layers` disables photographic layer export. Output directories must be empty. Input files are never overwritten. Reuse `clean_base.png` and `location.geojson` with `--offline` to redesign a map without repairing the base again.

## Photography and layout

No crop, resampling of the photograph, global recoloring or generative model. EXIF orientation is normalized, ICC profile retained. Outside overlay alpha and a reviewed repair mask, normalized pixels are checked for exact equality. PNG output is lossless relative to the normalized 8-bit source; JPEG decompression is not reversible.

Seven modes: coastline, topographic, urban, trail, river, regional, minimal; automatic selection uses verified feature kinds, an optional subject hint, and data within the geographic viewport. Placement uses edge density/local contrast, shrinks in busy compositions, and supports a user exclusion mask. This is **not semantic segmentation**: it cannot reliably identify people, peaks, boats, buildings or sky. Review every composition. Use `--exclusion-mask` for guaranteed pixel exclusion.

Five themes share the same data engine. Required dataset attribution remains visible even with `--no-labels`. Maps have no rectangular fill. Region locations use an open ring; exact GPS uses one solid mark. North refers only to the map. Optional scales are checked by inverse projection and WGS84 geodesic distance. Missing verified geometry produces a clean photograph with a warning, never invented map lines.

## Text repair

Optional `detect-text` uses an installed system Tesseract to propose boxes. Review the mask, then explicitly pass `--remove-text --text-mask reviewed.png`. OpenCV TELEA interpolates only selected pixels and flags the result for human review. It cannot restore authentic hidden details. Masks over 10% of the photograph are rejected. OCR is never used to infer geography. Screenshot bar detection is heuristic; no automatic crop or UI removal occurs.

## Codex Skill

Open this repository in Codex: `.agents/skills/camera-atlas/SKILL.md` is repository-discoverable. Invoke `$camera-atlas` or ask for a travel photograph with verified editorial geography. To use across projects, copy the `camera-atlas` folder to your Codex user skill directory (consult your Codex version's discovery paths). The Python package must be installed in the executing environment. See [Skill Usage](docs/Skill-Usage.md) and [official skills documentation](https://learn.chatgpt.com/docs/build-skills).

## Data, accuracy and licenses

Code is MIT. Geographic data and example photos keep their own licenses; MIT never relicenses OSM. Offline FeatureCollections require `sources` declarations and per-feature `source_id`. These declarations are auditable claims, not automatic authentication of an arbitrary dataset. Use trusted providers and inspect source URLs/checksums. See [provider schema](docs/Geographic-Data-Providers.md).

- OpenStreetMap: ODbL, visible credit and copyright URL. Overpass currently handles ways and place nodes; multipolygon relations are deliberately omitted rather than guessed.
- Natural Earth: public domain, overview only. Each source declares a minimum geographic span to prevent misleading high-detail use.
- DEM: local georeferenced raster plus source declaration, verified meter units, license and optional checksum. Contours come only from raster values. Credentials/downloads for Copernicus, NASADEM, SRTM and OpenTopography are not bundled.

**Public Nominatim policy:** read [the current usage policy](https://operations.osmfoundation.org/policies/nominatim/) before selecting that service. It limits aggregate use to at most one request per second, requires application identification and caching, restricts bulk/systematic queries, and restricts generic services generated by LLM platforms. Developers must make a deliberate informed decision and own compliance. Camera Atlas requires both an explicit endpoint and `--accept-public-nominatim-policy` for that host. Acceptance is not permission to violate the policy. Batch processing defaults to offline and has no public-geocoder toggle. Cache rate limits are coordinated only among processes sharing the same cache; deploy centrally for aggregate limits. Place queries/coordinates sent to online providers may disclose sensitive locations.

## Examples, tests and release

[Example gallery and licenses](examples/README.md). Public data subsets and licensed photography are separated from private user inputs. Reproduce with `python examples/build_examples.py` after installing extras.

```bash
pip install '.[terrain,repair,dev]'
pytest --cov=camera_atlas
ruff check .
python -m build
```

Offline CI uses small real-data extracts. Analytical rasters appear only in numerical algorithm tests and are labeled accordingly. Live network tests require `CAMERA_ATLAS_NETWORK=1 pytest -m network`. See [CONTRIBUTING](CONTRIBUTING.md), [release steps](docs/Release.md), and [Troubleshooting](docs/Troubleshooting.md).

Roadmap: robust OSM relation assembly, semantic subject adapters, vertical datum transformations, high-bit-depth composition, managed DEM download adapters and additional geocoder adapters. The current core does not implement these capabilities.


[Validation record / 实测记录](docs/Validation.md) · [Requirement status / 验收状态](docs/Acceptance.md)
