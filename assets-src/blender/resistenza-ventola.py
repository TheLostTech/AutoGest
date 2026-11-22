"""Cooling fan resistor (resistenza elettroventola radiatore) as removed from the fan
shroud of a small car: zinc-plated stamped steel bracket with folded stiffening edges and
two screw ears, two grooved ceramic insulator blocks, two helical resistance-wire coils
stretched between them and joined by a bridge, crimped terminal tabs, and a short twin
lead in a sleeve running to a black two-pin connector with locking latch."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm
PL, PW = 8.2, 3.4               # bracket plate length (X), width (Y)
XC = 2.75                       # ceramic block x
CR, WR, CP = 0.36, 0.045, 0.17  # coil radius, wire radius, coil pitch
CZ = 1.10                       # coil axis height
CY = (-0.68, 0.68)
ZTM = 1.76                      # terminal tab height (on top of the ceramic)


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), matrix=None, bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center, matrix=matrix)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=3):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def smooth_path(ctrl, n=12):
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def mat_ceramic(name="Steatite"):
    m = C.principled(name, (0.80, 0.77, 0.68), rough=0.62)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.5
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Max"].default_value = 0.5
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mc.inputs["Factor"])
    mc.inputs["A"].default_value = (0.80, 0.77, 0.68, 1)
    mc.inputs["B"].default_value = (0.45, 0.38, 0.30, 1)       # heat discolouration / dust
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    C.add_noise_bump(m, scale=120, strength=0.12, distance=0.004)
    return m


def mat_nichrome(name="Nichrome"):
    m = C.principled(name, (0.42, 0.40, 0.38), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1.2
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], mc.inputs["Factor"])
    mc.inputs["A"].default_value = (0.48, 0.46, 0.44, 1)
    mc.inputs["B"].default_value = (0.30, 0.25, 0.22, 1)        # heat-tinted oxide
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def bracket(zinc):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, PL, PW, 0.12, center=(0, 0, 0.06))
    for sy in (-1, 1):
        C.box_bm(bm, PL - 1.6, 0.12, 0.55, center=(0, sy * (PW / 2 - 0.06), 0.33))
    # screw ears (offset, slightly raised)
    for sx in (-1, 1):
        C.box_bm(bm, 1.3, 1.5, 0.12, center=(sx * (PL / 2 + 0.55), sx * 0.6, 0.06))
    pl = C.mesh_obj("Bracket", bm, [zinc])
    cut = []
    for sx in (-1, 1):
        cb = bmesh.new()
        C.cyl_bm(cb, 0.28, -1, 1, seg=32, matrix=Matrix.Translation((sx * (PL / 2 + 0.7), sx * 0.6, 0)))
        c = C.mesh_obj("Hole", cb, [zinc])
        bo = C.add_boolean(pl, c)
        bo.use_self = True
        cut.append(c)
    # embossed stiffening rib in the plate
    C.add_bevel(pl, 0.04, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35, remove=cut))
    bm = bmesh.new()
    C.box_bm(bm, PL - 3.2, 0.5, 0.06, center=(0, 0, 0.14))
    em = C.mesh_obj("Emboss", bm, [zinc])
    C.add_bevel(em, 0.03, segments=2, angle=30)
    out.append(C.finalize(em, angle=35))
    return out


def ceramics(cer, steel):
    out = []
    for sx in (-1, 1):
        x = sx * XC
        out.append(rbox("Ceramic", cer, 0.75, PW - 0.5, 1.6, center=(x, 0, 0.12 + 0.8), bevel=0.12, seg=3))
        # grooves holding the coil ends (dark slot strips)
        for y in CY:
            out.append(rbox("Seat", cer, 0.85, 0.42, 0.32, center=(x, y, CZ), bevel=0.08))
        # rivets through the bracket
        for y in (-1.05, 1.05):
            P = [(0.0, 1.72, 0), (0.22, 1.72, 0), (0.25, 1.76, 0), (0.22, 1.82, 0), (0.0, 1.83, 0)]
            ob = C.lathe("Rivet", P, [steel], steps=24)
            ob.matrix_world = Matrix.Translation((x, y, 0))
            out.append(C.finalize(ob, angle=40))
    return out


def coils(wire):
    out = []
    x0, x1 = -XC + 0.40, XC - 0.40
    n = int((x1 - x0) / CP * 24)
    for j, y in enumerate(CY):
        pts = [Vector((x0 + (x1 - x0) * i / n, y + CR * math.cos(math.tau * (x1 - x0) * i / n / CP),
                       CZ + CR * math.sin(math.tau * (x1 - x0) * i / n / CP))) for i in range(n + 1)]
        out.append(tube("Coil%d" % j, pts, WR, wire, res=2))
    # bridge joining the two coils on the right block, tails into the left block
    out.append(tube("Bridge", [Vector((x1, CY[0], CZ + CR)), Vector((x1 + 0.35, CY[0], CZ + CR + 0.08)),
                               Vector((x1 + 0.35, CY[1], CZ + CR + 0.08)), Vector((x1, CY[1], CZ + CR))], WR * 1.4, wire, res=2))
    return out


def terminals(tin, sleeve, wire_a, wire_b, plug):
    out = []
    xt = -XC - 0.38
    for y in CY:
        out.append(rbox("TermTab", tin, 0.75, 0.38, 0.06, center=(xt - 0.05, y, ZTM), bevel=0.02))
        out.append(rbox("Crimp", tin, 0.42, 0.42, 0.22, center=(xt - 0.45, y, ZTM), bevel=0.05))
        out.append(tube("Tail", [Vector((-XC + 0.4, y, CZ + CR)), Vector((-XC + 0.1, y, ZTM - 0.1)), Vector((xt + 0.25, y, ZTM))],
                        WR * 1.4, wire_a, res=2))
    # twin lead: two insulated wires into a sleeve, out to the connector
    ends = []
    for k, y in enumerate(CY):
        mat = wire_a if k == 0 else wire_b
        ctrl = [(xt - 0.6, y, ZTM), (xt - 1.3, y * 0.55, ZTM + 0.05), (xt - 1.9, y * 0.2, CZ + 0.4)]
        out.append(tube("Wire%d" % k, smooth_path(ctrl, 8), 0.16, mat, res=3))
    ctrl = [(xt - 1.85, 0, CZ + 0.45), (xt - 2.3, -0.6, CZ - 0.25), (xt - 2.6, -2.2, 0.32), (xt - 2.2, -3.8, 0.3)]
    pts = smooth_path(ctrl, 12)
    out.append(tube("Sleeve", pts, 0.30, sleeve, res=4))
    d = (pts[-1] - pts[-3]).normalized()
    M = Matrix.Translation(pts[-1] + d * 0.85) @ d.to_track_quat("Y", "Z").to_matrix().to_4x4()
    bm = bmesh.new()
    C.box_bm(bm, 1.6, 1.8, 1.05, matrix=M)
    C.box_bm(bm, 0.6, 0.7, 0.22, matrix=M @ Matrix.Translation((0, 0.15, 0.6)))
    C.box_bm(bm, 0.9, 0.5, 0.8, matrix=M @ Matrix.Translation((0, -1.05, 0)))
    pg = C.mesh_obj("Plug", bm, [plug])
    C.add_bevel(pg, 0.07, segments=2, angle=30)
    out.append(C.finalize(pg, angle=35))
    return out


def build():
    zinc = C.principled("Zinc", (0.58, 0.59, 0.61), metallic=1.0, rough=0.36)
    C.add_noise_bump(zinc, scale=80, strength=0.05, distance=0.002, rough_var=0.07)
    steel = C.principled("Steel", (0.60, 0.60, 0.60), metallic=1.0, rough=0.3)
    cer = mat_ceramic()
    wire = mat_nichrome()
    tin = C.principled("Tin", (0.76, 0.74, 0.70), metallic=1.0, rough=0.25)
    sleeve = C.mat_black_plastic("Sleeve", rough=0.6, color=0.025)
    wa = C.principled("WireRed", (0.32, 0.03, 0.025), rough=0.4)
    wb = C.principled("WireBrown", (0.11, 0.06, 0.035), rough=0.4)
    plug = C.mat_black_plastic("PlugPA", rough=0.45, color=0.03)
    objs = bracket(zinc) + ceramics(cer, steel) + coils(wire) + terminals(tin, sleeve, wa, wb, plug)
    C.transform_all(objs, Matrix.Rotation(math.radians(-12), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("resistenza-ventola", objs, "resistenza-ventola.py",
            "radiator cooling fan resistor: steel bracket with two ceramic blocks, two coiled resistance wires, lead to a two-pin connector",
            az=26, el=40, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
