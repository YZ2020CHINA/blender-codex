# 照片资料 → Three.js 场景 → Blender 精修 → 成品

用于用户希望从照片搭建可编辑场景，尤其是固定镜头游戏/视觉小说背景。可以直接在 Blender 完成的任务不强制绕行 Three.js。继续遵守主 skill 的六阶段协作，已给出的确认和后续授权持续有效。

## 1. 收集资料并确定场景范围

先读 production-review.json；明确项目位置、风格、固定镜头还是可自由环视。记录正面、货架/商品、建筑、路面等资料的用途。搜索结果入口不等于已读原网页，直链不等于已核实作者/许可。只研究外观的照片标为 reference，不把未知版权照片直接当成生产贴图。

新项目用 production_project_init（同时建立 production-pipeline.json）；已有项目用 pipeline_init，不覆盖既有工程。pipeline_reference 保存来源、角色、license_name、是否实际核实以及可选的本地预览。verified 表示来源事实已核查，不是商用许可判定；未知许可保留 unverified。许可与署名文档放 licenses/。展示参考并保存用户选材原话。

pipeline_stage 的 passed 表示有证据的阶段验收，必须提供 evidence 和实际文件 artifacts；不能只因为创建脚手架就通过。记录用户意见仍在 production-review.json，工具不会替用户作视觉决定。上游变化会把已通过的下游改为 review，并撤销交付批准。

## 2. 可编辑 Three.js 小样

create_threejs_project(directory="<项目>/source/threejs", project_directory="<项目>") 创建 model.js、transfer.js、index.html、quality-contract.json、capture.mjs。已有工程不覆盖。project_directory 可省略，兼容独立网页工作流。先看图片，再按轮廓/比例、结构、材质、灯光迭代代码；这是代码解释资料，不能称为摄影测量或自动精确重建。

以米为单位、Y 向上，语义分组、物件命名。复用几何和材质制作货架商品，避免只堆大色块。用户要求前后左右街区时检查背面、街道衔接、货架两侧、建筑侧后面；固定镜头范围之外未完成的区域如实记录。随机排列固定种子。evaluate(t) 无状态，跳转时间后构图应可重复。

优先 Standard/Physical/Basic 材质和可嵌入图片贴图。Canvas 商品标签应实际绘制并设置纹理更新；外链贴图需要 CORS，可选改为本地文件。自定义 shader/Reflector、浏览器天空、环境光和后期不承诺转移。先 preview_threejs，在实际浏览器截图检查小样，再登记 threejs 阶段证据。

## 3. 导出与校验

在网页确定镜头与时间点，点击“下载 GLB”，再点“下载交接清单”，保存同批 asset.glb 和 asset.transfer.json。清单记录 SHA256、米制/Y-up、分辨率、时间点和已知限制；清单对应上次导出快照。重新导出后必须同时替换两份文件。

transfer.js 对导出副本展开 InstancedMesh 并保留逐实例颜色、变换及子物件，原场景保持实例结构。大量实例展开会增大文件，先分区域测试。贴图随 GLB 嵌入，最大边 4096。导出包含当前相机，保持导出窗口比例。当前是静态快照，程序动画需另行烘焙 AnimationClip 或逐帧渲染；蒙皮和自定义材质需专用处理，不能默默声称完整导出。

inspect_threejs_transfer(glb_path, manifest_path) 只读检查文件头、大小、校验值、坐标约定和分辨率；不表示外观或网格质量已验收。

## 4. Blender 导入和精修

先 blender_status/scene_info。使用 import_threejs_scene(glb_path, manifest_path, checkpoint_path="<项目>/source/blender/before-import-唯一版本.blend", project_directory="<项目>")。检查点必须是新路径，保存副本且不切换用户当前工程路径；已有物件不会被清空。导入另建语义集合、默认激活导入相机并恢复分辨率，pack_all 打包资源。use_imported_camera=false 保持原相机与分辨率。失败可能有部分对象留在场景中，先检查再重试，可从检查点人工恢复；不盲目重复导入。

glTF 导入器完成 Y-up → Z-up，不能再整体多转 90°。检查对象数量/层级、实例颜色、比例、法线、UV、贴图、透视镜头与可见范围。导入结果 status=imported_needs_render_review，不自动把 blender_import 阶段通过。重复导入会产生独立集合；需要替换时先确认具体旧集合。

用 Blender 原生灯具、世界和材质优化风格。Three.js 的灯光强度/色彩管理与 Blender 不等价，按实际渲染匹配。材质节点按 bl_idname 查找，避免依赖本地化显示名；共享 mesh 的缩放应用只在需要时转单用户。对货架、商品、路面与建筑做细节和穿插检查。已有透明人物 PNG 保留原画完整裁切，明确是二维卡片；不自动补画被裁掉的身体。用户指定位置/相机后保留其他已确认内容。

若桥接能读取实际视口，按视口对齐相机并检查镜头、比例和偏移；只有截图时说明估算。黄昏/夜景等版本另存 .blend，保持已确认镜头和人物位置。物体发光材质不能替代照明，检查实际灯具、World、hide_render、集合和 view layer 排除状态。Solid 模式不显示真实灯光；切 Rendered 查看，F12 验证相机结果。保存的工作区可能因打开方式变化，不以视口截图代替正式渲染。

## 5. 验收与交付

先输出低清预览，与网页小样和参考对照。save_scene(pack_resources=true) 保存到新的精修版本，重新打开副本检查缺失贴图、活动相机、渲染尺寸与画面，才记录 blender_optimization 通过。不要在用户未保存的窗口中直接打开别的工程。

用户认可画面后按既定规格导出 PNG/图层/GLB 等，放 delivery/成品交付/；填写交付说明、版本、工程路径、软件版本、许可/署名、兼容性限制与文件校验值。GLB 不完整保留 NPR/Freestyle、合成器、天空、体积和面光；需要时烘焙并重新验收，不能承诺渲染等价。

pipeline_delivery_check 是只读技术检查，检查阶段和交付文件，不会批准。所有阶段 passed 且输出存在后，取得实际用户认可，才 pipeline_approve(user_confirmation="用户实际确认原话/回合")。不能把“工具成功”、AI 自评或沉默当成批准。检查只核实记录和文件存在，仍需实际打开/渲染/播放与许可审查证据。
