"""Front steering knuckle with hub (fusello completo di mozzo) for a MacPherson strut,
as removed from a small front-wheel-drive car: cast-iron knuckle with split strut
clamp and pinch-bolt ears on top, steering arm with tapered tie-rod bore, two caliper
mounting lugs, ABS sensor boss, lower ball-joint pinch clamp; pressed-in hub bearing
with seal, machined wheel hub flange with 4 wheel studs, centring spigot and splined
driveshaft bore. Cast body = primitive union fused by voxel remesh + smoothing;
machined faces and bores cut with booleans."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# hub axis = Y, outboard (wheel side) = -Y, Z up, X rearward. 1 unit ~ 10 cm
STRUT = Vector((0.0, 0.24, 0.92))       # strut clamp base centre (axis Z)
STRUT_AX = Vector((0.0, 0.18, 1.0)).normalized()
ARM_END = Vector((1.30, 0.42, 0.18))    # tie-rod bore
LBJ = Vector((0.10, 0.22, -1.05))       # lower ball-joint clamp


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=axis_mat(origin, axis), r1=r1)


def box(bm, x0, x1, y0, y1, z0, z1):
    C.box_bm(bm, x1 - x0, y1 - y0, z1 - z0, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def beam(bm, a, b, w, h, up=(0, 0, 1)):
    """box from point a to b with cross-section w (side) x h (up)"""
    a, b = Vector(a), Vector(b)
    d = b - a
    q = d.normalized().to_track_quat("Z", "Y" if abs(d.normalized().dot(Vector(up))) < 0.9 else "X")
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    C.box_bm(bm, w, h, d.length, matrix=M)


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def cast(name, bm, mat, voxel=0.012, iters=6, fac=0.5):
    ob = C.mesh_obj(name, bm, [mat])
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = fac
    sm.iterations = iters
    return ob


def lathe_at(name, prof, mats, origin, axis, steps=64, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


# ----------------------------------------------------------------- materials
def mat_rusty_iron(name, base=0.10, rust=0.5, scale=4.0, seed=0.0, metal=0.7):
    m = C.principled(name, (base, base, base * 1.03), metallic=metal, rough=0.6)
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
    patch.inputs["From Min"].default_value = 0.45
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
    met.inputs["To Min"].default_value = metal
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(fac.outputs[0], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.52
    ro.inputs["To Max"].default_value = 0.9
    nt.links.new(fac.outputs[0], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 260.0
    g.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 0.002
    hm = nt.nodes.new("ShaderNodeMath")
    hm.operation = "MULTIPLY_ADD"
    nt.links.new(g.outputs["Fac"], hm.inputs[0])
    hm.inputs[1].default_value = 1.0
    nt.links.new(nz2.outputs["Fac"], hm.inputs[2])
    nt.links.new(hm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- knuckle
def clamp(bm, cb, mb, c, r_out, r_bore, z0, z1, ear_x, bolts, closed_bottom=0.0):
    """vertical split clamp: sleeve + ear block toward +X, slit, pinch-bolt holes along Y"""
    cyl_axis(bm, r_out, c, (0, 0, 1), z0, z1, seg=56)
    box(bm, c.x, c.x + ear_x, c.y - 0.17, c.y + 0.17, c.z + z0 + 0.03, c.z + z1 - 0.03)
    zb = z0 + closed_bottom if closed_bottom else z0 - 0.3
    cyl_axis(mb, r_bore, c, (0, 0, 1), zb, z1 + 0.3, seg=56)
    box(cb, c.x, c.x + ear_x + 0.3, c.y - 0.026, c.y + 0.026, c.z + max(zb, z0 - 0.01), c.z + z1 + 0.3)
    for z in bolts:
        cyl_axis(mb, 0.055, c + Vector((ear_x - 0.12, 0, z)), (0, 1, 0), -0.5, 0.5, seg=24)


def knuckle(iron, mach):
    bm, cb, mb = bmesh.new(), bmesh.new(), bmesh.new()
    cyl_axis(bm, 0.56, (0, 0, 0), (0, 1, 0), -0.04, 0.34, seg=72)            # bearing housing
    cyl_axis(bm, 0.44, (0, 0, 0), (0, 1, 0), 0.30, 0.44, seg=72)             # inboard lip
    # upper column into the strut clamp
    box(bm, -0.27, 0.27, 0.05, 0.42, 0.20, STRUT.z + 0.22)
    clamp(bm, cb, mb, STRUT, 0.34, 0.255, 0.0, 0.80, 0.50, (0.24, 0.60), closed_bottom=0.12)
    # steering arm (tapering)
    beam(bm, (0.30, 0.22, 0.20), ARM_END, 0.24, 0.24)
    beam(bm, (0.30, 0.22, 0.14), ARM_END + Vector((-0.55, -0.05, 0.0)), 0.22, 0.36)
    cyl_axis(bm, 0.17, ARM_END, (0, 0, 1), -0.13, 0.13, seg=40)
    cyl_axis(mb, 0.085, ARM_END, (0, 0, 1), -0.3, 0.3, seg=32, r1=0.06)
    # lower column + ball-joint clamp
    box(bm, -0.20, 0.20, 0.04, 0.36, LBJ.z + 0.05, -0.25)
    clamp(bm, cb, mb, LBJ, 0.22, 0.10, -0.17, 0.17, 0.36, (0.0,))
    # caliper lugs (front side, -X)
    for z in (0.62, -0.62):
        beam(bm, (-0.25, 0.20, z * 0.7), (-0.88, 0.20, z), 0.26, 0.24)
        cyl_axis(bm, 0.15, (-0.88, 0.20, z), (0, 1, 0), -0.12, 0.12, seg=40)
        cyl_axis(mb, 0.065, (-0.88, 0.20, z), (0, 1, 0), -0.5, 0.5, seg=32)
    # ABS sensor boss
    cyl_axis(bm, 0.12, (-0.50, 0.30, 0.36), (0, 1, 0), -0.10, 0.12, seg=40)
    cyl_axis(mb, 0.052, (-0.50, 0.30, 0.36), (0, 1, 0), -0.5, 0.5, seg=24)
    ob = cast("Knuckle", bm, iron)
    cut = C.mesh_obj("KnCut", cb, [iron])
    boolean(ob, cut)
    # machined: bearing bore + outboard face, plus all bores/holes above
    cyl_axis(mb, 0.40, (0, 0, 0), (0, 1, 0), -0.5, 0.8, seg=72)
    cyl_axis(mb, 0.70, (0, 0, 0), (0, 1, 0), -0.5, -0.035, seg=72)
    mcut = C.mesh_obj("KnFace", mb, [mach])
    boolean(ob, mcut)
    return C.finalize(ob, angle=40, remove=[cut, mcut])


# ----------------------------------------------------------------- hub
def hub(flange_m, steel, seal_m):
    out = []
    # bearing outer race + seal visible in the housing
    P = [(0.30, -0.04, 0), (0.40, -0.04, 0), (0.40, 0.40, 0), (0.30, 0.40, 0)]
    out.append(C.finalize(lathe_at("Bearing", P, [steel], (0, 0, 0), (0, 1, 0), steps=96), angle=40))
    P = [(0.30, -0.05, 0), (0.395, -0.05, 0), (0.395, -0.02, 0), (0.30, -0.02, 0)]
    out.append(C.finalize(lathe_at("Seal", P, [seal_m], (0, 0, 0), (0, 1, 0), steps=96), angle=40))
    # hub: barrel, flange, spigot (built along +Z then pointed to -Y)
    P = [(0.14, -0.40, 0), (0.30, -0.40, 0), (0.30, 0.05, 0), (0.34, 0.06, 0), (0.36, 0.12, 0),
         (0.66, 0.12, 0), (0.68, 0.14, 0), (0.68, 0.23, 0), (0.66, 0.25, 0), (0.30, 0.25, 0),
         (0.29, 0.27, 0), (0.29, 0.36, 0), (0.27, 0.38, 0), (0.17, 0.38, 0), (0.14, 0.36, 0)]
    spl = lambda r, z, t: r + (0.012 if (r < 0.15 and math.cos(26 * t) > 0) else 0)
    hb = lathe_at("Hub", P, [flange_m], (0, 0, 0), (0, -1, 0), steps=208, mod=spl)
    cb = bmesh.new()
    for k in range(4):
        a = math.radians(45 + 90 * k)
        cyl_axis(cb, 0.052, (0.50 * math.cos(a), 0, 0.50 * math.sin(a)), (0, -1, 0), 0.0, 0.4, seg=24)
    cut = C.mesh_obj("StudHoles", cb, [flange_m])
    boolean(hb, cut)
    out.append(C.finalize(hb, angle=40, remove=[cut]))
    # wheel studs (knurled shank in the flange, threaded shank out, chamfered tip)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        o = (0.50 * math.cos(a), 0, 0.50 * math.sin(a))
        P = [(0.0, 0.07, 0), (0.085, 0.07, 0), (0.085, 0.12, 0), (0.054, 0.125, 0), (0.054, 0.26, 0)]
        z = 0.26
        for i in range(9):
            P += [(0.058, z + 0.012, 0), (0.050, z + 0.024, 0)]
            z += 0.024
        P += [(0.044, z + 0.02, 0), (0.0, z + 0.02, 0)]
        out.append(C.finalize(lathe_at("Stud", P, [steel], o, (0, -1, 0), steps=32), angle=50))
    return out


def build():
    iron = mat_rusty_iron("KnuckleIron", base=0.10, rust=0.5, scale=3.0)
    mach = mat_rusty_iron("MachinedIron", base=0.32, rust=0.25, scale=6.0, seed=5.0, metal=0.9)
    flange = mat_rusty_iron("HubSteel", base=0.30, rust=0.7, scale=5.0, seed=2.0, metal=0.9)
    C.add_radial_aniso(flange, 0.5, "Y")
    steel = C.principled("StudSteel", (0.55, 0.55, 0.53), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    seal = C.mat_rubber("SealRubber")
    objs = [knuckle(iron, mach)] + hub(flange, steel, seal)
    C.transform_all(objs, Matrix.Rotation(math.radians(-15), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("fusello", objs, "fusello.py",
            "front steering knuckle with hub bearing and wheel hub: cast knuckle with strut clamp, steering arm, caliper lugs, hub flange with 4 wheel studs",
            az=30, el=20, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
