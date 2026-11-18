"""A/C condenser (condensatore aria condizionata) as removed from a small car: wide, thin
aluminium core (flat multiport tubes proud of a fine louvred fin grid, top and bottom
side channels), round aluminium header tubes brazed on the two short sides, block-type
pipe fittings with short pipe stubs and protective caps, receiver-drier bottle strapped
to the right header with a screwed filter plug at the bottom, and small mounting tabs
with rubber grommets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

CW, CD, CH = 2.40, 0.065, 1.28   # core width (X), depth (Y), height (Z)
PITCH = 0.027                    # tube pitch
HR = 0.055                       # header tube radius
XH = CW / 2 + HR - 0.01          # header axis x
DR = 0.088                       # drier radius
XD = XH + HR + DR + 0.03         # drier axis x


# ----------------------------------------------------------------- materials
def mat_fins(name="FinGrid", pitch=0.0062):
    """fine louvred fins seen face-on (serpentine between tubes), dust mottling"""
    m = C.principled(name, (0.40, 0.40, 0.40), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
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
    wv.inputs["Scale"].default_value = 0.314 / pitch
    wv.inputs["Distortion"].default_value = 0.0
    nt.links.new(cmb.outputs[0], wv.inputs["Vector"])
    wz = nt.nodes.new("ShaderNodeTexWave")
    wz.wave_type = "BANDS"
    wz.bands_direction = "Z"
    wz.inputs["Scale"].default_value = 0.314 / 0.004
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
    cr.elements[1].color = (0.44, 0.44, 0.43, 1)
    nt.links.new(mx.outputs["Result"], ramp.inputs["Fac"])
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 3.0
    dn.inputs["Detail"].default_value = 8.0
    dm = nt.nodes.new("ShaderNodeMapRange")
    dm.inputs["From Min"].default_value = 0.45
    dm.inputs["From Max"].default_value = 0.75
    dm.inputs["To Max"].default_value = 0.4
    nt.links.new(dn.outputs["Fac"], dm.inputs["Value"])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.blend_type = "MULTIPLY"
    nt.links.new(dm.outputs["Result"], dirt.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], dirt.inputs["A"])
    dirt.inputs["B"].default_value = (0.36, 0.31, 0.25, 1)
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


def mat_alu(name, base=0.55, rough=0.32):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=500, strength=0.06, distance=0.0006, rough_var=0.08)
    return m


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=48):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def tube(name, pts, r, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def bend_path(p0, d0, d1, R, l0, l1, n=10):
    """straight l0 along d0, 90-deg-ish bend of radius R into d1, straight l1"""
    p0, d0, d1 = Vector(p0), Vector(d0).normalized(), Vector(d1).normalized()
    pts = [p0, p0 + d0 * l0]
    c = p0 + d0 * l0
    for k in range(1, n + 1):
        a = math.pi / 2 * k / n
        pts.append(c + d0 * R * math.sin(a) + d1 * R * (1 - math.cos(a)))
    pts.append(pts[-1] + d1 * l1)
    return pts


# ----------------------------------------------------------------- parts
def core(fins_m, tube_m, chan_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CW, CD - 0.006, CH, center=(0, 0, 0))
    out.append(C.mesh_obj("FinBlock", bm, [fins_m]))
    bm = bmesh.new()
    n = int(CH / PITCH)
    z0 = -(n - 1) * PITCH / 2
    for i in range(n):
        C.box_bm(bm, CW + 0.02, CD + 0.003, 0.0055, center=(0, 0, z0 + i * PITCH))
    tb = C.mesh_obj("Tubes", bm, [tube_m])
    C.add_bevel(tb, 0.001, segments=1, angle=30)
    out.append(C.finalize(tb, angle=35))
    for sz in (-1, 1):
        bm = bmesh.new()
        zc = sz * (CH / 2 + 0.012)
        C.box_bm(bm, CW, CD + 0.01, 0.024, center=(0, 0, zc))
        ch = C.mesh_obj("Channel", bm, [chan_m])
        C.add_bevel(ch, 0.004, segments=2, angle=30)
        out.append(C.finalize(ch, angle=35))
    return out


def headers(alu):
    out = []
    for sx in (-1, 1):
        z0, z1 = -CH / 2 - 0.09, CH / 2 + 0.09
        P = [(0.0, z0 - 0.012, 0), (HR - 0.012, z0 - 0.012, 0), (HR, z0, 0), (HR, z1, 0), (HR - 0.012, z1 + 0.012, 0), (0.0, z1 + 0.012, 0)]
        out.append(C.finalize(lathe_at("Header", P, [alu], (sx * XH, 0, 0), (0, 0, 1), steps=48), angle=40))
    return out


def tabs(alu, rubber):
    out = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            z = sz * (CH / 2 - 0.10)
            bm = bmesh.new()
            C.box_bm(bm, 0.14, 0.016, 0.10, center=(sx * (XH - 0.02), -0.04, z))
            tb = C.mesh_obj("Tab", bm, [alu])
            cb = bmesh.new()
            C.cyl_bm(cb, 0.024, -1, 1, seg=24, matrix=Matrix.Translation((sx * (XH - 0.05), 0, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
            cut = C.mesh_obj("TabHole", cb, [alu])
            C.add_boolean(tb, cut)
            C.add_bevel(tb, 0.004, segments=1, angle=30)
            out.append(C.finalize(tb, angle=35, remove=[cut]))
    # top locating pins with grommets
    for sx in (-1, 1):
        z = CH / 2 + 0.10
        P = [(0.0, z, 0), (0.022, z, 0), (0.022, z + 0.10, 0), (0.0, z + 0.10, 0)]
        out.append(C.finalize(lathe_at("Pin", P, [alu], (sx * XH, 0, 0), (0, 0, 1), steps=24), angle=40))
        P = [(0.022, z + 0.03, 0), (0.05, z + 0.03, 0), (0.052, z + 0.05, 0), (0.035, z + 0.06, 0), (0.035, z + 0.075, 0),
             (0.05, z + 0.08, 0), (0.05, z + 0.10, 0), (0.022, z + 0.10, 0)]
        out.append(C.finalize(lathe_at("Grommet", P, [rubber], (sx * XH, 0, 0), (0, 0, 1), steps=32), angle=40))
    return out


def fitting(alu, cap, pipe_pts, name):
    out = [tube(name + "Pipe", pipe_pts, 0.034, alu)]
    a, b = Vector(pipe_pts[-2]), Vector(pipe_pts[-1])
    d = (b - a).normalized()
    M = Matrix.Translation(b) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    C.box_bm(bm, 0.15, 0.085, 0.09, matrix=M @ Matrix.Translation((0.025, 0, 0.0)))
    bk = C.mesh_obj(name + "Block", bm, [alu])
    C.add_bevel(bk, 0.008, segments=2, angle=30)
    out.append(C.finalize(bk, angle=35))
    # protective plastic cap on the port spigot
    P = [(0.0, 0.045, 0), (0.045, 0.045, 0), (0.05, 0.06, 0), (0.05, 0.13, 0), (0.04, 0.14, 0), (0.0, 0.14, 0)]
    cp = C.lathe(name + "Cap", P, [cap], steps=32)
    cp.matrix_world = M
    out.append(C.finalize(cp, angle=40))
    return out


def drier(alu, steel, black):
    out = []
    z0, z1 = -0.52, 0.42
    P = [(0.0, z0, 0), (DR - 0.012, z0, 0), (DR, z0 + 0.012, 0), (DR, z1 - 0.03, 0), (DR - 0.02, z1, 0),
         (DR - 0.05, z1 + 0.02, 0), (0.0, z1 + 0.025, 0)]
    out.append(C.finalize(lathe_at("Drier", P, [alu], (XD, 0.0, 0), (0, 0, 1), steps=64), angle=40))
    # screwed filter plug at the bottom (hex socket plug + o-ring)
    P = [(0.0, z0 - 0.03, 0), (DR - 0.02, z0 - 0.03, 0), (DR - 0.02, z0, 0), (0.0, z0, 0)]
    out.append(C.finalize(lathe_at("Plug", P, [steel], (XD, 0.0, 0), (0, 0, 1), steps=48), angle=40))
    P = [(DR - 0.03, z0 - 0.008, 0), (DR - 0.012, z0 - 0.008, 0), (DR - 0.012, z0 + 0.002, 0), (DR - 0.03, z0 + 0.002, 0)]
    out.append(C.finalize(lathe_at("ORing", P, [black], (XD, 0.0, 0), (0, 0, 1), steps=48), angle=40))
    # transfer blocks to the header
    for z in (0.25, -0.30):
        bm = bmesh.new()
        C.box_bm(bm, XD - XH, 0.06, 0.08, center=((XD + XH) / 2, 0, z))
        bk = C.mesh_obj("Bridge", bm, [alu])
        C.add_bevel(bk, 0.008, segments=2, angle=30)
        out.append(C.finalize(bk, angle=35))
    # clamp strap with screw
    P = [(DR, -0.02, 0), (DR + 0.006, -0.02, 0), (DR + 0.006, 0.02, 0), (DR, 0.02, 0)]
    out.append(C.finalize(lathe_at("Strap", P, [steel], (XD, 0.0, 0), (0, 0, 1), steps=64), angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.03, 0.05, 0.05, center=(XD - DR - 0.01, -0.05, 0.0))
    C.cyl_bm(bm, 0.018, 0, 0.04, seg=6, matrix=Matrix.Translation((XD - DR - 0.01, -0.075, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    sc = C.mesh_obj("StrapScrew", bm, [steel])
    C.add_bevel(sc, 0.004, segments=1, angle=30)
    out.append(C.finalize(sc, angle=35))
    return out


def build():
    fins = mat_fins()
    tube_m = mat_alu("TubeAlu", 0.52, 0.30)
    chan = mat_alu("ChannelAlu", 0.42, 0.36)
    alu = mat_alu("HeaderAlu", 0.60, 0.30)
    steel = C.principled("ZincSteel", (0.62, 0.60, 0.55), metallic=1.0, rough=0.3)
    black = C.mat_rubber("ORing")
    cap = C.mat_black_plastic("CapPE", rough=0.5, color=0.03)
    objs = core(fins, tube_m, chan) + headers(alu) + tabs(alu, black)
    # inlet: top of the left header, stub going back and up
    pts = bend_path((-XH, 0.0, CH / 2 - 0.05), (-1, 0, 0), (-0.45, -0.8, 0.25), 0.07, 0.05, 0.10)
    objs += fitting(alu, cap, [Vector((-XH + 0.03, 0, CH / 2 - 0.05))] + pts, "Inlet")
    # outlet: bottom of the left header, stub going back and down
    pts = bend_path((-XH, 0.0, -CH / 2 + 0.06), (-1, 0, 0), (-0.45, -0.8, -0.2), 0.07, 0.05, 0.08)
    objs += fitting(alu, cap, [Vector((-XH + 0.03, 0, -CH / 2 + 0.06))] + pts, "Outlet")
    objs += drier(alu, steel, black)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("condensatore", objs, "condensatore.py",
            "A/C condenser: thin aluminium fin-and-tube core, round side header tubes, pipe fittings with caps, receiver-drier bottle",
            az=28, el=16, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
