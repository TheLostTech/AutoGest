"""Self-locking nut (dado autobloccante / nyloc), generic catalogue image for the whole
family: one M10 nyloc nut in clear zinc plating, seen from above so the white nylon
insert ring held by the crimped round collar is clearly visible. Chamfered hex,
helical thread in the bore below the insert."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

AF = 1.6
HH = 0.62      # hex height
HT = 1.00      # total height
P = 0.15
RMIN = 0.42
RCOL = 0.74    # collar outer radius


def body(zinc):
    a = AF / 2
    rc = a * 0.95
    fhex = M.nut_fn(AF, 0.0, HH, cham1=False)
    fbore = M.int_thread(RMIN, P, cs=[(0.0, 0.56)])

    def fn(tag, r, z, t):
        if tag == "hex":
            return fhex(r, z, t)
        rr = fbore(r, z, t)
        return rr
    prof = [(0.56, 0.0, 0), (rc - 0.02, 0.0, 0)]
    prof += M.hex_side(0.0, HH, a * 1.3, cham1=False)
    prof += [(a * 1.3, HH, 0, "hex")]
    # shoulder from hex top to the collar, collar, rolled-over lip
    prof += [(RCOL + 0.03, HH, 0), (RCOL, HH + 0.03, 0), (RCOL, HT - 0.10, 0)]
    for i in range(1, 10):
        ang = math.pi / 2 * i / 9
        prof.append((RCOL - 0.08 + 0.08 * math.cos(ang), HT - 0.10 + 0.08 * math.sin(ang), 0))
    prof += [(RCOL - 0.12, HT - 0.02, 0), (0.60, HT - 0.03, 0), (0.585, HT - 0.06, 0),
             (0.60, HT - 0.08, 0)]
    # inner pocket wall down to the insert seat (hidden), then the threaded bore
    prof += [(0.64, HT - 0.10, 0), (0.64, HH + 0.06, 0), (0.50, HH + 0.06, 0)]
    n = int((HH + 0.06) / P * 18)
    prof += [(0.0, (HH + 0.06) * (1 - i / n), 0, "bore") for i in range(1, n)]
    ob = M.revolve("NylocBody", prof, [zinc], steps=360, fn=fn)
    C.add_bevel(ob, 0.005, segments=2, angle=50)
    return C.finalize(ob, angle=28)


def insert(nylon):
    ri = 0.395
    z0, z1 = HH + 0.06, HT - 0.075
    prof = [(ri, z0, 0), (0.64, z0, 0), (0.64, z1 - 0.012, 0), (0.62, z1, 0), (ri + 0.03, z1, 0),
            (ri, z1 - 0.03, 0)]
    ob = C.lathe("Insert", prof, [nylon], steps=180)
    C.add_bevel(ob, 0.004, segments=2, angle=40)
    return C.finalize(ob, angle=50)


def build():
    zinc = M.mat_zinc("Zinc")
    nylon = M.mat_plastic("Nylon", (0.66, 0.65, 0.60), rough=0.40, sss=0.25)
    objs = [body(zinc), insert(nylon)]
    M.place(objs, Matrix.Rotation(math.radians(8), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("dado-autobloccante", objs, "dado-autobloccante.py",
            "self-locking nyloc nut M10, clear zinc plated, with white nylon insert ring",
            az=-30, el=40, lens=85, fill=0.84, **M.shoot_kw())
