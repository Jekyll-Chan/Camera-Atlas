# Camera Atlas v2.2.1：给照片和地点

使用能看照片、运行本地命令并交付文件的 Agent。第一次需要准备环境，之后通常可以复用。

## 从 Agensi 开始

1. 按 [Agensi 官方说明](https://www.agensi.io/docs/mcp-setup)连接你的 Agent，出现登录页面时登录自己的 Agensi 账户。
2. 让 Agent 加载免费的 [Camera Atlas](https://www.agensi.io/skills/camera-atlas)，检查返回的 Skill 版本是否为 **2.2 或更高**。如果平台还在提供旧版，改用下方源码包；旧版不能完成这套区域铺满流程。
3. 上传一张照片，发送：

> 请用 Camera Atlas 加工这张照片，地点是【地点＋城市/国家】。请你完成环境准备和制图。地图铺满适合的整片天空或水面，使用真实地图，避开主体，保留原图方向、构图、颜色和光影。只在地点或构图不确定时问我，最后给我成品、透明地图和来源文件。

Agent 会准备独立 Python 环境、确认地点、选择区域并导出。你不需要自己画选区、找坐标或运行代码。首次使用可能出现该工具正常的文件访问或执行确认。

## 不连接 Agensi 也能使用

选择包含渲染源码的 **Camera Atlas Agent Kit**。v2.2.1 发布后，可在[版本页面](https://github.com/Jekyll-Chan/Camera-Atlas/releases/tag/v2.2.1)或[源码包下载](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.1/Camera-Atlas-Agent-Kit-v2.2.1.zip)取得。

解压后，在 Agent 中打开 **Camera-Atlas** 文件夹，上传照片，在上面的请求前加一句：

> 请先读取项目中的 `.agents/skills/camera-atlas/SKILL.md`。

发布后的[小体积 Skill ZIP](https://github.com/Jekyll-Chan/Camera-Atlas/releases/download/v2.2.1/Camera-Atlas-Skill-v2.2.1.zip)包含说明和经过校验的安装工具；导入说明不等于引擎已安装。具体发布和实测进度见[验证记录](https://github.com/Jekyll-Chan/Camera-Atlas/blob/main/docs/Agensi-Live-Validation.md)。

## 领取和修改

**final.png** 是成品，**map_overlay.png** 是透明地图，**provenance.json** 记录来源。只有文字方案不算出图。

修改时直接说：“用同一张干净底图，把地图铺满整片天空，再淡一点，不挡住树枝。”同名地点补充城市或国家即可，通常不需要精确 GPS。

## 使用条件和限制

- Agent 需要 Python 3.11+、文件读写、命令执行和看图能力，以及首次安装独立环境的权限。具体命令由 Agent 处理。
- 本地路线支持不超过 18 MB、2500 万像素的照片，不自动缩图。HEIC 需可选解码组件；无法保真的 HDR、高位深或色彩配置输入，需要认可后的导出文件，不能偷偷变色。
- 初次下载和地图查询需要网络；已有的可信离线地图可复用。网络失败时应说明失败环节并保留照片。
- Trae、使用 DeepSeek 模型的客户端只有具备上述工具时才可能运行。尚未完成真实 Trae 会话及普通 DeepSeek 网页/App 的出图验证。能上传图片，不等于能加工并交付文件。

Camera Atlas 不要求云托管账户，也不额外调用付费整图生成服务。你的 AI 订阅/API、电脑和网络仍可能有成本。照片在授权的 Agent 环境处理；是否发送给云端模型取决于该工具设置。地图服务只需要地点/范围，不需要照片。
