"""Live Blender smoke test for v1.2.0: asset_audit and mesh_stats only.

Runs against an isolated, disposable data_dir so it never touches the
user's own .state, config.json or any existing .blend file. Only stops
the Blender process this script itself launches.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.client import Client
from blender_codex.common import load_config, write_json


def main():
    base_config = load_config(ROOT / "config.json")
    with tempfile.TemporaryDirectory(prefix="blender-codex-v120-") as tmp:
        folder = Path(tmp)
        config = dict(base_config)
        config["data_dir"] = str(folder)
        config["proxy"] = ""
        config_path = folder / "config.json"
        write_json(config_path, config)
        config = load_config(config_path)
        client = Client(config)
        records = []

        def call(action, params=None):
            result = client.call(action, params)
            records.append({"action": action, "result": result})
            write_json(folder / "results.json", records)
            print(action + ": PASS", flush=True)
            return result

        try:
            print(client.launch(background=True), flush=True)
            call("scene_template", {"template": "interior", "clear": True})

            full_audit = call("asset_audit", {})
            assert full_audit["mesh_objects"] >= 1, "interior template should contain mesh objects"
            assert full_audit["triangles"] > 0, "evaluated triangle count should be positive"
            assert full_audit["checks"] == [
                "evaluated_mesh_counts", "dimensions", "scale", "UV_layers", "material_slots",
            ]
            assert "limitations" in full_audit
            for mesh in full_audit["meshes"]:
                assert set(mesh) >= {"name", "triangles", "vertices", "dimensions", "scale",
                                      "materials", "uv_layers"}
            print("asset_audit structural checks: PASS", flush=True)

            one_name = full_audit["meshes"][0]["name"]
            scoped_audit = call("asset_audit", {"objects": [one_name]})
            assert scoped_audit["mesh_objects"] == 1
            assert scoped_audit["meshes"][0]["name"] == one_name
            print("asset_audit object filter: PASS", flush=True)

            mobile_stats = call("mesh_stats", {"budget": "mobile"})
            assert mobile_stats["budget"]["platform"] == "mobile"
            assert mobile_stats["budget"]["guidance_triangles_per_mesh"] == 3000
            assert isinstance(mobile_stats["budget"]["over_budget"], list)
            print("mesh_stats mobile budget: PASS", flush=True)

            default_stats = call("mesh_stats", {})
            assert default_stats["budget"]["platform"] == "web"
            print("mesh_stats default budget: PASS", flush=True)

            try:
                client.call("mesh_stats", {"budget": "quantum_cloud"})
            except RuntimeError as error:
                assert "budget must be" in str(error)
                print("mesh_stats invalid budget guard: PASS", flush=True)
            else:
                raise AssertionError("mesh_stats should reject an unknown budget name")

            print(json.dumps({"status": "passed", "operations": len(records),
                              "results": str(folder / "results.json")}), flush=True)
        finally:
            if client.process and client.process.poll() is None:
                client.process.terminate()
                client.process.wait(timeout=15)


if __name__ == "__main__":
    main()
