# Contributing

Use Python 3.11+, a virtual environment and `pip install '.[terrain,repair,dev]'`. Run `pytest --cov=camera_atlas`, `ruff check .`, `ruff format --check .`, and `python -m build`. CI covers Python 3.11–3.13 on Linux. Live APIs are opt-in and must never become an offline CI requirement.

Report a bug with version, minimal configuration, provider response/provenance and normalized dimensions; remove private GPS and photography first. Add behavioral regression tests for geographic claims and image integrity. Authenticity fixtures must come from verifiable datasets with documented licenses. Numerical analytical fixtures must be named as such. Never fix a test by replacing failed real geography with arbitrary curves.

Providers implement `Provider.fetch(bounds) -> GeoData`. Validate source IDs, geometry and WGS84; keep timeouts, retries, caching and service limits. Changes to third-party data need source URLs, versions, acquisition times and redistribution terms. Code contributions use MIT; data retains its own license.
