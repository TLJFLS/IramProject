#!/usr/bin/env python3
"""Vidéo « SOFTNESS 0 % → 100 % » (format satisfying, 9:16) en un seul script, 100 % gratuit (Blender + numpy).

Une capsule tombe sur 4 scies circulaires qui tournent au-dessus d'un socle hexagonal percé d'un trou.
Dure (0 %) : elle rebondit et reste bloquée. Moyenne : elle s'écrase et reste coincée à moitié.
Molle (≥ 60 %) : elle se faufile entre les scies comme de la pâte et tombe dans le trou.

Usage :
  python3 softness.py --out videos/softness/softness.mp4            # 0 à 100 % par pas de 10
  python3 softness.py --steps 0,20,40,60,80,100 --color rouge         # moins d'essais = plus rapide
  python3 softness.py --test                                          # 3 images de contrôle seulement
Options : --fps 24, --seconds 2.8 (par essai), --samples 12, --res 540x960 (agrandi en 1080x1920).
"""
import argparse, math, os, subprocess, sys, tempfile, wave
import numpy as np

COLORS = {"chrome": (0.92, 0.92, 0.95), "or": (1.0, 0.7, 0.18), "bleu": (0.08, 0.35, 0.95), "rouge": (0.9, 0.05, 0.08), "vert": (0.1, 0.75, 0.2),
          "jaune": (1.0, 0.75, 0.02), "rose": (1.0, 0.3, 0.6), "violet": (0.5, 0.15, 0.9), "orange": (1.0, 0.4, 0.02)}

# ---------- géométrie de la capsule et loi de déformation ----------
R0, HC = 0.45, 2.6          # rayon, hauteur
PLANE = 1.26                # dessus des scies (ou haut du tube)
GAP = 0.2                   # rayon du passage entre les 4 scies (ou rayon intérieur du tube)
HOLE = 0.56                 # rayon du trou du socle
GAME = "scies"              # "scies", "tube", "grille" ou "engrenages"
STYLE = "rose"              # "rose" (socle hexagonal) ou "marbre" (marbre gris, bagues dorées, rayons de lumière)
TUBE_IN, TUBE_TOP = 0.3, 1.9
GEAR_R, GEAR_X, GEAR_Z = 0.7, 0.75, 1.55   # rayon des engrenages, écart au centre, hauteur de l'axe


def set_game(game):
    global GAME, PLANE, GAP
    GAME = game
    if game == "tube":
        PLANE, GAP = TUBE_TOP, TUBE_IN
    elif game == "engrenages":  # l'objet repose dans le creux entre les deux engrenages
        PLANE = GEAR_Z + math.sqrt((GEAR_R + R0) ** 2 - GEAR_X ** 2) - R0
        GAP = 0.09
NT, NC, NB = 48, 12, 26     # segments autour, anneaux par demi-sphère, anneaux du corps


def r0_of(h):
    h = np.asarray(h, dtype=float)
    r = np.full_like(h, R0)
    lo, hi = h < R0, h > HC - R0
    r[lo] = np.sqrt(np.clip(R0 ** 2 - (R0 - h[lo]) ** 2, 0, None))
    r[hi] = np.sqrt(np.clip(R0 ** 2 - (h[hi] - (HC - R0)) ** 2, 0, None))
    return r


def capsule_mesh():
    d = (math.pi / 2) / NC
    rings = [R0 + R0 * math.sin(-math.pi / 2 + i * d) for i in range(1, NC + 1)]
    rings += [R0 + (HC - 2 * R0) * j / NB for j in range(1, NB)]
    rings += [HC - R0 + R0 * math.sin(i * d) for i in range(0, NC)]
    th = np.linspace(0, 2 * math.pi, NT, endpoint=False)
    verts_h, verts_t = [0.0], [0.0]
    for h in rings:
        verts_h += [h] * NT
        verts_t += list(th)
    verts_h.append(HC); verts_t.append(0.0)
    faces = []
    nr = len(rings)
    idx = lambda r, k: 1 + r * NT + (k % NT)
    for k in range(NT):
        faces.append((0, idx(0, k + 1), idx(0, k)))
    for r in range(nr - 1):
        for k in range(NT):
            faces.append((idx(r, k), idx(r, k + 1), idx(r + 1, k + 1), idx(r + 1, k)))
    top = 1 + nr * NT
    for k in range(NT):
        faces.append((idx(nr - 1, k), idx(nr - 1, k + 1), top))
    return np.array(verts_h), np.array(verts_t), faces


def init_object(r0, hc):
    """Capsule (r0, hc) ou bille (hc = 2 r0) : maillage + table des volumes."""
    global R0, HC, NB, VH, VT, FACES, _hh, _F, VOL, KC, VF, COS, SIN
    R0, HC = r0, hc
    NB = max(1, int(round(26 * (HC - 2 * R0) / 1.7)))
    VH, VT, FACES = capsule_mesh()
    _hh = np.linspace(0, HC, 4000)
    dv = np.pi * r0_of(_hh) ** 2
    _F = np.concatenate([[0], np.cumsum((dv[1:] + dv[:-1]) / 2 * np.diff(_hh))])
    VOL = _F[-1]
    _F = _F / VOL
    KC = VOL / (math.pi * R0 ** 2 * HC)
    VF = np.interp(VH, _hh, _F)            # fraction de volume de chaque sommet (du bas vers le haut)
    COS, SIN = np.cos(VT), np.sin(VT)


init_object(R0, HC)


def shape(qh):
    return r0_of(qh * HC) / R0


def q_of(fv):
    return np.interp(fv, _F, _hh) / HC


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def state(s, t):
    """Paramètres de forme pour la softness s (0..1) au temps t de l'essai."""
    g = 9.8
    z0 = PLANE + 1.25
    t_hit = math.sqrt(2 * (z0 - PLANE) / g)
    st = {"free": True, "bottom": PLANE, "f": 0.0, "a": 0.0, "bl": 0.9, "drop": 0.0, "jx": 0.0, "jy": 0.0,
          "hit": False, "flat": 0.0}
    if t < t_hit:
        st["bottom"] = z0 - 0.5 * g * t * t
        st["a"] = -0.06 * s * t / t_hit  # s'étire un peu en tombant
        return st
    tau = t - t_hit
    st["hit"] = True
    # écrasement : équilibre + oscillation amortie (plus lente et plus ample quand c'est mou)
    a_eq = 0.0 if s < 0.05 else 0.05 + 0.5 * s ** 1.1
    amp = 0.03 + 0.55 * s
    w = 26 - 16 * s
    st["a"] = a_eq * ease(tau / 0.08) + amp * math.exp(-5.5 * tau) * math.sin(w * tau)
    st["flat"] = min(0.17, max(0.0, st["a"]) * 0.45)
    # rebonds des capsules dures
    hard = 0.1 if GAME == "tube" else 0.25
    if s < hard:
        h1 = (hard - s) * 1.9
        e = 0.42
        tt, h = tau, h1
        while h > 0.004:
            T = 2 * math.sqrt(2 * h / g)
            if tt < T:
                v = math.sqrt(2 * g * h)
                st["bottom"] = PLANE + max(0.0, v * tt - 0.5 * g * tt * tt)
                st["free"] = st["bottom"] > PLANE + 1e-4
                break
            tt -= T
            h *= e * e
        else:
            st["free"] = False
        if not st["free"]:
            st["bottom"] = PLANE
            st["jx"] = 0.012 * math.sin(53 * tau) + 0.007 * math.sin(77 * tau + 1)
            st["jy"] = 0.010 * math.sin(61 * tau + 2)
        return st
    st["free"] = False
    if GAME == "tube":
        pts = [(0.1, 0.0), (0.2, 0.04), (0.5, 0.15), (0.75, 0.32), (0.95, 0.6)]
        fmax = 1.0 if s >= 0.95 else float(np.interp(s, [p[0] for p in pts], [p[1] for p in pts]))
        x = max(0.0, tau - 0.12)
        if fmax < 1.0:
            rate = 0.25 + 0.9 * s
            st["f"] = fmax * (1 - math.exp(-rate * x / max(fmax, 1e-3)))
            st["jx"] = 0.004 * math.sin(41 * tau)
        else:
            rate = 0.9
            st["f"] = min(1.0, (x * rate) ** 1.1)
            done = 1.0 / rate + 0.12
            if tau > done:
                tp = tau - done
                st["drop"] = 1.5 * tp + 0.5 * g * tp * tp
        st["bl"] = 1.0
        return st
    # passage entre les scies
    delay = 0.12
    if s < 0.55:
        fmax = 0.1 + (s - 0.25) * 1.25
        rate = 0.25 + 1.2 * (s - 0.25)
        x = max(0.0, tau - delay)
        st["f"] = fmax * (1 - math.exp(-rate * x / fmax))
        st["jx"] = 0.006 * math.sin(47 * tau)
        st["jy"] = 0.005 * math.sin(59 * tau + 1)
    else:
        rate = 0.6 + 2.6 * (s - 0.55)
        x = max(0.0, tau - delay)
        st["f"] = min(1.0, (x * rate) ** 1.15)
        done = (1.0 ** (1 / 1.15)) / rate + delay
        if tau > done:
            tp = tau - done
            st["drop"] = 1.2 * tp + 0.5 * g * tp * tp
    st["bl"] = 0.88 + 0.08 * math.sin(18 * tau) * math.exp(-2 * tau)
    return st


def deform(st):
    """Position de chaque sommet (N x 3) pour un état donné."""
    if st["free"] or not st["hit"]:
        a = st["a"]
        rad = r0_of(VH) * (1 + a)
        z = st["bottom"] + VH / (1 + a) ** 2
    else:
        f = st["f"]
        Vu, Vl = (1 - f) * VOL, f * VOL
        Ru = R0 * (1 + max(-0.1, st["a"]))
        if Vu > 1e-6:
            Ru = min(Ru, 1.25 * (3 * Vu / (4 * math.pi)) ** (1 / 3))
        Hu = Vu / (math.pi * Ru ** 2 * KC) if Vu > 1e-9 else 0.0
        Rl = GAP if GAME == "tube" else min(R0 * st["bl"], HOLE * 0.9)
        if Vl > 1e-9:
            Rl = min(Rl, 1.1 * (3 * Vl / (4 * math.pi)) ** (1 / 3))
        Hl = Vl / (math.pi * Rl ** 2 * KC) if Vl > 1e-9 else 0.0
        z = np.empty_like(VH)
        rad = np.empty_like(VH)
        low = VF < f
        if low.any():
            q = q_of(VF[low] / max(f, 1e-9))
            z[low] = PLANE - Hl + q * Hl - st["drop"]
            rad[low] = Rl * shape(q)
        up = ~low
        if up.any():
            q = q_of((VF[up] - f) / max(1 - f, 1e-9))
            qc = st["flat"] if f < 0.02 else 0.0
            z[up] = PLANE + Hu * np.clip((q - qc) / (1 - qc), 0, None)
            rad[up] = Ru * shape(q)
        if 0.0 < f < 1.0 and GAME != "tube":  # col de pâte entre les scies
            rad = np.maximum(rad, GAP * np.exp(-((z - PLANE) / 0.12) ** 2))
            rad = np.where(np.abs(z - PLANE) < 0.05, np.minimum(rad, GAP), rad)
        z = z if Vl > 0 else z
    kx = np.ones_like(rad)
    if GAME == "engrenages" and not (st["free"] or not st["hit"]):
        # entre les engrenages la pâte est laminée : très fine en x, large en y
        nip = (z < PLANE) & (z > GEAR_Z - GEAR_R * 0.9)
        kx = np.where(nip, np.minimum(1.0, GAP / np.maximum(rad, 1e-4)), 1.0)
        rad = np.where(nip, np.minimum(rad * 1.25, 0.6), rad)
    x = COS * rad * kx + st["jx"]
    y = SIN * rad + st["jy"]
    return np.stack([x, y, z], axis=1)


# ---------- scène Blender ----------
def build_scene(color, res, samples):
    import bpy, bmesh
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene

    def mat(name, col, rough=0.5, metal=0.0, sss=0.0, emit=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*col, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if sss:
            b.inputs["Subsurface Weight"].default_value = sss
            b.inputs["Subsurface Radius"].default_value = (0.2, 0.2, 0.3)
        if emit:
            b.inputs["Emission Color"].default_value = (*col, 1)
            b.inputs["Emission Strength"].default_value = emit
        return m

    def marble():
        m = bpy.data.materials.new("marbre")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Roughness"].default_value = 0.65
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 6
        n.inputs["Detail"].default_value = 12
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.55, 0.42, 0.75, 1)
        ramp.color_ramp.elements[1].color = (0.92, 0.6, 0.62, 1)
        ramp.color_ramp.elements[0].position = 0.42
        ramp.color_ramp.elements[1].position = 0.58
        nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.25
        nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        return m

    def grey_marble():
        m = bpy.data.materials.new("marbre_gris")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Roughness"].default_value = 0.35
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 3
        n.inputs["Detail"].default_value = 15
        n.inputs["Distortion"].default_value = 2.5
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.32, 0.33, 0.36, 1)
        ramp.color_ramp.elements[1].color = (0.82, 0.83, 0.85, 1)
        ramp.color_ramp.elements[0].position = 0.38
        ramp.color_ramp.elements[1].position = 0.62
        nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        return m

    gold = mat("or", (1.0, 0.72, 0.15), 0.2, 1.0)
    chrome = mat("chrome", (0.9, 0.9, 0.92), 0.12, 1.0)
    stone = grey_marble() if STYLE == "marbre" else marble()
    # socle percé (hexagonal ou rond)
    if STYLE == "marbre":
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.85, depth=4, location=(0, 0, -2))
    else:
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=1.75, depth=4, location=(0, 0, -2),
                                            rotation=(0, 0, math.radians(30)))
    ped = bpy.context.object
    ped.data.materials.append(stone)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=HOLE, depth=6, location=(0, 0, -2))
    cut = bpy.context.object
    mod = ped.modifiers.new("trou", "BOOLEAN")
    mod.operation, mod.object = "DIFFERENCE", cut
    bpy.context.view_layer.objects.active = ped
    bpy.ops.object.modifier_apply(modifier="trou")
    bpy.data.objects.remove(cut)
    bpy.ops.object.shade_flat()
    if STYLE == "marbre":
        bpy.ops.object.shade_smooth()
    # arêtes dorées et bord du trou
    top = [] if STYLE == "marbre" else [ped.matrix_world @ v.co for v in ped.data.vertices if abs((ped.matrix_world @ v.co).z) < 1e-3
           and (ped.matrix_world @ v.co).xy.length > 1.5]
    corners = sorted({(round(v.x, 4), round(v.y, 4)) for v in top}, key=lambda c: math.atan2(c[1], c[0]))
    if STYLE == "marbre":  # bagues dorées et rondelle autour du trou
        for z in (-0.04, -1.0):  # anneaux dorés autour du socle (pas un disque plein)
            bpy.ops.mesh.primitive_torus_add(major_radius=1.85, minor_radius=0.05, major_segments=128, location=(0, 0, z))
            bpy.context.object.data.materials.append(gold)
            bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=HOLE + 0.28, depth=0.04, location=(0, 0, 0.01))
        washer = bpy.context.object
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=HOLE, depth=1, location=(0, 0, 0))
        hcut = bpy.context.object
        wm = washer.modifiers.new("trou", "BOOLEAN")
        wm.operation, wm.object = "DIFFERENCE", hcut
        bpy.context.view_layer.objects.active = washer
        bpy.ops.object.modifier_apply(modifier="trou")
        bpy.data.objects.remove(hcut)
        washer.data.materials.clear()
        washer.data.materials.append(gold)
    for k, (x, y) in enumerate(corners):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.025, depth=4, location=(x, y, -2))
        bpy.context.object.data.materials.append(gold)
        x2, y2 = corners[(k + 1) % 6]
        L = math.hypot(x2 - x, y2 - y)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.025, depth=L, location=((x + x2) / 2, (y + y2) / 2, 0),
                                            rotation=(0, math.pi / 2, math.atan2(y2 - y, x2 - x)))
        bpy.context.object.data.materials.append(gold)
    if STYLE != "marbre":
        bpy.ops.mesh.primitive_torus_add(major_radius=HOLE + 0.02, minor_radius=0.03, location=(0, 0, 0))
        bpy.context.object.data.materials.append(gold)
    # intérieur du trou bien sombre
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=HOLE - 0.005, depth=0.01, location=(0, 0, -1.4))
    bpy.context.object.data.materials.append(mat("fond", (0.02, 0.01, 0.01), 0.9))
    blades = []
    if GAME == "tube":
        glass = bpy.data.materials.new("verre")
        glass.use_nodes = True
        gb = glass.node_tree.nodes["Principled BSDF"]
        gb.inputs["Base Color"].default_value = (0.9, 0.97, 1.0, 1)
        gb.inputs["Roughness"].default_value = 0.02
        gb.inputs["Alpha"].default_value = 0.22  # verre translucide : on voit la capsule dedans
        gb.inputs["Coat Weight"].default_value = 1.0
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=TUBE_IN + 0.06, depth=TUBE_TOP + 1.5,
                                            location=(0, 0, (TUBE_TOP - 1.5) / 2))
        tube = bpy.context.object
        sol = tube.modifiers.new("epaisseur", "SOLIDIFY")
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=TUBE_IN, depth=TUBE_TOP + 2, location=(0, 0, (TUBE_TOP - 1.5) / 2))
        inner = bpy.context.object
        mod = tube.modifiers.new("creux", "BOOLEAN")
        mod.operation, mod.object = "DIFFERENCE", inner
        bpy.context.view_layer.objects.active = tube
        tube.modifiers.remove(sol)
        bpy.ops.object.modifier_apply(modifier="creux")
        bpy.data.objects.remove(inner)
        bpy.ops.object.shade_smooth()
        tube.data.materials.clear()
        tube.data.materials.append(glass)
        bpy.ops.mesh.primitive_torus_add(major_radius=TUBE_IN + 0.03, minor_radius=0.045, location=(0, 0, TUBE_TOP))
        bpy.context.object.data.materials.append(gold)
        bpy.ops.mesh.primitive_torus_add(major_radius=TUBE_IN + 0.08, minor_radius=0.04, location=(0, 0, 0.02))
        bpy.context.object.data.materials.append(gold)
    if GAME == "engrenages":  # deux engrenages qui tournent en sens inverse
        teeth_n = 12
        stp = 2 * math.pi / teeth_n
        outline = []
        for k in range(teeth_n):
            a0 = k * stp
            for frac, rr in ((0.0, 0.55), (0.12, GEAR_R), (0.45, GEAR_R), (0.57, 0.55)):
                outline.append((rr * math.cos(a0 + frac * stp), rr * math.sin(a0 + frac * stp)))
        # maillage construit à la main (faces en éventail depuis le centre : pas de mauvaise triangulation)
        nO = len(outline)
        gverts = [(x, y, -0.75) for x, y in outline] + [(x, y, 0.75) for x, y in outline] + [(0, 0, -0.75), (0, 0, 0.75)]
        cF, cB = 2 * nO, 2 * nO + 1
        gfaces = []
        for i in range(nO):
            j = (i + 1) % nO
            gfaces.append((i, j, nO + j, nO + i))
            gfaces.append((cF, j, i))
            gfaces.append((cB, nO + i, nO + j))
        gb = bmesh.new()
        bvs = [gb.verts.new(v) for v in gverts]
        for f in gfaces:
            gb.faces.new([bvs[i] for i in f])
        bmesh.ops.recalc_face_normals(gb, faces=gb.faces[:])
        gmesh = bpy.data.meshes.new("engrenage")
        gb.to_mesh(gmesh)
        gb.free()
        gmat = grey_marble() if STYLE == "marbre" else stone
        if STYLE == "marbre":  # engrenages plus foncés pour se détacher du fond clair
            r = gmat.node_tree.nodes["Color Ramp"].color_ramp
            r.elements[0].color = (0.16, 0.17, 0.19, 1)
            r.elements[1].color = (0.5, 0.51, 0.54, 1)
            gmat.node_tree.nodes["Noise Texture"].inputs["Scale"].default_value = 1.2
        gmesh.materials.append(gmat)
        for side in (-1, 1):
            g = bpy.data.objects.new("engrenage", gmesh)
            sc.collection.objects.link(g)
            g.location = (side * GEAR_X, 0, GEAR_Z)
            g.rotation_euler = (math.pi / 2, 0, 0)
            g["sens"] = side
            blades.append(g)
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.16, depth=1.56, location=(side * GEAR_X, 0, GEAR_Z),
                                                rotation=(math.pi / 2, 0, 0))
            bpy.context.object.data.materials.append(gold)
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.045, depth=GEAR_Z - GEAR_R * 0.6,
                                                location=(side * GEAR_X, -0.5, (GEAR_Z - GEAR_R * 0.6) / 2))
            bpy.context.object.data.materials.append(chrome)
    if GAME == "grille":  # grille de barreaux, ouverture carrée au centre
        steel = mat("acier", (0.85, 0.85, 0.9), 0.18, 1.0)
        for i, c in enumerate([-1.0, -0.62, -GAP - 0.05, GAP + 0.05, 0.62, 1.0]):
            for axis in (0, 1):
                z = PLANE - 0.05 - (0.1 if axis else 0.0)
                loc = (c, 0, z) if axis == 0 else (0, c, z)
                rot = (math.pi / 2, 0, 0) if axis == 0 else (0, math.pi / 2, 0)
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.05, depth=2.4, location=loc, rotation=rot)
                bpy.context.object.data.materials.append(steel)
                bpy.ops.object.shade_smooth()
        for c in (-1.2, 1.2):  # cadre doré
            for axis in (0, 1):
                loc = (c, 0, PLANE - 0.1) if axis == 0 else (0, c, PLANE - 0.1)
                rot = (math.pi / 2, 0, 0) if axis == 0 else (0, math.pi / 2, 0)
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.07, depth=2.54, location=loc, rotation=rot)
                bpy.context.object.data.materials.append(gold)
    # 4 scies
    Rb = 0.95
    dpos = (Rb + GAP) / math.sqrt(2)
    teeth = 12
    bm = bmesh.new()
    pts = []
    if GAME in ("tube", "grille", "engrenages"):
        teeth = 0
    step = 2 * math.pi / max(teeth, 1)
    for k in range(teeth):
        a0 = k * step
        pts += [(Rb * math.cos(a0), Rb * math.sin(a0)),
                (Rb * 0.84 * math.cos(a0 + 0.12 * step), Rb * 0.84 * math.sin(a0 + 0.12 * step)),
                (Rb * 0.9 * math.cos(a0 + 0.6 * step), Rb * 0.9 * math.sin(a0 + 0.6 * step))]
    if pts:
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        face = bm.faces.new(vs)
        ext = bmesh.ops.extrude_face_region(bm, geom=[face])
        for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
            v.co.z += 0.04
    blade_mesh = bpy.data.meshes.new("scie")
    bm.to_mesh(blade_mesh)
    bm.free()
    for k, (sx, sy) in enumerate([] if GAME in ("tube", "grille", "engrenages") else [(1, 1), (-1, 1), (-1, -1), (1, -1)]):
        o = bpy.data.objects.new(f"scie{k}", blade_mesh)
        sc.collection.objects.link(o)
        o.location = (sx * dpos, sy * dpos, PLANE - 0.04 - (0.045 if k % 2 else 0.0))
        o.data.materials.append(chrome) if k == 0 else None
        blades.append(o)
    # capsule
    me = bpy.data.meshes.new("capsule")
    me.from_pydata([(0, 0, 0)] * len(VH), [], FACES)
    me.update()
    cap = bpy.data.objects.new("capsule", me)
    sc.collection.objects.link(cap)
    metal = color in (COLORS["chrome"], COLORS["or"])
    m = mat("capsule", color if metal else tuple(c * 0.75 for c in color), 0.1 if metal else 0.38, 1.0 if metal else 0.0)
    n = m.node_tree.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 40
    bump = m.node_tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    m.node_tree.links.new(n.outputs["Fac"], bump.inputs["Height"])
    m.node_tree.links.new(bump.outputs["Normal"], m.node_tree.nodes["Principled BSDF"].inputs["Normal"])
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    # fond, lumières, caméra
    w = bpy.data.worlds.new("monde")
    sc.world = w
    w.use_nodes = True
    bg_col, wall_col = ((0.42, 0.26, 0.24), (0.55, 0.36, 0.32)) if STYLE != "marbre" else ((0.6, 0.6, 0.62), (0.78, 0.78, 0.8))
    w.node_tree.nodes["Background"].inputs[0].default_value = (*bg_col, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 3), rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(mat("mur", wall_col, 0.9))
    for loc, en, size, rot in [((-4, -5, 7), 1600, 6, (math.radians(45), 0, math.radians(-35))),
                               ((5, -3, 4), 700, 5, (math.radians(60), 0, math.radians(55))),
                               ((0, 4, 6), 600, 4, (math.radians(-40), 0, 0))]:
        bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
        bpy.context.object.data.energy, bpy.context.object.data.size = en, size
    bpy.ops.object.camera_add(location=(0, -8.2, 3.1))
    camo = bpy.context.object
    sc.camera = camo
    camo.data.lens = 40
    target = Vector((0, 0, 1.75 if GAME in ("tube", "engrenages") else 1.45))
    camo.rotation_euler = (target - camo.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6 if GAME == "tube" else 0
    if GAME == "tube":
        sc.cycles.max_bounces = 8
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    return cap, blades


def render_frame(cap, blades, s, t, gt, path):
    import bpy
    co = deform(state(s, t)).astype(np.float32).ravel()
    cap.data.vertices.foreach_set("co", co)
    cap.data.update()
    for k, b in enumerate(blades):
        if GAME == "engrenages":
            b.rotation_euler.y = b["sens"] * gt * 2.2 + (0.2 if b["sens"] > 0 else 0.0)
        else:
            b.rotation_euler.z = (1 if k % 2 else -1) * gt * 9.0
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------- texte et son ----------
def overlay(frame, s, W=1080, H=1920):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    img = frame.resize((W, H), Image.BICUBIC).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fp = None
    for c in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(c):
            fp = c
            break
    def spaced(text, y, size, spacing):
        f = ImageFont.truetype(fp, size) if fp else ImageFont.load_default(size)
        widths = [d.textlength(ch, font=f) for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = (W - total) / 2
        for ch, wd in zip(text, widths):
            d.text((x, y), ch, font=f, fill=(255, 255, 255, 235))
            x += wd + spacing
    if STYLE == "marbre":
        # rayons de lumière en diagonale + texte noir « XX% SOFT »
        rays = Image.new("L", (W, H), 0)
        rd = ImageDraw.Draw(rays)
        for k, (x0, wd) in enumerate([(520, 70), (650, 110), (800, 60), (900, 140)]):
            rd.polygon([(x0, 0), (x0 + wd, 0), (x0 + wd - 900, H), (x0 - 900, H)], fill=60 + 15 * (k % 2))
        rays = rays.filter(ImageFilter.GaussianBlur(25))
        img = Image.composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), img, rays)
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        txt = f"{int(round(s * 100))}% SOFT"
        tw = d.textlength(txt, font=fb)
        d.text(((W - tw) / 2, 300), txt, font=fb, fill=(15, 12, 12, 255))
        img.alpha_composite(layer)
        return img.convert("RGB")
    spaced("SOFTNESS", 330, 78, 26)
    spaced(f"{int(round(s * 100))} %", 445, 70, 18)
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: v // 2))
    img.alpha_composite(shadow, (0, 5))
    img.alpha_composite(glow)
    img.alpha_composite(layer)
    return img.convert("RGB")


def soundtrack(steps, seconds, sr=44100):
    """Scies qui tournent + impacts + « squish » + plouf, synthétisés."""
    n = int(len(steps) * seconds * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(n)
    def lowpass(x, a):
        y = np.empty_like(x)
        acc = 0.0
        for i in range(0, len(x), 1):
            acc += a * (x[i] - acc)
            y[i] = acc
        return y
    hum = 0.05 * (np.sin(2 * np.pi * 190 * t) + 0.5 * np.sin(2 * np.pi * 380 * t + 1) + 0.25 * np.sin(2 * np.pi * 760 * t))
    hum *= 0.8 + 0.2 * np.sin(2 * np.pi * 3 * t)
    whir = np.convolve(noise, np.ones(8) / 8, mode="same") * 0.03
    out = hum + whir if GAME == "scies" else whir * 0.3
    if GAME == "engrenages":  # cliquetis des dents
        clicks = np.zeros(n)
        L = int(0.012 * sr)
        for k0 in range(0, n - L, int(sr / 11)):
            clicks[k0:k0 + L] += noise[k0:k0 + L] * np.exp(-np.arange(L) / (0.003 * sr)) * 0.25
        out = out + clicks
    t_hit = math.sqrt(2 * 1.25 / 9.8)
    for i, s in enumerate(steps):
        base = i * seconds
        # impact
        k0 = int((base + t_hit) * sr)
        L = int(0.4 * sr)
        tt = np.arange(L) / sr
        freq = 520 - 420 * s
        thud = (np.sin(2 * np.pi * freq * tt) * np.exp(-tt * (30 - 18 * s)) * (0.5 + 0.3 * (1 - s))
                + noise[:L] * np.exp(-tt * 60) * 0.15)
        seg = out[k0:k0 + L]
        seg += thud[:len(seg)]
        if s < 0.25 and GAME == "scies":  # grincement métal sur métal
            k1 = int((base + t_hit + 0.6) * sr)
            L2 = int((seconds - t_hit - 0.7) * sr)
            tt2 = np.arange(L2) / sr
            grind = (noise[k1:k1 + L2] - np.convolve(noise[k1:k1 + L2], np.ones(4) / 4, mode="same")) * 0.12
            grind *= 0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt2) ** 2
            out[k1:k1 + L2] += grind[:len(out[k1:k1 + L2])]
        elif s >= (0.1 if GAME == "tube" else 0.25):  # squish
            dur = 0.5 if s < 0.55 else max(0.25, 1.0 / (0.6 + 2.6 * (s - 0.55)))
            if GAME == "tube":
                dur = 1.1
            k1 = int((base + t_hit + 0.1) * sr)
            L2 = int(dur * sr)
            tt2 = np.arange(L2) / sr
            sq = np.convolve(noise[k1:k1 + L2], np.ones(24) / 24, mode="same") * 1.2
            sq *= np.sin(np.pi * tt2 / dur) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * tt2))
            out[k1:k1 + L2] += sq[:len(out[k1:k1 + L2])]
            if s >= (0.95 if GAME == "tube" else 0.55):  # plouf dans le trou
                k2 = k1 + L2 + int(0.25 * sr)
                L3 = int(0.35 * sr)
                tt3 = np.arange(L3) / sr
                plop = np.sin(2 * np.pi * (380 - 500 * tt3) * tt3) * np.exp(-tt3 * 14) * 0.45
                out[k2:k2 + L3] += plop[:len(out[k2:k2 + L3])]
    out /= max(1e-6, np.abs(out).max()) / 0.85
    return (out * 32767).astype(np.int16), sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="videos/softness/softness.mp4")
    ap.add_argument("--steps", default="0,20,50,75,100")
    ap.add_argument("--game", default="scies", choices=["scies", "tube", "grille", "engrenages"])
    ap.add_argument("--objet", default="capsule", choices=["capsule", "bille"])
    ap.add_argument("--style", default=None, choices=["rose", "marbre"], help="défaut : marbre pour engrenages, sinon rose")
    ap.add_argument("--color", default="bleu")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--seconds", type=float, default=2.8)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--res", default="540x960")
    ap.add_argument("--test", action="store_true", help="rend 3 images de contrôle")
    a = ap.parse_args()
    res = tuple(int(v) for v in a.res.split("x"))
    global STYLE
    STYLE = a.style or ("marbre" if a.game == "engrenages" else "rose")
    if a.objet == "bille":
        init_object(0.6, 1.2)
    set_game(a.game)
    steps = [int(v) / 100 for v in a.steps.split(",")]
    color = COLORS.get(a.color, COLORS["bleu"])
    cap, blades = build_scene(color, res, a.samples)
    from PIL import Image
    tmp = tempfile.mkdtemp()
    if a.test:
        outdir = os.path.dirname(os.path.abspath(a.out))
        os.makedirs(outdir, exist_ok=True)
        import time
        for s, t in [(0.0, 2.0), (0.5, 2.2), (1.0, 1.2)]:
            p = os.path.join(tmp, "t.png")
            t0 = time.time()
            render_frame(cap, blades, s, t, t, p)
            print(f"  image {int(s * 100)} % : {time.time() - t0:.1f} s", flush=True)
            overlay(Image.open(p), s).save(os.path.join(outdir, f"test_{a.game}_{int(s * 100)}.png"))
        print("images de test :", outdir)
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                            "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    per = int(round(a.seconds * a.fps))
    for i, s in enumerate(steps):
        for k in range(per):
            t = k / a.fps
            p = os.path.join(tmp, "f.png")
            render_frame(cap, blades, s, t, i * a.seconds + t, p)
            enc.stdin.write(overlay(Image.open(p), s).tobytes())
        print(f"  {int(s * 100)} % ok", flush=True)
    enc.stdin.close()
    enc.wait()
    audio, sr = soundtrack(steps, a.seconds)
    apath = os.path.join(tmp, "a.wav")
    with wave.open(apath, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", apath, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", a.out], check=True)
    print("Vidéo prête :", a.out)


if __name__ == "__main__":
    main()
