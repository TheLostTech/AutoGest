"""Ventilated, cross-drilled brake disc with hat, 5 bolt holes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Z_IN0, Z_IN1, Z_OUT0, Z_OUT1 = 0.0, 0.055, 0.135, 0.19
RI, RO = 0.60, 1.0
NV = 36            # vanes
CURVE = 0.28       # vane sweep (rad per unit radius)


def vane_angle(base, r):
    return base + CURVE * (r - RI)


def plate(name, z0, z1, friction_top, iron, mach):
    # friction surface on the outer side of each plate
    c = 0.006
    if friction_top:
        P = [(RI, z0, 0), (RO, z0, 0), (RO, z1 - c, 0), (RO - c, z1, 1), (RI + c, z1, 0), (RI, z1 - c, 0)]
    else:
        P = [(RI, z1, 0), (RI, z0 + c, 0), (RI + c, z0, 1), (RO - c, z0, 0), (RO, z0 + c, 0), (RO, z1, 0)]
    return C.lathe(name, P, [iron, mach], steps=192)


def drills(iron):
    bm = bmesh.new()
    rows = (0.71, 0.80, 0.89)
    for g in range(12):
        for j, r in enumerate(rows):
            base = math.radians(g * 30 + 5 + 10 * j)
            th = vane_angle(base, r)
            M = Matrix.Translation((r * math.cos(th), r * math.sin(th), 0))
            C.cyl_bm(bm, 0.027, -0.1, 0.3, seg=20, matrix=M)
            C.cyl_bm(bm, 0.027, Z_OUT1 - 0.012, Z_OUT1 + 0.02, seg=20, matrix=M, r1=0.045)
            C.cyl_bm(bm, 0.045, Z_IN0 - 0.02, Z_IN0 + 0.012, seg=20, matrix=M, r1=0.027)
    return C.mesh_obj("Drills", bm, [iron])


def vanes(iron):
    bm = bmesh.new()
    n = 8
    for k in range(NV):
        base = math.radians(k * 10)
        frames = []
        for i in range(n + 1):
            r = RI - 0.01 + (RO - 0.012 - RI + 0.01) * i / n
            th = vane_angle(base, r)
            P = Vector((r * math.cos(th), r * math.sin(th), 0))
            T = Vector((math.cos(th), math.sin(th), 0)) + CURVE * r * Vector((-math.sin(th), math.cos(th), 0))
            T.normalize()
            U = Vector((-T.y, T.x, 0))
            V = Vector((0, 0, 1))
            w = 0.026
            sec = [(-w / 2, Z_IN1 - 0.005), (w / 2, Z_IN1 - 0.005), (w / 2, Z_OUT0 + 0.005), (-w / 2, Z_OUT0 + 0.005)]
            frames.append((P, U, V, sec))
        C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Vanes", bm, [iron])
    return C.finalize(ob, angle=30)


def hat(iron, mach):
    P = [(0.50, 0.10, 0), (0.63, 0.10, 0), (0.63, 0.15, 0), (0.595, 0.172, 0), (0.567, 0.172, 0),
         (0.56, 0.185, 0), (0.56, 0.462, 0), (0.545, 0.48, 1), (0.238, 0.48, 0), (0.222, 0.468, 0),
         (0.222, 0.43, 0), (0.50, 0.43, 0)]
    h = C.lathe("Hat", P, [iron, mach], steps=160)
    bm = bmesh.new()
    for k in range(5):
        th = math.radians(90 + 72 * k)
        M = Matrix.Translation((0.38 * math.cos(th), 0.38 * math.sin(th), 0))
        C.cyl_bm(bm, 0.052, 0.3, 0.6, seg=32, matrix=M)
    for th in (math.radians(126), math.radians(306)):
        M = Matrix.Translation((0.38 * math.cos(th), 0.38 * math.sin(th), 0))
        C.cyl_bm(bm, 0.019, 0.3, 0.6, seg=20, matrix=M)
    cut = C.mesh_obj("BoltCut", bm, [iron])
    C.add_boolean(h, cut)
    return C.finalize(h, angle=35, remove=[cut])


def build():
    iron = C.mat_cast_iron("CastIron", rust=0.7)
    mach = C.mat_machined("FrictionRing", color=0.46, rough=0.17, rings=700)
    dr = drills(iron)
    objs = []
    for nm, z0, z1, top in (("Outer", Z_OUT0, Z_OUT1, True), ("Inner", Z_IN0, Z_IN1, False)):
        p = plate(nm, z0, z1, top, iron, mach)
        C.add_boolean(p, dr)
        objs.append(C.finalize(p, angle=35))
    bpy.data.objects.remove(dr, do_unlink=True)
    objs.append(vanes(iron))
    objs.append(hat(iron, mach))
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("disco-freno", objs, "disco-freno.py",
            "ventilated cross-drilled brake disc with hat, 5 bolt holes, cast iron with polished friction ring",
            az=30, el=14, lens=70, fill=0.82)
