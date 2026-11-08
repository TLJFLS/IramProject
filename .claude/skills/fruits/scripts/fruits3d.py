"""Scène 3D (Blender / bpy) : des fruits cartoon avec un visage, posés sur un plan de travail de cuisine.

Fonctions principales :
  build_scene(cast)            cast = [{"name": "fraise", "fruit": "fraise"}, ...]
  pose(char, emotion, mouth, blink)
  shot(kind, speaker=None)     kind = "close" | "wide" | "zoom"
  render(path)
"""
import math, random
import bpy
from mathutils import Vector

RES = (720, 1280)
SAMPLES = 16
SPACING = 2.7
CHARS = {}   # nom -> dict(body, eyes, pupils, shines, brows, mouth, tongue, face=(P, N), height)


# ---------- matériaux ----------
def material(name, color, rough=0.4, bump=0.0, bump_scale=40.0, coat=0.0, sss=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    if sss and "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.3, 0.08, 0.05)
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    if bump:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(tex.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def wood_material():
    m = bpy.data.materials.new("bois")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.45
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 0.35
    wave.inputs["Distortion"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.32, 0.17, 0.08, 1)
    ramp.color_ramp.elements[1].color = (0.55, 0.33, 0.17, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def tiles_material():
    m = bpy.data.materials.new("carrelage")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.2
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.55, 0.78, 0.72, 1)
    br.inputs["Color2"].default_value = (0.5, 0.72, 0.68, 1)
    br.inputs["Mortar"].default_value = (0.55, 0.55, 0.55, 1)
    br.inputs["Scale"].default_value = 1.2
    br.offset = 0.0
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    return m


# ---------- géométrie ----------
def sphere(name, seg=96, rings=48, mat=None, loc=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    if mat:
        o.data.materials.append(mat)
    return o


def deform(o, fn):
    for v in o.data.vertices:
        v.co = fn(v.co.copy())
    o.data.update()


def cylinder(name, r, depth, mat, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def leaf(name, mat, loc, rot, size=(0.35, 0.13, 0.03)):
    o = sphere(name, 24, 12, mat, loc, size)
    o.rotation_euler = rot
    return o


GREEN = None
BROWN = None


def make_fruit(kind, x):
    """Crée le corps du fruit centré en x, posé sur le plan (z = 0). Renvoie (corps, hauteur du visage)."""
    rnd = random.Random(hash(kind) % 1000)
    if kind == "orange":
        b = sphere("orange", mat=material("orange", (1.0, 0.33, 0.02), 0.5, 0.35, 70))
        deform(b, lambda v: Vector((v.x, v.y, v.z * 0.94)))
        cylinder("tige", 0.05, 0.14, BROWN, (0, 0, 0.98))
        leaf("feuille", GREEN, (0.18, 0, 1.0), (0, -0.4, 0.3))
        face_z, top = 0.05, 0.94
    elif kind == "pomme":
        b = sphere("pomme", mat=material("pomme", (0.75, 0.03, 0.04), 0.25, 0.05, 20, coat=0.6))
        def f(v):
            d = math.exp(-(v.x ** 2 + v.y ** 2) / 0.06)
            v = Vector((v.x * 1.06, v.y * 1.06, v.z * 0.92))
            v.z += -0.26 * d if v.z > 0 else 0.16 * d
            return v
        deform(b, f)
        cylinder("tige", 0.04, 0.4, BROWN, (0.03, 0, 0.82), (0, 0.2, 0))
        leaf("feuille", GREEN, (0.25, 0, 0.92), (0, -0.5, 0.4), (0.32, 0.14, 0.03))
        face_z, top = 0.0, 0.92
    elif kind == "fraise":
        b = sphere("fraise", mat=material("fraise", (0.85, 0.02, 0.05), 0.3, 0.05, 30, sss=0.1))
        def f(v):
            t = (v.z + 1) / 2
            s = 0.42 + 0.6 * t ** 0.65
            return Vector((v.x * s * 1.05, v.y * s * 1.05, v.z * 1.12))
        deform(b, f)
        seed = material("graine", (0.9, 0.6, 0.1), 0.4)
        for i in range(90):
            th, z = rnd.uniform(0, 2 * math.pi), rnd.uniform(-0.95, 0.85)
            d = Vector((math.cos(th), math.sin(th), 0))
            if d.y < -0.55 and -0.55 < z < 0.75:  # pas de graines sur le visage
                continue
            t = (z / 1.12 + 1) / 2
            r = (0.42 + 0.6 * t ** 0.65) * 1.05 * math.sqrt(max(0, 1 - (z / 1.12) ** 2))
            p = Vector((d.x * r, d.y * r, z))
            s = sphere("graine", 8, 6, seed, p, (0.03, 0.03, 0.045))
            s.rotation_euler = (0, 0, th)
        for k in range(7):
            a = k / 7 * 2 * math.pi
            leaf("sepale", GREEN, (0.3 * math.cos(a), 0.3 * math.sin(a), 1.1), (0.25 * math.sin(a), -0.25 * math.cos(a), a),
                 (0.42, 0.13, 0.03))
        cylinder("tige", 0.05, 0.3, GREEN, (0, 0, 1.25))
        face_z, top = 0.15, 1.12
    elif kind == "citron":
        b = sphere("citron", mat=material("citron", (0.95, 0.78, 0.04), 0.45, 0.3, 70))
        def f(v):
            e = math.exp(-(v.y ** 2 + v.z ** 2) / 0.05)
            return Vector((v.x * 1.2 * (1 + 0.28 * e), v.y * 0.95, v.z * 0.9))
        deform(b, f)
        face_z, top = 0.0, 0.9
    elif kind == "kiwi":
        b = sphere("kiwi", mat=material("kiwi", (0.33, 0.21, 0.09), 0.95, 0.6, 260))
        deform(b, lambda v: Vector((v.x * 0.95, v.y * 0.9, v.z * 1.12)))
        face_z, top = 0.1, 1.12
    elif kind == "banane":
        b = sphere("banane", mat=material("banane", (1.0, 0.72, 0.02), 0.4, 0.05, 10))
        def f(v):
            z = v.z * 1.55
            s = 0.5 * (1 - 0.2 * v.z ** 4)
            return Vector((v.x * s + 0.32 * (v.z ** 2), v.y * s * 0.95, z))
        deform(b, f)
        cylinder("tige", 0.07, 0.3, BROWN, (0.32, 0, 1.68))
        face_z, top = 0.1, 1.55
    else:
        raise ValueError(f"fruit inconnu : {kind}")
    parts = [o for o in bpy.context.scene.objects if o.parent is None and o.get("char") is None and o is not b
             and o.name.split(".")[0] in ("tige", "feuille", "graine", "sepale")]
    for p in parts:
        p.parent = b
        p["char"] = kind
    zmin = min(v.co.z for v in b.data.vertices)
    b.location = (x, 0, -zmin)
    b["char"] = kind
    return b, face_z - zmin, top - zmin


def surface_point(body, x, z):
    """Point de la surface avant (côté caméra, -Y) du corps, en coordonnées monde."""
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nor, *_ = bpy.context.scene.ray_cast(dg, Vector((x, -10, z)), Vector((0, 1, 0)))
    return (loc, nor) if hit else (Vector((x, -1, z)), Vector((0, -1, 0)))


def add_face(name, body, face_h):
    black = material("pupille", (0.01, 0.01, 0.01), 0.15, coat=1.0)
    white = material("blanc", (0.95, 0.95, 0.95), 0.25, coat=0.5)
    shine = material("reflet", (1, 1, 1), 0.1, emission=4.0)
    mouthm = material("bouche", (0.18, 0.02, 0.03), 0.6)
    tongm = material("langue", (0.95, 0.35, 0.4), 0.5)
    browm = material("sourcil", (0.08, 0.04, 0.02), 0.6)
    cx = body.location.x + (0.08 if body["char"] == "banane" else 0)
    bpy.context.view_layer.update()
    c = {"body": body, "eyes": [], "pupils": [], "shines": [], "brows": [], "base": {}}
    k = 0.75 if body["char"] in ("banane",) else 1.0  # visage plus serré sur les fruits fins
    for side in (-1, 1):
        P, N = surface_point(body, cx + side * 0.3 * k, face_h + 0.25)
        e = sphere(f"{name}_oeil", 48, 24, white, P + Vector((0, 0.05, 0)), (0.2 * k, 0.12, 0.24 * k))
        p = sphere(f"{name}_pupille", 32, 16, black, P + Vector((side * -0.02, -0.08, -0.02)), (0.11 * k, 0.06, 0.13 * k))
        s = sphere(f"{name}_reflet", 16, 8, shine, P + Vector((side * -0.02 + 0.04 * k, -0.13, 0.05 * k)), (0.035, 0.02, 0.04))
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.035, depth=0.3,
                                            location=P + Vector((0, -0.04, 0.32)), rotation=(0, math.pi / 2, 0))
        br = bpy.context.object
        bpy.ops.object.shade_smooth()
        br.data.materials.append(browm)
        c["eyes"].append(e); c["pupils"].append(p); c["shines"].append(s); c["brows"].append((br, side))
    P, N = surface_point(body, cx, face_h - 0.2)
    m = sphere(f"{name}_bouche", 48, 24, mouthm, P + Vector((0, 0.03, 0)), (0.2, 0.08, 0.05))
    t = sphere(f"{name}_langue", 24, 12, tongm, P + Vector((0, -0.02, -0.03)), (0.12, 0.05, 0.04))
    c["mouth"], c["tongue"] = m, t
    for o in [*c["eyes"], *c["pupils"], *c["shines"], m, t] + [b for b, _ in c["brows"]]:
        c["base"][o.name] = (o.location.copy(), o.scale.copy(), o.rotation_euler.copy())
    c["face_h"] = face_h
    return c


def build_scene(cast):
    global GREEN, BROWN
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    GREEN = material("vert", (0.12, 0.5, 0.08), 0.5)
    BROWN = material("brun", (0.25, 0.14, 0.06), 0.7)
    CHARS.clear()
    n = len(cast)
    for i, ch in enumerate(cast):
        x = (i - (n - 1) / 2) * SPACING
        body, face_h, top = make_fruit(ch["fruit"], x)
        CHARS[ch["name"]] = add_face(ch["name"], body, face_h)
        CHARS[ch["name"]]["top"] = top
    # cuisine
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 8, 0))
    bpy.context.object.data.materials.append(wood_material())
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 9, 0), rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(tiles_material())
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-4, 8.9, 5), rotation=(math.pi / 2, 0, 0))
    win = bpy.context.object
    win.scale = (5, 3.5, 1)
    win.data.materials.append(material("fenetre", (1.0, 0.92, 0.8), emission=3.0))
    for k, (x, col) in enumerate([(5.5, (0.9, 0.5, 0.1)), (6.6, (0.3, 0.6, 0.15)), (-6.0, (0.85, 0.1, 0.1))]):
        sphere("deco", 32, 16, material(f"deco{k}", col, 0.4), (x, 4.5, 0.6), (0.6, 0.6, 0.6))
    # lumières
    bpy.ops.object.light_add(type="AREA", location=(-3, -6, 6))
    key = bpy.context.object
    key.data.energy, key.data.size = 1200, 5
    key.rotation_euler = (math.radians(50), 0, math.radians(-25))
    bpy.ops.object.light_add(type="AREA", location=(4, 3, 5))
    rim = bpy.context.object
    rim.data.energy, rim.data.size = 900, 3
    rim.rotation_euler = (math.radians(-40), math.radians(30), 0)
    rim.data.color = (1.0, 0.85, 0.7)
    w = bpy.data.worlds.new("monde")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.8, 0.9, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    # caméra
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 2.2
    # rendu
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.image_settings.file_format = "PNG"


EMOTIONS = {  # (rotation des sourcils, hauteur des sourcils, taille des pupilles, largeur de bouche)
    "neutre": (0, 0.0, 1.0, 1.0),
    "joie": (-8, 0.03, 1.0, 1.25),
    "colere": (-22, -0.06, 0.85, 0.8),
    "triste": (22, 0.02, 1.1, 0.75),
    "choc": (0, 0.12, 0.6, 0.9),
    "malin": (-12, 0.0, 0.9, 1.1),
}


def pose(name, emotion="neutre", mouth=0, blink=False):
    c = CHARS[name]
    rot, lift, pup, mw = EMOTIONS.get(emotion, EMOTIONS["neutre"])
    for o in [*c["eyes"], *c["pupils"], *c["shines"], c["mouth"], c["tongue"]] + [b for b, _ in c["brows"]]:
        loc, sc, r = c["base"][o.name]
        o.location, o.scale, o.rotation_euler = loc.copy(), sc.copy(), r.copy()
        o.hide_render = False
    for o in c["pupils"]:
        o.scale *= pup
    if blink:
        for o in c["eyes"]:
            o.scale.z *= 0.12
        for o in [*c["pupils"], *c["shines"]]:
            o.hide_render = True
    for br, side in c["brows"]:
        br.location.z += lift
        br.rotation_euler.y = math.pi / 2 + math.radians(rot) * side
        if emotion == "malin" and side == 1:
            br.location.z += 0.08
            br.rotation_euler.y = math.pi / 2 - math.radians(10)
    m, t = c["mouth"], c["tongue"]
    m.scale.x *= mw
    h = [0.05, 0.11, 0.17, 0.23][mouth]
    m.scale.z = h if emotion != "choc" or mouth else 0.12
    m.location.z -= (h - 0.05) * 0.5
    t.hide_render = mouth == 0
    t.location.z = m.location.z - h * 0.45


def shot(kind, speaker=None):
    cam = bpy.context.scene.camera
    names = list(CHARS)
    if kind == "wide" or speaker is None:
        span = (len(names) - 1) * SPACING + 2.2
        d = max(8.0, span * 1.5)
        z = 1.3
        cam.location = (0, -d, z + 0.6)
        cam.rotation_euler = (math.radians(86), 0, 0)
        cam.data.lens = 35
        cam.data.dof.focus_distance = d
        return
    c = CHARS[speaker]
    b = c["body"]
    d = 4.6 if kind == "zoom" else 6.2
    # caméra plus basse que le visage : le visage reste dans le haut de l'image, au-dessus des sous-titres
    z = c["face_h"] - (0.0 if kind == "zoom" else 0.1)
    off = 0.0 if kind == "zoom" else (-0.35 if b.location.x > 0 else 0.35)
    cam.location = (b.location.x + off, -d, z)
    cam.rotation_euler = (math.radians(87), 0, math.radians(-off * 1.5))
    cam.data.lens = 50
    cam.data.dof.focus_distance = d


def render(path, region=None):
    """region = (x0, y0, x1, y1) en fractions de l'image (origine en bas à gauche) : ne calcule que cette zone."""
    r = bpy.context.scene.render
    r.filepath = path
    r.use_border = region is not None
    r.use_crop_to_border = region is not None
    if region:
        r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = region
    bpy.ops.render.render(write_still=True)


def face_region(name, margin=0.06):
    """Zone de l'image qui contient le visage (yeux, sourcils, bouche) pour la caméra actuelle."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    c = CHARS[name]
    xs, ys = [], []
    for o in [*c["eyes"], c["mouth"]] + [b for b, _ in c["brows"]]:
        for corner in o.bound_box:
            v = world_to_camera_view(sc, sc.camera, o.matrix_world @ Vector(corner))
            xs.append(v.x); ys.append(v.y)
    mx, my = margin, margin * RES[0] / RES[1]
    return (max(0.0, min(xs) - mx), max(0.0, min(ys) - my - 0.04), min(1.0, max(xs) + mx), min(1.0, max(ys) + my))
