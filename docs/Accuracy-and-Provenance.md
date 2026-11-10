# Accuracy and provenance

Explicit coordinates override EXIF. Explicit place names override EXIF too; unresolved names never silently fall back to a different EXIF location. Without explicit input, EXIF GPS is preferred, then declared offline locality. Visual clues are not used to infer location. EXIF itself can be wrong: exact_gps describes the type of input, not a surveyed accuracy guarantee.

Precision classes: exact_gps, locality, regional, unresolved. Resolved locality coordinates are only place/map centers. Open rings distinguish area locations from solid camera marks. An uncertainty radius is not invented; the ring is a symbol, not a geographic confidence interval. Ambiguous names return candidates in provenance and a clean photograph. Confirm a candidate's region, or supply true camera GPS only when known.

`provenance.json` records location, coordinate origin, conflicts, candidate list, dataset URLs/versions/licenses/retrieval times, source hashes, every drawn feature index/source/label, projection, extent, artistic pixel rectangle, optional geodesic scale and warnings. `location.geojson` retains the input geometry and declarations. `metadata.json` includes input image hash, pixel checks, composition method and repair review state. Original camera heading is unknown and never inferred from north.

A declared source is not independent verification. A malicious/fabricated input GeoJSON can lie about its source. Use trusted data, inspect URLs and compare upstream artifacts/hashes. The project guarantees traceability and conservative rendering of accepted data, not universal authenticity certification.

Scale endpoints are transformed back to WGS84 and measured on the ellipsoid. They apply to the map, never to the photograph. No camera-pose/perspective registration is attempted. Absolute elevation accuracy and vertical datum conversion are not guaranteed. No road number, elevation label or place name is synthesized from language-model knowledge.

Default EXIF export is disabled, but geolocation in output manifests remains sensitive. All outputs stay local unless explicitly published. Never commit private originals/GPS; `.gitignore` alone does not anonymize them.
