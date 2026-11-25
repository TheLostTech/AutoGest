"""Flexible brake hose (tubo freno flessibile) as removed from a small car: black EPDM hose
with a thin moulded rib along its length, zinc-plated crimped ferrules at both ends; at
the caliper end a banjo eye with its hollow banjo bolt and two copper sealing washers, at
the chassis end a hex female fitting with grooved spigot and the spring-steel U clip that
holds it in the body bracket; a rubber-sleeved steel mid-bracket on the hose. Lying on
the floor, z up. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RH = 0.052          # hose radius (10.5 mm OD)
ZE = 0.15           # height of the end fittings' axis

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


# ----------------------------------------------------------------- parts
def hose_path():
    A = Vector((-1.05, -0.95, ZE))
    B = Vector((1.05, 0.85, ZE - 0.02))
    pts = bezier(A, A + Vector((1.25, 0.05, -0.08)), B + Vector((-1.25, -0.1, -0.1)), B, 120)
    out = []
    for i, p in enumerate(pts):
        t = i / (len(pts) - 1)
        sag = math.sin(math.pi * t) ** 0.6
        out.append(Vector((p.x, p.y, (1 - sag) * p.z + sag * RH)))
    return resample(out, 0.02)


def frame_at(p, t):
    return Matrix.Translation(p) @ t.to_track_quat("Z", "Y").to_matrix().to_4x4()


def ferrule(name, zinc, M):
    """crimped sleeve along local +Z from 0 to 0.30, hex crimp marks"""
    P = [(RH - 0.004, -0.01, 0), (0.07, -0.01, 0), (0.078, 0.0, 0)]
    for k in range(3):
        z = 0.04 + 0.085 * k
        P += [(0.078, z, 0), (0.073, z + 0.012, 0), (0.073, z + 0.045, 0), (0.078, z + 0.057, 0)]
    P += [(0.078, 0.30, 0), (0.07, 0.31, 0), (RH - 0.004, 0.31, 0)]

    def crimp(r, z, t):
        if 0.03 < z < 0.29 and r > 0.072:
            return r - 0.006 * abs(math.cos(3 * t))
        return r
    ob = C.lathe(name, P, [zinc], steps=96, mod=crimp)
    ob.matrix_world = M
    C.add_bevel(ob, 0.003, segments=1, angle=35)
    return C.finalize(ob, angle=40)


def banjo_end(zinc, copper, steel, p, t):
    """ferrule pointing back into the hose, neck tube and eye (axis horizontal)"""
    out = []
    out.append(ferrule("FerruleA", zinc, frame_at(p, -t)))
    # neck
    tip = p - t * 0.30
    P = [(0.0, 0.0, 0), (0.042, 0.0, 0), (0.042, 0.16, 0), (0.0, 0.16, 0)]
    nk = C.lathe("Neck", P, [zinc], steps=32)
    nk.matrix_world = frame_at(tip, -t)
    out.append(C.finalize(nk, angle=40))
    side = t.cross(Vector((0, 0, 1))).normalized()
    E = tip - t * (0.16 + 0.13)
    # eye ring
    P = [(0.075, -0.08, 0), (0.14, -0.08, 0), (0.15, -0.065, 0), (0.15, 0.065, 0), (0.14, 0.08, 0), (0.075, 0.08, 0)]
    ey = C.lathe("Eye", P, [zinc], steps=64)
    ey.matrix_world = frame_at(E, side)
    out.append(C.finalize(ey, angle=40))
    # copper washers either side
    for s in (-1, 1):
        P = [(0.065, -0.012, 0), (0.15, -0.012, 0), (0.15, 0.012, 0), (0.065, 0.012, 0)]
        w = C.lathe("Washer", P, [copper], steps=64)
        w.matrix_world = frame_at(E + side * s * 0.093, side)
        C.add_bevel(w, 0.003, segments=1, angle=30)
        out.append(C.finalize(w, angle=40))
    # hollow banjo bolt: head on +side, thread out the other side
    pitch = 0.03

    def thread(r, z, tt):
        return r + 0.004 * math.sin(math.tau * z / pitch + tt) if (z < -0.12 and r > 0.05) else r
    P = [(0.0, -0.36, 0), (0.048, -0.36, 0)] + [(0.056, -0.34 + i * 0.01, 0) for i in range(22)] + \
        [(0.06, -0.11, 0), (0.06, 0.10, 0), (0.0, 0.10, 0)]
    bt = C.lathe("BoltShank", P, [steel], steps=48, mod=thread)
    bt.matrix_world = frame_at(E, side)
    out.append(C.finalize(bt, angle=50))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.118, 0.105, 0.205, seg=6)
    hx = C.mesh_obj("BoltHead", bm, [steel])
    hx.matrix_world = frame_at(E, side)
    cb = bmesh.new()
    C.cyl_bm(cb, 0.03, 0.15, 0.3, seg=20)
    hole = C.mesh_obj("BoltBore", cb, [steel])
    hole.matrix_world = frame_at(E, side)
    boolean(hx, hole)
    C.add_bevel(hx, 0.01, segments=2, angle=30)
    out.append(C.finalize(hx, angle=35, remove=[hole]))
    P = [(0.0, 0.10, 0), (0.125, 0.10, 0), (0.125, 0.115, 0), (0.0, 0.115, 0)]
    fl = C.lathe("BoltFlange", P, [steel], steps=48)
    fl.matrix_world = frame_at(E, side)
    out.append(C.finalize(fl, angle=40))
    return out


def chassis_end(zinc, spring, p, t):
    out = []
    out.append(ferrule("FerruleB", zinc, frame_at(p, t)))
    o = p + t * 0.31
    bm = bmesh.new()
    C.cyl_bm(bm, 0.115, 0.0, 0.13, seg=6)
    hx = C.mesh_obj("Hex", bm, [zinc])
    hx.matrix_world = frame_at(o, t)
    C.add_bevel(hx, 0.012, segments=2, angle=30)
    out.append(C.finalize(hx, angle=35))
    P = [(0.0, 0.13, 0), (0.078, 0.13, 0), (0.078, 0.16, 0), (0.064, 0.165, 0), (0.064, 0.20, 0), (0.078, 0.205, 0),
         (0.078, 0.32, 0), (0.07, 0.33, 0), (0.04, 0.33, 0), (0.04, 0.25, 0), (0.0, 0.25, 0)]
    sp = C.lathe("Spigot", P, [zinc], steps=64, mod=lambda r, z, tt: r - 0.01 * (abs(math.cos(tt)) > 0.93) if z > 0.2 and r > 0.07 else r)
    sp.matrix_world = frame_at(o, t)
    out.append(C.finalize(sp, angle=40))
    # U clip in the groove (horseshoe of flat spring steel)
    side = t.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(t).normalized()
    c = o + t * 0.1825
    frames = []
    n = 40
    for i in range(n + 1):
        a = -math.radians(200) + math.radians(220) * i / n
        r = 0.072
        P0 = c + (side * math.cos(a) + up * math.sin(a)) * r
        frames.append(P0)
    legs = [frames[0] + (frames[0] - frames[1]).normalized() * 0.12, frames[-1] + (frames[-1] - frames[-2]).normalized() * 0.10]
    pts = [legs[0]] + frames + [legs[1]]
    bm = bmesh.new()
    fr = []
    for i, q in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        fr.append((q, t, T.cross(t).normalized(), [(-0.016, -0.008), (0.016, -0.008), (0.016, 0.008), (-0.016, 0.008)]))
    C.sweep(bm, fr)
    C.fix_normals(bm)
    cl = C.mesh_obj("UClip", bm, [spring])
    C.add_bevel(cl, 0.003, segments=1, angle=30)
    out.append(C.finalize(cl, angle=40))
    return out


def mid_bracket(rubber, steel, p, t):
    out = []
    P = [(RH, -0.11, 0), (0.07, -0.10, 0), (0.078, -0.07, 0), (0.078, 0.07, 0), (0.07, 0.10, 0), (RH, 0.11, 0)]
    out.append(C.finalize(lathe_at("Sleeve", P, [rubber], p, t), angle=45))
    side = t.cross(Vector((0, 0, 1))).normalized()
    P = [(0.078, -0.05, 0), (0.092, -0.05, 0), (0.092, 0.05, 0), (0.078, 0.05, 0)]
    out.append(C.finalize(lathe_at("Band", P, [steel], p, t), angle=40))
    # flat tab with bolt hole, lying on the floor
    bm = bmesh.new()
    pts = [(-0.05, 0.0), (0.05, 0.0)] + [(0.075 * math.cos(a), 0.26 + 0.075 * math.sin(a)) for a in
                                          [math.radians(-50 + 280 * i / 16) for i in range(17)]]
    z0 = p.z - 0.092 - 0.018
    bot = [bm.verts.new(p + t * u + side * v + Vector((0, 0, z0 - p.z))) for (u, v) in pts]
    top = [bm.verts.new(p + t * u + side * v + Vector((0, 0, z0 + 0.018 - p.z))) for (u, v) in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    C.fix_normals(bm)
    tab = C.mesh_obj("Tab", bm, [steel])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.032, -0.1, 0.2, seg=20, matrix=Matrix.Translation(Vector((p.x, p.y, 0)) + side * 0.26))
    hole = C.mesh_obj("TabHole", cb, [steel])
    boolean(tab, hole)
    C.add_bevel(tab, 0.004, segments=1, angle=30)
    out.append(C.finalize(tab, angle=35, remove=[hole]))
    return out


def build():
    rubber = C.principled("HoseEPDM", (0.018, 0.018, 0.019), rough=0.55)
    C.add_noise_bump(rubber, scale=420, strength=0.06, distance=0.0008, rough_var=0.06)
    sleeve = C.mat_rubber("SleeveRubber")
    zinc = C.principled("YellowZinc", (0.70, 0.62, 0.40), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    steel = C.principled("ZincSteel", (0.62, 0.62, 0.60), metallic=1.0, rough=0.28)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    copper = C.principled("Copper", (0.80, 0.42, 0.26), metallic=1.0, rough=0.3)
    spring = C.principled("SpringClip", (0.05, 0.05, 0.055), metallic=0.8, rough=0.35)
    path = hose_path()
    # hose runs between the two ferrules
    pa, ta = point_at(path, 0.0)
    pb, tb = point_at(path, 1.0)
    objs = [tube("Hose", path, RH, rubber, seg=20)]
    # moulded rib along the hose
    fr = frames_along(path)
    rib = [p + U * (RH * 0.97) for (p, U, V) in fr][3:-3]
    objs.append(tube("Rib", rib, 0.008, rubber, seg=8))
    t0 = (path[1] - path[0]).normalized()
    objs += banjo_end(zinc, copper, steel, path[0] + t0 * 0.29, t0)
    t1 = (path[-1] - path[-2]).normalized()
    objs += chassis_end(zinc, spring, path[-1] - t1 * 0.29, t1)
    p, t = point_at(path, 0.42)
    objs += mid_bracket(sleeve, steel, p, t)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("tubo-freno", objs, "tubo-freno.py",
            "flexible brake hose: black rubber hose with crimped metal ferrules, banjo fitting with bolt and copper washers, threaded end with clip, mid bracket",
            az=20, el=42, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
