"""Body computer / fuse box (BCM): black polypropylene housing; on top, four fuse-holder
strips filled with colour-coded mini blade fuses (a few empty slots), two maxi fuses,
a block of micro relays and a white fuse puller; on the front face five multi-pin
connector sockets in different colours with coding ribs, pin fields and locking ramps;
mounting tabs with steel sleeves on the ends."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
L, W, H = 1.30, 0.86, 0.40       # housing (X, Y, Z)
YF = -W / 2                      # connector face


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


# ----------------------------------------------------------------- materials
def mat_fuse(name, rgb):
    m = C.principled(name, rgb + (1,), rough=0.22)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Transmission Weight", 0.45)
    C._set(b, "Subsurface Weight", 0.2)
    C._set(b, "Subsurface Radius", (0.02, 0.02, 0.02))
    return m


# ----------------------------------------------------------------- parts
def housing(black):
    out = []
    out.append(boxes("Housing", [(L, W, H - 0.04, (0, 0, (H - 0.04) / 2))], black, bevel=0.02, seg=3))
    # top cover-seat rim, slightly proud
    bm = bmesh.new()
    C.box_bm(bm, L + 0.016, W + 0.016, 0.05, center=(0, 0, H - 0.04))
    rim = C.mesh_obj("Rim", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, L - 0.05, W - 0.05, 0.2, center=(0, 0, H))
    cut = C.mesh_obj("RimCut", cb, [black])
    C.add_boolean(rim, cut)
    C.add_bevel(rim, 0.008, segments=2, angle=30)
    out.append(C.finalize(rim, angle=35, remove=[cut]))
    # deck inside the rim
    out.append(boxes("Deck", [(L - 0.05, W - 0.05, 0.02, (0, 0, H - 0.05))], black, bevel=0.0))
    # moulded ribs on the ends and the back
    specs = []
    for sx in (-1, 1):
        for y in (-0.25, 0.0, 0.25):
            specs.append((0.03, 0.04, H - 0.12, (sx * (L / 2 + 0.008), y, (H - 0.12) / 2 + 0.03)))
    out.append(boxes("EndRibs", specs, black, bevel=0.008))
    return out


def tabs(black, steel):
    out = []
    for sx, y in ((-1, 0.22), (1, -0.18), (1, 0.26)):
        x = sx * (L / 2 + 0.075)
        out.append(boxes("Tab", [(0.17, 0.13, 0.035, (x - sx * 0.02, y, 0.0175)),
                                 (0.04, 0.10, 0.12, (sx * (L / 2 + 0.015), y, 0.07))], black, bevel=0.008,
                         holes=[(0.03, -0.1, 0.2, T((x + sx * 0.01, y, 0)))]))
        out.append(lathe_at("Sleeve", [(0.020, -0.004, 0), (0.031, -0.004, 0), (0.031, 0.042, 0), (0.020, 0.042, 0)],
                            [steel], T((x + sx * 0.01, y, 0)), steps=32))
    return out


def fuses(black, dark, palette):
    out = []
    rnd = random.Random(5)
    zt = H - 0.04
    rows = [-0.27, -0.12, 0.03, 0.18]
    x0, x1 = -0.60, 0.16
    pitch = 0.054
    nper = int((x1 - x0) / pitch)
    by_mat = {}
    holes = []
    for r, y in enumerate(rows):
        out.append(boxes("FuseStrip", [(x1 - x0 + 0.03, 0.075, 0.035, ((x0 + x1) / 2, y, zt + 0.0175))], black, bevel=0.006))
        for i in range(nper):
            x = x0 + pitch * (i + 0.5)
            if rnd.random() < 0.10:
                holes.append((x, y))
                continue
            mi = rnd.choice((0, 0, 1, 1, 1, 2, 2, 3, 4, 5))
            by_mat.setdefault(mi, []).extend([
                (0.036, 0.011, 0.045, (x, y, zt + 0.035 + 0.0225)),
                (0.040, 0.016, 0.012, (x, y, zt + 0.035 + 0.045 + 0.004))])
    for mi, specs in by_mat.items():
        out.append(boxes("Fuses%d" % mi, specs, palette[mi], bevel=0.0025, seg=1))
    if holes:
        out.append(boxes("EmptySlots", [(0.030, 0.008, 0.004, (x + sx * 0.0, y, zt + 0.036)) for (x, y) in holes for sx in (0,)],
                         dark, bevel=0.0))
    # two maxi fuses
    for k, (x, mi) in enumerate(((0.24, 3), (0.34, 5))):
        out.append(boxes("MaxiSeat", [(0.10, 0.06, 0.03, (x, -0.29, zt + 0.015))], black, bevel=0.006))
        out.append(boxes("Maxi", [(0.075, 0.022, 0.07, (x, -0.29, zt + 0.03 + 0.035)), (0.082, 0.03, 0.016, (x, -0.29, zt + 0.10))],
                         palette[mi], bevel=0.004))
    return out


def relays(black, grey, white):
    out = []
    zt = H - 0.04
    spots = [(0.27, -0.13, black), (0.42, -0.13, black), (0.27, 0.03, grey), (0.42, 0.03, black), (0.42, 0.20, black)]
    for x, y, m in spots:
        out.append(boxes("Relay", [(0.12, 0.13, 0.14, (x, y, zt + 0.07)), (0.03, 0.12, 0.012, (x - 0.035, y, zt + 0.145))],
                         m, bevel=0.009))
    out.append(boxes("Puller", [(0.035, 0.16, 0.035, (0.53, 0.0, zt + 0.0175)), (0.05, 0.03, 0.05, (0.53, -0.08, zt + 0.025))],
                     white, bevel=0.006))
    return out


def connector(x0, x1, z0, z1, shell_m, pin_m, rows, depth=0.12):
    out = []
    cx = (x0 + x1) / 2
    w, h = x1 - x0, z1 - z0
    yb = YF + 0.01
    yfr = YF - depth
    bm = bmesh.new()
    C.box_bm(bm, w, yb - yfr, h, center=(cx, (yb + yfr) / 2, (z0 + z1) / 2))
    sh = C.mesh_obj("Shroud", bm, [shell_m])
    cb = bmesh.new()
    t = 0.018
    C.box_bm(cb, w - 2 * t, depth, h - 2 * t, center=(cx, yfr + depth / 2 - 0.04, (z0 + z1) / 2))
    cut = C.mesh_obj("ShroudCut", cb, [shell_m])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    # mounting frame on the face + locking ramp + coding ribs
    specs = [(w + 0.04, 0.02, h + 0.03, (cx, YF - 0.005, (z0 + z1) / 2)),
             (0.08, 0.04, 0.02, (cx, yfr + 0.04, z1 + 0.008)),
             (0.08, 0.02, 0.03, (cx, yfr + 0.07, z1 + 0.013))]
    for k in range(2):
        specs.append((0.014, depth - 0.05, 0.022, (x0 + w * (0.3 + 0.4 * k), yfr + depth / 2, z1 - t - 0.01)))
    out.append(boxes("ConnDetail", specs, shell_m, bevel=0.003))
    floor = yfr + depth - 0.04
    bm = bmesh.new()
    pitch = 0.028
    for r in range(rows):
        z = (z0 + z1) / 2 + (r - (rows - 1) / 2) * 0.032
        nx = int((w - 2 * t - 0.02) / pitch)
        for i in range(nx):
            x = cx - (nx - 1) * pitch / 2 + i * pitch
            C.box_bm(bm, 0.009, 0.08, 0.009, center=(x, floor - 0.03, z))
    out.append(C.finalize(C.mesh_obj("Pins", bm, [pin_m]), angle=40))
    return out


def build():
    black = C.mat_black_plastic("PP", rough=0.50, color=0.03)
    dark = C.principled("Slot", (0.004, 0.004, 0.004), rough=0.8)
    grey = C.mat_black_plastic("GreyPA", rough=0.45, color=0.16)
    white = C.mat_black_plastic("NaturalPA", rough=0.45, color=0.62)
    blue = C.mat_black_plastic("BluePA", rough=0.45, color=0.02)
    C._set(next(n for n in blue.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Base Color", C.srgb("#3A5C88"))
    brown = C.mat_black_plastic("BrownPA", rough=0.45, color=0.02)
    C._set(next(n for n in brown.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Base Color", C.srgb("#5A3B26"))
    steel = C.principled("ZincSteel", (0.6, 0.61, 0.62), metallic=1.0, rough=0.26)
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    palette = [mat_fuse("FuseRed", C.srgb("#B42420")[:3]), mat_fuse("FuseBlue", C.srgb("#2A5BA8")[:3]),
               mat_fuse("FuseYellow", C.srgb("#D6AA22")[:3]), mat_fuse("FuseGreen", C.srgb("#2F8540")[:3]),
               mat_fuse("FuseTan", C.srgb("#C9A36B")[:3]), mat_fuse("FuseClear", (0.85, 0.85, 0.85))]
    objs = housing(black) + tabs(black, steel) + fuses(black, dark, palette) + relays(black, grey, white)
    zc0 = 0.07
    specs = [(-0.60, -0.30, black, 4), (-0.26, -0.05, grey, 3), (-0.01, 0.24, white, 4), (0.28, 0.44, blue, 2),
             (0.48, 0.60, brown, 2)]
    for x0, x1, m, rows in specs:
        h = 0.07 + rows * 0.034
        objs += connector(x0, x1, zc0, zc0 + h, m, pin_m, rows)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("body-computer", objs, "body-computer.py",
            "car body computer / fuse box: black housing with rows of colour-coded mini blade fuses, maxi fuses and "
            "relays on top, five multi-pin connector sockets on the front face",
            az=30, el=36, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
