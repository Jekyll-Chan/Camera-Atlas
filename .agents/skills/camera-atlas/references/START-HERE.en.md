# Camera Atlas Free v2: your first use

Bring one photo and the place where it was taken. Let your agent handle environment checks, geographic data and output files.

## Use through Agensi

1. Sign in to Agensi and connect your agent using its official instructions: https://www.agensi.io/docs/mcp-setup . You may need to complete sign-in/authorization yourself. Availability depends on the app, account and actual tool permissions.
2. Once a listing is approved, search for **Camera Atlas**, confirm that its author/repository points to **Jekyll-Chan/Camera-Atlas**, and check that the price is **Free**. This guide accompanies a prepared adapter; it does not mean Agensi has approved or published it. If you cannot find it, use GitHub below.
3. In your connected agent's chat, attach the photo and paste:

> Use the free Camera Atlas skill for this travel photo, taken at [PLACE]. First check whether you can produce the actual image. If needed, prepare an isolated environment in this workspace. Preserve the original framing and colors, and add fine map lines from verified geographic sources. Return the final image and transparent layer. If this environment cannot render, say so clearly and give me an actionable design plan.

You do not need to know Python, map APIs or GeoJSON. Exact GPS is optional. A named lake/city is a locality, not an exact camera position. Ambiguous names may need a country or region.

## Try a public sample first

> Use Camera Atlas's public sample demo. Check the environment, prepare the necessary dependencies, and show me the final image and transparent layer. Do not use my private photos yet.

The sample uses NASA aerial/space photography and an actual Natural Earth lake outline. It is an engineering demonstration, not a ground-level travel photo. It uploads no private photograph and needs no geocoder API key.

## Understand the result

- **Actual rendering:** your agent has Python 3.11+, image file access and the required network/data. First setup may download about 61 MB of public engine source plus dependencies; the isolated environment can be reused. Open `final.png` for the artwork, `map_overlay.png` for an editable transparent map, and `provenance.json` for sources.
- **Planning only:** code execution, installation or reliable data is unavailable, or you asked for advice. You receive a clearly labeled design plan with geography, composition, protected subjects and next steps. It is not a rendered image.

Reading an image with Python is not visual understanding. If your agent cannot inspect images visually, it should report only automated checks and ask you to review composition. Missing reliable map data may also produce a clean photo without a map; that must be explained rather than called a successful map composition.

## Ask for changes in ordinary language

- "Make the map fainter and move it to the top right."
- "Remove place labels, but keep required source attribution."
- "Protect the people, main peak and boat."
- "Give me a plan only; do not install anything yet."
- "Keep all editable layers."

## Use without Agensi

Open https://github.com/Jekyll-Chan/Camera-Atlas in an agent with Python execution, then say:

> Read this repository's Camera Atlas Skill v2, check and prepare an isolated environment, then run the public sample demo. I am not comfortable with terminal commands; please handle the technical steps.

Alternatively, provide the skill folder and its supporting text resources through the mechanism your agent supports. Use the dedicated lightweight Agensi ZIP for platform submission, not the full project archive.

## Cost and privacy

This adapter is free. Core rendering does not call a paid generative-image service. Your agent/AI account and compute/network resources may have their own costs. This adapter does not automatically buy Agensi tools, start subscriptions or request API keys.

Photos stay within the agent environment you authorize. Online map queries disclose a place/area to the map provider; do not submit confidential locations. Switching agents does not automatically transfer your photo. Never put private original photos or GPS into a public repository or product gallery.

## If something gets stuck

- Cannot find the listing: it may not be published yet; use GitHub, and check authorship before using a similarly named listing.
- Connection fails: follow Agensi's official sign-in guide. Its current documentation allows one active agent connection per account; switching apps may require reconnecting.
- Missing Python/network/install permission: request a plan or use a code-enabled environment.
- No map: ask the agent to explain the provenance warnings; do not request invented geographic detail.
- No output file: ask for the actual existing `final.png` attachment/path. A plan should never be described as a completed image.

Versions: **Skill v2.0.1** is this free adapter; its pinned, tested **Python engine is 0.1.0**. v2 does not mean Agensi supplies a hosted renderer or that every agent has been tested.
