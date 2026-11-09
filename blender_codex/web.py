"""Generate a small, inspectable Three.js viewer, no remote asset uploads."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading

SERVERS = {}

HTML = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blender Studio · Three.js</title>
<style>body{margin:0;background:#14181c;color:#e8e4dc;font:14px system-ui}canvas{display:block}#ui{position:fixed;top:16px;left:16px;background:#16212bdd;padding:16px;border-radius:12px;max-width:350px}button,select{margin:5px;padding:7px}#status{font-size:12px;white-space:pre-wrap}a{color:#ffc779}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}</script>
</head><body><div id="ui"><b>Blender Studio · Web Scene</b><div><button id="play">暂停动画</button><button id="reset">重置视角</button><select id="camera"><option value="orbit">自由相机</option></select><select id="clips"></select></div><p id="status">正在载入本地 GLB…</p><a href="./scene-manifest.json">场景清单与兼容性</a></div>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled=true;document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#202831');
const free=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.01,10000);free.position.set(8,6,10);
let camera=free,controls=new OrbitControls(free,renderer.domElement),mixer,playing=true,actions=[],box;
const status=document.querySelector('#status'),select=document.querySelector('#camera'),clips=document.querySelector('#clips');
const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
loader.load('./scene.glb',gltf=>{
 scene.add(gltf.scene);gltf.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
 box=new THREE.Box3().setFromObject(gltf.scene);const center=box.getCenter(new THREE.Vector3());const radius=Math.max(box.getSize(new THREE.Vector3()).length(),1);
 free.position.copy(center).add(new THREE.Vector3(radius*.65,radius*.5,radius*.8));free.near=Math.max(.01,radius/10000);free.far=radius*10;free.updateProjectionMatrix();controls.target.copy(center);controls.update();controls.saveState();
 gltf.cameras.forEach((c,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=c.name||`相机 ${i+1}`;select.append(option);});
 select.onchange=()=>{camera=select.value==='orbit'?free:gltf.cameras[Number(select.value)];controls.enabled=camera===free;resize();};
 let lights=0;gltf.scene.traverse(o=>{if(o.isLight)lights++;});if(!lights){scene.add(new THREE.HemisphereLight(0xbad9ff,0x393429,2));const sun=new THREE.DirectionalLight(0xffe1b0,3);sun.position.set(5,8,4);scene.add(sun);}
 mixer=new THREE.AnimationMixer(gltf.scene);actions=gltf.animations.map(clip=>mixer.clipAction(clip));
 gltf.animations.forEach((clip,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=clip.name||`动画 ${i+1}`;clips.append(option);});
 if(actions.length)actions[0].play();clips.onchange=()=>{actions.forEach(a=>a.stop());actions[Number(clips.value)]?.play();};
 status.textContent=`已载入 · ${gltf.cameras.length} 个相机 · ${gltf.animations.length} 段动画\\n拖动旋转，滚轮缩放。网页光照与 Blender 存在差异。`;
},undefined,error=>{status.textContent='载入失败：'+error.message+'\\n请通过本地 HTTP 服务打开；首次联网需能访问 jsDelivr。';});
document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'暂停动画':'播放动画';};
document.querySelector('#reset').onclick=()=>{select.value='orbit';camera=free;controls.enabled=true;controls.reset();resize();};
function resize(){renderer.setSize(innerWidth,innerHeight);if(camera.isPerspectiveCamera){camera.aspect=innerWidth/innerHeight;}camera.updateProjectionMatrix();}addEventListener('resize',resize);
const clock=new THREE.Clock();renderer.setAnimationLoop(()=>{const dt=Math.min(clock.getDelta(),.1);if(playing)mixer?.update(dt);if(controls.enabled)controls.update();renderer.render(scene,camera);});
</script></body></html>'''


def build(glb_path, directory):
    source = Path(glb_path).resolve(strict=True)
    if source.suffix.lower() != ".glb":
        raise ValueError("Expected a GLB exported from Blender")
    folder = Path(directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / "scene.glb"
    if source != destination:
        shutil.copy2(source, destination)
    (folder / "index.html").write_text(HTML, encoding="utf-8")
    manifest = {"asset": "scene.glb", "three_version": "0.180.0", "dependencies": "Pinned jsDelivr modules; internet required. Vendor modules locally for offline distribution.",
                "supported": ["PBR meshes/textures", "skeletal and transform animation", "cameras", "punctual lights"],
                "limitations": ["Blender area lights, compositor, Freestyle, Shader-to-RGB, volumes and particle simulations do not transfer as-is",
                                "Bake compatible materials/textures or render 2D plates before export", "Camera cut markers are metadata; select cameras manually in this viewer",
                                "NLA export can yield separate clips; review clip selection and animation blending", "World HDRI is not embedded as Three.js environment by this viewer"],
                "license": "Viewer code MIT; imported models retain their own licenses"}
    (folder / "scene-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"directory": str(folder), "html": str(folder / "index.html"), "manifest": manifest}


def preview(directory):
    folder = Path(directory).resolve(strict=True)
    if not (folder / "index.html").is_file():
        raise ValueError("No index.html in viewer directory")
    key = str(folder)
    if key not in SERVERS:
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(folder)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        SERVERS[key] = server
    return {"url": f"http://127.0.0.1:{SERVERS[key].server_port}/", "lifetime": "Until this MCP server exits"}
