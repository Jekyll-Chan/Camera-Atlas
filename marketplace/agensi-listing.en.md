# Camera Atlas — Free v2

Price: Free. Skill version: 2.0.0. Engine: 0.1.0, pinned verified source.

Turn an original travel photograph into restrained editorial artwork with real geographic map annotation. Keep the photograph's framing and color, return an independent transparent layer and explain data sources. Start with a photo and a place; exact camera GPS is optional.

The skill checks your agent first. With Python 3.11+ and file access it can set up an isolated local engine and render. Without suitable execution tools it delivers a clearly labeled editorial plan, not an image. Without visual tools it will not claim image inspection. A public NASA/Natural Earth sample lets you try the workflow before supplying private photos.

Needs access to:
- Your authorized photo input and output files for rendering.
- Python 3.11+ and package installation in an isolated workspace for the render route.
- Network for first setup and online geography; reliable local data can support offline rendering after setup.
- Image understanding for visual composition review; otherwise human review is required.
- Browsing or trusted supplied sources for externally verified planning facts.

Includes English and Simplified Chinese beginner guides. No paid Agensi image tool, generative photo regeneration or geocoder API key is required by the core/sample workflow. Your AI agent and infrastructure may have separate costs. No hosted rendering service is included.

Important limits: subject saliency is a texture heuristic; complex OSM relation assembly, automatic DEM download, high-bit-depth processing and universal agent compatibility are not implemented. Missing geography yields a clean photograph or an explained plan. Text interpolation requires a reviewed mask and cannot recover authentic hidden details.

Source and full technical documentation: https://github.com/Jekyll-Chan/Camera-Atlas . Code is MIT; geographic data and photos retain their own licenses. Do not upload private originals to a public gallery.

Status: submission copy only; not yet approved/listed/tested inside Agensi. Actual user-facing listing must keep the requirements and limits visible.
