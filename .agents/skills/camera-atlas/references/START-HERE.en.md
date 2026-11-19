# Camera Atlas v2.2: a photo and a place

Use an agent that can open your photo, run local commands and show the finished file. First use needs setup; later sessions can reuse that environment.

## Through Agensi

1. Connect your agent using [Agensi's official guide](https://www.agensi.io/docs/mcp-setup). Sign in to your own Agensi account when prompted.
2. Ask it to load the free [Camera Atlas](https://www.agensi.io/skills/camera-atlas) Skill and check that the returned Skill version is **2.2 or later**. If an older version is still live, use the source kit below; the older version cannot provide this full-region workflow.
3. Attach a photo and send:

> Use Camera Atlas on this photo, taken at [PLACE + CITY/COUNTRY]. Handle setup and rendering for me. Fill the appropriate whole sky or water region with real map linework, protect the subject, and preserve orientation, framing, colors and light. Ask only when the place or composition is uncertain. Give me the finished image, transparent map and source report.

The agent prepares a separate Python environment, finds the location, selects the region and exports the files. You do not need to draw a mask, find map coordinates or run code. Normal permission prompts from your agent may appear during first setup.

## Without an Agensi connection

Use the **Camera Atlas Agent Kit**, which includes the renderer source. When v2.2 is published, get it from the [release page](https://github.com/Jekyll-Chan/Camera-Atlas/releases/tag/v2.2.0) or [Agent Kit download](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.0/Camera-Atlas-Agent-Kit-v2.2.0.zip).

Extract it, open **Camera-Atlas** in your agent, and attach your photo. Add this sentence before the request above:

> Read `.agents/skills/camera-atlas/SKILL.md` in this project first.

The smaller [Skill ZIP](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.0/Camera-Atlas-Skill-v2.2.0.zip), when published, contains instructions and the verified installer. Importing it does not itself install the renderer. See the [validation report](https://github.com/Jekyll-Chan/Camera-Atlas/blob/main/docs/Agensi-Live-Validation.md) for observed publication and test status.

## Your files and revisions

Open **final.png** for the artwork. **map_overlay.png** is the transparent map; **provenance.json** records its sources. A text plan is not a rendered image.

To revise: “Use the same clean base. Extend the map across the whole sky, make it fainter, and protect the branches.” Exact GPS is usually unnecessary; add a city or country for ambiguous place names.

## Requirements and limits

- The agent needs Python 3.11+, file access, command execution, image inspection and permission for isolated first-time installation. It handles the commands.
- The local route accepts up to 18 MB and 25 megapixels without resizing. HEIC needs an optional decoder. Unsupported HDR/high-bit-depth or unpreservable color-profile inputs need an approved export, not a silent color conversion.
- Maps and dependency downloads need a working network; existing verified offline data can be reused. On failure, the agent should identify the problem and preserve the photo.
- Trae and clients using DeepSeek are possible routes only when those actual tools exist. Real Trae sessions and the ordinary DeepSeek website/app have not been verified. Image upload alone does not prove execution or file delivery.

Camera Atlas adds no required cloud-hosting account or paid image-generation call. Your AI subscription/API, computer and network may still cost money. Processing happens in the authorized agent environment; image context may reach its cloud model according to that agent's settings. Map providers receive place/range queries, not the photograph.
