"""Blender main-thread operations for cinematic, NPR and 2D-background workflows."""
import contextlib
import io
import json
import math
from pathlib import Path
import random

import bpy
from mathutils import Vector


def vector(value, length=3):
    if len(value) != length or not all(isinstance(v, (float, int)) and math.isfinite(v) for v in value):
        raise ValueError(f"Expected {length} finite numbers")
    return tuple(value)


def bounded(value, low, high):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Value must be between {low} and {high}")
    return value


def obj(name):
    value = bpy.data.objects.get(name)
    if value is None:
        raise ValueError(f"Object not found: {name}")
    return value


def output(path, config, suffix=None):
    root = Path(config["data_dir"]) / "outputs"
    candidate = Path(path)
    candidate = candidate if candidate.is_absolute() else root / candidate
    candidate = candidate.resolve()
    if suffix and candidate.suffix.lower() != suffix:
        raise ValueError(f"Output must end with {suffix}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def aim(ob, target):
    direction = Vector(vector(target)) - ob.location
    if direction.length < 0.0001:
        raise ValueError("Camera/light position and target must differ")
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def material(name, color, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = vector(color, 4)
    mat.use_nodes = True
    node = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if node is None:
        node = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(node.outputs[0], out.inputs["Surface"])
    node.inputs["Base Color"].default_value = color
    node.inputs["Roughness"].default_value = roughness
    return mat


def primitive(p):
    kind = p.get("kind", "cube")
    operators = {"cube": bpy.ops.mesh.primitive_cube_add, "plane": bpy.ops.mesh.primitive_plane_add,
                 "sphere": bpy.ops.mesh.primitive_uv_sphere_add, "cylinder": bpy.ops.mesh.primitive_cylinder_add,
                 "cone": bpy.ops.mesh.primitive_cone_add, "monkey": bpy.ops.mesh.primitive_monkey_add}
    if kind not in operators:
        raise ValueError("Unknown primitive")
    location = vector(p.get("location", [0, 0, 0]))
    scale = vector(p.get("scale", [1, 1, 1]))
    color = vector(p.get("color", [0.5, 0.5, 0.5, 1]), 4)
    operators[kind](location=location)
    ob = bpy.context.object
    ob.name = p.get("name", "StudioObject")
    ob.scale = scale
    ob.data.materials.append(material(ob.name + "_Material", color))
    return {"object": ob.name}


def camera(p):
    location = vector(p.get("location", [7, -10, 6]))
    target = vector(p.get("target", [0, 0, 1]))
    lens = bounded(p.get("lens", 50), 8, 300)
    projection = p.get("projection", "PERSP")
    if projection not in ("PERSP", "ORTHO"):
        raise ValueError("projection must be PERSP or ORTHO")
    bpy.ops.object.camera_add(location=location)
    ob = bpy.context.object
    ob.name = p.get("name", "StudioCamera")
    ob.data.type = projection
    ob.data.lens = lens
    ob.data.ortho_scale = bounded(p.get("ortho_scale", 14), 0.1, 10000)
    aim(ob, target)
    ob.data.dof.use_dof = p.get("dof", False) and projection == "PERSP"
    ob.data.dof.focus_distance = (Vector(target) - ob.location).length
    ob.data.dof.aperture_fstop = bounded(p.get("fstop", 4), 0.5, 64)
    ob.data.show_composition_thirds = True
    ob.data.show_composition_center = True
    bpy.context.scene.camera = ob
    return {"camera": ob.name}


def light(p):
    kind = p.get("kind", "AREA")
    if kind not in ("AREA", "POINT", "SUN", "SPOT"):
        raise ValueError("Unknown light type")
    location = vector(p.get("location", [3, -4, 6]))
    energy = bounded(p.get("energy", 1000), 0, 1000000)
    color = vector(p.get("color", [1, 0.85, 0.7]))
    bpy.ops.object.light_add(type=kind, location=location)
    ob = bpy.context.object
    ob.name = p.get("name", "StudioLight")
    ob.data.energy = energy
    ob.data.color = color
    if kind == "AREA":
        ob.data.shape = "DISK"
        ob.data.size = bounded(p.get("size", 5), 0.01, 1000)
    if kind == "SUN":
        ob.data.angle = math.radians(8)
    aim(ob, p.get("target", [0, 0, 1]))
    return {"light": ob.name}


LIGHTING = {
    "golden_hour": ([1, .66, .35], [0.38, .53, .8], 900, .22),
    "moonlight": ([.36, .55, 1], [.18, .27, .48], 450, .12),
    "studio": ([1, .91, .8], [.65, .78, 1], 1100, .3),
    "anime_soft": ([1, .9, .78], [.65, .8, 1], 850, .5),
    "noir": ([1, .95, .85], [.08, .1, .15], 1700, .025),
}


def lighting(p):
    name = p.get("preset", "golden_hour")
    if name not in LIGHTING:
        raise ValueError("Unknown lighting preset: " + name)
    key, fill, power, world_strength = LIGHTING[name]
    lights = []
    for label, position, color, energy, size in (
        ("Key", [4, -4, 7], key, power, 4), ("Fill", [-4, -1, 4], fill, power * .3, 6),
        ("Rim", [1, 5, 5], key, power * .8, 3)):
        lights.append(light({"name": "Studio" + label, "location": position, "color": color,
                             "energy": energy, "size": size})["light"])
    environment({"mode": "color", "color": fill, "strength": world_strength})
    return {"preset": name, "lights": lights}


def environment(p):
    mode = p.get("mode", "sky")
    strength = bounded(p.get("strength", .4), 0, 100)
    if mode not in ("sky", "color", "hdri"):
        raise ValueError("mode must be sky, color, or hdri")
    image = None
    if mode == "hdri":
        path = Path(p["path"]).resolve(strict=True)
        if path.suffix.lower() not in (".hdr", ".exr"):
            raise ValueError("HDRI must be .hdr or .exr")
        image = bpy.data.images.load(str(path), check_existing=True)
    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    world.node_tree.links.new(bg.outputs[0], out.inputs["Surface"])
    if mode == "color":
        bg.inputs["Color"].default_value = (*vector(p.get("color", [.3, .4, .6])), 1)
    else:
        texture = nodes.new("ShaderNodeTexEnvironment" if mode == "hdri" else "ShaderNodeTexSky")
        if image:
            texture.image = image
            coordinates = nodes.new("ShaderNodeTexCoord")
            mapping = nodes.new("ShaderNodeMapping")
            mapping.inputs["Rotation"].default_value[2] = math.radians(p.get("rotation", 0))
            world.node_tree.links.new(coordinates.outputs["Generated"], mapping.inputs["Vector"])
            world.node_tree.links.new(mapping.outputs[0], texture.inputs[0])
        else:
            sky_types = {item.identifier for item in texture.bl_rna.properties["sky_type"].enum_items}
            texture.sky_type = "NISHITA" if "NISHITA" in sky_types else "MULTIPLE_SCATTERING"
            texture.sun_elevation = math.radians(bounded(p.get("sun_elevation", 25), -10, 90))
        world.node_tree.links.new(texture.outputs[0], bg.inputs["Color"])
    return {"world": world.name, "mode": mode}


def set_material(p):
    ob = obj(p["object"])
    mat = material(p.get("name", ob.name + "_Surface"), p.get("color", [.5, .5, .5, 1]),
                   bounded(p.get("roughness", .6), 0, 1))
    node = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    node.inputs["Metallic"].default_value = bounded(p.get("metallic", 0), 0, 1)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return {"object": ob.name, "material": mat.name}


def toon(p):
    ob = obj(p["object"])
    if ob.type != "MESH":
        raise ValueError("Toon shading requires a mesh")
    color = vector(p.get("color", [.65, .35, .22, 1]), 4)
    bands = int(bounded(p.get("bands", 3), 2, 5))
    # Discover EEVEE identifier across Blender 4/5 without assuming engine spelling.
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    mat = bpy.data.materials.new(ob.name + "_Toon")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    rgb = nodes.new("ShaderNodeShaderToRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    while len(ramp.color_ramp.elements) > 1:
        ramp.color_ramp.elements.remove(ramp.color_ramp.elements[-1])
    for i in range(bands):
        element = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(i / bands)
        element.position = i / bands
        factor = .23 + .77 * i / (bands - 1)
        element.color = tuple(c * factor for c in color[:3]) + (1,)
    emission = nodes.new("ShaderNodeEmission")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(diffuse.outputs[0], rgb.inputs[0])
    links.new(rgb.outputs[0], ramp.inputs[0])
    links.new(ramp.outputs[0], emission.inputs[0])
    links.new(emission.outputs[0], out.inputs["Surface"])
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return {"object": ob.name, "material": mat.name, "bands": bands, "engine": "EEVEE"}


def outline(p):
    scene = bpy.context.scene
    # Freestyle draws silhouettes without altering topology, supported by Cycles.
    scene.render.use_freestyle = p.get("enabled", True)
    scene.render.line_thickness = bounded(p.get("thickness", 1.2), .1, 10)
    settings = bpy.context.view_layer.freestyle_settings
    lineset = settings.linesets[0] if settings.linesets else settings.linesets.new("StudioOutline")
    lineset.linestyle.color = vector(p.get("color", [.025, .02, .03]))
    return {"enabled": scene.render.use_freestyle, "method": "Freestyle", "note": "Render-test your engine; NPR demo uses EEVEE + Freestyle"}


def keyframes(p):
    ob = obj(p["object"])
    prop = p.get("property", "location")
    if prop not in ("location", "rotation_euler", "scale"):
        raise ValueError("Only transform keyframes supported")
    keys = p["keys"]
    if not 1 <= len(keys) <= 1000:
        raise ValueError("Expected 1..1000 keys")
    validated = [(int(bounded(k["frame"], 1, 100000)), vector(k["value"])) for k in keys]
    for frame, value in validated:
        setattr(ob, prop, value)
        ob.keyframe_insert(data_path=prop, frame=frame)
    return {"object": ob.name, "property": prop, "keys": len(keys)}


def shot(p):
    start = int(bounded(p.get("start", 1), 1, 100000))
    end = int(bounded(p.get("end", 72), start + 1, 100001))
    target = vector(p.get("target", [0, 0, 1]))
    first = vector(p.get("from", [7, -10, 5]))
    last = vector(p.get("to", [4, -7, 3]))
    result = camera({"name": p.get("name", "Shot"), "location": first, "target": target,
                     "lens": p.get("lens", 50), "dof": p.get("dof", True), "fstop": p.get("fstop", 5.6)})
    cam = obj(result["camera"])
    # Use a target constraint so orbit/dolly tracks the subject throughout the shot.
    focus = bpy.data.objects.new(cam.name + "_Target", None)
    bpy.context.collection.objects.link(focus)
    focus.location = target
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = focus, "TRACK_NEGATIVE_Z", "UP_Y"
    cam.data.dof.focus_object = focus
    if p.get("motion", "dolly") == "orbit":
        radius = (Vector(first) - Vector(target)).xy.length
        angle = math.atan2(first[1] - target[1], first[0] - target[0])
        sweep = math.radians(bounded(p.get("orbit_degrees", 60), -360, 360))
        keys = [{"frame": round(start + (end - start) * i / 16), "value":
                 [target[0] + radius * math.cos(angle + sweep * i / 16),
                  target[1] + radius * math.sin(angle + sweep * i / 16), first[2]]} for i in range(17)]
    else:
        keys = [{"frame": start, "value": first}, {"frame": end, "value": last}]
    keyframes({"object": cam.name, "keys": keys})
    marker = bpy.context.scene.timeline_markers.new(cam.name, frame=start)
    marker.camera = cam
    cam["studio_shot"] = json.dumps({"start": start, "end": end, "notes": p.get("notes", "")})
    bpy.context.scene.frame_end = max(bpy.context.scene.frame_end, end)
    return {"camera": cam.name, "start": start, "end": end, "motion": p.get("motion", "dolly")}


def shot_list():
    return [{"camera": ob.name, **json.loads(ob["studio_shot"])} for ob in bpy.data.objects if "studio_shot" in ob]


def weather(p):
    kind = p.get("kind", "fog")
    if kind not in ("fog", "rain", "snow"):
        raise ValueError("weather kind must be fog, rain, or snow")
    if kind == "fog":
        primitive({"name": "StudioFog", "scale": p.get("scale", [15, 15, 10]), "location": [0, 0, 5]})
        ob = bpy.context.object
        mat = bpy.data.materials.new("StudioFogVolume")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        volume = nodes.new("ShaderNodeVolumePrincipled")
        volume.inputs["Density"].default_value = bounded(p.get("density", .015), 0, 1)
        out = nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(volume.outputs[0], out.inputs["Volume"])
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        return {"object": ob.name, "kind": kind}
    count = int(bounded(p.get("count", 150), 1, 1000))
    start, end = int(p.get("start", 1)), int(p.get("end", 120))
    if end <= start:
        raise ValueError("end must exceed start")
    rng = random.Random(p.get("seed", 42))
    collection = bpy.data.collections.new("Studio_" + kind)
    bpy.context.scene.collection.children.link(collection)
    # One animated mesh, shared vertices and a Cycles modifier: deterministic, no bake required.
    vertices, faces = [], []
    for _ in range(count):
        x, y, z = rng.uniform(-9, 9), rng.uniform(-7, 7), rng.uniform(0, 14)
        width, height = (.012, .3) if kind == "rain" else (.04, .055)
        base = len(vertices)
        vertices.extend([(x-width, y, z-height), (x+width, y, z-height), (x+width, y, z+height), (x-width, y, z+height)])
        faces.append(tuple(base+i for i in range(4)))
    mesh = bpy.data.meshes.new("PrecipitationMesh")
    mesh.from_pydata(vertices, [], faces)
    ob = bpy.data.objects.new("Studio_" + kind, mesh)
    collection.objects.link(ob)
    mesh.materials.append(material(kind + "_Surface", [.7, .82, .95, 1]))
    keyframes({"object": ob.name, "keys": [{"frame": start, "value": [0, 0, 0]},
              {"frame": end, "value": [2 if kind == "snow" else .5, 0, -14]}]})
    return {"object": ob.name, "kind": kind, "count": count,
            "note": "Stylized precipitation over the requested frame interval; no fluid or collision simulation"}


def billboard(p):
    path = Path(p["path"]).resolve(strict=True)
    if path.suffix.lower() not in (".png", ".webp", ".tga"):
        raise ValueError("Use an image with alpha, such as PNG")
    image = bpy.data.images.load(str(path), check_existing=True)
    cam = obj(p["camera"]) if p.get("camera") else bpy.context.scene.camera
    if not cam:
        raise ValueError("Create a camera first")
    primitive({"kind": "plane", "name": p.get("name", "CharacterCard"),
               "location": p.get("location", [0, 0, 1.6])})
    ob = bpy.context.object
    height = bounded(p.get("height", 3), .01, 1000)
    ob.scale = (height * image.size[0] / max(1, image.size[1]) / 2, height / 2, 1)
    constraint = ob.constraints.new("COPY_ROTATION")
    constraint.target = cam
    mat = bpy.data.materials.new("HandDrawnCard")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    emission = nodes.new("ShaderNodeEmission")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(texture.outputs["Color"], emission.inputs[0])
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return {"object": ob.name, "camera": cam.name, "source": str(path)}


def film_look(p):
    # Blender 5 uses a compositor node-tree group; older versions use scene.node_tree.
    scene = bpy.context.scene
    scene.use_nodes = True
    if hasattr(scene, "compositing_node_group"):
        tree = bpy.data.node_groups.new("StudioFilmCompositor", "CompositorNodeTree")
        scene.compositing_node_group = tree
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        final_type = "NodeGroupOutput"
    else:
        tree = scene.node_tree
        tree.nodes.clear()
        final_type = "CompositorNodeComposite"
    nodes, links = tree.nodes, tree.links
    render = nodes.new("CompositorNodeRLayers")
    balance = nodes.new("CompositorNodeColorBalance")
    if hasattr(balance, "lift"):
        balance.lift = (1.015, 1.0, .985)
        balance.gamma = (1.015, 1.0, .97)
        balance.gain = (1.04, 1.015, .98)
    else:
        for name, color in (("Lift", (1.015, 1, .985, 1)), ("Gamma", (1.015, 1, .97, 1)), ("Gain", (1.04, 1.015, .98, 1))):
            next(i for i in balance.inputs if i.name == name and i.type == "RGBA").default_value = color
    def mix_node(blend, factor, first, second):
        if bpy.app.version >= (5, 0, 0):
            mix = nodes.new("ShaderNodeMix")
            mix.data_type, mix.blend_type = "RGBA", blend
            mix.inputs[0].default_value = factor
            links.new(first, mix.inputs[6])
            links.new(second, mix.inputs[7])
            return mix.outputs[2]
        mix = nodes.new("CompositorNodeMixRGB")
        mix.blend_type = blend
        mix.inputs[0].default_value = factor
        links.new(first, mix.inputs[1])
        links.new(second, mix.inputs[2])
        return mix.outputs[0]
    hue = nodes.new("CompositorNodeHueSat")
    hue.inputs["Saturation"].default_value = bounded(p.get("saturation", .8), 0, 2)
    links.new(render.outputs["Image"], balance.inputs["Image"])
    links.new(balance.outputs[0], hue.inputs["Image"])
    last = hue.outputs[0]
    grain = bounded(p.get("grain", .035), 0, .3)
    if grain:
        rng = random.Random(19)
        width = min(scene.render.resolution_x, 1920)
        height = min(scene.render.resolution_y, 1080)
        noise = bpy.data.images.new("StudioFilmGrain", width, height)
        pixels = []
        for _ in range(width * height):
            v = rng.random()
            pixels.extend((v, v, v, 1))
        noise.pixels.foreach_set(pixels)
        noise.pack()
        source = nodes.new("CompositorNodeImage")
        source.image = noise
        scale = nodes.new("CompositorNodeScale")
        if hasattr(scale, "space"):
            scale.space = "RENDER_SIZE"
        else:
            scale.inputs["Type"].default_value = "Render Size"
        links.new(source.outputs["Image"], scale.inputs["Image"])
        last = mix_node("OVERLAY", grain * 4, last, scale.outputs[0])
    ellipse = nodes.new("CompositorNodeEllipseMask")
    if bpy.app.version >= (5, 0, 0):
        ellipse.inputs["Size"].default_value = (.87, .85)
        ellipse.inputs["Position"].default_value = (.5, .5)
    else:
        ellipse.width, ellipse.height = .87, .85
    blur = nodes.new("CompositorNodeBlur")
    if bpy.app.version >= (5, 0, 0):
        blur.inputs["Type"].default_value = "Gaussian"
        blur.inputs["Size"].default_value = (160, 160)
    else:
        blur.filter_type = "GAUSS"
        blur.size_x = blur.size_y = 160
    links.new(ellipse.outputs[0], blur.inputs[0])
    vignette = mix_node("MULTIPLY", bounded(p.get("vignette", .2), 0, 1), last, blur.outputs[0])
    final = nodes.new(final_type)
    links.new(vignette, final.inputs[0])
    return {"look": "warm vintage film", "grain": grain, "grain_temporal": "static",
            "note": "Aesthetic emulation; not a calibrated film-stock simulation. Replaces compositor; apply to background before character compositing."}


def render_settings(p):
    scene = bpy.context.scene
    width, height = int(bounded(p.get("width", 1280), 64, 8192)), int(bounded(p.get("height", 720), 64, 8192))
    engine = p.get("engine", "eevee")
    if engine == "eevee":
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"
    elif engine == "cycles":
        if any(n.bl_idname == "ShaderNodeShaderToRGB" for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes):
            raise ValueError("Shader-to-RGB toon materials require EEVEE")
        scene.render.engine = "CYCLES"
        scene.cycles.samples = int(bounded(p.get("samples", 32), 1, 4096))
    else:
        raise ValueError("engine must be eevee or cycles")
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.fps = int(bounded(p.get("fps", 24), 1, 120))
    scene.frame_start = int(bounded(p.get("start", 1), 1, 100000))
    scene.frame_end = int(bounded(p.get("end", 120), scene.frame_start, 100000))
    scene.frame_step = int(bounded(p.get("frame_step", 1), 1, 12))
    scene.render.film_transparent = p.get("transparent", False)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "Standard" if p.get("anime", False) else "AgX"
    except TypeError:
        pass
    return {"width": width, "height": height, "fps": scene.render.fps, "engine": scene.render.engine,
            "frame_step": scene.frame_step, "note": "frame_step skips output frames; use stepped_animation for held transform animation"}


def stepped(p):
    ob = obj(p["object"])
    step = int(bounded(p.get("step", 2), 1, 12))
    start, end = bpy.context.scene.frame_start, bpy.context.scene.frame_end
    transforms = []
    for frame in range(start, end + 1, step):
        bpy.context.scene.frame_set(frame)
        transforms.append((frame, tuple(ob.location), tuple(ob.rotation_euler), tuple(ob.scale)))
    for frame, location, rotation, scale in transforms:
        for prop, value in (("location", location), ("rotation_euler", rotation), ("scale", scale)):
            setattr(ob, prop, value)
            ob.keyframe_insert(data_path=prop, frame=frame)
    action = ob.animation_data.action
    curves = []
    if hasattr(action, "fcurves"):
        curves = list(action.fcurves)
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    for curve in curves:
        for point in curve.keyframe_points:
            point.interpolation = "CONSTANT"
    return {"object": ob.name, "step": step, "sampled": len(transforms)}


def group(p):
    name = p["name"]
    collection = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if not collection.users:
        bpy.context.scene.collection.children.link(collection)
    objects = [obj(n) for n in p["objects"]]
    for ob in objects:
        for old in list(ob.users_collection):
            old.objects.unlink(ob)
        collection.objects.link(ob)
    return {"collection": collection.name, "objects": [o.name for o in objects]}


def layers(p, config):
    names = p.get("collections", ["BG_Far", "BG_Mid", "BG_Foreground"])
    collections = [bpy.data.collections.get(n) for n in names]
    if any(c is None for c in collections):
        raise ValueError("Create and populate every requested collection before exporting")
    scene = bpy.context.scene
    state = [(c, c.hide_render) for c in bpy.data.collections]
    transparent, filepath = scene.render.film_transparent, scene.render.filepath
    result = []
    try:
        scene.render.film_transparent = True
        for current in collections:
            for col in collections:
                col.hide_render = col != current
            path = output(str(Path(p.get("directory", "layers")) / (current.name + ".png")), config, ".png")
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            result.append(str(path))
    finally:
        for col, value in state:
            col.hide_render = value
        scene.render.film_transparent, scene.render.filepath = transparent, filepath
    manifest = output(str(Path(p.get("directory", "layers")) / "layers.json"), config)
    manifest.write_text(json.dumps({"layers": result, "camera": scene.camera.name,
                        "note": "Only listed collections are isolated. Shared lights and unlisted geometry remain visible; layers are not occlusion-independent depth plates."}, indent=2), encoding="utf-8")
    return {"files": result, "manifest": str(manifest)}


def import_asset(p):
    path = Path(p["path"]).resolve(strict=True)
    before = set(bpy.data.objects)
    suffix = path.suffix.lower()
    if suffix == ".blend":
        # Append datablocks, never open the file or execute its embedded scripts.
        with bpy.data.libraries.load(str(path), link=False) as (source, dest):
            dest.objects = source.objects
        for ob in dest.objects:
            if ob:
                bpy.context.collection.objects.link(ob)
    elif suffix in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise ValueError("Supported: blend, glb, gltf, fbx, obj")
    return {"objects": sorted(o.name for o in set(bpy.data.objects) - before), "path": str(path)}


def template(p):
    style = p.get("template", "interior")
    if style not in ("interior", "exterior", "anime_stage", "game_isometric"):
        raise ValueError("Unknown template")
    if p.get("clear", False):
        for ob in list(bpy.context.scene.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        scene = bpy.context.scene
        if hasattr(scene, "compositing_node_group"):
            scene.compositing_node_group = None
        elif hasattr(scene, "use_nodes"):
            scene.use_nodes = False
    names = []
    def add(name, location, scale, color, kind="cube"):
        name = primitive({"name": name, "kind": kind, "location": location, "scale": scale, "color": color})["object"]
        names.append(name)
        return name
    add("Ground", [0, 0, -.15], [7, 6, .15], [.22, .3, .24, 1])
    if style in ("interior", "game_isometric"):
        add("BackWall", [0, 4, 2], [7, .12, 2], [.55, .65, .69, 1])
        add("SideWall", [-6, 0, 2], [.12, 4, 2], [.48, .58, .65, 1])
        add("Table", [0, 0, 1.2], [1.8, .85, .12], [.35, .18, .09, 1])
        for x in (-1.5, 1.5):
            for y in (-.6, .6):
                add("TableLeg", [x, y, .55], [.08, .08, .55], [.25, .14, .08, 1])
        add("Seat", [0, -1.8, .6], [.8, .65, .6], [.37, .19, .13, 1])
        add("Shelf", [-4, 2.8, 1], [1.5, .4, 1], [.3, .21, .14, 1])
        add("WindowGlow", [2.5, 3.8, 2.5], [1.5, .08, .9], [.65, .8, 1, 1])
    else:
        for i, (x, y) in enumerate([(-4, 2), (4, 3), (-3, 4), (2, 5)]):
            add("Trunk", [x, y, 1.3], [.2, .2, 1.3], [.25, .12, .06, 1], "cylinder")
            add("Canopy", [x, y, 3.2], [1.3, 1.3, 2], [.13, .32, .2, 1], "cone")
        add("Path", [0, -.5, .02], [1.4, 5, .03], [.45, .38, .29, 1])
        add("DistantBuilding", [-4.5, 5, 1.8], [1, 1, 1.8], [.43, .37, .35, 1])
    hero = add("HeroProxy", [0, .4, 1.1], [.8, .8, .8], [.65, .32, .2, 1], "monkey")
    if style == "anime_stage":
        toon({"object": hero})
    cam = camera({"location": [9, -12, 8] if style == "game_isometric" else [9, -13, 7],
                  "target": [0, 0, 1], "projection": "ORTHO" if style == "game_isometric" else "PERSP",
                  "ortho_scale": 16})
    lighting({"preset": "anime_soft" if style == "anime_stage" else "golden_hour"})
    # Templates use semantic layer collections for independent game-background exports.
    group({"name": "BG_Far", "objects": [n for n in names if any(s in n for s in ("Wall", "Building"))]})
    group({"name": "BG_Mid", "objects": [n for n in names if n != hero and not any(s in n for s in ("Wall", "Building"))]})
    group({"name": "BG_Foreground", "objects": [hero]})
    return {"template": style, "camera": cam["camera"], "hero": hero, "objects": names,
            "note": "Editable blockout geometry; replace proxies with licensed art assets for final production"}


def dispatch(action, p, config):
    if action == "status":
        return {"blender": bpy.app.version_string, "background": bpy.app.background,
                "file": bpy.data.filepath, "frame": bpy.context.scene.frame_current,
                "camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None}
    if action == "scene_info":
        return {"objects": [{"name": o.name, "type": o.type, "location": list(o.location)}
                            for o in bpy.context.scene.objects], "shots": shot_list()}
    functions = {"create_primitive": primitive, "create_camera": camera, "create_light": light,
                 "lighting_preset": lighting, "set_environment": environment, "set_material": set_material,
                 "toon_material": toon, "outline": outline, "keyframes": keyframes, "create_shot": shot,
                 "weather": weather, "character_card": billboard, "film_look": film_look,
                 "render_settings": render_settings, "stepped_animation": stepped, "group_objects": group,
                 "import_asset": import_asset, "scene_template": template}
    if action in functions:
        return functions[action](p)
    if action == "transform_object":
        ob = obj(p["object"])
        values = {key: vector(p[key]) for key in ("location", "rotation_euler", "scale") if key in p}
        for key, value in values.items():
            setattr(ob, key, value)
        return {"object": ob.name}
    if action == "delete_object":
        ob = obj(p["object"])
        bpy.data.objects.remove(ob, do_unlink=True)
        return {"deleted": p["object"]}
    if action == "set_frame":
        bpy.context.scene.frame_set(int(bounded(p["frame"], 1, 100000)))
        return {"frame": bpy.context.scene.frame_current}
    if action == "city_import":
        offset = Vector(vector(p.get("offset", [0, 0, 0])))
        result = import_asset(p)
        imported = {obj(n) for n in result["objects"]}
        for ob in imported:
            if ob.parent not in imported:
                ob.location += offset
        if bpy.context.scene.camera:
            bpy.context.scene.camera.data.clip_end = 10000
        result["offset"] = list(offset)
        return result
    if action == "render_still":
        path = output(p.get("path", "preview.png"), config, ".png")
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        return {"path": str(path)}
    if action == "render_animation":
        path = output(str(Path(p.get("directory", "frames")) / "frame_"), config)
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(animation=True)
        return {"directory": str(path.parent), "format": "PNG sequence", "fps": bpy.context.scene.render.fps}
    if action == "export_layers":
        return layers(p, config)
    if action == "save_scene":
        path = output(p.get("path", "scene.blend"), config, ".blend")
        if path.exists() and not p.get("overwrite", False):
            raise ValueError("File exists; set overwrite=true explicitly")
        if p.get("pack_resources", True):
            bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
        return {"path": str(path)}
    if action == "export_glb":
        path = output(p.get("path", "scene.glb"), config, ".glb")
        unsupported = []
        exported_objects = bpy.context.selected_objects if p.get("selected_only", False) else bpy.context.scene.objects
        used_materials = {slot.material for ob in exported_objects for slot in ob.material_slots if slot.material}
        for mat in used_materials:
            if mat.use_nodes and any(n.bl_idname in ("ShaderNodeShaderToRGB", "ShaderNodeVolumePrincipled") for n in mat.node_tree.nodes):
                unsupported.append(mat.name)
        if unsupported and not p.get("allow_material_loss", False):
            raise ValueError("GLB cannot preserve NPR/volume materials: " + ", ".join(unsupported) + ". Bake/replace them or explicitly allow_material_loss=true")
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_animations=True,
                                  export_cameras=True, export_lights=True, export_apply=False,
                                  use_selection=p.get("selected_only", False))
        return {"path": str(path), "material_warnings": unsupported,
                "limitations": "Compositor/Freestyle/world sky/area lights/weather volumes do not transfer; preview Three.js output"}
    if action == "execute_python":
        if not config.get("allow_python", False):
            raise PermissionError("Python disabled. Enable allow_python in local config and restart the bridge")
        stream = io.StringIO()
        namespace = {"bpy": bpy, "Vector": Vector, "__name__": "__codex__"}
        with contextlib.redirect_stdout(stream):
            exec(p["code"], namespace)
        return {"stdout": stream.getvalue()[-16000:], "result": str(namespace.get("result", ""))[:16000]}
    raise ValueError("Unknown scene action: " + action)
