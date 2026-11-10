# Camera Atlas engineering rules
Run `pytest` and `ruff check .` after behavioral changes. Keep live network tests opt-in.
Never synthesize geographic geometry or relabel analytical test rasters as real terrain.
Every rendered feature must reference a source with URL, license, version and acquisition time.
Keep original normalized pixels outside overlay and approved repair masks unchanged.
Do not commit personal photos, secrets, local caches or private GPS. Public example sources have separate licenses.
Changes to geographic accuracy require regression tests, not only image snapshots.
