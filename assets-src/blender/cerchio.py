"""Alloy wheel rim: 5 split spokes, hub with 5 lug holes, polished lip."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C


def mats():
    paint = C.mat_paint("SilverPaint", (0.33, 0.34, 0.355, 1), rough=0.38, coat=0.5, metallic=1.0)
    C.add_noise_bump(paint, scale=1500, strength=0.03, distance=0.0003)
    lip = C.mat_machined("PolishedLip", color=0.72, rough=0.13, rings=900)
    cap = C.mat_paint("CapBlack", (0.015, 0.015, 0.016, 1), rough=0.2, coat=1.0)
    chrome = C.mat_chrome()
    return paint, lip, cap, chrome


def rim(paint, lip):
    P = [
        (0.905, 0.800, 1), (0.985, 0.800, 1), (1.005, 0.790, 1), (1.012, 0.770, 0),
        (1.000, 0.745, 0), (0.940, 0.735, 0), (0.925, 0.700, 0), (0.925, 0.620, 0),
        (0.905, 0.600, 0), (0.840, 0.520, 0), (0.835, 0.300, 0), (0.905, 0.200, 0),
        (0.925, 0.180, 0), (0.925, 0.070, 0), (0.940, 0.055, 0), (1.000, 0.045, 0),
        (1.012, 0.025, 0), (1.000, 0.000, 0), (0.940, 0.000, 0), (0.885, 0.010, 0),
        (0.875, 0.170, 0), (0.800, 0.280, 0), (0.800, 0.520, 0), (0.860, 0.630, 0),
        (0.872, 0.740, 0), (0.880, 0.785, 1),
    ]
    ob = C.lathe("Rim", P, [paint, lip], steps=160)
    C.add_bevel(ob, 0.004, segments=2, angle=35)
    return C.finalize(ob, angle=38)


def spokes(paint):
    bm = bmesh.new()
    n = 30
    r0, r1 = 0.20, 0.895
    for k in range(5):
        th = math.radians(90 + 72 * k)
        dr = Vector((math.cos(th), math.sin(th), 0))
        pp = Vector((-math.sin(th), math.cos(th), 0))
        for s in (-1, 1):
            def w(t):
                return 0.125 - 0.055 * t + 0.050 * C.smoothstep(0.78, 1.0, t)

            def center(t):
                r = r0 + (r1 - r0) * t
                o = s * (w(t) / 2 * 0.97 + 0.080 * t ** 1.4)
                z = 0.572 + 0.193 * (0.35 * t + 0.65 * t * t)
                return r * dr + o * pp + Vector((0, 0, z))

            frames = []
            for i in range(n + 1):
                t = i / n
                Pc = center(t)
                T = center(min(1, t + 1e-3)) - center(max(0, t - 1e-3))
                T.z = 0
                T.normalize()
                U = Vector((-T.y, T.x, 0))
                V = Vector((0, 0, 1))
                ww = w(t)
                d = 0.15 - 0.05 * t
                sec = [(-0.43 * ww, -d), (0.43 * ww, -d), (0.5 * ww, -0.42 * d),
                       (0.37 * ww, 0.0), (-0.37 * ww, 0.0), (-0.5 * ww, -0.42 * d)]
                frames.append((Pc, U, V, sec))
            C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Spokes", bm, [paint])
    C.add_bevel(ob, 0.006, segments=2, angle=28)
    return C.finalize(ob, angle=30)


def hub(paint, cap, chrome):
    P = [(0.085, 0.580, 0), (0.270, 0.580, 0), (0.300, 0.566, 0), (0.312, 0.535, 0),
         (0.312, 0.380, 0), (0.290, 0.360, 0), (0.085, 0.360, 0)]
    h = C.lathe("Hub", P, [paint], steps=128)
    bm = bmesh.new()
    for k in range(5):
        th = math.radians(90 + 36 + 72 * k)
        M = Matrix.Translation((0.172 * math.cos(th), 0.172 * math.sin(th), 0))
        C.cyl_bm(bm, 0.034, 0.30, 0.70, seg=32, matrix=M)
        C.cyl_bm(bm, 0.034, 0.545, 0.62, seg=32, matrix=M, r1=0.064)  # countersink seat
    cut = C.mesh_obj("LugCut", bm, [paint])
    C.add_boolean(h, cut)
    C.add_bevel(h, 0.004, segments=2, angle=35)
    h = C.finalize(h, angle=35, remove=[cut])
    # centre cap
    Pc = [(0.0, 0.612, 0), (0.055, 0.609, 0), (0.074, 0.600, 1), (0.083, 0.588, 1),
          (0.086, 0.575, 0), (0.086, 0.50, 0), (0.0, 0.50, 0)]
    c = C.lathe("Cap", Pc, [cap, chrome], steps=96)
    c = C.finalize(c, angle=40)
    return [h, c]


def build():
    paint, lip, cap, chrome = mats()
    objs = [rim(paint, lip), spokes(paint)] + hub(paint, cap, chrome)
    # stand the wheel up, face toward -Y (front)
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("cerchio", objs, "cerchio.py",
            "alloy wheel rim, 5 split spokes, 5 lug holes, polished lip, silver metallic",
            az=28, el=12, lens=70, fill=0.82)
