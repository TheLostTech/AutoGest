"""Anti-roll bar (barra stabilizzatrice) as removed from a small car, laid flat: 20 mm
solid spring-steel bar in worn black paint, bent into a wide U with clearance kinks in
the centre section and two forward arms ending in forged flat eyes with link holes; two
rubber D-bushes held by pressed-steel clamps with bolt flanges, and a pair of pressed
collars that locate the bushes. 1 unit ~ 10 cm (about 95 cm across)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from braccio import mat_worn_black

RBAR = 0.10
XB = 2.55            # bush positions (x = +/-XB)

# ----------------------------------------------------------------- generic helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=48, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def bezier(p0, p1, p2, p3, n=40):
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / n for i in range(n + 1))]


def frames_along(pts):
    out = []
    n = len(pts)
    T0 = (pts[1] - pts[0]).normalized()
    U = T0.cross(Vector((0, 0, 1)))
    if U.length < 1e-3:
        U = T0.cross(Vector((1, 0, 0)))
    U.normalize()
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        U = (U - T * U.dot(T)).normalized()
        out.append((p, U, T.cross(U)))
    return out


def tube(name, pts, r, mat, seg=16):
    sec = [(r * math.cos(math.tau * i / seg), r * math.sin(math.tau * i / seg)) for i in range(seg)]
    bm = bmesh.new()
    C.sweep(bm, [(p, U, V, sec) for (p, U, V) in frames_along(pts)])
    C.fix_normals(bm)
    return C.finalize(C.mesh_obj(name, bm, [mat]), angle=70)


def resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        while acc + seg >= step:
            t = (step - acc) / seg
            a = a + (b - a) * t
            out.append(a.copy())
            seg = (b - a).length
            acc = 0.0
        acc += seg
    out.append(pts[-1])
    return out


def point_at(pts, f):
    """point and tangent at fraction f of the polyline length"""
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    s = f * L[-1]
    for i in range(len(pts) - 1):
        if L[i + 1] >= s:
            t = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
            return pts[i] + (pts[i + 1] - pts[i]) * t, (pts[i + 1] - pts[i]).normalized()
    return pts[-1], (pts[-1] - pts[-2]).normalized()


def mat_pvc(name="CablePVC"):
    m = C.principled(name, (0.020, 0.020, 0.021), rough=0.38)
    C.add_noise_bump(m, scale=300, strength=0.04, distance=0.0006, rough_var=0.06)
    return m


# ----------------------------------------------------------------- bar
def catmull(ctrl, n=12):
    pts = []
    P = [ctrl[0] * 2 - ctrl[1]] + ctrl + [ctrl[-1] * 2 - ctrl[-2]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(ctrl[-1])
    return pts


def bar_path():
    z = RBAR
    half = [Vector((0.0, 0.0, z)), Vector((1.2, 0.0, z)), Vector((1.75, 0.18, z)), Vector((2.15, 0.22, z)),
            Vector((3.30, 0.22, z)), Vector((3.95, 0.40, z)), Vector((4.30, 0.95, z)), Vector((4.42, 1.80, z)),
            Vector((4.52, 2.55, z)), Vector((4.60, 2.90, z))]
    ctrl = [Vector((-p.x, p.y, p.z)) for p in reversed(half[1:])] + half
    return resample(catmull(ctrl, 14), 0.03)


def flat_eye(paint, p, t):
    """forged flat end: tapered swage + flat paddle with a link hole, lying flat"""
    out = []
    side = Vector((-t.y, t.x, 0)).normalized()
    pts = []
    L = 0.42
    W = 0.15
    n = 20
    pts.append((-0.06, -0.085))
    pts.append((0.10, -W))
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        pts.append((L + W * math.cos(a), W * math.sin(a)))
    pts.append((0.10, W))
    pts.append((-0.06, 0.085))
    bm = bmesh.new()
    zc = RBAR
    th = 0.042
    bot = [bm.verts.new(p + t * u + side * v + Vector((0, 0, zc - th - p.z))) for (u, v) in pts]
    top = [bm.verts.new(p + t * u + side * v + Vector((0, 0, zc + th - p.z))) for (u, v) in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    C.fix_normals(bm)
    ob = C.mesh_obj("FlatEye", bm, [paint])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.062, -0.5, 0.5, seg=32, matrix=Matrix.Translation(p + t * L))
    hole = C.mesh_obj("EyeHole", cb, [paint])
    boolean(ob, hole)
    C.add_bevel(ob, 0.018, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[hole]))
    # swage transition: round bar squeezed into the paddle
    P = [(0.0, -0.20, 0), (RBAR, -0.20, 0), (RBAR, -0.10, 0), (0.08, 0.0, 0), (0.055, 0.06, 0), (0.0, 0.08, 0)]
    sw = lathe_at("Swage", P, [paint], p, t, steps=48)
    out.append(C.finalize(sw, angle=40))
    return out


def bush_clamp(rubber, steel, x, y):
    out = []
    zc = 0.255                      # bush centre height above the floor (clamp flanges on the floor)
    R = 0.215
    # D-shaped rubber bush (flat at the bottom), axis along X
    pts = []
    for i in range(25):
        a = math.radians(-35 + 250 * i / 24)
        pts.append((R * math.cos(a), R * math.sin(a)))
    pts += [(-0.17, -R + 0.005), (0.17, -R + 0.005)]
    bm = bmesh.new()
    L = 0.34
    a_ = [bm.verts.new((x - L / 2, y + u, zc + v)) for (u, v) in pts]
    b_ = [bm.verts.new((x + L / 2, y + u, zc + v)) for (u, v) in pts]
    bm.faces.new(a_[::-1])
    bm.faces.new(b_)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
    C.fix_normals(bm)
    bu = C.mesh_obj("Bush", bm, [rubber])
    C.add_bevel(bu, 0.025, segments=3, angle=30)
    out.append(C.finalize(bu, angle=35))
    # pressed-steel omega clamp: arch over the bush, legs, flat flanges with bolt holes
    path = [(0.40, 0.0), (0.27, 0.0), (0.235, 0.03), (0.232, zc - 0.03)]
    for i in range(1, 24):
        a = math.radians(180 * i / 24)
        path.append((0.232 * math.cos(a), zc + 0.232 * math.sin(a) * 1.0))
    path += [(-0.232, zc - 0.03), (-0.235, 0.03), (-0.27, 0.0), (-0.40, 0.0)]
    thk = 0.022
    outer, inner = [], []
    for i, (u, v) in enumerate(path):
        a = Vector(path[max(i - 1, 0)])
        b = Vector(path[min(i + 1, len(path) - 1)])
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x))
        outer.append(Vector((u, v)) + nrm * thk / 2)
        inner.append(Vector((u, v)) - nrm * thk / 2)
    poly = outer + inner[::-1]
    W = 0.24
    bm = bmesh.new()
    a_ = [bm.verts.new((x - W / 2, y + q.x, q.y + 0.011)) for q in poly]
    b_ = [bm.verts.new((x + W / 2, y + q.x, q.y + 0.011)) for q in poly]
    bm.faces.new(a_[::-1])
    bm.faces.new(b_)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
    C.fix_normals(bm)
    cl = C.mesh_obj("Clamp", bm, [steel])
    cb = bmesh.new()
    for s in (-1, 1):
        C.cyl_bm(cb, 0.045, -0.2, 0.2, seg=24, matrix=Matrix.Translation((x, y + s * 0.335, 0)))
    holes = C.mesh_obj("ClampHoles", cb, [steel])
    boolean(cl, holes)
    C.add_bevel(cl, 0.008, segments=2, angle=30)
    out.append(C.finalize(cl, angle=35, remove=[holes]))
    return out, zc


def build():
    paint = mat_worn_black("BarPaint")
    rubber = C.mat_rubber("BushRubber")
    steel = C.principled("ClampZinc", (0.55, 0.55, 0.53), metallic=1.0, rough=0.34)
    C.add_noise_bump(steel, scale=600, strength=0.08, distance=0.0006, rough_var=0.08)
    path = bar_path()
    # lift the centre section so it passes through the bush centres (bar rests on the clamps)
    zc = 0.255
    lifted = []
    for p in path:
        w = 1 - C.smoothstep(XB + 0.4, XB + 1.6, abs(p.x)) if p.y < 0.6 else 0.0
        lifted.append(Vector((p.x, p.y, RBAR + (zc - RBAR) * w)))
    path = resample(lifted, 0.03)
    objs = [tube("Bar", path, RBAR, paint, seg=28)]
    for sx in (-1, 1):
        p = Vector((sx * XB, 0.22, 0))
        g, _ = bush_clamp(rubber, steel, p.x, p.y)
        objs += g
        # locating collars either side of the bush
        for d in (-1, 1):
            P = [(RBAR - 0.005, -0.03, 0), (RBAR + 0.025, -0.03, 0), (RBAR + 0.025, 0.03, 0), (RBAR - 0.005, 0.03, 0)]
            objs.append(C.finalize(lathe_at("Collar", P, [steel], Vector((p.x + d * 0.215, 0.22, zc)), (1, 0, 0), steps=40), angle=40))
    for end in (0, 1):
        q = path[-1] if end else path[0]
        t = ((path[-1] - path[-2]) if end else (path[0] - path[1])).normalized()
        objs += flat_eye(paint, q, t)
    C.transform_all(objs, Matrix.Rotation(math.radians(-22), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("barra-stabilizzatrice", objs, "barra-stabilizzatrice.py",
            "anti-roll bar: bent black steel bar with flattened eye ends, two rubber bushes in steel clamps",
            az=8, el=40, lens=60, fill=0.92,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
