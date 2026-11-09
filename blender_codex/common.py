"""Shared configuration and durable JSON writes."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def discover_blender():
    candidates = [os.environ.get("BLENDER_EXECUTABLE", ""), shutil.which("blender")]
    if sys.platform == "win32":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as root:
                    for i in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                                name = winreg.QueryValueEx(key, "DisplayName")[0]
                                if "blender" in name.lower():
                                    location = winreg.QueryValueEx(key, "InstallLocation")[0]
                                    candidates.append(str(Path(location) / "blender.exe"))
                        except OSError:
                            pass
            except OSError:
                pass
    for path in candidates:
        if path and Path(path).is_file():
            return str(Path(path).resolve())
    return ""


def load_config(path):
    path = Path(path).resolve()
    value = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    value["data_dir"] = str(Path(value.get("data_dir") or path.parent / ".state").resolve())
    value["blender_executable"] = value.get("blender_executable") or discover_blender()
    value.setdefault("allow_python", False)
    value.setdefault("proxy", "")
    value.setdefault("request_timeout", 600)
    value["config_path"] = str(path)
    return value
