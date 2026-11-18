"""Engine cooling radiator (radiatore), cross-flow type as removed from a car: wide thin
aluminium core (flat tubes proud of a fine louvred fin grid, top and bottom side channels),
crimped aluminium header plates, black glass-filled nylon end tanks on the two short
sides with moulded ribs, inlet and outlet hose necks with retention beads, mounting
pegs with rubber grommets top and bottom, and a plastic drain plug."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

CW, CD, CH = 2.20, 0.10, 1.00   # core width (X), depth (Y), height (Z)
TW, TD, TH = 0.17, 0.20, 1.18   # tank width, depth, height
XT = CW / 2 + 0.025             # inner face of tank
PITCH = 0.034                   # tube pitch


# ----------------------------------------------------------------- materials
def mat_fins(name="FinGrid", pitch=0.0075):
    """Fine fin grid seen face-on: thin bright fin edges with dark gaps in between,
    a little dust and corrosion, plus bump so the grid catches the light."""
    m = C.principled(name, (0.40, 0.40, 0.40), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    # serpentine fins: shift x by a triangle wave of z (period = tube pitch) so the
    # folds zig-zag from tube to tube instead of forming a square grid
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    pp = nt.nodes.new("ShaderNodeMath")
    pp.operation = "PINGPONG"
    pp.inputs[1].default_value = PITCH / 2
    nt.links.new(sep.outputs["Z"], pp.inputs[0])
    amp = nt.nodes.new("ShaderNodeMath")
    amp.operation = "MULTIPLY_ADD"
    amp.inputs[1].default_value = 0.9 * pitch / (PITCH / 2)
    nt.links.new(pp.outputs[0], amp.inputs[0])
    nt.links.new(sep.outputs["X"], amp.inputs[2])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(amp.outputs[0], cmb.inputs["X"])
    nt.links.new(sep.outputs["Y"], cmb.inputs["Y"])
    nt.links.new(sep.outputs["Z"], cmb.inputs["Z"])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.wave_profile = "SIN"
    wv.inputs["Scale"].default_value = 0.314 / pitch
    wv.inputs["Distortion"].default_value = 0.0
    nt.links.new(cmb.outputs[0], wv.inputs["Vector"])
    # louvre wobble so the fins are not perfectly straight lines
    wz = nt.nodes.new("ShaderNodeTexWave")
    wz.wave_type = "BANDS"
    wz.bands_direction = "Z"
    wz.inputs["Scale"].default_value = 0.314 / 0.0045
    nt.links.new(co, wz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.inputs["Factor"].default_value = 0.18
    nt.links.new(wv.outputs["Fac"], mx.inputs["A"])
    nt.links.new(wz.outputs["Fac"], mx.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.38
    cr.elements[0].color = (0.006, 0.006, 0.006, 1)
    cr.elements[1].position = 0.72
    cr.elements[1].color = (0.42, 0.42, 0.41, 1)
    nt.links.new(mx.outputs["Result"], ramp.inputs["Fac"])
    # dust / road grime mottling
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 3.5
    dn.inputs["Detail"].default_value = 8.0
    dm = nt.nodes.new("ShaderNodeMapRange")
    dm.inputs["From Min"].default_value = 0.45
    dm.inputs["From Max"].default_value = 0.75
    dm.inputs["To Max"].default_value = 0.35
    nt.links.new(dn.outputs["Fac"], dm.inputs["Value"])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.blend_type = "MULTIPLY"
    nt.links.new(dm.outputs["Result"], dirt.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], dirt.inputs["A"])
    dirt.inputs["B"].default_value = (0.35, 0.30, 0.24, 1)
    nt.links.new(dirt.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.75
    rr.inputs["To Max"].default_value = 0.35
    nt.links.new(mx.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(mx.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_alu(name, base=0.55, rough=0.32, wear=0.0):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=500, strength=0.06, distance=0.0006, rough_var=0.08)
    return m


def mat_nylon(name="PA66GF"):
    """Glass-filled black nylon tank: slightly grey, satin, with a fibre-ish grain."""
    m = C.principled(name, (0.028, 0.028, 0.03), rough=0.55)
    C.add_noise_bump(m, scale=650, strength=0.10, distance=0.0006, rough_var=0.08)
    return m


# ----------------------------------------------------------------- core
def core(fins_m, tube_m, chan_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CW, CD - 0.006, CH, center=(0, 0, 0))
    fb = C.mesh_obj("FinBlock", bm, [fins_m])
    out.append(fb)
    bm = bmesh.new()
    n = int(CH / PITCH)
    z0 = -(n - 1) * PITCH / 2
    for i in range(n):
        C.box_bm(bm, CW, CD + 0.004, 0.0085, center=(0, 0, z0 + i * PITCH))
    tb = C.mesh_obj("Tubes", bm, [tube_m])
    C.add_bevel(tb, 0.0015, segments=1, angle=30)
    out.append(C.finalize(tb, angle=35))
    # top / bottom U-channels with stamped stiffening ribs
    for sz in (-1, 1):
        bm = bmesh.new()
        zc = sz * (CH / 2 + 0.014)
        C.box_bm(bm, CW, CD + 0.012, 0.028, center=(0, 0, zc))
        ch = C.mesh_obj("Channel", bm, [chan_m])
        C.add_bevel(ch, 0.004, segments=2, angle=30)
        out.append(C.finalize(ch, angle=35))
        bm = bmesh.new()
        for k in range(11):
            x = -CW / 2 + 0.12 + k * (CW - 0.24) / 10
            C.box_bm(bm, 0.07, 0.006, 0.012, center=(x, -(CD + 0.012) / 2 - 0.001, zc))
        em = C.mesh_obj("ChannelRibs", bm, [chan_m])
        C.add_bevel(em, 0.003, segments=1, angle=30)
        out.append(C.finalize(em, angle=35))
    return out


# ----------------------------------------------------------------- tanks
def tank(sx, nylon, alu):
    """sx = -1 left, +1 right"""
    out = []
    xc = sx * (XT + TW / 2)
    # crimped aluminium header plate
    bm = bmesh.new()
    C.box_bm(bm, 0.03, TD + 0.03, TH + 0.04, center=(sx * (XT - 0.004), 0, 0))
    hp = C.mesh_obj("Header", bm, [alu])
    C.add_bevel(hp, 0.008, segments=2, angle=30)
    out.append(C.finalize(hp, angle=35))
    # crimp tabs folded over the tank foot
    bm = bmesh.new()
    nt = 27
    for k in range(nt):
        z = -TH / 2 + 0.04 + k * (TH - 0.08) / (nt - 1)
        for sy in (-1, 1):
            C.box_bm(bm, 0.03, 0.006, 0.022, center=(sx * (XT + 0.018), sy * (TD / 2 + 0.004), z))
    ct = C.mesh_obj("CrimpTabs", bm, [alu])
    C.add_bevel(ct, 0.003, segments=1, angle=30)
    out.append(C.finalize(ct, angle=35))
    # tank body: foot flange + rounded shell
    bm = bmesh.new()
    C.box_bm(bm, 0.045, TD + 0.006, TH + 0.01, center=(sx * (XT + 0.025), 0, 0))
    ft = C.mesh_obj("TankFoot", bm, [nylon])
    C.add_bevel(ft, 0.008, segments=2, angle=30)
    out.append(C.finalize(ft, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, TW, TD - 0.02, TH - 0.03, center=(xc, 0, 0))
    sh = C.mesh_obj("TankShell", bm, [nylon])
    C.add_bevel(sh, 0.05, segments=5, angle=30)
    out.append(C.finalize(sh, angle=35))
    # moulded ribs: horizontal on the outer face, vertical stiffeners on the front face
    bm = bmesh.new()
    for k in range(7):
        z = -TH / 2 + 0.12 + k * (TH - 0.24) / 6
        C.box_bm(bm, 0.018, TD - 0.09, 0.016, center=(sx * (XT + TW + 0.002), 0, z))
    for k in range(2):
        x = sx * (XT + 0.06 + k * 0.06)
        C.box_bm(bm, 0.016, 0.014, TH - 0.16, center=(x, -(TD - 0.02) / 2 - 0.004, 0))
    rb = C.mesh_obj("TankRibs", bm, [nylon])
    C.add_bevel(rb, 0.006, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # mounting pegs with rubber grommets (top and bottom)
    for sz in (-1, 1):
        zt = sz * (TH / 2 - 0.03)
        flip = Matrix.Identity(4) if sz > 0 else Matrix.Rotation(math.pi, 4, "X")
        T = Matrix.Translation((xc, 0, 0)) @ flip
        peg = C.lathe("Peg", [(0.0, TH / 2 - 0.03, 0), (0.05, TH / 2 - 0.03, 0), (0.042, TH / 2 + 0.03, 0),
                               (0.03, TH / 2 + 0.04, 0), (0.03, TH / 2 + 0.13, 0), (0.024, TH / 2 + 0.14, 0), (0.0, TH / 2 + 0.14, 0)], [nylon], steps=40)
        peg.matrix_world = T
        out.append(C.finalize(peg, angle=40))
        z = TH / 2 + 0.05
        gr = C.lathe("Grommet", [(0.03, z, 0), (0.07, z, 0), (0.074, z + 0.012, 0), (0.07, z + 0.024, 0), (0.05, z + 0.03, 0),
                                  (0.05, z + 0.055, 0), (0.066, z + 0.06, 0), (0.07, z + 0.072, 0), (0.066, z + 0.084, 0),
                                  (0.03, z + 0.086, 0)], [rubber_m], steps=48)
        gr.matrix_world = T
        out.append(C.finalize(gr, angle=40))
    return out


def neck(name, nylon, origin, direction, r=0.058, length=0.24):
    """Hollow hose neck along local Z, with base fillet and end retention bead."""
    ri = r - 0.012
    P = [(ri, -0.02, 0), (r + 0.03, -0.02, 0), (r + 0.03, 0.0, 0), (r + 0.008, 0.02, 0), (r, 0.04, 0),
         (r, length - 0.05, 0), (r + 0.010, length - 0.035, 0), (r + 0.010, length - 0.02, 0), (r, length - 0.006, 0),
         (r - 0.004, length, 0), (ri, length, 0)]
    ob = C.lathe(name, P, [nylon], steps=64)
    d = Vector(direction).normalized()
    R = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    ob.matrix_world = Matrix.Translation(origin) @ R
    C.add_bevel(ob, 0.003, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def drain_plug(plug_m, nylon):
    out = []
    x = XT + TW * 0.55
    z = -TH / 2 + 0.06
    # boss on the front face of the right tank, plug pointing -Y
    R = Matrix.Rotation(math.radians(90), 4, "X")   # local Z -> -Y
    T = Matrix.Translation((x, -(TD - 0.02) / 2 + 0.02, z)) @ R
    boss = C.lathe("DrainBoss", [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.05, 0.045, 0), (0.044, 0.05, 0), (0.0, 0.05, 0)], [nylon], steps=40)
    boss.matrix_world = T
    out.append(C.finalize(boss, angle=40))
    pl = C.lathe("DrainPlug", [(0.0, 0.05, 0), (0.042, 0.05, 0), (0.042, 0.065, 0), (0.03, 0.07, 0), (0.0, 0.07, 0)], [plug_m], steps=40)
    pl.matrix_world = T
    out.append(C.finalize(pl, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.075, 0.02, 0.05, center=(0, 0, 0.095))
    wing = C.mesh_obj("DrainWing", bm, [plug_m])
    wing.matrix_world = T
    C.add_bevel(wing, 0.006, segments=2, angle=30)
    out.append(C.finalize(wing, angle=35))
    return out


rubber_m = None


def build():
    global rubber_m
    fins = mat_fins()
    tube = mat_alu("TubeAlu", 0.50, 0.30)
    chan = mat_alu("ChannelAlu", 0.40, 0.36)
    hdr = mat_alu("HeaderAlu", 0.30, 0.42)
    nylon = mat_nylon()
    rubber_m = C.mat_rubber("Grommet")
    plug = C.principled("DrainPlugPA", (0.30, 0.31, 0.32), rough=0.45)
    C.add_noise_bump(plug, scale=700, strength=0.05, distance=0.0005)
    objs = core(fins, tube, chan)
    objs += tank(-1, nylon, hdr) + tank(1, nylon, hdr)
    xl = -(XT + TW)
    objs.append(neck("InletNeck", nylon, (xl + 0.03, 0.0, 0.36), (-1, -0.15, 0.25)))
    objs.append(neck("OutletNeck", nylon, (-xl - 0.03, 0.0, -0.34), (1, -0.15, -0.12), r=0.052))
    objs += drain_plug(plug, nylon)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("radiatore", objs, "radiatore.py",
            "engine cooling radiator: aluminium fin-and-tube core, black plastic end tanks, inlet and outlet hose necks, rubber-grommet mounting pegs, drain plug",
            az=28, el=16, lens=70, fill=0.86)
