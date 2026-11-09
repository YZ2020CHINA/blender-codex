"""Audit ZIP contents and prepare a clean extracted copy without installing it."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))["version"]
archive = ROOT / f"dist/blender-studio-{version}.zip"
with zipfile.ZipFile(archive) as z:
    names = z.namelist()
    for name in names:
        parts = Path(name).parts
        assert not any(p in parts for p in (".state", "__pycache__", "project-blocks", ".git", "outputs", "plugins")), name
        assert Path(name).name not in ("config.json", "endpoint.json", "mcp.json"), name
    assert f"blender-codex/research/comparison.md" in names
    with tempfile.TemporaryDirectory(prefix="blender-clean-package-") as temp:
        z.extractall(temp)
        source = Path(temp) / "blender-codex"
        subprocess.run([sys.executable, "-X", "utf8", str(source / "scripts/check_release.py")], check=True)
        # Preparation needs a Blender path; CI only audits the portable source.
        if (ROOT / "config.json").exists():
            blender = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["blender_executable"]
            subprocess.run([sys.executable, "-X", "utf8", str(source / "scripts/package_plugin.py"), "--prepare", "--blender", blender], check=True)
print(f"Clean ZIP audit passed: {len(names)} files; no runtime configuration/assets")
