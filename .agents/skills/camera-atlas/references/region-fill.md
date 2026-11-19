# Region-fill workflow · v2.2

Read this for a map across a specified sky, water, ground or other region, or a map that looks like a small square despite a large layer.

## Capability gate

Run the onboarding doctor against the actual interpreter. Require `region_fill_supported`; the normal online agent route also requires `online_ready`. Use the verified immutable source declared by the current lock or the trusted source kit. Do not replace the lock with an unverified branch or invent a commit/checksum. If a received older lock or environment lacks the capability, explain the limitation and obtain the verified release; do not substitute its corner map and call the task complete.

## Construct the map window

1. Use the approved `clean_base.png`, with its existing normalized orientation. Resolve requested screenshot UI/text cleanup first. Never stack a second map over a previous `final.png`.
2. Create a grayscale mask at the clean base's exact pixel dimensions: white includes the entire desired map region, black excludes everything else. Protect architecture, people and important branches with black holes or a separate exclusion mask. Check the mask against the photo. Do not let the old corner heuristic or 20% default replace this region.
3. The region bounding rectangle sets the map aspect ratio. `--radius-km` is half the shorter geographic span. Extend the longer span proportionally, using the SAME metres-per-pixel for both axes. The map center may move within the selection to keep the locality marker visible, but its geographic coordinates do not change.
4. Obtain sourced geometry for the ENTIRE expanded viewport. Online fetching uses expanded bounds when no supplied geometry exists. Existing offline extracts are not automatically extended. For partial extracts, obtain a larger reliable source or explain missing coverage. A provider limit requires an appropriate regional extract. Never repeat, stretch or fabricate geography to fill gaps.
5. Render across the rectangle without a square inset, large footer or fixed margins, then clip all ink to the region minus protected subjects. Required credit must fit inside a clear part of the selection; otherwise enlarge a safe part. Keep the layer transparent.

Agent command template (substitute existing paths; users need not run this):

```bash
camera-atlas render --input /task/clean_base.png \
  --geojson /task/verified-expanded.geojson --location 'Confirmed locality' \
  --region-mask /task/selected-region.png --radius-km 2 \
  --map-mode urban --offline --svg --output /task/new-result
```

The radius is an illustration, not a preset. With `--region-mask`, `--map-area` and corner placement are ignored. No fixed percentage cap applies. Photo proportions and direction remain unchanged. `map_region_mask.png` records the effective allowed region.

## Acceptance

- Compare clean base and final: only map ink and separately approved repairs may change pixels. The mask must align after EXIF normalization.
- Confirm viewport aspect ratio and uniform geographic scale. Verify source coverage as well as region dimensions.
- Inspect geometry near relevant region edges and across its interior. A full-image PNG, a single line touching opposite edges, locator or footer is NOT proof of fill.
- `region_distribution` reports occupied cells using geometry only, excluding labels/marker/credits. Empty cells prompt review; genuinely sparse geography is possible. No percentage proves aesthetic success or dataset completeness.
- Check protected subjects, clipped labels and attribution in full-frame and detail views.
- For an unexplained blank strip, expand actual data or revise the verified viewport and rerender from the clean base. If data remain unavailable, label the limitation rather than claiming completion.

Regression cases: a horizontal sky above buildings, a narrow sky down the side of a sideways photo, and a sky with a building/tree-shaped hole. Apply the same region contract to the mobile editor, CLI and Skill.
