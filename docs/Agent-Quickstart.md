# Camera Atlas · 照片＋地点 / Photo + place

Skill v2.2 使用你已有的 Agent 制图，无需 Camera Atlas 云后台。首次使用需准备环境；只有上传图片能力的普通聊天窗口不一定能执行。发布和实测状态见[验证记录](Agensi-Live-Validation.md)。

Skill v2.2 runs in your own capable agent, without a Camera Atlas cloud backend. First use needs setup; image upload alone does not establish execution support. See the [validation record](Agensi-Live-Validation.md) for observed publication and test status.

## 中文

1. **已有 Agensi 连接**：让 Agent 加载免费的 [Camera Atlas](https://www.agensi.io/skills/camera-atlas)，确认返回的 Skill 为 2.2 或更高。连接方法见 [Agensi 官方指南](https://www.agensi.io/docs/mcp-setup)。
2. **不使用 Agensi，或平台仍提供旧版**：使用 v2.2 **Agent Kit**，解压后在 Codex 或其他有文件、命令和看图能力的 Agent 中打开 **Camera-Atlas** 文件夹。让它先读取 `.agents/skills/camera-atlas/SKILL.md`。
3. 上传照片，填上地点，发送：

> 请用 Camera Atlas 加工这张照片，地点是【地点＋城市/国家】。请你完成环境准备、查真实地图、选区和导出，我不会运行代码。地图铺满适合的整片天空或水面，避开主体，保留方向、构图、颜色和光影。只在确实不确定时问我，最后给我成品、透明地图和来源文件。

首次下载可能需要确认工具的正常访问权限，之后通常可复用。无需手动画选区或提供精确 GPS。修改时说：“用同一张干净底图，把地图铺满整片天空，再淡一点。”

**final.png** 是成品；**map_overlay.png** 是透明图层；**provenance.json** 是来源报告。只有文字方案不算出图。更多帮助见[中文小白指南](../.agents/skills/camera-atlas/references/START-HERE.zh-CN.md)。

## English

1. **Agensi already connected:** load the free [Camera Atlas](https://www.agensi.io/skills/camera-atlas) Skill and check that its returned version is 2.2 or later. See [Agensi's connection guide](https://www.agensi.io/docs/mcp-setup) for first setup.
2. **Without Agensi, or while an older version is live:** extract the v2.2 **Agent Kit**, open **Camera-Atlas** in Codex or another agent with file, command and image tools, and ask it to read `.agents/skills/camera-atlas/SKILL.md` first.
3. Attach your photo and send:

> Use Camera Atlas on this photo, taken at [PLACE + CITY/COUNTRY]. Handle environment setup, verified map data, region selection and export for me. I do not know how to run code. Fill the appropriate whole sky or water region, protect the subject, and preserve orientation, framing, colors and light. Ask only when something is uncertain. Return the finished image, transparent map and source report.

First use may need normal permission prompts and dependency downloads. Later sessions can reuse the environment. You do not need to paint a mask or supply exact GPS. To revise: “Reuse the same clean base. Fill the whole sky and make the map fainter.” A text plan is not a rendered image. See the [English beginner guide](../.agents/skills/camera-atlas/references/START-HERE.en.md).

## 下载 / Downloads

v2.2 发布后，以下文件会出现在[版本页面](https://github.com/Jekyll-Chan/Camera-Atlas/releases/tag/v2.2.0)。下载前查看上方验证记录，勿将准备完成等同于已发布。

When v2.2 is published, these files are available on the [release page](https://github.com/Jekyll-Chan/Camera-Atlas/releases/tag/v2.2.0). Check the validation record for the observed status.

- [Agent Kit — 包含源码 / includes renderer source](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.0/Camera-Atlas-Agent-Kit-v2.2.0.zip)
- [Skill ZIP — 说明和安装工具 / instructions and installer](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.0/Camera-Atlas-Skill-v2.2.0.zip)

## 条件、费用与隐私 / Requirements, cost and privacy

需要 Python 3.11+、文件读写、执行命令、看图和首次独立安装权限。Agent 处理具体操作。本地照片上限为 18 MB、2500 万像素；HEIC 需要可选解码组件。不自动缩图或将无法保真的 HDR/高位深输入偷偷转色。截图清洗和选区需复核，缺少真实地图时不能编造。

Python 3.11+, file access, commands, image inspection and isolated-install permission are required. The agent handles the operations. Local inputs are limited to 18 MB and 25 megapixels; HEIC needs the optional decoder. Unsupported HDR/high-bit-depth or color-profile inputs require an approved export. Screenshots and masks need review; missing geography is never fabricated.

Trae 和具备这些工具的 DeepSeek 客户端可按能力检查；真实 Trae 会话和普通 DeepSeek 网页/App 尚未完成验证。Camera Atlas 不要求额外云托管或付费生图服务，但用户的 AI 订阅/API、电脑和网络仍可能收费。地图服务收到地点/范围，不接收照片；照片是否进入云端模型取决于 Agent 设置。国内网络可达性仍需实测。

Trae and capable clients using DeepSeek must be checked by their actual tools; real Trae sessions and the ordinary DeepSeek website/app are not yet verified. No additional Camera Atlas hosting or paid image-generation service is required, but your agent/API, device and network can have costs. Map services receive place/range queries, not photos; model image-context handling follows the agent's settings. Regional network access still needs testing.
