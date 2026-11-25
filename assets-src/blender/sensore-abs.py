"""ABS wheel-speed sensor (sensore ABS) as removed from a small car: black moulded sensor
head (pin with O-ring and flat sensing face, wider back with the cable exit and strain
relief) with a mounting ear and pressed-in steel bushing; long black PVC cable coiled in
a loose bundle held by two cable ties, two rubber grommets and a steel P-clip on the
leads, and a small two-pin plug with latch at the other end. Lying on the floor, z up.
1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RC = 0.026                       # cable radius (5 mm cable)
CC = Vector((0.55, 0.35, 0.0))   # coil centre
RCO = 0.78                       # coil radius
TURNS = 2.4


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
    th0 = math.radians(215)
    n = int(TURNS * 96)
    pts = []
    for i in range(n + 1):
        t = i / n
        th = th0 + TURNS * math.tau * t
        R = RCO + 0.035 * math.sin(3 * th + 0.7) + 0.02 * math.sin(7 * th)
        z = RC + 2.05 * RC * TURNS * t
        pts.append(CC + Vector((R * math.cos(th), R * math.sin(th), z)))
    return pts


def cable_ties(black):
    out = []
    h = 2.05 * RC * TURNS + 2 * RC + 0.012
    for th in (math.radians(20), math.radians(140)):
        R = RCO + 0.035 * math.sin(3 * th + 0.7) + 0.02 * math.sin(7 * th)
        rad = Vector((math.cos(th), math.sin(th), 0))
        tan = Vector((-math.sin(th), math.cos(th), 0))
        w = RC + 0.045
        corners = [(R - w, -0.006), (R + w, -0.006), (R + w, h), (R - w, h)]
        path = []
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            for i in range(8):
                t = i / 8
                u = a[0] + (b[0] - a[0]) * t
                v = a[1] + (b[1] - a[1]) * t
                path.append((u, v))
        # round the loop a little
        cx = R
        cz = h / 2
        pts = []
        for (u, v) in path:
            du, dv = u - cx, v - cz
            k = 0.92 + 0.08 * (1 - abs(du) / w * abs(dv) / (h / 2))
            pts.append(CC + rad * (cx + du * k) + Vector((0, 0, cz + dv * k)))
        pts.append(pts[0])
        bm = bmesh.new()
        frames = []
        for i, p in enumerate(pts[:-1]):
            T = (pts[(i + 1) % (len(pts) - 1)] - pts[i - 1]).normalized()
            frames.append((p, tan, T.cross(tan).normalized(), [(-0.022, -0.004), (0.022, -0.004), (0.022, 0.004), (-0.022, 0.004)]))
        frames.append(frames[0])
        C.sweep(bm, frames, cap=False)
        C.fix_normals(bm)
        tie = C.mesh_obj("Tie", bm, [black])
        out.append(C.finalize(tie, angle=50))
        # tie head on top
        bm = bmesh.new()
        C.box_bm(bm, 0.07, 0.06, 0.035, center=CC + rad * (R + 0.02) + Vector((0, 0, h + 0.016)),
                 matrix=None)
        hd = C.mesh_obj("TieHead", bm, [black])
        hd.matrix_world = Matrix.Translation(CC + rad * (R + 0.02) + Vector((0, 0, h + 0.016))) @ \
            Matrix.Rotation(th, 4, "Z") @ Matrix.Translation(-(CC + rad * (R + 0.02) + Vector((0, 0, h + 0.016))))
        C.add_bevel(hd, 0.008, segments=2, angle=30)
        out.append(C.finalize(hd, angle=35))
    return out


# ----------------------------------------------------------------- sensor head + plug
def sensor_head(black, steel, oring):
    """local: pin axis -X, back of the head at x=0, cable leaves along +X"""
    out = []
    zc = 0.125
    o = Vector((0, 0, zc))
    ax = Vector((-1, 0, 0))
    P = [(0.0, 0.0, 0), (0.12, 0.0, 0), (0.125, 0.02, 0), (0.125, 0.15, 0), (0.105, 0.17, 0), (0.088, 0.17, 0),
         (0.085, 0.19, 0), (0.085, 0.50, 0), (0.078, 0.515, 0), (0.0, 0.515, 0)]
    hd = lathe_at("SensorBody", P, [black], o, ax, steps=64)
    out.append(C.finalize(hd, angle=40))
    P = [(0.084, 0.215, 0), (0.096, 0.215, 0), (0.104, 0.24, 0), (0.096, 0.265, 0), (0.084, 0.265, 0)]
    out.append(C.finalize(lathe_at("ORing", P, [oring], o, ax, steps=64), angle=60))
    # mounting ear (plane perpendicular to the pin axis), at the shoulder
    bm = bmesh.new()
    eh = 0.06
    pts = []
    for i in range(13):
        a = math.pi / 2 + math.pi * i / 12
        pts.append((0.11 * math.cos(a), 0.11 * math.sin(a)))
    for i in range(13):
        a = -math.pi / 2 + math.pi * i / 12
        pts.append((0.30 + 0.085 * math.cos(a), 0.085 * math.sin(a)))
    bot = [bm.verts.new((-0.13, y, zc + z)) for (y, z) in [(p[0], p[1]) for p in pts]]
    top = [bm.verts.new((-0.13 - eh, y, zc + z)) for (y, z) in [(p[0], p[1]) for p in pts]]
    bm.faces.new(bot)
    bm.faces.new(top[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    C.fix_normals(bm)
    ear = C.mesh_obj("Ear", bm, [black])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.058, -0.3, 0.1, seg=32, matrix=Matrix.Translation((0, 0.30, zc)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    cut = C.mesh_obj("EarHole", cb, [black])
    boolean(ear, cut)
    C.add_bevel(ear, 0.01, segments=2, angle=30)
    out.append(C.finalize(ear, angle=35, remove=[cut]))
    P = [(0.034, -0.012, 0), (0.058, -0.012, 0), (0.058, eh + 0.012, 0), (0.034, eh + 0.012, 0)]
    out.append(C.finalize(lathe_at("Bush", P, [steel], Vector((-0.13, 0.30, zc)), ax, steps=40), angle=40))
    # strain relief boot at the back
    P = [(0.0, -0.02, 0), (0.07, -0.02, 0), (0.06, 0.06, 0), (0.042, 0.13, 0), (RC + 0.006, 0.17, 0), (0.0, 0.17, 0)]
    out.append(C.finalize(lathe_at("Relief", P, [black], o, Vector((1, 0, 0)), steps=40), angle=50))
    return out, o + Vector((0.16, 0, 0))


def plug(black, pin):
    """local: cable enters along +X at the origin end, mouth at -X... built along +X"""
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 0.34, 0.20, 0.16, center=(0.17 + 0.12, 0, 0))
    bd = C.mesh_obj("Plug", bm, [black])
    cb = bmesh.new()
    for s in (-1, 1):
        C.box_bm(cb, 0.12, 0.05, 0.05, center=(0.46, s * 0.045, 0))
    cut = C.mesh_obj("PlugCut", cb, [black])
    boolean(bd, cut)
    C.add_bevel(bd, 0.018, segments=3, angle=30)
    out.append(C.finalize(bd, angle=35, remove=[cut]))
    bm = bmesh.new()
    C.box_bm(bm, 0.18, 0.08, 0.02, center=(0.33, 0, 0.09))      # latch
    C.box_bm(bm, 0.04, 0.08, 0.035, center=(0.40, 0, 0.10))
    lt = C.mesh_obj("Latch", bm, [black])
    C.add_bevel(lt, 0.006, segments=2, angle=30)
    out.append(C.finalize(lt, angle=35))
    P = [(0.0, -0.01, 0), (0.07, -0.01, 0), (0.07, 0.03, 0), (0.05, 0.10, 0), (RC + 0.006, 0.14, 0), (0.0, 0.14, 0)]
    out.append(C.finalize(lathe_at("PlugBoot", P, [black], Vector((0.13, 0, 0)), (-1, 0, 0), steps=40), angle=50))
    return out


def grommet(rubber, p, t):
    P = [(RC, -0.10, 0), (0.045, -0.09, 0), (0.068, -0.05, 0), (0.068, -0.018, 0), (0.05, -0.012, 0), (0.05, 0.012, 0),
         (0.068, 0.018, 0), (0.068, 0.05, 0), (0.045, 0.09, 0), (RC, 0.10, 0)]
    return C.finalize(lathe_at("Grommet", P, [rubber], p, t, steps=48), angle=45)


def p_clip(steel, p, t):
    out = []
    P = [(RC + 0.002, -0.03, 0), (RC + 0.012, -0.03, 0), (RC + 0.012, 0.03, 0), (RC + 0.002, 0.03, 0)]
    out.append(C.finalize(lathe_at("ClipRing", P, [steel], p, t, steps=32), angle=40))
    side = t.cross(Vector((0, 0, 1))).normalized()
    bm = bmesh.new()
    C.box_bm(bm, 0.06, 0.16, 0.012, center=(0, 0.09, 0))
    tab = C.mesh_obj("ClipTab", bm, [steel])
    M = Matrix.Identity(4)
    M.col[0] = t.to_4d()
    M.col[1] = side.to_4d()
    M.col[2] = t.cross(side).to_4d()
    M.col[0][3] = M.col[1][3] = M.col[2][3] = 0
    tab.matrix_world = Matrix.Translation(p + Vector((0, 0, -RC + 0.006))) @ M
    cb = bmesh.new()
    C.cyl_bm(cb, 0.022, -0.1, 0.1, seg=20, matrix=Matrix.Translation((0, 0.13, 0)))
    hole = C.mesh_obj("ClipHole", cb, [steel])
    hole.matrix_world = tab.matrix_world.copy()
    boolean(tab, hole)
    C.add_bevel(tab, 0.004, segments=1, angle=30)
    out.append(C.finalize(tab, angle=35, remove=[hole]))
    return out


def build():
    black = C.mat_black_plastic("SensorPA", rough=0.5, color=0.025)
    pvc = mat_pvc()
    rubber = C.mat_rubber("Grommet")
    steel = C.principled("ZincSteel", (0.62, 0.62, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    oring = C.principled("ORingNBR", (0.03, 0.03, 0.03), rough=0.55)
    objs = []
    head, exit_local = sensor_head(black, steel, oring)
    MH = Matrix.Translation((-1.05, -0.85, 0)) @ Matrix.Rotation(math.radians(-15), 4, "Z")
    C.transform_all(head, MH)
    objs += head
    H = MH @ exit_local
    hdir = (MH.to_3x3() @ Vector((1, 0, 0))).normalized()
    coil = coil_path()
    S = coil[0]
    tS = (coil[1] - coil[0]).normalized()
    lead1 = bezier(H, H + hdir * 0.5, S - tS * 0.6, S, 50)
    E = coil[-1]
    tE = (coil[-1] - coil[-2]).normalized()
    K = Vector((1.45, -1.05, 0.09))
    kdir = Vector((0.55, -1, 0)).normalized()
    lead2 = bezier(E, E + tE * 0.7, K - kdir * 0.8 + Vector((0, 0, -0.04)), K, 60)
    path = resample(lead1[:-1] + coil[:-1] + lead2, 0.02)
    objs.append(tube("Cable", path, RC, pvc, seg=16))
    objs += cable_ties(black)
    p, t = point_at(lead1, 0.45)
    objs.append(grommet(rubber, p, t))
    p, t = point_at(lead2, 0.35)
    objs.append(grommet(rubber, p, t))
    p, t = point_at(lead2, 0.72)
    objs += p_clip(steel, p, t)
    pl = plug(black, None)
    MP = Matrix.Translation(K) @ kdir.to_track_quat("X", "Z").to_matrix().to_4x4() @ Matrix.Translation((-0.13, 0, 0))
    C.transform_all(pl, MP)
    objs += pl
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("sensore-abs", objs, "sensore-abs.py",
            "ABS wheel speed sensor: black sensor head with mounting ear, long black cable coiled with ties, rubber grommets, two-pin connector",
            az=20, el=60, lens=70, fill=0.88,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
