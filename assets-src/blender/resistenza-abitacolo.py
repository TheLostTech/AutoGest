"""Blower motor resistor (resistenza ventola abitacolo) as removed from the heater box of a
small car: black plastic carrier with a mounting flange, two screw ears and a foam gasket,
the integrated connector shroud with blade pins underneath, and the white ceramic resistor
card standing in the air stream - printed thick-film resistor bands with laser-trim cuts,
silver conductor tracks, glass overglaze, a soldered thermal fuse - held by two plastic
guide posts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math, random
import numpy as np
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm. Flange in X-Y, card standing up (+Z) in the X-Z plane.
FX, FY, FT = 6.0, 3.0, 0.32
CWD, CHT, CTH = 4.4, 3.6, 0.10    # card width, height, thickness
ZC0 = FT + 0.45                   # card bottom (above flange top)


def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), matrix=None, bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center, matrix=matrix)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def lathe_at(name, prof, mats, M, steps=32):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    return C.finalize(ob, angle=40)


# ----------------------------------------------------------------- card artwork
def card_image(w=1100, h=900, seed=4):
    rnd = random.Random(seed)
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = (0.86, 0.85, 0.80)
    img[..., 3] = 1.0
    S = w / CWD

    def rect(x0, y0, x1, y1, col):        # card units, y from bottom
        a, b = int(x0 * S), int(x1 * S)
        c, d = int(y0 * S), int(y1 * S)
        img[max(0, c):min(h, d), max(0, a):min(w, b), :3] = col

    silver = (0.60, 0.60, 0.58)
    dark = (0.075, 0.075, 0.08)
    # terminal pads along the bottom edge (go into the carrier)
    pads = [0.55, 1.65, 2.75, 3.85]
    for x in pads:
        rect(x - 0.28, 0.0, x + 0.28, 0.75, silver)
    # vertical feeders up from the pads
    for x in pads:
        rect(x - 0.07, 0.7, x + 0.07, 1.05, silver)
    # bus bar across the top
    rect(0.30, 3.05, 4.10, 3.22, silver)
    # three resistor bands of different length between feeders and the bus
    bands = [(0.55, 1.05, 2.95, 0.36), (1.65, 1.05, 2.95, 0.46), (2.75, 1.05, 2.95, 0.40)]
    for (x, y0, y1, hw) in bands:
        rect(x - hw - 0.06, y0, x + hw + 0.06, y0 + 0.14, silver)
        rect(x - hw - 0.06, y1 - 0.14, x + hw + 0.06, y1, silver)
        rect(x - hw, y0 + 0.08, x + hw, y1 - 0.08, dark)
        # laser-trim cuts: short straight notches in from the band edges
        for k, side in enumerate((-1, 1)):
            yy = y0 + 0.55 + k * 0.85 + rnd.uniform(0, 0.15)
            L = hw * rnd.uniform(0.35, 0.55)
            xa = x + side * hw
            rect(min(xa, xa - side * L), yy, max(xa, xa - side * L), yy + 0.028, (0.62, 0.61, 0.57))
    # feeder from bus down to the last pad (thermal-fuse leg)
    rect(3.78, 1.95, 3.92, 3.10, silver)
    rect(3.60, 1.55, 4.10, 1.95, silver)
    # small printed code marks (no text): two rows of dots
    for i in range(7):
        rect(0.35 + i * 0.12, 3.35, 0.42 + i * 0.12, 3.42, (0.35, 0.35, 0.34))
    im = bpy.data.images.new("CardArt", w, h, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.pack()
    return im


def mat_card(im):
    m = C.principled("AluminaCard", (1, 1, 1), rough=0.32)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt, "Generated"), sep.inputs[0])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], cmb.inputs["X"])
    nt.links.new(sep.outputs["Z"], cmb.inputs["Y"])
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    tx.interpolation = "Cubic"
    tx.extension = "EXTEND"
    nt.links.new(cmb.outputs[0], tx.inputs["Vector"])
    # slight yellowing from heat in the middle
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1.5
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.8
    mr.inputs["To Max"].default_value = 0.35
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    mc.blend_type = "MULTIPLY"
    nt.links.new(mr.outputs["Result"], mc.inputs["Factor"])
    nt.links.new(tx.outputs["Color"], mc.inputs["A"])
    mc.inputs["B"].default_value = (0.85, 0.72, 0.52, 1)
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    # printed layers stand slightly proud
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.004
    bump.invert = True
    nt.links.new(tx.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def carrier(black, foam, pin):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, FX, FY, FT, center=(0, 0, FT / 2))
    for sx in (-1, 1):
        C.box_bm(bm, 1.3, 1.4, FT, center=(sx * (FX / 2 + 0.5), sx * 0.45, FT / 2))
    fl = C.mesh_obj("Flange", bm, [black])
    cuts = []
    for sx in (-1, 1):
        cb = bmesh.new()
        C.cyl_bm(cb, 0.26, -1, 1, seg=32, matrix=Matrix.Translation((sx * (FX / 2 + 0.7), sx * 0.45, 0)))
        c = C.mesh_obj("Hole", cb, [black])
        bo = C.add_boolean(fl, c)
        bo.use_self = True
        cuts.append(c)
    C.add_bevel(fl, 0.06, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35, remove=cuts))
    # foam gasket under the flange (grey open-cell)
    out.append(rbox("Gasket", foam, FX - 0.3, FY - 0.3, 0.22, center=(0, 0, -0.11), bevel=0.06))
    # socket that holds the card, stiffening ribs
    out.append(rbox("CardSocket", black, CWD + 0.5, 0.9, 0.55, center=(0, 0, FT + 0.27), bevel=0.08))
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.box_bm(bm, 0.14, 0.7, 0.35, center=(sx * 1.3, sy * 0.75, FT + 0.17))
    rb = C.mesh_obj("Ribs", bm, [black])
    C.add_bevel(rb, 0.03, segments=1, angle=30)
    out.append(C.finalize(rb, angle=35))
    # guide posts at the two card edges
    for sx in (-1, 1):
        x = sx * (CWD / 2 + 0.12)
        bm = bmesh.new()
        C.box_bm(bm, 0.36, 0.7, 2.9, center=(x, 0, FT + 1.4))
        po = C.mesh_obj("Post", bm, [black])
        cb = bmesh.new()
        C.box_bm(cb, 0.3, CTH + 0.04, 3.2, center=(x - sx * 0.14, 0, FT + 1.6))
        c = C.mesh_obj("Slot", cb, [black])
        bo = C.add_boolean(po, c)
        bo.use_self = True
        C.add_bevel(po, 0.06, segments=2, angle=30)
        out.append(C.finalize(po, angle=35, remove=[c]))
    # connector shroud below (mouth toward -Y), offset to one side
    yb = -0.2
    bm = bmesh.new()
    C.box_bm(bm, 3.6, 2.6, 1.7, center=(0.2, yb, -0.22 - 0.85))
    sh = C.mesh_obj("Shroud", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 3.2, 2.4, 1.3, center=(0.2, yb - 0.25, -0.22 - 0.85))
    c = C.mesh_obj("ShroudCut", cb, [black])
    bo = C.add_boolean(sh, c)
    bo.use_self = True
    C.add_bevel(sh, 0.07, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[c]))
    bm = bmesh.new()
    C.box_bm(bm, 0.9, 0.5, 0.2, center=(0.2, yb - 1.1, -0.22 - 0.02))
    C.box_bm(bm, 0.9, 0.16, 0.38, center=(0.2, yb - 1.38, -0.22 + 0.02))
    lt = C.mesh_obj("Latch", bm, [black])
    C.add_bevel(lt, 0.04, segments=1, angle=30)
    out.append(C.finalize(lt, angle=35))
    bm = bmesh.new()
    for i in range(4):
        C.box_bm(bm, 0.52, 1.6, 0.07, center=(-1.0 + i * 0.8, yb - 0.25, -1.07))
    pn = C.mesh_obj("Blades", bm, [pin])
    C.add_bevel(pn, 0.015, segments=1, angle=30)
    out.append(C.finalize(pn, angle=35))
    return out


def card(card_m, solder, fuse_m, edge_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CWD, CTH, CHT, center=(0, 0, ZC0 + CHT / 2 - 0.4))
    cd = C.mesh_obj("Card", bm, [card_m])
    C.add_bevel(cd, 0.02, segments=1, angle=30)
    out.append(C.finalize(cd, angle=35))
    # thermal fuse soldered across the bus/feeder on the front face
    x, z = CWD / 2 - 0.65, ZC0 - 0.4 + 2.2
    M = Matrix.Translation((x, -CTH / 2 - 0.16, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
    P = [(0.0, -0.45, 0), (0.12, -0.45, 0), (0.15, -0.40, 0), (0.15, 0.40, 0), (0.12, 0.45, 0), (0.0, 0.45, 0)]
    fz = C.lathe("Fuse", P, [fuse_m], steps=32)
    fz.matrix_world = Matrix.Translation((x, -CTH / 2 - 0.17, z)) @ Matrix.Rotation(math.radians(0), 4, "X")
    out.append(C.finalize(fz, angle=40))
    for sz in (-1, 1):
        out.append(rbox("FuseLeg", solder, 0.05, 0.16, 0.30, center=(x, -CTH / 2 - 0.09, z + sz * 0.6), bevel=0.0))
        out.append(rbox("Solder", solder, 0.24, 0.05, 0.22, center=(x, -CTH / 2 - 0.02, z + sz * 0.72), bevel=0.02))
    return out


def build():
    black = C.mat_black_plastic("PA66GF", rough=0.5, color=0.03)
    foam = C.principled("Foam", (0.09, 0.09, 0.09), rough=0.95)
    C.add_noise_bump(foam, scale=40, strength=0.5, distance=0.01)
    pin = C.principled("TinPin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.22)
    card_m = mat_card(card_image())
    solder = C.principled("Solder", (0.72, 0.72, 0.70), metallic=1.0, rough=0.18)
    fuse_m = C.principled("FuseBody", (0.30, 0.25, 0.18), metallic=0.6, rough=0.3)
    objs = carrier(black, foam, pin) + card(card_m, solder, fuse_m, black)
    C.transform_all(objs, Matrix.Rotation(math.radians(-10), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("resistenza-abitacolo", objs, "resistenza-abitacolo.py",
            "blower motor resistor: white ceramic resistor card with printed resistor tracks and thermal fuse, black plastic carrier with flange and connector",
            az=24, el=18, lens=70, fill=0.82,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
