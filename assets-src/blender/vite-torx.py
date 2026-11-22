"""Torx flange screw (vite Torx), generic catalogue image for the whole family: one M6 x 20
button-flange screw with a hexalobular (Torx) socket, dull silver zinc-flake coating,
lying on its side with the head turned toward the camera. Domed head, thin integrated
flange, helical thread with chamfered tip."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

D = 0.6
P = 0.10
L = 2.0
RFL = 0.70     # flange radius
RD = 0.54      # dome base radius
ZM = -0.31     # socket mouth height (head top)
A_OUT, A_IN = 0.278, 0.200
DEPTH = 0.20


def head(mat):
    def fn(tag, r, z, t):
        rr = M.torx_r(t, A_OUT, A_IN, phase=math.radians(15))
        d = z - ZM
        rr = max(rr, A_OUT * 1.06 - d * 1.0)
        rr = min(rr, max(0.0, (ZM + DEPTH + 0.09 - z) * 1.73))
        return rr
    prof = [(0.0, 0.0, 0), (RFL - 0.02, 0.0, 0), (RFL, -0.015, 0), (RFL, -0.05, 0),
            (RFL - 0.02, -0.068, 0), (RFL - 0.06, -0.078, 0)]
    n = 18
    for i in range(n + 1):
        r = RD - (RD - A_OUT * 1.12) * i / n
        q = max(0.0, 1 - (r / (RD + 0.03)) ** 2) ** 0.5
        q0 = max(0.0, 1 - (A_OUT * 1.12 / (RD + 0.03)) ** 2) ** 0.5
        qe = max(0.0, 1 - (RD / (RD + 0.03)) ** 2) ** 0.5
        prof.append((r, -0.085 - (-ZM - 0.085) * (q - qe) / (q0 - qe), 0))
    zs = [ZM + (DEPTH + 0.09) * i / 36 for i in range(0, 37)]
    prof += [(0.0, z, 0, "sock") for z in zs]
    ob = M.revolve("TorxHead", prof, [mat], steps=360, fn=fn)
    C.add_bevel(ob, 0.003, segments=2, angle=50)
    return C.finalize(ob, angle=50)


def shank(mat):
    r = D / 2
    f = M.ext_thread(r, P, 0.08, L, runout0=1.2, tip_cham=(L, r - 0.075))
    prof = [(0.0, -0.02, 0), (0.34, -0.02, 0), (0.34, 0.0, 0), (0.32, 0.012, 0), (r - 0.03, 0.03, 0),
            (r - 0.03, 0.06, 0)]
    prof += M.thread_samples(0.06, L, P, per_pitch=18)
    prof += [(r - 0.085, L + 0.003, 0), (0.1, L + 0.006, 0), (0.0, L + 0.006, 0)]
    ob = M.revolve("Shank", prof, [mat], steps=144, fn=lambda tag, rr, z, t: f(rr, z, t))
    return C.finalize(ob, angle=80)


def build():
    zf = M.mat_zinc_flake("ZincFlake")
    objs = [head(zf), shank(zf)]
    M.lie_on_x(objs, RFL, D / 2, L + 0.3)
    M.place(objs, Matrix.Rotation(math.radians(15), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("vite-torx", objs, "vite-torx.py",
            "Torx button flange screw M6x20, silver zinc-flake coating, hexalobular socket",
            az=-45, el=26, lens=85, fill=0.9, **M.shoot_kw())
