# Skill usage — Free v2.0.0

Repository path: `.agents/skills/camera-atlas/`. Open the repository in a compatible Codex session; invoke `$camera-atlas` or describe editorial travel-photo map annotation. Frontmatter supplies discovery metadata; `agents/openai.yaml` allows implicit invocation. Read [official skill documentation](https://learn.chatgpt.com/docs/build-skills) for the discovery paths supported by your installed Codex version.

To install personally, copy only that `camera-atlas` directory into a user skill directory supported by your Codex version. Install the Python package separately using the repository path and tell the agent where the checkout lives. Skills are instruction/resources; they do not bundle a Python runtime or install dependencies automatically. A newly copied skill may require a new session.

The skill is progressive: the main file routes to geography and design references when needed. It guides image inspection, location precision, optional reviewed text masks, real-data acquisition, transparent rendering, composition verification and file return. No OpenAI API key/model service is required. Original private photography is never a publishable example merely because the skill processed it.


The current Skill is v2.0.0, with the pinned engine still at 0.1.0. See [Agensi adapter](Agensi-v2.md), [English beginner instructions](../.agents/skills/camera-atlas/references/START-HERE.en.md), and [中文新手指南](../.agents/skills/camera-atlas/references/START-HERE.zh-CN.md). Render capability, installation, visual inspection and external geographic access must be checked per agent; when unavailable the skill delivers a labeled plan instead of claiming an image.
