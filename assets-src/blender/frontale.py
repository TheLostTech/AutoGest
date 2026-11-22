"""Front-end carrier (radiator support panel) of a generic modern small hatchback, removed
from the car. One-piece black glass-filled polypropylene moulding: deep upper cross member,
side posts and lower cross member framing the large radiator opening, all built as open
channels with W-truss stiffening ribs; headlamp mounting wings on both sides with
metal-insert screw bosses; zinc-plated bonnet latch with safety hook and release cable
in the middle of the upper beam, rubber bonnet bump stops, radiator mounting bushes.
Car front is -Y (the ribbed channel side faces forward)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

YB = 0.050        # back face of the base web
WEB = 0.004       # web thickness
WALL = 0.0035     # rib / wall thickness
ZI0, ZI1, XI = 0.085, 0.468, 0.36   # radiator opening


def outer_poly():
    half = [(0.0, 0.0), (0.40, 0.0), (0.452, 0.045), (0.462, 0.272), (0.628, 0.312), (0.664, 0.372),
            (0.660, 0.498), (0.622, 0.562), (0.30, 0.584), (0.0, 0.590)]
    r = [0, 0.03, 0.03, 0.02, 0.03, 0.03, 0.04, 0.05, 0.08, 0]
    pts = half[:-1] + [(-x, z) for (x, z) in reversed(half[1:])]
    rr = r[:-1] + list(reversed(r[1:]))
    poly = P.rounded(pts, rr, closed=True, seg=10)
    return P.resample(poly, 520, closed=True)


def inner_poly():
    pts = P.rounded([(-XI, ZI0), (XI, ZI0), (XI, ZI1), (-XI, ZI1)], [0.045] * 4, closed=True, seg=12)
    return P.resample(pts, 360, closed=True)


def wing_hole(sx):
    c = [(0.505, 0.345), (0.585, 0.362), (0.598, 0.43), (0.515, 0.43)]
    pts = [(sx * a, b) for (a, b) in (c if sx > 0 else c[::-1])]
    return P.resample(P.rounded(pts, [0.018] * 4, closed=True, seg=8), 80, closed=True)


def ztop(x):
    """Top outline height."""
    ax = abs(x)
    if ax < 0.30:
        return 0.590 - 0.006 * ax / 0.30
    return 0.584 - (0.584 - 0.562) * ((ax - 0.30) / 0.322) ** 1.5


def l3(q, y):
    return Vector((q.x, y, q.y))


def base_web(mat):
    bm = bmesh.new()
    P.prism_bm(bm, outer_poly(), l3, YB - WEB, YB)
    C.fix_normals(bm)
    ob = C.mesh_obj("Web", bm, [mat])
    cb = bmesh.new()
    P.prism_bm(cb, inner_poly(), l3, YB - 0.03, YB + 0.03)
    for sx in (-1, 1):
        P.prism_bm(cb, wing_hole(sx), l3, YB - 0.03, YB + 0.03)
    C.fix_normals(cb)
    cut = C.mesh_obj("Opening", cb, [mat])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(ob, 0.0012, segments=2, angle=40)
    return C.finalize(ob, angle=40, remove=[cut])


def wall(name, poly, mat, depth, closed=True):
    pts = [l3(q, YB - WEB * 0.5) for q in poly]
    fr = P.path_frames(pts, (0, -1, 0), closed=closed)
    sec = P.rrect(-WALL / 2, WALL / 2, 0.0, depth, 0.0012, seg=2)
    return P.tube_obj(name, fr, sec, [mat], closed=closed, cap=not closed, smooth_angle=45)


def ribs_bm(bm, segs, depth):
    for (a, b) in segs:
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        ang = math.atan2(d.y, d.x)
        mid = (a + b) / 2
        M = Matrix.Translation((mid.x, YB - WEB - depth / 2 + 0.0005, mid.y)) @ Matrix.Rotation(-ang, 4, "Y")
        C.box_bm(bm, L, depth, WALL * 0.85, matrix=M)


def zigzag(lo, hi, x0, x1, n):
    pts = []
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        pts.append((x, lo(x) if k % 2 == 0 else hi(x)))
    return list(zip(pts, pts[1:]))


def ribs(mat):
    out = []
    D = 0.040
    bm = bmesh.new()
    # upper cross member
    segs = zigzag(lambda x: ZI1 + 0.002, lambda x: ztop(x) - 0.003, -0.60, 0.60, 16)
    segs += [((x, ZI1 + 0.002), (x, ztop(x) - 0.003)) for x in (-0.60, 0.60)]
    # lower cross member
    segs += zigzag(lambda x: 0.003, lambda x: ZI0 - 0.002, -0.34, 0.34, 10)
    # side posts
    for sx in (-1, 1):
        pts = []
        n = 6
        for k in range(n + 1):
            z = 0.05 + (ZI1 - 0.05) * k / n
            xo = 0.452 + 0.010 * (z - 0.045) / 0.227 if z < 0.272 else 0.462
            pts.append((sx * (XI + 0.002) if k % 2 == 0 else sx * (xo - 0.003), z))
        segs += list(zip(pts, pts[1:]))
        # wing ribs: around the lightening hole
        segs += [((sx * 0.465, 0.30), (sx * 0.505, 0.345)), ((sx * 0.598, 0.43), (sx * 0.655, 0.47)),
                 ((sx * 0.515, 0.43), (sx * 0.50, ZI1 + 0.002)), ((sx * 0.585, 0.362), (sx * 0.64, 0.33))]
    ribs_bm(bm, segs, D)
    C.fix_normals(bm)
    ob = C.mesh_obj("Ribs", bm, [mat])
    C.add_bevel(ob, 0.0008, segments=1, angle=40)
    out.append(C.finalize(ob, angle=40))
    return out


def bosses(mat, insert):
    out = []
    spots = []
    for sx in (-1, 1):
        spots += [(sx * 0.488, 0.300), (sx * 0.640, 0.410), (sx * 0.560, 0.520), (sx * 0.410, 0.120)]
    for (x, z) in spots:
        ob = C.lathe("Boss", [(0.0045, 0.0, 1), (0.0105, 0.0, 0), (0.0105, 0.040, 0), (0.0085, 0.043, 0),
                              (0.0045, 0.043, 1), (0.0045, 0.0, 1)], [mat, insert], steps=40)
        ob.matrix_world = Matrix.Translation((x, YB - WEB, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
        out.append(C.finalize(ob, angle=40))
        ins = C.lathe("Insert", [(0.0, 0.040, 0), (0.0062, 0.040, 0), (0.0062, 0.0435, 0), (0.0032, 0.0435, 1),
                                 (0.0032, 0.030, 1), (0.0, 0.030, 1)], [insert, C.principled("BoreDark", (0.05, 0.045, 0.03), metallic=1, rough=0.5)], steps=40)
        ins.matrix_world = Matrix.Translation((x, YB - WEB, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
        out.append(C.finalize(ins, angle=40))
    return out


def latch(zinc, black, cable):
    out = []
    yf = YB - WEB - 0.040           # front edge of the channel walls
    bm = bmesh.new()
    C.box_bm(bm, 0.082, 0.004, 0.105, center=(0.0, yf - 0.002, ZI1 + 0.035))     # base plate
    C.box_bm(bm, 0.060, 0.030, 0.070, center=(0.0, yf - 0.019, ZI1 + 0.020))     # mechanism housing
    ob = C.mesh_obj("LatchPlate", bm, [zinc])
    cb = bmesh.new()
    C.box_bm(cb, 0.016, 0.05, 0.05, center=(0.0, yf - 0.02, ZI1 + 0.065))         # striker slot
    for dx in (-0.03, 0.03):
        C.cyl_bm(cb, 0.0045, -0.03, 0.03, seg=20, matrix=Matrix.Translation((dx, yf, ZI1 + 0.07)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    cut = C.mesh_obj("LatchCut", cb, [zinc])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    C.add_bevel(ob, 0.0015, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # dark slot interior
    bm = bmesh.new()
    C.box_bm(bm, 0.015, 0.002, 0.03, center=(0.0, yf - 0.0045, ZI1 + 0.058))
    out.append(C.finalize(C.mesh_obj("SlotBack", bm, [black]), angle=30))
    # bolt heads
    for dx in (-0.03, 0.03):
        hd = C.lathe("LatchBolt", [(0.0, 0.0, 0), (0.0075, 0.0, 0), (0.0075, 0.004, 0), (0.0065, 0.0052, 0), (0.0, 0.0055, 0)], [zinc], steps=6)
        hd.matrix_world = Matrix.Translation((dx, yf - 0.004, ZI1 + 0.07)) @ Matrix.Rotation(math.radians(90), 4, "X")
        C.add_bevel(hd, 0.0006, segments=1, angle=30)
        out.append(C.finalize(hd, angle=35))
    # safety hook: bent strip forward and up
    path = [Vector((0.022, yf - 0.034, ZI1 + 0.005)), Vector((0.022, yf - 0.060, ZI1 + 0.012)),
            Vector((0.022, yf - 0.075, ZI1 + 0.040)), Vector((0.022, yf - 0.066, ZI1 + 0.060))]
    path = P.bspline(path, 40)
    fr = P.path_frames(path, (1, 0, 0))
    out.append(P.tube_obj("SafetyHook", fr, P.rrect(-0.006, 0.006, -0.0015, 0.0015, 0.0008), [zinc], smooth_angle=50))
    # release cable: sheath along the beam, ending cut with a crimped ferrule
    pts = [Vector((0.03, yf - 0.02, ZI1 + 0.012)), Vector((0.09, yf - 0.024, ZI1 + 0.006)),
           Vector((0.20, yf - 0.012, ZI1 + 0.012)), Vector((0.31, yf - 0.010, ZI1 + 0.03)),
           Vector((0.38, yf - 0.04, ZI1 - 0.02)), Vector((0.36, yf - 0.09, ZI1 - 0.09))]
    pts = P.bspline(pts, 80)
    fr = P.path_frames(pts, (0, 0, 1))
    out.append(P.tube_obj("Cable", fr, P.circle(0.0035, 16), [cable], smooth_angle=60))
    end = pts[-1]
    tv = (pts[-1] - pts[-2]).normalized()
    fe = C.lathe("Ferrule", [(0.0, 0.0, 0), (0.0045, 0.0, 0), (0.0045, 0.014, 0), (0.0012, 0.014, 0), (0.0012, 0.026, 0), (0.0, 0.026, 0)], [zinc], steps=24)
    q = tv.to_track_quat("Z", "Y")
    fe.matrix_world = Matrix.Translation(end) @ q.to_matrix().to_4x4()
    out.append(C.finalize(fe, angle=40))
    return out


def bump_stops(rubber, mat):
    out = []
    for sx in (-1, 1):
        x = sx * 0.50
        z = ztop(x)
        ob = C.lathe("BumpStop", [(0.0, 0.0, 0), (0.012, 0.0, 0), (0.012, 0.012, 0), (0.010, 0.017, 0),
                                  (0.0, 0.019, 0)], [rubber], steps=40)
        ob.matrix_world = Matrix.Translation((x, YB - 0.022, z - 0.002))
        out.append(C.finalize(ob, angle=45))
    return out


def radiator_bushes(rubber):
    out = []
    for sx in (-1, 1):
        ob = C.lathe("RadBush", [(0.0055, 0.0, 0), (0.016, 0.0, 0), (0.016, 0.012, 0), (0.012, 0.016, 0),
                                 (0.0055, 0.016, 0)], [rubber], steps=40)
        ob.matrix_world = Matrix.Translation((sx * 0.25, YB - 0.022, ZI0 - 0.002))
        out.append(C.finalize(ob, angle=45))
    return out


def build():
    pp = P.textured_black("CompositePP", rough=0.58, v=0.028)
    insert = C.principled("BrassInsert", (0.62, 0.47, 0.25), metallic=1.0, rough=0.35)
    zinc = C.principled("ZincLatch", (0.70, 0.71, 0.66), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=200, strength=0.08, distance=0.0004, rough_var=0.08)
    black = C.mat_black_plastic("LatchBlack", rough=0.5)
    rubber = C.mat_rubber()
    objs = [base_web(pp)]
    objs.append(wall("OuterWall", outer_poly(), pp, 0.040))
    objs.append(wall("InnerWall", P.offset2d(inner_poly(), -0.0015 if P.signed_area(inner_poly()) > 0 else 0.0015, closed=True), pp, 0.040))
    for sx in (-1, 1):
        objs.append(wall("WingHoleWall", wing_hole(sx), pp, 0.022))
    objs += ribs(pp)
    objs += bosses(pp, insert)
    objs += latch(zinc, black, rubber)
    objs += bump_stops(rubber, pp)
    objs += radiator_bushes(rubber)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("frontale", objs, "frontale.py",
            "front-end carrier / radiator support (generic small hatchback): black glass-filled plastic frame with ribbed "
            "channels around the radiator opening, headlamp mounting wings with metal-insert bosses, bonnet latch with "
            "release cable, bump stops",
            az=-34, el=20, lens=70, fill=0.88, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
