# Planning route: useful work without pretending to render

Choose this route when the user requests advice, the agent has no usable Python/file environment, setup fails, or required reliable data cannot be obtained. Explain once: "I can prepare the design and source plan here; this environment cannot produce the image file." Use the user's language, not that fixed sentence if it would sound unnatural.

Use the actual photo when a vision tool can inspect it. If not, request one concise description (main subject, clear sky/water/background, orientation), and label judgments as based on that description. Do not claim EXIF, pixel preservation, subject detection, edited outputs or a rendered map without executing the relevant tools.

Deliver a short, actionable plan:
- Input: photo seen or described; supplied place; what remains missing.
- Geographic confidence: camera GPS / named locality / broad region / unresolved. List actually checked source links and uncertainty. No browsing means no claim of external verification; leave geographic shapes and coordinates unresolved.
- Composition: suitable map corner/size/ink as a proposal, subjects to protect, whether labels help. A proposed corner is not a computed saliency result.
- Data required: vector shore/road/river or real DEM; source/license restrictions; ambiguous place question if necessary.
- Production handoff: the photo reference, confirmed place and precision, selected theme/mode, exclusions and sources. Explain that the actual original photo must be supplied again when switching agents; do not upload it automatically.

The user should receive a usable editorial brief, optionally as Markdown/JSON if file output is available. Label it "Design plan / not yet rendered" (or Chinese equivalent). Do not provide fake download links, a blank placeholder image, generated geographic lines, invented altitude, or an assertion that a plan is the requested final photograph. If the user needs a finished image, explain the missing execution capability and offer to continue in a code-enabled environment.
