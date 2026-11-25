"""Socket head cap screw (vite a brugola / Allen), generic catalogue image for the whole
family: one M8 x 30 cap screw in black oxide, lying on its side with the head toward the
camera so the hex socket shows. Straight-knurled cylindrical head, chamfered edges,
hex socket with drill-point bottom, fully threaded helical shank."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

D = 0.8
P = 0.125
L = 3.0
DK = 1.3       # head diameter
K = 0.8        # head height
S = 0.6        # socket across flats
TS = 0.42      # socket depth
NK = 60        # knurl ridges


def head(mat):
    R = DK / 2

    def fn(tag, r, z, t):
        if tag == "knurl":
            s = (NK * t / math.tau) % 1.0
            v = 1.0 - abs(2 * s - 1)           # triangle ridges
            k = C.smoothstep(-0.06, -0.14, z) * C.smoothstep(-K + 0.03, -K + 0.10, z)
            return r - 0.012 * (1 - v) * k
        # socket: hex walls, small countersink at the mouth, drill-point bottom
        rr = M.hex_r(t, S, corner=0.99, phase=0.0)
        rr = max(rr, S / 2 * 1.16 - (z + K) * 1.0)
        zb = -K + TS
        rr = min(rr, max(0.0, (zb + 0.17 - z) * 1.73))
        return rr
    prof = [(0.0, 0.0, 0), (R - 0.04, 0.0, 0), (R, -0.04, 0)]
    prof += [(R, -0.04 - (K - 0.12) * i / 30, 0, "knurl") for i in range(1, 30)]
    prof += [(R, -K + 0.08, 0)]
    for i in range(1, 7):
        ang = math.pi / 2 * i / 6
        prof.append((R - 0.08 + 0.08 * math.cos(ang), -K + 0.08 - 0.08 * math.sin(ang), 0))
    prof += [(S / 2 * 1.22, -K, 0)]
    zb = -K + TS
    zs = [-K + (zb + 0.17 + K) * i / 40 for i in range(0, 41)]
    prof += [(0.0, z, 0, "sock") for z in zs]
    ob = M.revolve("CapHead", prof, [mat], steps=360, fn=fn)
    C.add_bevel(ob, 0.004, segments=2, angle=50)
    return C.finalize(ob, angle=50)


def shank(mat):
    r = D / 2
    f = M.ext_thread(r, P, 0.12, L, runout0=1.2, tip_cham=(L, r - 0.09))
    prof = [(0.0, -0.02, 0), (0.44, -0.02, 0), (0.44, 0.0, 0), (0.42, 0.015, 0), (r - 0.04, 0.04, 0),
            (r - 0.04, 0.10, 0)]
    prof += M.thread_samples(0.10, L, P, per_pitch=18)
    prof += [(r - 0.10, L + 0.004, 0), (0.15, L + 0.008, 0), (0.0, L + 0.008, 0)]
    ob = M.revolve("Shank", prof, [mat], steps=160, fn=lambda tag, rr, z, t: f(rr, z, t))
    return C.finalize(ob, angle=80)


def build():
    bo = M.mat_black_oxide("BlackOxide")
    objs = [head(bo), shank(bo)]
    M.lie_on_x(objs, DK / 2, D / 2, L + K)
    M.place(objs, Matrix.Rotation(math.radians(-5), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("vite-brugola", objs, "vite-brugola.py",
            "socket head cap screw M8x30 (Allen), black oxide, knurled head with hex socket",
            az=-42, el=28, lens=85, fill=0.9, **M.shoot_kw())
