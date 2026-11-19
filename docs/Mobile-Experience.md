# Camera Atlas · 手机体验设计与本地原型

状态：2026-11-19，本地可交互原型。未部署为公众可访问网站。Skill 更新为 2.1.0；公开安装锁仍指向旧渲染器，尚未发布新引擎。

## 入口与操作

界面全英文，统一使用 Georgia / Times New Roman 衬线字体。只保留四步：Photo → Place → Map → Save。默认不要求登录，样片入口不要求用户先提供私人照片。页面使用单列布局，主要按钮固定在当前步骤底部，避免重复标题、教程段落和技术名词。

1. **照片**：选照片或试用公开样片。保持原图方向、构图和颜色。照片先规范化 EXIF 方向，此后的选区严格匹配规范化尺寸。当前原型接受 JPG/PNG/WebP，18 MB、1000 万像素以内。大图、HEIC 转码和截图清洗在正式版单独补齐，不假装已经支持。
2. **地点**：输入地点 → 点击候选 → 明确确认。输入发生变化时撤销原确认与旧成品。只有地区信息时用空心红圈，不生成伪精确坐标。当前原型只搜索内置旧金山/卢塞恩湖真实数据，找不到时说明，不用其他城市替代。
3. **选区**：先用上方/右侧/全部快捷区域，再用手指或鼠标涂选、擦除。蓝色显示将放置地图的区域。撤销最多三步。当前手动选区不冒充自动天空识别。对话与界面共享 `region_mask` 规则。
4. **下载**：真实渲染 → 原图对照 → 下载 PNG。更多菜单提供透明地图、选区和来源文件。改图时始终从干净底图重新合成，不能在旧成品上叠第二层地图。改照片、地点、选区或线条深浅后旧成品失效。

默认界面仅保留必要英文短词。预览范围在照片页简短显示，隐私和功能边界放入顶部“预览版”说明。错误发生时就地提示。页脚只保留 Jekyll Chan 与 flyawaypencil480@gmail.com，不放菜单、宣传语或其他链接。

## 动效

首屏淡入并上移 6px，步骤内容上移 5px 淡入，导航下划线平滑移动，按钮按下轻微缩至 98.5%。时长约 250–650ms，使用缓出曲线。图片不进行大幅缩放或旋转。生成时显示细线旋转提示，不伪造进度百分比。遵循设备的减少动态效果设置，参见 [MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)。

## 区域铺满契约

- 底图、白色区域蒙版、可选主体保护蒙版三者同尺寸。
- 选区外框决定地理窗口比例，长轴按比例扩展真实范围，两个轴使用相同米/像素比。
- 渲染时不留方形内框、默认 20% 上限或地图底栏空白。最终透明图层裁入选区，建筑/人物等黑色区域不受影响。
- 在线数据查询必须覆盖扩展后的窗口。已有离线小范围数据不会自动增补，不能靠拉伸或重复填空。全球数据接入前，需要实现覆盖范围声明与补取流程。
- 校验地图几何在选区各部分的分布，排除地名、标记、署名对结果的干扰。稀疏真实地理不等于错误，分布计数也不等于美学验收。始终检查实际图片。
- 原图和区域之外的像素不变。缺少可靠几何时不给出“制作成功”的假结果。

## 当前实现与运行

界面：`src/camera_atlas/web/`。本地服务：`camera_atlas.mobile`。复用正式渲染路径，非前端伪造地图。公开示例来源及许可见 `examples/data/photos.sources.json`、GeoJSON 内 sources。

在本仓库的已安装环境运行：

```bash
python -m camera_atlas.mobile --port 8765
```

访问 `http://127.0.0.1:8765/`。原型仅绑定本机，适合桌面上的手机尺寸预览；没有开放局域网/公网，真实手机目前不能直接访问这个地址。上传与结果现在保存在 `~/.local/share/camera-atlas/mobile`，可用 `--storage` 指定其他私有目录。停止服务不删除文件；当前尚无自动过期清理。一个目录只能启动一个服务，队列执行器适用于 macOS/Linux。

API：`GET /api/places` 返回内置候选；`POST /api/photo` 接收原图；`POST /api/sample` 载入公开样片；`POST /api/jobs` 提交照片 ID、已确认地点 ID、原尺寸蒙版和透明度，返回任务 ID；`GET /api/jobs/{id}` 查询状态；`GET /api/jobs/{id}/input` 恢复输入；`POST /api/jobs/{id}/retry` 重试失败任务；`GET /files/{id}/...` 提供已登记的允许文件。旧同步 `/api/render` 保留兼容，网页已使用异步任务。以上接口只有本机保护，尚无公网多访客授权。

刷新页面会恢复此浏览器最近已提交任务；失败后可重试同一输入。尚未提交的编辑内容不保证跨刷新保留。`ready` 表示文件可下载，仍需检查地图分布，不是自动美学验收通过。

## 公众上线前的下一批工作

1. 地点搜索接入合规提供商，候选包含国家/城市/边界。记录用户确认版本，地点变化后重新选择数据。不要默认把公共 Nominatim 当无限量后台服务。
2. 按完整选区窗口获取矢量/DEM，记录数据覆盖范围与时间。可观察的请求失败、排队、取消和重试应保留照片与选区，不清空用户操作。
3. 将手机端选择/确认链条与服务端任务队列结合；照片访问权限、文件删除期限、限额与并发内存控制需在公开部署时实现。先支持无账号单次任务。
4. 自动天空/水面建议选区必须可编辑。截图修复独立确认并固定干净底图；保留修复记录，不宣称恢复真实被遮挡细节。
5. 在实际 iOS Safari、Android Chrome 中验证触摸涂选、相册选择、大图内存与下载。当前只验证了桌面浏览器的手机尺寸布局。
6. 发布包含 region-mask 的引擎版本，更新并校验 Skill 的不可变安装锁，再更新 Agensi 商品包。当前旧商品包不自动获得新能力。

## 验收

自动化测试覆盖：横长/竖长区域、主体空洞、选区外像素一致、等比例投影、扩展后的查询范围、空选区、未知地点、未确认地点、错误尺寸蒙版和真实渲染文件。浏览器手工验证样片→地点确认→选区→生成→实际下载，并检查空选区禁用、擦除和无页面脚本错误。没有把布局检查宣称为实际手机设备实测。

## Local entry-point fix

Styles/scripts now use relative URLs, and the server sets explicit HTML/CSS/JavaScript content types. Direct file views show a view-only notice instead of calling unavailable APIs. The local launcher uses --open-browser after the server binds, so it opens the functional HTTP entry automatically. A self-contained design preview is also exported with inline styles/scripts; rendering still requires the local service.


Backend implementation design: [Kernel-Pipeline.md](Kernel-Pipeline.md). This is a staged design, not a claim that the global pipeline is implemented.

公众产品的最终目标为“上传照片和地点，自动交付”，手工涂选降为可选编辑；当前四步原型用于验证内核。平台与上线方案见 [Public-Service.md](Public-Service.md)。
