"""Stud bolt (prigioniero), generic catalogue image for the whole family: one M8 double-end
stud in clear zinc plating lying diagonally: helical threads at both ends (longer nut
end, shorter tap end), plain reduced shank in the middle, chamfered ends."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

R = 0.4
P = 0.125
L = 5.0
B1 = 1.25     # tap end thread
B2 = 1.9      # nut end thread
RS = 0.36     # plain shank radius


def stud(zinc):
    f1 = M.ext_thread(R, P, 0.0, B1, runout1=1.4, tip_cham=(0.0, R - 0.09))
    f2 = M.ext_thread(R, P, L - B2, L, runout0=1.4, tip_cham=(L, R - 0.09))

    def fn(tag, rr, z, t):
        return f1(rr, z, t) if tag == "a" else f2(rr, z, t)
    prof = [(0.0, -0.006, 0), (0.12, -0.006, 0), (R - 0.10, -0.003, 0)]
    prof += M.thread_samples(0.0, B1, P, tag="a", per_pitch=18)
    prof += [(R - 0.005, B1 + 0.02, 0), (RS + 0.01, B1 + 0.06, 0), (RS, B1 + 0.10, 0),
             (RS, L - B2 - 0.10, 0), (RS + 0.01, L - B2 - 0.06, 0), (R - 0.005, L - B2 - 0.02, 0)]
    prof += M.thread_samples(L - B2, L, P, tag="b", per_pitch=18)
    prof += [(R - 0.10, L + 0.003, 0), (0.12, L + 0.006, 0), (0.0, L + 0.006, 0)]
    ob = M.revolve("Stud", prof, [zinc], steps=160, fn=fn)
    return C.finalize(ob, angle=80)


def build():
    zinc = M.mat_zinc("Zinc")
    ob = stud(zinc)
    objs = [ob]
    M.place(objs, Matrix.Translation((-L / 2, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
            @ Matrix.Translation((0, 0, 0)))
    M.place(objs, Matrix.Rotation(math.radians(-38), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("prigioniero", objs, "prigioniero.py",
            "double-end stud bolt M8, clear zinc plated, threaded at both ends with plain shank",
            az=-20, el=34, lens=85, fill=0.92, **M.shoot_kw())
