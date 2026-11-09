"""Import an explicitly selected downloaded GLB in isolated Blender and report materials."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.common import load_config, write_json
from blender_codex.client import Client

config = load_config(ROOT / "config.json")
config["data_dir"] += "/model-validation"
config["allow_python"] = True  # only this isolated test config, not the installed plugin
config_path = Path(config["data_dir"]) / "config.json"
write_json(config_path, config)
client = Client(load_config(config_path))
try:
    client.launch(background=True)
    result = client.call("import_asset", {"path": str(Path(sys.argv[1]).resolve())})
    materials = client.call("execute_python", {"code": "result = {'meshes': len([o for o in bpy.context.scene.objects if o.type == 'MESH']), 'images': [(i.name, list(i.size)) for i in bpy.data.images if i.type == 'IMAGE']}"})
    print(json.dumps({"import": result, "materials": materials}, ensure_ascii=False))
finally:
    if client.process and client.process.poll() is None:
        client.process.terminate()
        client.process.wait(timeout=15)
