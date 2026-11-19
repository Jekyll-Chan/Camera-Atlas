# Agensi / Codex validation · 2026-11-19

Status: live legacy instruction delivery verified; the revised local workflow passed one supplied-photo acceptance. The accepted renderer source is public and fresh isolated setup is verified; release assets and the live Agensi rerun are in progress.

## Observed live result

- Codex CLI 0.166.0 completed OAuth with `https://mcp.agensi.io/mcp/auth`.
- A separate Codex session called `get_skill(slug="camera-atlas")` and received the free live Skill **2.0.1**.
- It fetched `references/onboarding.md`, `references/rendering.md`, and `references/engine-lock.json` through Agensi. One transport failure succeeded on retry.
- The live lock references renderer 0.1.0 at commit `f9595def3d63c56b3d0326160d28b989f39b9f8d`, not the revised region-fill source.
- Python 3.11.15 is available. This connection test did not install the live renderer, process user photos, buy tools, publish reviews or update listings.

OAuth success and loading instructions are not evidence that a finished image was produced. The previously tested public NASA sample verifies engineering behavior, not travel-photo composition.

The Agensi listing's own version is **1.0**, while its delivered Skill frontmatter is **2.0.1**. A real Codex request using the supplied Yasaka Shrine photograph confirmed that this legacy renderer only supports a capped square corner placement. That live test stopped at the capability check and did not falsely claim full-sky output.

## Supplied-photo acceptance

An independent Codex evaluation used the user's photo and the named Kyoto locality, then handled environment checks, place search, full-sky selection, real map acquisition, rendering and visual review. An initially broad place search was refined to Yasaka Shrine. No user mask or geographic file was required.

The first result exposed oversized incidental labels, a faint unlabelled location mark and repeated attribution. These defects were corrected in the renderer, with regression tests, and the complete agent bridge was run again.

The revised result passed actual full-image, full-sky, roof-edge, location-label and attribution inspection. Its original 1206 × 2134 dimensions and ICC profile were preserved; clean-base pixels matched the normalized input exactly; no pixels changed outside the sky mask or where the independent overlay had zero alpha. Recomposition exactly reproduced the delivered image. Both required real map tiles covered the requested extent; cached tile and geocoder hashes matched recorded provenance. All 14 eligible geometry-distribution cells contained real map geometry; visual review, not that statistic alone, established acceptance.

This validates one Yasaka Shrine photograph and locality, not arbitrary photos, every agent or every network. The user's image and private test artifacts are not included in this public repository. Local tests: 174 passed, two opt-in network tests excluded; lint and formatting passed.

## Local issues corrected before photo acceptance

- Urban street maps no longer lose all road context merely because a water feature is present.
- The agent can revise map mode and geographic radius; online revisions query the expanded true bounds and keep the location identity unchanged.
- Common 12 MP phone inputs are accepted without resizing, and anonymous HEIC inputs select the optional decoder before opening.
- Original format, orientation and available GPS are kept in private workspace metadata for location-conflict review.
- Onboarding separately verifies offline, region-fill and online capabilities, including actual imports of the bridge and vector decoder. A legacy or incomplete install cannot report the primary workflow ready.

## Published source and fresh installation

The accepted renderer is public at immutable commit `aff52e15153809eb95b07f23f83ccbd2242cbf87`. [GitHub CI run 44519181301](https://github.com/Jekyll-Chan/Camera-Atlas/actions/runs/44519181301) completed successfully on Python 3.11, 3.12 and 3.13, including tests, lint, formatting and package builds.

The official commit archive was downloaded and verified against all runtime source files, bundled font assets and public sample hashes. Its size is 64,790,955 bytes and SHA256 is `0af51fe4156fbd8f61ab1ee9cff29cbbfcdf9efa7a77dbcfebaae89baccaed04`. The v2.2 engine lock declares the agent bridge, region-fill and online-map capabilities and pins this exact archive.

A new isolated environment installed this locked archive and its `maps` dependencies. The actual interpreter reported `online_ready: true`; it did not use an editable development checkout. The fresh installation independently completed photo preparation, actual Photon search, fresh map acquisition and rendering using the already reviewed mask. Visual and pixel checks passed, including zero changes outside the sky, preserved ICC and exact output-pixel agreement with the accepted development render. This installation check reused the reviewed mask; it is not a second blind region-selection test.

## Remaining release gates

1. Publish the versioned source kit and text-only Skill package, and verify the Agensi submission outcome.
2. After approval, load the live new Skill through Codex and verify actual photo-to-file execution again. A prepared package or submitted update is not yet a tested live version.

The old Agensi version remains the last verified live version at this checkpoint. No claim is made that arbitrary photographs, every geography or every agent client are already verified.

The first v2.2 MCP update submission was rejected because the platform requires a recognized text extension on `LICENSE`. No pending update was created. The package builder now emits the unchanged licence as `LICENSE.txt` and the unchanged sample GeoJSON as `sample/lucerne.json`, with a packaging regression check. Resubmission is pending at this checkpoint.
