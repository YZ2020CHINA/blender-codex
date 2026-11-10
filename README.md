# Blender Studio for Codex

连接本机 Blender 的 Codex 插件与 MCP。面向影视过场、镜头动画、三渲二、室内外游戏背景、透明人物卡片与胶片风格背景，并提供有许可记录的素材下载和 Three.js 往返工作流。

源码 MIT。Blender、素材、浏览器、FFmpeg 与第三方媒体分别适用其自身许可。无需模型 API key；Codex 本身及可选外部服务费用由用户自己的服务决定。

## 照片参考到 Blender 成品（1.1.0）

新增可复用路线：收集并确认照片/素材 → Three.js 可编辑小样 → GLB 与交接清单 → Blender 精修 → 预览修改 → 成品交付。适合便利店、街区等游戏/视觉小说背景。照片由 Codex 分析并编写场景代码，不是自动摄影测量。

新项目 production_project_init 同时建立 production-pipeline.json；旧项目可用 pipeline_init。pipeline_reference 记录来源/许可与预览，pipeline_stage 保存实际证据和文件。create_threejs_project 可选 project_directory 关联进度；省略仍可独立使用。

网页确定镜头后依次下载 asset.glb、asset.transfer.json。导出包含当前相机、分辨率、嵌入贴图和实例展开副本；inspect_threejs_transfer 校验文件，再 import_threejs_scene 指定全新的 checkpoint_path 导入。工具先保存当前场景副本，另建集合、激活导入相机并打包贴图。原有场景不清空，浏览器灯光需在 Blender 重建和渲染匹配。

pipeline_delivery_check 只读技术检查，不自动批准作品；pipeline_approve 只记录真实用户确认。完整操作、相机/人物/黄昏版本与货架检查见 [照片 → Three.js → Blender 工作流](skills/blender-studio/references/reference-threejs-blender.md)。安装新版本后新开聊天或重启 Codex，已运行 Blender 的旧模块需先保存工程、重启 Blender 后重新连接。

## 按步骤制作作品

默认 skill 要求六阶段协作，每阶段结束等待用户确认：

1. 首先询问工程文件夹的位置与名称，再用新手语言、多轮交流明确用途、画面、风格和规格。
2. 收集素材，展示来源、预览、许可和署名要求，由用户确认选择。
3. 确认构图、镜头、灯光、天气、角色、节奏和交付细节。
4. 生成低清小样或实际工程预览截图。
5. 根据反馈修改，等待细节验收。
6. 用户认可后正式输出并交付完整项目。

`production_project_init` 创建 source/、assets/、previews/、renders/、licenses/、`delivery/成品交付/`，附 `交付说明.md` 与 production-review.json。说明包含打开方法、版本、格式规格、素材署名和限制。阶段确认由对话 skill 管理；MCP 工具供智能体调用，本身没有独立审批 UI。用户可以明确更改确认节奏。

## 安装

要求 Python 3.10+、本机 Blender、支持插件的 Codex。真实集成验收版本为 Windows + Blender 5.2.3 LTS；保留部分旧版 API 兼容分支，但不代表已在所有 Blender 版本验收。

下载 Release 源码 ZIP，解压到稳定目录，或 clone 仓库。PowerShell：

```powershell
./install.ps1 -BlenderExe 'D:\steam\steamapps\common\Blender\blender.exe'
```

可通过 `-PythonExe` / `-CodexExe` 指定程序路径。脚本生成忽略提交的 config.json、本机 MCP 描述与本地 marketplace，再调用 Codex 官方插件命令安装。**安装后新开聊天或重启 Codex**，源码目录需保留。插件名 `blender-studio`，marketplace 名 `blender-studio-tools`。

自动发现失败时指定 Blender 路径。网络需代理时在本机 config.json 设置 `proxy`，如 `http://127.0.0.1:7897`；下载模块验证 HTTPS，不关闭证书校验。修改后重启 MCP。源码包不包含本机绝对路径、连接令牌或素材。

```powershell
./uninstall.ps1
./build.ps1
```

卸载脚本仅移除 Codex 插件注册；项目文件与 .blend 不会因此被删除。

## 连接已有 Blender

首次可由 `blender_launch` 启动可见 Blender，`background=true` 可无界面测试。要连接已打开工程：Blender 首选项 → 插件 → 从磁盘安装 Release 的 `codex-studio-bridge-*.zip`；启用插件，填写稳定源码目录和 config.json 路径，点击 Connect。先保存当前工程。该插件是经典 Blender add-on，非 Blender Extensions 商店包。

桥接采用随机令牌、随机 loopback 端口、主线程操作队列。MCP 走 stdio，桥接只监听 127.0.0.1。高级 Python 默认禁用；本机设置 `allow_python=true` 后具有当前用户权限。停止桥接用 add-on Disconnect；工具不强制关闭用户窗口。

## 功能和边界

| 功能 | 已提供 | 需要注意 |
| --- | --- | --- |
| 搭景 | primitive、变换、材质、室内/室外/动漫/等距白模 | 模板是搭建起点，猴头为明确占位，不是完成的影视场景 |
| 灯光环境 | 三点光、暖阳/月光/黑色电影预设、天空、本地 HDRI | 预设追加灯具，重复执行前检查场景 |
| 运镜动画 | 推镜、环绕、相机切换标记、物体关键帧、PNG 序列 | 不自动生成角色绑定、表演或视频动捕 |
| 天气 | 几何雨雪与体积雾 | 风格化效果，无流体/碰撞物理保证 |
| 三渲二 | EEVEE 色阶、Freestyle、物体变换二拍/三拍 | 骨骼抽帧、完整动漫角色生成未实现 |
| 2D 背景 | 正交/透视、语义集合、透明 PNG 图层 | 不自动补画遮挡背面的内容 |
| 手绘卡片 | 已有透明人物图、面向镜头、背景复古调色/暗角/静态颗粒 | 不包含绘图模型；角色层与背景层分开处理 |
| 电影构图 | BFI/ASC/FilmGrab/Commons 搜索入口与六种构图建议 | 返回检索链接，不是已抓取的电影截图；截图版权独立 |
| Web | GLB + Three.js 0.180.0 查看器、相机/动画选择、本地预览 | CDN 需联网；Blender 合成器/天空/NPR/体积不能原样导出 |
| 图到代码 | 可编辑 model.js、质量检查清单、体素 helper、静态 GLB 导出 | Codex 需分析图并逐轮改代码，非自动摄影测量 |
| 代码短片 | 无状态 evaluate(t)、可选 Playwright 逐帧截图脚本 | 需另备 Playwright/Chromium、编码器；不捆绑音乐 |

`export_glb` 默认阻止 NPR/体积材质静默损失。允许损失后也要在网页验收。代码动画需烘焙为 AnimationClip 或逐帧输出，静态导出按钮不自动保存函数动画。查看 [详细工作流](skills/blender-studio/references/workflows.md)。

## 素材来源

| 来源 | 查找/下载方式 | 商用与署名 |
| --- | --- | --- |
| Poly Haven | 实时目录、blend 与贴图依赖/HDRI 限额下载 | CC0，保存来源与校验值 |
| ambientCG | 检索与原站下载入口 | CC0；当前不自动下载 |
| Polyfork | 搜索免费 low-poly、单项 GLB 下载 | 本插件选 CC BY 4.0，保留逐项 credit；HD 与 .mjs 不自动下载 |
| PLATEAU / CodePawl | 选城市/分块、engine GLB、坐标偏移导入 | CC BY 4.0；MLIT/地方政府及 CodePawl 修改说明 |
| ABO / CodePawl | 家具/道具英文词检索、单模型下载 | CC BY 4.0，署名 Amazon.com 与转换；品牌权利另查 |
| Scenario 3D collection | 固定版本清单按路径/ID 查找、单项下载 | CC BY 4.0，AI 生成；不包含另有条款的 Hunyuan companion |
| Fab / Megascans | 官方页面搜索、账号领取和下载后本地导入 | Quixel 2026-11-05 公告恢复免费；Fab 许可非 CC0，不能单独转售/分发素材 |
| sand3d | 外部编程库参考 | 不是素材站，未作为依赖安装 |

下载默认有限额，保留 provenance.json、来源版本、SHA256 和需署名来源的 ATTRIBUTION.txt。用户项目应归档到 assets/ 与 licenses/；下载缓存不作为正式交付目录。外部素材不随插件、Git 仓库或发布 ZIP 分发。版权许可不替代商标、肖像等权利核查。

## 测试和开发

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/integration.py
python -X utf8 scripts/verify_assets.py
python -X utf8 scripts/package_plugin.py --zip
git diff --check
```

单元测试无需 Blender；integration 使用隔离状态目录启动本机 Blender，只终止自己创建的进程。素材测试会联网，按来源少量下载，需本机配置且不适合无网络 CI。GitHub CI 检查单元测试、版本一致性、源码语法与发布包内容，不声称覆盖 GPU/所有素材。

## Git 与版本管理

项目使用独立仓库、main 主分支。后续工作使用 feature/* 或 fix/* 分支，通过 PR 合入；不强推 main。版本遵循 SemVer，plugin.json 与 Python __version__ 必须一致，每次 Release 更新 CHANGELOG，打不可变 vX.Y.Z 标签。安装 ZIP 和 SHA256 对应标签的源码。

忽略本机配置、.state/、缓存、输出、生成插件、dist/、项目积木运行数据和研究下载；不建立父目录总仓库。修改流程和回滚规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。上游星数/许可评估见 [research/comparison.md](research/comparison.md)。

安装依据 [Codex 官方插件文档](https://developers.openai.com/plugins/build/plugins)。
