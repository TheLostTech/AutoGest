"""Automatic transmission control unit (centralina cambio automatico, TCU): compact
die-cast aluminium base tray with three mounting tabs carrying rubber grommets and steel
sleeves, black glass-filled plastic cover with a moulded stiffening-rib grid, clip lugs
and a recessed blank label, and one large black multi-pin connector header (two pin
fields, coding ribs) with its swing locking lever.

Units ~ decimetres (~13 x 9 cm footprint)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
L, W = 1.20, 0.86          # footprint (X long, Y depth)
ZB, ZC = 0.11, 0.27        # base tray top, cover top
YF = -W / 2                # front long side (connector)


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def mat_cast_alu(name, base=0.50, rough=0.45, grain=520.0, wear=0.35):
    """Die-cast aluminium: mottled tone, fine grain, brighter worn edges."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 6.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.86, base * 0.86, base * 0.85, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.80, 0.80, 0.80, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def base(alu, steel, grommet):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, L, W, ZB, center=(0, 0, ZB / 2))
    out.append(fin(C.mesh_obj("Tray", bm, [alu]), bevel=0.02, seg=3))
    # small cooling ribs on the tray sides
    bm = bmesh.new()
    for i in range(9):
        x = -0.44 + 0.11 * i
        C.box_bm(bm, 0.022, 0.03, ZB - 0.035, center=(x, YF - 0.008, ZB / 2))
    out.append(fin(C.mesh_obj("TrayRibs", bm, [alu]), bevel=0.007))
    # three tabs: two on the right short side, one on the left
    for (x, y, sx) in ((L / 2, -0.24, 1), (L / 2, 0.24, 1), (-L / 2, 0.0, -1)):
        cx = x + sx * 0.13
        bm = bmesh.new()
        C.box_bm(bm, 0.28, 0.24, 0.045, center=(x + sx * 0.10, y, 0.0225))
        C.box_bm(bm, 0.05, 0.10, 0.08, center=(x + sx * 0.02, y, 0.06))
        cb = bmesh.new()
        C.cyl_bm(cb, 0.075, -0.1, 0.2, seg=40, matrix=Matrix.Translation((cx, y, 0)))
        out.append(fin(C.mesh_obj("Tab", bm, [alu]), bevel=0.01,
                       cutters=[C.mesh_obj("TabHole", cb, [alu])]))
        # rubber grommet + steel sleeve
        P = [(0.042, -0.03, 0), (0.095, -0.03, 0), (0.10, -0.02, 0), (0.08, -0.005, 0), (0.08, 0.05, 0),
             (0.10, 0.065, 0), (0.095, 0.075, 0), (0.042, 0.075, 0)]
        g = C.lathe("Grommet", P, [grommet], steps=48)
        g.matrix_world = Matrix.Translation((cx, y, 0))
        out.append(fin(g, angle=50))
        P = [(0.03, -0.035, 0), (0.044, -0.035, 0), (0.044, 0.085, 0), (0.05, 0.085, 0), (0.05, 0.095, 0), (0.03, 0.095, 0)]
        s = C.lathe("Sleeve", P, [steel], steps=40)
        s.matrix_world = Matrix.Translation((cx, y, 0))
        out.append(fin(s, angle=40))
    return out


def cover(plastic):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, L - 0.04, W - 0.04, ZC - ZB + 0.01, center=(0, 0, (ZB + ZC) / 2 - 0.005))
    ob = C.mesh_obj("Cover", bm, [plastic])
    cb = bmesh.new()
    C.box_bm(cb, 0.46, 0.34, 0.03, center=(-0.25, 0.10, ZC + 0.006))
    out.append(fin(ob, bevel=0.045, seg=4, cutters=[C.mesh_obj("LabelRecess", cb, [plastic])]))
    # moulded rib grid on the right part of the top
    bm = bmesh.new()
    x0, x1, y0, y1 = 0.08, 0.50, -0.32, 0.32
    for i in range(4):
        x = x0 + (x1 - x0) * i / 3
        C.box_bm(bm, 0.025, y1 - y0, 0.035, center=(x, 0, ZC + 0.012))
    for j in range(4):
        y = y0 + (y1 - y0) * j / 3
        C.box_bm(bm, x1 - x0, 0.025, 0.035, center=((x0 + x1) / 2, y, ZC + 0.012))
    out.append(fin(C.mesh_obj("RibGrid", bm, [plastic]), bevel=0.008))
    # diagonal ribs crossing the left part (in front of the label)
    bm = bmesh.new()
    for k in range(5):
        C.box_bm(bm, 0.025, 0.04, 0.035, center=(-0.50 + 0.12 * k, -0.18, ZC + 0.008))
    C.box_bm(bm, 0.50, 0.025, 0.03, center=(-0.25, -0.12, ZC + 0.008))
    out.append(fin(C.mesh_obj("FrontRibs", bm, [plastic]), bevel=0.008))
    # clip lugs over the tray seam
    bm = bmesh.new()
    for x in (-0.35, 0.35):
        for sy in (-1, 1):
            C.box_bm(bm, 0.10, 0.03, 0.13, center=(x, sy * (W / 2 - 0.005), ZB + 0.01))
    for sx in (-1, 1):
        C.box_bm(bm, 0.03, 0.10, 0.13, center=(sx * (L / 2 - 0.005), 0.30 * (-sx), ZB + 0.01))
    out.append(fin(C.mesh_obj("Clips", bm, [plastic]), bevel=0.008))
    # pressure-compensation vent
    P = [(0.0, ZC + 0.05, 0), (0.04, ZC + 0.05, 0), (0.05, ZC + 0.04, 0), (0.05, ZC - 0.01, 0), (0.0, ZC - 0.01, 0)]
    v = C.lathe("Vent", P, [plastic], steps=48)
    v.matrix_world = Matrix.Translation((-0.42, 0.30, 0))
    out.append(fin(v, bevel=0.004, angle=40))
    return out


def connector(black, pin, lever_m):
    out = []
    x0, x1 = -0.40, 0.34
    z0, z1 = 0.03, 0.245
    depth = 0.16
    cx, w, h = (x0 + x1) / 2, x1 - x0, z1 - z0
    yb, yfr = YF + 0.03, YF - depth
    bm = bmesh.new()
    C.box_bm(bm, w, yb - yfr, h, center=(cx, (yb + yfr) / 2, (z0 + z1) / 2))
    sh = C.mesh_obj("Shroud", bm, [black])
    t = 0.022
    cuts = []
    # two cavities separated by a middle wall
    for (a, b) in ((x0 + t, cx - 0.012), (cx + 0.012, x1 - t)):
        cb = bmesh.new()
        C.box_bm(cb, b - a, depth, h - 2 * t, center=((a + b) / 2, yfr + depth / 2 - 0.05, (z0 + z1) / 2))
        cuts.append(C.mesh_obj("Cavity", cb, [black]))
    out.append(fin(sh, bevel=0.005, cutters=cuts))
    bm = bmesh.new()
    C.box_bm(bm, w + 0.06, 0.03, h + 0.04, center=(cx, YF, (z0 + z1) / 2))
    for k in range(3):
        C.box_bm(bm, 0.016, depth - 0.06, 0.028, center=(x0 + w * (0.15 + 0.32 * k), yfr + depth / 2, z1 - t - 0.012))
    out.append(fin(C.mesh_obj("Frame", bm, [black]), bevel=0.006))
    # pin fields
    floor = yfr + depth - 0.05
    bm = bmesh.new()
    pitch = 0.030
    for (a, b, rows) in ((x0 + t, cx - 0.012, 4), (cx + 0.012, x1 - t, 3)):
        ww = b - a
        nx = int((ww - 0.03) / pitch)
        for r in range(rows):
            z = (z0 + z1) / 2 + (r - (rows - 1) / 2) * 0.034
            off = pitch / 2 if r % 2 else 0
            for i in range(nx - (1 if r % 2 else 0)):
                x = (a + b) / 2 - (nx - 1) * pitch / 2 + i * pitch + off
                C.box_bm(bm, 0.009, 0.09, 0.009, center=(x, floor - 0.035, z))
    out.append(fin(C.mesh_obj("Pins", bm, [pin]), angle=40))
    # swing locking lever: two side cheeks on pivots + a grip bar across the top front
    piv_y, piv_z = yfr + 0.07, (z0 + z1) / 2
    bm = bmesh.new()
    rot = Matrix.Rotation(math.radians(-28), 4, "X")
    for sx in (-1, 1):
        xx = cx + sx * (w / 2 + 0.018)
        M = Matrix.Translation((xx, piv_y, piv_z)) @ rot
        C.box_bm(bm, 0.022, 0.07, 0.20, center=(0, 0, 0.08), matrix=M)
        C.cyl_bm(bm, 0.045, -0.011, 0.011, seg=32, matrix=M @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    M = Matrix.Translation((cx, piv_y, piv_z)) @ rot
    C.box_bm(bm, w + 0.06, 0.06, 0.03, center=(0, -0.0, 0.175), matrix=M)
    C.box_bm(bm, 0.22, 0.03, 0.05, center=(0, -0.03, 0.18), matrix=M)
    out.append(fin(C.mesh_obj("Lever", bm, [lever_m]), bevel=0.007))
    # pivot bosses on the shroud sides
    bm = bmesh.new()
    for sx in (-1, 1):
        C.cyl_bm(bm, 0.03, 0, 0.03, seg=24, matrix=Matrix.Translation((cx + sx * (w / 2 + 0.03), piv_y, piv_z))
                 @ Matrix.Rotation(sx * math.pi / 2, 4, "Y"))
    out.append(fin(C.mesh_obj("Pivots", bm, [black]), bevel=0.004))
    return out


def build():
    alu = mat_cast_alu("TcuAlu", base=0.42, rough=0.40)
    steel = C.principled("ZincSteel", (0.60, 0.61, 0.62), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    plastic = C.principled("CoverPBT", (0.026, 0.026, 0.028), rough=0.55)
    C.add_noise_bump(plastic, scale=650, strength=0.25, distance=0.0005, detail=4.0, rough_var=0.06)
    black = C.mat_black_plastic("ConnPA", rough=0.48, color=0.03)
    lever_m = C.mat_black_plastic("LeverPA", rough=0.40, color=0.045)
    pin = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    grommet = C.mat_rubber("Grommet")
    objs = base(alu, steel, grommet) + cover(plastic) + connector(black, pin, lever_m)
    im = C.label_image("TcuLabel", 1024, 760, seed=11)
    M = Matrix.Translation((-0.25, 0.10, ZC - 0.008)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    objs.append(C.label_plane("Label", C.mat_label(im), 0.42, 0.30, M))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("centralina-cambio", objs, "centralina-cambio.py",
            "automatic transmission control unit: aluminium base tray with rubber-grommet mounting tabs, "
            "black ribbed plastic cover with blank label, large multi-pin connector header with locking lever",
            az=30, el=32, lens=70, fill=0.84, **kw)
