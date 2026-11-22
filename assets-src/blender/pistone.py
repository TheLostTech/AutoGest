"""Diesel piston with connecting rod (pistone con biella), as removed from a small
inline-4: cast-aluminium piston with re-entrant combustion bowl and valve reliefs in
the sooty crown, two compression rings and an oil-control ring in their grooves (ring
gaps visible), graphite-coated thrust skirt, recessed pin bosses with hollow gudgeon
pin and circlips; forged steel I-beam rod with bronze small-end bush, split big end
(cap parting line), bearing shells and two cap bolts.

Pin axis along Y at the origin, crown up (+Z), rod in the XZ plane. 1 unit = 100 mm."""
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
R = 0.38          # piston radius
ZC = 0.46         # crown height above pin axis
ZS = -0.24        # skirt bottom
LR = 1.30         # rod centre distance
ZB = -LR


def mat_piston():
    m = cast_alu("PistonAlu", base=0.56, rough=0.36, grime=0.35, grain=260.0, wear=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = next(l for l in nt.links if l.to_node == b and l.to_socket.name == "Base Color")
    src = lk.from_socket
    nt.links.remove(lk)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt), sep.inputs[0])

    def node(op, a=None, bv=None, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, bv)):
            if v is None:
                continue
            if isinstance(v, float):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    # graphite skirt: |x| large and z below the oil ring
    ax = node("ABSOLUTE", sep.outputs["X"])
    gx = node("MULTIPLY", node("SUBTRACT", ax, 0.17), 9.0, clamp=True)
    gz = node("MULTIPLY", node("SUBTRACT", 0.15, sep.outputs["Z"]), 18.0, clamp=True)
    gb = node("MULTIPLY", node("SUBTRACT", sep.outputs["Z"], ZS + 0.03), 18.0, clamp=True)
    g = node("MULTIPLY", node("MULTIPLY", gx, gz), gb)
    # soot: crown and bowl
    sz = node("MULTIPLY", node("SUBTRACT", sep.outputs["Z"], ZC - 0.17), 14.0, clamp=True)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 9.0
    nz.inputs["Detail"].default_value = 6.0
    sn = node("MULTIPLY", node("SUBTRACT", nz.outputs["Fac"], 0.25), 2.2, clamp=True)
    soot = node("MULTIPLY", sz, sn)
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    nt.links.new(g, mx.inputs["Factor"])
    nt.links.new(src, mx.inputs["A"])
    mx.inputs["B"].default_value = (0.07, 0.07, 0.072, 1)
    mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = "RGBA"
    nt.links.new(soot, mx2.inputs["Factor"])
    nt.links.new(mx.outputs["Result"], mx2.inputs["A"])
    mx2.inputs["B"].default_value = (0.035, 0.028, 0.022, 1)
    nt.links.new(mx2.outputs["Result"], b.inputs["Base Color"])
    met = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(node("MAXIMUM", g, soot), met.inputs["Value"])
    met.inputs["To Min"].default_value = 1.0
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    return m


def piston(alu, dark):
    out = []
    r = R
    P = [(0.0, ZC - 0.07, 0), (0.05, ZC - 0.075, 0), (0.11, ZC - 0.115, 0), (0.15, ZC - 0.15, 0), (0.19, ZC - 0.14, 0),
         (0.225, ZC - 0.10, 0), (0.232, ZC - 0.05, 0), (0.215, ZC - 0.018, 0), (0.225, ZC, 0),
         (r - 0.014, ZC, 0), (r, ZC - 0.014, 0), (r, 0.385, 0)]
    for (za, zb, dep) in ((0.385, 0.355, 0.04), (0.315, 0.29, 0.04), (0.245, 0.205, 0.045)):
        P += [(r - dep, za, 0), (r - dep, zb, 0), (r, zb, 0)]
        if zb > 0.25:
            P.append((r, zb - 0.035 if zb > 0.3 else zb - 0.045, 0))
    P += [(r, 0.10, 0), (r - 0.002, ZS + 0.04, 0), (r - 0.012, ZS, 0), (r - 0.05, ZS, 0), (r - 0.05, 0.12, 0),
          (r - 0.09, 0.22, 0), (0.0, 0.22, 0)]
    ob = C.lathe("Piston", P, [alu], steps=192)
    cb = bmesh.new()
    for s in (-1, 1):          # recessed pin-boss sides
        y0, y1 = sorted((s * 0.315, s * 0.6))
        box(cb, -0.6, 0.6, y0, y1, ZS - 0.1, 0.175)
    cut = C.mesh_obj("SideCut", cb, [alu])
    vb = bmesh.new()
    for (x, y) in ((0.17, 0.10), (0.17, -0.10)):   # valve reliefs
        cyl_axis(vb, 0.13, (x + 0.07, y, ZC - 0.012), (0, 0, 1), 0.0, 0.2, seg=48)
    vcut = C.mesh_obj("Reliefs", vb, [alu])
    boolean(ob, cut)
    boolean(ob, vcut)
    C.add_bevel(ob, 0.004, segments=1, angle=40)
    out.append(C.finalize(ob, angle=38, remove=[cut, vcut]))
    # pin bosses (inside the recess) + inner skirt walls on the pin sides
    def bosses(bm):
        for s in (-1, 1):
            a, b2 = sorted((s * 0.125, s * 0.33))
            cyl_axis(bm, 0.165, (0, a, 0), (0, 1, 0), 0.0, b2 - a, seg=48)
            y0, y1 = sorted((s * 0.255, s * 0.30))
            box(bm, -0.20, 0.20, y0, y1, ZS + 0.02, 0.17)
    hb = bmesh.new()
    cyl_axis(hb, 0.112, (0, -0.5, 0), (0, 1, 0), 0.0, 1.0, seg=48)
    hc = C.mesh_obj("PinBore", hb, [dark])
    tb = bmesh.new()
    cyl_axis(tb, 0.6, (0, 0, -0.5), (0, 0, 1), 0.0, 0.5 + ZS + 0.02, seg=32)   # trim walls below skirt
    tb_ = C.mesh_obj("Trim", tb, [alu])
    ws = solid("Bosses", bosses, [alu], bevel=0.012, cutters=[hc, tb_])
    out.append(ws)
    return out


def rings(ring_m):
    out = []
    for i, (za, zb, dep, gap) in enumerate(((0.383, 0.357, 0.04, 0.4), (0.313, 0.292, 0.04, 2.5), (0.243, 0.207, 0.045, 4.4))):
        P = [(R - dep + 0.004, za, 0), (R - 0.002, za, 0), (R - 0.002, zb, 0), (R - dep + 0.004, zb, 0)]
        ob = C.lathe("Ring", P, [ring_m], steps=192)
        cb = bmesh.new()
        box(cb, -0.006, 0.006, 0.2, 0.6, 0.1, 0.5, M=Matrix.Rotation(gap, 4, "Z"))
        cut = C.mesh_obj("Gap", cb, [ring_m])
        C.add_boolean(ob, cut)
        if i == 2:   # oil ring: slotted rail look
            ob2 = C.lathe("OilSlot", [(R - 0.003, 0.229, 0), (R + 0.0005, 0.229, 0), (R + 0.0005, 0.221, 0), (R - 0.003, 0.221, 0)],
                          [C.principled("Slot", (0.015, 0.015, 0.015), rough=0.7)], steps=192)
            out.append(C.finalize(ob2, angle=40))
        C.add_bevel(ob, 0.002, segments=1, angle=40)
        out.append(C.finalize(ob, angle=40, remove=[cut]))
    return out


def pin(pin_m, dark, clip_m):
    out = []
    P = [(0.065, -0.31, 0), (0.108, -0.31, 0), (0.111, -0.305, 0), (0.111, 0.305, 0), (0.108, 0.31, 0),
         (0.065, 0.31, 1), (0.065, -0.31, 1)]
    ob = C.lathe("Pin", P, [pin_m, dark], steps=64)
    ob.matrix_world = RXm
    out.append(C.finalize(ob, angle=40))
    for s in (-1, 1):
        P = [(0.095, 0.0, 0), (0.125, 0.0, 0), (0.125, 0.012, 0), (0.095, 0.012, 0)]
        out.append(lathe_at("Clip", P, clip_m, Matrix.Translation((0, s * 0.322, 0)) @ RXm, steps=48))
    return out


def rod(forged, bush, shell, bolt):
    out = []
    bm = bmesh.new()
    t_s, t_b = 0.11, 0.105             # half thickness small / big end
    cyl_axis(bm, 0.175, (0, -t_s, 0), (0, 1, 0), 0.0, 2 * t_s, seg=64)
    sec = [(-0.10, -0.12), (0.10, -0.12), (0.17, ZB + 0.30), (-0.17, ZB + 0.30)]
    prism_bm(bm, [(x, -z) for (x, z) in sec], -0.085, 0.085, RXm)
    cyl_axis(bm, 0.39, (0, -t_b, ZB), (0, 1, 0), 0.0, 2 * t_b, seg=96)
    box(bm, -0.45, 0.45, -t_b, t_b, ZB - 0.24, ZB + 0.20)
    ob = cast("Rod", bm, forged, voxel=0.008 if not FAST else 0.014, iters=4, fac=0.5)
    cuts = []

    def cutter(fill, mat):
        cb = bmesh.new()
        fill(cb)
        C.fix_normals(cb)
        c = C.mesh_obj("RodCut", cb, [mat])
        boolean(ob, c)
        cuts.append(c)
    cutter(lambda cb: cyl_axis(cb, 0.122, (0, -0.5, 0), (0, 1, 0), 0.0, 1.0, seg=64), bush)
    cutter(lambda cb: cyl_axis(cb, 0.245, (0, -0.5, ZB), (0, 1, 0), 0.0, 1.0, seg=96), shell)
    for s in (-1, 1):   # I-beam pockets
        pk = [(-0.055, -0.27), (0.055, -0.27), (0.10, ZB + 0.46), (-0.10, ZB + 0.46)]
        pk = [(x, -z * s) for (x, z) in pk]
        cutter(lambda cb, s=s, pk=pk: prism_bm(cb, pk, 0.0, 0.3, Matrix.Translation((0, s * 0.045, 0)) @ (RXm if s > 0 else RX)), forged)
    # cap parting line + bolt seats
    cutter(lambda cb: box(cb, -0.6, 0.6, -0.4, 0.4, ZB - 0.004, ZB + 0.004), shell)
    cutter(lambda cb: [box(cb, s * 0.31 - 0.11, s * 0.31 + 0.11, -0.4, 0.4, ZB - 0.6, ZB - 0.20) for s in (-1, 1)], forged)
    out.append(C.finalize(ob, angle=40, remove=cuts))
    # bearing shells and bush (thin visible rims)
    P = [(0.232, -0.098, 0), (0.246, -0.098, 0), (0.246, 0.098, 0), (0.232, 0.098, 0)]
    out.append(lathe_at("Shells", P, shell, Matrix.Translation((0, 0, ZB)) @ RXm, steps=96))
    P = [(0.111, -0.108, 0), (0.123, -0.108, 0), (0.123, 0.108, 0), (0.111, 0.108, 0)]
    out.append(lathe_at("Bush", P, bush, RXm, steps=64))
    # cap bolts from below
    for s in (-1, 1):
        M = Matrix.Translation((s * 0.31, 0, ZB - 0.20)) @ Matrix.Rotation(math.pi, 4, "X")
        out.append(lathe_at("BoltWasher", [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.085, 0.012, 0), (0.0, 0.012, 0)], bolt, M, steps=32))
        out.append(hex_at("BoltHead", 0.07, 0.012, 0.10, bolt, M, bevel=0.008))
        out.append(hex_at("BoltHead2", 0.07, 0.012, 0.10, bolt, M @ Matrix.Rotation(math.pi / 6, 4, "Z"), bevel=0.008))
    return out


def build():
    alu = mat_piston()
    dark = C.principled("Dark", (0.02, 0.02, 0.02), metallic=0.5, rough=0.6)
    ring_m = C.principled("RingSteel", (0.12, 0.12, 0.13), metallic=1.0, rough=0.3)
    C.add_noise_bump(ring_m, scale=800, strength=0.03, distance=0.0003)
    pin_m = C.mat_machined("PinSteel", color=0.62, rough=0.10, rings=0.0)
    clip_m = C.principled("ClipSteel", (0.25, 0.25, 0.26), metallic=1.0, rough=0.3)
    forged = mat_rusty_iron("RodSteel", base=0.085, rust=0.10, scale=6.0, seed=3.1)
    bush = C.principled("Bronze", (0.62, 0.42, 0.22), metallic=1.0, rough=0.3)
    shell = C.principled("BearingShell", (0.55, 0.55, 0.53), metallic=1.0, rough=0.35)
    C.add_noise_bump(shell, scale=600, strength=0.03, distance=0.0004)
    bolt = C.principled("BoltSteel", (0.22, 0.22, 0.23), metallic=1.0, rough=0.35)
    C.add_noise_bump(bolt, scale=500, strength=0.04, distance=0.0005)
    objs = piston(alu, dark) + rings(ring_m) + pin(pin_m, dark, clip_m) + rod(forged, bush, shell, bolt)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("pistone", objs,
         "diesel piston with connecting rod: aluminium piston with combustion bowl, piston rings, gudgeon pin, forged I-beam rod with split big-end cap and bolts",
         az=34, el=26, lens=70, fill=0.88)
