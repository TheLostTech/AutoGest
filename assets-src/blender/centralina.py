"""Engine ECU (centralina motore): flat die-cast aluminium housing in two halves with a
finned cover held by Torx screws, four mounting tabs with steel-sleeved holes, two black
multi-pin connector headers (visible pin rows, coding ribs, locking ramp) on the front
long side, a breather membrane and a blank adhesive label."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

L, W = 1.50, 1.00          # footprint (X long side, Y depth)
ZB, ZF, ZC = 0.13, 0.155, 0.25   # base top, seam flange top, cover top
YF = -W / 2                # front long side (connectors)


# ----------------------------------------------------------------- materials
def mat_cast_alu(name, base=0.50, rough=0.45, grain=520.0, wear=0.35):
    """Die-cast aluminium: mottled tone, fine sand-cast grain, brighter worn edges."""
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
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.06
    rr.inputs["To Max"].default_value = rough - 0.06
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    rmix = nt.nodes.new("ShaderNodeMix")
    nt.links.new(wmul.outputs[0], rmix.inputs["Factor"])
    nt.links.new(rr.outputs["Result"], rmix.inputs["A"])
    rmix.inputs["B"].default_value = 0.22
    nt.links.new(rmix.outputs["Result"], b.inputs["Roughness"])
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


# ----------------------------------------------------------------- housing
def base(alu, gasket):
    bm = bmesh.new()
    C.box_bm(bm, L, W, ZB, center=(0, 0, ZB / 2))
    ob = C.mesh_obj("Base", bm, [alu])
    C.add_bevel(ob, 0.018, segments=3, angle=30)
    out = [C.finalize(ob, angle=35)]
    # seam flange between the halves (slightly proud)
    bm = bmesh.new()
    C.box_bm(bm, L + 0.03, W + 0.03, ZF - ZB + 0.01, center=(0, 0, (ZB + ZF) / 2 - 0.005))
    fl = C.mesh_obj("Flange", bm, [alu])
    C.add_bevel(fl, 0.008, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35))
    # dark sealing bead squeezed out along the seam
    bm = bmesh.new()
    C.box_bm(bm, L + 0.014, W + 0.014, 0.012, center=(0, 0, ZB - 0.011))
    gk = C.mesh_obj("Gasket", bm, [gasket])
    C.add_bevel(gk, 0.005, segments=2, angle=30)
    out.append(C.finalize(gk, angle=35))
    # stiffening ribs on the short ends of the base
    bm = bmesh.new()
    for sx in (-1, 1):
        for y in (-0.30, -0.10, 0.10, 0.30):
            C.box_bm(bm, 0.03, 0.035, ZB - 0.03, center=(sx * (L / 2 + 0.012), y, (ZB - 0.03) / 2 + 0.015))
    rb = C.mesh_obj("BaseRibs", bm, [alu])
    C.add_bevel(rb, 0.008, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    return out


def cover(alu):
    bm = bmesh.new()
    C.box_bm(bm, L - 0.01, W - 0.01, ZC - ZF + 0.01, center=(0, 0, (ZF + ZC) / 2 - 0.005))
    ob = C.mesh_obj("Cover", bm, [alu])
    C.add_bevel(ob, 0.03, segments=3, angle=30)
    out = [C.finalize(ob, angle=35)]
    # cooling fins over the right two thirds (running front-to-back)
    bm = bmesh.new()
    n = 15
    x0, x1 = -0.12, 0.62
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        C.box_bm(bm, 0.022, W - 0.22, 0.075, center=(x, 0.0, ZC + 0.0375 - 0.004))
    fins = C.mesh_obj("Fins", bm, [alu])
    C.add_bevel(fins, 0.009, segments=2, angle=30)
    out.append(C.finalize(fins, angle=35))
    # raised pad for the label on the left third
    bm = bmesh.new()
    C.box_bm(bm, 0.50, W - 0.22, 0.03, center=(-0.47, 0.0, ZC + 0.011))
    pad = C.mesh_obj("Pad", bm, [alu])
    C.add_bevel(pad, 0.012, segments=2, angle=30)
    out.append(C.finalize(pad, angle=35))
    return out


def screws(steel):
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (L / 2 - 0.07), sy * (W / 2 - 0.07)
            P = [(0.0, ZC - 0.01, 0), (0.042, ZC - 0.01, 0), (0.042, ZC + 0.012, 0), (0.036, ZC + 0.02, 0), (0.0, ZC + 0.02, 0)]
            hd = C.lathe("Screw", P, [steel], steps=40)
            hd.matrix_world = Matrix.Translation((x, y, 0))
            # torx-ish recess
            bm = bmesh.new()
            C.cyl_bm(bm, 0.017, ZC + 0.008, ZC + 0.04, seg=6, matrix=Matrix.Translation((x, y, 0)))
            cut = C.mesh_obj("ScrewCut", bm, [steel])
            C.add_boolean(hd, cut)
            C.add_bevel(hd, 0.003, segments=1, angle=40)
            out.append(C.finalize(hd, angle=40, remove=[cut]))
    return out


def tabs(alu, steel):
    out = []
    for sx in (-1, 1):
        for y in (-0.30, 0.30):
            bm = bmesh.new()
            cx = sx * (L / 2 + 0.10)
            C.box_bm(bm, 0.26, 0.20, 0.035, center=(cx - sx * 0.03, y, 0.0175))
            # gusset up the body wall
            C.box_bm(bm, 0.05, 0.04, 0.09, center=(sx * (L / 2 + 0.02), y, 0.06))
            tb = C.mesh_obj("Tab", bm, [alu])
            cb = bmesh.new()
            C.cyl_bm(cb, 0.045, -0.1, 0.2, seg=40, matrix=Matrix.Translation((sx * (L / 2 + 0.135), y, 0)))
            cut = C.mesh_obj("TabHole", cb, [alu])
            C.add_boolean(tb, cut)
            C.add_bevel(tb, 0.008, segments=2, angle=30)
            out.append(C.finalize(tb, angle=35, remove=[cut]))
            sl = C.lathe("Sleeve", [(0.030, -0.004, 0), (0.046, -0.004, 0), (0.046, 0.042, 0), (0.030, 0.042, 0)], [steel], steps=40)
            sl.matrix_world = Matrix.Translation((sx * (L / 2 + 0.135), y, 0))
            C.add_bevel(sl, 0.003, segments=1, angle=40)
            out.append(C.finalize(sl, angle=40))
    return out


# ----------------------------------------------------------------- connectors
def header(black, pin, x0, x1, rows, z0=0.025, z1=0.235, depth=0.17, seed=0):
    """Black shroud open toward -Y with rows of pins inside and a locking ramp on top."""
    out = []
    cx = (x0 + x1) / 2
    w = x1 - x0
    h = z1 - z0
    yb = YF + 0.02            # back plane (inside the housing wall)
    yfr = YF - depth          # mouth of the shroud
    bm = bmesh.new()
    C.box_bm(bm, w, yb - yfr, h, center=(cx, (yb + yfr) / 2, (z0 + z1) / 2))
    sh = C.mesh_obj("Shroud", bm, [black])
    cb = bmesh.new()
    t = 0.022
    C.box_bm(cb, w - 2 * t, depth, h - 2 * t, center=(cx, yfr + depth / 2 - 0.05 - 0.0, (z0 + z1) / 2))
    cut = C.mesh_obj("ShroudCut", cb, [black])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    # coding ribs moulded on the inner walls of the cavity
    bm = bmesh.new()
    for k in range(3):
        xk = x0 + w * (0.2 + 0.3 * k)
        C.box_bm(bm, 0.018, depth - 0.06, 0.03, center=(xk, yfr + depth / 2 - 0.0, z1 - t - 0.012))
    C.box_bm(bm, 0.018, depth - 0.06, 0.03, center=(x0 + w * 0.35, yfr + depth / 2 - 0.0, z0 + t + 0.012))
    cr = C.mesh_obj("CodingRibs", bm, [black])
    C.add_bevel(cr, 0.003, segments=1, angle=30)
    out.append(C.finalize(cr, angle=35))
    # mounting frame against the housing
    bm = bmesh.new()
    C.box_bm(bm, w + 0.06, 0.03, h + 0.0, center=(cx, YF + 0.0, (z0 + z1) / 2))
    fr = C.mesh_obj("Frame", bm, [black])
    C.add_bevel(fr, 0.008, segments=2, angle=30)
    out.append(C.finalize(fr, angle=35))
    # locking ramp + guide ribs on top of the shroud
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 0.05, 0.022, center=(cx, yfr + 0.05, z1 + 0.009))
    C.box_bm(bm, 0.11, 0.025, 0.035, center=(cx, yfr + 0.085, z1 + 0.015))
    for sxg in (-1, 1):
        C.box_bm(bm, 0.018, depth - 0.02, 0.022, center=(cx + sxg * (w / 2 - 0.05), yfr + depth / 2 + 0.01, z1 + 0.009))
    rp = C.mesh_obj("Ramp", bm, [black])
    C.add_bevel(rp, 0.004, segments=1, angle=30)
    out.append(C.finalize(rp, angle=35))
    # pin field: rows of square pins sticking out of the cavity floor
    floor = yfr + depth - 0.05
    bm = bmesh.new()
    pitch = 0.032
    zs = [z0 + h / 2 + (r - (rows - 1) / 2) * 0.036 for r in range(rows)]
    for r, z in enumerate(zs):
        nx = int((w - 2 * t - 0.03) / pitch)
        off = (pitch / 2) if r % 2 else 0.0
        for i in range(nx - (1 if r % 2 else 0)):
            x = cx - (nx - 1) * pitch / 2 + i * pitch + off
            C.box_bm(bm, 0.010, 0.10, 0.010, center=(x, floor - 0.04, z))
    pn = C.mesh_obj("Pins", bm, [pin])
    out.append(C.finalize(pn, angle=40))
    return out


def build():
    alu_b = mat_cast_alu("CastAluBase", base=0.30, rough=0.38)
    alu_c = mat_cast_alu("CastAluCover", base=0.40, rough=0.40, grain=700)
    steel = C.principled("ZincSteel", (0.58, 0.59, 0.61), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    black = C.mat_black_plastic("PBT", rough=0.52, color=0.03)
    pin = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    gasket = C.mat_rubber("Gasket")
    objs = base(alu_b, gasket) + cover(alu_c) + screws(steel) + tabs(alu_b, steel)
    objs += header(black, pin, -0.62, 0.12, rows=3)
    objs += header(black, pin, 0.24, 0.62, rows=2)
    # breather membrane (round grey cap) next to the fins
    P = [(0.0, ZC + 0.058, 0), (0.045, ZC + 0.058, 0), (0.055, ZC + 0.045, 0), (0.055, ZC + 0.015, 0), (0.0, ZC + 0.015, 0)]
    vt = C.lathe("Vent", P, [black], steps=48)
    vt.matrix_world = Matrix.Translation((-0.47, 0.33, 0))
    C.add_bevel(vt, 0.004, segments=2, angle=30)
    objs.append(C.finalize(vt, angle=40))
    im = C.label_image("EcuLabel", 1024, 640, seed=7)
    M = Matrix.Translation((-0.47, -0.06, ZC + 0.0265)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    objs.append(C.label_plane("Label", C.mat_label(im), 0.42, 0.50, M))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("centralina", objs, "centralina.py",
            "engine ECU: die-cast aluminium housing with finned cover, mounting tabs, two black multi-pin connector headers, blank label",
            az=32, el=30, lens=70, fill=0.84)
