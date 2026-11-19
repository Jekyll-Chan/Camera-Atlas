# Editorial composition and review

Preserve the approved clean base, original direction, crop, color and light. Compose independent transparent layers: no opaque card, central title, decorative frame or whole-photo regeneration. Default to fine warm-white lines, restrained opacity and one red location mark (open ring for locality, solid only for actual GPS). Keep source credit readable.

## Region before map

Determine the continuous area where the map belongs from the user request and actual image. A whole-sky request includes the sky to the photo edges, around building outlines and between large branches. A sideways photo may have its sky down the right side; do not rotate it or assume sky means the top. Protect important subjects with a mask.

The selected region overrides the usual 15–25% starting suggestion. No automatic shrink on busy texture applies in region-fill mode. A wide or tall region needs a matching geographic viewport, not a centered square. Read [region-fill.md](region-fill.md) for fitting, data coverage and review.

Use real roads for cities, water/coastlines for coasts/lakes, verified DEM contours for mountains, and real trails/rivers when suitable. A pond or moat in an urban dataset is not a reason to discard the surrounding street network; select the appropriate map mode explicitly when necessary. Combine only supported, sourced features. A water body can naturally have an empty interior; do not invent contours. Placement is artistic, not registration to visible terrain or camera perspective.

The legacy analyzer only estimates texture/contrast and picks a small corner. It cannot recognize sky, people, trees, peaks or buildings. Region-fill currently requires a visually reviewed selection, not a claim of automatic semantic segmentation.

Review full-frame and selected-area crops. Check continuity toward the region ends, clipped words, protected objects and subtle line weight. A sparse map may need a wider source extract or another real-data layer, not heavier lines. Inspect PNG alpha and attribution. At full resolution, check that street lines do not cross label or credit letterforms; v2.2.1 clears underlying map ink transparently, without altering the clean photo or adding opaque label boxes. SVG text varies with viewer fonts; PNG is the reference. Repair is interpolation, not authentic recovery.
