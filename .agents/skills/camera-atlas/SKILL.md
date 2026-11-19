---
name: camera-atlas
description: Create photography-preserving travel-zine artwork with verified geographic overlays, or deliver a clearly labeled editorial plan when the user's agent cannot render. Use for travel, landscape, and architectural photographs with real map annotation.
metadata:
  version: "2.2.0"
  distribution: "Free Agensi adapter and repository skill"
---

# Camera Atlas · Free Skill v2.2 · Bring your own agent

Reply in the user's language. The user supplies a photo and a place; the agent handles setup, verified geography, region selection and file delivery. Use the full selected region as the map viewport, following [region-fill.md](references/region-fill.md). Before rendering, verify the actual agent bridge, `region_mask` support and online map decoder. A package version label alone does not establish these capabilities.

Rendering runs through the user's code-capable agent without a Camera Atlas cloud account or server. Agensi delivers these instructions; the source-bundled Agent Kit is an alternative. Read [agent-workflow.md](references/agent-workflow.md) for the common workflow. A standalone Skill import still needs the renderer: use the verified immutable source in [engine-lock.json](references/engine-lock.json), or the trusted source kit. If a received lock lacks the declared agent/region/online capabilities, do not install it as the v2.2 workflow. Verify actual file access, execution and image inspection rather than inferring them from the model/product name.

## Requirements for rendering

Rendering runs on the buyer’s machine. The agent needs local Python 3.11 or later, permission to read the chosen photo and write output files, and permission to create an isolated Python environment and install the renderer on first use. First setup needs network access unless the verified source and dependencies are already available locally. Check actual online readiness, including the region renderer, agent bridge and map decoder; the old engine's version label alone is insufficient. HEIC originals need the optional HEIF decoder in the same environment. The planning route is available when these requirements cannot be met.

Try the [public sample](references/public-sample.md) to see the inputs and expected result.

## Start simply

Use the supplied photo/place first. Ask together for only the missing photo and location. Do not request exact GPS when a named locality is sufficient. If useful, offer a public sample instead of asking for private photography.

Check actual capabilities before promising files:
- **Render:** the agent can execute Python 3.11+, read/write image files and access the engine. Use the workflow below. Image inspection is needed to claim a visual review; if unavailable, report only automated checks and request human review.
- **Plan:** no usable execution environment, installation/network unavailable, or user wants advice. Read [planning.md](references/planning.md). Deliver an editorial plan with verified facts and uncertainties; never present it as an edited photograph. Without vision, ask for a description and say the image was not inspected.

Explain the selected route in one plain sentence. Do not make the user choose technical modes or install GIS libraries manually. Never purchase a tool, subscribe, or upload private photos/GPS to a new service as an implicit setup step. This free adapter requires no paid Agensi tool.

## Render route

Read [rendering.md](references/rendering.md) when rendering. For a missing engine, read [onboarding.md](references/onboarding.md): its standard-library helper diagnoses capabilities and installs checksum-verified source into a separate environment. A lock declaring the current capabilities installs the `maps` extra by default. With a source kit, install its source with `maps` instead. Require `online_ready` from the actual interpreter, then follow [agent-workflow.md](references/agent-workflow.md). Explain the one-time download and proceed within existing installation authorization. Never install into global Python, replace another environment or downgrade a verified kit. On Agensi, fetch supporting text files on demand and run scripts unchanged from temporary files, with explicit paths; no checkout or skill-directory working path can be assumed.

Resolve explicit input/EXIF/locality and any conflict. Ambiguous names require disambiguation. Region centers use open rings; only actual camera GPS uses solid marks. Obtain traceable vector data; contours require real DEM. Read [geography.md](references/geography.md) for sources, licensing and public-service limits. Missing verified data means a clean photograph or a plan with a clear explanation, never invented map lines.

Keep original framing, normalized pixels, orientation and color. Use independent layers over `clean_base.png`; never send the entire photograph for regeneration merely to add a map. Old-text repair needs a reviewed mask and is not authentic recovery of hidden scenery. Reuse the approved clean base on every revision, never an older screenshot or a previous composited final.

Read [design.md](references/design.md) for placement. When the user names an area (whole sky, water, trees, a drawn selection), **that entire area is the map viewport**. The 15–25% composition suggestion is not a size cap. Read [region-fill.md](references/region-fill.md): select the full area, protect subjects, expand real geographic extent at uniform scale, clip by the irregular mask, and inspect spatial distribution. Do not stretch a square, tile/repeat features, fill empty space with invented roads, or treat a large transparent PNG as proof of map coverage. If no area is specified, propose or select a suitable negative-space region from the actual photo; do not silently use the old square-corner heuristic.

Return `final.png` first, then transparent `map_overlay.png`, region mask, optional SVG and provenance. Inspect both the whole photo and the selected region, including distant edges and subject holes. Automated ink coverage/bounding boxes cannot prove that the map fills the region. Explain missing source extent, location precision and whether visual review was possible. A clean fallback or partially mapped region must be labeled as such. Keep private originals local to the authorized agent environment.

## Beginner help

Give the user the guide in their language when requested or when connection/setup is confusing: [English](references/START-HERE.en.md) · [简体中文](references/START-HERE.zh-CN.md). Reload the live Agensi Skill on a new use and check its returned version; a listing link does not prove v2.2 is serving yet. Current release evidence is recorded in the repository's [validation report](https://github.com/Jekyll-Chan/Camera-Atlas/blob/main/docs/Agensi-Live-Validation.md). Listing approval is not universal agent compatibility. Deliver actual existing files, not a claim that another service generated them.
