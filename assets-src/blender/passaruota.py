"""Front wheel-arch liner (inner fender) of a generic modern small hatchback, removed from
the car and standing on its two ends. Moulded grained black polypropylene arch: a part
cylinder round the tyre with circumferential stiffening ribs, a flared outer lip that
clips to the wing's arch flange (holes and push clips), an inner wall turning down
towards the suspension, and bolting tabs at the front and rear ends.
Car front is -X, outside is -Y (the open side faces outwards)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

R = 0.365            # radius of the main surface
W = 0.255            # width across the tyre (y)
TH0, TH1 = math.radians(-112), math.radians(104)   # arc ends (0 = top, - = front)
NTH, NW = 360, 150
T = 0.0028
LIP = 0.022


def radius(th, w):
    r = R
    # flared outer lip (w small): turns outwards to meet the wing flange
    if w < LIP:
        t = 1 - w / LIP
        r += 0.040 * t * t
    # circumferential ribs
    for wc in (0.055, 0.09, 0.125, 0.16, 0.195):
        r += 0.008 * P.bump(((w - wc) / 0.009) ** 2)
    # inner side turns down (smaller radius) towards the suspension
    r -= 0.075 * P.sstep(W - 0.05, W, w) ** 1.6
    # slight bulge at the top rear (clearance for steering lock)
    r += 0.012 * P.bump(((th - 0.5) / 0.9) ** 2) * P.sstep(0.03, 0.12, w) * (1 - P.sstep(W - 0.08, W - 0.03, w))
    return r


def pt(th, w, dr=0.0):
    r = radius(th, w) + dr
    return Vector((r * math.sin(th), w, r * math.cos(th)))


def lip_frame(k):
    """Frame on the flared lip at hole k: local Z = surface normal pointing out of the arch side."""
    th = TH0 + 0.12 + (TH1 - TH0 - 0.24) * k / 8
    w = 0.008
    c = pt(th, w)
    du = (pt(th + 1e-4, w) - pt(th - 1e-4, w)).normalized()
    dv = (pt(th, w + 1e-4) - pt(th, w - 1e-4)).normalized()
    n = du.cross(dv).normalized()
    if n.y > 0:
        n = -n
    X = du
    Y = n.cross(X)
    return P.basis(X, Y, n, c)


def liner(pp):
    rows = []
    for j in range(NW + 1):
        w = W * j / NW
        rows.append([pt(TH0 + (TH1 - TH0) * i / NTH, w) for i in range(NTH + 1)])
    ob = P.grid_obj("Liner", rows, [pp], lambda c: Vector((-c.x, 0, -c.z)))
    P.solidify(ob, T, offset=1)
    cb = bmesh.new()
    for k in range(9):
        C.cyl_bm(cb, 0.0048, -0.03, 0.03, seg=20, matrix=lip_frame(k))
    cut = C.mesh_obj("LipHoles", cb, [pp])
    m = C.add_boolean(ob, cut)
    m.solver = "MANIFOLD"
    C.add_bevel(ob, 0.0012, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=[cut])


def clips(nylon):
    out = []
    for k in range(0, 9, 2):
        M = lip_frame(k)
        hd = C.lathe("ClipHead", [(0.0, -0.0025, 0), (0.0095, -0.0025, 0), (0.0095, -0.0005, 0), (0.007, 0.0, 0), (0.0, 0.0, 0)],
                     [nylon], steps=32)
        hd.matrix_world = M
        out.append(C.finalize(hd, angle=40))
        sh = C.lathe("ClipShank", [(0.0, 0.0, 0), (0.0042, 0.0, 0), (0.0042, 0.006, 0), (0.0055, 0.009, 0), (0.0035, 0.016, 0), (0.0, 0.016, 0)],
                     [nylon], steps=24)
        sh.matrix_world = M
        out.append(C.finalize(sh, angle=40))
    return out


def end_tabs(pp):
    out = []
    for th in (TH0, TH1):
        sgn = -1 if th < 0 else 1
        c = pt(th, W * 0.45, 0.0)
        tdir = Vector((math.cos(th), 0, -math.sin(th))) * sgn       # continuing past the arc end
        n = Vector((math.sin(th), 0, math.cos(th)))
        M = P.basis(tdir, Vector((0, 1, 0)), n, c + tdir * 0.022 + n * 0.0014)
        bm = bmesh.new()
        C.box_bm(bm, 0.05, 0.075, T, matrix=M)
        tb = C.mesh_obj("EndTab", bm, [pp])
        cb = bmesh.new()
        for dy in (-0.022, 0.022):
            C.cyl_bm(cb, 0.0052, -0.02, 0.02, seg=20, matrix=M @ Matrix.Translation((0.008, dy, 0)))
        cut = C.mesh_obj("TabHoles", cb, [pp])
        C.add_boolean(tb, cut)
        C.add_bevel(tb, 0.0012, segments=2, angle=30)
        out.append(C.finalize(tb, angle=35, remove=[cut]))
    return out


def build():
    pp = P.textured_black("LinerPP", rough=0.6, v=0.036)
    nylon = C.mat_black_plastic("ClipPA", rough=0.4, color=0.03)
    objs = [liner(pp)]
    objs += clips(nylon)
    objs += end_tabs(pp)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("passaruota", objs, "passaruota.py",
            "front wheel-arch liner (generic small hatchback): black grained plastic arch with circumferential ribs, "
            "flared outer lip with clips, inner wall, bolting tabs at the ends",
            az=-30, el=18, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
