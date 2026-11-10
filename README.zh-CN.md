# Camera Atlas

**Photography First. Geography Verified. 摄影优先，地理可核查。**

[GitHub 开源仓库](https://github.com/Jekyll-Chan/Camera-Atlas)

Camera Atlas 在原始摄影上叠加独立透明地理图层，生成克制的旅行杂志式作品。它不使用生成式图像模型重绘照片，不全局调色，不强制裁切。提供 Python CLI、可复用 API、Codex Agent Skill 和可追溯输出。当前版本为 0.1.0 初始版本；能力与限制均在下方说明。

[English README](README.md) · [架构](docs/Architecture.md) · [CLI 全选项](docs/CLI-Reference.md) · [精度和溯源](docs/Accuracy-and-Provenance.md) · [公开示例与许可](examples/README.md)


## 免费 Skill v2

**Skill 版本 2.0.0；Python 引擎保持 0.1.0。** 新版先检查 Agent 能力，可自动准备独立环境并运行公开样片；能制图就输出实际文件，不能执行则明确交付设计方案。它是已准备的免费适配版，不表示已经在 Agensi 上架或所有 Agent 都通过实测。

先看：[中文小白指南](.agents/skills/camera-atlas/references/START-HERE.zh-CN.md) · [English beginner guide](.agents/skills/camera-atlas/references/START-HERE.en.md) · [v2 说明](docs/Agensi-v2.md) · [版本记录](CHANGELOG.md)。


## 安装

要求 Python 3.11+。在仓库根目录运行：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install '.[terrain,repair]'
camera-atlas --help
```

只用矢量图层可 `pip install .`。可选依赖：`terrain` 为 rasterio/contourpy，`repair` 为 OpenCV，`heic` 为 HEIC 解码，`dev` 为测试、检查和构建工具。离线功能不需要模型服务或 API Key。TIFF/HEIC/HDR 均规范化为 8 位 RGBA；本版不提供高位深归档合成。

## 使用

明确拍摄 GPS（下列数值仅为命令示例，请替换为真实拍摄点）：

```bash
camera-atlas render --input photo.jpg --lat 46.98 --lon 8.60 \
  --geojson examples/data/lucerne.geojson --radius-km 45 --offline \
  --svg --scale --output render-output/lake
```

只有地区信息时不必提供精确 GPS：

```bash
camera-atlas render --input photo.jpg --location 'Lake Lucerne' \
  --geojson examples/data/lucerne.geojson --radius-km 45 --offline \
  --output render-output/locality
```

地点名使用配置好的 Nominatim 兼容服务查询，或匹配离线 GeoJSON 的已声明地区。不会默认启用公共地名服务。查询多个结果时保持未解决状态，并返回候选；不得凭热度选取。若只知道区域中心，使用 `--confirmed-region --lat ... --lon ...`，输出空心地区标记，不伪装成精确机位。

```bash
camera-atlas render --input photo.jpg --location 'Sayram Lake, Xinjiang, China' \
  --nominatim-url https://你的合规地名服务 \
  --output render-output/sayram
camera-atlas render --input photo.jpg --lat 46.90 --lon 8.60 --confirmed-region \
  --dem terrain.tif --dem-source terrain.source.json --map-mode topographic \
  --contour-interval 100 --offline --output render-output/terrain
camera-atlas batch --input photos --manifest locations.csv --output render-output/batch
```

批处理 CSV 必须有 `file` 列，可加 `lat,lon,location,geojson,dem,dem_source,confirmed_region`。照片路径限于输入目录内，地理数据路径相对于 CSV。串行执行，默认离线，每行错误记录于 `batch_report.json`，其余行继续处理。公开服务不可用或无可靠几何时安全降级为干净摄影，并在结果中报告原因。

## Python API

```python
from camera_atlas import RenderConfig, render

result = render(
    RenderConfig(
        input="photo.jpg",
        output="render-output/api",
        location="Lake Lucerne",
        geojson="examples/data/lucerne.geojson",
        offline=True,
        radius_km=45,
        svg=True,
    )
)
print(result.final, result.metadata["quality"])
```

输出通常包含 `final.png`、规范化 `original.png`、`clean_base.png`、真正带 alpha 的 `map_overlay.png`、显著性掩膜、`location.geojson`、`metadata.json` 和 `provenance.json`。`--svg` 可加可编辑矢量图层；文字修复时另存掩膜。`--no-layers` 关闭摄影分层导出。目标目录必须为空，输入原文件不被覆盖。重新设计时用 `clean_base.png` 和已导出的 `location.geojson` 离线渲染，不重复修复底图。

## 摄影、文字与构图

EXIF 方向只规范化一次，ICC 配置保留，照片不缩放、不裁切、不做全局调色。除透明图层覆盖区域和明确授权的文字修复区域外，程序验证规范化像素完全一致。原始压缩文件保留在输入位置；规范化 PNG 并非原 JPEG 文件的字节副本。

七种地图模式：coastline、topographic、urban、trail、river、regional、minimal；自动选择只使用当前地理范围内真实可用的数据，可用 `--subject` 提供主体提示或 `--map-mode` 手动覆盖。五种主题使用同一地理引擎。默认地图约占 20% 画幅，细暖白线、较低透明度，不加中央标题或不透明卡片。`--no-labels` 可关闭可选文字，但数据许可要求的署名必须保留。

负空间分析仅使用边缘密度与局部对比度，不是语义分割；不能可靠识别人、山峰、建筑、船只或天空。可用 `--exclusion-mask` 保护明确主体，非零像素不被地图覆盖。截图黑条仅作启发式提示，不自动裁切播放器。所有成品仍须人工检查构图与可读性。

可选 `detect-text` 依赖系统 Tesseract，只生成候选掩膜。审阅后显式传入 `--remove-text --text-mask reviewed.png`，才用 OpenCV TELEA 局部插值。它无法恢复被文字遮挡的真实摄影细节；输出会标注待人工复核。修复掩膜超过画面 10% 会被拒绝，区域外像素不变，OCR 不用于推断位置。

## 地理精度与数据源

用户明确输入优先于冲突 EXIF 并记录冲突；否则优先 EXIF，再使用已声明地区。命名地区中心不是机位。精确 GPS 用实心标记，区域/地方用空心环；环不是伪造的误差半径。北向只表示地图方向，不代表摄影机朝向。可选比例尺使用实际投影和反投影后椭球距离；从未验证的数据中不虚构海拔、公路编号、地名或等高线。

- **OpenStreetMap**：小范围 Overpass 矢量查询，保留 OSM ID、来源网址和快照时间，ODbL 许可，图上保留署名与版权网址。本版处理 ways/place nodes，尚不组装复杂 multipolygon relations，可能漏掉大型湖泊，绝不编造补齐。
- **Natural Earth**：公有领域概览数据。数据源声明最小地理跨度，跨度太小时不绘制，避免将概览线放大为精细岸线。1:10m 是制图比例尺，绝不是 10 米精度。
- **DEM**：读取真实本地栅格并计算等高线；要求 CRS、来源许可、米制单位和可选校验和。示例为 Mapzen/Tilezen 真实高程子集。Copernicus、NASADEM、SRTM、OpenTopography 在线下载与认证适配器尚未集成，需合法取得后本地输入；本版不转换垂直基准。

每个显示地物关联来源，每次生成记录版本、URL、时间、许可、哈希、精度、投影、地图像素布局和不确定性。任意用户 GeoJSON 可以谎报来源；软件验证结构与溯源关系，不自动证明声明的真实性。请使用可信数据并检查上游来源。

**Nominatim 公共服务限制：**使用前必须阅读[现行政策](https://operations.osmfoundation.org/policies/nominatim/)。当前要求全应用合计最多每秒一次、有效应用标识、缓存，限制批量、系统性查询和 LLM 平台生成的通用服务。开发者须有意识地选择合规服务并负责遵守。公共主机另需显式 `--accept-public-nominatim-policy`；该标志不授予违反条款的权利。批处理默认离线，不提供公共地名服务开关。缓存限流只协调同一缓存目录的进程，跨机器部署须自行聚合限流。线上位置查询会向提供商披露坐标/地点。

## Codex Skill

在 Codex 中打开本仓库，发现路径为 `.agents/skills/camera-atlas/SKILL.md`。显式使用 `$camera-atlas`，或自然描述“为旅行摄影添加真实地理地图的杂志风作品”，可触发隐式调用。跨项目使用可将该目录复制到当前 Codex 版本支持的用户技能目录；Python 包需另行安装。参考[官方技能文档](https://learn.chatgpt.com/docs/build-skills)与[本项目指南](docs/Skill-Usage.md)。

## 测试、文档与开源

```bash
pip install '.[terrain,repair,dev]'
pytest --cov=camera_atlas
ruff check .
ruff format --check .
python -m build
python examples/build_examples.py --output render-output/examples
```

离线 CI 不依赖公开 API 永久在线，真实湖岸/DEM/道路测试与明确标注的数值算法栅格测试分开。在线测试需 `CAMERA_ATLAS_NETWORK=1 pytest -m network`。示例使用有来源的 NASA 公开摄影，并注明它们是航空/航天摄影工程示例，不冒充地面旅行作品。查看[效果、素材权利与数据处理](examples/README.md)。

代码 MIT；OSM 数据保持 ODbL、DEM 保持各自来源条款、照片保持素材权利，均不得宣称为代码 MIT 许可。私人摄影、GPS、API Key 不得提交公开仓库。默认不导出 EXIF，但位置 manifest 仍有地理敏感性。参阅[贡献指南](CONTRIBUTING.md)、[发布步骤](docs/Release.md)和[故障排查](docs/Troubleshooting.md)。

后续路线：OSM 关系组装、可选语义主体分析、高位深合成、垂直基准处理、合规在线 DEM 下载和更多地名服务适配器。本版未将这些未实现功能描述为已完成。


[Validation record / 实测记录](docs/Validation.md) · [Requirement status / 验收状态](docs/Acceptance.md)
