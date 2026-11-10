"""Photo-route handoff test with synthetic geometry, labels and instances; no user scene touched.

Requires existing Node/Playwright/Chromium. Set NODE_EXE, PLAYWRIGHT_MODULE,
BROWSER_EXE and optional BROWSER_PROXY; no packages are installed by this test.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex import authoring, pipeline, transfer
from blender_codex.common import load_config, write_json
from server import Server

folder = ROOT / ".state" / ("transfer-" + str(time.time_ns()))
folder.mkdir(parents=True)
authoring.scaffold(folder / "threejs")
model = folder / "threejs/model.js"
text = model.read_text(encoding="utf-8").replace(" return root;", """
 const canvas=document.createElement('canvas');canvas.width=128;canvas.height=64;
 const ctx=canvas.getContext('2d');ctx.fillStyle='#ffe8aa';ctx.fillRect(0,0,128,64);ctx.fillStyle='#252525';ctx.font='bold 22px sans-serif';ctx.fillText('TEST 24h',6,40);
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;
 const sign=new THREE.Mesh(new THREE.BoxGeometry(1,.5,.1),new THREE.MeshStandardMaterial({map:tex}));sign.name='CanvasLabel';sign.position.set(0,2,0);root.add(sign);
 const products=new THREE.InstancedMesh(new THREE.BoxGeometry(.2,.4,.2),new THREE.MeshStandardMaterial({color:0xffffff}),3);products.name='Products';products.position.set(.4,0,.2);
 for(let i=0;i<3;i++){products.setMatrixAt(i,new THREE.Matrix4().makeTranslation(i*.3,1.8,0));products.setColorAt(i,new THREE.Color([0xff2222,0x22ff22,0x2222ff][i]));}root.add(products);
 root.position.set(.25,0,0);
 return root;""")
text = text.replace("camera.lookAt(0,1,0);", "camera.lookAt(0,1,0);asset.updateMatrixWorld(true);camera.updateMatrixWorld(true);window.testProbes=[new THREE.Vector3(1.5,.09,.75),new THREE.Vector3(-1.5,-.09,-.75)].map(v=>{asset.children[0].localToWorld(v);const world=v.toArray();v.project(camera);return {world,screen:[(v.x+1)/2,(v.y+1)/2]};});")
model.write_text(text, encoding="utf-8")
subprocess.run([os.environ.get("NODE_EXE", "node"), str(ROOT / "scripts/transfer_browser.cjs"), str(folder / "threejs")], check=True)
bundle = transfer.inspect_bundle(folder / "threejs/asset.glb", folder / "threejs/asset.transfer.json")
config = load_config(ROOT / "config.json")
config.update(data_dir=str(folder / "bridge"), allow_python=True)  # isolated fixture assertions only
config_path = folder / "test-config.json"
write_json(config_path, config)
server = Server(load_config(config_path))
client = server.client
records = []


def call(name, params):
    result = server.call(name, params)
    value = json.loads(result["content"][0]["text"])
    records.append({"tool": name, "result": value})
    write_json(folder / "results.json", records)
    print(name + ": PASS", flush=True)
    return value


def assertion(code):
    result = client.call("execute_python", {"code": code})
    return result


try:
    client.launch(background=True)
    call("create_primitive", {"name": "ExistingUserObject", "location": [0, 0, -1]})
    pipeline.init(folder)
    imported = call("import_threejs_scene", {"glb_path": bundle["glb"], "manifest_path": bundle["manifest"],
                    "checkpoint_path": str(folder / "before-import.blend"), "project_directory": str(folder)})
    assert len(imported["objects"]) == 12, imported
    assert imported["images"] and all(i["packed"] for i in imported["images"]), imported
    assert pipeline.status(folder)["stages"]["blender_import"]["status"] == "review"
    probes = json.loads((folder / "threejs/probes.json").read_text(encoding="utf-8"))
    assertion("from bpy_extras.object_utils import world_to_camera_view\nexpected=" + repr(probes) + "\nactual=[world_to_camera_view(bpy.context.scene,bpy.context.scene.camera,Vector((p['world'][0],-p['world'][2],p['world'][1]))) for p in expected]\nassert all(abs(a.x-e['screen'][0])<1e-4 and abs(a.y-e['screen'][1])<1e-4 for a,e in zip(actual,expected)), ([(a.x,a.y) for a in actual],expected)\nresult='projected screen points match browser'")
    assertion("expected=" + repr(probes) + "\nmesh=bpy.data.objects['Mesh_0']\nworld=[mesh.matrix_world.__matmul__(vertex.co) for vertex in mesh.data.vertices]\nassert all(min((v-Vector((p['world'][0],-p['world'][2],p['world'][1]))).length for v in world)<1e-4 for p in expected), ([tuple(v) for v in world],expected)\nresult='actual exported geometry matches browser probe positions'")
    assertion("""import math
assert bpy.data.objects.get('ExistingUserObject')
assert bpy.context.scene.camera.name.startswith('TransferCamera')
expected=Vector((6*math.cos(.16),-6*math.sin(.16),3.4))
assert (bpy.context.scene.camera.matrix_world.translation-expected).length<1e-4
assert bpy.context.scene.render.resolution_x==960 and bpy.context.scene.render.resolution_y==540
assert bpy.context.scene.camera.data.sensor_fit=='VERTICAL'
assert abs(2*math.atan(bpy.context.scene.camera.data.sensor_height/(2*bpy.context.scene.camera.data.lens))-math.radians(40))<1e-5
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Products_')]
assert len(meshes)==3
assert len({tuple(o.active_material.diffuse_color) for o in meshes})==3
for o in meshes:
 assert abs(o.dimensions.z-.4)<1e-4
assert len({tuple(round(c,4) for c in o.matrix_world.translation) for o in meshes})==3
result='camera, transforms, dimensions, colors, existing object preserved'
""")
    # A reused checkpoint must be refused before creating additional objects.
    before = len(client.call("scene_info")["objects"])
    try:
        client.call("import_threejs_scene", {"glb_path": bundle["glb"], "manifest_path": bundle["manifest"], "checkpoint_path": str(folder / "before-import.blend")})
    except RuntimeError as error:
        assert "Checkpoint exists" in str(error), error
    else:
        raise AssertionError("Checkpoint overwrite was allowed")
    assert len(client.call("scene_info")["objects"]) == before
    call("lighting_preset", {"preset": "golden_hour"})
    call("render_settings", {"width": 480, "height": 270, "samples": 8})
    call("render_still", {"path": str(folder / "blender.png")})
    call("save_scene", {"path": str(folder / "optimized.blend"), "pack_resources": True})
    assertion("bpy.ops.wm.open_mainfile(filepath=" + repr(str(folder / "optimized.blend")) + ")\nassert bpy.context.scene.camera\nassert all(i.packed_file for i in bpy.data.images if i.type=='IMAGE' and i.source=='FILE')\nresult='saved reopen and packed image check passed'")
    call("render_still", {"path": str(folder / "reopened.png")})
    assertion("bpy.ops.wm.open_mainfile(filepath=" + repr(str(folder / "before-import.blend")) + ")\nassert bpy.data.objects.get('ExistingUserObject')\nassert not any(o.name.startswith('Products_') for o in bpy.context.scene.objects)\nresult='checkpoint contains original scene before import'")
    report = {"status": "passed", "folder": str(folder), "blender": client.call("status")["blender"],
              "checks": ["browser deterministic/source preserved", "GLB checksum", "camera axis/framing resolution", "instance colors/transforms", "embedded canvas texture", "new checkpoint/overwrite refusal", "existing objects preserved", "save/reopen/packed texture", "render after reopen"], "operations": len(records)}
    write_json(folder / "verification.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
finally:
    if client.process and client.process.poll() is None:
        client.process.terminate()
        client.process.wait(timeout=15)
