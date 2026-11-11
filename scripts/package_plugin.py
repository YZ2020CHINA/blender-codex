"""Prepare relocatable source distribution and machine-local Codex marketplace."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.common import discover_blender, write_json

FILES = ("plugin.json", "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md", "CHANGELOG.md", "CONTRIBUTING.md",
         "VALIDATION.md", "config.example.json", "server.py", "bootstrap.py", "install.ps1", "uninstall.ps1", "build.ps1")
FOLDERS = ("blender_codex", "skills", "addon", "scripts", "tests", ".github")


def write_launcher(plugin, command, args, env=None):
    """Codex plugin stdio servers must use a bare executable, so absolute paths live in a launcher."""
    def quote(value):
        return '"' + str(value).replace("%", "%%") + '"'
    lines = ["@echo off", "chcp 65001 >nul"]
    lines += ['set "{}={}"'.format(key, str(value).replace("%", "%%")) for key, value in (env or {}).items()]
    lines.append(" ".join(quote(part) for part in [command, *args]))
    (plugin / "launch-mcp.cmd").write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return {"type": "stdio", "command": "cmd.exe", "args": ["/d", "/s", "/c", "call", "./launch-mcp.cmd"], "cwd": "./"}


def source_files():
    files = [ROOT / n for n in FILES]
    files += [ROOT / "research/comparison.md", ROOT / ".gitignore", ROOT / ".gitattributes"]
    files += [p for name in FOLDERS for p in (ROOT / name).rglob("*")
              if p.is_file() and "__pycache__" not in p.parts]
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--blender", default="")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    result = {"name": manifest["name"], "version": manifest["version"]}
    if args.prepare:
        config_path = ROOT / "config.json"
        config = json.loads((config_path if config_path.exists() else ROOT / "config.example.json").read_text(encoding="utf-8-sig"))
        config["blender_executable"] = args.blender or config.get("blender_executable") or discover_blender()
        if not Path(config["blender_executable"]).is_file():
            parser.error("Blender not found; pass --blender /path/to/blender")
        config["data_dir"] = str((ROOT / ".state").resolve())
        write_json(config_path, config)
        plugin = ROOT / "plugins" / manifest["name"]
        plugin.mkdir(parents=True, exist_ok=True)
        for name in ("plugin.json", "LICENSE", "THIRD_PARTY_NOTICES.md", "server.py", "bootstrap.py"):
            shutil.copy2(ROOT / name, plugin / name)
        for name in ("blender_codex", "skills"):
            shutil.copytree(ROOT / name, plugin / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Absolute source paths deliberately point to the stable user checkout, not disposable Codex cache.
        write_json(plugin / "mcp.json", {"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"blender_studio": write_launcher(plugin, sys.executable,
                ["-X", "utf8", "-s", str(ROOT / "server.py"), "--config", str(config_path)])}})
        write_json(ROOT / ".agents/plugins/marketplace.json", {"name": "blender-studio-tools",
            "interface": {"displayName": "Blender 影视与动漫工作室"}, "plugins": [{"name": manifest["name"],
            "source": {"source": "local", "path": "./plugins/" + manifest["name"]},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Creativity"}]})
        result["plugin"] = str(plugin)
    if args.zip:
        dist = ROOT / "dist"
        dist.mkdir(exist_ok=True)
        archive = dist / f"blender-studio-{manifest['version']}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for path in source_files():
                z.write(path, "blender-codex/" + path.relative_to(ROOT).as_posix())
        addon = dist / f"codex-studio-bridge-{manifest['version']}.zip"
        with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(ROOT / "addon/__init__.py", "codex_studio_bridge/__init__.py")
        for path in (archive, addon):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix(".zip.sha256").write_text(digest + "  " + path.name + "\n", encoding="ascii")
        result.update(archive=str(archive), addon=str(addon), files=len(source_files()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
