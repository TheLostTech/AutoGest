"""Fuel filler flap of a generic modern small hatchback, removed from the car.
Small rounded-rectangular door, slightly domed, painted in the same metallic grey
clear-coat as the other body panels, with a rolled edge; on the back an e-coated inner
panel with a pressed stiffening ring, a goose-neck hinge arm that runs out of the hinge
edge to its pivot block (zinc pin and torsion spring), a push-push latch hook and a
rubber bump stop. Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
HW, HH, R = 0.086, 0.068, 0.034
T = 0.0045


def outline(inset=0.0, n=260):
    pts = P.rounded([(-HW + inset, -HH + inset), (HW - inset, -HH + inset), (HW - inset, HH - inset), (-HW + inset, HH - inset)],
                    [max(0.005, R - inset)] * 4, closed=True, seg=20)
    return P.resample(pts, n, closed=True)


def dome(q):
    r2 = (q.x / 0.10) ** 2 + (q.y / 0.085) ** 2
    return -0.0045 * (1 - r2)


def skin(q, off=0.0):
    return Vector((q.x, dome(q) + off, q.y))


def flap(paint, ec):
    poly = outline()
    ob = P.fan_obj("Flap", poly, Vector((0, 0)), 24, skin, [paint, ec], OUT, power=1.3)
    P.solidify(ob, T, offset=-1, inner=1, rim=0)
    C.add_bevel(ob, 0.0016, segments=3, angle=40)
    return C.finalize(ob, angle=45)


def inner_panel(ec):
    poly = outline(0.009)
    c = Vector((0, 0))

    def lift(q):
        # stiffening ring pressed into the inner panel
        r = math.sqrt((q.x / HW) ** 2 + (q.y / HH) ** 2)
        h = 0.004 * P.bump(((r - 0.62) / 0.16) ** 2)
        return skin(q, T + 0.0015 + h)
    ob = P.fan_obj("InnerPanel", poly, c, 40, lift, [ec], -OUT, power=1.0)
    P.solidify(ob, 0.0012, offset=-1)
    C.add_bevel(ob, 0.0008, segments=2, angle=40)
    return C.finalize(ob, angle=45)


def hinge(ec, zinc, black, spring_m):
    out = []
    yb = T + 0.004
    # goose-neck arm: riveted along the back, out past the hinge (front) edge, then inward to the pivot
    path = [Vector((0.030, yb, 0.0)), Vector((-0.040, yb, 0.0)), Vector((-0.080, yb + 0.002, 0.0)),
            Vector((-0.100, yb + 0.012, 0.0)), Vector((-0.112, yb + 0.034, 0.0)), Vector((-0.108, yb + 0.058, 0.0)),
            Vector((-0.094, yb + 0.072, 0.0))]
    path = P.bspline(path, 90)
    fr = P.path_frames(path, (0, 0, 1))
    sec = P.rrect(-0.0016, 0.0016, -0.008, 0.008, 0.0012, seg=2)
    out.append(P.tube_obj("HingeArm", fr, sec, [ec], smooth_angle=50))
    # stiffening rib pressed along the arm
    out.append(P.tube_obj("ArmRib", fr[4:-4], P.rrect(-0.0028, 0.0028, -0.0025, 0.0025, 0.0015, seg=2), [ec], smooth_angle=50))
    # rivets
    for x in (0.018, -0.030):
        rv = C.lathe("Rivet", [(0.0, 0.0, 0), (0.0045, 0.0, 0), (0.004, 0.0012, 0), (0.0025, 0.0019, 0), (0.0, 0.002, 0)], [zinc], steps=24)
        rv.matrix_world = Matrix.Translation((x, yb + 0.0016, 0.0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        out.append(C.finalize(rv, angle=40))
    # pivot block with vertical pin and torsion spring
    end = path[-1]
    bm = bmesh.new()
    P.superellipsoid(bm, 0.012, 0.011, 0.026, e1=0.3, e2=0.3, matrix=Matrix.Translation(end + Vector((0.006, 0.010, 0.0))))
    out.append(C.finalize(C.mesh_obj("PivotBlock", bm, [black]), angle=45))
    pin = C.lathe("Pin", [(0.0, -0.036, 0), (0.0042, -0.036, 0), (0.0042, -0.033, 0), (0.0024, -0.032, 0), (0.0024, 0.032, 0),
                          (0.0042, 0.033, 0), (0.0042, 0.036, 0), (0.0, 0.036, 0)], [zinc], steps=24)
    pin.matrix_world = Matrix.Translation(end + Vector((0.0, 0.001, 0.0)))
    out.append(C.finalize(pin, angle=40))
    # torsion spring coils round the pin, below the arm
    pts = []
    turns = 5
    for k in range(turns * 24 + 1):
        a = math.tau * k / 24
        pts.append(end + Vector((0.0068 * math.cos(a), 0.001 + 0.0068 * math.sin(a), -0.013 - 0.0145 * k / (turns * 24))))
    fr = P.path_frames(pts, lambda p: Vector((0, 0, 1)))
    out.append(P.tube_obj("Spring", fr, P.circle(0.0011, 10), [spring_m], smooth_angle=70))
    return out


def latch(black, rubber):
    out = []
    yb = T + 0.004
    bm = bmesh.new()
    C.box_bm(bm, 0.016, 0.006, 0.020, center=(0.062, yb, 0.0))
    C.box_bm(bm, 0.008, 0.018, 0.008, center=(0.062, yb + 0.010, 0.0))
    C.box_bm(bm, 0.008, 0.006, 0.014, center=(0.062, yb + 0.018, 0.004))
    ob = C.mesh_obj("LatchHook", bm, [black])
    C.add_bevel(ob, 0.0011, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    bs = C.lathe("BumpStop", [(0.0, 0.0, 0), (0.006, 0.0, 0), (0.006, 0.004, 0), (0.004, 0.0065, 0), (0.0, 0.007, 0)], [rubber], steps=28)
    bs.matrix_world = Matrix.Translation((0.03, yb - 0.002, -0.045)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.finalize(bs, angle=40))
    return out


def build():
    paint = P.body_paint()
    ec = P.ecoat()
    zinc = C.principled("Zinc", (0.66, 0.66, 0.68), metallic=1.0, rough=0.3)
    black = C.mat_black_plastic("POM", rough=0.42)
    rubber = C.mat_rubber()
    spring_m = C.principled("SpringSteel", (0.12, 0.12, 0.13), metallic=1.0, rough=0.35)
    objs = [flap(paint, ec), inner_panel(ec)]
    objs += hinge(ec, zinc, black, spring_m)
    objs += latch(black, rubber)
    C.transform_all(objs, Matrix.Rotation(math.radians(14), 4, "Z") @ Matrix.Rotation(math.radians(-28), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("sportellino-carburante", objs, "sportellino-carburante.py",
            "fuel filler flap (generic small hatchback), metallic grey paint: small domed rounded-rectangular door with "
            "goose-neck hinge arm, pivot block with pin and spring, latch hook on the back",
            az=-32, el=22, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
