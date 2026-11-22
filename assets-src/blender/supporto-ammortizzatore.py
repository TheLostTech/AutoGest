"""Strut top mount (supporto ammortizzatore / cuscinetto duomo) for a McPherson front
strut of a small car: three-lobed zinc-plated pressed-steel top plate with three
passivated M8 studs and a pressed centre dome, bonded rubber body, lower steel cup,
central steel sleeve for the damper rod, and the plastic thrust bearing with its
upper spring seat underneath. Lathe profiles, extruded plate outline."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm, Z up, plate top at z ~0.035
STUD_R = 0.47


def prism(bm, poly, z0, z1):
    vb = [bm.verts.new((x, y, z0)) for x, y in poly]
    vt = [bm.verts.new((x, y, z1)) for x, y in poly]
    m = len(poly)
    bm.faces.new(vb[::-1])
    bm.faces.new(vt)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))


def lobe_outline(n=240):
    pts = []
    for i in range(n):
        t = math.tau * i / n
        c = math.cos(3 * (t - math.radians(90)))
        r = 0.43 + 0.17 * (max(0.0, c) ** 2.2)  # three rounded ears, round body between them
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


def plate(zinc):
    out = []
    bm = bmesh.new()
    prism(bm, lobe_outline(), 0.0, 0.035)
    ob = C.mesh_obj("TopPlate", bm, [zinc])
    hb = bmesh.new()
    C.cyl_bm(hb, 0.20, -0.2, 0.2, seg=96)
    holes = C.mesh_obj("PlateHole", hb, [zinc])
    b = C.add_boolean(ob, holes)
    b.use_self = True
    b.use_hole_tolerant = True
    C.add_bevel(ob, 0.008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[holes]))
    # pressed centre dome with the rod hole
    P = [(0.085, 0.115, 0), (0.15, 0.115, 0), (0.185, 0.10, 0), (0.205, 0.06, 0), (0.215, 0.035, 0),
         (0.23, 0.02, 0), (0.23, 0.0, 0), (0.195, 0.0, 0), (0.18, 0.05, 0), (0.14, 0.085, 0), (0.085, 0.085, 0)]
    out.append(C.finalize(C.lathe("Dome", P, [zinc], steps=128), angle=40))
    return out


def studs(yzinc):
    out = []
    for k in range(3):
        a = math.radians(90 + 120 * k)
        P = [(0.0, -0.035, 0), (0.07, -0.035, 0), (0.07, -0.005, 0), (0.042, 0.0, 0), (0.042, 0.06, 0)]
        z = 0.06
        for i in range(15):
            P += [(0.043, z + 0.0075, 0), (0.037, z + 0.015, 0)]
            z += 0.015
        P += [(0.03, z + 0.016, 0), (0.0, z + 0.016, 0)]
        ob = C.lathe("Stud", P, [yzinc], steps=32)
        ob.matrix_world = Matrix.Translation((STUD_R * math.cos(a), STUD_R * math.sin(a), 0.035))
        out.append(C.finalize(ob, angle=50))
    return out


def body(rubber, zinc, steel, plastic, race):
    out = []
    # bonded rubber body, slightly bulged with a moulded groove
    P = [(0.09, -0.30, 0), (0.33, -0.30, 0), (0.37, -0.27, 0), (0.405, -0.22, 0), (0.42, -0.17, 0),
         (0.405, -0.145, 0), (0.41, -0.12, 0), (0.425, -0.08, 0), (0.42, -0.03, 0), (0.39, -0.005, 0),
         (0.37, 0.005, 0), (0.09, 0.005, 0)]
    out.append(C.finalize(C.lathe("Rubber", P, [rubber], steps=160), angle=50))
    # rubber lip visible through the plate hole + steel sleeve for the rod
    P = [(0.09, 0.0, 0), (0.20, 0.0, 0), (0.20, 0.08, 0), (0.14, 0.085, 0), (0.09, 0.085, 0)]
    out.append(C.finalize(C.lathe("RubberCore", P, [rubber], steps=128), angle=50))
    P = [(0.062, -0.34, 0), (0.092, -0.34, 0), (0.092, 0.125, 0), (0.08, 0.135, 0), (0.062, 0.135, 0)]
    out.append(C.finalize(C.lathe("Sleeve", P, [steel], steps=96), angle=40))
    # lower steel cup
    P = [(0.17, -0.345, 0), (0.37, -0.345, 0), (0.395, -0.33, 0), (0.40, -0.29, 0), (0.39, -0.265, 0),
         (0.36, -0.26, 0), (0.36, -0.30, 0), (0.17, -0.30, 0)]
    out.append(C.finalize(C.lathe("LowerCup", P, [zinc], steps=160), angle=35))
    # thrust bearing: steel races + plastic housing with upper spring seat
    P = [(0.18, -0.395, 0), (0.33, -0.395, 0), (0.33, -0.345, 0), (0.18, -0.345, 0)]
    out.append(C.finalize(C.lathe("Race", P, [race], steps=128), angle=40))
    ribs = lambda r, z, t: r + (0.010 if (r > 0.40 and z < -0.43 and math.cos(36 * t) > 0.55) else 0.0)
    P = [(0.17, -0.53, 0), (0.36, -0.53, 0), (0.395, -0.515, 0), (0.41, -0.49, 0), (0.41, -0.445, 0),
         (0.50, -0.435, 0), (0.535, -0.42, 0), (0.545, -0.395, 0), (0.53, -0.38, 0), (0.42, -0.38, 0),
         (0.36, -0.372, 0), (0.345, -0.36, 0), (0.345, -0.40, 0), (0.17, -0.40, 0)]
    out.append(C.finalize(C.lathe("Bearing", P, [plastic], steps=288, mod=ribs), angle=40))
    return out


def build():
    zinc = C.principled("ZincPlate", (0.58, 0.59, 0.60), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=180, strength=0.06, distance=0.0008, rough_var=0.08)
    yzinc = C.principled("YellowZinc", C.srgb("#A39B78"), metallic=1.0, rough=0.32)
    C.add_noise_bump(yzinc, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    steel = C.mat_machined("SleeveSteel", color=0.45, rough=0.3)
    rubber = C.mat_rubber("MountRubber")
    plastic = C.mat_black_plastic("BearingPA", rough=0.5, color=0.05)
    race = C.principled("RaceSteel", (0.35, 0.35, 0.36), metallic=1.0, rough=0.35)
    objs = plate(zinc) + studs(yzinc) + body(rubber, zinc, steel, plastic, race)
    C.transform_all(objs, Matrix.Rotation(math.radians(-12), 4, "Z"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("supporto-ammortizzatore", objs, "supporto-ammortizzatore.py",
            "strut top mount: three-lobed zinc steel plate with three studs, bonded rubber body, centre sleeve, plastic thrust bearing with spring seat",
            az=28, el=30, lens=70, fill=0.80,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
