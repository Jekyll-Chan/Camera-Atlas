# Design system

Themes are immutable `Theme` values in `cartography/design.py`: ink RGB, accent RGB, line weight and maximum label count. Default ink is warm white, opacity .65, map area .20, margins 4.5% of the short side, at most four labels, one precision symbol. Map area is a target; canvas dimensions/margins and texture may reduce it. Artwork contains no opaque fill, central title, information card or photo crop.

editorial-minimal is the default; topographic-fine uses lighter contour strokes, coastal-atlas cooler ink, urban-documentary denser but thin roads, monochrome-print neutral strokes and marker. All share the same geography and accuracy rules.

Labels are collision-checked within the local map canvas. English uses `name:en` or ASCII `name`, local uses `name`, bilingual combines supplied values. Non-Latin labels need `--font` pointing to a licensed font with coverage; no translation or transliteration is invented. Fonts are not bundled. SVG viewers choose their own sans-serif fallback. `--no-labels` removes optional geographic text and scale/north text; required source credit remains.

A solid mark means input camera GPS; an open ring means locality/region. It does not encode a made-up uncertainty distance. North is local map north and never camera direction. A scale requires a valid projection/extent. No local geography is perspective-aligned over photographic landforms.

The analyzer handles texture, not semantics. In detailed images use manual position, a smaller map area, reduced opacity and a subject exclusion mask. Review photographic subjects and legibility at final viewing/print size. Tiny canvases that cannot hold legal credit fail explicitly.
