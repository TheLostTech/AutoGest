"""Self-tapping sheet-metal screws (viti autofilettanti da lamiera), generic catalogue image
for the whole family: three ST4.8 hex-washer-head tapping screws in clear zinc plating,
one standing on its head with the gimlet point up, two lying in front. Coarse sharp
helical thread running out onto the pointed tip, hex head with integrated washer."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

RMAJ = 0.24
P = 0.16
L = 1.9
AF = 0.8
KH = 0.36      # head top (hex) height above bearing face
RW = 0.50      # washer radius
TW = 0.07      # washer thickness


def head(zinc):
    a = AF / 2

    def fn(tag, r, z, t):
        rr = M.hex_r(t, AF, corner=0.975)
        return min(rr, a * 0.94 + (z + KH) * 1.732)
    prof = [(0.0, 0.0, 0), (RW - 0.02, 0.0, 0), (RW, -0.015, 0), (RW - 0.005, -TW + 0.015, 0),
            (RW - 0.03, -TW, 0), (a * 1.08, -TW - 0.012, 0)]
    z0 = -TW - 0.012
    zs = [z0 + (-KH + 0.08 - z0) * i / 10 for i in range(0, 10)]
    zs += [-KH + 0.08 * (1 - i / 16) for i in range(0, 16)]
    prof += [(a * 1.3, z, 0, "hex") for z in zs]
    prof += [(a * 0.92, -KH, 0), (0.0, -KH - 0.004, 0)]
    ob = M.revolve("HexWasherHead", prof, [zinc], steps=360, fn=fn)
    C.add_bevel(ob, 0.003, segments=2, angle=50)
    return C.finalize(ob, angle=50)


def shank(zinc):
    f = M.ext_thread(RMAJ, P, 0.05, L, depth=0.075, runout0=0.8, sharp=2.2, tip_cone=(L, 0.42))
    prof = [(0.0, -0.02, 0), (0.25, -0.02, 0), (0.25, 0.0, 0), (0.22, 0.02, 0), (0.175, 0.05, 0)]
    prof += M.thread_samples(0.05, L - 0.004, P, per_pitch=22)
    prof += [(0.0, L, 0)]
    ob = M.revolve("Shank", prof, [zinc], steps=144, fn=lambda tag, rr, z, t: f(rr, z, t))
    return C.finalize(ob, angle=80)


def screw(zinc):
    return [head(zinc), shank(zinc)]


def build():
    zinc = M.mat_zinc("Zinc")
    objs = []
    # standing on the washer face, point up
    s = screw(zinc)
    M.place(s, Matrix.Translation((0.55, 1.05, KH)) @ Matrix.Rotation(math.radians(12), 4, "Z"))
    objs += s
    # two lying in front, heads to the left
    for (x, y, rz, roll) in ((-0.55, 0.05, -12, 0.3), (0.05, -0.95, 6, 1.1)):
        s = screw(zinc)
        M.lie_on_x(s, RW, RMAJ, L + KH, roll=roll)
        M.drop_to_ground(s)
        M.place(s, Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rz), 4, "Z"))
        objs += s
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("vite-lamiera", objs, "vite-lamiera.py",
            "three self-tapping sheet metal screws, hex washer head, clear zinc plated, pointed tip",
            az=-32, el=30, lens=85, fill=0.88, **M.shoot_kw())
