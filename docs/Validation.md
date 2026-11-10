# Validation record — 0.1.0

Local validation date: 2026-11-10. macOS, Python 3.11.15. Exact tested packages: [requirements-tested.txt](../requirements-tested.txt). This is an observed environment record, not a cross-platform dependency lock.

| Check | Observed result |
|---|---|
| Offline suite | **57 passed**, one network test excluded; 2.30s on the recorded run |
| Coverage | **85.77%** statement coverage (832 / 970 statements) |
| Live Overpass integration | **1 passed**, run separately with explicit network opt-in |
| Ruff lint | All checks passed |
| Ruff format | All selected source/document files passed the formatter |
| Skill structural validator | Skill is valid |
| Isolated package build | sdist and universal Python wheel built successfully |
| Clean core wheel install | Separate new Python virtual environment; `pip check` and offline CLI lake render verified |
| Geographic end-to-end examples | Seven scenarios generated from real public data and documented NASA photography |
| Pixel integrity | No unexpected base/composite changes in checked renders; original aspect ratio preserved |
| Visual review | Gallery and full-resolution terrain composition inspected; fine low-contrast lines need human review |

The automated suite covers EXIF GPS/orientation, finite coordinate validation, explicit input conflicts, ambiguous geocoding, region/exact markers, AEQD projection round-trips, actual Natural Earth shorelines, genuine raster-derived contours, actual OSM streets, geodesic scale, persistent cache/offline behavior, bounded retries, ordered provider fallback, RGBA/SVG export, mask-limited local repair, source IDs/overview resolution, safe data outage and serial batch handling/path containment.

Analytical plane rasters are restricted to numerical contour algorithm tests. Geographic authenticity tests use separately documented real extracts. A zero-length contour at a real integer elevation extremum is omitted and reported rather than perturbed into a fictional line. Geographic declarations from arbitrary third parties are still a trust boundary.

The recorded environment emits one non-failing upstream rasterio/Affine PendingDeprecationWarning in the analytical test. Initial Linux/Python 3.11–3.13 GitHub Actions runs exposed a color-dependent CLI-help test assertion: ANSI formatting split the option name, although the help command exited successfully and the other 56 tests passed. The follow-up fixes normalize ANSI for assertions and exercise fresh colored/plain terminal processes. Local regression: 58 tests passed. SQLite cache connections are now closed explicitly to address Python 3.13 resource warnings. Current remote results are available on the [Actions page](https://github.com/Jekyll-Chan/Camera-Atlas/actions); historical failure notifications remain in GitHub/email. HEIC, system Tesseract OCR, additional DEM products and every possible ICC profile were not exercised here. These results must not be described as exhaustive format/platform certification.

## Explicit remaining limits

- Texture/contrast composition is not semantic recognition of people, peaks, boats, sky or buildings. Human review and subject masks remain necessary.
- Interpolation can hide old text but cannot recover verified occluded detail. It is explicitly marked for human review.
- OSM relation/multipolygon assembly is not implemented. Some large lake/coastline/boundary queries may be incomplete; the app never guesses missing geometry.
- Online DEM acquisition/credentials and vertical datum conversion are not implemented. Use legal georeferenced local meter-unit rasters.
- Source declarations and upstream hashes support audit; they do not independently authenticate arbitrary supplied data.
- TIFF/HEIC/HDR normalize to 8-bit RGBA; high-bit-depth archival fidelity is not supported.
- SVG text uses viewer fonts and can differ from reference PNG metrics. Fonts with non-Latin coverage must be supplied legally.
- Polar/antimeridian cases require dedicated split data/projections; this version declines them conservatively.
- Public geocoder/Overpass policies and availability may change; production services need their own authorized infrastructure.
- Examples are real NASA aerial photographs used for educational verification, not a ground-level travel-photography portfolio.
- Published source repository: https://github.com/Jekyll-Chan/Camera-Atlas . Initial publication used the authenticated GitHub Desktop app. No PyPI upload or tagged GitHub Release has been performed; see [Release.md](Release.md).
