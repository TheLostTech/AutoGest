"""Hex nut (dado), generic catalogue image for the whole family: one M10 hex nut in
clear zinc plating standing on a face, seen from above so the threaded bore shows.
Double-chamfered hex (30-degree arcs on the flats), 90-degree countersinks, real
helical internal thread."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

AF = 1.6
MH = 0.84
P = 0.15
RMIN = 0.42


def nut(zinc, af=AF, h=MH, rmin=RMIN, pitch=P, cs=0.53, name="Nut"):
    a = af / 2
    rc = a * 0.95
    fhex = M.nut_fn(af, 0.0, h)
    fbore = M.int_thread(rmin, pitch, cs=[(0.0, cs), (h, cs)])

    def fn(tag, r, z, t):
        return fhex(r, z, t) if tag == "hex" else fbore(r, z, t)
    prof = [(cs, 0.0, 0), (rc - 0.02, 0.0, 0)]
    prof += M.hex_side(0.0, h, a * 1.3)
    prof += [(rc - 0.02, h, 0), (cs, h, 0)]
    n = int(h / pitch * 18)
    prof += [(0.0, h - h * i / n, 0, "bore") for i in range(1, n)]
    ob = M.revolve(name, prof, [zinc], steps=360, fn=fn)
    C.add_bevel(ob, 0.005, segments=2, angle=50)
    return C.finalize(ob, angle=28)


def build():
    zinc = M.mat_zinc("Zinc")
    ob = nut(zinc)
    ob.matrix_world = Matrix.Rotation(math.radians(8), 4, "Z")
    return [ob]


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("dado", objs, "dado.py",
            "hex nut M10, clear zinc plated, double chamfered, with internal thread",
            az=-30, el=38, lens=85, fill=0.84, **M.shoot_kw())
