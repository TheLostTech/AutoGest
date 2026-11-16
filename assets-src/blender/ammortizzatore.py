"""Shock absorber / coilover: red coil spring (helix curve), black damper body,
chrome rod, rubber bellows, spring seats, top mount with studs, bottom eye bush."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

SR = 0.27      # spring centre-line radius
WR = 0.045     # spring wire radius
Z_LO, Z_HI = 0.62, 2.03   # spring seats (seat surfaces)


def spring(red):
    turns = 6.25
    n = 900
    th_end = 0.9 * math.tau   # closed end coils
    th_tot = turns * math.tau
    # pitch per radian: closed at ends, open in the middle (smooth blend)
    def pitch(th):
        a = C.smoothstep(0, th_end, th) * C.smoothstep(0, th_end, th_tot - th)
        return 1.0 * (1 - a) + 4.2 * a
    zs = [0.0]
    ths = [th_tot * i / n for i in range(n + 1)]
    for i in range(1, n + 1):
        zs.append(zs[-1] + pitch((ths[i] + ths[i - 1]) / 2) * (ths[i] - ths[i - 1]))
    span = (Z_HI - WR) - (Z_LO + WR)
    k = span / zs[-1]
    cu = bpy.data.curves.new("Spring", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = WR
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(n)
    for p, th, z in zip(sp.points, ths, zs):
        p.co = (SR * math.cos(th), SR * math.sin(th), Z_LO + WR + z * k, 1)
    ob = C.link(bpy.data.objects.new("Spring", cu))
    cu.materials.append(red)
    return C.finalize(ob, angle=60)


def body(paint, chrome, rubber, steel):
    out = []
    P = [(0.0, 0.17, 0), (0.10, 0.17, 0), (0.13, 0.21, 0), (0.13, 1.30, 0), (0.115, 1.32, 0),
         (0.075, 1.33, 0), (0.075, 1.36, 0), (0.0, 1.36, 0)]
    out.append(C.finalize(C.lathe("Damper", P, [paint], steps=96), angle=35))
    # lower spring seat (cup)
    P = [(0.12, Z_LO - 0.10, 0), (0.15, Z_LO - 0.10, 0), (0.30, Z_LO - 0.02, 0), (0.345, Z_LO, 0),
         (0.36, Z_LO + 0.05, 0), (0.345, Z_LO + 0.055, 0), (0.33, Z_LO + 0.012, 0), (0.12, Z_LO, 0)]
    out.append(C.finalize(C.lathe("LowerSeat", P, [paint], steps=96), angle=35))
    # chrome rod
    P = [(0.0, 1.30, 0), (0.042, 1.30, 0), (0.042, 2.10, 0), (0.0, 2.10, 0)]
    out.append(C.finalize(C.lathe("Rod", P, [chrome], steps=64), angle=40))
    # bellows boot
    P = [(0.0, 1.66, 0), (0.06, 1.66, 0)]
    z = 1.66
    for i in range(11):
        P += [(0.088, z + 0.016, 0), (0.072, z + 0.032, 0)]
        z += 0.032
    P += [(0.09, 2.03, 0), (0.0, 2.03, 0)]
    out.append(C.finalize(C.lathe("Boot", P, [rubber], steps=96), angle=50))
    # upper seat + top mount
    P = [(0.07, Z_HI + 0.06, 0), (0.33, Z_HI + 0.03, 0), (0.355, Z_HI, 0), (0.36, Z_HI - 0.045, 0),
         (0.345, Z_HI - 0.05, 0), (0.33, Z_HI - 0.01, 0), (0.07, Z_HI, 0)]
    out.append(C.finalize(C.lathe("UpperSeat", P, [paint], steps=96), angle=35))
    P = [(0.0, Z_HI + 0.05, 0), (0.24, Z_HI + 0.05, 0), (0.25, Z_HI + 0.10, 0), (0.23, Z_HI + 0.15, 0), (0.0, Z_HI + 0.15, 0)]
    out.append(C.finalize(C.lathe("MountRubber", P, [rubber], steps=96), angle=40))
    P = [(0.0, Z_HI + 0.15, 0), (0.20, Z_HI + 0.15, 0), (0.215, Z_HI + 0.165, 0), (0.205, Z_HI + 0.18, 0),
         (0.06, Z_HI + 0.19, 0), (0.0, Z_HI + 0.19, 0)]
    out.append(C.finalize(C.lathe("MountPlate", P, [steel], steps=96), angle=40))
    zt = Z_HI + 0.19
    bm = bmesh.new()
    for k in range(3):
        th = math.tau * k / 3 + 0.4
        M = Matrix.Translation((0.14 * math.cos(th), 0.14 * math.sin(th), 0))
        C.cyl_bm(bm, 0.018, zt - 0.01, zt + 0.12, seg=16, matrix=M)
    C.cyl_bm(bm, 0.05, zt - 0.01, zt + 0.05, seg=6)          # centre nut
    C.cyl_bm(bm, 0.022, zt, zt + 0.09, seg=16)               # rod end
    st = C.mesh_obj("Studs", bm, [steel])
    C.add_bevel(st, 0.004, segments=1, angle=30)
    out.append(C.finalize(st, angle=35))
    # bottom eye with rubber bush
    Rx = Matrix.Rotation(math.radians(90), 4, "Y")
    eye = C.lathe("Eye", [(0.06, -0.08, 0), (0.105, -0.08, 0), (0.105, 0.08, 0), (0.06, 0.08, 0)], [paint], steps=64)
    eye.matrix_world = Matrix.Translation((0, 0, 0.105)) @ Rx
    C.add_bevel(eye, 0.008, segments=2, angle=30)
    out.append(C.finalize(eye, angle=35))
    bush = C.lathe("Bush", [(0.03, -0.085, 0), (0.06, -0.085, 0), (0.06, 0.085, 0), (0.03, 0.085, 0)], [rubber], steps=64)
    bush.matrix_world = Matrix.Translation((0, 0, 0.105)) @ Rx
    out.append(C.finalize(bush, angle=35))
    sleeve = C.lathe("Sleeve", [(0.016, -0.10, 0), (0.03, -0.10, 0), (0.03, 0.10, 0), (0.016, 0.10, 0)], [steel], steps=48)
    sleeve.matrix_world = Matrix.Translation((0, 0, 0.105)) @ Rx
    out.append(C.finalize(sleeve, angle=35))
    return out


def build():
    red = C.mat_paint("SpringRed", C.srgb("#C0121A"), rough=0.28, coat=0.6)
    paint = C.mat_paint("DamperBlack", (0.02, 0.02, 0.022, 1), rough=0.35, coat=0.3)
    C.add_noise_bump(paint, scale=700, strength=0.05, distance=0.0005)
    chrome = C.mat_chrome()
    rubber = C.mat_rubber()
    steel = C.principled("ZincSteel", (0.70, 0.71, 0.73), metallic=1.0, rough=0.28)
    objs = [spring(red)] + body(paint, chrome, rubber, steel)
    C.transform_all(objs, Matrix.Rotation(math.radians(8), 4, "Y"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("ammortizzatore", objs, "ammortizzatore.py",
            "coilover shock absorber: red coil spring, black damper body, chrome rod, rubber boot, top mount",
            az=30, el=14, lens=70, fill=0.86)
