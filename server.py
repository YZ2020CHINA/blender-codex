"""Dependency-free MCP stdio server using newline-delimited JSON-RPC."""
import argparse
import base64
import json
import math
from pathlib import Path
import sys
import traceback

from blender_codex import __version__
from blender_codex.assets import Assets, film_references, asset_sources
from blender_codex.datasets import Datasets
from blender_codex import web, authoring, production, pipeline, transfer
from blender_codex.client import Client
from blender_codex.common import load_config


def schema(properties=None, required=()):
    return {"type": "object", "properties": properties or {}, "required": list(required), "additionalProperties": False}


def string(description="", enum=None):
    value = {"type": "string", "description": description}
    if enum:
        value["enum"] = enum
    return value


NUMBER = {"type": "number"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}
VEC3 = {"type": "array", "items": NUMBER, "minItems": 3, "maxItems": 3}
RGBA = {"type": "array", "items": NUMBER, "minItems": 4, "maxItems": 4}
STRINGS = {"type": "array", "items": string()}


def tool(name, description, properties=None, required=(), readonly=False, destructive=False):
    return {"name": name, "description": description, "inputSchema": schema(properties, required),
            "annotations": {"readOnlyHint": readonly, "destructiveHint": destructive,
                            "idempotentHint": readonly, "openWorldHint": name.startswith(("asset_", "film_"))}}


TOOLS = [
    tool("pipeline_init", "Initialize a reusable reference → Three.js → Blender → delivery record inside an existing project folder.",
         {"directory": string(), "title": string()}, ["directory"]),
    tool("pipeline_status", "Read pipeline stages, recorded references, artifacts and delivery gate status.",
         {"directory": string()}, ["directory"], readonly=True),
    tool("pipeline_reference", "Record a reference photo/material source, license status and optional local preview copy.",
         {"directory": string(), "source": string(), "role": string(), "license_name": string(),
          "verified": BOOLEAN, "local_path": string(), "notes": string()}, ["directory", "source"]),
    tool("pipeline_stage", "Record an observed stage result and artifacts without claiming user approval.",
         {"directory": string(), "stage": string(enum=list(pipeline.STAGES)), "status": string(enum=list(pipeline.STATUSES)),
          "artifacts": STRINGS, "evidence": STRINGS, "notes": string()}, ["directory", "stage", "status"]),
    tool("pipeline_delivery_check", "Check that all upstream stages passed and delivery artifacts exist; does not publish or upload.",
         {"directory": string()}, ["directory"], readonly=True),
    tool("pipeline_approve", "Record explicit final user approval after technical checks. Supply the user's actual words; tool success is not approval.",
         {"directory": string(), "user_confirmation": string()}, ["directory", "user_confirmation"]),
    tool("inspect_threejs_transfer", "Validate exported GLB header/checksum, transfer manifest, units and resolution before touching Blender.",
         {"glb_path": string(), "manifest_path": string()}, ["glb_path", "manifest_path"], readonly=True),
    tool("import_threejs_scene", "Checkpoint existing Blender scene to a NEW .blend, import validated Three.js GLB, group objects, activate imported camera and pack images. Does not clear existing objects or reproduce browser lighting. Import failures may leave partial objects; inspect before retrying.",
         {"glb_path": string(), "manifest_path": string(), "checkpoint_path": string(), "collection_name": string(),
          "use_imported_camera": BOOLEAN, "project_directory": string()}, ["glb_path", "manifest_path", "checkpoint_path"]),
    tool("production_project_init", "Create folders after user confirms project location/name. Includes source, assets, previews, licenses and delivery/成品交付 with instructions. Does not approve review stages.",
         {"directory": string(), "title": string()}, ["directory"]),
    tool("blender_launch", "Launch Blender and connect the authenticated local bridge; reuses a healthy bridge.", {"background": BOOLEAN}),
    tool("blender_status", "Get connection, Blender version and active camera.", readonly=True),
    tool("scene_info", "List scene objects, transforms and shot metadata.", readonly=True),
    tool("scene_template", "Build editable indoor, outdoor, anime or isometric blockout; clear=true deletes existing scene objects.",
         {"template": string(enum=["interior", "exterior", "anime_stage", "game_isometric"]), "clear": BOOLEAN}, destructive=True),
    tool("create_primitive", "Add blockout geometry with a material. Units are meters; rotation values elsewhere are radians.",
         {"kind": string(enum=["cube", "plane", "sphere", "cylinder", "cone", "monkey"]), "name": string(), "location": VEC3, "scale": VEC3, "color": RGBA}),
    tool("transform_object", "Set object transforms; rotation_euler uses radians.",
         {"object": string(), "location": VEC3, "rotation_euler": VEC3, "scale": VEC3}, ["object"]),
    tool("delete_object", "Delete one named object. Save a scene checkpoint first.", {"object": string()}, ["object"], destructive=True),
    tool("set_material", "Replace the named mesh's surface material with a Principled material.",
         {"object": string(), "name": string(), "color": RGBA, "roughness": NUMBER, "metallic": NUMBER}, ["object"]),
    tool("create_camera", "Create perspective/orthographic camera, target, lens and optional depth of field.",
         {"name": string(), "location": VEC3, "target": VEC3, "projection": string(enum=["PERSP", "ORTHO"]),
          "lens": NUMBER, "ortho_scale": NUMBER, "dof": BOOLEAN, "fstop": NUMBER}),
    tool("create_light", "Add an area, point, spot or sun light aimed at the target.",
         {"name": string(), "kind": string(enum=["AREA", "POINT", "SPOT", "SUN"]), "location": VEC3,
          "target": VEC3, "energy": NUMBER, "color": VEC3, "size": NUMBER}),
    tool("lighting_preset", "Add key/fill/rim lights and set environment. Existing lights remain; inspect scene before repeating.",
         {"preset": string(enum=["golden_hour", "moonlight", "studio", "anime_soft", "noir"])}),
    tool("set_environment", "Set a new world with color, Nishita sky or local HDRI. rotation and sun_elevation are degrees.",
         {"mode": string(enum=["color", "sky", "hdri"]), "strength": NUMBER, "color": VEC3,
          "path": string(), "rotation": NUMBER, "sun_elevation": NUMBER}),
    tool("toon_material", "Apply 2–5 band cel shading to a mesh; switches renderer to EEVEE. Does not generate characters or rigs.",
         {"object": string(), "color": RGBA, "bands": INTEGER}, ["object"]),
    tool("outline", "Configure Freestyle silhouette rendering. Render-test with your Blender engine.",
         {"enabled": BOOLEAN, "thickness": NUMBER, "color": VEC3}),
    tool("weather", "Add stylized fog, rain or snow. Rain/snow use deterministic animated geometry over a frame interval; no fluid/collision simulation.",
         {"kind": string(enum=["fog", "rain", "snow"]), "density": NUMBER, "scale": VEC3,
          "count": INTEGER, "seed": INTEGER, "start": INTEGER, "end": INTEGER}),
    tool("keyframes", "Insert transform keyframes; rotation_euler values in radians.",
         {"object": string(), "property": string(enum=["location", "rotation_euler", "scale"]),
          "keys": {"type": "array", "items": schema({"frame": INTEGER, "value": VEC3}, ["frame", "value"])}}, ["object", "keys"]),
    tool("create_shot", "Create animated dolly/orbit camera with subject tracking, DOF, shot metadata and timeline cut marker.",
         {"name": string(), "start": INTEGER, "end": INTEGER, "from": VEC3, "to": VEC3, "target": VEC3,
          "lens": NUMBER, "dof": BOOLEAN, "fstop": NUMBER, "motion": string(enum=["dolly", "orbit"]),
          "orbit_degrees": NUMBER, "notes": string()}),
    tool("stepped_animation", "Bake held transform poses for anime on twos/threes. Does not retime skeletal or shape-key animation.",
         {"object": string(), "step": INTEGER}, ["object"]),
    tool("set_frame", "Evaluate scene at a frame.", {"frame": INTEGER}, ["frame"]),
    tool("character_card", "Place an existing alpha image as an unlit camera-facing hand-drawn character card.",
         {"path": string(), "name": string(), "location": VEC3, "height": NUMBER, "camera": string()}, ["path"]),
    tool("film_look", "Replace compositor with warm vintage grading, static grain and vignette. Apply to background separately to preserve clean character colors.",
         {"grain": NUMBER, "saturation": NUMBER, "vignette": NUMBER}, destructive=True),
    tool("render_settings", "Set frame range, resolution, fps, transparency and engine. frame_step skips renders, not animation retiming.",
         {"width": INTEGER, "height": INTEGER, "fps": INTEGER, "start": INTEGER, "end": INTEGER,
          "frame_step": INTEGER, "engine": string(enum=["eevee", "cycles"]), "samples": INTEGER, "transparent": BOOLEAN, "anime": BOOLEAN}),
    tool("render_still", "Render current frame to PNG. Existing output file may be overwritten.", {"path": string()}, destructive=True),
    tool("render_animation", "Render PNG image sequence synchronously; use a short low-resolution preview first. May overwrite same frame filenames.",
         {"directory": string()}, destructive=True),
    tool("group_objects", "Move named objects into a semantic scene collection for layers.", {"name": string(), "objects": STRINGS}, ["name", "objects"]),
    tool("export_layers", "Render transparent PNGs isolating specified collections; shared lights/unlisted geometry stay visible; not depth/occlusion reconstruction.",
         {"collections": STRINGS, "directory": string()}, destructive=True),
    tool("import_asset", "Import a local blend/GLB/glTF/FBX/OBJ. Appends blend objects without opening or executing embedded Python.",
         {"path": string()}, ["path"]),
    tool("save_scene", "Save .blend and pack resources. Refuses overwrite unless overwrite=true.",
         {"path": string(), "overwrite": BOOLEAN, "pack_resources": BOOLEAN}),
    tool("execute_python", "Advanced arbitrary Blender Python. Disabled by default; enable locally and restart. Has full user filesystem permissions.",
         {"code": string()}, ["code"], destructive=True),
    tool("asset_search", "Search live Poly Haven CC0 catalog for commercial-use models, HDRIs, textures. Optional ambientCG discovery; returns source/license URLs.",
         {"query": string(), "kind": string(enum=["models", "hdris", "textures"]), "limit": INTEGER,
          "provider": string(enum=["polyhaven", "ambientcg"])}, readonly=True),
    tool("asset_files", "Read Poly Haven download manifest before selecting format/resolution.", {"asset_id": string()}, ["asset_id"], readonly=True),
    tool("asset_download", "Download Poly Haven model + texture dependencies or HDRI with bounded size, checksums and provenance. Never auto-imports.",
         {"asset_id": string(), "kind": string(enum=["models", "hdris"]), "resolution": string(enum=["1k", "2k", "4k", "8k"]), "max_mb": INTEGER}, ["asset_id"]),
    tool("film_reference_search", "Generate curated BFI/ASC/FilmGrab/Commons search links and a reusable composition preset; these are search entry points, not retrieved stills.",
         {"query": string(), "technique": string(enum=["thirds", "symmetry", "low_angle", "deep_focus", "negative_space", "silhouette"])}, readonly=True),
    tool("image_preview", "Return an existing local PNG as an MCP image for visual review (max 8 MiB).", {"path": string()}, ["path"], readonly=True),
    tool("asset_sources", "List source-specific search/download workflows including Fab Megascans and CC BY city/furniture datasets.", {"query": string()}, readonly=True),
    tool("city_search", "Search pinned PLATEAU Japanese city tiles. CC BY 4.0 requires attribution. Queries match tile ids; use city to select region.",
         {"city": string(enum=["tokyo", "osaka", "yokohama", "nagoya", "sapporo"]), "query": string(), "limit": INTEGER, "textured_only": BOOLEAN}, readonly=True),
    tool("city_download", "Download only the selected PLATEAU engine GLB with attribution, source policy and Blender coordinate offset.",
         {"tile_id": string(), "max_mb": INTEGER}, ["tile_id"]),
    tool("city_import", "Import an already-downloaded city GLB, optionally place it by city offset. Requires its provenance.json.",
         {"provenance": string(), "place_at_city_offset": BOOLEAN}, ["provenance"]),
    tool("abo_search", "Search Amazon Berkeley Objects furniture/props by English name/category. CC BY 4.0, not CC0.",
         {"query": string(), "limit": INTEGER}, readonly=True),
    tool("abo_download", "Download one ABO model with attribution. Uses meshopt/WebP web GLB; importer compatibility must be checked.",
         {"model_id": string(), "max_mb": INTEGER}, ["model_id"]),
    tool("polyfork_search", "Search free low-poly Polyfork assets; CC BY 4.0 mesh license with per-asset credit.", {"query": string(), "limit": INTEGER}, readonly=True),
    tool("polyfork_download", "Download one free Polyfork GLB and its credit. No paid HD or source modules.",
         {"asset_id": string(), "max_mb": INTEGER}, ["asset_id"]),
    tool("scenario_search", "List Scenario AI-generated models by path/id substring; returned viewer link supports manual prompt browsing.",
         {"query": string(), "limit": INTEGER}, readonly=True),
    tool("scenario_download", "Download one pinned Scenario CC BY 4.0 file; excludes Hunyuan companion.",
         {"file": string(), "max_mb": INTEGER}, ["file"]),
    tool("export_glb", "Export Blender scene/cameras/punctual lights/animations to GLB. Refuses NPR/volume material loss unless explicitly allowed; never silently promises render equivalence.",
         {"path": string(), "selected_only": BOOLEAN, "allow_material_loss": BOOLEAN}),
    tool("build_threejs_viewer", "Build HTML + local GLB Three.js viewer with orbit camera, camera selector and animation clips; CDN libraries require internet.",
         {"glb_path": string(), "directory": string()}, ["glb_path", "directory"]),
    tool("preview_threejs", "Serve a generated viewer over loopback HTTP until MCP server exits; does not publish or upload it.",
         {"directory": string()}, ["directory"]),
    tool("create_threejs_project", "Create editable reference-to-code model, sparse voxel helper, deterministic evaluate(t), GLB export and optional Playwright frame-capture script. Reference image is guidance, not automatic reconstruction.",
         {"directory": string(), "brief": string(), "reference_path": string(), "project_directory": string()}, ["directory"]),
]
INDEX = {t["name"]: t for t in TOOLS}


def validate(value, spec, path="arguments"):
    kind = spec.get("type")
    checks = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
              "string": lambda x: isinstance(x, str), "boolean": lambda x: isinstance(x, bool),
              "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
              "number": lambda x: isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x)}
    if kind and not checks[kind](value):
        raise ValueError(path + " must be " + kind)
    if "enum" in spec and value not in spec["enum"]:
        raise ValueError(path + " has an unsupported value")
    if kind == "object":
        if any(k not in value for k in spec.get("required", [])):
            raise ValueError(path + " missing required fields")
        props = spec.get("properties", {})
        if not spec.get("additionalProperties", True) and any(k not in props for k in value):
            raise ValueError(path + " contains unknown fields")
        for key, item in value.items():
            if key in props:
                validate(item, props[key], path + "." + key)
    if kind == "array":
        if not spec.get("minItems", 0) <= len(value) <= spec.get("maxItems", 100000):
            raise ValueError(path + " has invalid length")
        for item in value:
            validate(item, spec["items"], path + "[]")


class Server:
    def __init__(self, config):
        self.config, self.client = config, Client(config)
        self.assets = Assets(config)
        self.datasets = Datasets(config)

    def call(self, name, arguments):
        if name not in INDEX:
            raise ValueError("Unknown tool: " + name)
        validate(arguments, INDEX[name]["inputSchema"])
        if name == "pipeline_init":
            value = pipeline.init(**arguments)
        elif name == "pipeline_status":
            value = pipeline.status(**arguments)
        elif name == "pipeline_reference":
            value = pipeline.record_reference(**arguments)
        elif name == "pipeline_stage":
            value = pipeline.record_stage(**arguments)
        elif name == "pipeline_delivery_check":
            value = pipeline.delivery_check(**arguments)
        elif name == "pipeline_approve":
            value = pipeline.approve(**arguments)
        elif name == "inspect_threejs_transfer":
            value = transfer.inspect_bundle(**arguments)
        elif name == "import_threejs_scene":
            params = dict(arguments)
            project = params.pop("project_directory", "")
            if project:
                pipeline.status(project)
            transfer.inspect_bundle(params["glb_path"], params["manifest_path"])
            value = self.client.call(name, params)
            if project:
                pipeline.auto_stage(project, "blender_import", artifacts=[params["glb_path"], params["manifest_path"], value["checkpoint"]],
                                    notes="Import observed; check render, hierarchy, camera, materials and packed images before passing")
        elif name == "blender_launch":
            value = self.client.launch(**arguments)
        elif name == "production_project_init":
            value = production.initialize(**arguments)
            value["pipeline"] = pipeline.init(arguments["directory"], arguments.get("title", "Untitled production"))
        elif name == "asset_search":
            value = self.assets.search(**arguments)
        elif name == "asset_files":
            value = self.assets.files(**arguments)
        elif name == "asset_download":
            value = self.assets.download(**arguments)
        elif name == "film_reference_search":
            value = film_references(**arguments)
        elif name == "asset_sources":
            value = asset_sources(**arguments)
        elif name == "city_search":
            value = self.datasets.city_search(**arguments)
        elif name == "abo_search":
            value = self.datasets.abo_search(**arguments)
        elif name == "city_download":
            value = self.datasets.download("city", arguments["tile_id"], arguments.get("max_mb", 64))
        elif name == "abo_download":
            value = self.datasets.download("abo", arguments["model_id"], arguments.get("max_mb", 64))
        elif name == "scenario_search":
            value = self.datasets.scenario_search(**arguments)
        elif name == "scenario_download":
            value = self.datasets.download("scenario", arguments["file"], arguments.get("max_mb", 64))
        elif name == "polyfork_search":
            value = self.assets.polyfork_search(**arguments)
        elif name == "polyfork_download":
            value = self.assets.polyfork_download(**arguments)
        elif name == "build_threejs_viewer":
            value = web.build(**arguments)
        elif name == "preview_threejs":
            value = web.preview(**arguments)
        elif name == "create_threejs_project":
            params = dict(arguments)
            project = params.pop("project_directory", "")
            if project:
                pipeline.status(project)
            value = authoring.scaffold(**params)
            if project:
                pipeline.auto_stage(project, "threejs", artifacts=[value["html"]], notes="Scaffold created; modeling, preview and visual review still required")
        elif name == "city_import":
            provenance = json.loads(Path(arguments["provenance"]).read_text(encoding="utf-8"))
            if provenance.get("dataset") != "city" or provenance.get("license") != "CC-BY-4.0":
                raise ValueError("Expected PLATEAU download provenance")
            value = self.client.call("city_import", {"path": provenance["path"], "offset": provenance["blender_offset"] if arguments.get("place_at_city_offset", False) else [0, 0, 0]})
            value["attribution"] = provenance["attribution"]
        elif name == "image_preview":
            path = Path(arguments["path"]).resolve(strict=True)
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Preview too large; render at a smaller resolution")
            data = path.read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Only PNG previews supported")
            return {"content": [{"type": "image", "mimeType": "image/png", "data": base64.b64encode(data).decode("ascii")}]}
        else:
            value = self.client.call("status" if name == "blender_status" else name, arguments)
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}

    def handle(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32600, "message": "Invalid Request"}}
        method = request["method"]
        if "id" not in request:
            return None
        response = {"jsonrpc": "2.0", "id": request["id"]}
        params = request.get("params", {})
        try:
            if method == "initialize":
                version = params.get("protocolVersion", "2024-11-05")
                if version not in ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"):
                    version = "2025-11-25"
                response["result"] = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                                      "serverInfo": {"name": "blender-codex-studio", "version": __version__}}
            elif method == "ping":
                response["result"] = {}
            elif method == "tools/list":
                response["result"] = {"tools": TOOLS}
            elif method == "tools/call":
                try:
                    response["result"] = self.call(params["name"], params.get("arguments", {}))
                except Exception as error:
                    response["result"] = {"content": [{"type": "text", "text": f"{type(error).__name__}: {error}"}], "isError": True}
            else:
                response["error"] = {"code": -32601, "message": "Method not found"}
        except (KeyError, TypeError, ValueError) as error:
            response["error"] = {"code": -32602, "message": str(error)}
        return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    server = Server(load_config(args.config))
    for line in sys.stdin.buffer:
        try:
            if len(line) > 2 * 1024 * 1024:
                raise ValueError("MCP request exceeds size limit")
            response = server.handle(json.loads(line))
        except (ValueError, UnicodeError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        except Exception:
            traceback.print_exc(file=sys.stderr)
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": "Internal error"}}
        if response:
            sys.stdout.buffer.write((json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
