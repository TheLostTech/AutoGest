"""Gearbox mount (supporto cambio) as removed from a small FWD car: cast-aluminium
bracket with a ribbed, pocketed arm running from a three-bolt mounting pad (spot-faced
holes) to a round eye that holds the rubber bush; the black rubber bush shows its two
kidney-shaped voids and is bonded around a long steel inner sleeve that bolts to the
body side.

Eye axis along Y, arm along -X; units ~ decimetres (overall length ~15 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RX = Matrix.Rotation(math.radians(-90), 4, "X")     # lathe Z -> world +Y


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def ylathe(name, prof, mats, at=(0, 0, 0), steps=96, bevel=None, angle=40):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = Matrix.Translation(at) @ RX
    return fin(ob, bevel=bevel, angle=angle)


def mat_cast_alu(name, base=0.44, rough=0.48):
    """Sand-cast aluminium: mottled tone, grainy bump, grime in the crevices (AO)."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.08
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 1.0
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.05, base * 1.03, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.79, base * 0.75, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.12, 0.11, 0.10, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.2
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 520.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.16
    bp.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def sector_prism(bm, r0, r1, a0, a1, y0, y1, n=24, rnd=0.0):
    """Kidney-shaped prism (annular sector with rounded ends) along Y."""
    pts = []
    rm, hw = (r0 + r1) / 2, (r1 - r0) / 2
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((r1 * math.cos(a), r1 * math.sin(a)))
    for i in range(1, 12):
        t = math.pi * i / 12
        c = (rm * math.cos(a1), rm * math.sin(a1))
        d = Vector((math.cos(a1), math.sin(a1)))
        tg = Vector((-math.sin(a1), math.cos(a1)))
        p = Vector(c) + d * hw * math.cos(t) + tg * hw * math.sin(t)
        pts.append((p.x, p.y))
    for i in range(n + 1):
        a = a1 - (a1 - a0) * i / n
        pts.append((r0 * math.cos(a), r0 * math.sin(a)))
    for i in range(1, 12):
        t = math.pi * i / 12
        c = (rm * math.cos(a0), rm * math.sin(a0))
        d = Vector((math.cos(a0), math.sin(a0)))
        tg = Vector((math.sin(a0), -math.cos(a0)))
        p = Vector(c) - d * hw * math.cos(t) + tg * hw * math.sin(t)
        pts.append((p.x, p.y))
    frames = [(Vector((0, y, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), pts) for y in (y0, y1)]
    C.sweep(bm, frames)


EYE_RO, EYE_RI, EYE_HL = 0.44, 0.36, 0.17


def eye(alu, rubber, steel):
    out = []
    P = [(EYE_RI, -EYE_HL, 0), (EYE_RO - 0.02, -EYE_HL, 0), (EYE_RO, -EYE_HL + 0.02, 0),
         (EYE_RO, EYE_HL - 0.02, 0), (EYE_RO - 0.02, EYE_HL, 0), (EYE_RI, EYE_HL, 0)]
    out.append(ylathe("EyeHousing", P, [alu], steps=128, bevel=0.006))
    # rubber bush, slightly recessed, concave faces, with two kidney voids
    P = [(0.112, -0.115, 0), (0.20, -0.135, 0), (0.30, -0.148, 0), (EYE_RI + 0.004, -0.155, 0),
         (EYE_RI + 0.004, 0.155, 0), (0.30, 0.148, 0), (0.20, 0.135, 0), (0.112, 0.115, 0)]
    rb = C.lathe("Bush", P, [rubber], steps=128)
    rb.matrix_world = RX.copy()
    cuts = []
    for a in (math.radians(90), math.radians(270)):
        bm = bmesh.new()
        sector_prism(bm, 0.18, 0.29, a - math.radians(48), a + math.radians(48), -0.5, 0.5)
        C.fix_normals(bm)
        cuts.append(C.mesh_obj("Void", bm, [rubber]))
    out.append(fin(rb, bevel=0.01, angle=45, cutters=cuts))
    # bonded steel inner sleeve, longer than the housing
    P = [(0.062, -0.23, 0), (0.108, -0.23, 0), (0.112, -0.225, 0), (0.112, 0.225, 0), (0.108, 0.23, 0), (0.062, 0.23, 0)]
    out.append(ylathe("Sleeve", P, [steel], steps=64))
    return out


def arm(alu):
    out = []
    # tapered arm from the pad (x=-1.05) to the eye (x=0), section height/width taper
    frames = []
    n = 16
    for i in range(n + 1):
        u = i / n
        x = -1.02 + 0.98 * u
        hh = 0.42 - 0.12 * u + 0.05 * math.sin(math.pi * u)
        hw = 0.15 - 0.03 * u
        z = -0.05 * (1 - u)
        sec = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        frames.append((Vector((x, 0, z)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Arm", bm, [alu])
    # pockets on both flanks (I-beam look) and the eye bore
    cuts = []
    for sy in (-1, 1):
        bm = bmesh.new()
        frames = []
        for i in range(n + 1):
            u = i / n
            x = -0.86 + 0.52 * u
            hh = 0.30 - 0.11 * u
            sec = [(-0.12, -hh), (0.12, -hh), (0.12, hh), (-0.12, hh)]
            frames.append((Vector((x, sy * 0.19, -0.04 * (1 - u))), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
        C.sweep(bm, frames)
        C.fix_normals(bm)
        cuts.append(C.mesh_obj("Pocket", bm, [alu]))
    bm = bmesh.new()
    C.cyl_bm(bm, EYE_RI + 0.01, -0.6, 0.6, seg=96, matrix=RX)
    cuts.append(C.mesh_obj("EyeBore", bm, [alu]))
    out.append(fin(ob, bevel=0.022, angle=30, seg=3, cutters=cuts))
    # diagonal stiffening rib inside each pocket
    bm = bmesh.new()
    for sy in (-1, 1):
        M = Matrix.Translation((-0.60, sy * 0.08, -0.04)) @ Matrix.Rotation(math.radians(38), 4, "Y")
        C.box_bm(bm, 0.62, 0.05, 0.05, matrix=M)
    rib = C.mesh_obj("Rib", bm, [alu])
    out.append(fin(rib, bevel=0.015, angle=30))
    return out


def pad(alu, steel):
    out = []
    holes = [(0.0, 0.40), (-0.30, -0.34), (0.30, -0.34)]   # (y, z)
    bm = bmesh.new()
    C.box_bm(bm, 0.13, 0.86, 0.98, center=(-1.10, 0, -0.03))
    ob = C.mesh_obj("Pad", bm, [alu])
    cuts = []
    for (y, z) in holes:
        bm = bmesh.new()
        C.cyl_bm(bm, 0.055, -0.4, 0.4, seg=40, matrix=Matrix.Translation((-1.10, y, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
        cuts.append(C.mesh_obj("Hole", bm, [alu]))
    # corner relief on the pad (cast shape, not a slab)
    for sy in (-1, 1):
        bm = bmesh.new()
        M = Matrix.Translation((-1.10, sy * 0.52, 0.42)) @ Matrix.Rotation(sy * math.radians(35), 4, "X")
        C.box_bm(bm, 0.4, 0.3, 0.5, matrix=M)
        cuts.append(C.mesh_obj("Corner", bm, [alu]))
    out.append(fin(ob, bevel=0.025, angle=30, seg=3, cutters=cuts))
    # spot-faced bosses on the outer face (toward +X, arm side) around each hole
    for (y, z) in holes:
        P = [(0.056, 0.0, 0), (0.11, 0.0, 0), (0.11, 0.05, 0), (0.10, 0.06, 0), (0.056, 0.06, 0)]
        bo = C.lathe("Boss", P, [alu], steps=48)
        bo.matrix_world = Matrix.Translation((-1.05, y, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        out.append(fin(bo, angle=40))
    # steel thread inserts visible in the holes
    for (y, z) in holes:
        P = [(0.042, -0.07, 0), (0.056, -0.07, 0), (0.056, 0.115, 0), (0.042, 0.115, 0)]
        sl = C.lathe("Insert", P, [steel], steps=32)
        sl.matrix_world = Matrix.Translation((-1.10, y, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        out.append(fin(sl, angle=40))
    return out


def body_bracket(paint, steel):
    """black stamped body-side bracket behind the eye, held by the through-bolt."""
    out = []
    yb0, yb1 = EYE_HL + 0.10, EYE_HL + 0.16
    pts = []
    for i in range(24):
        a = math.pi / 2 + math.pi * i / 23
        pts.append((0.24 * math.cos(a), 0.24 * math.sin(a)))
    pts += [(0.10, -0.24), (0.62, 0.20), (0.62, 0.52), (0.30, 0.52), (0.0, 0.24)]
    bm = bmesh.new()
    C.sweep(bm, [(Vector((0, y, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), pts) for y in (yb0, yb1)])
    C.fix_normals(bm)
    out.append(fin(C.mesh_obj("BodyBracket", bm, [paint]), bevel=0.015))
    # foot bent over toward -Y with two bolt holes
    bm = bmesh.new()
    C.box_bm(bm, 0.34, 0.50, 0.05, center=(0.46, yb1 - 0.25, 0.545))
    cb = bmesh.new()
    for x in (0.38, 0.54):
        C.cyl_bm(cb, 0.04, 0.3, 0.8, seg=24, matrix=Matrix.Translation((x, yb1 - 0.30, 0)))
    out.append(fin(C.mesh_obj("Foot", bm, [paint]), bevel=0.012, cutters=[C.mesh_obj("FootHoles", cb, [])]))
    # through-bolt: head + washer on the front face, nut at the back
    M = RX.copy()
    P = [(0.0, -0.255, 0), (0.16, -0.255, 0), (0.16, -0.23, 0), (0.0, -0.23, 0)]
    out.append(ylathe("Washer", P, [steel], steps=48))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.13, -0.33, -0.255, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    out.append(fin(C.mesh_obj("BoltHead", bm, [steel]), bevel=0.012))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.13, yb1, yb1 + 0.09, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    out.append(fin(C.mesh_obj("Nut", bm, [steel]), bevel=0.012))
    P = [(0.0, -0.26, 0), (0.06, -0.26, 0), (0.06, yb1 + 0.14, 0), (0.0, yb1 + 0.14, 0)]
    out.append(ylathe("BoltShank", P, [steel], steps=32))
    # spacer filling the gap between sleeve and bracket
    P = [(0.062, EYE_HL + 0.05, 0), (0.12, EYE_HL + 0.05, 0), (0.12, yb0, 0), (0.062, yb0, 0)]
    out.append(ylathe("Spacer", P, [steel], steps=48))
    return out


def build():
    alu = mat_cast_alu("MountAlu", base=0.44, rough=0.48)
    rubber = C.mat_rubber("BushRubber")
    rb = next(n for n in rubber.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rb.inputs["Roughness"].default_value = 0.62
    steel = C.principled("ZincSleeve", (0.62, 0.62, 0.60), metallic=1.0, rough=0.28)
    C.add_noise_bump(steel, scale=800, strength=0.04, distance=0.0005, rough_var=0.06)
    paint = C.mat_paint("BracketBlack", (0.025, 0.025, 0.027, 1), rough=0.42, coat=0.15)
    C.add_noise_bump(paint, scale=600, strength=0.05, distance=0.0005)
    objs = eye(alu, rubber, steel) + arm(alu) + pad(alu, steel) + body_bracket(paint, steel)
    # stand it on the pad's lower edge, eye toward the viewer's right, bush face visible
    C.transform_all(objs, Matrix.Rotation(math.radians(10), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("supporto-cambio", objs, "supporto-cambio.py",
            "gearbox mount: cast-aluminium bracket with ribbed arm and three-bolt mounting pad, "
            "rubber bush with kidney voids and steel inner sleeve",
            az=22, el=26, lens=70, fill=0.84, **kw)
