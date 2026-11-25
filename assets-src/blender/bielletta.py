"""Stabiliser link (bielletta barra stabilizzatrice) as removed from a small car: zinc-
plated steel rod pressed into two black ball-joint housings, rubber boots, threaded
ball studs with a flange collar and an internal hex in the tip for counter-holding, a
zinc flange nut on each stud. Lying on the floor with one stud pointing up and the
other turned towards the camera. 1 unit ~ 10 cm (about 24 cm long)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

XL = 1.10            # housing centres at x = +/-XL
RR = 0.058           # rod radius
ZC = 0.165           # rod axis height when lying on the housings


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=48, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def joint(sx, ang, house, rubber, stud_m, zinc):
    """ball joint at x = sx*XL; stud axis in the YZ plane, tilted by ang from +Z"""
    out = []
    o = Vector((sx * XL, 0, ZC))
    ax = Vector((0, -math.sin(ang), math.cos(ang)))
    # housing: cup around the ball, axis = stud axis, with a boss towards the rod
    P = [(0.0, -0.13, 0), (0.12, -0.13, 0), (0.16, -0.10, 0), (0.165, -0.02, 0), (0.15, 0.07, 0), (0.12, 0.10, 0), (0.0, 0.10, 0)]
    hs = lathe_at("Housing", P, [house], o, ax, steps=64)
    out.append(C.finalize(hs, angle=40))
    P = [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.095, 0.03, 0), (0.095, 0.20, 0), (0.075, 0.24, 0), (0.0, 0.24, 0)]
    out.append(C.finalize(lathe_at("Boss", P, [house], o, (-sx, 0, 0), steps=48), angle=40))
    # rubber boot from the housing rim to the stud collar
    P = [(0.0, 0.08, 0), (0.125, 0.08, 0), (0.15, 0.12, 0), (0.15, 0.17, 0), (0.12, 0.215, 0), (0.08, 0.24, 0),
         (0.06, 0.26, 0), (0.06, 0.28, 0), (0.0, 0.28, 0)]
    out.append(C.finalize(lathe_at("Boot", P, [rubber], o, ax, steps=64), angle=50))
    # stud: collar (hex flats), plain shank, thread, internal hex in the tip
    bm = bmesh.new()
    C.cyl_bm(bm, 0.098, 0.27, 0.315, seg=6)
    col = C.mesh_obj("Collar", bm, [stud_m])
    col.matrix_world = axis_mat(o, ax)
    C.add_bevel(col, 0.008, segments=2, angle=30)
    out.append(C.finalize(col, angle=35))
    pitch = 0.03

    def thread(r, z, t):
        return r + 0.005 * math.sin(math.tau * z / pitch + t) if (z > 0.38 and r > 0.04) else r
    P = [(0.0, 0.31, 0), (0.06, 0.31, 0), (0.058, 0.36, 0)] + [(0.052, 0.38 + 0.01 * i, 0) for i in range(30)] + \
        [(0.044, 0.685, 0), (0.0, 0.685, 0)]
    st = lathe_at("Stud", P, [stud_m], o, ax, steps=48, mod=thread)
    cb = bmesh.new()
    C.cyl_bm(cb, 0.026, 0.64, 0.8, seg=6)
    hx = C.mesh_obj("HexSocket", cb, [stud_m])
    hx.matrix_world = axis_mat(o, ax)
    boolean(st, hx)
    out.append(C.finalize(st, angle=50, remove=[hx]))
    # flange nut part-way down the thread
    P = [(0.052, 0.52, 0), (0.105, 0.52, 0), (0.105, 0.535, 0), (0.052, 0.535, 0)]
    out.append(C.finalize(lathe_at("NutFlange", P, [zinc], o, ax, steps=48), angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.088, 0.535, 0.61, seg=6)
    nt_ = C.mesh_obj("Nut", bm, [zinc])
    nt_.matrix_world = axis_mat(o, ax) @ Matrix.Rotation(math.radians(15), 4, "Z")
    cb = bmesh.new()
    C.cyl_bm(cb, 0.05, 0.5, 0.7, seg=32)
    hole = C.mesh_obj("NutHole", cb, [zinc])
    hole.matrix_world = axis_mat(o, ax)
    boolean(nt_, hole)
    C.add_bevel(nt_, 0.01, segments=2, angle=30)
    out.append(C.finalize(nt_, angle=35, remove=[hole]))
    return out


def build():
    house = C.mat_black_plastic("HousingPA", rough=0.48, color=0.028)
    rubber = C.mat_rubber("BootRubber")
    rod_m = C.principled("ZincRod", (0.66, 0.65, 0.62), metallic=1.0, rough=0.26)
    C.add_noise_bump(rod_m, scale=500, strength=0.05, distance=0.0005, rough_var=0.07)
    stud_m = C.principled("StudSteel", (0.50, 0.50, 0.51), metallic=1.0, rough=0.3)
    C.add_noise_bump(stud_m, scale=800, strength=0.04, distance=0.0004, rough_var=0.05)
    zinc = C.principled("YellowZinc", (0.70, 0.60, 0.36), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    objs = []
    P = [(0.0, -XL + 0.16, 0), (RR, -XL + 0.16, 0), (RR, XL - 0.16, 0), (0.0, XL - 0.16, 0)]
    objs.append(C.finalize(lathe_at("Rod", P, [rod_m], Vector((0, 0, ZC)), (1, 0, 0), steps=48), angle=40))
    objs += joint(-1, 0.0, house, rubber, stud_m, zinc)
    objs += joint(1, math.radians(65), house, rubber, stud_m, zinc)
    C.transform_all(objs, Matrix.Rotation(math.radians(-24), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("bielletta", objs, "bielletta.py",
            "stabiliser link: steel rod with two ball joints, rubber boots, threaded studs with nuts",
            az=16, el=26, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
