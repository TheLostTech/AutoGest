"""Crankshaft (albero motore) of a small inline-4, as removed from the engine: forged
steel webs with eight counterweights and a dark forge-scale finish, ground and polished
main journals (5) and crank pins (4, flat-plane 180 deg) with fillet rolls and oil
holes, timing-end snout with Woodruff keyway and threaded centre hole, rear oil-seal
land and flywheel flange with six bolt holes and pilot bore.

Built along X (snout +X), crank pins 1 and 4 up (+Z). 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RX = Matrix.Rotation(math.pi / 2, 4, "X")       # local Z -> -Y
RXm = Matrix.Rotation(-math.pi / 2, 4, "X")     # local Z -> +Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # local Z -> +X
RYm = Matrix.Rotation(-math.pi / 2, 4, "Y")     # local Z -> -X


# ----------------------------------------------------------------- helpers
def box(bm, x0, x1, y0, y1, z0, z1, mat=0, M=None):
    C.box_bm(bm, x1 - x0, y1 - y0, z1 - z0, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat, matrix=M)


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None, mat=0):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=frame_to(origin, axis), r1=r1, mat=mat)


def shot(name, objs, desc, **kw):
    if FAST:
        kw.update(res=(512, 512), samples=32)
    C.shoot(name, objs, name + ".py", desc, **kw)


def circ(r, n=40, ph=0.0):
    return [(r * math.cos(math.tau * k / n + ph), r * math.sin(math.tau * k / n + ph)) for k in range(n)]


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def frame_to(P, Z):
    """Matrix placing local Z along direction Z at point P."""
    q = Vector(Z).normalized().to_track_quat("Z", "Y")
    return Matrix.Translation(P) @ q.to_matrix().to_4x4()


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), raw=False):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    if raw:
        return ob
    for c in cutters:
        C.add_boolean(ob, c).use_self = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=4, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    cu.resolution_u = 16
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.25
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = grime
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.78, base * 0.72, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.093, 0.08, 1)
    em = C.edge_mask(nt, 0.015, 4.0)
    wm = nt.nodes.new("ShaderNodeMath"); wm.operation = "MULTIPLY"; wm.use_clamp = True
    wm.inputs[1].default_value = wear
    nt.links.new(em, wm.inputs[0])
    mix3 = nt.nodes.new("ShaderNodeMix"); mix3.data_type = "RGBA"
    nt.links.new(wm.outputs[0], mix3.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    mix3.inputs["B"].default_value = (0.72, 0.72, 0.71, 1)
    nt.links.new(mix3.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.25
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.18
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def hot_iron(name="TurbineIron"):
    """Cast iron after heat cycles: dark grey-brown, rusty bloom, coarse sand-cast grain."""
    m = C.mat_cast_iron(name, rust=0.75, base=0.11)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # overall heat oxidation: patches of brown-red scale over the grey iron
    link = next(l for l in nt.links if l.to_node == b and l.to_socket.name == "Base Color")
    src = link.from_socket
    nt.links.remove(link)
    m2 = nt.nodes.new("ShaderNodeMapRange")
    m2.inputs["From Min"].default_value = 0.42
    m2.inputs["From Max"].default_value = 0.68
    m2.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], m2.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(m2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(src, mix.inputs["A"])
    mix.inputs["B"].default_value = (0.16, 0.075, 0.04, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["To Min"].default_value = 0.8
    mm.inputs["To Max"].default_value = 0.3
    nt.links.new(m2.outputs["Result"], mm.inputs["Value"])
    for l in [l for l in nt.links if l.to_node == b and l.to_socket.name == "Metallic"]:
        nt.links.remove(l)
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    return m


def cast(name, bm, mat, voxel=0.010, iters=4, fac=0.5):
    ob = C.mesh_obj(name, bm, [mat])
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = fac
    sm.iterations = iters
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_rusty_iron(name, base=0.10, rust=0.55, scale=5.0, seed=0.0):
    """dark cast iron with blotchy surface rust (more on edges), grainy cast bump"""
    m = C.principled(name, (base, base, base * 1.03), metallic=0.7, rough=0.6)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (seed, seed * 1.7, seed * 0.3)
    nt.links.new(co, mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 12.0
    nz.inputs["Roughness"].default_value = 0.68
    patch = nt.nodes.new("ShaderNodeMapRange")
    patch.inputs["From Min"].default_value = 0.42
    patch.inputs["From Max"].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], patch.inputs["Value"])
    em = C.edge_mask(nt, 0.025, 4.0)
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.use_clamp = True
    add.inputs[1].default_value = 0.6
    nt.links.new(em, add.inputs[0])
    nt.links.new(patch.outputs["Result"], add.inputs[2])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.use_clamp = True
    fac.inputs[1].default_value = rust
    nt.links.new(add.outputs[0], fac.inputs[0])
    # rust colour varies between orange-brown and dark brown
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz2.inputs["Vector"])
    nz2.inputs["Scale"].default_value = 40.0
    nz2.inputs["Detail"].default_value = 6.0
    rc = nt.nodes.new("ShaderNodeValToRGB")
    rc.color_ramp.elements[0].position = 0.35
    rc.color_ramp.elements[0].color = (0.055, 0.024, 0.012, 1)
    rc.color_ramp.elements[1].position = 0.70
    rc.color_ramp.elements[1].color = (0.17, 0.065, 0.025, 1)
    nt.links.new(nz2.outputs["Fac"], rc.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(fac.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.03, 1)
    nt.links.new(rc.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    met = nt.nodes.new("ShaderNodeMapRange")
    met.inputs["To Min"].default_value = 0.7
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(fac.outputs[0], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.55
    ro.inputs["To Max"].default_value = 0.9
    nt.links.new(fac.outputs[0], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # grainy sand-cast bump + rust scale
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 260.0
    g.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    hm = nt.nodes.new("ShaderNodeMath")
    hm.operation = "MULTIPLY_ADD"
    nt.links.new(g.outputs["Fac"], hm.inputs[0])
    hm.inputs[1].default_value = 1.0
    nt.links.new(nz2.outputs["Fac"], hm.inputs[2])
    nt.links.new(hm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def thread_prof(r_root, r_crest, z0, z1, pitch):
    P = []
    z = z0
    while z + pitch <= z1 + 1e-6:
        P += [(r_root, z, 0), (r_crest, z + pitch * 0.5, 0)]
        z += pitch
    P.append((r_root, z, 0))
    return P


def steel_body(name, color=0.50, rough=0.24):
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.6, "Z", rings_scale=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.14
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # faint grime/oxidation
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color, color, color * 1.01, 1)
    mix.inputs["B"].default_value = (color * 0.62, color * 0.58, color * 0.50, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def flat_machined(name, color=0.60, rough=0.26, axis="Z", scale=6.0):
    """Fly-cut face: anisotropic metal with faint arc marks."""
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.5, axis, rings_scale=scale, ring_strength=0.03)
    C.add_noise_bump(m, scale=300, strength=0.03, distance=0.001)
    return m
MAINS = (-1.64, -0.82, 0.0, 0.82, 1.64)
PINS = ((-1.23, 0.0), (-0.41, math.pi), (0.41, math.pi), (1.23, 0.0))
RM, RP, T = 0.25, 0.21, 0.40       # main / pin radius, throw
WM, WP = 0.20, 0.22                # journal widths


def journal(name, x, w, r, mat, oy=0.0, oz=0.0):
    P = [(0.0, -w / 2 - 0.012, 0), (r + 0.035, -w / 2 - 0.012, 0), (r + 0.02, -w / 2 + 0.002, 0), (r, -w / 2 + 0.014, 0),
         (r, w / 2 - 0.014, 0), (r + 0.02, w / 2 - 0.002, 0), (r + 0.035, w / 2 + 0.012, 0), (0.0, w / 2 + 0.012, 0)]
    return lathe_at(name, P, mat, Matrix.Translation((x, oy, oz)) @ RY, steps=96)


def web_section(ang, cw=True):
    """2D outline in the (y, z) plane; pin centre at angle ang from +Z."""
    py, pz = -T * math.sin(ang), T * math.cos(ang)
    pts = [(py + 0.30 * math.cos(t), pz + 0.30 * math.sin(t)) for t in [math.tau * k / 48 for k in range(48)]]
    if cw:
        for k in range(41):
            a = ang + math.pi + math.radians(-68 + 136 * k / 40)
            pts.append((-0.66 * math.sin(a), 0.66 * math.cos(a)))
    else:
        pts += [(0.34 * math.cos(t), 0.34 * math.sin(t)) for t in [math.tau * k / 48 for k in range(48)]]
    # convex hull (monotone chain)
    pts = sorted(set((round(a, 5), round(b, 5)) for a, b in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    hull = lo[:-1] + up[:-1]
    return [(-z, y) for (y, z) in hull]     # prism local (x, y) -> world (-z, y) under RY


def webs(forged):
    out = []
    for (xp, ang) in PINS:
        for s in (-1, 1):
            x0 = xp + s * (WP / 2 + 0.004)
            x1 = xp + s * (0.41 - WM / 2 - 0.004)
            a, b = sorted((x0, x1))

            def fill(bm, a=a, b=b, ang=ang):
                prism_bm(bm, web_section(ang), a, b, RY)
            out.append(solid("Web", fill, [forged], bevel=0.035, seg=3, angle=35))
    return out


def oil_hole(x, ang, r, mat):
    d = Vector((0, -math.sin(ang), math.cos(ang)))
    return lathe_at("OilHole", [(0.0, 0.0, 0), (0.028, 0.0, 0), (0.028, 0.06, 0), (0.0, 0.06, 0)], mat,
                    frame_to(Vector((x, 0, 0)) + d * (r - 0.058), d), steps=20)


def ends(mach, forged, face_m, dark):
    out = []
    # snout (+X): seal land, gear seat with keyway, pulley seat
    x0 = MAINS[-1] + WM / 2
    P = [(0.0, x0, 0), (0.30, x0, 0), (0.30, x0 + 0.05, 0), (0.22, x0 + 0.08, 0), (0.21, x0 + 0.40, 0), (0.19, x0 + 0.42, 0),
         (0.17, x0 + 0.44, 0), (0.17, x0 + 0.74, 0), (0.155, x0 + 0.76, 0), (0.0, x0 + 0.76, 0)]
    sn = C.lathe("Snout", P, [mach], steps=96)
    sn.matrix_world = RY
    cb = bmesh.new()
    box(cb, x0 + 0.12, x0 + 0.38, -0.03, 0.03, 0.16, 0.30)                   # Woodruff keyway
    box(cb, x0 + 0.50, x0 + 0.80, -0.025, 0.025, 0.13, 0.30)
    cyl_axis(cb, 0.05, (x0 + 0.5, 0, 0), (1, 0, 0), 0.0, 0.4, seg=24)       # threaded centre hole
    cut = C.mesh_obj("KeyCut", cb, [dark])
    boolean(sn, cut)
    C.add_bevel(sn, 0.004, segments=1, angle=40)
    out.append(C.finalize(sn, angle=40, remove=[cut]))
    # Woodruff key sitting in the first slot
    def key(bm):
        cyl_axis(bm, 0.12, (x0 + 0.25, 0, 0.13), (0, 1, 0), -0.028, 0.028, seg=32)
    kc = bmesh.new()
    box(kc, x0, x0 + 0.6, -0.1, 0.1, -0.2, 0.155)
    box(kc, x0, x0 + 0.6, -0.1, 0.1, 0.245, 0.5)
    kcut = C.mesh_obj("KeyTrim", kc, [mach])
    out.append(solid("Key", key, [mach], bevel=0.004, cutters=[kcut]))
    # rear: oil-seal land + flywheel flange
    x1 = MAINS[0] - WM / 2
    P = [(0.0, -x1, 0), (0.30, -x1, 0), (0.30, -x1 + 0.17, 0), (0.33, -x1 + 0.18, 0), (0.48, -x1 + 0.19, 0), (0.49, -x1 + 0.21, 0),
         (0.49, -x1 + 0.30, 0), (0.47, -x1 + 0.315, 0), (0.0, -x1 + 0.315, 0)]
    fl = C.lathe("Flange", P, [mach, face_m], steps=128)
    fl.matrix_world = RYm
    cb = bmesh.new()
    for k in range(6):
        t = math.tau * k / 6 + 0.26
        cyl_axis(cb, 0.045, (x1 - 0.40, 0.33 * math.cos(t), 0.33 * math.sin(t)), (1, 0, 0), 0.0, 0.22, seg=24)
    cut = C.mesh_obj("FlHoles", cb, [dark])
    cb2 = bmesh.new()
    cyl_axis(cb2, 0.16, (x1 - 0.46, 0, 0), (1, 0, 0), 0.0, 0.20, seg=48)   # pilot bore
    cyl_axis(cb2, 0.10, (x1 - 0.46, 0, 0), (1, 0, 0), 0.0, 0.40, seg=48)
    cut2 = C.mesh_obj("Pilot", cb2, [dark])
    cb3 = bmesh.new()
    cyl_axis(cb3, 0.6, (0, 0, 0), (-1, 0, 0), -x1 + 0.305, -x1 + 0.6, seg=64)  # faced end
    cut3 = C.mesh_obj("FlFace", cb3, [face_m])
    for c in (cut, cut2, cut3):
        boolean(fl, c)
    C.add_bevel(fl, 0.005, segments=1, angle=40)
    out.append(C.finalize(fl, angle=40, remove=[cut, cut2, cut3]))
    return out


def build():
    mach = C.mat_machined("Journal", color=0.62, rough=0.10, rings=700)
    face = flat_machined("FlangeFace", 0.52, 0.22, "Z", 30.0)
    forged = mat_rusty_iron("ForgedSteel", base=0.075, rust=0.18, scale=6.0, seed=2.0)
    dark = C.principled("Dark", (0.02, 0.02, 0.02), metallic=0.6, rough=0.6)
    objs = []
    for i, x in enumerate(MAINS):
        objs.append(journal("Main", x, WM, RM, mach))
        objs.append(oil_hole(x, 0.7 + i, RM, dark))
    for (x, ang) in PINS:
        objs.append(journal("Pin", x, WP, RP, mach, oy=-T * math.sin(ang), oz=T * math.cos(ang)))
        objs.append(oil_hole(x, ang + 0.9, RP, dark) if False else None)
    objs = [o for o in objs if o is not None]
    # oil holes on the pins
    for (x, ang) in PINS:
        c = Vector((x, -T * math.sin(ang), T * math.cos(ang)))
        d = Vector((0, -math.sin(ang + 0.9), math.cos(ang + 0.9)))
        objs.append(lathe_at("PinHole", [(0.0, 0.0, 0), (0.025, 0.0, 0), (0.025, 0.06, 0), (0.0, 0.06, 0)], dark,
                             frame_to(c + d * (RP - 0.058), d), steps=20))
    objs += webs(forged) + ends(mach, forged, face, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("albero-motore", objs,
         "inline-4 crankshaft: forged webs with counterweights, polished main journals and crank pins, keyed snout, flywheel flange with bolt holes",
         az=-56, el=34, lens=70, fill=0.9)
