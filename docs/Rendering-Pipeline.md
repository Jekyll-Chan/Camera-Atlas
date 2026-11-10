# Rendering pipeline

1. Decode JPEG/PNG/TIFF/WebP (optional HEIC), apply EXIF orientation once, preserve ICC. Work in 8-bit RGBA; no color-profile conversion, global grade or image resize.
2. Optional reviewed binary text mask → OpenCV TELEA interpolation; only selected RGB pixels are copied back. Alpha and all unselected pixels remain unchanged. Save the mask and flag human review. This cannot recover authentic hidden detail.
3. Compute local contrast/edge density saliency and optional explicit subject exclusion. Screenshot black-bar hints are heuristic; UI/text is not automatically cropped or removed.
4. Resolve location, obtain real geometry, select a data-supported mode within the geographic viewport. Suppress sources too coarse for the chosen span. Missing reliable data returns clean photography.
5. Project with local AEQD, clip in projected meters, map to a small corner canvas, draw fine lines/limited labels/precision symbol/credits. Rasterize at 2x map size, then downsample only the overlay for antialiasing. Full-frame output remains transparent outside artwork.
6. Composite with `Pillow.Image.alpha_composite`. Validate unchanged dimensions, no base changes outside the repair mask, no final changes outside overlay alpha, and no overlay inside a supplied subject mask. Save atomically.

PNG is the typography reference. SVG preserves geometric vectors and editable text but font metrics can differ across apps. Exclusion masks are embedded as raster SVG masks. Rendering quality checks measure pixels and bounds, not human aesthetic judgment, text contrast or semantic foreground identity. Visually inspect required attribution and all important subjects.

Use `clean_base.png` and exported `location.geojson` to restyle without rerunning text interpolation. Turn off repair for that pass; retain the prior mask/provenance with the project. The normalized original is not a byte-identical copy of the compressed source, which remains untouched at the user's input path.
