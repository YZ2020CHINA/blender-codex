"""Real Blender smoke test. Creates isolated test scenes and stops only the process it launches."""
import argparse
import json
from pathlib import Path
import sys
import time
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.client import Client
from blender_codex.common import load_config, write_json
from blender_codex import web


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    args = parser.parse_args()
    config = load_config(args.config)
    folder = Path(config["data_dir"]) / ("integration-" + str(int(time.time())))
    config["data_dir"] = str(folder)
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
        call("render_settings", {"width": 480, "height": 270, "start": 1, "end": 3})
        call("render_still", {"path": "interior.png"})
        call("export_layers", {"directory": "interior-layers"})
        call("create_shot", {"name": "Dolly", "start": 1, "end": 24})
        call("create_shot", {"name": "Orbit", "start": 25, "end": 48, "motion": "orbit"})
        call("render_settings", {"width": 320, "height": 180, "start": 1, "end": 3})
        call("render_animation", {"directory": "animation"})
        call("weather", {"kind": "rain", "count": 40})
        call("weather", {"kind": "snow", "count": 20})
        call("save_scene", {"path": "cinematic.blend"})
        glb = call("export_glb", {"path": "cinematic.glb"})
        web.build(glb["path"], folder / "web")
        call("scene_template", {"template": "anime_stage", "clear": True})
        call("render_settings", {"width": 480, "height": 270, "end": 12, "anime": True})
        call("outline", {"enabled": True})
        call("keyframes", {"object": "HeroProxy", "keys": [{"frame": 1, "value": [0, .4, 1.1]}, {"frame": 12, "value": [1, .4, 1.1]}]})
        call("stepped_animation", {"object": "HeroProxy", "step": 2})
        call("render_still", {"path": "anime.png"})
        try:
            client.call("export_glb", {"path": "must-refuse.glb"})
        except RuntimeError:
            print("NPR export guard: PASS", flush=True)
        else:
            raise AssertionError("NPR material export should require explicit loss acknowledgement")
        call("film_look", {"grain": .04})
        call("render_still", {"path": "anime-film.png"})
        call("save_scene", {"path": "anime.blend"})
        call("scene_template", {"template": "game_isometric", "clear": True})
        call("render_settings", {"width": 480, "height": 270})
        call("render_still", {"path": "isometric.png"})
        call("scene_template", {"template": "exterior", "clear": True})
        call("set_environment", {"mode": "sky"})
        call("weather", {"kind": "fog", "density": .006})
        call("render_still", {"path": "exterior-fog.png"})
        # Tiny synthetic alpha swatch tests the card importer, not character generation.
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        image = folder / "alpha-test.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
                          + chunk(b"IDAT", zlib.compress(b"\x00\xff\x80\x40\xff\xff\x80\x40\x00" * 2)) + chunk(b"IEND", b""))
        call("character_card", {"path": str(image), "name": "AlphaTestSwatch"})
        call("render_still", {"path": "alpha-card-test.png"})
        try:
            client.call("execute_python", {"code": "raise Exception('must not execute')"})
        except RuntimeError as error:
            assert "disabled" in str(error)
            print("Python permission guard: PASS", flush=True)
        else:
            raise AssertionError("Python should be disabled")
        print(json.dumps({"status": "passed", "operations": len(records), "results": str(folder / "results.json"), "web": str(folder / "web")}), flush=True)
    finally:
        if client.process and client.process.poll() is None:
            client.process.terminate()
            client.process.wait(timeout=15)


if __name__ == "__main__":
    main()
