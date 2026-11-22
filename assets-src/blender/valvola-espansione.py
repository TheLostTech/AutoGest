"""A/C block-type thermostatic expansion valve (valvola di espansione) as removed from the
bulkhead of a small car: machined aluminium block with fly-cut faces, two refrigerant
bores on each side (large suction, small liquid) with O-ring counterbores, a central
through-hole for the mounting stud, a threaded hole beside it, and the stainless
crimped power-element dome on top with its sealing plug; sealed adjusting plug below."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm.  Bores run along Y.
BX, BY, BZ = 3.2, 2.6, 4.6
ZS, ZL = 1.05, -1.15            # suction / liquid bore heights


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=64, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def mat_milled(name="MilledAlu", base=0.62, rough=0.24):
    """aluminium with faint fly-cutter arcs (concentric rings centred off the part)"""
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    off = nt.nodes.new("ShaderNodeVectorMath")
    off.operation = "ADD"
    off.inputs[1].default_value = (6.0, 0.0, 9.0)
    nt.links.new(co, off.inputs[0])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "RINGS"
    wv.rings_direction = "SPHERICAL"
    wv.inputs["Scale"].default_value = 9.0
    wv.inputs["Distortion"].default_value = 0.4
    wv.inputs["Detail"].default_value = 2.0
    nt.links.new(off.outputs[0], wv.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 2.5
    g.inputs["Detail"].default_value = 6.0
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.06
    rr.inputs["To Max"].default_value = rough + 0.10
    nt.links.new(g.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    g2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g2.inputs["Vector"])
    g2.inputs["Scale"].default_value = 90.0
    bump2 = nt.nodes.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.04
    bump2.inputs["Distance"].default_value = 0.002
    nt.links.new(g2.outputs["Fac"], bump2.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bump2.inputs["Normal"])
    nt.links.new(bump2.outputs["Normal"], b.inputs["Normal"])
    em = C.edge_mask(nt, 0.05, 4.0)
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    nt.links.new(em, mc.inputs["Factor"])
    mc.inputs["A"].default_value = (base, base, base * 0.99, 1)
    mc.inputs["B"].default_value = (0.80, 0.80, 0.80, 1)
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    return m


def block(alu, bore_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, BX, BY, BZ, center=(0, 0, 0))
    # stepped shoulder: the upper (suction) section is a little narrower front-to-back
    ob = C.mesh_obj("Block", bm, [alu, bore_m])
    cutters = []
    holes = [((0.0, ZS), 0.62, 0.86), ((-0.35, ZL), 0.40, 0.60), ((0.55, -0.05), 0.33, 0.0), ((-0.85, -0.05), 0.26, 0.0)]
    for (x, z), r, rc in holes:
        cb = bmesh.new()
        R = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        C.cyl_bm(cb, r, -BY, BY, seg=64, matrix=R, mat=1)
        cut = C.mesh_obj("Bore", cb, [bore_m])
        cut.data.materials.append(bore_m)
        cutters.append(cut)
        bo = C.add_boolean(ob, cut)
        bo.use_self = True
        bo.use_hole_tolerant = True
        if rc:
            for sy in (-1, 1):
                cb = bmesh.new()
                C.cyl_bm(cb, rc, -0.18, 0.18, seg=64, mat=1,
                         matrix=Matrix.Translation((x, sy * BY / 2, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
                cut = C.mesh_obj("Counterbore", cb, [bore_m])
                cutters.append(cut)
                bo = C.add_boolean(ob, cut)
                bo.use_self = True
                bo.use_hole_tolerant = True
    # side relief milled into the lower half (typical step between port halves)
    for sx in (-1, 1):
        cb = bmesh.new()
        C.box_bm(cb, 0.5, BY + 1, 1.6, center=(sx * (BX / 2 + 0.05), 0, -1.6))
        cut = C.mesh_obj("Relief", cb, [alu])
        cutters.append(cut)
        bo = C.add_boolean(ob, cut)
        bo.use_self = True
    C.add_bevel(ob, 0.06, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35, remove=cutters))
    return out


def head(steel, dark, alu):
    out = []
    z = BZ / 2
    # threaded boss, then crimped dome
    P = [(0.0, z - 0.02, 0), (1.05, z - 0.02, 0), (1.05, z + 0.30, 0), (0.98, z + 0.36, 0), (0.0, z + 0.36, 0)]
    out.append(lathe_at("Boss", P, [alu], origin=(0, 0, 0), steps=96, bevel=0.03))
    P = [(0.0, z + 0.34, 0), (1.55, z + 0.34, 0), (1.62, z + 0.40, 0), (1.62, z + 0.56, 0), (1.55, z + 0.62, 0),
         (1.42, z + 0.64, 0), (1.32, z + 0.78, 0), (1.05, z + 1.02, 0), (0.62, z + 1.16, 0), (0.30, z + 1.19, 0),
         (0.0, z + 1.20, 0)]
    out.append(lathe_at("Dome", P, [steel], steps=128, bevel=0.012))
    P = [(0.0, z + 1.17, 0), (0.24, z + 1.17, 0), (0.24, z + 1.27, 0), (0.20, z + 1.31, 0), (0.0, z + 1.31, 0)]
    out.append(lathe_at("SealPlug", P, [dark], steps=48, bevel=0.01))
    # sealed adjuster plug underneath
    P = [(0.0, -BZ / 2 + 0.02, 0), (0.62, -BZ / 2 + 0.02, 0), (0.62, -BZ / 2 - 0.22, 0), (0.55, -BZ / 2 - 0.28, 0), (0.0, -BZ / 2 - 0.28, 0)]
    ob = C.lathe("Adjuster", P, [steel], steps=96, mod=lambda r, zz, t: min(r, 0.56 / math.cos((t % (math.pi / 3)) - math.pi / 6)) if r > 0.5 else r)
    out.append(C.finalize(ob, angle=38))
    return out


def build():
    alu = mat_milled("MilledAlu", 0.60, 0.24)
    bore = C.principled("BoreAlu", (0.30, 0.30, 0.30), metallic=1.0, rough=0.35)
    steel = C.principled("Stainless", (0.66, 0.66, 0.65), metallic=1.0, rough=0.18)
    C.add_noise_bump(steel, scale=60, strength=0.04, distance=0.002, rough_var=0.05)
    dark = C.principled("DarkPlug", (0.08, 0.08, 0.085), metallic=0.8, rough=0.35)
    objs = block(alu, bore) + head(steel, dark, alu)
    C.transform_all(objs, Matrix.Rotation(math.radians(-8), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("valvola-espansione", objs, "valvola-espansione.py",
            "A/C block expansion valve: machined aluminium block with refrigerant bores and O-ring seats, stainless power-element dome on top",
            az=34, el=20, lens=70, fill=0.78,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
