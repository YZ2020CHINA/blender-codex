# 开发与版本管理

1. 在本项目根目录运行 `git status --short --branch`，先识别并保留已有改动。
2. `git fetch --prune origin`，main 使用 `git pull --ff-only`。发生分叉先检查，禁止强推或 reset 丢弃他人改动。
3. 建立 `feature/说明`、`fix/说明` 或 `docs/说明` 分支。一个提交聚焦一个目的，禁止加入素材缓存和发布产物。
4. 运行 README 中适用的测试。结构化操作变化需真实 Blender 验收，网页变化需浏览器截图验收。新来源先核查逐项许可、大小和重定向边界。
5. `git diff --check` 后按明确文件名 stage，检查 `git diff --cached --stat` 与实际 diff，再提交。
6. 推送功能分支，通过 Pull Request 合入 main。清理合并分支；不得改写已发布标签。

## 发布

使用 SemVer：修复 patch，兼容新增 minor，不兼容修改 major。同步 plugin.json / blender_codex/__init__.py，更新 CHANGELOG，并运行 scripts/check_release.py。打包后在全新目录解压检查可准备安装，确保没有 config.json、.state、用户作品、下载素材或凭据。

只有 main 完成测试后打带注释标签 vX.Y.Z，推送 main 和标签，在 GitHub Release 上传两份 ZIP 和 SHA256。记录真实 Blender、Python 与浏览器验证版本。发布后的修复新建版本，不覆盖旧 ZIP/标签。回退安装旧 Release；工程副本先备份，不承诺 .blend 跨版本向下兼容。

## 文件归属

本仓库只管理插件源码、文档、测试、CI 和精简来源评估。config.json、MCP 本机描述、下载素材、输出、dist、project-blocks 数据均忽略。作品各用独立工程目录，使用 source/assets/previews/licenses/delivery；如需 Git 管理大型作品，单独配置 Git LFS，禁止把二进制素材随意塞进插件仓库。

研究参考不等于可复制授权。引入代码必须保留其许可并更新 THIRD_PARTY_NOTICES；样片、截图、模型的许可与代码分开。
