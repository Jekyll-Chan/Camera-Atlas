---
name: camera-atlas
description: Create photography-preserving travel-zine artwork with verified geographic overlays, or deliver a clearly labeled editorial plan when the user's agent cannot render. Use for travel, landscape, and architectural photographs with real map annotation.
metadata:
  version: "2.0.0"
  distribution: "Free Agensi adapter and repository skill"
---

# Camera Atlas · Free Skill v2

Reply in the user's language. The user should only need a photo and a place, not a terminal, API key or knowledge of GIS. Keep the Python engine at the verified revision in [engine-lock.json](references/engine-lock.json); Skill v2 is distinct from engine 0.1.0.

## Start simply

Use the supplied photo/place first. Ask together for only the missing photo and location. Do not request exact GPS when a named locality is sufficient. If useful, offer a public sample instead of asking for private photography.

Check actual capabilities before promising files:
- **Render:** the agent can execute Python 3.11+, read/write image files and access the engine. Use the workflow below. Image inspection is needed to claim a visual review; if unavailable, report only automated checks and request human review.
- **Plan:** no usable execution environment, installation/network unavailable, or user wants advice. Read [planning.md](references/planning.md). Deliver an editorial plan with verified facts and uncertainties; never present it as an edited photograph. Without vision, ask for a description and say the image was not inspected.

Explain the selected route in one plain sentence. Do not make the user choose technical modes or install GIS libraries manually. Never purchase a tool, subscribe, or upload private photos/GPS to a new service as an implicit setup step. This free adapter requires no paid Agensi tool.

## Render route

Read [rendering.md](references/rendering.md) when rendering. If setup is needed, read [onboarding.md](references/onboarding.md); its standard-library helper supports read-only diagnosis, isolated installation and a verified public demo. Explain the one-time setup/download; proceed within the user's existing installation authorization. Never install into global Python or replace another environment. On Agensi, fetch supporting text files on demand and run scripts unchanged from temporary files, with explicit paths; no repository checkout or skill-directory working path can be assumed.

Resolve explicit input/EXIF/locality and any conflict. Ambiguous names require disambiguation. Region centers use open rings; only actual camera GPS uses solid marks. Obtain traceable vector data; contours require real DEM. Read [geography.md](references/geography.md) for sources, licensing and public-service limits. Missing verified data means a clean photograph or a plan with a clear explanation, never invented map lines.

Keep original framing, normalized pixels and color. Use default editorial-minimal/auto; read [design.md](references/design.md) for placement and subject protection. Avoid unexplained options or repeated setup questions. Old-text repair needs a reviewed mask and is not authentic recovery of hidden scenery.

Return `final.png` first, then transparent `map_overlay.png`, optional SVG and provenance. Inspect the actual files and automated integrity report. Explain warnings, location precision and whether visual review was possible. A clean fallback must be described as a clean photo, not a successful map composition. Keep private originals local to the authorized agent environment.

## Beginner help

Give the user the guide in their language when requested or when connection/setup is confusing: [English](references/START-HERE.en.md) · [简体中文](references/START-HERE.zh-CN.md). They contain copy-and-paste requests, sample-photo and troubleshooting paths. No Agensi listing approval or all-agent compatibility has been verified yet; do not claim otherwise.
