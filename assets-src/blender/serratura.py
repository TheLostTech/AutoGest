"""Front door lock (latch with integrated central-locking actuator), generic small hatchback.
Black phosphated steel latch plate with the striker slot, threaded fixing holes and worn
edges; the rotary claw visible in the slot; black plastic latch body and actuator housing
behind it with the motor bulge, moulded ribs and the electrical connector shroud with
pins; two Bowden cable stubs (sheath, end fittings, steel inner cable with nipple).
The plate faces -Y (the door's rear edge), the housing runs back into the door (+Y)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

RX = Matrix.Rotation(math.radians(90), 4, "X")     # cylinder axis Z -> -Y
RY = Matrix.Rotation(math.radians(90), 4, "Y")     # cylinder axis Z -> X


def bool_cut(ob, cut):
    """Exact difference that tolerates overlapping pieces in the object and the cutter."""
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_black_steel(name="BlackPhosphate"):
    base = 0.035
    m = C.principled(name, (base, base, base * 1.05), metallic=0.75, rough=0.48)
    nt = m.node_tree
    b = P.bsdf(m)
    C.add_noise_bump(m, scale=420, strength=0.10, distance=0.0004, rough_var=0.06)
    em = C.edge_mask(nt, 0.0012, 2.5)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 140.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.05, 1)
    mix.inputs["B"].default_value = (0.36, 0.36, 0.37, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------ latch plate
PX0, PX1, PZ0, PZ1 = -0.031, 0.031, -0.057, 0.057
SLOT_Z, SLOT_H, SLOT_X1 = -0.004, 0.0175, 0.006
HOLES = [(0.017, 0.041), (0.017, -0.045), (-0.019, 0.036)]


def plate(steel, dark):
    bm = bmesh.new()
    C.box_bm(bm, PX1 - PX0, 0.0032, PZ1 - PZ0, center=((PX0 + PX1) / 2, 0.0016, 0.0))
    ob = C.mesh_obj("Plate", bm, [steel])
    cb = bmesh.new()
    # striker slot, open towards -X, round inner end
    C.box_bm(cb, SLOT_X1 - PX0 + 0.02, 0.05, SLOT_H, center=((PX0 - 0.02 + SLOT_X1) / 2, 0.0, SLOT_Z))
    C.cyl_bm(cb, SLOT_H / 2, -0.03, 0.03, seg=40, matrix=Matrix.Translation((SLOT_X1, 0.0, SLOT_Z)) @ RX)
    # lead-in chamfer of the slot mouth
    for sz in (-1, 1):
        C.box_bm(cb, 0.011, 0.05, 0.011, center=(0, 0, 0),
                 matrix=Matrix.Translation((PX0, 0.0, SLOT_Z + sz * (SLOT_H / 2))) @ Matrix.Rotation(math.radians(45), 4, "Y"))
    for (x, z) in HOLES:
        C.cyl_bm(cb, 0.0042, -0.03, 0.03, seg=32, matrix=Matrix.Translation((x, 0.0, z)) @ RX)
    cut = C.mesh_obj("PlateCut", cb, [dark])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0011, segments=3, angle=30)
    out = [C.finalize(ob, angle=35, remove=[cut])]
    # pressed collars round the threaded holes
    for (x, z) in HOLES:
        col = C.lathe("Collar", [(0.0042, 0.0, 0), (0.0072, 0.0, 0), (0.0064, 0.0011, 0), (0.0046, 0.0013, 0), (0.0042, 0.0006, 0)],
                      [steel], steps=40)
        col.matrix_world = Matrix.Translation((x, 0.0, z)) @ RX
        out.append(C.finalize(col, angle=40))
        thr = C.lathe("Thread", [(0.0034, 0.0, 0), (0.0041, 0.0, 0), (0.0041, 0.03, 0), (0.0034, 0.03, 0)], [dark], steps=24,
                      mod=lambda r, zz, t: r - 0.0004 * (0.5 + 0.5 * math.sin(zz * 2 * math.pi / 0.0008 + t)))
        thr.matrix_world = Matrix.Translation((x, 0.0, z)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        out.append(C.finalize(thr, angle=60))
    return out


def claw(steel, plastic):
    """Rotary claw seen through the slot: a coated fork disc and the pawl."""
    out = []
    bm = bmesh.new()
    C.cyl_bm(bm, 0.0175, 0.0, 0.009, seg=64, matrix=Matrix.Translation((0.004, 0.004, SLOT_Z - 0.011)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    ob = C.mesh_obj("Claw", bm, [plastic])
    cb = bmesh.new()
    C.box_bm(cb, 0.022, 0.03, 0.0105, center=(-0.006, 0.008, SLOT_Z + 0.0005),
             matrix=Matrix.Translation((0.004, 0, SLOT_Z - 0.011)) @ Matrix.Rotation(math.radians(-18), 4, "Y") @ Matrix.Translation((-0.004, 0, -(SLOT_Z - 0.011))))
    cut = C.mesh_obj("ClawCut", cb, [plastic])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # rubber bump stop lining the back of the slot
    bm = bmesh.new()
    C.box_bm(bm, 0.010, 0.010, SLOT_H + 0.004, center=(SLOT_X1 + 0.006, 0.012, SLOT_Z))
    st = C.mesh_obj("SlotStop", bm, [plastic])
    C.add_bevel(st, 0.002, segments=2, angle=30)
    out.append(C.finalize(st, angle=35))
    return out


# ------------------------------------------------------------------ housing
def housing(plastic, dark):
    out = []
    bm = bmesh.new()
    # latch body right behind the plate
    P.superellipsoid(bm, 0.029, 0.016, 0.054, e1=0.15, e2=0.15, matrix=Matrix.Translation((0.0, 0.019, 0.0)))
    # actuator body running back into the door
    P.superellipsoid(bm, 0.020, 0.048, 0.046, e1=0.18, e2=0.18, matrix=Matrix.Translation((-0.006, 0.072, -0.008)))
    # motor can bulge on the outer (-X) side
    C.cyl_bm(bm, 0.0135, 0.040, 0.108, seg=48, matrix=Matrix.Translation((-0.019, 0.0, -0.030)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    # moulded ribs on the side
    for y in (0.050, 0.064, 0.078, 0.092):
        C.box_bm(bm, 0.006, 0.0025, 0.040, center=(-0.025, y, 0.016))
    # lid seam
    C.box_bm(bm, 0.043, 0.098, 0.003, center=(-0.006, 0.072, 0.0385))
    ob = C.mesh_obj("Housing", bm, [plastic])
    cb = bmesh.new()
    C.box_bm(cb, 0.06, 0.06, SLOT_H, center=(PX0 + 0.004, 0.02, SLOT_Z))
    cut = C.mesh_obj("HousingSlot", cb, [dark])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0012, segments=2, angle=30)
    out.append(C.finalize(ob, angle=40, remove=[cut]))
    return out


def connector(plastic, pins_m, dark):
    out = []
    cx, cy, cz = -0.026, 0.096, -0.005
    bm = bmesh.new()
    C.box_bm(bm, 0.016, 0.026, 0.018, center=(cx - 0.006, cy, cz))
    ob = C.mesh_obj("Shroud", bm, [plastic])
    cb = bmesh.new()
    C.box_bm(cb, 0.02, 0.021, 0.013, center=(cx - 0.012, cy, cz))
    cut = C.mesh_obj("ShroudCut", cb, [dark])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # locking ramp on top of the shroud
    bm = bmesh.new()
    C.box_bm(bm, 0.008, 0.006, 0.003, center=(cx - 0.008, cy, cz + 0.010))
    rp = C.mesh_obj("Ramp", bm, [plastic])
    C.add_bevel(rp, 0.0006, segments=1, angle=30)
    out.append(C.finalize(rp, angle=35))
    bm = bmesh.new()
    for k in range(4):
        y = cy - 0.0075 + 0.005 * k
        C.box_bm(bm, 0.009, 0.0012, 0.0024, center=(cx - 0.008, y, cz))
    pn = C.mesh_obj("Pins", bm, [pins_m])
    out.append(C.finalize(pn, angle=35))
    return out


def bowden(sheath, plastic, steel):
    out = []
    specs = [((-0.012, 0.100, 0.036), (-0.30, 0.55, 1.0), 0.075),
             ((0.002, 0.108, 0.030), (0.10, 1.0, 0.55), 0.065)]
    for (o, d, L) in specs:
        o = Vector(o)
        d = Vector(d).normalized()
        # end fitting on the housing
        n0 = d
        up = Vector((1, 0, 0)) if abs(n0.x) < 0.9 else Vector((0, 1, 0))
        X = up.cross(n0).normalized()
        Y = n0.cross(X)
        M = P.basis(X, Y, n0, o)
        fit = C.lathe("Ferrule", [(0.0, -0.004, 0), (0.0062, -0.004, 0), (0.0062, 0.006, 0), (0.0048, 0.008, 0),
                                  (0.0048, 0.016, 0), (0.0036, 0.019, 0), (0.0, 0.019, 0)], [plastic], steps=32)
        fit.matrix_world = M
        out.append(C.finalize(fit, angle=40))
        # sheath: gentle curve
        pts = []
        s0 = o + n0 * 0.018
        bend = Vector((0, 0.35, -0.6)).normalized()
        for k in range(41):
            t = k / 40
            pts.append(s0 + n0 * (L * t) + bend * (0.035 * t * t))
        fr = P.path_frames(pts, (1, 0, 0))
        out.append(P.tube_obj("Sheath", fr, P.circle(0.0033, 20), [sheath], smooth_angle=60))
        # end ferrule + inner cable + nipple
        tip = pts[-1]
        T = (pts[-1] - pts[-2]).normalized()
        X2 = Vector((1, 0, 0)).cross(T).normalized()
        M2 = P.basis(X2, T.cross(X2), T, tip)
        ef = C.lathe("EndFerrule", [(0.0, -0.006, 0), (0.0042, -0.006, 0), (0.0042, 0.005, 0), (0.0026, 0.007, 0), (0.0, 0.007, 0)],
                     [steel], steps=32)
        ef.matrix_world = M2
        out.append(C.finalize(ef, angle=40))
        wire = C.lathe("Inner", [(0.0, 0.006, 0), (0.0011, 0.006, 0), (0.0011, 0.030, 0), (0.0, 0.030, 0)], [steel], steps=16)
        wire.matrix_world = M2
        out.append(C.finalize(wire, angle=40))
        nip = C.lathe("Nipple", [(0.0, 0.028, 0), (0.0032, 0.028, 0), (0.0032, 0.036, 0), (0.0, 0.036, 0)], [steel], steps=24)
        nip.matrix_world = M2
        C.add_bevel(nip, 0.0006, segments=2, angle=30)
        out.append(C.finalize(nip, angle=40))
    return out


def build():
    steel = mat_black_steel()
    plastic = C.mat_black_plastic("HousingPA", rough=0.5, color=0.028)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.7)
    sheath = C.mat_black_plastic("SheathPE", rough=0.35, color=0.02)
    bright = C.principled("ZincSteel", (0.66, 0.66, 0.68), metallic=1.0, rough=0.28)
    C.add_noise_bump(bright, scale=500, strength=0.05, distance=0.0003, rough_var=0.05)
    tin = C.principled("TinPins", (0.80, 0.78, 0.72), metallic=1.0, rough=0.25)
    objs = plate(steel, dark)
    objs += claw(steel, plastic)
    objs += housing(plastic, dark)
    objs += connector(plastic, tin, dark)
    objs += bowden(sheath, plastic, bright)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("serratura", objs, "serratura.py",
            "door lock latch with central-locking actuator (generic small hatchback): black steel latch plate with striker "
            "slot and claw, black plastic actuator housing with connector, two Bowden cable stubs",
            az=-40, el=22, lens=80, fill=0.82, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
