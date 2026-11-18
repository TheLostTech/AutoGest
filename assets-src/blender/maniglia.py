"""Exterior front door pull handle of a generic modern small hatchback, removed from the car.
Metallic-grey painted grip (same paint as the body panels) standing off a black base
gasket on two legs, matching painted lock-cylinder cap at the front end with a keyhole;
behind, the black plastic carrier (handle bracket) with ribs, screw bosses and the
zinc-plated actuating lever with its rod clip. Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P


def se_obj(name, a, b, c, loc, mat, e1=0.4, e2=0.4, rot=None, nu=72, nv=36):
    bm = bmesh.new()
    M = Matrix.Translation(loc)
    if rot is not None:
        M = M @ rot
    P.superellipsoid(bm, a, b, c, e1=e1, e2=e2, nu=nu, nv=nv, matrix=M)
    return C.mesh_obj(name, bm, [mat])


def bowed(ob, k=0.06):
    """Bend along x so the part follows the door's plan curvature (ends towards +Y)."""
    for v in ob.data.vertices:
        v.co.y += k * v.co.x * v.co.x
    return ob


def grip(paint):
    g = se_obj("Grip", 0.082, 0.0115, 0.0165, (0.004, -0.031, 0.0), paint, e1=0.55, e2=0.42, nu=96, nv=48)
    legs = []
    for (x, a) in ((-0.060, 0.010), (0.070, 0.0105)):
        legs.append(se_obj("Leg", a, 0.018, 0.0125, (x, -0.016, 0.0), paint, e1=0.5, e2=0.5))
    bm = bmesh.new()
    for lg in legs:
        bm.from_mesh(lg.data)
        bpy.data.objects.remove(lg, do_unlink=True)
    legob = C.mesh_obj("Legs", bm, [paint])
    C.add_boolean(g, legob, op="UNION")
    bowed(g)
    return C.finalize(g, angle=50, remove=[legob])


def lock_cap(paint, chrome, black):
    out = []
    cap = se_obj("LockCap", 0.025, 0.010, 0.0165, (-0.106, -0.0115, 0.0), paint, e1=0.55, e2=0.45)
    bowed(cap)
    out.append(C.finalize(cap, angle=50))
    yo = -0.0115 - 0.010 + 0.06 * 0.106 ** 2 + 0.0004
    M = Matrix.Translation((-0.108, yo, 0.0)) @ Matrix.Rotation(math.radians(90), 4, "X")
    ring = C.lathe("KeyRing", [(0.0045, 0.0012, 0), (0.0068, 0.0012, 0), (0.0072, 0.0, 0), (0.0072, -0.003, 0), (0.0045, -0.003, 0)],
                   [chrome], steps=48)
    ring.matrix_world = M
    out.append(C.finalize(ring, angle=40))
    disc = C.lathe("KeyFace", [(0.0, -0.0004, 0), (0.0047, -0.0004, 0), (0.0047, -0.003, 0), (0.0, -0.003, 0)], [chrome], steps=48)
    disc.matrix_world = M
    out.append(C.finalize(disc, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.0018, 0.0012, 0.0080, center=(0, 0, 0),
             matrix=Matrix.Translation((-0.108, yo + 0.0001, 0.0)))
    slot = C.mesh_obj("KeySlot", bm, [black])
    out.append(C.finalize(slot, angle=40))
    return out


def base(tex, rubber):
    """Black base gasket between the handle and the paint (two pads joined by a thin web)."""
    out = []
    b = se_obj("Base", 0.121, 0.0028, 0.0225, (-0.012, -0.0015, 0.0), tex, e1=0.25, e2=0.3, nu=96)
    bowed(b)
    C.add_bevel(b, 0.0008, segments=2, angle=30)
    out.append(C.finalize(b, angle=45))
    return out


def carrier(black, zinc, rubber):
    out = []
    bm = bmesh.new()
    P.superellipsoid(bm, 0.128, 0.016, 0.028, e1=0.3, e2=0.25, matrix=Matrix.Translation((-0.010, 0.017, 0.0)))
    # stiffening ribs on the top and bottom faces
    for x in (-0.07, 0.0, 0.065):
        for sz in (-1, 1):
            C.box_bm(bm, 0.0035, 0.022, 0.004, center=(x, 0.021, sz * 0.0295))
    # screw bosses
    for x in (-0.135, 0.112):
        C.cyl_bm(bm, 0.0105, 0.0, 0.034, seg=32, matrix=Matrix.Translation((x, 0.0, 0.0)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    ob = C.mesh_obj("Carrier", bm, [black])
    bowed(ob)
    C.add_bevel(ob, 0.0012, segments=2, angle=30)
    out.append(C.finalize(ob, angle=40))
    # screws in the bosses (heads on the inside face)
    for x in (-0.135, 0.112):
        y = 0.034 + 0.06 * x * x
        M = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        hd = C.lathe("Screw", [(0.0, 0.0, 0), (0.0062, 0.0, 0), (0.0062, 0.002, 0), (0.0052, 0.0042, 0), (0.0, 0.0046, 0)],
                     [zinc], steps=32)
        hd.matrix_world = M
        out.append(C.finalize(hd, angle=40))
    # actuating lever at the rear with the rod clip
    bm = bmesh.new()
    C.box_bm(bm, 0.050, 0.004, 0.016, center=(0.0, 0.0, 0.0),
             matrix=Matrix.Translation((0.112, 0.048, -0.006)) @ Matrix.Rotation(math.radians(-28), 4, "Z"))
    C.cyl_bm(bm, 0.006, -0.012, 0.012, seg=24, matrix=Matrix.Translation((0.090, 0.036, -0.006)))
    lv = C.mesh_obj("Lever", bm, [zinc])
    C.add_bevel(lv, 0.001, segments=2, angle=30)
    out.append(C.finalize(lv, angle=40))
    clip = C.lathe("RodClip", [(0.0, 0.0, 0), (0.007, 0.0, 0), (0.0075, 0.004, 0), (0.0055, 0.011, 0), (0.0, 0.012, 0)],
                   [black], steps=32)
    clip.matrix_world = Matrix.Translation((0.132, 0.058, -0.012)) @ Matrix.Rotation(math.radians(62), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")
    out.append(C.finalize(clip, angle=40))
    # foam seal pads where the legs pass through
    for x in (-0.060, 0.070):
        bm = bmesh.new()
        P.superellipsoid(bm, 0.017, 0.0015, 0.019, e1=0.3, e2=0.3, matrix=Matrix.Translation((x, 0.0003 + 0.06 * x * x, 0.0)))
        pad = C.mesh_obj("Pad", bm, [rubber])
        out.append(C.finalize(pad, angle=45))
    return out


def build():
    paint = P.body_paint()
    tex = P.textured_black("BaseTPE", rough=0.55, v=0.02)
    black = C.mat_black_plastic("CarrierPA", rough=0.5, color=0.03)
    rubber = C.mat_rubber()
    chrome = C.mat_chrome()
    zinc = C.principled("YellowZinc", (0.62, 0.56, 0.36), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=300, strength=0.05, distance=0.0004, rough_var=0.06)
    objs = [grip(paint)]
    objs += lock_cap(paint, chrome, black)
    objs += base(tex, rubber)
    objs += carrier(black, zinc, rubber)
    # lay it as on the door: slight downward tilt of the camera does the rest
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("maniglia", objs, "maniglia.py",
            "exterior door pull handle (generic small hatchback): metallic grey painted grip and lock-cylinder cap with "
            "keyhole, black base gasket, black plastic carrier bracket with screws and zinc actuating lever",
            az=-34, el=24, lens=80, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
