"""Front brake caliper (pinza freno), floating single-piston type, as removed from a small
car: cast-iron body (piston housing, bridge with pad window, outer fingers) and carrier
bracket, both with surface rust; both brake pads in place; guide pins with rubber boots
and zinc bolt heads; bleed nipple with rubber dust cap; threaded hose port.
Built straight (X tangential, Y axial with inboard +Y, Z radial) then bent around the
disc axis so the body follows the disc arc. Cast parts are primitive unions fused by a
voxel remesh + smoothing (cast fillets), then machined holes are cut with booleans."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RP = 1.05      # radius of the pad centre from the disc axis (1 unit ~ 10 cm)


# ----------------------------------------------------------------- helpers
def box(bm, x0, x1, y0, y1, z0, z1, mat=0):
    C.box_bm(bm, x1 - x0, y1 - y0, z1 - z0, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat)


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=axis_mat(origin, axis), r1=r1)


def cast(name, bm, mat, voxel=0.010, iters=4, fac=0.5):
    ob = C.mesh_obj(name, bm, [mat])
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = fac
    sm.iterations = iters
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def lathe_at(name, prof, mats, origin, axis, steps=48):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def bake(ob):
    me = ob.data
    me.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


def bend(objs):
    """wrap the straight build around the disc axis (parallel to Y, at z=-RP)"""
    for ob in objs:
        bake(ob)
        for v in ob.data.vertices:
            x, y, z = v.co
            r = RP + z
            t = x / RP
            v.co = (r * math.sin(t), y, r * math.cos(t) - RP)
        ob.data.update()


# ----------------------------------------------------------------- materials
def mat_rusty_iron(name, base=0.10, rust=0.55, scale=5.0, seed=0.0):
    """dark cast iron with blotchy surface rust (more on edges), grainy cast bump"""
    m = C.principled(name, (base, base, base * 1.03), metallic=0.7, rough=0.6)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (seed, seed * 1.7, seed * 0.3)
    nt.links.new(co, mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 12.0
    nz.inputs["Roughness"].default_value = 0.68
    patch = nt.nodes.new("ShaderNodeMapRange")
    patch.inputs["From Min"].default_value = 0.42
    patch.inputs["From Max"].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], patch.inputs["Value"])
    em = C.edge_mask(nt, 0.025, 4.0)
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.use_clamp = True
    add.inputs[1].default_value = 0.6
    nt.links.new(em, add.inputs[0])
    nt.links.new(patch.outputs["Result"], add.inputs[2])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.use_clamp = True
    fac.inputs[1].default_value = rust
    nt.links.new(add.outputs[0], fac.inputs[0])
    # rust colour varies between orange-brown and dark brown
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz2.inputs["Vector"])
    nz2.inputs["Scale"].default_value = 40.0
    nz2.inputs["Detail"].default_value = 6.0
    rc = nt.nodes.new("ShaderNodeValToRGB")
    rc.color_ramp.elements[0].position = 0.35
    rc.color_ramp.elements[0].color = (0.055, 0.024, 0.012, 1)
    rc.color_ramp.elements[1].position = 0.70
    rc.color_ramp.elements[1].color = (0.17, 0.065, 0.025, 1)
    nt.links.new(nz2.outputs["Fac"], rc.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(fac.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.03, 1)
    nt.links.new(rc.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    met = nt.nodes.new("ShaderNodeMapRange")
    met.inputs["To Min"].default_value = 0.7
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(fac.outputs[0], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.55
    ro.inputs["To Max"].default_value = 0.9
    nt.links.new(fac.outputs[0], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # grainy sand-cast bump + rust scale
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 260.0
    g.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    hm = nt.nodes.new("ShaderNodeMath")
    hm.operation = "MULTIPLY_ADD"
    nt.links.new(g.outputs["Fac"], hm.inputs[0])
    hm.inputs[1].default_value = 1.0
    nt.links.new(nz2.outputs["Fac"], hm.inputs[2])
    nt.links.new(hm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_friction(name="PadFriction"):
    m = C.principled(name, (0.075, 0.068, 0.060), rough=0.92)
    C.add_noise_bump(m, scale=900, strength=0.4, distance=0.001, rough_var=0.04)
    return m


# ----------------------------------------------------------------- parts
GX, GZ = 0.80, 0.37          # guide pin axis (x = +/-GX)


def caliper_body(iron, mach):
    bm = bmesh.new()
    cyl_axis(bm, 0.36, (0, 0, -0.02), (0, 1, 0), 0.27, 0.70, seg=64)       # piston housing
    cyl_axis(bm, 0.30, (0, 0, -0.02), (0, 1, 0), 0.60, 0.80, seg=64)       # rounded back
    box(bm, -0.56, 0.56, 0.27, 0.60, -0.20, 0.30)                          # housing block
    box(bm, -0.58, 0.58, -0.50, 0.58, 0.31, 0.50)                          # bridge
    box(bm, -0.60, -0.14, -0.52, -0.27, -0.24, 0.48)                       # outer fingers
    box(bm, 0.14, 0.60, -0.52, -0.27, -0.24, 0.48)
    box(bm, -0.60, 0.60, -0.52, -0.27, 0.12, 0.48)
    for sx in (-1, 1):                                                     # guide-pin ears
        cyl_axis(bm, 0.115, (sx * GX, 0, GZ), (0, 1, 0), 0.36, 0.58, seg=40)
        box(bm, min(sx * 0.45, sx * GX), max(sx * 0.45, sx * GX), 0.38, 0.56, 0.18, 0.44)
    cyl_axis(bm, 0.075, (-0.30, 0.56, 0.24), (0, 0.25, 1), 0.0, 0.14, seg=32)   # bleed boss
    cyl_axis(bm, 0.10, (0.22, 0.70, 0.14), (0, 1, 0.35), 0.0, 0.12, seg=32)     # hose boss
    ob = cast("Caliper", bm, iron)
    cb = bmesh.new()
    box(cb, -0.36, 0.36, -0.25, 0.25, 0.20, 0.70)                          # pad window
    box(cb, -0.17, 0.17, -0.60, -0.20, -0.40, 0.04)                        # finger notch
    for sx in (-1, 1):
        cyl_axis(cb, 0.052, (sx * GX, 0, GZ), (0, 1, 0), 0.30, 0.70, seg=24)
    cyl_axis(cb, 0.045, (0.22, 0.70, 0.14), (0, 1, 0.35), 0.0, 0.30, seg=32)   # hose thread
    cyl_axis(cb, 0.085, (0.22, 0.70, 0.14), (0, 1, 0.35), 0.105, 0.14, seg=32, r1=0.045)
    cut = C.mesh_obj("CalCut", cb, [iron])
    boolean(ob, cut)
    mb = bmesh.new()
    for sx in (-1, 1):                                                     # faced ear seats
        cyl_axis(mb, 0.13, (sx * GX, 0, GZ), (0, 1, 0), 0.57, 0.8, seg=40)
    cyl_axis(mb, 0.105, (0.22, 0.70, 0.14), (0, 1, 0.35), 0.112, 0.4, seg=40)
    mcut = C.mesh_obj("CalFace", mb, [mach])
    boolean(ob, mcut)
    out = [C.finalize(ob, angle=40, remove=[cut, mcut])]
    return out


def carrier(iron, mach):
    bm = bmesh.new()
    for sx in (-1, 1):
        xa, xb = sorted((sx * 0.63, sx * 0.96))
        box(bm, xa, xb, -0.40, 0.30, 0.27, 0.44)          # over the disc edge
        box(bm, xa, xb, -0.40, -0.17, -0.28, 0.44)        # outboard leg
        box(bm, xa, xb, 0.16, 0.42, -0.70, 0.44)          # inboard leg
        cyl_axis(bm, 0.125, (sx * GX, 0, GZ), (0, 1, 0), -0.36, 0.26, seg=40)
        cyl_axis(bm, 0.15, (sx * 0.73, 0, -0.56), (0, 1, 0), 0.16, 0.44, seg=40)
    box(bm, -0.85, 0.85, 0.18, 0.40, -0.70, -0.44)        # inboard base
    ob = cast("Carrier", bm, iron)
    cb = bmesh.new()
    for sx in (-1, 1):
        cyl_axis(cb, 0.062, (sx * 0.73, 0, -0.56), (0, 1, 0), 0.0, 0.6, seg=32)
        cyl_axis(cb, 0.052, (sx * GX, 0, GZ), (0, 1, 0), -0.5, 0.4, seg=24)
        # pad abutment slots
        xa, xb = sorted((sx * 0.60, sx * 0.70))
        box(cb, xa, xb, -0.30, -0.19, -0.30, 0.255)
        box(cb, xa, xb, 0.19, 0.30, -0.30, 0.255)
    cut = C.mesh_obj("CarCut", cb, [iron])
    boolean(ob, cut)
    mb = bmesh.new()
    box(mb, -1.5, 1.5, 0.415, 0.8, -1.0, -0.40)                           # faced mounting pads
    mcut = C.mesh_obj("CarFace", mb, [mach])
    boolean(ob, mcut)
    return [C.finalize(ob, angle=40, remove=[cut, mcut])]


def pads(steel, fric):
    out = []
    for sy in (-1, 1):
        bm = bmesh.new()
        y0, y1 = sorted((sy * 0.21, sy * 0.255))
        box(bm, -0.67, 0.67, y0, y1, -0.27, 0.29)
        bp = C.mesh_obj("Backing", bm, [steel])
        C.add_bevel(bp, 0.02, segments=3, angle=30)
        out.append(C.finalize(bp, angle=35))
        bm = bmesh.new()
        y0, y1 = sorted((sy * 0.112, sy * 0.212))
        box(bm, -0.56, 0.56, y0, y1, -0.25, 0.26)
        fr = C.mesh_obj("Friction", bm, [fric])
        cb = bmesh.new()
        box(cb, -0.012, 0.012, sy * 0.05 - 0.07, sy * 0.05 + 0.07, -0.4, 0.4)   # centre slot
        cut = C.mesh_obj("Slot", cb, [fric])
        C.add_boolean(fr, cut)
        C.add_bevel(fr, 0.03, segments=2, angle=30)
        out.append(C.finalize(fr, angle=35, remove=[cut]))
    return out


def guide_pins(zinc, rubber):
    out = []
    for sx in (-1, 1):
        o = (sx * GX, 0, GZ)
        # accordion boot between carrier bore and caliper ear
        P = [(0.05, 0.25, 0), (0.105, 0.25, 0)]
        y = 0.25
        for i in range(3):
            P += [(0.115, y + 0.018, 0), (0.088, y + 0.036, 0)]
            y += 0.036
        P += [(0.10, 0.37, 0), (0.05, 0.37, 0)]
        out.append(C.finalize(lathe_at("Boot", P, [rubber], o, (0, 1, 0)), angle=50))
        # bolt: flange + hex head on the inboard face of the ear
        P = [(0.0, 0.575, 0), (0.095, 0.575, 0), (0.095, 0.595, 0), (0.0, 0.595, 0)]
        out.append(C.finalize(lathe_at("Flange", P, [zinc], o, (0, 1, 0)), angle=40))
        bm = bmesh.new()
        cyl_axis(bm, 0.08, o, (0, 1, 0), 0.59, 0.67, seg=6)
        hx = C.mesh_obj("Hex", bm, [zinc])
        C.add_bevel(hx, 0.008, segments=2, angle=30)
        out.append(C.finalize(hx, angle=35))
    return out


def bleed_nipple(zinc, rubber):
    o, ax = (-0.30, 0.56, 0.24), (0, 0.25, 1)
    out = []
    bm = bmesh.new()
    cyl_axis(bm, 0.052, o, ax, 0.13, 0.19, seg=6)
    hx = C.mesh_obj("BleedHex", bm, [zinc])
    C.add_bevel(hx, 0.006, segments=2, angle=30)
    out.append(C.finalize(hx, angle=35))
    P = [(0.0, 0.10, 0), (0.034, 0.10, 0), (0.034, 0.135, 0), (0.0, 0.135, 0)]
    out.append(C.finalize(lathe_at("BleedShank", P, [zinc], o, ax), angle=40))
    # rubber dust cap over the tip
    P = [(0.0, 0.185, 0), (0.044, 0.185, 0), (0.048, 0.20, 0), (0.048, 0.27, 0), (0.044, 0.285, 0),
         (0.02, 0.29, 0), (0.0, 0.29, 0)]
    out.append(C.finalize(lathe_at("BleedCap", P, [rubber], o, ax), angle=50))
    P = [(0.0, 0.25, 0), (0.06, 0.25, 0), (0.06, 0.262, 0), (0.0, 0.262, 0)]
    out.append(C.finalize(lathe_at("CapRim", P, [rubber], o, ax), angle=50))
    return out


def build():
    iron = mat_rusty_iron("CaliperIron", base=0.085, rust=0.5, scale=3.5)
    iron2 = mat_rusty_iron("CarrierIron", base=0.075, rust=0.7, scale=4.5, seed=3.1)
    mach = mat_rusty_iron("MachinedIron", base=0.30, rust=0.35, scale=6.0, seed=5.0)
    steel = mat_rusty_iron("BackingPlate", base=0.38, rust=0.45, scale=9.0, seed=7.0)
    fric = mat_friction()
    zinc = C.principled("ZincBolt", (0.62, 0.60, 0.55), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.06, distance=0.0005, rough_var=0.08)
    rubber = C.mat_rubber("BootRubber")
    objs = caliper_body(iron, mach) + carrier(iron2, mach) + pads(steel, fric)
    objs += guide_pins(zinc, rubber) + bleed_nipple(zinc, rubber)
    bend(objs)
    C.transform_all(objs, Matrix.Rotation(math.radians(168), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("pinza", objs, "pinza.py",
            "front brake caliper: floating single-piston cast-iron body with carrier bracket, brake pads, guide pins with rubber boots, bleed nipple with cap",
            az=35, el=33, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
