# 区域铺满 · Skill 2.1 本地更新

旧逻辑在四角选择方形区域，忙碌背景还会缩小地图；渲染器内部再留边距与底部署名区。因此增加图层尺寸不一定增加实际地图范围。

新增 `--region-mask /path/region.png`：白色允许地图，黑色保护照片，尺寸必须与规范化底图一致。选区可横长、竖长或包含主体空洞。选区模式忽略 map-area 和 corner position 的比例/位置限制。

地图投影使用选区外框比例，保持统一米/像素，并扩大长轴地理范围。渲染覆盖完整窗口，然后按选区裁剪透明图层。署名在允许区域内寻找可读位置，不保留大块底栏。没有空间时报告原因。

```bash
camera-atlas render --input clean_base.png --geojson verified-expanded.geojson \
  --location 'Verified locality' --region-mask selected-region.png \
  --radius-km 2 --offline --svg --output new-result
```

radius 为短轴半跨度，示例数值不适用于所有数据。地图坐标与照片透视没有地理配准关系，标记艺术位置移动不改变地点坐标。

在标准独立图层外，输出 `map_region_mask.png`、geometry-only 分布诊断、完整投影范围、来源和像素完整性记录。分布计数不证明铺满或源数据完整，真实稀疏区域不能虚构填空。已有离线范围不会自动扩大，必须另取足够的真实数据。

Skill 内容、设计参考、渲染流程、双语使用补充和环境检测已同步。`onboard.py doctor` 增加 `region_fill_supported` 检查。安装锁保留先前经校验的不可变版本，明确不支持新功能；当前区域铺满需要这个更新后的本地仓库。新引擎发布/锁更新/Agensi 包发布尚未执行。

手机交互设计与当前运行方法见 [Mobile-Experience.md](Mobile-Experience.md)。
