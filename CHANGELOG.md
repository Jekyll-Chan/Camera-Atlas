# Changelog

## Skill 2.2.1 — 2026-11-19

Patch prepared after an independent Codex photo-and-place test of the approved, live Agensi 2.2.0 Skill completed setup, full-sky rendering and file delivery. Visual review found street lines crossing type, so workflow execution was not treated as polished visual acceptance. Publication remains separate; see [the validation record](docs/Agensi-Live-Validation.md) for the current live version.

- Clear map strokes transparently behind labels and attribution so streets do not cross letterforms. Keep the photograph unchanged and avoid opaque label cards.
- Include the composition color profile in the independent PNG overlay so it can be reused with the matching clean base.
- Update Skill, installer, package metadata and release downloads to 2.2.1. The full-region workflow still requires version 2.2 or later, plus actual renderer capability checks; the Python package label remains 0.1.0.

## Skill 2.2.0 — 2026-11-19

Photo-and-place workflow in the user's own capable agent, with optional Agensi discovery and no required Camera Atlas cloud backend. Publication and observed end-to-end results are tracked separately in [the validation record](docs/Agensi-Live-Validation.md); this entry does not establish marketplace availability.

- Source-bundled Agent Kit, text-only Agensi package and bilingual beginner guides. The agent handles setup, actual negative-space selection, verified geography, rendering and file delivery.
- Immutable checksum-verified setup with capability-gated `maps` installation; `doctor.online_ready` verifies the bridge, region support and decoder. Python package version remains 0.1.0.
- Full-region geography expands at uniform scale to fill selected bounds, clips around subjects and checks distribution across the region. No square-card cap or repeated map patches.
- Local JSON prepare/place-search/render bridge, bounded Photon/OpenFreeMap requests, revisable radius/mode and verified display labels. Named places remain locality markers rather than invented camera GPS.
- Independent transparent compositing, clean-base integrity checks, protected-pixel verification, readable serif labels and geographic attribution. Local phone inputs up to 18 MB/25 MP; unsupported HDR/high-bit-depth or color-profile inputs fail explicitly.
- Local mobile/service prototypes and durable jobs remain separate development tools, not a claim of public hosting or universal agent compatibility. Ordinary Trae/DeepSeek sessions are not verified.

## Skill 2.0.1 — 2026-11-11

The Agensi submission ZIP places `SKILL.md` at its root and includes a public sample walkthrough with its GeoJSON and photo attribution. The skill and both listing descriptions state the buyer’s local Python, file access and isolated environment requirements.

## Skill 2.0.0 — 2026-11-10

Free Agensi/repository adapter release. Python engine remains 0.1.0 at an immutable verified revision.

- Capability-based actual-render and explicitly labeled planning routes; no universal-agent claim.
- Standard-library doctor, isolated verified source setup and checksum-verified NASA/Natural Earth public demo.
- English and Simplified Chinese beginner guides and copy/paste requests.
- Lightweight text-only skill packaging and honest bilingual marketplace listing copy.
- Preserve photographic integrity, geographic precision/provenance and data/photo license boundaries.
- No paid tool requirement, private-photo publishing, marketplace signup/listing or automatic email sending.

## Engine 0.1.0 / initial Skill — 2026-11-10

Python CLI/API, transparent geography overlays, real vectors/DEM, offline/provider architecture, batch processing, reviewed-mask text interpolation, pixel validation, public examples, bilingual README and CI. Follow-up fixed color-sensitive CLI tests and SQLite connection closure. Local engine suite: 58 passed; Python 3.11–3.13 GitHub checks passed on the pinned engine revision.
