"""Plastic fuel tank (black HDPE, blow-moulded): irregular saddle shape straddling a
centre tunnel, deeper left lobe with the pump opening and its locking ring, stepped
lower right lobe with the filler-neck stub and vent nipple, moulded ribs and strap
grooves, pinch-off flange around the sides, rollover valves on top."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
A0 = 1.0        # half width (X)
Y0 = 0.56       # half depth (Y)
RF = 0.07       # edge fillet at the front/back walls
ZF = 0.19       # pinch-off flange height
PUMP = (-0.55, 0.02)


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


# ----------------------------------------------------------------- shape
def zt(x):
    t = C.smoothstep(0.08, 0.36, x)
    z = 0.44 - 0.08 * t
    for xr in (-0.92, -0.80, 0.56, 0.70, 0.84):
        z += 0.013 * math.exp(-((x - xr) / 0.017) ** 2)
    return z


def zb(x):
    z = 0.02 - 0.08 * (1 - C.smoothstep(-0.62, -0.30, x))
    tun = 1 - C.smoothstep(0.16, 0.32, abs(x))
    return z + (0.215 - z) * tun


def groove(y):
    return sum(0.026 * math.exp(-((y - yg) / 0.028) ** 2) for yg in (-0.21, 0.23))


def section(y, nsec=200, ne=6.0):
    d = abs(y) - (Y0 - RF)
    f = 0.0
    if d > 0:
        f = RF * (1 - math.sqrt(max(0.0, 1 - (d / RF) ** 2)))
    g = groove(y)
    a = A0 - f - g
    pts = []
    for k in range(nsec):
        ang = TAU * k / nsec
        c, s = math.cos(ang), math.sin(ang)
        cx = math.copysign(abs(c) ** (2 / ne), c)
        cz = math.copysign(abs(s) ** (2 / ne), s)
        x = a * cx
        top, bot = zt(x) - g - f, zb(x) + g + f
        zm, hh = (top + bot) / 2, max(0.004, (top - bot) / 2)
        pts.append((x, zm + cz * hh))
    return pts


# ----------------------------------------------------------------- parts
def shell(mat):
    M_ = 150
    fr = []
    for i in range(M_ + 1):
        y = -Y0 * math.cos(math.pi * i / M_)
        fr.append((Vector((0, y, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), section(y)))
    ob = loft("Tank", fr, mat)
    C.add_bevel(ob, 0.006, segments=2, angle=50)
    return C.finalize(ob, angle=40)


def pinch_flange(mat):
    out = []
    for sx in (-1, 1):
        x0, x1 = 0.36, A0 + 0.035
        out.append(boxes("Flange", [(x1 - x0, 2 * Y0 + 0.05, 0.014, (sx * (x0 + x1) / 2, 0, ZF))], mat, bevel=0.012))
    return out


def pump_opening(black, ring_m, dark):
    out = []
    z0 = zt(PUMP[0]) - 0.02
    P = [(0.0, 0.30, 1), (0.158, 0.30, 1), (0.158, z0 + 0.065, 0), (0.205, z0 + 0.065, 0), (0.212, z0 + 0.055, 0),
         (0.212, z0 - 0.04, 0), (0.0, z0 - 0.04, 0)]
    out.append(lathe_at("PumpCollar", P, [black, dark], T((PUMP[0], PUMP[1], 0)), steps=128, bevel=0.004))

    def tabs(r, z, t):
        if r < 0.24:
            return r
        v = math.cos(10 * t)
        return r + 0.018 * max(0.0, v * 3 - 2)
    R = [(0.212, z0 + 0.012, 0), (0.25, z0 + 0.012, 0), (0.25, z0 + 0.052, 0), (0.24, z0 + 0.062, 0), (0.212, z0 + 0.062, 0)]
    out.append(lathe_at("LockRing", R, [ring_m], T((PUMP[0], PUMP[1], 0)), steps=160, bevel=0.003))
    # a few raised moulding pads around the opening
    for k in range(3):
        th = TAU * k / 3 + 0.4
        x, y = PUMP[0] + 0.31 * math.cos(th), PUMP[1] + 0.31 * math.sin(th)
        out.append(boxes("Pad", [(0.07, 0.07, 0.03, (x, y, zt(x) - 0.004))], black, bevel=0.01))
    return out


def filler(black, dark):
    out = []
    pts, b = path_pts((0.84, 0.30, 0.28), (0.5, 0, 0.866), (1, 0, -0.6), [("L", 0.20), ("A", 0.20, 18), ("L", 0.10)])
    out.append(pipe("FillerNeck", pts, b, 0.065, black, wall=0.012))
    for i in (-3, -7, 4):
        P, t = pts[i]
        out.append(lathe_at("Bead", [(0.06, -0.008, 0), (0.074, -0.004, 0), (0.074, 0.004, 0), (0.06, 0.008, 0)],
                            [black], frame_matrix(P, b, t), steps=64))
    # weld boss where the neck meets the shell
    out.append(lathe_at("NeckBoss", [(0.0, 0.0, 0), (0.12, 0.0, 0), (0.10, 0.06, 0), (0.0, 0.06, 0)], [black],
                        T((0.86, 0.30, zt(0.86) - 0.04)), steps=64, bevel=0.01))
    # vent nipple next to the neck
    pts, b = path_pts((0.70, 0.44, zt(0.70) - 0.01), (0, 0, 1), (1, 0, 0), [("L", 0.05), ("A", 0.04, 90), ("L", 0.09)])
    out.append(pipe("Vent", pts, b, 0.017, black, wall=0.006))
    return out


def valves(black, grey):
    out = []
    for (x, y) in ((0.58, -0.30), (-0.20, 0.34)):
        z = zt(x) - 0.01
        P = [(0.0, z, 0), (0.065, z, 0), (0.065, z + 0.03, 0), (0.05, z + 0.05, 0), (0.0, z + 0.05, 0)]
        out.append(lathe_at("Valve", P, [grey], T((x, y, 0)), steps=64, bevel=0.004))
        pts, b = path_pts((x + 0.02, y, z + 0.04), (0, 0, 1), (1, 0, 0), [("L", 0.02), ("A", 0.03, 90), ("L", 0.07)])
        out.append(pipe("ValveNip", pts, b, 0.012, black, wall=0.004))
    return out


def build():
    hdpe = C.mat_black_plastic("HDPE", rough=0.50, color=0.017)
    nt = hdpe.node_tree
    fine = next(n for n in nt.nodes if n.type == "BUMP")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 12.0
    nz.inputs["Detail"].default_value = 3.0
    coarse = nt.nodes.new("ShaderNodeBump")
    coarse.inputs["Strength"].default_value = 0.06
    coarse.inputs["Distance"].default_value = 0.004
    nt.links.new(nz.outputs["Fac"], coarse.inputs["Height"])
    nt.links.new(coarse.outputs["Normal"], fine.inputs["Normal"])
    ring_m = C.mat_black_plastic("RingPOM", rough=0.40, color=0.10)
    dark = C.principled("Inside", (0.006, 0.006, 0.006), rough=0.7)
    objs = [shell(hdpe)]
    objs += pinch_flange(hdpe)
    objs += pump_opening(hdpe, ring_m, dark)
    objs += filler(hdpe, dark)
    objs += valves(hdpe, ring_m)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("serbatoio", objs, "serbatoio.py",
            "plastic car fuel tank: black HDPE saddle-shaped tank with moulded ribs and strap grooves, pump opening "
            "with locking ring, filler-neck stub and vent nipples",
            az=28, el=32, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
