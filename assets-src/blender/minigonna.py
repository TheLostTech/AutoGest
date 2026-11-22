"""Left side sill cover (side skirt) of a generic modern small hatchback, removed from the car.
Long moulded plastic panel: upper face painted in the same metallic grey clear-coat as the
other body panels, with a soft feature line, lower lip in unpainted grained black
plastic; both ends cut on the arc of the wheel arches; inward flanges top and bottom with
white nylon push clips along the top and screw holes along the bottom.
Car front is -X, outside is -Y; the panel is laid at an angle."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

L = 1.56
NU, NT = 520, 150
SKIN_T = 0.003
Z_BLACK = 0.060
ZS = 1.25           # section height scale
ARCH_R, ARCH_ZC = 0.37, 0.30

# section: (outward distance a towards -Y, height z), from the top flange to the bottom flange
SEC = P.bspline([(-0.045, 0.132), (-0.012, 0.132), (0.004, 0.128), (0.017, 0.114), (0.025, 0.092), (0.029, 0.070),
                 (0.031, 0.056), (0.036, 0.050), (0.037, 0.040), (0.033, 0.020), (0.022, 0.006), (0.004, 0.0),
                 (-0.030, 0.0), (-0.050, 0.004)], NT + 1)
SEC = [Vector((p.x, p.y * ZS)) for p in SEC]


def x_half(z):
    zz = min(max(z, 0.0), 0.17)
    return L / 2 - (math.sqrt(ARCH_R ** 2 - (ARCH_ZC - zz) ** 2) - math.sqrt(ARCH_R ** 2 - ARCH_ZC ** 2))


def a_end(x, a, z):
    """Ends fold in slightly towards the body (return into the arch)."""
    e = abs(x) / x_half(z)
    return a - 0.012 * P.sstep(0.96, 1.0, e)


def pt(x, a, z):
    bow = 0.006 * (1 - (x / (L / 2)) ** 2)        # gentle outward bow
    return Vector((x, -(a_end(x, a, z) + bow), z))


def shell(paint, raw, black, rawb):
    rows = []
    for j in range(NT + 1):
        q = SEC[j]
        xh = x_half(q.y)
        rows.append([pt((2 * i / NU - 1) * xh, q.x, q.y) for i in range(NU + 1)])
    bm = P.clean(P.grid_bm(rows))
    for f in bm.faces:
        if f.calc_center_median().z < Z_BLACK:
            f.material_index = 2
    P.orient(bm, Vector((0, -1, 0.2)))
    ob = C.mesh_obj("SillSkin", bm, [paint, raw, black, rawb])
    P.solidify(ob, SKIN_T, offset=-1, inner=1, rim=1)
    cuts = []
    cb = bmesh.new()
    for k in range(6):
        x = -0.62 + k * 0.248
        C.box_bm(cb, 0.016, 0.009, 0.05, center=(x, 0.028, 0.165))
    cuts.append(C.mesh_obj("ClipHoles", cb, [paint]))
    cb = bmesh.new()
    for x in (-0.55, -0.18, 0.18, 0.55):
        C.cyl_bm(cb, 0.0045, -0.03, 0.03, seg=20, matrix=Matrix.Translation((x, 0.034, 0.0)))
    cuts.append(C.mesh_obj("ScrewHoles", cb, [paint]))
    for c in cuts:
        m = C.add_boolean(ob, c)
        m.solver = "MANIFOLD"
    C.add_bevel(ob, 0.0014, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=cuts)


def clips(nylon):
    out = []
    for k in range(6):
        x = -0.62 + k * 0.248
        bm = bmesh.new()
        C.box_bm(bm, 0.022, 0.016, 0.003, center=(x, 0.028, 0.1685))                    # head
        C.box_bm(bm, 0.013, 0.0075, 0.020, center=(x, 0.028, 0.157))                     # shank
        for s in (-1, 1):                                                                # barbs
            C.box_bm(bm, 0.003, 0.010, 0.010, center=(x + s * 0.0075, 0.028, 0.153),
                     matrix=None)
        ob = C.mesh_obj("Clip", bm, [nylon])
        C.add_bevel(ob, 0.0009, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


def build():
    paint = P.body_paint()
    raw = P.textured_black("RawPP", rough=0.6, v=0.025)
    black = P.textured_black("SillPP", rough=0.6, v=0.02)
    nylon = C.principled("NylonClip", (0.78, 0.76, 0.70), rough=0.45)
    C.add_noise_bump(nylon, scale=600, strength=0.05, distance=0.0003)
    objs = [shell(paint, raw, black, raw)]
    objs += clips(nylon)
    C.transform_all(objs, Matrix.Rotation(math.radians(-22), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("minigonna", objs, "minigonna.py",
            "side sill cover / side skirt (generic small hatchback): long plastic panel, metallic grey painted upper face "
            "with feature line, grained black lower lip, ends cut to the wheel arches, push clips along the top flange",
            az=14, el=13, lens=70, fill=0.92, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
