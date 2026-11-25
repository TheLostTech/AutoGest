"""Flat washers (rondelle), generic catalogue image for the whole family: three M10 plain
washers in clear zinc plating stacked in a loose fan, stamped profile with one rounded
(die-roll) edge and one sharp edge."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

RI = 0.53
RO = 1.0
T = 0.2


def washer(zinc, name="Washer"):
    rr = 0.035
    prof = [(RI + 0.01, 0.0, 0), (RO - 0.004, 0.0, 0), (RO, 0.006, 0), (RO, T - rr, 0)]
    for i in range(1, 6):
        a = math.pi / 2 * i / 5
        prof.append((RO - rr + rr * math.cos(a), T - rr + rr * math.sin(a), 0))
    prof += [(RI + rr, T, 0)]
    for i in range(1, 6):
        a = math.pi / 2 + math.pi / 2 * i / 5
        prof.append((RI + rr + rr * math.cos(a), T - rr + rr * math.sin(a), 0))
    prof += [(RI, 0.006, 0)]
    ob = C.lathe(name, prof, [zinc], steps=200)
    C.add_bevel(ob, 0.003, segments=2, angle=40)
    return C.finalize(ob, angle=40)


def build():
    zinc = M.mat_zinc("Zinc")
    objs = []
    for i, (dx, dy, rz) in enumerate(((0.0, 0.0, 0), (0.42, 0.20, 70), (0.80, 0.52, 140))):
        w = washer(zinc, "Washer%d" % i)
        w.matrix_world = Matrix.Translation((dx, dy, i * T)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        objs.append(w)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("rondella", objs, "rondella.py",
            "three flat washers M10, clear zinc plated, stacked in a loose fan",
            az=-30, el=42, lens=85, fill=0.86, **M.shoot_kw())
