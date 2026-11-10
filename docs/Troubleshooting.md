# Troubleshooting

- Clean image/no map: inspect provenance warnings. Supply a resolved location, real features inside the selected extent, and source-appropriate radius. Unresolved names, omitted relations and unavailable APIs are not replaced with guesses.
- Lake missing at small span: Natural Earth is overview data. Increase radius or supply a trusted high-resolution OSM/local shoreline extract. A 1:10m dataset does not have 10m accuracy.
- Place unresolved: configure an approved geocoder or use an offline dataset with locality. Multiple results require disambiguation. Do not supply region-center coordinates as exact camera GPS; use `--confirmed-region`.
- Public endpoint rejected: read the current provider policy, use an eligible authorized service or local extracts. Changing a flag does not grant usage rights.
- Missing glyphs: English output can omit non-ASCII names without an English label. Supply a font with appropriate coverage and local/bilingual labels. Check font license for distribution.
- Attribution too wide: increase map area/photo dimensions or provide a shorter source-approved attribution that still satisfies terms. Required credit must remain readable.
- Terrain error: install `[terrain]`, supply a valid CRS, meter units and matching checksum; warp rotated grids and subset huge rasters first. Vertical datum conversion is unsupported.
- Screenshot UI: use the original photo/frame when available. Black-bar hints are heuristic, never automatic crop. Reviewed text masks may interpolate small overlays; complex hidden detail cannot be recovered.
- Repair error: install `[repair]`, review a mask matching normalized dimensions, keep it below 10% of image area. The original remains untouched. Inspect repaired content manually.
- OCR unavailable: install the system Tesseract program, or supply a manually reviewed mask; no OCR is required for normal map rendering.
- Busy photo: manually position/shrink the map or supply a subject exclusion mask. Saliency is not semantic recognition.
- Existing output: choose a fresh directory. Camera Atlas refuses to overwrite an existing render. A standalone clean base can be restyled with the prior location GeoJSON.
- HEIC: install `[heic]`. TIFF/HDR/CMYK normalize to 8-bit RGBA; specialized archival color workflows are outside this version.
