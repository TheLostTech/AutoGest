"""Clutch slave cylinder (cilindro frizione / cilindretto secondario, external type):
cast-aluminium cylinder body with casting ribs and a two-ear mounting flange for the
gearbox bellhousing, black rubber dust boot at the front with the steel pushrod and its
rounded tip, the bleed nipple with a red rubber dust cap on top at the back, and the
hydraulic line connection (union boss, flare nut, short steel pipe and rubber hose
section with crimped end) entering from the rear.

Cylinder axis along +X (pushrod at +X); units ~ decimetres (~20 cm overall)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # lathe Z -> world +X
RYn = Matrix.Rotation(math.radians(-90), 4, "Y")    # lathe Z -> world -X
RB = 0.19           # body radius
XF = 0.95           # pushrod end of the body


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M, steps=96, bevel=None, angle=40, mod=None, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def hexp(name, r, z0, z1, mat, M, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    return fin(C.mesh_obj(name, bm, [mat]), bevel=bevel)


def axis_matrix(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def frames_along(pts, sec):
    out = []
    n = len(pts)
    prevU = None
    for i, P in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prevU is None:
            U = T.cross(Vector((0, 0, 1)))
            if U.length < 1e-4:
                U = T.cross(Vector((1, 0, 0)))
        else:
            U = prevU - T * prevU.dot(T)
        U.normalize()
        V = T.cross(U).normalized()
        prevU = U
        out.append((P, U, V, sec))
    return out


def bezier(p0, p1, p2, p3, n):
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / n for i in range(n + 1))]


def thread_mat(name, color, rough=0.3, scale=40.0):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = scale
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.008
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_cast_alu(name, base=0.46, rough=0.44):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 8.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.05
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 1.0
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.05, base * 1.03, 1)
    mix1.inputs["B"].default_value = (base * 0.82, base * 0.81, base * 0.77, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.13, 0.12, 0.10, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 600.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.14
    bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def body(alu, steel, rubber, brass, red, pipe_m, hose_m):
    out = []
    P = [(0.0, 0.0, 0), (0.10, 0.0, 0), (0.13, 0.02, 0), (RB - 0.01, 0.06, 0), (RB, 0.10, 0), (RB, XF - 0.12, 0),
         (RB + 0.02, XF - 0.10, 0), (RB + 0.02, XF - 0.02, 0), (RB, XF, 0), (0.0, XF, 0)]
    out.append(lathe_at("Body", P, [alu], RY, steps=96, bevel=0.008))
    bm = bmesh.new()
    for a in (math.radians(-90), math.radians(-35), math.radians(-145), math.radians(90)):
        M = Matrix.Rotation(a, 4, "X") @ Matrix.Translation((0.48, 0, RB - 0.012))
        C.box_bm(bm, 0.58, 0.035, 0.05, matrix=M)
    out.append(fin(C.mesh_obj("Ribs", bm, [alu]), bevel=0.012))
    # mounting flange: two ears with bolt holes, plate perpendicular to the axis
    xm = 0.62
    bm = bmesh.new()
    n = 48
    sec = []
    for i in range(n):
        t = math.tau * i / n
        c, s = math.cos(t), math.sin(t)
        y = 0.46 * math.copysign(abs(c) ** 0.55, c)
        z = 0.15 * s + 0.0
        sec.append((y, z))
    C.sweep(bm, [(Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec) for x in (xm, xm + 0.09)])
    C.fix_normals(bm)
    fl = C.mesh_obj("Flange", bm, [alu])
    cb = bmesh.new()
    for sy in (-1, 1):
        C.cyl_bm(cb, 0.055, -0.3, 0.3, seg=32, matrix=Matrix.Translation((xm, sy * 0.33, 0)) @ RY)
    out.append(fin(fl, bevel=0.014, cutters=[C.mesh_obj("FlHoles", cb, [])]))
    # gussets from the flange ears back onto the body
    bm = bmesh.new()
    for sy in (-1, 1):
        M = Matrix.Translation((xm - 0.10, sy * 0.20, 0)) @ Matrix.Rotation(sy * math.radians(-28), 4, "Z")
        C.box_bm(bm, 0.24, 0.04, 0.10, matrix=M)
    out.append(fin(C.mesh_obj("Gussets", bm, [alu]), bevel=0.012))
    # steel sleeves in the ear holes
    for sy in (-1, 1):
        out.append(lathe_at("Sleeve", [(0.040, -0.01, 0), (0.056, -0.01, 0), (0.056, 0.10, 0), (0.040, 0.10, 0)], [steel],
                            Matrix.Translation((xm, sy * 0.33, 0)) @ RY, steps=32))
    # bleed nipple boss on top at the back + nipple + red dust cap
    xb = 0.18
    Mb = Matrix.Translation((xb, 0, 0)) @ Matrix.Rotation(math.radians(-12), 4, "Y")
    out.append(lathe_at("BleedBoss", [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.09, RB + 0.06, 0), (0.08, RB + 0.07, 0), (0.0, RB + 0.07, 0)],
                        [alu], Mb, steps=48, bevel=0.006))
    out.append(hexp("BleedHex", 0.055, RB + 0.07, RB + 0.13, brass, Mb, bevel=0.006))
    out.append(lathe_at("BleedTip", [(0.0, RB + 0.13, 0), (0.032, RB + 0.13, 0), (0.032, RB + 0.17, 0), (0.0, RB + 0.17, 0)],
                        [brass], Mb, steps=24))
    out.append(lathe_at("BleedCap", [(0.0, RB + 0.15, 0), (0.048, RB + 0.15, 0), (0.05, RB + 0.17, 0), (0.05, RB + 0.24, 0),
                                     (0.04, RB + 0.255, 0), (0.0, RB + 0.255, 0)], [red], Mb, steps=40, angle=50))
    # line connection at the rear end: union boss, flare nut, pipe, hose
    Mu = Matrix.Translation((0.06, 0, -0.02)) @ Matrix.Rotation(math.radians(180 + 30), 4, "Y")
    out.append(lathe_at("UnionBoss", [(0.0, -0.06, 0), (0.085, -0.06, 0), (0.085, 0.06, 0), (0.0, 0.06, 0)], [alu], Mu, steps=48,
                        bevel=0.006))
    out.append(hexp("FlareNut", 0.072, 0.06, 0.15, steel, Mu, bevel=0.008))
    p0 = Mu @ Vector((0, 0, 0.15))
    d = (Mu.to_3x3() @ Vector((0, 0, 1))).normalized()
    pts = bezier(p0, p0 + d * 0.25, p0 + Vector((-0.40, 0.10, -0.05)), p0 + Vector((-0.55, 0.32, -0.02)), 30)
    sec = [(0.028 * math.cos(math.tau * j / 16), 0.028 * math.sin(math.tau * j / 16)) for j in range(16)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec))
    out.append(fin(C.mesh_obj("Pipe", bm, [pipe_m]), angle=60))
    T = (pts[-1] - pts[-2]).normalized()
    Mh = axis_matrix(pts[-1], T)
    out.append(lathe_at("Crimp", [(0.0, -0.02, 0), (0.06, -0.02, 0), (0.062, 0.0, 0), (0.062, 0.14, 0), (0.05, 0.16, 0), (0.0, 0.16, 0)],
                        [steel], Mh, steps=40, bevel=0.004))
    q0 = Mh @ Vector((0, 0, 0.15))
    pts2 = bezier(q0, q0 + T * 0.3, q0 + Vector((-0.2, 0.45, 0.0)), q0 + Vector((-0.05, 0.75, -0.02)), 30)
    sec = [(0.05 * math.cos(math.tau * j / 20), 0.05 * math.sin(math.tau * j / 20)) for j in range(20)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts2, sec))
    out.append(fin(C.mesh_obj("Hose", bm, [hose_m]), angle=60))
    return out


def pushrod(rubber, rod_m, tip_m):
    out = []
    P = [(0.0, XF - 0.05, 0), (RB + 0.01, XF - 0.05, 0), (RB + 0.02, XF + 0.03, 0), (0.15, XF + 0.08, 0), (0.17, XF + 0.12, 0),
         (0.12, XF + 0.17, 0), (0.14, XF + 0.21, 0), (0.09, XF + 0.27, 0), (0.07, XF + 0.31, 0), (0.0, XF + 0.31, 0)]
    out.append(lathe_at("Boot", P, [rubber], RY, steps=96, angle=50))
    out.append(lathe_at("Rod", [(0.0, XF + 0.25, 0), (0.045, XF + 0.25, 0), (0.045, XF + 0.78, 0), (0.0, XF + 0.78, 0)], [rod_m], RY, steps=32))
    # rounded tip that pushes the release fork
    P = [(0.0, XF + 0.74, 0), (0.06, XF + 0.74, 0), (0.065, XF + 0.78, 0)]
    for i in range(1, 9):
        a = math.pi / 2 * i / 8
        P.append((0.065 * math.cos(a), XF + 0.80 + 0.065 * math.sin(a), 0))
    out.append(lathe_at("Tip", P, [tip_m], RY, steps=40))
    # retaining collar on the rod
    out.append(lathe_at("Collar", [(0.045, XF + 0.50, 0), (0.07, XF + 0.50, 0), (0.07, XF + 0.54, 0), (0.045, XF + 0.54, 0)],
                        [tip_m], RY, steps=40))
    return out


def build():
    alu = mat_cast_alu("SlaveAlu", base=0.44, rough=0.46)
    steel = C.principled("Zinc", (0.64, 0.64, 0.60), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    rubber = C.mat_rubber("BootRubber")
    brass = C.principled("BleedBrass", (0.62, 0.50, 0.30), metallic=1.0, rough=0.3)
    red = C.principled("CapRed", (0.42, 0.03, 0.03), rough=0.55)
    C.add_noise_bump(red, scale=400, strength=0.06, distance=0.0008)
    pipe_m = C.principled("PipeSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    hose_m = C.principled("HoseRubber", (0.025, 0.025, 0.026), rough=0.5)
    C.add_noise_bump(hose_m, scale=300, strength=0.06, distance=0.0008)
    rod_m = C.principled("RodSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.30)
    C.add_noise_bump(rod_m, scale=600, strength=0.04, distance=0.0005, rough_var=0.06)
    tip_m = C.principled("TipSteel", (0.62, 0.62, 0.63), metallic=1.0, rough=0.18)
    objs = body(alu, steel, rubber, brass, red, pipe_m, hose_m) + pushrod(rubber, rod_m, tip_m)
    C.transform_all(objs, Matrix.Rotation(math.radians(-30), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("cilindro-frizione", objs, "cilindro-frizione.py",
            "external clutch slave cylinder: cast-aluminium body with two-ear mounting flange, rubber boot and "
            "pushrod with rounded tip, bleed nipple with red dust cap, flare-nut line connection with hose",
            az=30, el=26, lens=70, fill=0.86, **kw)
