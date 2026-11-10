---
name: camera-atlas
description: Turn travel, landscape, and architectural photography into editorial photography or travel-zine artwork with verified geographic overlays, transparent editable layers, and auditable provenance. Use for photographic map annotation, not generative photo restyling.
---

# Camera Atlas

Use the installed `camera-atlas` Python CLI/API. From this repository, install with `python -m pip install '.[terrain,repair]'` if needed. Locate the repository through the current workspace or this skill's location; never assume the process starts in the repository. Do not install this repository's package name from an unrelated package index.

Preserve original photography. Never redraw scenery, invent coastlines/contours, infer a camera point from a place centroid, or substitute a map screenshot. Read [geography.md](references/geography.md) when selecting data and resolving ambiguity; read [design.md](references/design.md) for layout and review criteria.

1. Read the supplied photograph; inspect format, EXIF GPS/orientation and screenshot hints. Prefer an available original over a screenshot. The engine normalizes orientation and retains ICC; it does not crop or globally grade.
2. Resolve location. Explicit user input overrides conflicting EXIF and is logged. GPS is exact only when supplied as camera coordinates. A named place resolves to locality; confirmed area coordinates require `--confirmed-region`. If multiple places match, ask for a distinguishing region while continuing photo inspection. Never choose by popularity or visual guess. If unresolved, a clean no-map output is valid and must be explained.
3. Determine whether old text needs removal. Run `camera-atlas detect-text` only if useful. OCR masks are candidates, never location evidence. Repair only an explicitly reviewed mask via `--remove-text --text-mask`. Flag interpolated details for review and retain the mask.
4. Select data and geographic span using source resolution. Offline GeoJSON requires source records and per-feature source IDs. DEM needs georeferencing plus `--dem-source` metadata with meter units. Check source URLs/licenses. Name lookup needs a deliberately configured Nominatim-compatible provider; public endpoint restrictions are in the geography reference. Never invent a response to an unavailable API.
5. Use `--map-mode auto` or a user-specified mode. Inspect negative space and protect recognizable subjects using `--exclusion-mask`; the built-in analyzer is a texture heuristic, not a semantic detector. Choose a larger map span instead of magnifying coarse data.
6. Render to a new output directory, normally with `--svg`. For example:

   ```bash
   camera-atlas render --input photo.jpg --location 'Lake Lucerne' \
     --geojson examples/data/lucerne.geojson --radius-km 45 --offline \
     --svg --output render-output/lucerne
   ```

7. Inspect `final.png`, transparent `map_overlay.png`, `metadata.json` and `provenance.json`. Verify no unexpected pixel changes, no subject or label clipping, visible attribution, correct precision and suitable contrast. Reject unauditable labels, arbitrary curves or inaccurate scale claims. North is map north, not camera bearing.
8. Return the final artwork, independent layers and provenance with source restrictions and remaining uncertainty. Do not publish original user photography or GPS without explicit authorization.

For batch CSV format and all switches, use `camera-atlas batch --help`, `camera-atlas render --help`, or the repository's `docs/CLI-Reference.md`. Regenerate styling from `clean_base.png` plus `location.geojson` without repeating repair.
