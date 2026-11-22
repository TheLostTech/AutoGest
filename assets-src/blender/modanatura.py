"""Side body moulding (door protection strip), generic small hatchback: a long black
grained-plastic strip with a softly crowned face, a narrow satin rubbing rib, rounded
tapered ends and a gentle bow that follows the door; on the back, grey foam tape with
its red release liner and four white nylon fir-tree clips on T-bases. Laid diagonally,
face up, resting on its clips so the clips show underneath.
Local frame: length along X, width along Y, face up (+Z), back on z = 0."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

L = 0.92        # length
HW = 0.024      # half width
H = 0.0105      # crown height
LE = 0.045      # length of the rounded taper at each end
BOW = 0.045     # plan bow (m per m^2)
CLIPS = (-0.36, -0.12, 0.12, 0.36)


def yb(x):
    return BOW * x * x


def taper(x):
    d = L / 2 - abs(x)
    if d >= LE:
        return 1.0
    t = max(d / LE, 0.0)
    return max(math.sqrt(max(1 - (1 - t) ** 2, 0.0)), 0.025)


def section(f, n=44):
    """Closed section (a = across, b = up): flat back, crowned face."""
    hw = HW * f
    h = H * (0.35 + 0.65 * f)
    pts = []
    for k in range(n + 1):
        a = hw - 2 * hw * k / n
        u = abs(a) / hw
        b = h * max(1 - u ** 2.6, 0.0) ** (1 / 2.6)
        pts.append((a, b))
    # flat back with a small chamfer at both edges
    pts.append((-hw * 0.97, -0.0004))
    pts.append((hw * 0.97, -0.0004))
    return pts


def xs():
    out = []
    N = 260
    for k in range(N + 1):
        t = k / N
        # denser near the ends
        u = 0.5 - 0.5 * math.cos(math.pi * t)
        out.append(-L / 2 + L * (0.5 * t + 0.5 * u))
    return out


def strip(mat):
    frames = []
    for x in xs():
        f = taper(x)
        Pp = Vector((x, yb(x), 0.0))
        T = Vector((1, 2 * BOW * x, 0)).normalized()
        U = Vector((0, 0, 1)).cross(T).normalized()
        frames.append((Pp, U, Vector((0, 0, 1)), section(f)))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Strip", bm, [mat])
    return C.finalize(ob, angle=50)


def rib(mat):
    """Narrow satin rubbing rib along the crown."""
    lim = L / 2 - LE * 1.1
    xx = [x for x in xs() if abs(x) < lim]
    frames = []
    for x in xx:
        e = math.sqrt(max(1 - (abs(x) / lim) ** 12, 0.0)) * 0.97 + 0.03
        Pp = Vector((x, yb(x) - 0.004, H - 0.0007 - 0.0012 * (1 - e)))
        T = Vector((1, 2 * BOW * x, 0)).normalized()
        U = Vector((0, 0, 1)).cross(T).normalized()
        sec = [(0.0034 * math.cos(math.pi * k / 12), 0.0016 * e * math.sin(math.pi * k / 12)) for k in range(13)]
        sec += [(-0.0034, -0.0006), (0.0034, -0.0006)]
        frames.append((Pp, U, Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    return C.finalize(C.mesh_obj("Rib", bm, [mat]), angle=60)


def tape(foam, liner):
    out = []
    xs_ = [x for x in xs() if abs(x) < L / 2 - LE * 0.55]
    for (zz, th, w, m, nm) in ((-0.0004, 0.0011, 0.034, foam, "Foam"), (-0.0015, 0.00025, 0.036, liner, "Liner")):
        pts = [Vector((x, yb(x), zz)) for x in xs_]
        fr = P.path_frames(pts, (0, 0, 1))
        sec = P.rrect(-w / 2, w / 2, -th, 0.0, min(th * 0.45, 0.0003), seg=2)
        out.append(P.tube_obj(nm, fr, sec, [m], smooth_angle=60))
    return out


def clips(nylon, mat):
    out = []
    for x in CLIPS:
        y = yb(x)
        ang = math.atan(2 * BOW * x)
        M = Matrix.Translation((x, y, -0.0016)) @ Matrix.Rotation(ang, 4, "Z")
        # moulded T-rail on the strip back
        bm = bmesh.new()
        C.box_bm(bm, 0.026, 0.016, 0.0028, center=(0, 0, -0.0010))
        rail = C.mesh_obj("Rail", bm, [mat])
        C.add_bevel(rail, 0.0006, segments=1, angle=30)
        rail.matrix_world = M
        out.append(C.finalize(rail, angle=35))
        # clip: T-base, flange, fir-tree stem
        bm = bmesh.new()
        C.box_bm(bm, 0.016, 0.010, 0.0024, center=(0, 0, -0.0036))
        base = C.mesh_obj("ClipBase", bm, [nylon])
        C.add_bevel(base, 0.0006, segments=1, angle=30)
        base.matrix_world = M
        out.append(C.finalize(base, angle=35))
        prof = [(0.0, -0.0048, 0), (0.0068, -0.0048, 0), (0.0068, -0.0062, 0), (0.0030, -0.0068, 0)]
        z = -0.0072
        while z > -0.0150:
            prof += [(0.0026, z, 0), (0.0046, z - 0.0006, 0), (0.0026, z - 0.0022, 0)]
            z -= 0.0022
        prof += [(0.0020, -0.0160, 0), (0.0, -0.0164, 0)]
        st = C.lathe("ClipStem", prof, [nylon], steps=36)
        st.matrix_world = M
        out.append(C.finalize(st, angle=40))
    return out


def build():
    black = P.textured_black("MouldingPP", rough=0.55, v=0.024)
    satin = C.mat_black_plastic("RubRib", rough=0.32, color=0.03, tex=False)
    foam = C.principled("TapeFoam", (0.32, 0.32, 0.33), rough=0.9)
    C.add_noise_bump(foam, scale=1200, strength=0.3, distance=0.0003)
    liner = C.principled("TapeLiner", C.srgb("#C0262B"), rough=0.35)
    nylon = C.principled("Nylon", (0.82, 0.80, 0.74), rough=0.5, Subsurface_Weight=0.15)
    objs = [strip(black), rib(satin)]
    objs += tape(foam, liner)
    objs += clips(nylon, black)
    C.transform_all(objs, Matrix.Rotation(math.radians(77), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("modanatura", objs, "modanatura.py",
            "side body moulding (generic small hatchback): long black grained plastic protection strip with tapered "
            "ends, foam tape with red liner and white nylon clips on the back",
            az=8, el=22, lens=70, fill=0.92, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
