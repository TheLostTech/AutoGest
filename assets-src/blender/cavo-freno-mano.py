"""Handbrake cable (cavo freno a mano) as removed from a small car: long black PVC-sheathed
cable coiled in a loose bundle held by tape, with its end fittings: at the lever end a
zinc sheath ferrule with hex collar, a short length of stranded inner cable and a barrel
nipple; at the brake end a zinc sheath fitting with the star-shaped retaining clip, the
exposed inner cable with its return coil spring and a cylindrical end nipple; a rubber
grommet with a steel mounting tab half way along. Lying on the floor, z up.
1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RC = 0.033                       # sheath radius (6.5 mm)
CC = Vector((0.35, 0.40, 0.0))   # coil centre
RCO = 0.98
TURNS = 2.3

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


# ----------------------------------------------------------------- coil
def coil_path():
    th0 = math.radians(225)
    n = int(TURNS * 120)
    pts = []
    for i in range(n + 1):
        t = i / n
        th = th0 + TURNS * math.tau * t
        R = RCO + 0.05 * math.sin(2 * th + 0.4) + 0.025 * math.sin(5 * th + 1.0)
        z = RC + 2.05 * RC * TURNS * t
        pts.append(CC + Vector((R * math.cos(th), R * math.sin(th), z)))
    return pts


def tape_wraps(tape):
    out = []
    h = 2.05 * RC * TURNS + 2 * RC
    for th in (math.radians(75), math.radians(330)):
        R = RCO + 0.05 * math.sin(2 * th + 0.4) + 0.025 * math.sin(5 * th + 1.0)
        rad = Vector((math.cos(th), math.sin(th), 0))
        tan = Vector((-math.sin(th), math.cos(th), 0))
        w = RC + 0.03
        n = 48
        pts = []
        for i in range(n):
            a = math.tau * i / n
            # superellipse around the bundle cross-section
            ca, sa = math.cos(a), math.sin(a)
            u = w * math.copysign(abs(ca) ** 0.5, ca)
            v = (h / 2 + 0.012) * math.copysign(abs(sa) ** 0.5, sa)
            pts.append(CC + rad * (R + u) + Vector((0, 0, h / 2 + v - 0.006)))
        bm = bmesh.new()
        frames = []
        for i, p in enumerate(pts):
            T = (pts[(i + 1) % n] - pts[i - 1]).normalized()
            frames.append((p, tan, T.cross(tan).normalized(), [(-0.07, -0.004), (0.07, -0.004), (0.07, 0.004), (-0.07, 0.004)]))
        frames.append(frames[0])
        C.sweep(bm, frames, cap=False)
        C.fix_normals(bm)
        out.append(C.finalize(C.mesh_obj("Tape", bm, [tape]), angle=50))
    return out


# ----------------------------------------------------------------- end fittings
def strand_mod(pitch=0.05, k=7):
    def f(r, z, t):
        if r < 0.005:
            return r
        return r * (1 + 0.10 * math.cos(k * t + math.tau * z / pitch))
    return f


def frame_at(p, t):
    return Matrix.Translation(p) @ t.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lever_end(zinc, steel, p, t):
    """sheath ends at p, fitting continues along t"""
    out = []
    P = [(RC - 0.004, -0.06, 0), (0.042, -0.06, 0), (0.048, -0.04, 0), (0.048, 0.10, 0), (0.0, 0.10, 0)]
    out.append(C.finalize(lathe_at("FerruleA", P, [zinc], p, t, steps=48), angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.07, 0.10, 0.17, seg=6)
    hx = C.mesh_obj("HexA", bm, [zinc])
    hx.matrix_world = frame_at(p, t)
    C.add_bevel(hx, 0.008, segments=2, angle=30)
    out.append(C.finalize(hx, angle=35))
    P = [(0.0, 0.17, 0), (0.035, 0.17, 0), (0.026, 0.21, 0), (0.0, 0.21, 0)]
    out.append(C.finalize(lathe_at("NoseA", P, [zinc], p, t, steps=32), angle=40))
    # inner cable and barrel nipple
    P = [(0.0, 0.20, 0), (0.014, 0.20, 0), (0.014, 0.62, 0), (0.0, 0.62, 0)]
    out.append(C.finalize(lathe_at("InnerA", P, [steel], p, t, steps=24, mod=strand_mod()), angle=60))
    side = t.cross(Vector((0, 0, 1))).normalized()
    q = p + t * 0.66
    P = [(0.0, -0.075, 0), (0.042, -0.075, 0), (0.045, -0.06, 0), (0.045, 0.06, 0), (0.042, 0.075, 0), (0.0, 0.075, 0)]
    out.append(C.finalize(lathe_at("Barrel", P, [zinc], q, side, steps=32), angle=40))
    P = [(0.0, 0.58, 0), (0.024, 0.58, 0), (0.024, 0.64, 0), (0.0, 0.64, 0)]
    out.append(C.finalize(lathe_at("Swage", P, [zinc], p, t, steps=24), angle=40))
    return out


def brake_end(zinc, steel, spring, p, t):
    out = []
    P = [(RC - 0.004, -0.08, 0), (0.044, -0.08, 0), (0.05, -0.06, 0), (0.05, 0.05, 0), (0.075, 0.06, 0),
         (0.075, 0.10, 0), (0.05, 0.11, 0), (0.05, 0.20, 0), (0.036, 0.22, 0), (0.0, 0.22, 0)]
    out.append(C.finalize(lathe_at("FerruleB", P, [zinc], p, t, steps=48), angle=40))
    # star retaining clip on the spigot
    def star(r, z, tt):
        f = (tt * 6 / math.tau) % 1.0
        return r if r < 0.08 else r - 0.04 * (1 - abs(2 * f - 1)) ** 2
    P = [(0.05, 0.12, 0), (0.12, 0.12, 0), (0.12, 0.135, 0), (0.05, 0.135, 0)]
    out.append(C.finalize(lathe_at("StarClip", P, [spring], p, t, steps=96, mod=star), angle=40))
    # exposed inner cable with return spring and end nipple
    P = [(0.0, 0.21, 0), (0.014, 0.21, 0), (0.014, 0.70, 0), (0.0, 0.70, 0)]
    out.append(C.finalize(lathe_at("InnerB", P, [steel], p, t, steps=24, mod=strand_mod()), angle=60))
    pts = []
    n = 9 * 20
    side = t.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(t).normalized()
    for i in range(n + 1):
        u = i / n
        a = 9 * math.tau * u
        pts.append(p + t * (0.24 + 0.36 * u) + (side * math.cos(a) + up * math.sin(a)) * 0.036)
    cu = bpy.data.curves.new("ReturnSpring", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.008
    cu.bevel_resolution = 2
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for qq, v in zip(sp.points, pts):
        qq.co = (v.x, v.y, v.z, 1)
    cu.materials.append(spring)
    out.append(C.finalize(C.link(bpy.data.objects.new("ReturnSpring", cu)), angle=60))
    P = [(0.0, 0.64, 0), (0.04, 0.64, 0), (0.045, 0.655, 0), (0.045, 0.74, 0), (0.04, 0.755, 0), (0.0, 0.755, 0)]
    nb = lathe_at("EndNipple", P, [zinc], p, t, steps=32)
    C.add_bevel(nb, 0.004, segments=1, angle=30)
    out.append(C.finalize(nb, angle=40))
    return out


def grommet_tab(rubber, steel, p, t):
    out = []
    P = [(RC, -0.14, 0), (0.06, -0.13, 0), (0.085, -0.09, 0), (0.085, -0.03, 0), (0.07, -0.02, 0), (0.07, 0.02, 0),
         (0.085, 0.03, 0), (0.085, 0.09, 0), (0.06, 0.13, 0), (RC, 0.14, 0)]
    out.append(C.finalize(lathe_at("Grommet", P, [rubber], p, t, steps=48), angle=45))
    side = t.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(t).normalized()
    # steel tab clamped in the groove, lying flat
    pts = [(-0.035, 0.0), (0.035, 0.0)] + [(0.07 * math.cos(a), 0.24 + 0.07 * math.sin(a)) for a in
                                           [math.radians(-60 + 300 * i / 16) for i in range(17)]]
    bm = bmesh.new()
    zb = -0.018
    bot = [bm.verts.new(p + t * u + side * v + up * (zb - 0.009)) for (u, v) in pts]
    top = [bm.verts.new(p + t * u + side * v + up * (zb + 0.009)) for (u, v) in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    C.fix_normals(bm)
    tab = C.mesh_obj("Tab", bm, [steel])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.03, -0.2, 0.2, seg=20, matrix=frame_at(p + side * 0.24, up))
    hole = C.mesh_obj("TabHole", cb, [steel])
    boolean(tab, hole)
    C.add_bevel(tab, 0.004, segments=1, angle=30)
    out.append(C.finalize(tab, angle=35, remove=[hole]))
    return out


def build():
    pvc = mat_pvc("SheathPVC")
    tape = C.principled("Tape", (0.012, 0.012, 0.013), rough=0.32)
    C.add_noise_bump(tape, scale=200, strength=0.08, distance=0.0008)
    rubber = C.mat_rubber("Grommet")
    zinc = C.principled("Zinc", (0.64, 0.63, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    steel = C.principled("StrandSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.32)
    spring = C.principled("SpringSteel", (0.07, 0.07, 0.075), metallic=0.8, rough=0.35)
    objs = []
    coil = coil_path()
    S, tS = coil[0], (coil[1] - coil[0]).normalized()
    E, tE = coil[-1], (coil[-1] - coil[-2]).normalized()
    A = Vector((-1.35, -1.05, RC + 0.012))
    adir = Vector((-0.75, -1, 0)).normalized()
    B = Vector((1.70, -1.05, RC + 0.01))
    bdir = Vector((0.55, -1, 0)).normalized()
    lead1 = bezier(A, A - adir * 0.9, S - tS * 0.8, S, 60)
    lead2 = bezier(E, E + tE * 0.9, B - bdir * 0.9 + Vector((0, 0, -0.02)), B, 70)
    path = resample(lead1[:-1] + coil[:-1] + lead2, 0.02)
    objs.append(tube("Sheath", path, RC, pvc, seg=16))
    objs += tape_wraps(tape)
    objs += lever_end(zinc, steel, A, adir)
    objs += brake_end(zinc, steel, spring, B, bdir)
    p, t = point_at(lead2, 0.35)
    objs += grommet_tab(rubber, zinc, p, t)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("cavo-freno-mano", objs, "cavo-freno-mano.py",
            "handbrake cable: long black sheathed steel cable coiled, metal end ferrules, barrel nipple, return spring, retaining clip, rubber grommet",
            az=18, el=48, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
