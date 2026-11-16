"""Alternator: finned cast-aluminium two-piece body, stator ring, copper windings visible
through cooling windows, external fan, poly-V pulley with nut, mounting ears."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

NWIN = 10


def rib(r, z, t, z0, z1):
    """longitudinal ribs on the cylindrical part only"""
    if r < 0.595 or not (z0 < z < z1):
        return r
    v = math.cos(24 * t)
    sq = max(-1.0, min(1.0, v * 3.0)) * 0.5 + 0.5
    return r + 0.022 * sq


def window_cutter(z0, z1, mat, phase=0.0):
    bm = bmesh.new()
    for k in range(NWIN):
        th = math.tau * k / NWIN + phase
        M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.62, 0, (z0 + z1) / 2))
        C.box_bm(bm, 0.22, 0.17, z1 - z0, matrix=M)
    return C.mesh_obj("WinCut", bm, [mat])


def rear_housing(alu):
    P = [(0.10, 0.0, 0), (0.50, 0.0, 0), (0.575, 0.022, 0), (0.60, 0.07, 0), (0.60, 0.45, 0),
         (0.56, 0.45, 0), (0.56, 0.08, 0), (0.50, 0.045, 0), (0.10, 0.045, 0)]
    ob = C.lathe("RearHousing", P, [alu], steps=240, mod=lambda r, z, t: rib(r, z, t, 0.06, 0.46))
    cut = window_cutter(0.27, 0.42, alu)
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.004, segments=2, angle=35)
    return C.finalize(ob, angle=35, remove=[cut])


def front_housing(alu):
    P = [(0.60, 0.57, 0), (0.60, 0.80, 0), (0.585, 0.865, 0), (0.53, 0.90, 0), (0.20, 0.90, 0),
         (0.19, 0.92, 0), (0.12, 0.92, 0), (0.12, 0.86, 0), (0.50, 0.86, 0), (0.56, 0.82, 0), (0.56, 0.57, 0)]
    ob = C.lathe("FrontHousing", P, [alu], steps=240, mod=lambda r, z, t: rib(r, z, t, 0.56, 0.81))
    cut = window_cutter(0.60, 0.74, alu, phase=math.pi / NWIN)
    # radial cooling slots on the drive-end face
    bm = bmesh.new()
    for k in range(8):
        th = math.tau * k / 8 + math.pi / 8
        M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.37, 0, 0.88))
        C.box_bm(bm, 0.24, 0.085, 0.12, matrix=M)
    fs = C.mesh_obj("FaceSlots", bm, [alu])
    C.add_boolean(ob, cut)
    C.add_boolean(ob, fs)
    C.add_bevel(ob, 0.004, segments=2, angle=35)
    return C.finalize(ob, angle=35, remove=[cut, fs])


def ears(alu):
    out = []
    specs = [(math.pi / 2, 0.62, 0.80), (math.pi / 2, 0.20, 0.42), (-math.pi / 2, 0.64, 0.80)]
    for th, z0, z1 in specs:
        Rz = Matrix.Rotation(th - math.pi / 2, 4, "Z")  # build along +Y then rotate
        bm = bmesh.new()
        C.box_bm(bm, 0.15, 0.28, z1 - z0, center=(0, 0.60, (z0 + z1) / 2), matrix=Rz)
        b = C.mesh_obj("EarArm", bm, [alu])
        C.add_bevel(b, 0.01, segments=2, angle=30)
        out.append(C.finalize(b, angle=35))
        tube = C.lathe("EarBoss", [(0.048, z0, 0), (0.095, z0, 0), (0.095, z1, 0), (0.048, z1, 0)], [alu], steps=48)
        tube.matrix_world = Rz @ Matrix.Translation((0, 0.80, 0))
        C.add_bevel(tube, 0.008, segments=2, angle=30)
        out.append(C.finalize(tube, angle=35))
    return out


def stator(steel):
    P = [(0.56, 0.45, 0), (0.628, 0.45, 0), (0.628, 0.57, 0), (0.56, 0.57, 0)]
    ob = C.lathe("Stator", P, [steel], steps=160)
    return C.finalize(ob, angle=40)


def windings(copper, dark):
    ob = C.lathe("Windings", [(0.0, 0.12, 0), (0.50, 0.12, 0), (0.545, 0.2, 0), (0.545, 0.82, 0), (0.0, 0.82, 0)],
                 [copper], steps=96)
    rotor = C.lathe("Rotor", [(0.0, 0.83, 0), (0.42, 0.83, 0), (0.42, 0.86, 0), (0.0, 0.86, 0)], [dark], steps=64)
    return [C.finalize(ob, angle=40), C.finalize(rotor, angle=40)]


def fan(steel):
    bm = bmesh.new()
    C.cyl_bm(bm, 0.52, 0.925, 0.935, seg=96)
    C.cyl_bm(bm, 0.20, 0.925, 1.0, seg=64)
    for k in range(14):
        th = math.tau * k / 14
        M = (Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.355, 0, 0.965))
             @ Matrix.Rotation(math.radians(28), 4, "X"))
        C.box_bm(bm, 0.31, 0.012, 0.075, matrix=M)
    ob = C.mesh_obj("Fan", bm, [steel])
    C.add_bevel(ob, 0.003, segments=1, angle=30)
    return C.finalize(ob, angle=35)


def pulley(steel):
    P = [(0.07, 1.0, 0), (0.275, 1.0, 0), (0.275, 1.025, 0)]
    z = 1.035
    for i in range(6):
        P += [(0.238, z, 0), (0.262, z + 0.0135, 0)]
        z += 0.027
    P += [(0.238, z, 0), (0.275, z + 0.012, 0), (0.275, z + 0.032, 0), (0.238, z + 0.032, 0),
          (0.226, z + 0.004, 0), (0.125, z - 0.004, 0), (0.108, z + 0.032, 0), (0.07, z + 0.032, 0)]
    ob = C.lathe("Pulley", P, [steel], steps=160)
    C.add_bevel(ob, 0.002, segments=1, angle=40)
    top = z + 0.032
    pul = C.finalize(ob, angle=40)
    # hex nut + shaft end
    bm = bmesh.new()
    C.cyl_bm(bm, 0.085, top, top + 0.07, seg=6)
    nut = C.mesh_obj("Nut", bm, [steel])
    C.add_bevel(nut, 0.008, segments=2, angle=30)
    nut = C.finalize(nut, angle=35)
    sh = C.lathe("Shaft", [(0.0, top, 0), (0.042, top, 0), (0.042, top + 0.10, 0), (0.034, top + 0.11, 0), (0.0, top + 0.11, 0)], [steel], steps=48)
    sh = C.finalize(sh, angle=40)
    washer = C.lathe("Washer", [(0.05, top - 0.002, 0), (0.11, top - 0.002, 0), (0.11, top + 0.012, 0), (0.05, top + 0.012, 0)], [steel], steps=64)
    return [pul, nut, C.finalize(sh, angle=40) if False else sh, C.finalize(washer, angle=40)]


def rear_cover(black, red, steel):
    P = [(0.0, -0.13, 0), (0.30, -0.12, 0), (0.48, -0.08, 0), (0.54, -0.02, 0), (0.55, 0.03, 0), (0.0, 0.03, 0)]
    ob = C.lathe("RearCover", P, [black], steps=96)
    out = [C.finalize(ob, angle=40)]
    # B+ terminal with red boot on the cover
    boot = C.lathe("Boot", [(0.0, -0.08, 0), (0.06, -0.08, 0), (0.07, -0.16, 0), (0.05, -0.22, 0), (0.0, -0.23, 0)], [red], steps=48)
    boot.matrix_world = Matrix.Translation((0.26, 0.18, 0.0))
    out.append(C.finalize(boot, angle=40))
    # plug socket
    bm = bmesh.new()
    C.box_bm(bm, 0.20, 0.12, 0.14, center=(-0.22, 0.25, -0.12))
    pl = C.mesh_obj("Plug", bm, [black])
    C.add_bevel(pl, 0.012, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    return out


def build():
    alu = C.principled("CastAlu", (0.48, 0.48, 0.475), metallic=1.0, rough=0.36)
    C.add_noise_bump(alu, scale=420, strength=0.07, distance=0.001, rough_var=0.08)
    steel = C.principled("ZincSteel", (0.56, 0.57, 0.59), metallic=1.0, rough=0.24)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    lam = C.principled("Lamination", (0.10, 0.10, 0.105), metallic=0.9, rough=0.38)
    copper = C.principled("Copper", (0.80, 0.42, 0.24), metallic=1.0, rough=0.32)
    cn = copper.node_tree
    wv = cn.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"; wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 45.0
    wv.inputs["Distortion"].default_value = 1.5
    cn.links.new(C._coord(cn), wv.inputs["Vector"])
    bp = cn.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    cn.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    cn.links.new(bp.outputs["Normal"], next(n for n in cn.nodes if n.type == "BSDF_PRINCIPLED").inputs["Normal"])
    dark = C.principled("DarkSteel", (0.08, 0.08, 0.085), metallic=1.0, rough=0.45)
    black = C.mat_black_plastic("CoverABS", rough=0.45)
    red = C.mat_paint("RedBoot", (0.55, 0.02, 0.02, 1), rough=0.4, coat=0.2)
    objs = [rear_housing(alu), front_housing(alu), stator(lam)]
    objs += windings(copper, dark)
    objs += ears(alu)
    objs += [fan(steel)]
    objs += pulley(steel)
    objs += rear_cover(black, red, steel)
    # axis Z -> horizontal, pulley toward front-left; ears up/down
    C.transform_all(objs, Matrix.Rotation(math.radians(-12), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("alternatore", objs, "alternatore.py",
            "car alternator: finned cast-aluminium body, cooling slots, copper windings, fan, poly-V pulley",
            az=35, el=20, lens=70, fill=0.82)
