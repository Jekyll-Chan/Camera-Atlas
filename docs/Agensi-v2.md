# Camera Atlas Free Skill v2.2

Skill v2.2 provides a photo-and-place workflow through the user's code-capable agent: isolated setup, real geographic data, a reviewed full-region mask, independent map compositing and actual files. Agensi delivers instructions; it does not host this renderer. The Python package version remains **0.1.0**; the immutable revision and verified capabilities distinguish the updated engine from the older package with that same label.

Beginner instructions: [English](../.agents/skills/camera-atlas/references/START-HERE.en.md) · [简体中文](../.agents/skills/camera-atlas/references/START-HERE.zh-CN.md) · [Bilingual quickstart](Agent-Quickstart.md).

## Requirements

| Agent capability | Behavior |
|---|---|
| Python 3.11+, files, command execution and image inspection | Set up the verified renderer, review the mask and deliver real image files |
| Supported Python, engine missing, installation authorized | Prepare one isolated environment with the required map decoder |
| No execution or installation | Explain the limitation and offer a clearly labeled editorial plan |
| No image inspection | Do not claim visual acceptance; automated checks require human review |
| No verified geographic data | Preserve the photo and report the missing data; never fabricate lines |

The standard-library `onboard.py` runs unchanged from a temporary file with an explicit lock path. Setup verifies the official immutable archive's SHA256 before installation. A current lock declares `agent_bridge`, `region_fill` and `online_maps`; setup installs `maps` by default. Doctor must report `online_ready`, not only an engine version. Native source-kit installation uses the same `maps` extra. Public samples have separate verified sources and licenses.

## What changed

- A selected whole sky, water or other negative-space region sets the geographic viewport; the old square-corner size cap does not apply.
- Expanding the region or radius queries a larger real extent at uniform scale, then clips the transparent layer around protected subjects.
- The agent chooses and reviews the mask; a novice is not asked to paint it. Heuristic suggestions are not semantic segmentation.
- Map mode and radius can be revised. A city pond no longer suppresses its surrounding streets. A verified display label does not change coordinates.
- Original framing, normalized pixels, direction and supported color profiles are preserved outside actual map ink or approved repairs. Common phone photos up to 18 MB/25 MP are accepted without resizing; unsupported HDR/high-bit-depth or color-profile input is rejected rather than silently altered.

## Packages

```bash
python scripts/package_agensi.py --output dist/Camera-Atlas-Skill-v2.2.0.zip
python scripts/package_agent_kit.py --output dist/Camera-Atlas-Agent-Kit-v2.2.0.zip
```

The Agensi ZIP has `SKILL.md` at its root and contains text instructions, bilingual guides, the installer, source lock and public sample text data. It contains no private photos, environment, cache or compiled executable. The separate Agent Kit includes renderer source and licensed public samples. Never upload the entire repository archive as the text-only Agensi package.

No paid Agensi image tool is required. The user's agent/API, computer and network costs remain separate. Trae and DeepSeek client compatibility must be assessed by actual tools and sessions, not a product name.

## Publication and validation

The [validation record](Agensi-Live-Validation.md) is the source of observed status. The earlier live marketplace listing was version **1.0**, containing Skill **2.0.1**; those are different version fields. Its pinned corner-map renderer could not fulfill the full-sky test. Loading that older Skill through Codex does not validate v2.2 delivery.

For v2.2, publish and verify the updated immutable renderer, test a fresh installation from its lock, submit the new package, then load the newest live version through Codex and test actual file delivery. A prepared ZIP, submitted update, approved listing and verified photo workflow are distinct states. One supplied-photo result does not establish universal image, agent or network compatibility.

Official platform references, checked 2026-11-19: [connection](https://www.agensi.io/docs/mcp-setup), [file loading](https://www.agensi.io/docs/how-agents-load-skills), [agent submission](https://www.agensi.io/docs/submit-from-your-agent), [updates](https://www.agensi.io/docs/updates). Updates keep serving the previous live version until approved; check what `get_skill` actually returns.
