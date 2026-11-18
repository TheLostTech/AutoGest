"""Front lower control arm (braccio oscillante / triangolo) as removed from a small car:
L-shaped pressed-steel arm in satin black paint with worn edges, stamped stiffening
recess and a lightening hole, front bush in a welded eye (axis along the car), large
vertical rear bush, riveted ball joint with rubber boot and grooved pinch-bolt stud."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

T = 0.30                         # section height (1 unit ~ 10 cm)
FB = Vector((0.0, 0.0, 0.0))     # front bush centre (axis X)
RB = Vector((-2.82, 0.78, 0.0))  # rear bush centre (axis Z)
BJ = Vector((0.26, 3.36, 0.0))   # ball joint centre

OUTLINE = [(0.32, 0.10), (0.42, 0.9), (0.46, 1.8), (0.56, 2.65), (0.74, 3.12), (0.70, 3.55),
           (0.40, 3.80), (0.02, 3.76), (-0.24, 3.48), (-0.40, 2.95), (-0.62, 2.35), (-1.05, 1.88),
           (-1.70, 1.55), (-2.35, 1.38), (-2.85, 1.30), (-3.22, 1.05), (-3.26, 0.55), (-2.95, 0.30),
           (-2.45, 0.40), (-1.75, 0.78), (-1.05, 0.86), (-0.52, 0.62), (-0.30, 0.25), (-0.26, 0.10)]


def catmull(pts, n=10):
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = (Vector(pts[(i + k) % m]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def offset(poly, d):
    """inward offset of a CCW polygon by d (vertex-normal miter, ok for gentle curves)"""
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        t = (c - a).normalized()
        nrm = Vector((-t.y, t.x))       # left normal = inward for CCW
        out.append(b + nrm * d)
    return out


def prism(bm, poly, z0, z1, mat=0):
    bot = [bm.verts.new((p.x, p.y, z0)) for p in poly]
    top = [bm.verts.new((p.x, p.y, z1)) for p in poly]
    fs = [bm.faces.new(top), bm.faces.new(bot[::-1])]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        fs.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in fs:
        f.material_index = mat
    return fs


def signed_area(poly):
    return 0.5 * sum(poly[i - 1].x * poly[i].y - poly[i].x * poly[i - 1].y for i in range(len(poly)))


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=64):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


# ----------------------------------------------------------------- materials
def mat_worn_black(name="ArmPaint"):
    m = C.mat_paint(name, (0.022, 0.022, 0.024, 1), rough=0.42, coat=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 14.0
    nz.inputs["Detail"].default_value = 10.0
    em = C.edge_mask(nt, 0.02, 5.0)
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.55
    th.inputs["From Max"].default_value = 0.62
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    nt.links.new(em, mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 1.3
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], th.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs["B"].default_value = (0.20, 0.19, 0.18, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.42
    ro.inputs["To Max"].default_value = 0.8
    nt.links.new(th.outputs["Result"], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # orange-peel
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 220.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def arm(paint):
    poly = catmull(OUTLINE, 10)
    if signed_area(poly) < 0:
        poly.reverse()
    bm = bmesh.new()
    prism(bm, poly, -T / 2, T / 2)
    ob = C.mesh_obj("Arm", bm, [paint])
    cb = bmesh.new()
    # stamped channel on top, leaving a raised flange all round
    inner = offset(poly, 0.12)
    for _ in range(60):          # curvature-flow smoothing rounds off narrow wedge tips
        inner = [(inner[i - 1] + inner[(i + 1) % len(inner)]) * 0.25 + inner[i] * 0.5 for i in range(len(inner))]
    prism(cb, inner, T / 2 - 0.085, T)
    cut = C.mesh_obj("Channel", cb, [paint])
    boolean(ob, cut)
    hb = bmesh.new()
    # lightening hole in the elbow, bush and ball-joint seats
    M = Matrix.Translation((-0.85, 1.35, 0)) @ Matrix.Rotation(math.radians(-25), 4, "Z") @ Matrix.Diagonal((1.5, 0.75, 1, 1))
    C.cyl_bm(hb, 0.22, -1, 1, seg=48, matrix=M)
    C.cyl_bm(hb, 0.27, -1, 1, seg=48, matrix=Matrix.Translation(BJ))
    C.cyl_bm(hb, 0.40, -1, 1, seg=48, matrix=Matrix.Translation(RB))
    holes = C.mesh_obj("Holes", hb, [paint])
    boolean(ob, holes)
    C.add_bevel(ob, 0.03, segments=3, angle=30)
    return C.finalize(ob, angle=35, remove=[cut, holes])


def front_bush(paint, rubber, steel):
    out = []
    P = [(0.22, -0.34, 0), (0.31, -0.34, 0), (0.31, 0.30, 0), (0.22, 0.30, 0)]
    eye = lathe_at("FrontEye", P, [paint], FB, (1, 0, 0), steps=64)
    C.add_bevel(eye, 0.015, segments=2, angle=30)
    out.append(C.finalize(eye, angle=35))
    P = [(0.115, -0.36, 0), (0.225, -0.36, 0), (0.225, 0.32, 0), (0.115, 0.32, 0)]
    out.append(C.finalize(lathe_at("FrontRubber", P, [rubber], FB, (1, 0, 0), steps=64), angle=40))
    P = [(0.075, -0.42, 0), (0.115, -0.42, 0), (0.115, 0.38, 0), (0.075, 0.38, 0)]
    out.append(C.finalize(lathe_at("FrontSleeve", P, [steel], FB, (1, 0, 0), steps=48), angle=40))
    return out


def rear_bush(paint, rubber, steel):
    out = []
    P = [(0.34, -0.26, 0), (0.43, -0.26, 0), (0.43, 0.20, 0), (0.48, 0.22, 0), (0.48, 0.26, 0), (0.34, 0.26, 0)]
    cup = lathe_at("RearCup", P, [paint], RB, (0, 0, 1), steps=80)
    C.add_bevel(cup, 0.012, segments=2, angle=30)
    out.append(C.finalize(cup, angle=35))
    P = [(0.10, -0.30, 0), (0.345, -0.28, 0), (0.345, 0.27, 0), (0.30, 0.30, 0), (0.22, 0.31, 0), (0.15, 0.36, 0), (0.10, 0.36, 0)]
    rb = lathe_at("RearRubber", P, [rubber], RB, (0, 0, 1), steps=80)
    # kidney-shaped voids in the rubber
    cb = bmesh.new()
    for a in (0.0, math.pi):
        M = Matrix.Translation(RB + Vector((0.23 * math.cos(a + 0.6), 0.23 * math.sin(a + 0.6), 0)))
        C.cyl_bm(cb, 0.055, 0.0, 0.5, seg=24, matrix=M)
    cut = C.mesh_obj("Voids", cb, [rubber])
    boolean(rb, cut)
    out.append(C.finalize(rb, angle=40, remove=[cut]))
    P = [(0.07, -0.34, 0), (0.105, -0.34, 0), (0.105, 0.42, 0), (0.07, 0.42, 0)]
    out.append(C.finalize(lathe_at("RearSleeve", P, [steel], RB, (0, 0, 1), steps=48), angle=40))
    return out


def ball_joint(paint, rubber, steel):
    out = []
    z = T / 2
    P = [(0.0, -T / 2 - 0.14, 0), (0.22, -T / 2 - 0.14, 0), (0.27, -T / 2 - 0.08, 0), (0.27, z + 0.02, 0),
         (0.30, z + 0.03, 0), (0.30, z + 0.07, 0), (0.0, z + 0.07, 0)]
    hs = lathe_at("BJHousing", P, [paint], BJ, (0, 0, 1), steps=80)
    C.add_bevel(hs, 0.012, segments=2, angle=30)
    out.append(C.finalize(hs, angle=35))
    # boot
    z0 = z + 0.07
    P = [(0.0, z0, 0), (0.25, z0, 0), (0.27, z0 + 0.04, 0), (0.26, z0 + 0.12, 0), (0.21, z0 + 0.19, 0),
         (0.14, z0 + 0.23, 0), (0.115, z0 + 0.26, 0), (0.115, z0 + 0.30, 0), (0.0, z0 + 0.30, 0)]
    out.append(C.finalize(lathe_at("BJBoot", P, [rubber], BJ, (0, 0, 1), steps=80), angle=50))
    # stud with pinch-bolt groove, threaded-look rings at the tip
    z1 = z0 + 0.30
    P = [(0.0, z1 - 0.02, 0), (0.085, z1 - 0.02, 0), (0.085, z1 + 0.16, 0), (0.06, z1 + 0.18, 0),
         (0.06, z1 + 0.22, 0), (0.085, z1 + 0.24, 0), (0.085, z1 + 0.42, 0), (0.07, z1 + 0.44, 0), (0.0, z1 + 0.44, 0)]
    out.append(C.finalize(lathe_at("BJStud", P, [steel], BJ, (0, 0, 1), steps=48), angle=40))
    # rivets
    bm = bmesh.new()
    for k in range(3):
        a = math.radians(70 + 120 * k)
        p = BJ + Vector((0.42 * math.cos(a), 0.42 * math.sin(a), z - 0.02))
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=0.06,
                                  matrix=Matrix.Translation(p) @ Matrix.Diagonal((1, 1, 0.55, 1)))
    for f in bm.faces:
        f.smooth = True
    out.append(C.mesh_obj("Rivets", bm, [paint]))
    return out


def build():
    paint = mat_worn_black()
    rubber = C.mat_rubber()
    steel = C.principled("ZincSteel", (0.60, 0.59, 0.56), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    objs = [arm(paint)] + front_bush(paint, rubber, steel) + rear_bush(paint, rubber, steel) + ball_joint(paint, rubber, steel)
    C.transform_all(objs, Matrix.Rotation(math.radians(-30), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("braccio", objs, "braccio.py",
            "front lower control arm: L-shaped pressed-steel wishbone, black paint, two rubber bushes, ball joint with rubber boot",
            az=35, el=38, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
