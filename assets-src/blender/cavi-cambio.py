"""Gear shift cables (cavi cambio / cavi selezione e innesto marce): a pair of black
plastic-sheathed Bowden cables loosely coiled on the floor. Each end carries a moulded
abutment fitting with a crimped steel ferrule, a rubber dust boot over the sliding inner
rod and a plastic eye end (eyelet with a pressed bush) for the lever / gearbox ball
stud; each cable also has a bulkhead clip (winged plastic clip in a rubber grommet).

Units ~ decimetres (coil ~45 cm across)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RS = 0.048          # sheath radius
ZF = 0.088          # axis height at the end fittings (largest fitting radius)


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M, steps=48, bevel=None, angle=40):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle)


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


def axis_matrix(origin, axis, roll=0.0):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "Z")


def coil_path(r0, r1, a0, turns, lead0, lead1, n=260):
    """flat CCW spiral from inner radius r0 to outer r1, with straight leads at both ends."""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a0 + math.tau * turns * t
        r = r0 + (r1 - r0) * t
        pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.0)))
    t0 = (pts[0] - pts[1]).normalized()
    t1 = (pts[-1] - pts[-2]).normalized()
    nh, nt = int(lead0 / 0.05), int(lead1 / 0.05)
    head = [pts[0] + t0 * lead0 * k / nh for k in range(nh, 0, -1)]
    tail = [pts[-1] + t1 * lead1 * k / nt for k in range(1, nt + 1)]
    return head + pts + tail


def offset_path(pts, d):
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        N = Vector((T.y, -T.x, 0.0))
        out.append(p + N * d)
    return out


def lift_ends(pts):
    """lying on the floor, lifted near the ends where the fittings are fatter"""
    out = []
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    for p, s in zip(pts, L):
        lift = max(1 - C.smoothstep(0.0, 0.5, s), C.smoothstep(L[-1] - 0.5, L[-1], s))
        out.append(Vector((p.x, p.y, RS + (ZF - RS) * lift)))
    return out


def sheath(name, pts, mat):
    sec = [(RS * math.cos(math.tau * i / 20), RS * math.sin(math.tau * i / 20)) for i in range(20)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec), cap=True)
    return fin(C.mesh_obj(name, bm, [mat]), angle=60)


def end_fitting(M, black, zinc, rubber, rod_m, bush_m, eye_rot=0.0):
    """M: local +Z points out of the sheath end, origin at the sheath end."""
    out = []
    # crimped steel ferrule over the sheath end
    P = [(0.0, -0.10, 0), (0.056, -0.10, 0), (0.058, -0.09, 0), (0.058, -0.06, 0), (0.054, -0.055, 0),
         (0.054, -0.045, 0), (0.058, -0.04, 0), (0.058, 0.01, 0), (0.0, 0.01, 0)]
    out.append(lathe_at("Ferrule", P, [zinc], M, steps=40))
    # moulded abutment body with a grooved collar
    P = [(0.0, 0.0, 0), (0.066, 0.0, 0), (0.07, 0.01, 0), (0.07, 0.05, 0), (0.086, 0.055, 0), (0.086, 0.085, 0),
         (0.07, 0.09, 0), (0.07, 0.12, 0), (0.086, 0.125, 0), (0.086, 0.15, 0), (0.06, 0.16, 0),
         (0.05, 0.20, 0), (0.0, 0.20, 0)]
    out.append(lathe_at("Abutment", P, [black], M, steps=48, bevel=0.003))
    # rubber dust boot (small bellows) over the rod
    P = [(0.0, 0.19, 0), (0.05, 0.19, 0), (0.048, 0.22, 0), (0.038, 0.245, 0), (0.046, 0.27, 0),
         (0.033, 0.295, 0), (0.040, 0.32, 0), (0.026, 0.345, 0), (0.024, 0.37, 0), (0.0, 0.37, 0)]
    out.append(lathe_at("Boot", P, [rubber], M, steps=40, angle=55))
    # sliding steel rod
    P = [(0.0, 0.35, 0), (0.017, 0.35, 0), (0.017, 0.56, 0), (0.0, 0.56, 0)]
    out.append(lathe_at("Rod", P, [rod_m], M, steps=24))
    # plastic eye end: shank + ring with its axis perpendicular to the cable (lying flat)
    P = [(0.0, 0.53, 0), (0.032, 0.53, 0), (0.036, 0.55, 0), (0.036, 0.63, 0), (0.0, 0.63, 0)]
    out.append(lathe_at("EyeShank", P, [black], M, steps=32, bevel=0.003))
    Me = M @ Matrix.Translation((0, 0, 0.70)) @ Matrix.Rotation(eye_rot, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
    P = [(0.042, -0.034, 0), (0.078, -0.034, 0), (0.088, -0.024, 0), (0.088, 0.024, 0), (0.078, 0.034, 0),
         (0.042, 0.034, 0)]
    out.append(lathe_at("EyeRing", P, [black], Me, steps=48, bevel=0.003))
    # pressed metal bush in the eye
    P = [(0.030, -0.038, 0), (0.043, -0.038, 0), (0.043, 0.038, 0), (0.030, 0.038, 0)]
    out.append(lathe_at("EyeBush", P, [bush_m], Me, steps=40))
    return out


def bulkhead_clip(M, black, rubber):
    """winged plastic clip with a rubber grommet, around the sheath (local Z along the cable)."""
    out = []
    P = [(RS - 0.004, -0.06, 0), (0.07, -0.06, 0), (0.078, -0.05, 0), (0.078, 0.05, 0), (0.07, 0.06, 0),
         (RS - 0.004, 0.06, 0)]
    out.append(lathe_at("Grommet", P, [rubber], M, steps=40, angle=50))
    P = [(0.07, -0.022, 0), (0.12, -0.022, 0), (0.125, -0.015, 0), (0.125, 0.015, 0), (0.12, 0.022, 0), (0.07, 0.022, 0)]
    out.append(lathe_at("ClipRing", P, [black], M, steps=48))
    bm = bmesh.new()
    for s in (-1, 1):
        C.box_bm(bm, 0.11, 0.03, 0.04, center=(s * 0.16, 0, 0.0), matrix=M)
        C.box_bm(bm, 0.03, 0.05, 0.07, center=(s * 0.205, 0, 0.0), matrix=M)
    out.append(fin(C.mesh_obj("ClipWings", bm, [black]), bevel=0.006))
    return out


def cable(name, pts, sh_m, black, zinc, rubber, rod_m, bush_m, clip_at):
    # lift the sheath where the bulkhead clip sits (the clip is fatter than the cable)
    i = int(len(pts) * clip_at)
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    zc = 0.125
    pts = [Vector((p.x, p.y, max(p.z, RS + (zc - RS) * (1 - C.smoothstep(0.12, 0.55, abs(s - L[i]))))))
           for p, s in zip(pts, L)]
    out = [sheath(name, pts, sh_m)]
    # ends
    t0 = (pts[0] - pts[1]).normalized()
    t1 = (pts[-1] - pts[-2]).normalized()
    out += end_fitting(axis_matrix(pts[0], t0), black, zinc, rubber, rod_m, bush_m, eye_rot=math.pi / 2)
    out += end_fitting(axis_matrix(pts[-1], t1), black, zinc, rubber, rod_m, bush_m, eye_rot=math.pi / 2)
    # bulkhead clip, wings lying flat (perpendicular to Z world)
    T = (pts[i + 1] - pts[i - 1]).normalized()
    M = axis_matrix(pts[i], T)
    # roll so that the wings lie horizontal
    x_local = (M.to_3x3() @ Vector((1, 0, 0)))
    want = T.cross(Vector((0, 0, 1))).normalized()
    ang = math.atan2(x_local.cross(want).dot(T), x_local.dot(want))
    M = M @ Matrix.Rotation(ang, 4, "Z")
    out += bulkhead_clip(M, black, rubber)
    return out


def build():
    sh_m = C.principled("SheathPE", (0.020, 0.020, 0.021), rough=0.36, Coat_Weight=0.15)
    C.add_noise_bump(sh_m, scale=420, strength=0.05, distance=0.0004, rough_var=0.05)
    black = C.mat_black_plastic("FittingPA", rough=0.48, color=0.03)
    zinc = C.principled("Ferrule", (0.62, 0.62, 0.60), metallic=1.0, rough=0.28)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005, rough_var=0.05)
    rubber = C.mat_rubber("BootRubber")
    rod_m = C.principled("RodSteel", (0.72, 0.72, 0.73), metallic=1.0, rough=0.16)
    bush_m = C.principled("BushBrass", (0.55, 0.52, 0.45), metallic=1.0, rough=0.3)
    objs = []
    # two cables coiled side by side, ends staggered
    base = coil_path(1.12, 1.78, math.radians(200), 1.0, 0.85, 1.6)
    N = len(base)
    p1 = lift_ends(base[0:N - 9])
    p2 = lift_ends(offset_path(base, 0.135)[7:N])
    objs += cable("Sheath1", p1, sh_m, black, zinc, rubber, rod_m, bush_m, 0.34)
    objs += cable("Sheath2", p2, sh_m, black, zinc, rubber, rod_m, bush_m, 0.52)
    C.transform_all(objs, Matrix.Rotation(math.radians(15), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("cavi-cambio", objs, "cavi-cambio.py",
            "pair of gear shift cables: black sheathed Bowden cables loosely coiled, end fittings with "
            "ferrules, rubber boots and plastic eyelets, bulkhead clips",
            az=20, el=48, lens=70, fill=0.86, **kw)
