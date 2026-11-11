# Changelog

## Unreleased

- Codex 兼容性：`mcp.json` 改为 `cmd.exe` + `launch-mcp.cmd` 启动器，去掉 Codex 不接受的超时字段；现在在 Codex 中使用 Claude（如经 Magpie 中转）或 GPT 模型都能调用本插件工具和 skill。

## 1.1.0 — 2026-11-10

- Reference-photo → editable Three.js → Blender refinement → delivery workflow, source/license records and evidence-backed stage tracking.
- GLB handoff includes current camera, resolution, embedded textures, expanded instance transforms/colors and a SHA256 transfer manifest; exported clones leave source scenes editable.
- Structured transfer preflight and Blender importer create a new checkpoint copy, group imports, restore camera framing and pack resources without clearing existing objects.
- Technical delivery checks are read-only; final user approval is explicit and invalidated by later stage changes. Standalone Three.js scaffolding remains compatible without a pipeline file.

## 1.0.0 — 2026-11-09

- Initial stdio MCP, authenticated loopback bridge, optional Blender GUI add-on and local Codex marketplace installer.
- Cinematic cameras/lighting, sky/HDRI, stylized weather, animation, EEVEE toon/Freestyle, game background layers, alpha cards and vintage compositor.
- Selective, bounded asset discovery/download with license records: Poly Haven, Polyfork, PLATEAU, ABO and Scenario; ambientCG and Fab discovery routes.
- Film composition search entry points; Blender-to-GLB-to-Three.js viewer; editable image/prompt-to-code scaffold with deterministic frame rendering route.
- Six-stage beginner-friendly production review, user-selected project location and dedicated delivery folder/instructions.
- Isolated Blender 5.2 integration checks, unit tests, clean source/add-on ZIP packaging, CI and SemVer release discipline.
