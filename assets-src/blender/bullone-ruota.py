"""Wheel bolt (bullone ruota), generic catalogue image for the whole family: one M12 x 1.5
wheel bolt with a 60-degree conical seat, 17 mm hex head, long helical thread and an
unthreaded pilot tip, bright zinc plating, lying on its side with head and cone
toward the camera."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

R = 0.6
P = 0.15
L = 2.9        # under the cone seat
AF = 1.7
ZC = -0.62     # cone big end
RC = 1.06      # collar radius above the cone
ZH0 = -0.70    # hex bottom
ZH1 = -1.36    # hex top


def head(mat):
    a = AF / 2
    rc = a * 0.95

    def fn(tag, r, z, t):
        rr = M.hex_r(t, AF, corner=0.975)
        rr = min(rr, rc + (z - ZH1) * 1.732)
        rr = min(rr, a * 1.10 + (ZH0 - z) * 1.732)
        return rr
    t30 = math.tan(math.radians(30))
    prof = [(0.0, 0.02, 0), (R + 0.06, 0.02, 0), (R + 0.06, 0.0, 0), (R + 0.075, -0.012, 0)]
    # 60-degree included cone seat
    for i in range(1, 13):
        z = -0.012 + (ZC + 0.02 + 0.012) * i / 12
        prof.append((R + 0.075 + (-0.012 - z) * t30 * 1.0 + 0.0, z, 0))
    rtop = prof[-1][0]
    prof += [(rtop + 0.015, ZC, 0), (RC, ZC - 0.015, 0), (RC, ZH0 + 0.012, 0), (RC - 0.02, ZH0, 0),
             (a * 1.02, ZH0, 0)]
    zs = [ZH0 + (ZH1 + 0.12 - ZH0) * i / 8 for i in range(0, 8)]
    zs += [ZH1 + 0.12 * (1 - i / 16) for i in range(0, 16)]
    prof += [(a * 1.3, z, 0, "hex") for z in zs]
    prof += [(rc - 0.02, ZH1, 0), (0.45, ZH1 - 0.008, 0), (0.0, ZH1 - 0.012, 0)]
    ob = M.revolve("WheelBoltHead", prof, [mat], steps=360, fn=fn)
    C.add_bevel(ob, 0.005, segments=2, angle=50)
    return C.finalize(ob, angle=50)


def shank(mat):
    zt0, zt1 = 0.25, L - 0.30
    f = M.ext_thread(R, P, zt0, zt1, runout0=1.2, runout1=0.0, tip_cham=(zt1 + 0.07, R - 0.15))
    prof = [(0.0, -0.05, 0), (R + 0.06, -0.05, 0), (R + 0.06, 0.0, 0), (R + 0.02, 0.03, 0), (R - 0.01, 0.06, 0),
            (R - 0.01, zt0, 0)]
    prof += M.thread_samples(zt0, zt1 + 0.02, P, per_pitch=18)
    prof += [(0.46, zt1 + 0.06, 0), (0.46, L - 0.04, 0), (0.42, L, 0), (0.0, L + 0.004, 0)]
    ob = M.revolve("Shank", prof, [mat], steps=160, fn=lambda tag, rr, z, t: f(rr, z, t))
    return C.finalize(ob, angle=80)


def build():
    zinc = M.mat_zinc("Zinc", tint=(0.56, 0.57, 0.60), rough=0.20)
    objs = [head(zinc), shank(zinc)]
    M.place(objs, Matrix.Translation((0, 0, -ZH1)))
    M.lie_on_x(objs, RC, R, L - ZH1)
    M.place(objs, Matrix.Rotation(math.radians(-8), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("bullone-ruota", objs, "bullone-ruota.py",
            "wheel bolt M12x1.5 with 60-degree conical seat and 17 mm hex head, bright zinc plated",
            az=-40, el=26, lens=85, fill=0.9, **M.shoot_kw())
