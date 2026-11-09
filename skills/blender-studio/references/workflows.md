# 工作流与网页视觉参考

本插件提供结构化 Blender 操作、代码建模脚手架与本地预览。全新作品按 SKILL.md 六阶段逐步确认。

## 可用路线

| 需求 | 路线 | 验收重点 |
| --- | --- | --- |
| 影视过场 | 镜头表 → 授权资产 → 白模 → 灯光/天气 → 推镜/环绕 → PNG 序列 | 动作与叙事、穿帮、连续性、贴图 |
| 三渲二 | EEVEE toon bands + Freestyle → 固定曝光/Standard → 停格变换 | 阴影边界、轮廓闪烁；不自动创建角色/绑定 |
| 游戏背景 | 室内/室外白模 → 资产替换 → 正交/透视 → 集合分层 PNG | 边缘透明、遮挡、视差尺度 |
| 立绘 + 复古背景 | 已授权透明人物图 → 干净人物层 + 独立胶片背景 → 合成 | 人物色彩保持、透视与接地感 |
| Blender → Web | 导出 GLB → HTML viewer → 本地 HTTP → 截图/动画检查 | PBR、相机、剪辑；NPR 需烘焙或重做 |
| 图 → 代码模型 → Blender | 参考图分析 → create_threejs_project → 多轮改 model.js → GLB → import_asset | 轮廓/比例/材质逐项比较；非自动重建 |
| 代码 3D 短片 | 概念图 → 稀疏体素/程序化几何 → evaluate(t) → capture.mjs → PNG | 确定性、逐帧完整、时间单位、颜色管理 |

可选编码（用户安装 FFmpeg 后）：`ffmpeg -framerate 24 -i frames/%06d.png -c:v libx264 -pix_fmt yuv420p output.mp4`。帧率必须与截图一致。音频另外校验授权与同步。本插件不捆绑 FFmpeg、浏览器、音乐或 AI 生图/3D 服务。

## 上游方法参考（代码未直接复制）

- [img2threejs](https://github.com/img2threejs/img2threejs)：分阶段建模、quality contract 与截图反馈；当前插件提供自己的轻量脚手架，不等于安装上游完整系统。
- [X 代码短片流程](https://x.com/gkxspace/status/2108743836348694659)：已读取帖子正文，作者描述 2D 概念图/体素、按 t 动画与 Playwright。未核验其两小时耗时、成本与影片制作的全部细节。
- [Motion2MixamoRig](https://github.com/MaxLiu22/Motion2MixamoRig)：视频动作重定向可作外部实验路线；需另装环境并检查 SMPL-X/Mixamo/输入视频许可，不内置。
- [dsh-blender-plugin](https://github.com/sixtysevenlf/dsh-blender-plugin)：依赖 DSH，不能直接当作 Codex 插件。
- [dioramas](https://github.com/blendi-remade/dioramas)：可参考 Web 场景与后期；其 fal/Meshy 生成需付费服务，不自动启用。
- [sand3d](https://github.com/Sandflow-ai/sand3d)：Python/bpy 编程库，可选外部扩展；不是模型源。
- video-shotcraft、lemo-opuscar、mg-styles-15 适合镜头/动效研究。代码许可和样片媒体许可分开，未打包其媒体。

## 网页案例路线

- [R3F 官方案例](https://r3f.docs.pmnd.rs/getting-started/examples)：React/Next.js 组件化模型交互；本插件默认纯 Three.js。
- [Codrops](https://tympanus.net/codrops/) 与 [R3F 标签](https://tympanus.net/codrops/tag/react-three-fiber/)：用于研究 GLSL 溶解、粒子与网页转场。此次抓取被 403 阻止；不要声称已分析具体教程，需逐篇核对演示和许可。
- [PixiJS 展示](https://pixijs.com/showcase)：2D 游戏、拖拽、角色。PixiJS + GSAP + Matter.js 属另一种 2D 交互路线，不与 Blender GLB 直接等同。
- [Three.js WebGPU 粒子](https://threejs.org/examples/webgpu_compute_particles.html)：TSL/WebGPU 计算示例；浏览器/GPU 必须支持，发布前提供兼容性说明和 WebGL 回退。

新增 R3F、GSAP、GLSL 或 WebGPU 效果时独立建 feature 分支，固定依赖版本，先做小样再合入；不把所有框架强塞进默认插件。
