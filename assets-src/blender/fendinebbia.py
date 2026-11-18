"""Front fog lamp: round clear polycarbonate lens in a black plastic housing with a raised
bezel, faceted chrome reflector with the bulb and its chrome shield cap visible through
the lens, three mounting tabs with steel sleeves, bulb socket with bayonet lugs and a
connector shroud at the back."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
RL = 0.415            # lens radius
FWD = Matrix.Rotation(math.radians(90), 4, "X")    # local +Z (lamp front) -> world -Y, local +Y -> world +Z


# ----------------------------------------------------------------- helpers
def oval(w, h, n=2.0, N=N):
    pts = []
    for k in range(N):
        a = TAU * k / N
        c, s = math.cos(a), math.sin(a)
        pts.append((w / 2 * math.copysign(abs(c) ** (2 / n), c), h / 2 * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def resample(poly, n):
    L = [0.0]
    P = poly + [poly[0]]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + math.dist(a, b))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


def loft(name, frames, mat, cap=True):
    bm = bmesh.new()
    C.sweep(bm, frames, cap=cap)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def frame_matrix(P, X, Z):
    X, Z = X.normalized(), Z.normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P.x), (X.y, Y.y, Z.y, P.y), (X.z, Y.z, Z.z, P.z), (0, 0, 0, 1)))


def path_pts(start, d, n, segs, step=0.02):
    """Planar pipe centre-line: segs = [('L', len) | ('A', radius, deg)] bending toward n."""
    P = Vector(start)
    d = Vector(d).normalized()
    n = Vector(n).normalized()
    b = d.cross(n).normalized()
    pts = [(P.copy(), d.copy())]
    for s in segs:
        if s[0] == "L":
            k = max(1, int(s[1] / step))
            for i in range(1, k + 1):
                pts.append((P + d * (s[1] * i / k), d.copy()))
            P = P + d * s[1]
        else:
            R, ang = s[1], math.radians(s[2])
            Cc = P + n * R
            k = max(2, int(R * abs(ang) / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, b)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, b)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts, b


def pipe(name, pts, b, r, mat, wall=0.009):
    sec = circle_pts(0, 0, r, 48)
    fr = [(P, b, t.cross(b), sec) for (P, t) in pts]
    ob = loft(name, fr, mat, cap=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def tube(name, pts, r, mat, res=3, caps=True):
    """Smooth bezier tube through pts (auto handles)."""
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


def boxes(name, specs, mat, bevel=0.01, holes=(), seg=2, M=None):
    """specs: [(sx, sy, sz, center[, matrix])]; holes: [(r, z0, z1, matrix)] boolean cylinders."""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, z0, z1, HM) in holes:
            C.cyl_bm(cb, r, z0, z1, seg=32, matrix=HM)
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2):
    """Extrude a 2D polygon along local Z, optional boolean holes [(r, cx, cy)] through it."""
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (z0, z1)]
    ob = loft(name, fr, mat)
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, cx, cy) in holes:
            C.cyl_bm(cb, r, z0 - 0.5, z1 + 0.5, seg=32, matrix=T((cx, cy, 0)))
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


# ----------------------------------------------------------------- parts
def housing(black):
    out = []
    P = [(0.47, 0.005, 0), (0.472, -0.05, 0), (0.46, -0.13, 0), (0.435, -0.25, 0), (0.39, -0.35, 0), (0.30, -0.43, 0),
         (0.18, -0.47, 0), (0.0, -0.48, 0)]
    ob = C.lathe("Housing", P, [black], steps=128, closed=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.02
    so.offset = 1
    ob.matrix_world = FWD
    C.add_bevel(ob, 0.004, segments=2, angle=40)
    out.append(C.finalize(ob, angle=40))
    # front bezel ring holding the lens
    B = [(RL - 0.012, 0.012, 0), (0.47, 0.005, 0), (0.49, 0.02, 0), (0.49, 0.045, 0), (0.475, 0.06, 0), (RL + 0.015, 0.06, 0),
         (RL - 0.012, 0.045, 0)]
    out.append(lathe_at("Bezel", B, [black], FWD, steps=128, bevel=0.003))
    return out


def lens(clear):
    def zf(r):
        return 0.058 - 0.13 * r * r
    rs = [0.0, 0.08, 0.16, 0.24, 0.30, 0.36, 0.40, RL]
    P = [(r, zf(r), 0) for r in rs]
    P += [(RL, zf(RL) - 0.022, 0)]
    P += [(r, zf(r) - 0.02, 0) for r in reversed(rs[:-1])]
    return lathe_at("Lens", P, [clear], FWD, steps=128, angle=60)


def reflector(chrome):
    R, f = 0.405, 0.205
    prof = []
    for i in range(8):
        r = 0.06 + (R - 0.06) * i / 7
        prof.append((r, (r * r - R * R) / (4 * f), 0))
    ob = C.lathe("Reflector", prof, [chrome], steps=18, closed=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.006
    so.offset = -1
    ob.matrix_world = FWD
    out = [C.finalize(ob, angle=8)]
    # bulb collar in the apex
    z0 = (0.06 ** 2 - R * R) / (4 * f)
    out.append(lathe_at("Collar", [(0.0, z0 - 0.03, 0), (0.062, z0 - 0.03, 0), (0.062, z0 + 0.005, 0), (0.04, z0 + 0.01, 0),
                                   (0.0, z0 + 0.01, 0)], [chrome], FWD, steps=48))
    return out, z0


def bulb(z0, glass, chrome, tip_m, filament):
    out = []
    zb = z0 + 0.01
    G = [(0.0, zb + 0.15, 0), (0.016, zb + 0.147, 0), (0.026, zb + 0.13, 0), (0.028, zb + 0.10, 0), (0.028, zb + 0.0, 0),
         (0.0, zb + 0.0, 0)]
    out.append(lathe_at("BulbGlass", G, [glass], FWD, steps=48, angle=60))
    out.append(lathe_at("BulbTip", [(0.0, zb + 0.158, 0), (0.018, zb + 0.152, 0), (0.026, zb + 0.135, 0), (0.026, zb + 0.128, 0),
                                    (0.0, zb + 0.128, 0)], [tip_m], FWD, steps=48))
    # filament coil
    cu = bpy.data.curves.new("Filament", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0022
    sp = cu.splines.new("POLY")
    n = 120
    sp.points.add(n)
    for i in range(n + 1):
        a = TAU * 9 * i / n
        sp.points[i].co = (0.006 * math.cos(a), 0.006 * math.sin(a), zb + 0.06 + 0.04 * i / n, 1)
    ob = C.link(bpy.data.objects.new("Filament", cu))
    cu.materials.append(filament)
    ob.matrix_world = FWD
    out.append(C.finalize(ob, angle=50))
    # chrome shield cup in front of the bulb on a thin wire bracket
    S = [(0.0, zb + 0.20, 0), (0.05, zb + 0.198, 0), (0.07, zb + 0.18, 0), (0.072, zb + 0.16, 0), (0.066, zb + 0.16, 0),
         (0.064, zb + 0.178, 0), (0.046, zb + 0.192, 0), (0.0, zb + 0.193, 0)]
    out.append(lathe_at("Shield", S, [chrome], FWD, steps=64, angle=50))
    pts = [(0.0, -(zb + 0.17), 0.068), (0.0, -(zb + 0.12), 0.10), (0.0, -(zb + 0.06), 0.11), (0.0, -(zb + 0.02), 0.12)]
    out.append(tube("ShieldWire", pts, 0.004, chrome, res=2))
    return out


def tabs(black, steel):
    out = []
    for deg in (18, 162, 270):
        th = math.radians(deg)
        M = FWD @ Matrix.Rotation(th, 4, "Z")
        poly = resample(hull2d(circle_pts(0.40, 0, 0.10, 32) + circle_pts(0.58, 0, 0.06, 32)), 96)
        out.append(prism("Tab", poly, -0.10, -0.055, black, M=M, bevel=0.006, holes=[(0.028, 0.58, 0.0)]))
        out.append(boxes("TabRib", [(0.12, 0.022, 0.07, (0.48, 0.0, -0.13))], black, bevel=0.006, M=M))
        out.append(lathe_at("TabSleeve", [(0.016, -0.105, 0), (0.028, -0.105, 0), (0.028, -0.05, 0), (0.016, -0.05, 0)],
                            [steel], M @ T((0.58, 0, 0)), steps=32))
    return out


def socket(black, rubber, pin_m):
    out = []
    S = [(0.0, -0.47, 0), (0.15, -0.47, 0), (0.15, -0.50, 0), (0.12, -0.51, 0), (0.12, -0.58, 0), (0.10, -0.60, 0),
         (0.0, -0.60, 0)]
    out.append(lathe_at("Socket", S, [black], FWD, steps=96, bevel=0.004))
    for k in range(3):
        M = FWD @ Matrix.Rotation(TAU * k / 3 + 0.3, 4, "Z")
        out.append(boxes("Lug", [(0.07, 0.05, 0.03, (0.15, 0.0, -0.53))], black, bevel=0.006, M=M))
    out.append(lathe_at("Oring", [(0.15, -0.475, 0), (0.17, -0.475, 0), (0.17, -0.462, 0), (0.15, -0.462, 0)], [rubber], FWD, steps=64))
    # connector shroud, opening toward the back (-local Z)
    cz = -0.66
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.10, 0.14, center=(0.0, 0.0, cz))
    sh = C.mesh_obj("Shroud", bm, [black])
    sh.matrix_world = FWD
    cb = bmesh.new()
    C.box_bm(cb, 0.12, 0.065, 0.14, center=(0.0, 0.0, cz - 0.03))
    cut = C.mesh_obj("ShroudCut", cb, [black])
    cut.matrix_world = FWD
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    out.append(boxes("Pins", [(0.016, 0.006, 0.07, (sx * 0.03, 0.0, cz + 0.0)) for sx in (-1, 1)], pin_m, bevel=0.0, M=FWD))
    out.append(boxes("Latch", [(0.05, 0.03, 0.06, (0.0, 0.06, cz - 0.02))], black, bevel=0.005, M=FWD))
    return out


def build():
    black = C.mat_black_plastic("HousingPP", rough=0.42, color=0.025)
    clear = C.mat_clear("LensPC")
    glass = C.mat_clear("Glass", ior=1.52)
    chrome = C.mat_chrome()
    tip_m = C.principled("BulbTipBlack", (0.03, 0.03, 0.035), metallic=0.6, rough=0.3)
    filament = C.principled("Filament", (0.55, 0.45, 0.35), metallic=1.0, rough=0.35)
    steel = C.principled("ZincSteel", (0.6, 0.61, 0.62), metallic=1.0, rough=0.26)
    rubber = C.mat_rubber("Oring")
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    objs = housing(black)
    objs.append(lens(clear))
    refl, z0 = reflector(chrome)
    objs += refl
    objs += bulb(z0, glass, chrome, tip_m, filament)
    objs += tabs(black, steel)
    objs += socket(black, rubber, pin_m)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("fendinebbia", objs, "fendinebbia.py",
            "car front fog lamp: round clear lens in black plastic housing, faceted chrome reflector with bulb and "
            "shield cap, three mounting tabs, bulb socket with connector at the back",
            az=32, el=14, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
