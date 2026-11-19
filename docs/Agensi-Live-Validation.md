# Agensi / Codex validation · 2026-11-19

Status: live legacy instruction delivery verified; the revised local workflow passed one supplied-photo acceptance. New-version publication and live Agensi rerun remain pending.

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

## Remaining release gates

1. Publish the accepted renderer source to GitHub and inspect CI.
2. Pin its immutable commit and checksum, and test a fresh isolated installation.
3. Build and publish the source kit and text-only Skill package, then submit the Agensi update.
4. After approval, load the live new Skill through Codex and verify actual photo-to-file execution again. A prepared package or submitted update is not yet a tested live version.

No new GitHub source or Agensi update has been published as part of this validation checkpoint. No claim is made that arbitrary photographs, every geography or every agent client are already verified.
