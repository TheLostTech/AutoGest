"""Oil filter housing with oil cooler (supporto filtro olio), as fitted to small diesels:
cast-aluminium body with a machined mounting flange and four bolts, vertical filter
cup closed by a ribbed black plastic cartridge cap with hex, brazed plate-type oil
cooler (stacked aluminium plates, top cover and two coolant hose stubs with beads),
oil pressure switch with connector, temperature sender and a hex port plug.

Z up, mounting face in the plane y=0 (block side +Y). 1 unit = 100 mm."""
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
FX = (0.0, -0.62)      # filter axis (x, y)
RF = 0.44


def body(alu, face_m, dark):
    bm = bmesh.new()
    cyl_axis(bm, RF, (FX[0], FX[1], -0.10), (0, 0, 1), 0.0, 0.98, seg=96)       # filter cup
    box(bm, -0.55, 0.55, -0.48, -0.02, -0.18, 0.62)                             # neck to flange
    box(bm, -0.70, 0.70, -0.16, 0.0, -0.30, 0.78)                               # mounting flange
    box(bm, 0.25, 1.45, -1.02, -0.18, -0.16, 0.10)                              # cooler seat
    cyl_axis(bm, 0.13, (-0.40, -0.55, 0.15), (-1, 0, 0), 0.0, 0.25, seg=32)     # pressure switch boss
    cyl_axis(bm, 0.11, (-0.30, -0.92, 0.30), (-0.6, -1, 0), 0.0, 0.25, seg=32)  # temp sender boss
    cyl_axis(bm, 0.10, (0.40, -0.40, 0.45), (1, -0.4, 0), 0.0, 0.22, seg=32)    # plugged port boss
    for (x, z) in ((-0.58, -0.18), (0.58, -0.18), (-0.58, 0.66), (0.58, 0.66)):
        cyl_axis(bm, 0.12, (x, -0.24, z), (0, 1, 0), 0.0, 0.24, seg=32)        # bolt bosses
    ob = cast("FilterBody", bm, alu, voxel=0.01 if not FAST else 0.018, iters=4, fac=0.5)
    cuts = []

    def cutter(fill, mat):
        cb = bmesh.new()
        fill(cb)
        C.fix_normals(cb)
        c = C.mesh_obj("FCut", cb, [mat])
        boolean(ob, c)
        cuts.append(c)
    cutter(lambda cb: box(cb, -2, 2, -0.01, 1.0, -1, 2), face_m)
    cutter(lambda cb: cyl_axis(cb, 0.6, (FX[0], FX[1], 0.86), (0, 0, 1), 0.0, 1.0, seg=96), face_m)
    cutter(lambda cb: box(cb, 0.22, 1.5, -1.1, -0.1, 0.08, 1.0), face_m)
    cutter(lambda cb: [cyl_axis(cb, 0.05, (x, -0.6, z), (0, 1, 0), 0.0, 1.0, seg=20)
                       for (x, z) in ((-0.58, -0.18), (0.58, -0.18), (-0.58, 0.66), (0.58, 0.66))], dark)
    return [C.finalize(ob, angle=40, remove=cuts)]


def cap(black, dark):
    out = []

    def ribs(r, z, t):
        if z < 0.98 or z > 1.42 or r < RF - 0.02:
            return r
        return r + 0.022 * (0.5 + 0.5 * max(-1.0, min(1.0, 4 * math.cos(20 * t))))
    P = [(0.0, 0.86, 0), (RF + 0.01, 0.86, 0), (RF + 0.03, 0.88, 0), (RF + 0.03, 0.96, 0), (RF, 0.98, 0), (RF, 1.42, 0),
         (RF - 0.04, 1.50, 0), (0.30, 1.55, 0), (0.0, 1.55, 0)]
    c = C.lathe("Cap", P, [black], steps=160, mod=ribs)
    c.matrix_world = Matrix.Translation((FX[0], FX[1], 0))
    C.add_bevel(c, 0.006, segments=1, angle=40)
    out.append(C.finalize(c, angle=40))
    out.append(hex_at("CapHex", 0.20, 1.53, 1.66, black, Matrix.Translation((FX[0], FX[1], 0)), bevel=0.014))
    out.append(lathe_at("CapORing", [(RF + 0.0, 0.85, 0), (RF + 0.035, 0.85, 0), (RF + 0.035, 0.87, 0), (RF, 0.87, 0)],
                        C.mat_rubber("ORing"), Matrix.Translation((FX[0], FX[1], 0)), steps=96))
    return out


def cooler(plate_a, plate_b, alu_c, pipe_m):
    out = []
    z = 0.10
    T = Matrix.Translation((0.85, -0.60, 0))
    for k in range(9):
        th = 0.032 if k % 2 == 0 else 0.022
        m = plate_a if k % 2 == 0 else plate_b
        w = 1.12 if k % 2 == 0 else 1.08
        def pl(bm, z=z, th=th, w=w):
            prism_bm(bm, rrect(w, 0.80 - (1.12 - w), 0.16, 6), z, z + th, T)
        out.append(solid("Plate", pl, [m], bevel=0.006, angle=40))
        z += th
    def top(bm):
        prism_bm(bm, rrect(1.14, 0.82, 0.17, 6), z, z + 0.06, T)
    out.append(solid("CoolerTop", top, [alu_c], bevel=0.012, angle=40))
    # centre screw (hollow bolt) and coolant stubs
    out.append(hex_at("CoolerNut", 0.11, z + 0.06, z + 0.15, pipe_m, T @ Matrix.Translation((0, 0, 0)), bevel=0.01))
    for dx, ang in ((-0.36, 0.5), (0.36, -0.2)):
        base = Vector((0.85 + dx, -0.60 - 0.18, z + 0.06))
        d = Vector((0.25 * math.copysign(1, dx), -0.55, 0.75)).normalized()
        M = frame_to(base, d)
        P = [(0.0, -0.02, 0), (0.095, -0.02, 0), (0.095, 0.03, 0), (0.07, 0.05, 0), (0.07, 0.30, 0), (0.085, 0.32, 0),
             (0.085, 0.35, 0), (0.07, 0.37, 0), (0.07, 0.44, 0), (0.055, 0.45, 0), (0.055, 0.0, 1)]
        out.append(lathe_at("Stub", P, pipe_m, M, steps=48, mats=[pipe_m, C.principled("Hole", (0.01, 0.01, 0.01), rough=0.8)]))
    return out


def sensors(steel, black, brass):
    out = []
    # oil pressure switch on -X boss
    M = Matrix.Translation((-0.65, -0.55, 0.15)) @ RYm
    out.append(hex_at("PSHex", 0.10, 0.0, 0.08, steel, M, bevel=0.008))
    out.append(lathe_at("PSBody", [(0.0, 0.08, 0), (0.085, 0.08, 0), (0.085, 0.20, 0), (0.06, 0.24, 0), (0.0, 0.24, 0)], black, M, steps=40))
    def plug(bm):
        C.box_bm(bm, 0.14, 0.16, 0.18, center=(0, 0, 0.30), matrix=M)
    out.append(solid("PSConn", plug, [black], bevel=0.015))
    # temperature sender
    d = Vector((-0.6, -1, 0)).normalized()
    M2 = frame_to(Vector((-0.30, -0.92, 0.30)) + d * 0.25, d)
    out.append(hex_at("TSHex", 0.085, 0.0, 0.07, brass, M2, bevel=0.008))
    out.append(lathe_at("TSBody", [(0.0, 0.07, 0), (0.06, 0.07, 0), (0.06, 0.16, 0), (0.04, 0.19, 0), (0.0, 0.19, 0)], black, M2, steps=32))
    # hex port plug
    d3 = Vector((1, -0.4, 0)).normalized()
    M3 = frame_to(Vector((0.40, -0.40, 0.45)) + d3 * 0.22, d3)
    out.append(hex_at("PortPlug", 0.075, 0.0, 0.06, steel, M3, bevel=0.008))
    # mounting bolts (heads on the housing side)
    for (x, z) in ((-0.58, -0.18), (0.58, -0.18), (-0.58, 0.66), (0.58, 0.66)):
        Mb = Matrix.Translation((x, -0.24, z)) @ RX
        out.append(lathe_at("BWasher", [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.09, 0.015, 0), (0.0, 0.015, 0)], steel, Mb, steps=32))
        out.append(hex_at("BHead", 0.07, 0.015, 0.09, steel, Mb, bevel=0.008))
    return out


def build():
    alu = cast_alu("HousingAlu", base=0.44, rough=0.48, grime=0.7, grain=180.0, wear=0.25)
    face = flat_machined("HFace", 0.48, 0.32, "Z", 10.0)
    dark = C.principled("Dark", (0.02, 0.02, 0.02), rough=0.6)
    black = C.mat_black_plastic("CapPA", rough=0.42, color=0.025)
    pa = C.principled("PlateA", (0.56, 0.56, 0.55), metallic=1.0, rough=0.32)
    C.add_noise_bump(pa, scale=600, strength=0.04, distance=0.0004)
    pb = C.principled("PlateB", (0.30, 0.30, 0.30), metallic=1.0, rough=0.45)
    alu_c = C.principled("CoolerTop", (0.50, 0.50, 0.49), metallic=1.0, rough=0.36)
    C.add_noise_bump(alu_c, scale=500, strength=0.05, distance=0.0005)
    pipe = steel_body("StubSteel", 0.52, 0.26)
    brass = C.principled("Brass", (0.62, 0.48, 0.24), metallic=1.0, rough=0.3)
    objs = body(alu, face, dark) + cap(black, dark) + cooler(pa, pb, alu_c, pipe) + sensors(pipe, black, brass)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("supporto-filtro-olio", objs,
         "oil filter housing with plate oil cooler: cast-aluminium body and mounting flange, black cartridge filter cap with hex, coolant stubs, oil pressure switch",
         az=-28, el=26, lens=70, fill=0.86)
