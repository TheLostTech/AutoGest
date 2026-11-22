"""Hex head bolt (bullone), generic catalogue image for the whole family: one M10 x 40
partially threaded bolt in clear zinc plating, lying on its side. Real helical thread
with run-out and chamfered tip, hex head with the 30-degree chamfer arcs on the flats,
washer face, raised grade-mark lines on the head (no text)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

D = 1.0        # nominal diameter (cm)
P = 0.15       # pitch
L = 4.0        # length under head
B = 2.6        # thread length
AF = 1.6       # across flats
K = 0.64       # head height


def head(zinc):
    a = AF / 2
    rc = a * 0.95
    k0 = 0.04            # washer face height

    def fn(tag, r, z, t):
        rr = M.hex_r(t, AF, corner=0.975)
        rr = min(rr, rc + (z + K) * 1.732)               # top chamfer
        rr = min(rr, a * 1.12 + (-k0 - z) * 1.732)       # tiny bearing-side chamfer
        return rr
    prof = [(0.0, -K - 0.006, 0), (0.30, -K - 0.004, 0), (rc - 0.02, -K, 0)]
    prof += M.seg(rc + 0.2, -K, rc + 0.2, -K + 0.12, 18, tag="hex")
    prof += M.seg(rc + 0.2, -K + 0.12, rc + 0.2, -k0, 8, tag="hex", include_end=True)
    prof += [(0.745, -k0, 0), (0.745, -0.01, 0), (0.73, 0.0, 0), (0.45, 0.0, 0), (0.0, 0.0, 0)]
    ob = M.revolve("Head", prof, [zinc], steps=360, fn=fn)
    C.add_bevel(ob, 0.006, segments=2, angle=50)
    return C.finalize(ob, angle=50)


def shank(zinc):
    r = D / 2
    z0 = L - B
    f = M.ext_thread(r, P, z0, L, runout0=1.6, tip_cham=(L, r - 0.115))

    def fn(tag, rr, z, t):
        return f(rr, z, t)
    prof = [(0.0, -0.02, 0), (0.545, -0.02, 0), (0.545, 0.0, 0), (0.52, 0.012, 0), (r, 0.04, 0),
            (r, z0 - 0.3, 0)]
    prof += M.thread_samples(z0 - 0.05, L, P, per_pitch=18)
    prof += [(r - 0.13, L + 0.004, 0), (0.2, L + 0.008, 0), (0.0, L + 0.008, 0)]
    ob = M.revolve("Shank", prof, [zinc], steps=160, fn=fn)
    return C.finalize(ob, angle=80)


def grade_marks(zinc):
    """three short raised radial lines on the head top (property-class mark, no text)"""
    bm = bmesh.new()
    for i in range(3):
        th = math.radians(90 + 120 * i)
        Mx = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.40, 0, -K - 0.004))
        C.box_bm(bm, 0.22, 0.032, 0.022, matrix=Mx)
    ob = C.mesh_obj("Marks", bm, [zinc])
    C.add_bevel(ob, 0.007, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def build():
    zinc = M.mat_zinc("Zinc")
    objs = [head(zinc), shank(zinc), grade_marks(zinc)]
    M.lie_on_x(objs, AF / 2, D / 2, L + K)
    M.place(objs, Matrix.Rotation(math.radians(-5), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("bullone", objs, "bullone.py",
            "hex head bolt M10x40, partially threaded, clear zinc plated, with grade-mark lines on the head",
            az=-38, el=30, lens=85, fill=0.9, **M.shoot_kw())
