"""Rear wheel hub bearing unit (mozzo posteriore) of a small car with bolt-on rear
hubs: forged wheel flange with 4 pressed-in wheel studs and centring spigot, zinc
dust cap, sealed bearing body with a square 4-bolt mounting flange, and a toothed
ABS tone ring at the inboard end. Lathe profiles for the round parts; mounting flange
is an extruded rounded square with boolean bolt holes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# built along +Z = outboard (wheel side); 1 unit ~ 10 cm


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


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def rounded_square(half, rad, seg=10):
    pts = []
    for cx, cy, a0 in ((half - rad, half - rad, 0), (-half + rad, half - rad, 90),
                       (-half + rad, -half + rad, 180), (half - rad, -half + rad, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def prism(bm, poly, z0, z1):
    vb = [bm.verts.new((x, y, z0)) for x, y in poly]
    vt = [bm.verts.new((x, y, z1)) for x, y in poly]
    m = len(poly)
    bm.faces.new(vb[::-1])
    bm.faces.new(vt)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))


def wheel_flange(flange, cap_m):
    out = []
    # flange disc + spigot + barrel into the bearing
    P = [(0.17, -0.52, 0), (0.30, -0.52, 0), (0.30, 0.04, 0), (0.34, 0.06, 0), (0.37, 0.10, 0),
         (0.665, 0.10, 0), (0.685, 0.12, 0), (0.685, 0.19, 0), (0.665, 0.21, 0), (0.305, 0.21, 0),
         (0.295, 0.225, 0), (0.295, 0.33, 0), (0.28, 0.345, 0), (0.22, 0.345, 0), (0.17, 0.30, 0)]
    hb = C.lathe("WheelFlange", P, [flange], steps=192)
    cb = bmesh.new()
    for k in range(4):
        a = math.radians(45 + 90 * k)
        C.cyl_bm(cb, 0.052, 0.0, 0.4, seg=28, matrix=Matrix.Translation((0.50 * math.cos(a), 0.50 * math.sin(a), 0)))
        # small threaded hole for the drum/disc retaining screw between studs
        a2 = a + math.radians(45)
        if k in (0, 2):
            C.cyl_bm(cb, 0.030, 0.0, 0.4, seg=20, matrix=Matrix.Translation((0.40 * math.cos(a2), 0.40 * math.sin(a2), 0)))
    cut = C.mesh_obj("StudHoles", cb, [flange])
    boolean(hb, cut)
    out.append(C.finalize(hb, angle=40, remove=[cut]))
    # pressed zinc dust cap in the spigot
    P = [(0.0, 0.43, 0), (0.10, 0.425, 0), (0.17, 0.405, 0), (0.205, 0.37, 0), (0.215, 0.345, 0),
         (0.226, 0.335, 0), (0.226, 0.25, 0), (0.0, 0.25, 0)]
    out.append(C.finalize(C.lathe("DustCap", P, [cap_m], steps=128), angle=40))
    return out


def studs(steel):
    out = []
    for k in range(4):
        a = math.radians(45 + 90 * k)
        P = [(0.0, 0.06, 0), (0.088, 0.06, 0), (0.088, 0.10, 0), (0.054, 0.21, 0), (0.054, 0.27, 0)]
        z = 0.27
        for i in range(10):
            P += [(0.058, z + 0.012, 0), (0.050, z + 0.024, 0)]
            z += 0.024
        P += [(0.044, z + 0.02, 0), (0.0, z + 0.02, 0)]
        ob = C.lathe("Stud", P, [steel], steps=32)
        ob.matrix_world = Matrix.Translation((0.50 * math.cos(a), 0.50 * math.sin(a), 0))
        out.append(C.finalize(ob, angle=50))
    return out


def bearing_body(iron, mach, seal_m, tone_m):
    out = []
    # bearing outer body (forged), with a seal ring against the flange
    P = [(0.30, -0.56, 1), (0.40, -0.56, 0), (0.42, -0.54, 0), (0.42, -0.20, 0), (0.44, -0.16, 0),
         (0.44, 0.02, 0), (0.42, 0.045, 1), (0.30, 0.045, 1)]
    out.append(C.finalize(C.lathe("BearingBody", P, [iron, mach], steps=160), angle=35))
    P = [(0.30, 0.040, 0), (0.425, 0.040, 0), (0.425, 0.075, 0), (0.30, 0.075, 0)]
    out.append(C.finalize(C.lathe("Seal", P, [seal_m], steps=144), angle=40))
    # square mounting flange
    bm = bmesh.new()
    prism(bm, rounded_square(0.50, 0.17), -0.20, -0.105)
    mf = C.mesh_obj("MountFlange", bm, [iron])
    hb = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.cyl_bm(hb, 0.055, -0.5, 0.2, seg=28, matrix=Matrix.Translation((0.355 * sx, 0.355 * sy, 0)))
    C.cyl_bm(hb, 0.41, -0.5, 0.2, seg=96)
    holes = C.mesh_obj("FlangeHoles", hb, [iron])
    boolean(mf, holes)
    C.add_bevel(mf, 0.012, segments=2, angle=30)
    out.append(C.finalize(mf, angle=35, remove=[holes]))
    # ABS tone ring (48 teeth) pressed on the inboard end
    teeth = lambda r, z, t: r + (0.022 if (r > 0.30 and math.cos(48 * t) > 0.0) else 0.0)
    P = [(0.255, -0.64, 0), (0.33, -0.64, 0), (0.33, -0.555, 0), (0.255, -0.555, 0)]
    out.append(C.finalize(C.lathe("ToneRing", P, [tone_m], steps=48 * 8, mod=teeth), angle=45))
    # inner ring end + bore visible from inboard
    P = [(0.155, -0.66, 0), (0.255, -0.66, 0), (0.255, -0.50, 0), (0.155, -0.50, 0)]
    out.append(C.finalize(C.lathe("InnerRing", P, [mach], steps=128), angle=40))
    return out


def build():
    iron = mat_rusty_iron("HubIron", base=0.11, rust=0.55, scale=3.0)
    mach = mat_rusty_iron("HubMachined", base=0.32, rust=0.25, scale=6.0, seed=5.0, metal=0.9)
    flange = mat_rusty_iron("FlangeSteel", base=0.28, rust=0.65, scale=5.0, seed=2.0, metal=0.9)
    C.add_radial_aniso(flange, 0.5, "Z")
    steel = C.principled("StudSteel", (0.55, 0.55, 0.53), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    cap = C.principled("ZincCap", (0.62, 0.62, 0.60), metallic=1.0, rough=0.26)
    C.add_noise_bump(cap, scale=300, strength=0.05, distance=0.0005, rough_var=0.05)
    seal = C.mat_rubber("SealRubber")
    tone = mat_rusty_iron("ToneSteel", base=0.20, rust=0.4, scale=8.0, seed=9.0, metal=0.9)
    objs = wheel_flange(flange, cap) + studs(steel) + bearing_body(iron, mach, seal, tone)
    # axis horizontal, wheel side facing the camera side (-Y), turned a little
    C.transform_all(objs, Matrix.Rotation(math.radians(-28), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("mozzo-posteriore", objs, "mozzo-posteriore.py",
            "rear wheel hub bearing unit: wheel flange with 4 studs and dust cap, sealed bearing body with square 4-bolt mounting flange, toothed ABS ring",
            az=22, el=18, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
