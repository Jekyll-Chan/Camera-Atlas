# Agensi / Codex validation · 2026-11-19

Status: Agensi 2.2.1 is live and free. The real Codex photo-to-file workflow, independent patch visual acceptance, fresh installation and live patch replay passed. GitHub v2.2.1 and all four download assets are published and verified.

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

## Live Agensi 2.2.0 photo-to-file run

The first MCP update was rejected for the extensionless `LICENSE` filename. Packaging was corrected to emit the same licence as `LICENSE.txt` and sample GeoJSON as `sample/lucerne.json`. Agensi accepted all 18 text files, approved version 2.2.0 and reported `review_status: live`, `security_status: approved`, and no pending update. Live `SKILL.md`, `engine-lock.json` and `onboard.py` matched submitted SHA256 hashes.

A separate Codex CLI session loaded the live Skill and references, received only the user's photo and Kyoto locality plus the full-sky requirement, installed the pinned public source in its own environment, resolved the shrine through Photon, created a new sky mask and rendered real geography. It did not read the development checkout or reuse the earlier mask. The supplied bootstrap interpreter path was wrong; the agent found the installed Python 3.11.15 and continued. First setup needed roughly two minutes for source/dependencies; total agent work also included map acquisition and review.

The new output covered the selected sky using all nine required real map tiles. Independent checks found zero changed pixels outside the mask or at zero overlay alpha, preserved original ICC and normalized base, exact recomposition, and matching tile/geocoder hashes. The independent visual audit nevertheless found street lines crossing the main place label and source credit. Execution succeeded, but polished visual acceptance failed. The producing agent also tagged the standalone overlay with the composition ICC profile without changing pixels.

## 2.2.1 correction and remaining gates

The patch separates geographic ink from annotations and removes only underlying map ink around accepted text. This creates transparent reading space without an opaque card or altered photograph, and is represented in PNG and SVG. The renderer also exports the independent overlay with the composition ICC profile directly.

The corrected nine-tile live-case render passed an independent full-image, sky, roof-edge, label and credit review. Both collisions are gone. Only 1,492 pixels differ from the earlier live image, within text-clearance boxes or their anti-alias fringe. All source/pixel checks still pass; final and independent overlay both preserve the original 536-byte ICC profile.

Patch source is public at `966a7567f278ef825b4e1ffc07076f2437d0d829`. [CI run 44522700221](https://github.com/Jekyll-Chan/Camera-Atlas/actions/runs/44522700221) passed on Python 3.11–3.13. Local verification: 178 tests passed, two opt-in network tests excluded, lint and formatting passed. The official archive is 64,795,450 bytes, SHA256 `f89b721efd771821672bc62c780df541ee791da17b2a83a5121b50774ac7e30c`; runtime files and font assets match the accepted patch. The updated engine lock pins this source.

A fresh isolated installation of the pinned patch reported online readiness and reproduced the accepted live-case final and overlay pixels exactly, including both original ICC profiles. It imported exclusively from its installed site-packages, with no development checkout substitution.

Agensi accepted and approved 2.2.1 with the free price unchanged. A real Codex session fetched the live Skill, lock and setup helper and verified byte identity against the submitted payload. It checked the fresh installed interpreter with the fetched helper, prepared the original photo in a new private workspace, performed an actual locality search and rendered the revised map. This patch replay reused the sky mask created by the earlier independent live agent; the full photo-only region-selection exercise was performed on 2.2.0.

The live 2.2.1 final, transparent overlay and mask pixels exactly match the independently accepted patch. Both output ICC profiles are preserved; no manual postprocessing or profile tagging was needed. Zero pixels changed outside the sky mask or wherever overlay alpha is zero, and recomposition is exact. Actual full-sky, roof-edge, primary-label and complete-credit inspections passed.

[GitHub release v2.2.1](https://github.com/Jekyll-Chan/Camera-Atlas/releases/tag/v2.2.1) targets `e2f8bf7daae55ba68f3bf3ced07e6d23b0a718b9`, which pins the accepted renderer source above. [Release build 44524257895](https://github.com/Jekyll-Chan/Camera-Atlas/actions/runs/44524257895) and [CI 44524258029](https://github.com/Jekyll-Chan/Camera-Atlas/actions/runs/44524258029) completed successfully, including Python 3.11–3.13. The release contains the Agent Kit ZIP, Skill ZIP, wheel and source archive. Both ZIPs were independently downloaded from the public release and matched the locally built packages exactly:

| Asset | Bytes | SHA256 |
| --- | ---: | --- |
| Camera-Atlas-Skill-v2.2.1.zip | 33,774 | `19a7450b10698b02519dd9e174ad4e9aef25cb9646b97664fd0c2d2878b930ab` |
| Camera-Atlas-Agent-Kit-v2.2.1.zip | 1,020,502 | `16692ae1007ad18877c078cc403346aae9012d2f524778f8b3b382ff6e212409` |

Publication and the requested Codex/Agensi validation are complete for this tested case. Agensi instruction delivery is not a cloud image-generation backend; rendering still occurs in the user's capable agent environment.

These checks cover one supplied Yasaka Shrine photograph and locality. They do not establish universal photo, geography, network or agent-client compatibility. Private imagery and test artifacts remain outside this public repository.
