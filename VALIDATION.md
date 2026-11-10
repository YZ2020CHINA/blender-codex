# 验收记录

## v1.1.0 · 2026-11-10

- 19 项单元测试通过，含独立脚手架兼容、项目相对/绝对文件、同名参考不覆盖、阶段依赖与证据、只读交付检查、用户批准和后续变更撤销、交接 SHA256/坐标约定校验。
- Windows Python 3.10，Edge 157.0.4341.42，Blender 5.2.3 LTS 实测 scripts/integration_transfer.py：浏览器生成 GLB/交接清单、重复时间点截图一致、导出不改变原画面；3 个不同颜色与位置的实例展开；Canvas 128×64 标签嵌入且 Blender 打包；透视相机坐标/40°垂直视场角/16:9 分辨率，浏览器屏幕投影点和模型实际顶点校验通过。
- 结构化 import_threejs_scene 实测创建导入前 .blend 副本，保留旧对象，导入 12 个对象并另建集合；重复检查点路径拒绝且无新增对象；保存、重新打开、贴图打包检查与再次渲染通过；备份重新打开只含导入前对象。测试使用隔离进程和合成桌子/色块，不改动用户便利店工程，不表示复杂场景审美已获用户批准。
- 当前已真实验收透视镜头；正交镜头参数支持但尚无浏览器往返专项实测。浏览器背景、环境光和 Blender 灯光/色彩管理需重新匹配，程序动画不自动烘焙；高级 Python 仅在隔离断言配置中启用，正式 config 保持关闭。
- 本地 Codex 安装确认 blender-studio 1.1.0；重启 Codex/新开聊天加载新工具；已运行 Blender 的旧 Python 模块需重启 Blender（先保存工程）后加载新实现。

## v1.0.0

日期：2026-11-09，Windows，Python 3.10，Blender 5.2.3 LTS，Edge 157.0.4341.42。

- 13 项单元测试通过：真实 stdio JSON-RPC 进程、schema、下载 URL 与路径边界、限额/依赖/来源、需免费和署名条件、坐标转换、项目目录与禁止覆盖用户代码。
- Blender 隔离进程 30 项操作通过：室内/室外/等距/动漫白模、相机运动与三帧 PNG、雨雪雾、天空、三渲二、Freestyle、二拍变换、复古合成器、透明测试卡片、分层、.blend 与 GLB。高级 Python 默认禁用和 NPR 导出保护通过。
- Edge 无界面浏览器读取 Three.js 页面成功；3 个相机与4 段动画可被加载，无 pageerror；同一 t 值重复截图像素一致。代码脚手架 GLB 下载后在 Blender 成功导入。示例是桌子白模，不作为最终影视作品或自动重建质量证明。
- 分别完成 Polyfork 免费 GLB、PLATEAU 札幌单块、Scenario 单 GLB、Poly Haven 扶手椅及贴图、Poly Haven HDRI 的下载和 Blender 导入/环境设置；ABO 单样本模型与两张 2048² WebP 贴图读取成功。此为代表样本，不保证全库兼容。
- 网络存在间歇 TLS/代理失败；加入 Windows 系统 TLS 回退、逐跳重定向域名检查、大小上限和有限重试。单次失败保留明确错误，不据失败声称素材不存在；不关闭 TLS 证书验证。系统 curl 的 revocation best effort 允许在吊销查询离线时继续，不禁用链/主机验证。
- 安装命令确认 blender-studio@blender-studio-tools v1.0.0 installed=true、enabled=true。当前聊天工具清单不会热加载，使用需新开聊天或重启 Codex。可见 GUI add-on 的交互安装尚未端到端验收；已测试的连接为隔离 background Blender。
- 发行 ZIP 不含本机 config.json、MCP 描述、连接令牌、模型素材、用户输出和缓存；全新目录解压、源码检查与本机安装准备通过。SHA256 随包发布。

自动化 CI 只验证无 Blender 的源码/单元/包检查。视觉小样、材质外观与作品最终审美仍需按六阶段由用户确认；未将技术测试等同作品验收。
