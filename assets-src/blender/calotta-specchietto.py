"""Door-mirror cap (cover), generic small hatchback, left side: the painted outer shell of
the mirror head, same shape family as specchietto.py, in the catalogue's body colour.
Unpainted grained black inside with a locating step, two screw bosses and moulded ribs;
five snap clips stand out of the rim with their hook lips. Upright, seen from the side
so the painted outer end and the clips inside both show.
Local frame: rim on y = 0, dome towards +Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

S = 0.225          # width of the rim (m)
DEPTH = 0.078      # rim -> top of the dome
T = 0.0024         # wall
HEAD_PTS = [(-0.56, 0.17), (-0.47, 0.29), (0.28, 0.31), (0.44, 0.24), (0.47, -0.10),
            (0.36, -0.23), (-0.28, -0.22), (-0.53, -0.07)]
NU = 240


def outline(grow=0.0):
    pts = [Vector((x * S / 1.03, z * S / 1.03)) for x, z in HEAD_PTS]
    sm = P.bspline(pts, n=NU, closed=True)
    if P.signed_area(sm) < 0:
        sm = sm[::-1]
    if grow:
        sm = P.offset2d(sm, -grow, closed=True)   # CCW: left normal inwards, so -grow grows
    return sm


RIM = outline()
HC = sum(RIM, Vector((0, 0))) / len(RIM) + Vector((-0.012, 0.004))   # dome apex slightly outboard


def profile():
    """(scale, y) rings from the rim to the apex."""
    P_ = [(1.0, 0.0), (1.0, 0.004), (1.002, 0.010)]
    K = 22
    for k in range(1, K + 1):
        ph = (math.pi / 2) * k / K
        s = 1.002 * max(math.cos(ph), 0.0) ** 0.42
        y = 0.010 + (DEPTH - 0.010) * math.sin(ph) ** 1.9
        P_.append((s, y))
    return P_


def shell(paint, raw):
    rows = []
    for (s, y) in reversed(profile()):
        rows.append([Vector((HC.x + (q.x - HC.x) * s, y, HC.y + (q.y - HC.y) * s)) for q in RIM])
    cen = Vector((HC.x, DEPTH * 0.25, HC.y))
    ob = P.grid_obj("Cap", rows, [paint, raw], lambda c: c - cen, closed_u=True)
    P.solidify(ob, T, offset=-1, inner=1, rim=1)
    C.add_bevel(ob, 0.0007, segments=2, angle=30)
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    return C.finalize(ob, angle=50)


def frame_at(i, grow):
    """2D point, tangent and inward normal on the (offset) rim at index i."""
    poly = outline(grow)
    p = poly[i % NU]
    t = (poly[(i + 1) % NU] - poly[i - 1]).normalized()
    n = Vector((-t.y, t.x))          # CCW: inward
    return p, t, n


def clips(raw):
    out = []
    for i in (8, 62, 118, 160, 205):
        p, t, n = frame_at(i, -T - 0.0004)
        X = Vector((t.x, 0, t.y))
        Nn = Vector((n.x, 0, n.y))
        Y = Vector((0, 1, 0))
        M = P.basis(X, Nn, Y, Vector((p.x, 0.0, p.y)))
        bm = bmesh.new()
        C.box_bm(bm, 0.011, 0.0017, 0.024, center=(0, 0.00085, 0.004))       # tongue (y local = inward)
        C.box_bm(bm, 0.011, 0.0034, 0.0030, center=(0, 0.0030, -0.0065))     # hook lip
        C.box_bm(bm, 0.0016, 0.0042, 0.012, center=(-0.0062, 0.0021, 0.010))  # side gussets
        C.box_bm(bm, 0.0016, 0.0042, 0.012, center=(0.0062, 0.0021, 0.010))
        ob = C.mesh_obj("Clip", bm, [raw])
        C.add_bevel(ob, 0.0004, segments=1, angle=30)
        ob.matrix_world = M
        out.append(C.finalize(ob, angle=35))
    return out


def inner_detail(raw):
    out = []
    # locating step: a narrow ledge running round the inside a few mm below the rim
    path = outline(-T - 0.0002)
    fr = P.frames_on_surface(path, lambda q: Vector((q.x, 0.012, q.y)), Vector((0, 1, 0)), closed=True)
    out.append(P.tube_obj("Ledge", fr, P.rrect(0.0, 0.0032, -0.0012, 0.0012, 0.0006, seg=2), [raw],
                          closed=True, smooth_angle=50))
    # two screw bosses rising from the dome floor towards the rim
    Ry = Matrix.Rotation(math.radians(90), 4, "X")   # lathe Z -> -Y (from the dome towards the rim)
    for (dx, dz) in ((-0.045, 0.010), (0.055, -0.004)):
        q = Vector((HC.x + dx, HC.y + dz))
        boss = C.lathe("Boss", [(0.0024, 0.0, 0), (0.0055, 0.0, 0), (0.0055, 0.040, 0), (0.0045, 0.042, 0),
                                (0.0024, 0.042, 0), (0.0024, 0.030, 0)], [raw], steps=40)
        boss.matrix_world = Matrix.Translation((q.x, DEPTH - 0.012, q.y)) @ Ry
        out.append(C.finalize(boss, angle=40))
    return out


def build():
    paint = P.body_paint()
    raw = P.textured_black("RawPP", rough=0.6, v=0.03)
    objs = [shell(paint, raw)]
    objs += clips(raw)
    objs += inner_detail(raw)
    # upright, opening towards -Y; the camera looks at it from the side so the painted
    # outer end and the inside with its clips both show
    M = Matrix.Rotation(math.radians(-6), 4, "X")
    C.transform_all(objs, M)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("calotta-specchietto", objs, "calotta-specchietto.py",
            "door mirror cap (generic small hatchback): metallic grey painted cap shell, grained black inside "
            "with snap clips, screw bosses and ribs",
            az=-62, el=24, lens=70, fill=0.80, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
