"""Opt-in live provider checks; downloads one bounded sample per source, never a dataset mirror."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.common import load_config, write_json
from blender_codex.assets import Assets
from blender_codex.datasets import Datasets
from blender_codex.client import Client


def main():
    config = load_config(ROOT / "config.json")
    config["data_dir"] = str(Path(config["data_dir"]) / "asset-validation")
    config_path = Path(config["data_dir"]) / "config.json"
    write_json(config_path, config)
    client = Client(load_config(config_path))
    assets, datasets = Assets(config), Datasets(config)
    records = []
    def check(label, operation):
        try:
            result = operation()
            print(label + ": PASS", flush=True)
            records.append({"check": label, "status": "passed", "result": result})
            return result
        except Exception as error:
            print(label + ": " + str(error), flush=True)
            records.append({"check": label, "status": "failed", "error": str(error)})
        finally:
            write_json(Path(config["data_dir"]) / "results.json", records)
    try:
        check("blender", lambda: client.launch(background=True))
        result = check("polyfork search", lambda: assets.polyfork_search("chair", 1))
        if result and result["results"]:
            model = check("polyfork download", lambda: assets.polyfork_download(result["results"][0]["id"]))
            if model:
                check("polyfork import", lambda: client.call("import_asset", {"path": model["path"]}))
        result = check("city search", lambda: datasets.city_search("sapporo", limit=1))
        if result and result["results"]:
            model = check("city download", lambda: datasets.download("city", result["results"][0]["id"], 32))
            if model:
                check("city import", lambda: client.call("import_asset", {"path": model["path"]}))
        result = check("abo search", lambda: datasets.abo_search("chair", limit=1))
        if result and result["results"]:
            model = check("abo download", lambda: datasets.download("abo", result["results"][0]["id"], 32))
            if model:
                check("abo import", lambda: client.call("import_asset", {"path": model["path"]}))
        result = check("scenario search", lambda: datasets.scenario_search(".glb", limit=1))
        if result and result["results"]:
            model = check("scenario download", lambda: datasets.download("scenario", result["results"][0], 32))
            if model:
                check("scenario import", lambda: client.call("import_asset", {"path": model["path"]}))
        result = check("polyhaven search", lambda: assets.search("chair", limit=1))
        if result and result["results"]:
            model = check("polyhaven download", lambda: assets.download(result["results"][0]["id"], max_mb=64))
            if model:
                check("polyhaven import", lambda: client.call("import_asset", {"path": model["path"]}))
        result = check("hdri search", lambda: assets.search("studio", kind="hdris", limit=1))
        if result and result["results"]:
            model = check("hdri download", lambda: assets.download(result["results"][0]["id"], kind="hdris", max_mb=16))
            if model:
                check("hdri environment", lambda: client.call("set_environment", {"mode": "hdri", "path": model["path"]}))
    finally:
        if client.process and client.process.poll() is None:
            client.process.terminate()
            client.process.wait(timeout=15)
    print(json.dumps({"checks": len(records), "failed": sum(r["status"] == "failed" for r in records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
