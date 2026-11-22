"""Engine oil pump (pompa olio), chain-driven gerotor type that bolts under the crankcase:
cast-aluminium pump housing with mounting lugs, machined outlet flange with port and
two bolt holes, pressure-relief valve boss with plug, bolted machined cover with six
screws, drive shaft with roller-chain sprocket and nut; steel pickup tube bolted to the
housing by a two-bolt flange, bending down into a pressed-steel strainer with a
perforated screen.

Pump axis along Z, outlet +X, pickup -X. 1 unit = 100 mm."""
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


def mat_perforated(name):
    m = C.principled(name, (0.36, 0.36, 0.35), metallic=1.0, rough=0.38)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 26.0
    vo.inputs["Randomness"].default_value = 0.0
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.24
    mr.inputs["From Max"].default_value = 0.30
    nt.links.new(vo.outputs["Distance"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.005, 0.005, 0.005, 1)
    mix.inputs["B"].default_value = (0.36, 0.36, 0.35, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(mr.outputs["Result"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


LUGS = ((0.15, 0.80), (-0.25, -0.80))


def housing(alu, face_m, dark):
    bm = bmesh.new()
    cyl_axis(bm, 0.56, (0, 0, -0.22), (0, 0, 1), 0.0, 0.32, seg=96)            # rotor chamber
    box(bm, 0.25, 0.86, -0.24, 0.24, -0.20, 0.08)                              # outlet arm
    box(bm, -0.80, -0.30, -0.17, 0.17, -0.16, 0.06)                            # pickup boss
    cyl_axis(bm, 0.13, (0.10, -0.42, -0.06), (1, 0, 0), -0.25, 0.62, seg=40)  # relief valve bore boss
    for (x, y) in LUGS:
        cyl_axis(bm, 0.13, (x, y, -0.06), (0, 0, 1), 0.0, 0.16, seg=40)
        box(bm, min(0, x) - 0.1, max(0, x) + 0.1, min(0, y), max(0, y), -0.06, 0.08)
    for k in range(6):                                                         # cover screw bosses
        t = math.tau * k / 6 + 0.2
        cyl_axis(bm, 0.09, (0.52 * math.cos(t), 0.52 * math.sin(t), -0.2), (0, 0, 1), 0.0, 0.3, seg=24)
    ob = cast("PumpBody", bm, alu, voxel=0.008 if not FAST else 0.014, iters=4, fac=0.5)
    cuts = []

    def cutter(fill, mat):
        cb = bmesh.new()
        fill(cb)
        C.fix_normals(cb)
        c = C.mesh_obj("PCut", cb, [mat])
        boolean(ob, c)
        cuts.append(c)
    cutter(lambda cb: box(cb, -2, 2, -2, 2, 0.085, 1.0), face_m)                # faced top (cover seat)
    cutter(lambda cb: box(cb, 0.84, 1.5, -0.5, 0.5, -0.5, 0.5), face_m)         # outlet flange face
    cutter(lambda cb: box(cb, -1.5, -0.78, -0.5, 0.5, -0.5, 0.5), face_m)       # pickup flange face
    cutter(lambda cb: [cyl_axis(cb, 0.11, (0.6, 0, -0.06), (1, 0, 0), 0.0, 0.5, seg=32),
                       cyl_axis(cb, 0.035, (0.6, 0.175, -0.06), (1, 0, 0), 0.0, 0.5, seg=16),
                       cyl_axis(cb, 0.035, (0.6, -0.175, -0.06), (1, 0, 0), 0.0, 0.5, seg=16)], dark)
    cutter(lambda cb: [cyl_axis(cb, 0.055, (x, y, -0.5), (0, 0, 1), 0.0, 1.0, seg=20) for (x, y) in LUGS], dark)
    return [C.finalize(ob, angle=40, remove=cuts)]


def cover(face_m, steel, sprocket_m, dark):
    out = []
    P = [(0.0, 0.085, 0), (0.60, 0.085, 0), (0.60, 0.14, 0), (0.585, 0.155, 0), (0.0, 0.155, 0)]
    cv = C.lathe("Cover", P, [face_m], steps=128)
    for k in range(6):
        pass
    C.add_bevel(cv, 0.004, segments=1, angle=40)
    out.append(C.finalize(cv, angle=40))
    for k in range(6):
        t = math.tau * k / 6 + 0.2
        T = Matrix.Translation((0.52 * math.cos(t), 0.52 * math.sin(t), 0.155))
        out.append(lathe_at("Screw", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.03, 0), (0.05, 0.055, 0), (0.0, 0.058, 0)], steel, T, steps=32))
        def slot(bm, T=T, t=t):
            C.box_bm(bm, 0.11, 0.016, 0.04, center=(0, 0, 0.055), matrix=T @ Matrix.Rotation(t + 0.6, 4, "Z"))
        out.append(solid("ScrewSlot", slot, [dark]))
    # shaft, sprocket and nut
    out.append(lathe_at("Shaft", [(0.0, 0.15, 0), (0.12, 0.15, 0), (0.12, 0.30, 0), (0.0, 0.30, 0)], steel, steps=48))
    n = 28
    sec = []
    rp, rr = 0.42, 0.026            # pitch radius, roller radius
    for k in range(n):
        for j in range(20):
            u = j / 20
            t = math.tau * (k + u) / n
            d = (u - 0.5) / 0.28
            if abs(d) < 1.0:
                r = rp - rr * math.sqrt(1 - d * d)
            else:
                f = min(1.0, (abs(u - 0.5) - 0.28) / 0.22)
                r = rp + 0.032 * math.sin(f * math.pi / 2)
            sec.append((r * math.cos(t), r * math.sin(t)))
    def spr(bm):
        prism_bm(bm, sec, 0.30, 0.37)
    hb = bmesh.new()
    for k in range(4):
        t = math.tau * k / 4 + 0.4
        cyl_axis(hb, 0.075, (0.25 * math.cos(t), 0.25 * math.sin(t), 0.2), (0, 0, 1), 0.0, 0.3, seg=32)
    hc = C.mesh_obj("SprHoles", hb, [sprocket_m])
    out.append(solid("Sprocket", spr, [sprocket_m], bevel=0.006, angle=40, cutters=[hc]))
    out.append(lathe_at("Hub", [(0.0, 0.29, 0), (0.17, 0.29, 0), (0.17, 0.40, 0), (0.0, 0.40, 0)], sprocket_m, steps=48, bevel=0.006))
    out.append(hex_at("Nut", 0.11, 0.40, 0.47, steel, bevel=0.01))
    out.append(lathe_at("ShaftEnd", [(0.0, 0.47, 0), (0.06, 0.47, 0), (0.05, 0.50, 0), (0.0, 0.50, 0)], steel, steps=24))
    # relief valve plug (on -X end of the bore boss) + snap ring look
    M = Matrix.Translation((-0.15, -0.42, -0.06)) @ RYm
    out.append(lathe_at("ReliefPlug", [(0.0, 0.0, 0), (0.10, 0.0, 0), (0.10, 0.04, 0), (0.0, 0.05, 0)], steel, M, steps=40))
    return out


def pickup(steel, screen, frame_m, bolt):
    out = []
    # flange plate on the pickup boss face (-X)
    def fl(bm):
        prism_bm(bm, rrect(0.42, 0.20, 0.08, 6), -0.86, -0.80, RY)
    hb = bmesh.new()
    for z in (-0.05 + 0.13, -0.05 - 0.13):
        pass
    out.append(solid("PickFlange", lambda bm: box(bm, -0.86, -0.80, -0.21, 0.21, -0.13, 0.03), [frame_m], bevel=0.015))
    for y in (-0.15, 0.15):
        M = Matrix.Translation((-0.86, y, -0.05)) @ RYm
        out.append(hex_at("PFBolt", 0.05, 0.0, 0.06, bolt, M, bevel=0.006))
    pts = [(-0.86, 0, -0.05), (-1.05, 0, -0.06), (-1.22, 0, -0.20), (-1.30, 0, -0.50), (-1.30, 0, -0.85)]
    out.append(tube("PickTube", pts, 0.075, steel))
    # strainer: pressed-steel frame with perforated screen top
    def pan(bm):
        prism_bm(bm, rrect(1.10, 0.85, 0.32, 8), -1.10, -0.97, Matrix.Translation((-1.30, 0, 0)))
        prism_bm(bm, rrect(1.18, 0.93, 0.36, 8), -1.12, -1.08, Matrix.Translation((-1.30, 0, 0)))
    out.append(solid("StrainerPan", pan, [frame_m], bevel=0.012, angle=40))
    sb = bmesh.new()
    prism_bm(sb, rrect(1.00, 0.75, 0.28, 8), -0.975, -0.955, Matrix.Translation((-1.30, 0, 0)))
    C.fix_normals(sb)
    out.append(C.mesh_obj("Screen", sb, [screen]))
    out.append(lathe_at("TubeCollar", [(0.0, -0.97, 0), (0.12, -0.97, 0), (0.12, -0.92, 0), (0.08, -0.86, 0), (0.0, -0.86, 0)],
                        frame_m, Matrix.Translation((-1.30, 0, 0)), steps=40))
    return out


def build():
    alu = cast_alu("PumpAlu", base=0.46, rough=0.48, grime=0.6, grain=200.0, wear=0.25)
    face = flat_machined("PumpFace", 0.50, 0.30, "Z", 12.0)
    dark = C.principled("Dark", (0.02, 0.02, 0.02), metallic=0.4, rough=0.6)
    steel = steel_body("ZincSteel", 0.50, 0.28)
    spr = C.principled("SprocketSteel", (0.20, 0.20, 0.21), metallic=1.0, rough=0.32)
    C.add_noise_bump(spr, scale=500, strength=0.04, distance=0.0005)
    tube_m = C.principled("TubeSteel", (0.12, 0.12, 0.125), metallic=0.6, rough=0.42)
    C.add_noise_bump(tube_m, scale=400, strength=0.05, distance=0.0005)
    screen = mat_perforated("Screen")
    frame_m = C.principled("PressedSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.36)
    C.add_noise_bump(frame_m, scale=300, strength=0.05, distance=0.0006)
    objs = housing(alu, face, dark) + cover(face, steel, spr, dark) + pickup(tube_m, screen, frame_m, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("pompa-olio", objs,
         "engine oil pump: cast-aluminium gerotor housing with bolted cover, chain sprocket on the drive shaft, outlet flange, pickup tube with strainer",
         az=32, el=30, lens=70, fill=0.86)
