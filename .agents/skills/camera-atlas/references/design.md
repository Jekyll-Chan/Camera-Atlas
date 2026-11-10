# Editorial composition and review

Default: editorial-minimal; fine warm-white lines, restrained opacity, one red location mark, no central title, opaque card or decorative frame. Other themes change only design parameters: topographic-fine, coastal-atlas, urban-documentary, monochrome-print. Monochrome intentionally uses a neutral mark. All optional geographic text can be disabled; required legal attribution remains.

Modes use data availability: water/coastline, contour topography, roads, trails, river, regional boundaries or minimal. An optional subject hint affects priority but never creates data. The image analyzer estimates texture and contrast, picks a corner and shrinks on busy backgrounds. It cannot identify sky, people, peaks, buildings or boats. Review visually; supply a normalized-size grayscale exclusion mask (nonzero protects) for important subjects.

Maps occupy about 20% of the photo by default and may shrink. Placement is purely artistic: map coordinates stay in WGS84/local AEQD independently of the pixel rectangle. A map is a locator, not terrain registered to the camera perspective. Use scale only with known projection and extent. North labels describe map direction only. Insufficient data yields a clean photo and a warning.

Check standalone overlay alpha in an image editor; inspect low-contrast lines, clipped text and masked attribution. PNG is the reference image; SVG uses editable system font text and may differ in typography across viewers. All repaired detail is interpolation and requires human review. Do not claim authentic recovery of text-occluded features.
