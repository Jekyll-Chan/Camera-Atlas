# CLI reference

Use `camera-atlas render --help` for generated types/defaults. All outputs are directory-based and must be empty. Configuration is validated before mutation.

| Option | Meaning |
|---|---|
| `--input`, `--output` | Existing photo, separate empty result directory |
| `--location` | Place-name lookup or matching declared offline locality |
| `--lat`, `--lon` | Both required together; finite WGS84 camera GPS |
| `--confirmed-region` | Supplied coordinates are a region center, not camera GPS |
| `--geojson` | Traceable RFC7946 FeatureCollection |
| `--dem`, `--dem-source` | Local georeferenced elevations and provenance JSON |
| `--contour-interval` | Positive meter interval, default 100 |
| `--map/--no-map` | Enable map or export clean photograph |
| `--map-mode` | auto/coastline/topographic/urban/trail/river/regional/minimal |
| `--style` | editorial-minimal/topographic-fine/coastal-atlas/urban-documentary/monochrome-print |
| `--map-area` | Target area fraction .03–.30, default .20 |
| `--radius-km` | Half-width of square map, greater than 0 up to 100, default 10 |
| `--opacity` | 0–1, default .65 (legal credit may use higher alpha) |
| `--position` | auto/top-left/top-right/bottom-left/bottom-right |
| `--labels/--no-labels` | Optional geography text; credit always retained |
| `--label-language` | en/local/bilingual, supplied names only |
| `--font` | Licensed local TrueType/OpenType font for Unicode coverage |
| `--svg` | Editable SVG in addition to PNG, if map available |
| `--layers/--no-layers` | Export normalized original, clean base and overlay; default on |
| `--preserve-metadata` | Retain EXIF in PNG, reset applied orientation; default off |
| `--offline` | Cache/local inputs only; no HTTP requests |
| `--cache` | Shared SQLite cache directory |
| `--scale`, `--north` | Verified map scale / map north, optional |
| `--remove-text`, `--text-mask` | Explicit reviewed-mask interpolation |
| `--exclusion-mask` | Nonzero pixels protected from overlay, normalized photo size |
| `--subject` | unknown/lake/mountain/city/trail/river/coast hint; never creates data |
| `--nominatim-url` | Configured approved service, no default |
| `--accept-public-nominatim-policy` | Additional deliberate public-host gate, not a terms exemption |
| `--overpass-url` | Replace small-query public default |
| `--user-agent` | Identifying application agent; supply contact for a deployed app |

`camera-atlas detect-text --input photo.jpg --output review/` normalizes orientation, uses system Tesseract TSV boxes (confidence ≥60), and writes candidate mask/review JSON. It never repairs automatically. Install Tesseract separately for this optional command.

`camera-atlas batch --input photos/ --manifest locations.csv --output results/` is serial/offline by default. CSV requires `file`; optional `lat,lon,location,geojson,dem,dem_source,confirmed_region`. Photo paths must stay inside input. Data paths are relative to the CSV. Per-row failures are collected, other rows continue, `batch_report.json` is always written after a valid CSV header. Exit codes: 0 success (warnings may indicate clean fallback), 1 batch row failures, 2 invalid input/CLI error.

```csv
file,location,geojson,lat,lon,confirmed_region
lake.jpg,Lake Lucerne,../examples/data/lucerne.geojson,,,
city.jpg,San Francisco,../examples/data/san_francisco.geojson,37.7955,-122.4065,true
```

Python API accepts `RenderConfig` or a dict and exposes the same fields (`map_enabled` corresponds to `--map`). It raises `ValueError`/Pydantic validation errors for invalid inputs. A clean fallback is a successful result with a clear warning and no geographic alpha.
