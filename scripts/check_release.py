"""Read-only release source invariants, used locally and in CI."""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex import __version__

manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
assert manifest["version"] == __version__, "Manifest/Python version mismatch"
assert "## " + __version__ + " — " in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
assert all(part in license_text for part in ("MIT License", "Permission is hereby granted, free of charge", "THE SOFTWARE IS PROVIDED", "LIABILITY"))
paths = [ROOT / "server.py", ROOT / "bootstrap.py"]
paths += [p for folder in ("blender_codex", "addon", "scripts", "tests") for p in (ROOT / folder).rglob("*.py")]
for path in paths:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print(f"Version {__version__}; license and {len(paths)} Python sources checked")
