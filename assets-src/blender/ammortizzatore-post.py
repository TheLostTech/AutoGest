"""Rear shock absorber (ammortizzatore posteriore) as removed from a small car: twin-tube
damper without spring, black painted steel body with rolled bottom seam, blank adhesive
label, welded bottom eye and top eye on the rod end, both with rubber bushes and steel
sleeves; rod guide cap, a short length of chrome piston rod visible below the black
plastic bellows dust boot with its top cap. Built along Z, then laid on the floor
diagonally. 1 unit ~ 10 cm (eye to eye about 46 cm extended)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RB = 0.25            # body radius (50 mm tube)
ZB0, ZB1 = 0.22, 2.70
ZTOP = 4.40          # top eye centre


def eye(name, z, paint, rubber, steel, width=0.40, ro=0.20):
    out = []
    Rx = Matrix.Translation((0, 0, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
    P = [(0.135, -width / 2, 0), (ro, -width / 2, 0), (ro, width / 2, 0), (0.135, width / 2, 0)]
    e = C.lathe(name, P, [paint], steps=64)
    e.matrix_world = Rx
    C.add_bevel(e, 0.015, segments=2, angle=30)
    out.append(C.finalize(e, angle=35))
    P = [(0.06, -width / 2 - 0.03, 0), (0.12, -width / 2 - 0.03, 0), (0.137, -width / 2 + 0.01, 0), (0.137, width / 2 - 0.01, 0),
         (0.12, width / 2 + 0.03, 0), (0.06, width / 2 + 0.03, 0)]
    b = C.lathe(name + "Bush", P, [rubber], steps=64)
    b.matrix_world = Rx
    out.append(C.finalize(b, angle=40))
    P = [(0.04, -width / 2 - 0.05, 0), (0.062, -width / 2 - 0.05, 0), (0.062, width / 2 + 0.05, 0), (0.04, width / 2 + 0.05, 0)]
    s = C.lathe(name + "Sleeve", P, [steel], steps=48)
    s.matrix_world = Rx
    C.add_bevel(s, 0.004, segments=1, angle=30)
    out.append(C.finalize(s, angle=40))
    return out


def body(paint, chrome, plastic, steel):
    out = []
    P = [(0.0, 0.17, 0), (0.12, 0.17, 0), (0.20, ZB0 - 0.02, 0), (0.235, ZB0 + 0.01, 0), (RB + 0.008, ZB0 + 0.03, 0),
         (RB + 0.008, ZB0 + 0.06, 0), (RB, ZB0 + 0.075, 0),                      # rolled seam
         (RB, ZB1 - 0.05, 0), (RB - 0.01, ZB1, 0), (0.20, ZB1 + 0.02, 0), (0.0, ZB1 + 0.02, 0)]
    out.append(C.finalize(C.lathe("Body", P, [paint], steps=96), angle=35))
    # rod guide / seal cap
    P = [(0.0, ZB1, 0), (0.205, ZB1, 0), (0.21, ZB1 + 0.05, 0), (0.17, ZB1 + 0.08, 0), (0.10, ZB1 + 0.10, 0), (0.0, ZB1 + 0.10, 0)]
    out.append(C.finalize(C.lathe("GuideCap", P, [steel], steps=96), angle=35))
    # chrome rod
    P = [(0.0, ZB1 + 0.05, 0), (0.063, ZB1 + 0.05, 0), (0.063, ZTOP - 0.15, 0), (0.0, ZTOP - 0.15, 0)]
    out.append(C.finalize(C.lathe("Rod", P, [chrome], steps=64), angle=40))
    # bellows dust boot (black plastic) under a top cap
    z0, z1 = 3.12, 4.02
    P = [(0.0, z0, 0), (0.09, z0, 0), (0.12, z0 + 0.03, 0)]
    z = z0 + 0.03
    n = 13
    pitch = (z1 - 0.06 - z) / n
    for i in range(n):
        P += [(0.175, z + pitch * 0.45, 0), (0.135, z + pitch, 0)]
        z += pitch
    P += [(0.15, z1 - 0.03, 0), (0.12, z1, 0), (0.0, z1, 0)]
    out.append(C.finalize(C.lathe("Bellows", P, [plastic], steps=96), angle=55))
    P = [(0.0, z1 - 0.02, 0), (0.20, z1 - 0.02, 0), (0.215, z1 + 0.01, 0), (0.20, z1 + 0.04, 0), (0.08, z1 + 0.06, 0), (0.0, z1 + 0.06, 0)]
    out.append(C.finalize(C.lathe("TopCap", P, [paint], steps=96), angle=35))
    # neck between top cap and top eye
    P = [(0.0, z1 + 0.04, 0), (0.08, z1 + 0.04, 0), (0.09, ZTOP - 0.24, 0), (0.12, ZTOP - 0.17, 0), (0.0, ZTOP - 0.17, 0)]
    out.append(C.finalize(C.lathe("EyeNeck", P, [paint], steps=64), angle=40))
    # bottom eye neck (welded pad)
    P = [(0.0, 0.10, 0), (0.13, 0.10, 0), (0.15, 0.19, 0), (0.0, 0.19, 0)]
    out.append(C.finalize(C.lathe("BottomPad", P, [paint], steps=64), angle=40))
    return out


def curved_label(mat):
    """blank label wrapped around the body tube"""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    a0, a1 = math.radians(-60), math.radians(60)
    z0, z1 = 1.25, 1.85
    nu, nv = 24, 2
    r = RB + 0.0015
    vs = [[bm.verts.new((r * math.sin(a0 + (a1 - a0) * i / nu), -r * math.cos(a0 + (a1 - a0) * i / nu), z0 + (z1 - z0) * j / nv))
           for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uv].uv = (ii / nu, jj / nv)
    for f in bm.faces:
        f.smooth = True
    return C.mesh_obj("Label", bm, [mat])


def build():
    paint = C.mat_paint("DamperBlack", (0.02, 0.02, 0.022, 1), rough=0.38, coat=0.25)
    C.add_noise_bump(paint, scale=700, strength=0.05, distance=0.0005)
    chrome = C.mat_chrome()
    rubber = C.mat_rubber()
    plastic = C.mat_black_plastic("BootPP", rough=0.5, color=0.03)
    steel = C.principled("ZincSteel", (0.62, 0.62, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    im = C.label_image("DamperLabel", w=1024, h=512, seed=11)
    lab = C.mat_label(im, "LabelMat")
    objs = body(paint, chrome, plastic, steel)
    objs += eye("BottomEye", 0.0, paint, rubber, steel)
    objs += eye("TopEye", ZTOP, paint, rubber, steel, width=0.38, ro=0.19)
    objs.append(curved_label(lab))
    # lay it down: axis along X, label facing up/camera, then diagonal
    C.transform_all(objs, Matrix.Rotation(math.radians(40), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "Y")
                    @ Matrix.Rotation(math.radians(-70), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("ammortizzatore-post", objs, "ammortizzatore-post.py",
            "rear shock absorber: black twin-tube damper body with eye mounts at both ends, rubber bushes, chrome rod, bellows dust boot, no spring",
            az=12, el=30, lens=70, fill=0.88,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
