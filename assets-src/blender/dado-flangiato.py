"""Serrated flange nut (dado flangiato), generic catalogue image for the whole family:
two M10 flange nuts in clear zinc plating, one standing upright (hex, conical flange,
threaded bore) and one flipped over to show the radial locking serrations under the
flange."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

AF = 1.5
P = 0.15
RMIN = 0.42
RF = 1.06        # flange radius
ZH0 = 0.26       # hex starts
HT = 1.00        # total height
NT = 34          # serration teeth
TH = 0.028       # tooth height


def nut(zinc):
    a = AF / 2
    rc = a * 0.95
    fhex = M.nut_fn(AF, ZH0, HT, cham0=False)
    fbore = M.int_thread(RMIN, P, cs=[(0.0, 0.55), (HT, 0.55)])

    def fn(tag, r, z, t):
        if tag == "hex":
            return fhex(r, z, t)
        if tag == "serr":
            s = (NT * t / math.tau) % 1.0
            saw = s / 0.8 if s < 0.8 else (1.0 - s) / 0.2
            k = C.smoothstep(0.66, 0.74, r) * C.smoothstep(RF - 0.005, RF - 0.04, r)
            return (r, z - TH * saw * k)
        return fbore(r, z, t)
    prof = [(0.55, 0.0, 0), (0.62, 0.0, 0)]
    prof += [(0.62 + (RF - 0.02 - 0.62) * i / 24, 0.0, 0, "serr") for i in range(1, 25)]
    prof += [(RF, 0.02, 0), (RF, 0.075, 0), (RF - 0.03, 0.095, 0)]
    # conical top of the flange rising to the hex
    for i in range(1, 8):
        u = i / 8
        prof.append((RF - 0.03 - (RF - 0.03 - a * 0.97) * u, 0.095 + (ZH0 - 0.01 - 0.095) * u ** 1.3, 0))
    prof += [(a * 1.3, ZH0, 0, "hex")]
    prof += M.hex_side(ZH0, HT, a * 1.3, cham0=False)[1:]
    prof += [(rc - 0.02, HT, 0), (0.55, HT, 0)]
    n = int(HT / P * 18)
    prof += [(0.0, HT * (1 - i / n), 0, "bore") for i in range(1, n)]
    ob = M.revolve("FlangeNut", prof, [zinc], steps=360, fn=fn)
    C.add_bevel(ob, 0.004, segments=2, angle=55)
    return C.finalize(ob, angle=28)


def build():
    zinc = M.mat_zinc("Zinc")
    up = nut(zinc)
    up.matrix_world = Matrix.Translation((-0.85, -0.45, TH)) @ Matrix.Rotation(math.radians(10), 4, "Z")
    dn = nut(zinc)
    dn.matrix_world = (Matrix.Translation((1.05, 0.75, HT)) @ Matrix.Rotation(math.radians(-25), 4, "Z")
                       @ Matrix.Rotation(math.pi, 4, "X"))
    return [up, dn]


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("dado-flangiato", objs, "dado-flangiato.py",
            "two serrated flange nuts M10, clear zinc plated, one flipped to show the locking serrations",
            az=-25, el=40, lens=85, fill=0.86, **M.shoot_kw())
