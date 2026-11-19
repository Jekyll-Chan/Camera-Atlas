# 免费托管政策核查

核查日期：2026-11-19。依据各平台当日官方文档；没有注册、创建或部署云服务，没有添加支付方式或购买资源。用户要求先查清政策，部署保持未执行。

## Render：可以零月租试用，但不是无限免费生产服务

必须同时选择免费 Hobby 工作区与 Web Service 的 `free` 计算方案。Hobby 无月费不代表工作区下所有实例都免费。

| 项目 | 当前官方政策 | 对 Camera Atlas 的影响 |
| --- | --- | --- |
| 计算规格 | 0.1 CPU、512 MB RAM | 需单任务执行、限制图片大小并实测内存；不能保证高清批量处理 |
| 运行时长 | 每工作区每自然月 750 小时，所有免费实例共享 | 一台实例通常足够覆盖一个月，多台共享消耗；用尽暂停 |
| 出站流量 | Hobby 每月 5 GB，工作区共享，不结转 | 页面、预览、成品和图层下载都会消耗 |
| 构建 | Hobby 每月 500 分钟 Starter pipeline | 安装依赖、构建和重新部署消耗；不是图片处理时间 |
| 休眠 | 15 分钟无入站流量自动休眠，重新访问唤醒约一分钟 | 用户首访可能等待，不能承诺随时秒出图 |
| 文件 | 休眠、重启、部署都会丢失本地修改 | 上传照片、SQLite 任务和未下载成品会丢失，不能声称云端永久恢复 |
| 持久磁盘/worker | 免费 Web Service 不支持持久磁盘；独立 background worker 没有 Free 计划 | 先在一个应用中有界处理，不额外建立付费 worker |
| 免费数据库 | Free Postgres 30 天过期 | 不作为长期免费任务库 |

来源：[免费实例规则](https://render.com/docs/free)、[计算规格](https://render.com/docs/compute-plans)、[出站流量](https://render.com/docs/outbound-bandwidth)、[构建额度](https://render.com/docs/build-pipeline)。

### 是否会自动扣费

- **没有添加支付方式**：出站流量耗尽会暂停服务至下月；构建分钟耗尽会暂停新构建，已有版本继续运行。
- **已经添加支付方式**：即使所有实例选 Free，流量或构建超额仍可能收费。当前公网出站超额为 $0.15/GB。
- Pipeline spend limit 只限制构建费用，不是所有收费项目的总开关。
- 免费额度不是现金抵扣所有产品。不能创建付费实例、磁盘或数据库后以为先扣免费额度。

来源：[计费 FAQ](https://render.com/docs/faq)、[流量价格与超额处理](https://render.com/docs/outbound-bandwidth)、[构建费用上限](https://render.com/docs/build-pipeline)。

按每次制作及下载合计出站 20 MB 粗算，5 GB 约对应 250 次；这只是算术示例，不是平台承诺或容量测试。重复预览、再次下载、源图/透明图层大小及其他访问都会改变实际数量。应用还需要限制排队与文件生命周期，而不是承诺 unlimited。

官方明确不建议将 Free 用于生产应用。外部请求流量异常高也可能被暂停；没有“不休眠”“永远可用”或公众高并发保证。不设置自动保活来掩盖这些限制。来源：[官方免费说明](https://render.com/docs/free)。

## 其他平台

- **Hugging Face**：CPU Basic 的小时价格为零，但当前新建 Docker/Gradio compute Space 要求付费计划；免费个人账户的 ZeroGPU 例外有单独条件，不能把它当作任意免费 Docker 主机。当前不据此承诺本项目免费部署。[官方说明](https://huggingface.co/docs/hub/spaces-overview)
- **GitHub**：用于代码、测试与发布；不把 Actions 当用户图片加工服务器。[使用条款](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions)
- **OpenFreeMap**：可免 API key 获取地图，商业使用允许，区域提取有限制；本地实现每任务最多 16 瓦片、8 MiB、顺序请求并保留来源署名，比官方提取上限更严格。不提供 SLA，也不包含 DEM。[官方说明](https://openfreemap.org/)
- **Photon**：公共演示服务允许合理量的项目请求，但会限流且无可用性保证。试用设计采用明确提交搜索、共享缓存和应用级限速；不能宣传无限全球地名查询。[官方 README](https://github.com/komoot/photon)

## 当前选择

Render Free 仅作为有条件的公开试用候选。零收费的前提是账户未配置支付方式、没有创建任何付费资源，并接受用量达到上限就停服。实际账户开户检查未进行，不能保证一定不会出现平台验证要求。

如果必须兼顾“原尺寸高清、用户无感、后台可靠持续运行”，现阶段不能保证完全零成本。下一步先在本地完成内存/时间测试与真实照片验收，再决定是否适合该免费规格；政策确认前不操作部署。
