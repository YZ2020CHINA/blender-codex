"""Preflight for the Three.js handoff; no Blender dependency or code execution."""
import hashlib
import json
import math
from pathlib import Path
import struct

LIMITATIONS = ["World/background, hemisphere/area lights and compositor need Blender setup",
              "Custom shaders, reflection helpers and procedural animation are not transferred",
              "Current frame is a static snapshot; compare a Blender render before delivery"]


def inspect_bundle(glb_path, manifest_path):
    path = Path(glb_path).resolve(strict=True)
    manifest_file = Path(manifest_path).resolve(strict=True)
    if path.suffix.lower() != ".glb" or not path.is_file():
        raise ValueError("Expected a local GLB file")
    with path.open("rb") as stream:
        header = stream.read(12)
    if len(header) != 12 or struct.unpack("<4sII", header) != (b"glTF", 2, path.stat().st_size):
        raise ValueError("Invalid GLB v2 header or file size")
    if manifest_file.stat().st_size > 1024 * 1024:
        raise ValueError("Transfer manifest exceeds 1 MiB")
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    if data.get("schema") != "blender-studio-transfer/1" or data.get("up") != "Y" or data.get("units") != "meters":
        raise ValueError("Unsupported transfer schema, units or up axis")
    if data.get("glb") != path.name:
        raise ValueError("Manifest GLB filename differs from selected file")
    with path.open("rb") as stream:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
        digest = hasher.hexdigest()
    if data.get("sha256") != digest:
        raise ValueError("GLB checksum differs from manifest; export/download both files again")
    resolution = data.get("resolution")
    if not isinstance(resolution, list) or len(resolution) != 2 or any(type(n) is not int or not 16 <= n <= 16384 for n in resolution):
        raise ValueError("Transfer resolution must contain two integers between 16 and 16384")
    camera = data.get("camera_projection")
    if not isinstance(camera, dict):
        raise ValueError("Missing camera projection metadata; export again with the current transfer.js")
    def positive(key):
        n = camera.get(key)
        if type(n) not in (int, float) or not math.isfinite(n) or n <= 0:
            raise ValueError("Invalid camera projection: " + key)
        return n
    if camera.get("type") == "perspective":
        if not 1 <= positive("vertical_fov") <= 175:
            raise ValueError("Unsupported vertical field of view")
        aspect = positive("aspect")
    elif camera.get("type") == "orthographic":
        aspect = positive("width") / positive("height")
        if camera.get("center") != [0, 0]:
            raise ValueError("Center the orthographic camera frustum before handoff")
    else:
        raise ValueError("Unsupported camera projection")
    if abs(aspect - resolution[0] / resolution[1]) > 1e-4:
        raise ValueError("Camera aspect differs from export resolution")
    return {"glb": str(path), "manifest": str(manifest_file), "sha256": digest,
            "resolution": resolution, "camera_projection": camera, "limitations": LIMITATIONS}
