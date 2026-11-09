# v1.0.0 验收记录

日期：2026-11-09，Windows，Python 3.10，Blender 5.2.3 LTS，Edge 157.0.4341.42。

- 13 项单元测试通过：真实 stdio JSON-RPC 进程、schema、下载 URL 与路径边界、限额/依赖/来源、需免费和署名条件、坐标转换、项目目录与禁止覆盖用户代码。
- Blender 隔离进程 30 项操作通过：室内/室外/等距/动漫白模、相机运动与三帧 PNG、雨雪雾、天空、三渲二、Freestyle、二拍变换、复古合成器、透明测试卡片、分层、.blend 与 GLB。高级 Python 默认禁用和 NPR 导出保护通过。
- Edge 无界面浏览器读取 Three.js 页面成功；3 个相机与4 段动画可被加载，无 pageerror；同一 t 值重复截图像素一致。代码脚手架 GLB 下载后在 Blender 成功导入。示例是桌子白模，不作为最终影视作品或自动重建质量证明。
- 分别完成 Polyfork 免费 GLB、PLATEAU 札幌单块、Scenario 单 GLB、Poly Haven 扶手椅及贴图、Poly Haven HDRI 的下载和 Blender 导入/环境设置；ABO 单样本模型与两张 2048² WebP 贴图读取成功。此为代表样本，不保证全库兼容。
- 网络存在间歇 TLS/代理失败；加入 Windows 系统 TLS 回退、逐跳重定向域名检查、大小上限和有限重试。单次失败保留明确错误，不据失败声称素材不存在；不关闭 TLS 证书验证。系统 curl 的 revocation best effort 允许在吊销查询离线时继续，不禁用链/主机验证。
- 安装命令确认 blender-studio@blender-studio-tools v1.0.0 installed=true、enabled=true。当前聊天工具清单不会热加载，使用需新开聊天或重启 Codex。可见 GUI add-on 的交互安装尚未端到端验收；已测试的连接为隔离 background Blender。
- 发行 ZIP 不含本机 config.json、MCP 描述、连接令牌、模型素材、用户输出和缓存；全新目录解压、源码检查与本机安装准备通过。SHA256 随包发布。

自动化 CI 只验证无 Blender 的源码/单元/包检查。视觉小样、材质外观与作品最终审美仍需按六阶段由用户确认；未将技术测试等同作品验收。
