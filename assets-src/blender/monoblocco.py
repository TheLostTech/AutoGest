"""Bare inline-4 engine block (monoblocco) of a small diesel, as removed from the car:
grey cast-iron casting fused from primitives by a voxel remesh (cast fillets), machined
deck with four honed bores, ten head-bolt holes, water-jacket and oil ports and two
dowels; flared crankcase skirt with main-bearing bulkhead ribs and sump flange; on the
exhaust side core plugs, main oil gallery, oil-filter pad and threaded mounting bosses;
machined timing-end face with bolt holes and front crank-seal bore.

Crank axis along X (timing end +X), exhaust side -Y, Z up, z=0 sump face.
1 unit = 100 mm."""
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
L = 3.80
ZD = 2.60          # deck height
ZK = 0.55          # crank axis
BORES = (-1.23, -0.41, 0.41, 1.23)
RB = 0.36
BOLT_X = (-1.64, -0.82, 0.0, 0.82, 1.64)
BOLT_Y = 0.74


def body_bm():
    bm = bmesh.new()
    sec = [(-z, y) for (y, z) in ((-1.10, 0.10), (1.10, 0.10), (1.10, 0.78), (0.92, 1.28), (0.92, ZD - 0.02),
                                  (-0.92, ZD - 0.02), (-0.92, 1.28), (-1.10, 0.78))]
    prism_bm(bm, sec, -L / 2, L / 2, RY)
    box(bm, -L / 2 - 0.02, L / 2 + 0.02, -1.18, 1.18, 0.0, 0.14)                  # sump flange
    box(bm, -L / 2, L / 2, -0.98, 0.98, ZD - 0.20, ZD + 0.02)                    # deck lip
    for x in BOLT_X:                                                             # bulkhead ribs
        for s in (-1, 1):
            y0, y1 = sorted((s * 1.0, s * 1.19))
            box(bm, x - 0.06, x + 0.06, y0, y1, 0.08, 0.86)
    for x in BORES:                                                              # bulges (back side)
        cyl_axis(bm, 0.44, (x, 0.52, 1.30), (0, 0, 1), 0.0, ZD - 1.40, seg=48)
    # exhaust side details
    cyl_axis(bm, 0.10, (-L / 2 + 0.05, -0.93, 1.16), (1, 0, 0), 0.0, L - 0.1, seg=24)      # main oil gallery
    box(bm, 0.62, 1.52, -1.24, -0.80, 0.52, 1.12)                                # oil-filter pad
    for (x, z) in ((1.62, 2.10), (1.62, 1.50), (-1.62, 2.10), (0.82, 2.18)):     # mount bosses
        cyl_axis(bm, 0.12, (x, -0.80, z), (0, -1, 0), 0.0, 0.24, seg=32)
    cyl_axis(bm, 0.09, (-0.62, -1.02, 0.90), (0, -0.2, 1), 0.0, 0.40, seg=24)    # dipstick boss
    # timing end: front cover face pad and crank nose boss
    box(bm, L / 2 - 0.06, L / 2 + 0.06, -0.86, 0.86, 0.18, ZD - 0.04)
    cyl_axis(bm, 0.50, (L / 2 - 0.10, 0, ZK), (1, 0, 0), 0.0, 0.18, seg=48)
    return bm


def block(iron, deck_m, bore_m, hole_m, face_m):
    ob = cast("Block", body_bm(), iron, voxel=0.018 if not FAST else 0.03, iters=5, fac=0.5)
    cutters = []

    def cutter(name, fill, mat):
        bm = bmesh.new()
        fill(bm)
        C.fix_normals(bm)
        c = C.mesh_obj(name, bm, [mat])
        boolean(ob, c)
        cutters.append(c)

    # machined deck and timing-end face (thin slices carry the machined material)
    cutter("DeckSlice", lambda bm: box(bm, -3, 3, -2, 2, ZD - 0.03, ZD + 1.0), deck_m)
    cutter("EndSlice", lambda bm: box(bm, L / 2 + 0.035, L / 2 + 1, -2, 2, 0.16, ZD + 0.5), face_m)
    cutter("PadSlice", lambda bm: box(bm, 0.55, 1.60, -2.0, -1.215, 0.45, 1.2), face_m)
    for i, x in enumerate(BORES):
        cutter("Bore%d" % i, lambda bm, x=x: cyl_axis(bm, RB, (x, 0, 1.15), (0, 0, 1), 0.0, 2.0, seg=96), bore_m)

    def holes(bm):
        for x in BOLT_X:
            for s in (-1, 1):
                cyl_axis(bm, 0.056, (x, s * BOLT_Y, ZD - 0.9), (0, 0, 1), 0.0, 1.2, seg=24)
        for x in BORES:   # water-jacket ports
            for s in (-1, 1):
                for dx in (-0.21, 0.21):
                    prism_bm(bm, rrect(0.17, 0.075, 0.035, 4), ZD - 0.5, ZD + 0.3,
                             Matrix.Translation((x + dx, s * 0.55, 0)) @ Matrix.Rotation(s * dx * 2.2, 4, "Z"))
        for (x, y, r) in ((1.80, 0.55, 0.05), (-1.80, -0.55, 0.05), (1.80, -0.30, 0.035), (-1.80, 0.40, 0.06),
                          (1.81, 0.10, 0.03), (-1.81, -0.15, 0.03)):
            cyl_axis(bm, r, (x, y, ZD - 0.6), (0, 0, 1), 0.0, 1.0, seg=20)
    cutter("DeckHoles", holes, hole_m)

    def endholes(bm):
        cyl_axis(bm, 0.30, (L / 2 - 0.4, 0, ZK), (1, 0, 0), 0.0, 1.0, seg=64)
        for (y, z) in ((-0.75, 0.40), (0.75, 0.40), (-0.75, 1.30), (0.75, 1.30), (-0.70, 2.30), (0.70, 2.30),
                       (0.0, 2.36), (-0.32, 1.85), (0.32, 1.85)):
            cyl_axis(bm, 0.04, (L / 2 - 0.3, y, z), (1, 0, 0), 0.0, 1.0, seg=16)
        cyl_axis(bm, 0.14, (L / 2 - 0.3, -0.38, 1.20), (1, 0, 0), 0.0, 1.0, seg=32)  # water pump port
        # side: filter thread + mount threads + dipstick bore
        cyl_axis(bm, 0.075, (1.07, -0.9, 0.82), (0, -1, 0), 0.0, 1.0, seg=24)
        for (x, z) in ((1.62, 2.10), (1.62, 1.50), (-1.62, 2.10), (0.82, 2.18)):
            cyl_axis(bm, 0.045, (x, -0.7, z), (0, -1, 0), 0.0, 1.0, seg=16)
        cyl_axis(bm, 0.04, (-0.62, -1.02, 0.90), (0, -0.2, 1), 0.0, 1.0, seg=16)
    cutter("EndHoles", endholes, hole_m)

    def plugseats(bm):
        for x in (-1.23, 0.0, 1.23):
            cyl_axis(bm, 0.19, (x, -0.80, 1.80), (0, -1, 0), 0.0, 0.5, seg=40)
    cutter("PlugSeats", plugseats, face_m)
    return C.finalize(ob, angle=40, remove=cutters)


def extras(zinc, steel):
    out = []
    for x in (-1.23, 0.0, 1.23):     # pressed-steel core plugs
        P = [(0.0, -0.01, 0), (0.17, -0.01, 0), (0.185, 0.0, 0), (0.185, 0.035, 0), (0.17, 0.045, 0),
             (0.12, 0.03, 0), (0.0, 0.025, 0)]
        out.append(lathe_at("CorePlug", P, zinc, Matrix.Translation((x, -0.92 + 0.0, 1.80)) @ RX, steps=64))
    for (x, y) in ((1.64, 0.55), (-1.64, -0.55)):   # dowels
        P = [(0.0, ZD - 0.1, 0), (0.05, ZD - 0.1, 0), (0.05, ZD + 0.07, 0), (0.042, ZD + 0.08, 0), (0.0, ZD + 0.08, 0)]
        out.append(lathe_at("Dowel", P, steel, Matrix.Translation((x, y, 0)), steps=32))
    return out


def build():
    iron = mat_rusty_iron("BlockIron", base=0.20, rust=0.32, scale=3.0, seed=1.3)
    deck = flat_machined("DeckFace", 0.55, 0.26, "Z", 2.5)
    face = flat_machined("EndFace", 0.48, 0.30, "X", 4.0)
    bore = C.mat_machined("Bore", color=0.40, rough=0.16, rings=900)
    hole = C.principled("Hole", (0.03, 0.03, 0.03), metallic=0.5, rough=0.7)
    zinc = C.principled("PlugZinc", (0.55, 0.54, 0.50), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=500, strength=0.05, distance=0.0005)
    steel = C.principled("DowelSteel", (0.5, 0.5, 0.5), metallic=1.0, rough=0.25)
    objs = [block(iron, deck, bore, hole, face)] + extras(zinc, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("monoblocco", objs,
         "bare inline-4 cast-iron engine block: machined deck with four bores and head-bolt holes, water ports, crankcase skirt, core plugs, mounting bosses",
         az=34, el=36, lens=70, fill=0.86)
