"""Tyre pressure (TPMS) sensor, clamp-in type: anodised aluminium valve stem with
rubber grommet, washer, hex nut and black knurled cap, screwed to the curved black
plastic sensor housing that sits on the rim well. No markings. Lathe profiles for the
stem; housing is a bevelled box bent to the rim radius."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 1 cm, housing along X lying on the floor, stem rising at the -X end


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


STEM_O = Vector((-0.25, 0.0, 0.95))
STEM_D = Vector((-0.62, 0.0, 0.78)).normalized()


def rrect(w, h, rt, rb, n=8):
    """rounded rectangle section (u across, v up), bottom at v=0; top corners rt, bottom rb"""
    pts = []
    for cx, cv, r, a0 in ((w / 2 - rb, rb, rb, -90), (w / 2 - rt, h - rt, rt, 0),
                          (-w / 2 + rt, h - rt, rt, 90), (-w / 2 + rb, rb, rb, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def housing(plastic, dark):
    out = []
    bm = bmesh.new()
    x0, x1, N = -0.2, 4.2, 60
    frames = []
    for i in range(N + 1):
        x = x0 + (x1 - x0) * i / N
        e = min(x - x0, x1 - x) / 0.35          # rounded ends: shrink the section near both ends
        k = math.sqrt(max(0.0, 1 - (1 - min(e, 1.0)) ** 2)) if e < 1 else 1.0
        k = 0.55 + 0.45 * k
        t = max(0.0, x - 2.0) / 2.2
        w = 2.45 * (1 - 0.14 * t) * k
        h = 1.30 * (1 - 0.12 * t) * (0.7 + 0.3 * k)
        sec = rrect(w, h, min(0.55, w / 2 - 0.01) * (0.6 + 0.4 * k), 0.16)
        z0 = 0.02 + 0.045 * (x - 2.0) ** 2 * 0.9
        frames.append((Vector((x, 0, z0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Housing", bm, [plastic])
    out.append(C.finalize(ob, angle=50))
    # moulded round cap (battery side) on top
    P = [(0.0, 0.0, 0), (0.62, 0.0, 0), (0.62, 0.05, 0), (0.58, 0.08, 0), (0.0, 0.08, 0)]
    ob = C.lathe("Lid", P, [dark], steps=64)
    ob.matrix_world = Matrix.Translation((2.45, 0, 1.25))
    out.append(C.finalize(ob, angle=40))
    # boss where the stem screws on
    ob = C.lathe("Boss", [(0.0, -0.9, 0), (0.78, -0.9, 0), (0.86, -0.82, 0), (0.86, 0.0, 0), (0.0, 0.0, 0)], [plastic], steps=64)
    ob.matrix_world = axis_mat(STEM_O, STEM_D)
    C.add_bevel(ob, 0.05, segments=3, angle=30)
    out.append(C.finalize(ob, angle=40))
    return out


def stem(alu, rubber, cap_m, steel):
    out = []
    M = axis_mat(STEM_O, STEM_D)
    # stem body: head, threaded shank, neck, valve thread
    P = [(0.0, -0.05, 0), (0.56, -0.05, 0), (0.6, 0.0, 0), (0.6, 0.32, 0), (0.555, 0.36, 0), (0.555, 0.62, 0)]
    z = 0.62
    for i in range(28):
        P += [(0.575, z + 0.035, 0), (0.535, z + 0.07, 0)]
        z += 0.07
    P += [(0.50, z + 0.06, 0), (0.42, z + 0.12, 0), (0.40, z + 0.55, 0), (0.0, z + 0.55, 0)]
    zt = z
    ob = C.lathe("Stem", P, [alu], steps=64)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=50))
    # rubber grommet (sits against the inside of the rim)
    P = [(0.54, 0.30, 0), (0.80, 0.32, 0), (0.86, 0.40, 0), (0.80, 0.56, 0), (0.54, 0.58, 0)]
    ob = C.lathe("Grommet", P, [rubber], steps=64)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=50))
    # washer + hex nut further out (rim thickness gap between grommet and washer)
    P = [(0.58, 0.86, 0), (0.95, 0.86, 0), (0.95, 0.94, 0), (0.58, 0.94, 0)]
    ob = C.lathe("Washer", P, [steel], steps=64)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=50))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.78, 0.94, 1.42, seg=6)
    nut = C.mesh_obj("Nut", bm, [alu])
    nut.matrix_world = M
    hb = bmesh.new()
    C.cyl_bm(hb, 0.57, 0.5, 2.0, seg=48)
    hole = C.mesh_obj("NutHole", hb, [alu])
    hole.matrix_world = M
    b = C.add_boolean(nut, hole)
    b.use_self = True
    C.add_bevel(nut, 0.06, segments=2, angle=30)
    out.append(C.finalize(nut, angle=35, remove=[hole]))
    # knurled cap
    knurl = lambda r, zz, t: r + (0.025 if (r > 0.44 and math.cos(30 * t) > 0) else 0.0)
    P = [(0.0, zt + 0.82, 0), (0.36, zt + 0.82, 0), (0.43, zt + 0.77, 0), (0.46, zt + 0.70, 0),
         (0.46, zt + 0.22, 0), (0.44, zt + 0.17, 0), (0.0, zt + 0.17, 0)]
    ob = C.lathe("Cap", P, [cap_m], steps=240, mod=knurl)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=50))
    # fixing screw in the housing boss (torx head visible on the side)
    bm = bmesh.new()
    Ms = Matrix.Translation(STEM_O + STEM_D * -0.45) @ Matrix.Rotation(math.radians(-90), 4, "X")
    C.cyl_bm(bm, 0.30, 0.86, 1.02, seg=32, matrix=Ms)
    sc = C.mesh_obj("Screw", bm, [steel])
    C.add_bevel(sc, 0.03, segments=2, angle=30)
    out.append(C.finalize(sc, angle=35))
    return out


def build():
    plastic = C.mat_black_plastic("HousingPA", rough=0.42, color=0.03)
    dark = C.mat_black_plastic("Dark", rough=0.55, color=0.045)
    alu = C.principled("AnodAlu", (0.62, 0.63, 0.65), metallic=1.0, rough=0.24)
    C.add_radial_aniso(alu, 0.5, "Z")
    C.add_noise_bump(alu, scale=900, strength=0.03, distance=0.0003)
    rubber = C.mat_rubber("Grommet")
    cap = C.mat_black_plastic("CapPA", rough=0.35, color=0.025)
    steel = C.principled("Steel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.3)
    objs = housing(plastic, dark) + stem(alu, rubber, cap, steel)
    C.transform_all(objs, Matrix.Rotation(math.radians(-140), 4, "Z"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("sensore-tpms", objs, "sensore-tpms.py",
            "TPMS tyre pressure sensor: aluminium clamp-in valve stem with nut and black cap on a black plastic sensor housing",
            az=30, el=30, lens=70, fill=0.82,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
