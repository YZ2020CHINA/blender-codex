# GitHub 与素材来源评估

核查日期：2026-11-09。星数是当时 GitHub API 快照，会随时间改变。以下区分可直接借鉴的连接架构、创作方法和外部服务；未将第三方源码或媒体复制打包。评估依据仓库 README、许可证与实际 API，不采用社交帖近似星数作为事实。

## Blender MCP 候选

| 项目 | Stars | 许可 | 采用思路 |
| --- | ---: | --- | --- |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | 33,712 | MIT | 主要参考；本地桥接、主线程队列和预览反馈；自写令牌认证与结构化工具 |
| [VxASI/blender-mcp-vxai](https://github.com/VxASI/blender-mcp-vxai) | 300 | MIT | 替代桥接方案 |
| [HoldMyBeer-gg/blenderwright](https://github.com/HoldMyBeer-gg/blenderwright) | 193 | MIT | 自动化方向参考 |
| [dhakalnirajan/blender-open-mcp](https://github.com/dhakalnirajan/blender-open-mcp) | 122 | MIT | 开放 MCP 方案参考 |

搜索也出现 Blender skills、Scenario GPL 插件及其他软件项目；它们不等同于可直接安装的 Codex Blender MCP，未为追求星数混入选型。

## 用户提供的项目

| 项目 | Stars | 核查与取舍 |
| --- | ---: | --- |
| [img2threejs](https://github.com/img2threejs/img2threejs) | 21,005 | Apache-2.0；参考阶段建模/截图质量门；本插件提供自己实现的代码脚手架 |
| [Motion2MixamoRig](https://github.com/MaxLiu22/Motion2MixamoRig) | 1,945 | Apache-2.0；外部实验动捕路线，SMPL-X 等另有要求，不自动安装 |
| [dsh-blender-plugin](https://github.com/sixtysevenlf/dsh-blender-plugin) | 1,894 | BSD-3-Clause；依赖 DSH，非 Codex 直连方案 |
| [dioramas](https://github.com/blendi-remade/dioramas) | 898 | MIT；Web 3D 参考，fal/Meshy 需付费 key |
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | 18,034 | Apache-2.0；Remotion 镜头/产品视频，非 Blender 建模系统 |
| [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | 13,828 | MIT 代码 + CC BY 4.0 媒体；当前 README 66 风格，非原帖 51 |
| [jianying-headless](https://github.com/mcncarl/jianying-headless) | 未确认 | 用户给的确切仓库地址 API 返回 404；不编造可用性或星数 |
| [mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15) | 3,330 | MIT 代码；样片许可逐项核查，只作动效参考 |
| [sand3d](https://github.com/Sandflow-ai/sand3d) | 1,511 | Apache-2.0；Python/bpy 编程库，不是模型库 |

## 素材与许可

- [Quixel 公告](https://quixel.com/news/update-megascans-are-going-free-again)：2026-11-05 公告全 Megascans 库恢复免费；[Fab EULA](https://www.fab.com/eula) 支持兼容工具中的商用，非 CC0，不许单独转售/分发素材。采用官方账号领取/下载，不实现绕过登录。
- [PLATEAU city GLB](https://huggingface.co/datasets/codepawl/plateau-city-glb)：797 城市分块，5 个日本都市；采用 engine GLB，保留 CC BY/MLIT/地方政府/CodePawl 来源与坐标。固定版本下载，避免全库镜像。
- 用户的 InspirationTuts 视频标题为 “8000 Free 3D Assets, Unreal Engine 6 & New 3D software Update”；视频元数据与说明 00:13 指向 [ABO GLB](https://huggingface.co/datasets/codepawl/abo-glb)。7,953 家具道具，CC BY Amazon.com 与转换说明，非 CC0。只核查说明，未假称逐镜头看完。
- [Scenario](https://huggingface.co/datasets/scenario-labs/3d-collection)：AI 生成、CC BY 4.0；GLB/Blend/FBX 有选择性下载，Hunyuan companion 单独条款排除。搜索当前是路径/ID 匹配，非语义检索。
- [Polyfork catalog](https://github.com/lucas-martinic/polyfork-catalog) 与 [许可](https://polyfork.dev/licensing)：当时 README 3,156 模型/29 kits，网站数量会变化。免费 mesh 双许可；本插件选择 CC BY4 并保留每个模型 credit。原帖“免署名”取决于另一套专有许可，不可推广为 CC0。`npx polyfork add <id>` 为官方可选命令，本插件走公开 GLB API，不执行未知 npm 包。
- [Poly Haven](https://polyhaven.com/license) 与 [ambientCG](https://docs.ambientcg.com/license/)：CC0。前者自动下载并记录依赖；后者提供发现入口。

## 新增 X 工作流

[余温帖子](https://x.com/gkxspace/status/2108743836348694659) 公开正文经 FxTwitter 读取。作者描述概念图切片为稀疏 32³ 体素、顶点 AO、按时间 t 编写 Three.js 动画、Playwright 逐帧抽图合成短片。采用可编辑体素 helper、无状态时间求值及可选 capture.mjs；当前不实现自动图像到体素或顶点 AO，不据帖子推断实际成本/效果保证。

R3F、PixiJS、Three.js WebGPU 示例和 Codrops 的路线/访问限制见 skills/blender-studio/references/workflows.md。GitHub 代码许可不能延伸到演示媒体或模型素材。
