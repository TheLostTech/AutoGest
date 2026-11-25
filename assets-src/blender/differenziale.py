"""Rear differential (differenziale posteriore, independent rear suspension type): dark
cast-iron carrier housing ("pumpkin") with a ribbed pinion nose, the cast-aluminium rear
cover with horizontal cooling fins and a ring of flange bolts, fill plug and breather;
input companion flange with four bolt holes and pinion nut at the front, two six-hole
drive-shaft output flanges on seal bosses at the sides, and rubber-bushed mounting ears
on the nose and on the cover.

Pinion axis +X (input flange at +X), output axis Y; units ~ decimetres."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # lathe Z -> world +X
RXm = Matrix.Rotation(math.radians(-90), 4, "X")    # lathe Z -> world +Y
XC = -0.58          # cover joint plane
RB = 1.12           # bowl radius


def fin(ob, bevel=None, angle=35, seg=2, cutters=(), op="DIFFERENCE"):
    for c in cutters:
        m = C.add_boolean(ob, c, op=op)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M, steps=96, bevel=None, angle=40, mod=None, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def hexp(name, r, z0, z1, mat, M, bevel=0.008):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    return fin(C.mesh_obj(name, bm, [mat]), bevel=bevel)


def cast_alu(name, base=0.50, rough=0.46):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.12
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 1.0
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.04, base * 1.04, base * 1.02, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.79, base * 0.74, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.095, 0.085, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.22
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 420.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.16
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- housing
def housing(iron, steel):
    out = []
    nose_r = {0.86, 0.64}

    def ribs(r, z, t):
        if round(r, 3) not in nose_r:
            return r
        v = math.cos(6 * t + math.pi / 6)
        return r + 0.05 * max(0.0, (v - 0.86) / 0.14)
    P = [(0.0, XC, 0), (1.02, XC, 0), (1.06, XC + 0.02, 0), (1.06, XC + 0.08, 0), (RB, XC + 0.12, 0),
         (RB, -0.12, 0), (1.08, 0.12, 0), (0.98, 0.32, 0), (0.86, 0.52, 0), (0.64, 0.80, 0), (0.50, 0.98, 0),
         (0.40, 1.02, 0), (0.38, 1.20, 0), (0.0, 1.20, 0)]
    out.append(lathe_at("Carrier", P, [iron], RY, steps=192, bevel=0.012, mod=ribs))
    # side bosses for the output shafts
    for s in (-1, 1):
        M = Matrix.Translation((-0.12, 0, 0)) @ (RXm if s > 0 else Matrix.Rotation(math.radians(90), 4, "X"))
        P = [(0.0, 0.6, 0), (0.62, 0.6, 0), (0.62, 1.0, 0), (0.56, 1.10, 0), (0.44, 1.14, 0), (0.42, 1.20, 0),
             (0.0, 1.20, 0)]
        out.append(lathe_at("SideBoss", P, [iron], M, steps=128, bevel=0.01))
    # casting ribs from the nose to the bowl (top & bottom)
    bm = bmesh.new()
    for sz in (-1, 1):
        M = Matrix.Translation((0.55, 0, sz * 0.78)) @ Matrix.Rotation(sz * math.radians(-33), 4, "Y")
        C.box_bm(bm, 0.75, 0.10, 0.10, matrix=M)
    out.append(fin(C.mesh_obj("NoseRibs", bm, [iron]), bevel=0.03, seg=3))
    # front mounting ears (left/right, bushes vertical) on top of the nose
    for s in (-1, 1):
        cx, cy, cz = 0.62, s * 0.82, 0.62
        bm = bmesh.new()
        C.box_bm(bm, 0.30, 0.55, 0.16, center=(0.62, s * 0.52, 0.62))
        C.cyl_bm(bm, 0.22, cz - 0.10, cz + 0.10, seg=48, matrix=Matrix.Translation((cx, cy, 0)))
        cb = bmesh.new()
        C.cyl_bm(cb, 0.16, -1, 2, seg=48, matrix=Matrix.Translation((cx, cy, 0)))
        out.append(fin(C.mesh_obj("FrontEar", bm, [iron]), bevel=0.02, cutters=[C.mesh_obj("EarHole", cb, [iron])]))
    return out


def bushes(rubber, steel, centers, axis):
    out = []
    for (c, r0, r1, h) in centers:
        M = Matrix.Translation(c) @ Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
        P = [(0.075, -h * 0.55, 0), (r1 - 0.01, -h * 0.5, 0), (r1, -h * 0.45, 0), (r1, h * 0.45, 0),
             (r1 - 0.01, h * 0.5, 0), (0.075, h * 0.55, 0)]
        out.append(lathe_at("Bush", P, [rubber], M, steps=64, angle=50))
        P = [(0.05, -h * 0.62, 0), (0.078, -h * 0.62, 0), (0.078, h * 0.62, 0), (0.05, h * 0.62, 0)]
        out.append(lathe_at("BushSleeve", P, [steel], M, steps=40))
    return out


def cover(alu, steel, black):
    out = []
    P = [(0.0, XC - 0.34, 0), (0.42, XC - 0.33, 0), (0.75, XC - 0.28, 0), (0.95, XC - 0.18, 0),
         (1.03, XC - 0.08, 0), (1.06, XC - 0.04, 0), (1.06, XC, 0), (0.0, XC, 0)]
    out.append(lathe_at("Cover", P, [alu], RY, steps=192, bevel=0.01))
    # horizontal cooling fins = slabs intersected with an enlarged dome
    Pd = [(0.0, XC - 0.44, 0), (0.48, XC - 0.42, 0), (0.84, XC - 0.34, 0), (1.04, XC - 0.20, 0),
          (1.06, XC - 0.04, 0), (0.0, XC - 0.04, 0)]
    dome = C.lathe("FinDome", Pd, [alu], steps=128)
    dome.matrix_world = RY.copy()
    bm = bmesh.new()
    for k in range(-5, 6):
        z = k * 0.17
        C.box_bm(bm, 0.6, 2.4, 0.045, center=(XC - 0.30, 0, z))
    fins = C.mesh_obj("Fins", bm, [alu])
    out.append(fin(fins, bevel=0.012, cutters=[dome], op="INTERSECT"))
    # flange bolts round the joint
    for k in range(12):
        a = math.tau * (k + 0.5) / 12
        M = Matrix.Translation((XC, 1.0 * math.cos(a), 1.0 * math.sin(a))) @ Matrix.Rotation(math.radians(-90), 4, "Y")
        out.append(hexp("CoverBolt", 0.045, 0.0, 0.05, steel, M, bevel=0.006))
        P = [(0.0, 0.0, 0), (0.06, 0.0, 0), (0.06, 0.012, 0), (0.0, 0.012, 0)]
        out.append(lathe_at("BoltWasher", P, [steel], M, steps=32))
    # fill plug (hex) on a boss at the right side of the cover
    M = Matrix.Translation((XC - 0.20, 0.84, -0.30)) @ Matrix.Rotation(math.radians(-60), 4, "X") @ Matrix.Rotation(math.radians(-20), 4, "Y")
    P = [(0.0, -0.2, 0), (0.11, -0.2, 0), (0.11, 0.04, 0), (0.10, 0.05, 0), (0.0, 0.05, 0)]
    out.append(lathe_at("PlugBoss", P, [alu], M, steps=48, bevel=0.006))
    out.append(hexp("FillPlug", 0.06, 0.05, 0.11, steel, M))
    # rear mounting ear on top of the cover (bush axis along Y)
    bm = bmesh.new()
    C.box_bm(bm, 0.22, 0.30, 0.36, center=(XC - 0.16, 0, 1.0))
    C.cyl_bm(bm, 0.19, -0.15, 0.15, seg=48, matrix=Matrix.Translation((XC - 0.16, 0, 1.20)) @ RXm)
    cb = bmesh.new()
    C.cyl_bm(cb, 0.135, -1, 1, seg=48, matrix=Matrix.Translation((XC - 0.16, 0, 1.20)) @ RXm)
    out.append(fin(C.mesh_obj("RearEar", bm, [alu]), bevel=0.025, seg=3, cutters=[C.mesh_obj("EarHole", cb, [alu])]))
    # breather on top of the carrier
    P = [(0.0, 0.0, 0), (0.035, 0.0, 0), (0.035, 0.12, 0), (0.06, 0.13, 0), (0.06, 0.17, 0), (0.0, 0.18, 0)]
    out.append(lathe_at("Breather", P, [black], Matrix.Translation((0.05, -0.30, 1.04)), steps=32))
    return out


def flanges(steel, mach, dark, rubber):
    out = []
    # input companion flange + nut + seal
    x0 = 1.20
    P = [(0.0, x0 - 0.02, 0), (0.30, x0 - 0.02, 0), (0.30, x0 + 0.02, 0), (0.0, x0 + 0.02, 0)]
    out.append(lathe_at("PinionSeal", P, [rubber], RY, steps=64))
    P = [(0.0, x0 + 0.02, 0), (0.20, x0 + 0.02, 0), (0.20, x0 + 0.16, 0), (0.0, x0 + 0.16, 0)]
    out.append(lathe_at("FlangeNeck", P, [steel], RY, steps=64, bevel=0.006))
    P = [(0.0, x0 + 0.16, 0), (0.46, x0 + 0.16, 0), (0.48, x0 + 0.18, 0), (0.48, x0 + 0.24, 0), (0.46, x0 + 0.26, 0),
         (0.0, x0 + 0.26, 0)]
    cb = bmesh.new()
    for k in range(4):
        a = math.tau * k / 4 + math.pi / 4
        C.cyl_bm(cb, 0.045, x0, x0 + 0.4, seg=24, matrix=Matrix.Translation((0, 0.34 * math.cos(a), 0.34 * math.sin(a))) @ RY)
    out.append(lathe_at("InputFlange", P, [mach], RY, steps=128, bevel=0.006,
                        cutters=[C.mesh_obj("FlHoles", cb, [mach])]))
    out.append(hexp("PinionNut", 0.13, x0 + 0.26, x0 + 0.36, dark, RY, bevel=0.012))
    P = [(0.0, x0 + 0.36, 0), (0.07, x0 + 0.36, 0), (0.07, x0 + 0.40, 0), (0.05, x0 + 0.42, 0), (0.0, x0 + 0.42, 0)]
    out.append(lathe_at("PinionEnd", P, [mach], RY, steps=48))
    # output flanges both sides
    for s in (-1, 1):
        M = Matrix.Translation((-0.12, 0, 0)) @ (RXm if s > 0 else Matrix.Rotation(math.radians(90), 4, "X"))
        P = [(0.0, 1.20, 0), (0.32, 1.20, 0), (0.32, 1.23, 0), (0.0, 1.23, 0)]
        out.append(lathe_at("OutSeal", P, [rubber], M, steps=64))
        P = [(0.0, 1.23, 0), (0.22, 1.23, 0), (0.22, 1.30, 0), (0.50, 1.30, 0), (0.52, 1.32, 0), (0.52, 1.39, 0),
             (0.50, 1.41, 0), (0.0, 1.41, 0)]
        cb = bmesh.new()
        for k in range(6):
            a = math.tau * k / 6
            C.cyl_bm(cb, 0.04, 1.0, 1.6, seg=24, matrix=M @ Matrix.Translation((0.38 * math.cos(a), 0.38 * math.sin(a), 0)))
        out.append(lathe_at("OutFlange", P, [mach], M, steps=128, bevel=0.006,
                            cutters=[C.mesh_obj("OutHoles", cb, [mach])]))
        P = [(0.0, 1.41, 0), (0.16, 1.41, 0), (0.16, 1.44, 0), (0.13, 1.47, 0), (0.0, 1.47, 0)]
        out.append(lathe_at("OutCap", P, [dark], M, steps=64))
    return out


def build():
    iron = C.mat_cast_iron("CarrierIron", rust=0.35, base=0.11)
    alu = cast_alu("CoverAlu", base=0.42, rough=0.48)
    steel = C.principled("Zinc", (0.62, 0.62, 0.60), metallic=1.0, rough=0.28)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005, rough_var=0.05)
    mach = C.mat_machined("FlangeSteel", color=0.42, rough=0.30, rings=500)
    dark = C.principled("DarkSteel", (0.09, 0.09, 0.095), metallic=1.0, rough=0.40)
    C.add_noise_bump(dark, scale=600, strength=0.05, distance=0.0005)
    rubber = C.mat_rubber("Rubber")
    black = C.mat_black_plastic("Breather")
    objs = housing(iron, steel) + cover(alu, steel, black) + flanges(steel, mach, dark, rubber)
    objs += bushes(rubber, steel, [((0.62, -0.82, 0.62), 0.07, 0.165, 0.22), ((0.62, 0.82, 0.62), 0.07, 0.165, 0.22)],
                   Vector((0, 0, 1)))
    objs += bushes(rubber, steel, [((XC - 0.16, 0, 1.20), 0.07, 0.14, 0.32)], Vector((0, 1, 0)))
    # cover toward the viewer, input flange receding to the back-right
    C.transform_all(objs, Matrix.Rotation(math.radians(172), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("differenziale", objs, "differenziale.py",
            "rear differential: cast-iron carrier housing with finned aluminium rear cover, input companion "
            "flange, two drive-shaft output flanges, rubber-bushed mounting ears",
            az=35, el=22, lens=70, fill=0.84, **kw)
