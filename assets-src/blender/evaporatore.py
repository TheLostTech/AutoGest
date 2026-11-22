"""A/C evaporator (evaporatore climatizzatore) as removed from the HVAC box of a small car:
compact but thick brazed aluminium plate-fin core (vertical flat plates proud of a fine
louvred fin grid), twin ribbed plate-cup tanks along the top and bottom, side end plates,
and on the left end two short refrigerant pipes running into a pipe block with the
block-type thermostatic expansion valve bolted on (power-element dome on top, two bulkhead
ports with dust caps, centre stud), plus the clip-on fin temperature probe with its lead."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 10 cm. Core in the X-Z plane, front face toward -Y.
CW, CD, CH = 2.30, 0.62, 1.80
TP = 0.10                       # plate (tube) pitch along X
TR = 0.15                       # tank radius
ZT = CH / 2 + 0.11              # tank axis height


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=48, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), matrix=None, bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center, matrix=matrix)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=6):
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


# ----------------------------------------------------------------- materials
def mat_fins(name="FinGrid", pitch=0.0145):
    """louvred serpentine fins between VERTICAL plates (pattern axes swapped: plates
    run along Z, fins zig-zag across X)"""
    m = C.principled(name, (0.40, 0.40, 0.40), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co0 = C._coord(nt)
    s0 = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co0, s0.inputs[0])
    sw = nt.nodes.new("ShaderNodeCombineXYZ")          # (x,y,z) -> (z,y,x)
    nt.links.new(s0.outputs["Z"], sw.inputs["X"])
    nt.links.new(s0.outputs["Y"], sw.inputs["Y"])
    nt.links.new(s0.outputs["X"], sw.inputs["Z"])
    co = sw.outputs[0]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    pp = nt.nodes.new("ShaderNodeMath")
    pp.operation = "PINGPONG"
    pp.inputs[1].default_value = TP / 2
    nt.links.new(sep.outputs["Z"], pp.inputs[0])
    amp = nt.nodes.new("ShaderNodeMath")
    amp.operation = "MULTIPLY_ADD"
    amp.inputs[1].default_value = 0.9 * pitch / (TP / 2)
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
    wz.inputs["Scale"].default_value = 0.314 / 0.008
    nt.links.new(co, wz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.inputs["Factor"].default_value = 0.18
    nt.links.new(wv.outputs["Fac"], mx.inputs["A"])
    nt.links.new(wz.outputs["Fac"], mx.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.38
    cr.elements[0].color = (0.008, 0.008, 0.008, 1)
    cr.elements[1].position = 0.72
    cr.elements[1].color = (0.44, 0.44, 0.43, 1)
    nt.links.new(mx.outputs["Result"], ramp.inputs["Fac"])
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co0, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 3.0
    dn.inputs["Detail"].default_value = 8.0
    dm = nt.nodes.new("ShaderNodeMapRange")
    dm.inputs["From Min"].default_value = 0.45
    dm.inputs["From Max"].default_value = 0.75
    dm.inputs["To Max"].default_value = 0.45
    nt.links.new(dn.outputs["Fac"], dm.inputs["Value"])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.blend_type = "MULTIPLY"
    nt.links.new(dm.outputs["Result"], dirt.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], dirt.inputs["A"])
    dirt.inputs["B"].default_value = (0.40, 0.36, 0.30, 1)
    nt.links.new(dirt.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.75
    rr.inputs["To Max"].default_value = 0.35
    nt.links.new(mx.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.003
    nt.links.new(mx.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_alu(name, base=0.55, rough=0.32):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=300, strength=0.06, distance=0.0008, rough_var=0.08)
    return m


# ----------------------------------------------------------------- core + tanks
def core(fins_m, plate_m, side_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CW, CD - 0.02, CH, center=(0, 0, 0))
    out.append(C.mesh_obj("FinBlock", bm, [fins_m]))
    bm = bmesh.new()
    n = int(CW / TP)
    x0 = -(n - 1) * TP / 2
    for i in range(n):
        C.box_bm(bm, 0.02, CD + 0.004, CH + 0.04, center=(x0 + i * TP, 0, 0))
    pl = C.mesh_obj("Plates", bm, [plate_m])
    C.add_bevel(pl, 0.006, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    for sx in (-1, 1):
        out.append(rbox("EndPlate", side_m, 0.04, CD + 0.02, CH + 0.06, center=(sx * (CW / 2 + 0.02), 0, 0), bevel=0.01))
        bm = bmesh.new()
        for k in range(4):
            z = -CH / 2 + 0.25 + k * (CH - 0.5) / 3
            C.box_bm(bm, 0.014, CD - 0.16, 0.14, center=(sx * (CW / 2 + 0.045), 0, z))
        bd = C.mesh_obj("EndBeads", bm, [side_m])
        C.add_bevel(bd, 0.006, segments=2, angle=30)
        out.append(C.finalize(bd, angle=35))
    return out


def tanks(tank_m):
    out = []
    L = CW + 0.06

    def cups(r, z, t):
        if r < TR - 0.03:
            return r
        u = (z + L / 2) / TP
        return r - 0.011 * (math.cos(math.pi * u) ** 16)

    for sz in (-1, 1):
        for sy in (-1, 1):
            P = [(0.0, -L / 2, 0), (TR - 0.05, -L / 2, 0), (TR - 0.02, -L / 2 + 0.02, 0)]
            n = 90
            for i in range(n + 1):
                P.append((TR, -L / 2 + 0.04 + (L - 0.08) * i / n, 0))
            P += [(TR - 0.02, L / 2 - 0.02, 0), (TR - 0.05, L / 2, 0), (0.0, L / 2, 0)]
            out.append(lathe_at("Tank", P, [tank_m], origin=(0, sy * (CD / 2 - TR + 0.02), sz * ZT), axis=(1, 0, 0),
                                steps=40, mod=cups))
        # web between the twin tanks
        out.append(rbox("TankWeb", tank_m, L - 0.04, CD - 2 * TR + 0.12, 0.16, center=(0, 0, sz * (ZT - 0.02)), bevel=0.02))
    return out


# ----------------------------------------------------------------- valve + pipes
def valve(pipe_m, blk_m, txv_m, head_m, cap_m, steel, oring):
    out = []
    xl = -(CW / 2 + 0.03)
    yb, ys = -(CD / 2 - TR + 0.02), (CD / 2 - TR + 0.02)
    # pipe block on the left of the top tanks, valve bolted on its outer face
    xv = xl - 0.62
    zv = ZT - 0.02
    for i, (y, r) in enumerate(((yb, 0.085), (ys, 0.06))):
        ctrl = [(xl + 0.05, y, ZT), (xl - 0.12, y, ZT), (xl - 0.30, y * 0.6, zv), (xv + 0.10, y * 0.35, zv)]
        out.append(tube("Pipe%d" % i, smooth_path(ctrl, 10), r, pipe_m))
        out.append(lathe_at("Collar", [(r - 0.01, 0.0, 0), (r + 0.03, 0.0, 0), (r + 0.03, 0.025, 0), (r, 0.05, 0), (r - 0.01, 0.05, 0)],
                            [pipe_m], origin=(xl + 0.01, y, ZT), axis=(-1, 0, 0), steps=40))
    # evaporator-side pipe block
    out.append(rbox("PipeBlock", blk_m, 0.16, 0.48, 0.30, center=(xv + 0.04, 0, zv), bevel=0.02))
    # expansion valve body (aluminium block, slightly taller)
    vx = xv - 0.20
    out.append(rbox("TXV", txv_m, 0.24, 0.42, 0.56, center=(vx, 0, zv + 0.06), bevel=0.018))
    # power-element dome on top
    zt = zv + 0.34
    P = [(0.0, zt - 0.01, 0), (0.15, zt - 0.01, 0), (0.15, zt + 0.02, 0), (0.16, zt + 0.03, 0), (0.16, zt + 0.05, 0),
         (0.14, zt + 0.06, 0), (0.11, zt + 0.11, 0), (0.05, zt + 0.135, 0), (0.0, zt + 0.14, 0)]
    out.append(lathe_at("Dome", P, [head_m], origin=(vx, 0, 0), steps=64, bevel=0.003))
    # bulkhead ports on the outer face (two spigots + dust caps), centre stud
    for (y, r) in ((-0.10, 0.07), (0.12, 0.055)):
        T = (vx - 0.12, y, zv + 0.06)
        P = [(0.0, 0.0, 0), (r, 0.0, 0), (r, 0.03, 0), (r - 0.012, 0.035, 0), (r - 0.012, 0.055, 0), (r, 0.06, 0), (r, 0.08, 0), (0.0, 0.08, 0)]
        out.append(lathe_at("Port", P, [txv_m], origin=T, axis=(-1, 0, 0), steps=40))
        P = [(0.0, 0.04, 0), (r + 0.018, 0.04, 0), (r + 0.024, 0.05, 0), (r + 0.024, 0.13, 0), (r + 0.012, 0.14, 0), (0.0, 0.14, 0)]
        out.append(lathe_at("Cap", P, [cap_m], origin=T, axis=(-1, 0, 0), steps=40, bevel=0.004))
    T = (vx - 0.12, 0.0, zv - 0.16)
    out.append(lathe_at("Stud", [(0.0, 0.0, 0), (0.022, 0.0, 0), (0.022, 0.16, 0), (0.016, 0.17, 0), (0.0, 0.17, 0)], [steel],
                        origin=T, axis=(-1, 0, 0), steps=24))
    # clamp bolts holding valve to block
    for z in (zv - 0.16, zv + 0.26):
        bm = bmesh.new()
        C.cyl_bm(bm, 0.035, 0, 0.03, seg=6, matrix=axis_mat((vx - 0.12, 0.13 if z > zv else -0.13, z), (-1, 0, 0)))
        bo = C.mesh_obj("Bolt", bm, [steel])
        C.add_bevel(bo, 0.005, segments=1, angle=30)
        out.append(C.finalize(bo, angle=35))
    return out


def probe(black, wire):
    """clip-on fin temperature probe pushed into the fins near the bottom, with its lead"""
    out = []
    x, z = 0.55, -0.35
    y = -CD / 2
    out.append(rbox("ProbeClip", black, 0.10, 0.06, 0.20, center=(x, y - 0.03, z), bevel=0.012))
    out.append(rbox("ProbeHead", black, 0.08, 0.06, 0.09, center=(x, y - 0.07, z + 0.12), bevel=0.012))
    xe = CW / 2 + 0.02
    ctrl = [(x, y - 0.07, z + 0.16), (x + 0.05, y - 0.08, z + 0.30), (x + 0.30, y - 0.05, z + 0.38), (xe - 0.15, y - 0.04, z + 0.30),
            (xe - 0.02, y - 0.04, z + 0.12)]
    out.append(tube("ProbeLead", smooth_path(ctrl, 10), 0.016, wire, res=3))
    out.append(rbox("ProbePlug", black, 0.10, 0.12, 0.16, center=(xe - 0.01, y - 0.05, z - 0.02), bevel=0.015))
    return out


def build():
    fins = mat_fins()
    plate = mat_alu("PlateAlu", 0.50, 0.30)
    side = mat_alu("SideAlu", 0.42, 0.36)
    tank_m = mat_alu("TankAlu", 0.52, 0.32)
    pipe_m = mat_alu("PipeAlu", 0.62, 0.24)
    blk = mat_alu("BlockAlu", 0.46, 0.38)
    txv = C.mat_machined("TXVAlu", color=0.58, rough=0.26, rings=0.0)
    head = C.principled("Stainless", (0.66, 0.66, 0.66), metallic=1.0, rough=0.2)
    C.add_noise_bump(head, scale=800, strength=0.03, distance=0.0004)
    cap = C.mat_black_plastic("CapPE", rough=0.5, color=0.03)
    steel = C.principled("ZincSteel", (0.60, 0.60, 0.58), metallic=1.0, rough=0.3)
    oring = C.mat_rubber("ORing")
    black = C.mat_black_plastic("ProbePA", rough=0.45, color=0.03)
    wire = C.mat_rubber("Wire")
    objs = core(fins, plate, side) + tanks(tank_m)
    objs += valve(pipe_m, blk, txv, head, cap, steel, oring) + probe(black, wire)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("evaporatore", objs, "evaporatore.py",
            "car A/C evaporator: thick aluminium plate-fin core with ribbed top and bottom tanks, block expansion valve on two short pipes, fin temperature probe",
            az=-32, el=20, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
