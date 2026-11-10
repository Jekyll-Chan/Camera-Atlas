# Requirement status

This is a working initial release with explicit constraints, not a claim that every advanced capability in the full specification is production-complete.

| Requirement | Status and evidence |
|---|---|
| Codex skill | Repository-discoverable `.agents/skills/camera-atlas`, explicit and implicit invocation metadata, structural validation passed |
| Installable CLI and API | Built sdist/wheel, clean core installation and render verified |
| Real vector/DEM maps | Authenticated-source example extracts; validated source records and per-feature IDs; audit trust boundary documented |
| Original photography and editable layers | No global regeneration/grade/crop, transparent PNG and SVG, normalized base layers, pixel invariants tested |
| Exact and region-level position | Both supported; named locality never becomes camera GPS |
| Location ambiguity | Multiple candidates remain unresolved; no guessed camera location |
| Providers/cache/retries/fallback | Abstract provider, offline/NaturalEarth/Overpass/DEM, configured geocoder, SQLite cache and explicit ProviderChain |
| Modes/design system | All seven modes/five themes implemented; automatic selection uses real in-extent data and optional subject hint |
| Composition | Edge/contrast heuristic and manual exclusion implemented; semantic segmentation deferred |
| Text/screenshot handling | Reviewed-mask interpolation and optional Tesseract detection; screenshot hints only, no automatic UI removal |
| Automated quality control | Pixel integrity, dimensions, alpha, text bounds/collisions, exclusion, scale and contrast proxy; human aesthetic review still required |
| Reusable outputs | Full-frame layers, input hashes, source manifests and geometry export; restyle clean base without repeated repair |
| Documentation/examples | English and Chinese README, eight engineering guides plus release/validation/status, seven reproducible public-data scenarios |
| GitHub preparation | Staged Git commits, CI/release workflows, MIT code license with separate data/photo rights; public source repository published at https://github.com/Jekyll-Chan/Camera-Atlas |

See [Validation.md](Validation.md) for the actual checks and [Release.md](Release.md) for exact publication steps. Do not advertise deferred semantic segmentation, complex OSM relation support, online DEM downloads or high-bit-depth processing as implemented.
