"""Rear brake caliper with integrated parking brake (pinza freno posteriore) as removed
from a small car: floating single-piston cast-iron body like the front one, but with the
piston housing extended at the back into the handbrake mechanism housing with a
perpendicular shaft boss; zinc shaft with the stamped parking-brake lever (cable eye at
the tip) and its torsion return spring; a bent steel cable bracket bolted to the back
of the housing with the keyhole slot for the cable sheath; carrier bracket, pads, guide
pins with boots, bleed nipple with cap, hose port. Reuses the front-caliper helpers
(pinza.py). Built straight then bent around the disc axis; lever parts added after
bending. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from pinza import (box, axis_mat, cyl_axis, cast, boolean, lathe_at, bend, mat_rusty_iron,
                   mat_friction, carrier, pads, guide_pins, bleed_nipple, GX, GZ)

YS = 0.93          # handbrake shaft axis (parallel to Z) at x=0, y=YS
ZL = 0.36          # lever plane


def caliper_body(iron, mach):
    bm = bmesh.new()
    cyl_axis(bm, 0.33, (0, 0, -0.02), (0, 1, 0), 0.27, 0.70, seg=64)       # piston housing
    cyl_axis(bm, 0.25, (0, 0, -0.02), (0, 1, 0), 0.60, 1.05, seg=64)       # handbrake housing
    cyl_axis(bm, 0.14, (0, YS, 0), (0, 0, 1), -0.26, 0.30, seg=48)         # shaft boss
    box(bm, -0.56, 0.56, 0.27, 0.60, -0.20, 0.30)                          # housing block
    box(bm, -0.58, 0.58, -0.50, 0.58, 0.31, 0.50)                          # bridge
    box(bm, -0.60, -0.14, -0.52, -0.27, -0.24, 0.48)                       # outer fingers
    box(bm, 0.14, 0.60, -0.52, -0.27, -0.24, 0.48)
    box(bm, -0.60, 0.60, -0.52, -0.27, 0.12, 0.48)
    for sx in (-1, 1):                                                     # guide-pin ears
        cyl_axis(bm, 0.115, (sx * GX, 0, GZ), (0, 1, 0), 0.36, 0.58, seg=40)
        box(bm, min(sx * 0.45, sx * GX), max(sx * 0.45, sx * GX), 0.38, 0.56, 0.18, 0.44)
    cyl_axis(bm, 0.075, (-0.30, 0.56, 0.24), (0, 0.25, 1), 0.0, 0.14, seg=32)   # bleed boss
    cyl_axis(bm, 0.10, (0.30, 0.50, 0.24), (0.15, 0.25, 1), 0.0, 0.14, seg=32)  # hose boss
    ob = cast("Caliper", bm, iron)
    cb = bmesh.new()
    box(cb, -0.36, 0.36, -0.25, 0.25, 0.20, 0.70)                          # pad window
    box(cb, -0.17, 0.17, -0.60, -0.20, -0.40, 0.04)                        # finger notch
    for sx in (-1, 1):
        cyl_axis(cb, 0.052, (sx * GX, 0, GZ), (0, 1, 0), 0.30, 0.70, seg=24)
    cyl_axis(cb, 0.045, (0.30, 0.50, 0.24), (0.15, 0.25, 1), 0.0, 0.30, seg=32)   # hose thread
    cyl_axis(cb, 0.085, (0.30, 0.50, 0.24), (0.15, 0.25, 1), 0.105, 0.14, seg=32, r1=0.045)
    cyl_axis(cb, 0.05, (-0.12, 1.0, -0.02), (0, 1, 0), 0.0, 0.2, seg=24)          # bracket bolt hole
    cut = C.mesh_obj("CalCut", cb, [iron])
    boolean(ob, cut)
    mb = bmesh.new()
    for sx in (-1, 1):                                                     # faced ear seats
        cyl_axis(mb, 0.13, (sx * GX, 0, GZ), (0, 1, 0), 0.57, 0.8, seg=40)
    cyl_axis(mb, 0.105, (0.30, 0.50, 0.24), (0.15, 0.25, 1), 0.112, 0.4, seg=40)
    box(mb, -0.4, 0.4, 1.035, 1.3, -0.4, 0.4)                              # faced back
    cyl_axis(mb, 0.15, (0, YS, 0), (0, 0, 1), 0.285, 0.6, seg=48)          # faced boss top
    mcut = C.mesh_obj("CalFace", mb, [mach])
    boolean(ob, mcut)
    return [C.finalize(ob, angle=40, remove=[cut, mcut])]


def parking_lever(zinc, ecoat, spring):
    out = []
    o = Vector((0, YS, 0))
    # shaft stub + nut
    P = [(0.0, 0.28, 0), (0.055, 0.28, 0), (0.055, ZL + 0.10, 0), (0.045, ZL + 0.11, 0), (0.0, ZL + 0.11, 0)]
    out.append(C.finalize(lathe_at("Shaft", P, [zinc], o, (0, 0, 1)), angle=40))
    bm = bmesh.new()
    cyl_axis(bm, 0.075, o, (0, 0, 1), ZL + 0.04, ZL + 0.10, seg=6)
    nt_ = C.mesh_obj("ShaftNut", bm, [zinc])
    C.add_bevel(nt_, 0.008, segments=2, angle=30)
    out.append(C.finalize(nt_, angle=35))
    # stamped lever: hub around the shaft, arm towards -X, cable eye at the tip
    tip = Vector((-0.66, YS + 0.10, 0))
    pts = []
    for i in range(25):                       # hub half-circle on the +X side
        a = -math.pi / 2 + math.pi * i / 24
        pts.append(Vector((0.11 * math.cos(a), YS + 0.11 * math.sin(a), 0)))
    d = (tip - o)
    nrm = Vector((-d.y, d.x, 0)).normalized()
    for i in range(25):                       # rounded tip
        a = math.atan2(nrm.y, nrm.x) + math.pi * i / 24
        pts.append(tip + Vector((0.075 * math.cos(a), 0.075 * math.sin(a), 0)))
    bm = bmesh.new()
    bot = [bm.verts.new((p.x, p.y, ZL)) for p in pts]
    top = [bm.verts.new((p.x, p.y, ZL + 0.04)) for p in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    C.fix_normals(bm)
    lv = C.mesh_obj("Lever", bm, [ecoat])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.032, ZL - 0.1, ZL + 0.2, seg=24, matrix=Matrix.Translation(tip))
    hole = C.mesh_obj("Eye", cb, [ecoat])
    boolean(lv, hole)
    C.add_bevel(lv, 0.008, segments=2, angle=30)
    out.append(C.finalize(lv, angle=35, remove=[hole]))
    # torsion return spring around the boss, tang hooked over the lever
    pts = []
    n = 4 * 32
    for i in range(n + 1):
        t = i / n
        a = math.radians(30) + 3.6 * math.tau * t
        pts.append(Vector((0.17 * math.cos(a), YS + 0.17 * math.sin(a), 0.06 + 0.24 * t)))
    end = pts[-1]
    pts += [end + Vector((-0.12, 0.02, 0.03)), end + Vector((-0.24, 0.05, ZL + 0.06 - end.z - 0.0))]
    cu = bpy.data.curves.new("TorsionSpring", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.017
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for q, v in zip(sp.points, pts):
        q.co = (v.x, v.y, v.z, 1)
    cu.materials.append(spring)
    out.append(C.finalize(C.link(bpy.data.objects.new("TorsionSpring", cu)), angle=60))
    return out


def cable_bracket(ecoat, zinc):
    out = []
    bm = bmesh.new()
    box(bm, -0.97, 0.16, 1.05, 1.09, -0.14, 0.10)            # base plate on the faced back
    box(bm, -1.01, -0.97, 0.90, 1.09, -0.14, ZL + 0.16)      # bent-up tab facing the lever
    box(bm, -0.97, -0.70, 1.05, 1.09, 0.10, 0.22)            # gusset
    br = C.mesh_obj("CableBracket", bm, [ecoat])
    cb = bmesh.new()
    zc = ZL + 0.02
    C.cyl_bm(cb, 0.05, -0.2, 0.2, seg=28, matrix=Matrix.Translation((-0.99, YS + 0.10, zc)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    C.box_bm(cb, 0.3, 0.05, 0.3, center=(-0.99, YS + 0.10, zc + 0.15))
    C.cyl_bm(cb, 0.05, 1.0, 1.2, seg=24, matrix=Matrix.Translation((-0.12, 0, -0.02)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    cut = C.mesh_obj("BracketCut", cb, [ecoat])
    boolean(br, cut)
    C.add_bevel(br, 0.01, segments=2, angle=30)
    out.append(C.finalize(br, angle=35, remove=[cut]))
    # flange bolt holding the bracket
    o = Vector((-0.12, 1.09, -0.02))
    P = [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.085, 0.018, 0), (0.0, 0.018, 0)]
    out.append(C.finalize(lathe_at("BoltFlange", P, [zinc], o, (0, 1, 0)), angle=40))
    bm = bmesh.new()
    cyl_axis(bm, 0.068, o, (0, 1, 0), 0.016, 0.085, seg=6)
    hx = C.mesh_obj("BoltHex", bm, [zinc])
    C.add_bevel(hx, 0.008, segments=2, angle=30)
    out.append(C.finalize(hx, angle=35))
    return out


def build():
    iron = mat_rusty_iron("CaliperIron", base=0.085, rust=0.5, scale=3.5, seed=1.7)
    iron2 = mat_rusty_iron("CarrierIron", base=0.075, rust=0.7, scale=4.5, seed=3.9)
    mach = mat_rusty_iron("MachinedIron", base=0.30, rust=0.35, scale=6.0, seed=5.5)
    steel = mat_rusty_iron("BackingPlate", base=0.38, rust=0.45, scale=9.0, seed=7.0)
    fric = mat_friction()
    zinc = C.principled("ZincBolt", (0.62, 0.60, 0.55), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.06, distance=0.0005, rough_var=0.08)
    rubber = C.mat_rubber("BootRubber")
    ecoat = C.principled("LeverEcoat", (0.035, 0.035, 0.038), metallic=0.3, rough=0.42)
    C.add_noise_bump(ecoat, scale=500, strength=0.06, distance=0.0005, rough_var=0.05)
    spring = C.principled("SpringSteel", (0.05, 0.05, 0.055), metallic=0.8, rough=0.35)
    objs = caliper_body(iron, mach) + carrier(iron2, mach) + pads(steel, fric)
    objs += guide_pins(zinc, rubber) + bleed_nipple(zinc, rubber)
    bend(objs)
    objs += parking_lever(zinc, ecoat, spring) + cable_bracket(ecoat, zinc)
    C.transform_all(objs, Matrix.Rotation(math.radians(168), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("pinza-posteriore", objs, "pinza-posteriore.py",
            "rear brake caliper with integrated parking brake: cast-iron body, handbrake lever with return spring, cable bracket, carrier, pads",
            az=28, el=36, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
