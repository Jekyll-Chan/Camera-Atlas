# Public samples · engineering checks

Use the bridge in [agent-workflow.md](agent-workflow.md) with the verified v2.2 engine. The source kit contains two matched offline examples:

| Photo under `examples/data/` | Built-in place ID | Geography |
| --- | --- | --- |
| `city_photo.jpg` | `san-francisco` | Recorded OpenStreetMap streets/water |
| `lake_photo.jpg` | `lucerne` | Natural Earth lake outline |

Run prepare, inspect/refine the region mask, then render with the matching built-in ID; no place search or network geography query is needed. Both photographs are NASA aerial/orbital engineering samples, not ground-travel aesthetic benchmarks. An installed wheel may not contain samples; run from the extracted kit root or pass `--data /actual/kit/examples/data`.

## Lake Lucerne setup check

> Run Camera Atlas's Lake Lucerne public demo. Prepare the local environment if needed, then show me the finished image, transparent layer and source report.

The helper's `demo` command is a basic installation check, not proof of full-sky visual quality. Follow [onboarding](onboarding.md); use the current verified lock and do not replace a working v2.2 environment with an older engine. The helper obtains the public photograph, GeoJSON and source record from `demo_files` in `engine-lock.json`, checks their hashes and writes the result locally.

The example uses a NASA photograph of the Alps taken from Skylab 3 and a Natural Earth lake outline. The lake is the mapped locality, not an exact camera position. The photo source record contains credit and reuse information. The text-only Agensi ZIP includes the GeoJSON and source record under `sample/`; it downloads the matched public photograph when needed. These sample licenses do not extend to the user's private photos.

中文试用指令：

> 请用 Camera Atlas 的卢塞恩湖公开样片做一次环境检查。需要时先准备本机环境，然后给我成品、透明地图图层和来源报告。

公开航拍样片只验证安装与输出链条。真实旅行照片仍须单独检查天空边缘、主体保护、地图覆盖和文字可读性。
