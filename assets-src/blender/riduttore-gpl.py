"""LPG vaporiser / pressure reducer: round two-part sand-cast aluminium body (coolant
chamber base and diaphragm cover) with screw lobes and eight socket screws, central
boss with the brass adjustment screw and lock nut, two bent aluminium coolant spigots,
a larger gas outlet spigot, a gas inlet block with a brass union and an upright black
shut-off solenoid with its lead and 2-pin connector, a small temperature sensor, and a
zinc-plated mounting bracket.

1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
RB = 0.66           # body radius
ZS = 0.46           # split line between base and cover
NL = 8              # screw lobes


# ----------------------------------------------------------------- helpers
def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), M=I4):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    ob.matrix_world = M
    for c in cutters:
        c.matrix_world = M
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None, mod=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=3, caps=True):
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


def axis_frame(P, d):
    d = Vector(d).normalized()
    x = d.orthogonal().normalized()
    y = d.cross(x)
    return Matrix(((x.x, y.x, d.x, P[0]), (x.y, y.y, d.y, P[1]), (x.z, y.z, d.z, P[2]), (0, 0, 0, 1)))


def barb(r, length):
    P = [(0.0, 0.0, 0), (r, 0.0, 0)]
    z = 0.04
    while z < length - 0.08:
        P += [(r, z, 0), (r * 1.18, z + 0.05, 0), (r, z + 0.055, 0)]
        z += 0.085
    P += [(r, length - 0.015, 0), (r * 0.85, length, 0), (r * 0.6, length, 1), (r * 0.6, length - 0.02, 1), (0.0, length - 0.02, 1)]
    return P


# ----------------------------------------------------------------- materials
def mat_cast_alu(name, base=0.50, rough=0.48, grain=140.0, wear=0.35):
    """Sand-cast aluminium: mottled, coarse cast grain, slightly brighter worn edges,
    faint coolant stains."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 5.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.80, base * 0.79, base * 0.74, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.78, 0.78, 0.78, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.08
    rr.inputs["To Max"].default_value = rough - 0.08
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def lobes(r, z, t, z0, z1, amp=0.075, width=0.16):
    if z0 <= z <= z1 and r > 0.3:
        best = 0.0
        for k in range(NL):
            a = TAU * (k + 0.5) / NL
            d = math.atan2(math.sin(t - a), math.cos(t - a))
            best = max(best, math.exp(-(d / width) ** 2))
        return r + amp * best
    return r


def body(alu, alu2, steel, brass):
    out = []
    # base (coolant chamber): foot, slight waist, flange at the split line with screw lobes
    P = [(0.0, 0.0, 0), (RB - 0.10, 0.0, 0), (RB - 0.06, 0.03, 0), (RB - 0.04, 0.10, 0), (RB - 0.05, 0.25, 0),
         (RB - 0.02, 0.36, 0), (RB, 0.38, 0), (RB, ZS, 0), (0.0, ZS, 0)]
    out.append(lathe_at("Base", P, alu, steps=192, bevel=0.01, mod=lambda r, z, t: lobes(r, z, t, 0.37, ZS + 0.01)))
    # cast ribs on the base side between the lobes
    bm = bmesh.new()
    for k in range(NL):
        a = TAU * k / NL
        C.box_bm(bm, 0.07, 0.035, 0.26, center=(0, 0, 0), matrix=Matrix.Rotation(a, 4, "Z") @ T((RB - 0.03, 0, 0.21)))
    rb = C.mesh_obj("Ribs", bm, [alu])
    C.add_bevel(rb, 0.012, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # cover: flange with lobes, dome, central boss
    P = [(0.0, ZS, 0), (RB, ZS, 0), (RB, ZS + 0.08, 0), (RB - 0.06, ZS + 0.10, 0), (RB - 0.14, ZS + 0.17, 0), (0.42, ZS + 0.22, 0),
         (0.20, ZS + 0.25, 0), (0.16, ZS + 0.26, 0), (0.15, ZS + 0.36, 0), (0.13, ZS + 0.38, 0), (0.0, ZS + 0.38, 0)]
    out.append(lathe_at("Cover", P, alu2, steps=192, bevel=0.01, mod=lambda r, z, t: lobes(r, z, t, ZS - 0.01, ZS + 0.085)))
    # thin dark gasket line at the split
    out.append(lathe_at("Gasket", [(RB - 0.02, ZS - 0.008, 0), (RB + 0.004, ZS - 0.008, 0), (RB + 0.004, ZS + 0.008, 0), (RB - 0.02, ZS + 0.008, 0)],
                        C.principled("Gasket", (0.03, 0.03, 0.03), rough=0.7), steps=192,
                        mod=lambda r, z, t: lobes(r, z, t, ZS - 0.02, ZS + 0.02)))
    # socket-head screws in the lobes
    for k in range(NL):
        a = TAU * (k + 0.5) / NL
        x, y = (RB + 0.02) * math.cos(a), (RB + 0.02) * math.sin(a)
        hd = C.lathe("Screw", [(0.0, ZS + 0.08, 0), (0.045, ZS + 0.08, 0), (0.045, ZS + 0.125, 0), (0.04, ZS + 0.13, 0), (0.0, ZS + 0.13, 0)],
                     [steel], steps=32)
        hd.matrix_world = T((x, y, 0))
        bm = bmesh.new()
        C.cyl_bm(bm, 0.02, ZS + 0.10, ZS + 0.2, seg=6, matrix=T((x, y, 0)))
        cut = C.mesh_obj("ScrewCut", bm, [steel])
        C.add_boolean(hd, cut)
        C.add_bevel(hd, 0.004, segments=1, angle=40)
        out.append(C.finalize(hd, angle=40, remove=[cut]))
    # adjustment screw with lock nut in the central boss
    out.append(hex_at("LockNut", 0.085, ZS + 0.38, ZS + 0.44, steel, bevel=0.008))
    P = [(0.0, ZS + 0.43, 0), (0.05, ZS + 0.43, 0), (0.05, ZS + 0.52, 0), (0.044, ZS + 0.53, 0), (0.0, ZS + 0.53, 0)]
    sc = C.lathe("AdjScrew", P, [brass], steps=32)
    bm = bmesh.new()
    C.box_bm(bm, 0.14, 0.018, 0.05, center=(0, 0, ZS + 0.53))
    cut = C.mesh_obj("Slot", bm, [brass])
    C.add_boolean(sc, cut)
    C.add_bevel(sc, 0.004, segments=1, angle=40)
    out.append(C.finalize(sc, angle=40, remove=[cut]))
    return out


def spigots(alu, brass, black, dark):
    out = []
    # two coolant spigots out of the base, bending down and out (front-left)
    for (a, name) in ((math.radians(205), "CoolIn"), (math.radians(240), "CoolOut")):
        d = Vector((math.cos(a), math.sin(a), 0))
        p0 = d * (RB - 0.08) + Vector((0, 0, 0.22))
        out.append(lathe_at(name + "Boss", [(0.0, 0.0, 0), (0.10, 0.0, 0), (0.10, 0.10, 0), (0.085, 0.12, 0), (0.0, 0.12, 0)],
                            alu, axis_frame(p0, d), steps=40, bevel=0.01))
        p1 = p0 + d * 0.12
        pts = [p1, p1 + d * 0.12, p1 + d * 0.22 + Vector((0, 0, -0.04)), p1 + d * 0.26 + Vector((0, 0, -0.16))]
        out.append(tube(name, pts, 0.062, alu, res=4))
        e = Vector(pts[-1])
        dd = (e - Vector(pts[-2])).normalized()
        out.append(lathe_at(name + "Barb", barb(0.062, 0.26), alu, axis_frame(e - dd * 0.01, dd), steps=40, mats=[alu, dark]))
    # gas outlet spigot from the cover side (right), horizontal, larger
    a = math.radians(-20)
    d = Vector((math.cos(a), math.sin(a), 0))
    p0 = d * (RB - 0.12) + Vector((0, 0, ZS + 0.13))
    out.append(lathe_at("OutBoss", [(0.0, 0.0, 0), (0.13, 0.0, 0), (0.13, 0.14, 0), (0.11, 0.16, 0), (0.0, 0.16, 0)],
                        alu, axis_frame(p0, d), steps=48, bevel=0.012))
    out.append(lathe_at("GasOut", barb(0.07, 0.30), brass, axis_frame(p0 + d * 0.15, d), steps=48, mats=[brass, dark]))
    return out


def inlet(alu, brass, black, rubber, tin, dark):
    """Inlet block on the back-right with the solenoid coil standing up and a brass union."""
    out = []
    a = math.radians(60)
    d = Vector((math.cos(a), math.sin(a), 0))
    t = Vector((-d.y, d.x, 0))
    c = d * (RB + 0.10) + Vector((0, 0, 0.22))
    M = Matrix(((d.x, t.x, 0, c.x), (d.y, t.y, 0, c.y), (0, 0, 1, c.z), (0, 0, 0, 1)))

    def blk(bm):
        C.box_bm(bm, 0.34, 0.34, 0.30, center=(0.0, 0.0, 0.0))
        C.box_bm(bm, 0.16, 0.22, 0.20, center=(-0.18, 0.0, 0.0))
    out.append(solid("InletBlock", blk, [alu], bevel=0.03, M=M))
    # solenoid: stem, coil, top nut
    Ms = M @ T((0.02, 0.0, 0.15))
    out.append(lathe_at("Stem", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.50, 0), (0.0, 0.50, 0)], brass, Ms, steps=32))
    out.append(lathe_at("Coil", [(0.0, 0.02, 0), (0.165, 0.02, 0), (0.175, 0.04, 0), (0.175, 0.38, 0), (0.165, 0.40, 0), (0.0, 0.40, 0)],
                        black, Ms, steps=64, bevel=0.008))
    out.append(hex_at("CoilNut", 0.09, 0.40, 0.48, brass, Ms, bevel=0.006))
    # coil connector socket on the coil side + lead to a small 2-pin plug
    def con(bm):
        C.box_bm(bm, 0.12, 0.16, 0.16, center=(0.0, -0.23, 0.22))
    def cav(bm):
        C.box_bm(bm, 0.08, 0.12, 0.12, center=(0.0, -0.30, 0.22))
    out.append(solid("CoilSocket", con, [black], bevel=0.012, cutters=[cutter("CoilCav", cav, dark)], M=Ms))
    p0 = Ms @ Vector((0.0, -0.31, 0.22))
    pts = [p0, Ms @ Vector((0.0, -0.45, 0.20)), Ms @ Vector((0.10, -0.62, 0.02)), Ms @ Vector((0.28, -0.72, -0.30))]
    out.append(tube("Lead", pts, 0.028, black, res=3))
    e = Vector(pts[-1])
    dd = (e - Vector(pts[-2])).normalized()
    Mp = axis_frame(e, dd)
    def plug(bm):
        prism_bm(bm, rrect(0.16, 0.12, 0.025), 0.0, 0.22)
    out.append(solid("Plug", plug, [black], bevel=0.012, M=Mp))
    # brass inlet union with nut on the outer face of the block (pipe from the tank)
    Mu = M @ T((0.17, 0.0, -0.02)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(hex_at("UnionHex", 0.085, 0.0, 0.08, brass, Mu, bevel=0.006))
    out.append(lathe_at("UnionStem", [(0.0, 0.08, 0), (0.05, 0.08, 0), (0.05, 0.18, 0), (0.0, 0.18, 0)], brass, Mu, steps=32))
    out.append(hex_at("UnionNut", 0.07, 0.12, 0.20, brass, Mu, bevel=0.006))
    # small coolant-temperature sensor on the base (front)
    a = math.radians(300)
    d2 = Vector((math.cos(a), math.sin(a), 0))
    Mt = axis_frame(d2 * (RB - 0.04) + Vector((0, 0, 0.20)), d2)
    out.append(hex_at("TempHex", 0.06, 0.0, 0.05, brass, Mt, bevel=0.005))
    out.append(lathe_at("TempBody", [(0.0, 0.05, 0), (0.05, 0.05, 0), (0.05, 0.12, 0), (0.06, 0.14, 0), (0.06, 0.22, 0), (0.0, 0.22, 0)],
                        black, Mt, steps=32, bevel=0.006))
    return out


def bracket(zinc, steel):
    """Zinc-plated L bracket bolted under the base, upright leg with slots at the back."""
    out = []
    a = math.radians(140)
    d = Vector((math.cos(a), math.sin(a), 0))
    t = Vector((-d.y, d.x, 0))
    M = Matrix(((d.x, t.x, 0, 0), (d.y, t.y, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

    def b(bm):
        C.box_bm(bm, 0.86, 0.40, 0.03, center=(0.30, 0.0, -0.015))
        C.box_bm(bm, 0.03, 0.40, 0.62, center=(RB + 0.10, 0.0, 0.28))

    def holes(bm):
        prism_bm(bm, rrect(0.24, 0.08, 0.04), -0.3, 0.3, M=T((RB + 0.10, -0.08, 0.40)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
        prism_bm(bm, rrect(0.24, 0.08, 0.04), -0.3, 0.3, M=T((RB + 0.10, 0.10, 0.40)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    out.append(solid("Bracket", b, [zinc], bevel=0.008, cutters=[cutter("BrHoles", holes, zinc)], M=M))
    return out


def build():
    alu = mat_cast_alu("BaseAlu", 0.46, 0.50)
    alu2 = mat_cast_alu("CoverAlu", 0.54, 0.42, grain=220.0)
    steel = C.principled("ScrewSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.35)
    brass = C.principled("Brass", (0.68, 0.53, 0.30), metallic=1.0, rough=0.30)
    C.add_noise_bump(brass, scale=500, strength=0.05, distance=0.0005, rough_var=0.08)
    black = C.mat_black_plastic("CoilPA", rough=0.42, color=0.022)
    rubber = C.mat_rubber()
    tin = C.principled("Tin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.2)
    zinc = C.principled("Zinc", (0.62, 0.60, 0.52), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=400, strength=0.05, distance=0.0006, rough_var=0.08)
    dark = C.principled("Bore", (0.01, 0.01, 0.01), rough=0.8)
    objs = body(alu, alu2, steel, brass) + spigots(alu, brass, black, dark) + inlet(alu, brass, black, rubber, tin, dark)
    objs += bracket(zinc, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("riduttore-gpl", objs, "riduttore-gpl.py",
            "LPG vaporiser / pressure reducer: round cast aluminium body with screwed cover and adjustment screw, two coolant "
            "spigots, gas outlet spigot, inlet block with black shut-off solenoid and brass union, mounting bracket",
            az=30, el=34, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
