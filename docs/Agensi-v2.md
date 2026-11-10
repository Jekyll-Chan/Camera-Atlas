# Camera Atlas Free Skill v2.0.0

This release adapts the existing open-source engine to text-delivered Agensi skills and beginner use. The Skill version is **2.0.0**; the Python package stays **0.1.0**, pinned to an immutable, previously verified commit and SHA256. This is an adapter release, not a claim of a new renderer or hosted service.

Beginner instructions: [English](../.agents/skills/camera-atlas/references/START-HERE.en.md) · [简体中文](../.agents/skills/camera-atlas/references/START-HERE.zh-CN.md).

| Agent capability | Behavior |
|---|---|
| Python 3.11+, image files, trusted engine | Render actual final PNG, transparent layer, SVG and provenance |
| Supported Python, engine missing, installation authorized | Explain and prepare one isolated environment; no global install |
| No execution/installation, or user wants advice | Deliver a clearly labeled editorial plan |
| No vision | Use user description; never claim visual inspection; automated rendering still needs human review |
| No verified geographic data | Clean photo or plan with reason; never fabricated geography |

The standard-library `onboard.py` supports read-only doctor, verified isolated setup, and a real public demo. It is designed to run unchanged from a temporary file, with an explicitly fetched lock JSON. Setup only uses the official immutable source and checks its digest before installation. Public demo inputs also have pinned SHA256; no private images are transmitted. It downloads roughly 61 MB of source plus dependencies during first setup. Core, terrain, repair and HEIC dependency capabilities are reported separately.

## Platform packaging

```bash
python scripts/package_agensi.py --output dist/camera-atlas-agensi-v2.0.0.zip
```

The package contains one Skill, bilingual guides, supporting references, a standard-library helper, a source lock and the MIT code license. It contains no source photos, raster terrain, virtual environment, secrets or compiled executable. Source code and example photography/data keep their existing license boundaries. Do not upload the full project source archive as the skill package.

Platform declarations checked against official docs on 2026-11-10:
- [Packaging](https://www.agensi.io/docs/packaging): text/code delivery, temporary exact script execution, 50 MB website / 5 MB agent upload, no bundled dependency environments.
- [Loading](https://www.agensi.io/docs/how-agents-load-skills): on-demand file loading, actual session requirements, newest version and temporary scripts.
- [Product formats](https://www.agensi.io/docs/what-you-can-sell): skills/packs, no hosting of our own server.

No paid Agensi tool is configured or needed. There is no external checkout link. Optional paid AI/agent plans or infrastructure costs remain separate. The adapter does not assume every connected agent can run Python, inspect photos, install dependencies or contact geography providers.

## Status

The local package, helper, source lock and engine/demo paths are testable without an Agensi account. Marketplace security review, account connection, listing approval and a real buyer session have not been verified. Listing copy is prepared under `marketplace/`; no claim of platform certification, guaranteed compatibility, sales or user demand is made.


## Recorded validation — 2026-11-10

- Local suite: **69 passed**, one live-network test excluded by default.
- Ruff lint/format and Skill structural validator passed.
- Deterministic text-only package: **13 files, about 22 KB**, verified per-file SHA256 and repeatable ZIP output.
- Copied the helper into an unrelated temporary location and supplied the lock file explicitly. A clean Python 3.11 environment correctly recommended setup; checksum-verified isolated installation succeeded, without using a global engine.
- Downloaded the actual pinned official source archive and verified its SHA256. The full install used that matching local archive to avoid downloading the same 61 MB twice.
- The standalone helper fetched three checksum-verified public demo inputs and rendered a real NASA/Natural Earth sample. Dimensions 1276×1280 preserved; zero unexpected base/composite pixel modifications; transparent overlay and SVG exported.
- Actual Agensi login, skill delivery, review and buyer-session execution remain untested. Local validation is not marketplace certification.
