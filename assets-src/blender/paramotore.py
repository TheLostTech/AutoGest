"""Under-engine splash shield (engine undertray) of a generic modern small hatchback,
removed from the car and shown from the road side. Large moulded panel in grained black
polypropylene: tapered outline narrower at the front, edges curving away into a bolting
lip with holes and zinc spire clips; longitudinal and transverse stiffening beads, a
recessed oil-drain access hatch with two quarter-turn fasteners, a row of cooling slots
at the rear and drain holes. Car front is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

Y0, Y1 = -0.40, 0.42
NU, NV = 400, 330
T = 0.003
ZP = 0.055            # height of the main face
HATCH = (0.0, -0.15, 0.115, 0.075, 0.02)   # cx, cy, half w, half h, r
SLOTS = [(-0.27 + 0.0771 * k, 0.335) for k in range(8)]
DRAINS = [(-0.30, -0.05), (0.30, -0.05), (-0.12, 0.20), (0.12, 0.20)]


def hw(y):
    t = (y - Y0) / (Y1 - Y0)
    return 0.43 + 0.07 * P.sstep(0.0, 0.5, t)


def rrect_sdf(x, y, cx, cy, hx, hy, r):
    qx = abs(x - cx) - hx + r
    qy = abs(y - cy) - hy + r
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r


def height(x, y):
    e = min(hw(y) - abs(x), y - Y0, Y1 - y)
    z = ZP
    # edge rolls away into a flat bolting lip
    z -= 0.034 * (1 - P.sstep(0.026, 0.085, e))
    # longitudinal beads
    for bx in (-0.34, -0.19, 0.19, 0.34):
        w = 0.018
        ty = P.sstep(Y0 + 0.10, Y0 + 0.16, y) * (1 - P.sstep(Y1 - 0.16, Y1 - 0.10, y))
        z += 0.0075 * P.bump(((x - bx) / w) ** 2) * ty
    # transverse bead
    tx = 1 - P.sstep(hw(y) - 0.16, hw(y) - 0.10, abs(x))
    z += 0.0065 * P.bump(((y - 0.08) / 0.016) ** 2) * tx
    # recessed hatch pocket
    cx, cy, hx, hy, r = HATCH
    s = rrect_sdf(x, y, cx, cy, hx + 0.012, hy + 0.012, r + 0.012)
    z -= 0.010 * (1 - P.sstep(-0.004, 0.006, s))
    # raised pad round the slots
    s2 = rrect_sdf(x, y, 0.0, 0.335, 0.33, 0.03, 0.02)
    z += 0.004 * (1 - P.sstep(-0.004, 0.006, s2))
    return z


def uv(u, v):
    X = 2 * u - 1
    y0 = Y0
    y1 = Y1
    rb, rt = 0.07, 0.05
    e = (1 - abs(X)) * hw(Y0)
    if e < rb:
        y0 += rb * (1 - math.sqrt(max(0.0, 1 - ((rb - e) / rb) ** 2)))
    e = (1 - abs(X)) * hw(Y1)
    if e < rt:
        y1 -= rt * (1 - math.sqrt(max(0.0, 1 - ((rt - e) / rt) ** 2)))
    y = y0 + (y1 - y0) * v
    return X * hw(y), y


def panel(pp):
    rows = []
    for j in range(NV + 1):
        row = []
        for i in range(NU + 1):
            x, y = uv(i / NU, j / NV)
            row.append(Vector((x, y, height(x, y))))
        rows.append(row)
    ob = P.grid_obj("Undertray", rows, [pp], Vector((0, 0, 1)))
    P.solidify(ob, T, offset=-1)
    cuts = []
    cb = bmesh.new()
    for (x, y) in SLOTS:
        C.box_bm(cb, 0.052, 0.010, 0.08, center=(x, y, ZP))
    for (x, y) in DRAINS:
        C.cyl_bm(cb, 0.011, ZP - 0.05, ZP + 0.05, seg=32, matrix=Matrix.Translation((x, y, 0)))
    # bolting holes along the lip
    holes = []
    for k in range(5):
        holes.append((-0.36 + 0.18 * k, Y0 + 0.012))
        holes.append((-0.40 + 0.20 * k, Y1 - 0.013))
    for y in (-0.22, 0.0, 0.22):
        for sx in (-1, 1):
            holes.append((sx * (hw(y) - 0.013), y))
    for (x, y) in holes:
        C.cyl_bm(cb, 0.0055, 0.0, 0.06, seg=24, matrix=Matrix.Translation((x, y, 0)))
    cuts.append(C.mesh_obj("Cuts", cb, [pp]))
    for c in cuts:
        m = C.add_boolean(ob, c)
        m.solver = "MANIFOLD"
    C.add_bevel(ob, 0.0012, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=cuts), holes


def hatch(pp, zinc, dark):
    out = []
    cx, cy, hx, hy, r = HATCH
    poly = P.resample(P.rounded([(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)], [r] * 4,
                                closed=True, seg=10), 160, closed=True)
    z = ZP - 0.010 + 0.0005

    def lift(q):
        return Vector((q.x, q.y, z + 0.003 * (1 - ((q.x - cx) / hx) ** 2) * (1 - ((q.y - cy) / hy) ** 2)))
    ob = P.fan_obj("Hatch", poly, Vector((cx, cy)), 12, lift, [pp], Vector((0, 0, 1)))
    P.solidify(ob, 0.003, offset=-1)
    C.add_bevel(ob, 0.0012, segments=2, angle=40)
    out.append(C.finalize(ob, angle=45))
    # gap shadow round the hatch
    gap = P.offset2d(poly, -0.004 if P.signed_area(poly) > 0 else 0.004, closed=True)
    pts = [Vector((q.x, q.y, z - 0.002)) for q in gap]
    fr = P.path_frames(pts, (0, 0, 1), closed=True)
    out.append(P.tube_obj("HatchGap", fr, P.rrect(-0.0025, 0.0025, -0.004, 0.001, 0.0008, seg=1), [dark], closed=True, smooth_angle=60))
    # quarter-turn fasteners
    for sx in (-1, 1):
        x = cx + sx * (hx - 0.03)
        ft = C.lathe("Fastener", [(0.0, 0.0, 0), (0.011, 0.0, 0), (0.011, 0.0025, 0), (0.0095, 0.0045, 0), (0.0, 0.005, 0)], [zinc], steps=40)
        ft.matrix_world = Matrix.Translation((x, cy, z + 0.002))
        out.append(C.finalize(ft, angle=40))
        bm = bmesh.new()
        C.box_bm(bm, 0.013, 0.0018, 0.0016, center=(x, cy, z + 0.0068),
                 matrix=Matrix.Translation((x, cy, 0)) @ Matrix.Rotation(math.radians(35 * sx), 4, "Z") @ Matrix.Translation((-x, -cy, 0)))
        out.append(C.finalize(C.mesh_obj("FastenerSlot", bm, [dark]), angle=30))
    return out


def spire_clips(holes, zinc):
    """U-shaped spire clips wrapped over the lip at every other hole."""
    out = []
    for i, (x, y) in enumerate(holes):
        if i % 2:
            continue
        z = height(x, y)
        # outward direction (towards the nearest edge)
        cand = [(hw(y) - abs(x), Vector((math.copysign(1, x), 0))), (y - Y0, Vector((0, -1))), (Y1 - y, Vector((0, 1)))]
        d = min(cand, key=lambda c: c[0])[1]
        o = Vector((x, y, z))
        ang = math.atan2(d.y, d.x)
        M = Matrix.Translation(o) @ Matrix.Rotation(ang, 4, "Z")
        bm = bmesh.new()
        C.box_bm(bm, 0.026, 0.020, 0.0012, center=(0.002, 0, 0.0008), matrix=M)
        C.box_bm(bm, 0.026, 0.020, 0.0012, center=(0.002, 0, -T - 0.0008), matrix=M)
        ob = C.mesh_obj("SpireClip", bm, [zinc])
        C.add_bevel(ob, 0.0004, segments=1, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


def slot_backs(dark):
    """Dark ducting seen through the cooling slots and drains."""
    bm = bmesh.new()
    C.box_bm(bm, 0.66, 0.05, 0.002, center=(0.0, 0.335, ZP - 0.03))
    return [C.finalize(C.mesh_obj("SlotBack", bm, [dark]), angle=30)]


def build():
    pp = P.textured_black("UndertrayPP", rough=0.66, v=0.024)
    hatch_pp = P.textured_black("HatchPP", rough=0.6, v=0.02)
    zinc = C.principled("Zinc", (0.64, 0.64, 0.62), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=300, strength=0.06, distance=0.0003, rough_var=0.06)
    dark = C.principled("Gap", (0.004, 0.004, 0.004), rough=0.9)
    pan, holes = panel(pp)
    objs = [pan]
    objs += hatch(hatch_pp, zinc, dark)
    objs += spire_clips(holes, zinc)
    objs += slot_backs(dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("paramotore", objs, "paramotore.py",
            "engine undertray / splash shield (generic small hatchback): large grained black plastic panel seen from the road "
            "side, stiffening beads, oil-drain access hatch, cooling slots, drain holes, bolting lip with spire clips",
            az=-30, el=36, lens=70, fill=0.9, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
