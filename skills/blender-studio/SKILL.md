---
name: blender-studio
description: 使用本机 Blender 制作影视过场、镜头动画、三渲二动漫、室内外游戏背景、手绘立绘合成与胶片风格场景；查找可商用素材、PLATEAU 城市和经典电影构图参考。用户指定 Blender 或本插件工作流时使用。
---

# Blender 影视与动漫场景工作室

## 必须遵守的六阶段协作

使用本插件制作作品时按下列阶段与用户协作。每次只推进当前阶段，不能收到一句创作要求就自行做完。阶段结束用简短易懂的话复述已确认事项、说明下一步，并等待用户明确确认；沉默、工具成功、AI 自评均不代表用户确认。用户之后明确授权跳过某些确认时按其最新指令执行，并记录授权范围。工具本身不弹出重复许可窗口，阶段控制由本 skill 的对话负责。

1. **了解需求**：首先询问工程文件夹建在哪里、叫什么名字，确认后用 `production_project_init` 创建独立目录，才开始保存工程或下载素材，不默认放入插件目录或桌面。再询问用途和想看到的画面，通过多轮对话逐渐明确风格、内容、时长/静图、尺寸、使用平台、交付方式与可接受的制作成本。使用新手语言；例如解释“镜头慢慢靠近人物”，再附注“推镜”，不要先堆焦距、采样、渲染器等术语。每轮集中少量问题，可给易比较选项；信息不够时继续交流。复述需求，待用户确认后才进入素材阶段。
2. **收集并确认素材**：搜索模型、环境光、纹理、人物图、电影构图参考。给用户可看的缩略图/来源链接、用途、商用许可、署名要求和下载大小。区分免费免署名、免费需署名、需账号领取以及仅供构图参考的图片。提供候选供选择；取得选材确认后再导入、组合。不得自动替用户选定最终人物或核心场景。只为展示候选进行必要的小量预览下载，保存来源。
3. **确认制作细节**：确认构图、人物位置、镜头如何运动、光线/天气、动画节奏、背景与角色是否分层、字幕/音频需求、网页与 Blender 输出差异、交付格式。用镜头表、示意图或简单白模解释；列出尚未确定的事项。等待用户确认，再开始制作小样。
4. **小样或工程预览截图**：只制作已批准范围的低成本小样，如 480×270 静帧、2–3 秒低清镜头、网页截图或旋转查看。明确标注占位模型和未完成部分，展示实际工具生成的画面，不能把白模称为最终作品。请用户检查画面方向与可读性，等待反馈。
5. **确认与修改细节**：将反馈整理成具体修改项，先复述有歧义的修改，再逐轮修改和展示。记录哪些修改已获确认。用户认可小样及细节后，才进入正式交付；不要自行把“没有报错”当作画面验收通过。
6. **项目交付**：完整工程必须有专用的 `delivery/成品交付/` 文件夹存放模型、动画、图片或网页成品，并填写 `交付说明.md`（文件用途、打开步骤、软件版本、规格、工程位置、素材署名、已知限制和版本）。source/ 放可编辑工程，assets/ 放素材，previews/ 放小样，licenses/ 放来源。按已确认规格生成正式输出，核对丢失贴图、动画范围、画面、播放和许可清单。交付可编辑工程、渲染/网页结果、素材署名和版本说明。公开上传、发布到第三方或付费任务需要用户明确授权。若当前环境缺少能力，说明具体未完成项，不能声称完成。

在用户项目目录维护 `production-review.json`（不含密钥），记录 current_stage、需求摘要、候选素材及选择、各阶段确认的用户原话/回合、待确认问题、预览路径和修改清单。可通过普通文件工具写入；不要虚构用户确认。用户返回继续制作时先读这份记录。未经授权不进入下一阶段，不自动一次执行完整流程。

先用 `blender_status` 查看连接；未连接时用 `blender_launch` 打开可见 Blender。批量验收可用 background=true。已打开的用户工程通过 Blender add-on 连接；不要为连接而关闭用户的窗口。先 `scene_info`，已有内容先 `save_scene` 创建新路径检查点。不要未经当前任务授权删除原场景。

## 选择交付路线

- 影视/过场：先整理简短镜头表（用途、时长、帧率、景别、焦距、起止位置、目标、灯光），再搭景。使用 `create_shot` 创建轨道/推镜与时间线切镜，`keyframes` 控制道具。先低清静帧和短 PNG 序列，视觉检查通过后输出正式帧序列和 .blend。
- 三渲二：`toon_material` 使用 EEVEE Shader to RGB，不能切 Cycles；`outline` 开启 Freestyle；`render_settings(anime=true)` 使用 Standard。`stepped_animation` 只处理物体变换的停格，不声称支持骨骼动画自动抽帧。保留用户已有绑定和动画；不承诺自动生成角色/绑定/表演。
- 2D 游戏/动画背景：室内 `interior`、室外 `exterior`、正交 `game_isometric` 都是可编辑白模起点。可用模型替换桌椅、建筑、植被。按 BG_Far/BG_Mid/BG_Foreground 分组，固定相机，`export_layers` 输出透明 PNG 与清单。共有灯光保留；未列入集合的几何仍可能出现在所有图层，先检查集合。分层不是自动补全遮挡后的图像。
- 手绘立绘 + 胶片背景：使用用户已有透明 PNG，通过 `character_card` 入景；如需全新立绘，使用可用绘图工具/skill 并明确是 AI 生成，不能把占位猴头称为手绘人物。先隐藏角色渲染背景并施加 `film_look`；另行输出干净角色层，在后期合成，避免全局胶片颗粒污染人物颜色。胶片效果是风格模拟，颗粒为静态，非物理胶片扫描。

## 场景工具

`scene_template` 默认追加；仅在用户授权清空时传 clear=true。`create_primitive`、`transform_object`、`set_material` 可搭建和调整场景；旋转 Euler 使用弧度。`lighting_preset` 提供 golden_hour/moonlight/studio/anime_soft/noir，每次增加新灯，请先查场景避免重复。`set_environment` 支持天空和本地 HDRI。`weather` 的雨雪是帧区间内的风格化几何降水，雾是体积材质，均不承诺真实流体/碰撞。

`render_animation` 是同步渲染，先用 320×180、少量帧试验；长片拆成逐镜头批次，避免协议超时。超时后先查进度和输出，不能盲目重试长任务。图片以 `image_preview` 检查。正式交付 `save_scene(pack_resources=true)`，注明帧率、范围、输出与素材来源。PNG 序列可交给视频剪辑工具编码；本插件不捆绑 FFmpeg 或音乐。

## 素材与参考

`asset_search` 优先检索 Poly Haven CC0，`asset_files` 看版本后 `asset_download` 限额下载，保存 provenance.json；再 `import_asset`。ambientCG 为发现与原站下载入口。外部素材和许可不随 MIT 插件打包。

`asset_sources` 包括 Fab/Quixel Megascans、ambientCG、Poly Haven 和 PLATEAU。Fab 并非 CC0，使用官方账号领取和下载，保留素材页与许可，不模拟登录、不抓令牌、不绕过付费。按 2026-11-05 Quixel 公告全库免费，当前逐项价格与权益仍以账号页面为准。

`city_search` 查 PLATEAU 城市分块；`city_download` 只下载选中的 engine GLB 到本地、保留署名与修改说明。`city_import` 导入并按索引偏移放置（glTF Y-up 到 Blender Z-up）。优先单块，避免一次载入几 GB。CC BY 4.0 必须署名，非 CC0；公开作品记录 MLIT、相关地方政府、CodePawl 的加工和自己所作修改；不用于测绘。

`film_reference_search` 返回 BFI/ASC/FilmGrab/Commons 检索入口和构图建议，不是已抓取到的电影镜头。需要具体例图时，用可用联网工具打开原站验证片名/年份/来源并记录。电影截图不属于可商用素材池。可以分析构图、光色、焦距观感和镜头运动，然后把抽象技法落到原创场景；不声称精确还原未知镜头参数。

高级 `execute_python` 默认关闭，若用户需要可在本机 config.json 开启 allow_python 后重启桥接；它具有本机用户完整权限，不是沙箱。尽可能先使用结构化工具完成工作。

## Three.js、参考图建模与代码短片

用户希望“先找照片/素材，用 Three.js 搭景，再进 Blender 精修并交付”时，读取 [照片到 Blender 工作流](references/reference-threejs-blender.md)。使用 pipeline_* 记录来源与阶段证据；网页同时导出 GLB 和交接清单，inspect_threejs_transfer 预检后用 import_threejs_scene 创建检查点并导入。技术通过与用户批准分别记录，不默认强制所有 Blender 任务经过 Three.js。

继续遵守六阶段确认。`export_glb` → `build_threejs_viewer` → `preview_threejs` 提供 Blender 到 HTML 路线。查看相机和动画剪辑列表并截图验收；GLB 不保留 Freestyle、合成器、天空、体积雾或面光的完整外观。NPR/体积材质默认拒绝静默丢失；先烘焙/替换或经用户确认允许损失。动画片段与时间线切镜须在网页重新编排。

参考图/文字 → 代码模型：先读取图片并与用户确认轮廓、比例、风格。用 `create_threejs_project` 建立全新目录；编辑 `model.js` 的 createAsset，分轮廓/比例、结构、材质、光照逐步实现，按 quality-contract.json 截图比较并记录修改。初始桌子只是原创白模示例。网页“下载 GLB”和“下载交接清单”导出同一静态快照及相机，按上述交接工具导入 Blender；已有普通 GLB 仍可通过 `import_asset` 导入。代码运动不自动成为 GLB 动画，需烘焙为 glTF AnimationClip 或在浏览器逐帧渲染。不能声称自动摄影测量或复杂人物精确重建。

代码短片路线参考 https://x.com/gkxspace/status/2108743836348694659 ：概念图 → 人工/代码解释为稀疏体素单元（如 32³ 范围）→ voxelMesh → evaluate(t) → 逐帧 PNG → 编码。evaluate(t) 必须无状态，固定随机种子，任意时间跳转都得到同一画面。脚手架的 capture.mjs 用可选 Playwright 对本地页面逐帧截图，需用户环境已有 Playwright/Chromium；不自动安装或运行付费服务。顶点 AO 是可选后续改进，当前 helper 不宣称已实现。音乐和配音单独收集/制作并确认授权。参考 guide 见 [工作流与来源](references/workflows.md)。

Polyfork：`polyfork_search` → 用户选中 → `polyfork_download` → `import_asset`。仅免费低多边形 GLB，选择 CC BY 4.0 路线并保留逐项 credit。网站另有免署名但禁止素材再分发的自有许可，不要笼统说所有文件 CC0；HD 和 .mjs 不纳入自动下载。ABO 家具用 `abo_search/download`，PLATEAU 城市用 city 工具，Scenario AI 资产用 `scenario_search/download`（当前仅路径/ID 搜索），均保留署名。sand3d 是编程库，不是模型下载站，也不是本插件依赖。
