"""Editable reference-to-code scene scaffold with deterministic frame evaluation."""
import json
from pathlib import Path
import shutil

MODEL = '''import * as THREE from 'three';
// Replace this original blockout after inspecting your reference image.
// Use world metres, Y up. Keep geometry/materials compatible with glTF.
export function createAsset(){
 const root=new THREE.Group(); root.name='EditableAsset';
 const wood=new THREE.MeshStandardMaterial({color:0xa77445,roughness:.8});
 const top=new THREE.Mesh(new THREE.BoxGeometry(3,.18,1.5),wood);top.position.y=1.5;root.add(top);
 for(const x of [-1.25,1.25])for(const z of [-.55,.55]){
  const leg=new THREE.Mesh(new THREE.BoxGeometry(.12,1.5,.12),wood);leg.position.set(x,.75,z);root.add(leg);
 }
 return root;
}
// Stateless: the same t must produce exactly the same pose, even when seeking backwards.
export function evaluate(t,asset,camera){
 asset.rotation.y=.12*Math.sin(t*.7);
 camera.position.set(6*Math.cos(t*.08),3.4,6*Math.sin(t*.08));camera.lookAt(0,1,0);
}
// Optional sparse voxel helper (explicit cells, not automatic image reconstruction).
export function voxelMesh(cells,cellSize=.1){
 const geometry=new THREE.BoxGeometry(cellSize,cellSize,cellSize);
 const material=new THREE.MeshStandardMaterial({vertexColors:false,roughness:1});
 const mesh=new THREE.InstancedMesh(geometry,material,cells.length), matrix=new THREE.Matrix4();
 cells.forEach((c,i)=>{matrix.makeTranslation(c.x*cellSize,c.y*cellSize,c.z*cellSize);mesh.setMatrixAt(i,matrix);mesh.setColorAt(i,new THREE.Color(c.color??0x849474));});
 mesh.instanceMatrix.needsUpdate=true;return mesh;
}
'''

HTML = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Reference to Three.js · Editable Scene</title>
<style>body{margin:0;background:#20252b;color:white;font:14px system-ui}canvas{display:block}aside{position:fixed;top:12px;left:12px;background:#20252bdd;padding:14px;border-radius:10px}button,input{margin:6px}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}</script>
<aside><b>参考图 → 可编辑代码 → GLB</b><p>当前为桌子白模示例，请编辑 model.js。</p><input id="seek" type="range" min="0" max="10" step=".01" value="0"><button id="export">下载 GLB</button><span id="status"></span></aside>
<script type="module">
import * as THREE from 'three';import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';import {createAsset,evaluate} from './model.js';
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x20252b);const asset=createAsset();scene.add(asset);
scene.add(new THREE.HemisphereLight(0xd8e9ff,0x65523a,2));const key=new THREE.DirectionalLight(0xffdfb0,3);key.position.set(4,7,3);scene.add(key);
const camera=new THREE.PerspectiveCamera(40,innerWidth/innerHeight,.1,1000);
window.renderAt=async t=>{evaluate(Number(t),asset,camera);renderer.render(scene,camera);};
document.querySelector('#seek').oninput=e=>window.renderAt(e.target.value);
document.querySelector('#export').onclick=async()=>{try{const buffer=await new GLTFExporter().parseAsync(asset,{binary:true,onlyVisible:true});const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([buffer],{type:'model/gltf-binary'}));a.download='asset.glb';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}catch(e){document.querySelector('#status').textContent=e.message;}};
window.addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();window.renderAt(document.querySelector('#seek').value);});
await window.renderAt(0);window.sceneReady=true;
</script></html>'''

CAPTURE = '''// Optional dependency: install Playwright and its Chromium in your own render environment.
// node capture.mjs http://127.0.0.1:PORT/ 240 24 frames
import {chromium} from 'playwright';import fs from 'node:fs/promises';
const [url,count='24',fps='24',out='frames']=process.argv.slice(2);
if(!url||!/^http:\/\/(127\\.0\\.0\\.1|localhost):\\d+\\/$/.test(url))throw Error('Use the local preview URL');
if(!Number.isInteger(+count)||+count<1||+count>100000||!Number.isFinite(+fps)||+fps<=0)throw Error('Invalid frame range');
await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({headless:true});
try{const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});await page.goto(url);await page.waitForFunction(()=>window.sceneReady===true);
 await page.locator('aside').evaluate(el=>el.style.display='none');
 for(let frame=0;frame<+count;frame++){await page.evaluate(t=>window.renderAt(t),frame/+fps);await page.locator('canvas').screenshot({path:`${out}/${String(frame).padStart(6,'0')}.png`});}
}finally{await browser.close();}
'''


def scaffold(directory, brief="", reference_path=""):
    folder = Path(directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    names = ["index.html", "model.js", "capture.mjs", "quality-contract.json"]
    if any((folder / n).exists() for n in names):
        raise ValueError("Use a new directory; existing authoring files will not be overwritten")
    reference = None
    if reference_path:
        source = Path(reference_path).resolve(strict=True)
        if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Reference must be a PNG/JPEG/WebP image")
        reference = "reference" + source.suffix.lower()
        shutil.copy2(source, folder / reference)
    for name, text in (("model.js", MODEL), ("index.html", HTML), ("capture.mjs", CAPTURE)):
        (folder / name).write_text(text, encoding="utf-8")
    contract = {"brief": brief, "reference": reference, "status": "blockout_needs_review",
                "passes": ["silhouette", "proportions", "negative_space", "materials", "lighting", "motion", "export_import"],
                "reviews": [], "frame_evaluation": "evaluate(t) must be stateless; seed any procedural randomness",
                "limits": "No automatic image reconstruction, music generation or rigging. GLB button exports the current static asset; procedural motion needs explicit baked animation clips or offline frame rendering."}
    (folder / "quality-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"directory": str(folder), "html": str(folder / "index.html"), "reference": reference,
            "next": "Edit model.js from the reference; preview_threejs, compare screenshots, record review evidence, download GLB and import_asset. For deterministic PNG sequences use capture.mjs with optional Playwright."}
