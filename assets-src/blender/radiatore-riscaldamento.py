"""Heater core (radiatore riscaldamento abitacolo) as removed from the HVAC box of a small
car: compact brazed aluminium core (flat tubes proud of a fine louvred fin grid), top and
bottom side plates, rounded aluminium end tanks crimped onto the header plates on both
short sides, and two aluminium pipes leaving the inlet/outlet tank, bending toward the
bulkhead and ending in a shared two-hole flange plate with O-ring spigots and a screw
hole."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 10 cm. Core in the X-Z plane, front face toward -Y.
CW, CD, CH = 1.80, 0.32, 1.40
TP = 0.085                      # tube pitch
TW = 0.16                       # tank width
XT = CW / 2 + 0.02
PR = 0.085                      # pipe radius
PZ = (0.30, -0.06)              # pipe heights on the left tank


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=48, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
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


def tube(name, pts, r, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def bend_path(p0, d0, d1, R, l0, l1, n=12):
    p0, d0, d1 = Vector(p0), Vector(d0).normalized(), Vector(d1).normalized()
    pts = [p0, p0 + d0 * l0]
    c = p0 + d0 * l0
    for k in range(1, n + 1):
        a = math.pi / 2 * k / n
        pts.append(c + d0 * R * math.sin(a) + d1 * R * (1 - math.cos(a)))
    pts.append(pts[-1] + d1 * l1)
    return pts


# ----------------------------------------------------------------- materials
def mat_fins(name="FinGrid", pitch=0.016):
    """serpentine louvred fins seen face-on between the tubes, with light dust"""
    m = C.principled(name, (0.40, 0.40, 0.40), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
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
    wz.inputs["Scale"].default_value = 0.314 / 0.009
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
    cr.elements[1].color = (0.46, 0.46, 0.45, 1)
    nt.links.new(mx.outputs["Result"], ramp.inputs["Fac"])
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 4.0
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
    dirt.inputs["B"].default_value = (0.36, 0.31, 0.25, 1)
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


# ----------------------------------------------------------------- parts
def core(fins_m, tube_m, plate_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CW, CD - 0.012, CH, center=(0, 0, 0))
    out.append(C.mesh_obj("FinBlock", bm, [fins_m]))
    bm = bmesh.new()
    n = int(CH / TP)
    z0 = -(n - 1) * TP / 2
    for i in range(n):
        C.box_bm(bm, CW, CD + 0.006, 0.018, center=(0, 0, z0 + i * TP))
    tb = C.mesh_obj("Tubes", bm, [tube_m])
    C.add_bevel(tb, 0.004, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    for sz in (-1, 1):
        zc = sz * (CH / 2 + 0.02)
        out.append(rbox("SidePlate", plate_m, CW, CD + 0.012, 0.04, center=(0, 0, zc), bevel=0.008))
        # stamped stiffening beads along the side plate
        bm = bmesh.new()
        for k in range(5):
            x = -CW / 2 + 0.2 + k * (CW - 0.4) / 4
            C.box_bm(bm, 0.18, CD - 0.08, 0.012, center=(x, 0, zc + sz * 0.022))
        out.append(C.finalize(C.mesh_obj("Beads", bm, [plate_m]), angle=35))
    return out


def tank(sx, alu, hdr):
    out = []
    TH = CH + 0.10
    xc = sx * (XT + TW / 2)
    out.append(rbox("Header", hdr, 0.035, CD + 0.05, TH + 0.04, center=(sx * (XT - 0.005), 0, 0), bevel=0.01))
    bm = bmesh.new()
    for k in range(13):
        z = -TH / 2 + 0.06 + k * (TH - 0.12) / 12
        for sy in (-1, 1):
            C.box_bm(bm, 0.035, 0.012, 0.04, center=(sx * (XT + 0.022), sy * (CD / 2 + 0.03), z))
    ct = C.mesh_obj("Crimp", bm, [hdr])
    C.add_bevel(ct, 0.004, segments=1, angle=30)
    out.append(C.finalize(ct, angle=35))
    out.append(rbox("TankShell", alu, TW, CD + 0.03, TH, center=(xc, 0, 0), bevel=0.065, seg=6))
    # end caps of the tank (brazed plugs)
    for sz in (-1, 1):
        out.append(lathe_at("TankPlug", [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.05, 0.025, 0), (0.04, 0.035, 0), (0.0, 0.035, 0)],
                            [hdr], origin=(xc, 0, sz * TH / 2 - sz * 0.01), axis=(0, 0, sz), steps=32))
    return out


def pipes(pipe_m, hdr, flange_m, oring):
    out = []
    xl = -(XT + TW)
    y_end = -0.70
    fy = y_end
    for i, z in enumerate(PZ):
        pts = [Vector((xl + 0.06, 0.0, z))]
        pts += bend_path((xl + 0.02, 0.0, z), (-1, 0, 0), (0, -1, 0), 0.20, 0.30, 0.0)
        pts.append(Vector((pts[-1].x, fy + 0.02, z)))
        out.append(tube("Pipe%d" % i, pts, PR, pipe_m))
        # brazed collar at the tank
        out.append(lathe_at("Collar", [(PR - 0.01, 0.0, 0), (PR + 0.035, 0.0, 0), (PR + 0.035, 0.02, 0), (PR, 0.05, 0), (PR - 0.01, 0.05, 0)],
                            [hdr], origin=(xl + 0.012, 0, z), axis=(-1, 0, 0), steps=40))
        # O-ring spigot through the flange
        xs = pts[-1].x
        P = [(0.0, 0.0, 0), (PR, 0.0, 0), (PR, 0.07, 0), (PR - 0.012, 0.075, 0), (PR - 0.012, 0.105, 0), (PR, 0.11, 0),
             (PR, 0.15, 0), (PR - 0.01, 0.16, 0), (PR - 0.024, 0.16, 0), (PR - 0.024, 0.12, 0), (0.0, 0.12, 0)]
        out.append(lathe_at("Spigot", P, [pipe_m], origin=(xs, fy, z), axis=(0, -1, 0), steps=48, bevel=0.003))
        P = [(PR - 0.014, 0.078, 0), (PR + 0.012, 0.078, 0), (PR + 0.016, 0.09, 0), (PR + 0.012, 0.102, 0), (PR - 0.014, 0.102, 0)]
        out.append(lathe_at("ORing", P, [oring], origin=(xs, fy, z), axis=(0, -1, 0), steps=48))
    # shared flange plate (stamped steel, zinc) with a screw hole between the pipes
    xs = xl + 0.02 - 0.30 - 0.20
    zc = (PZ[0] + PZ[1]) / 2
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.035, 0.66, center=(xs, fy + 0.0, zc))
    C.box_bm(bm, 0.18, 0.035, 0.18, center=(xs - 0.2, fy, zc))
    fl = C.mesh_obj("Flange", bm, [flange_m])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.035, -1, 1, seg=32, matrix=Matrix.Translation((xs - 0.24, 0, zc)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    cut = C.mesh_obj("FlangeHole", cb, [flange_m])
    bo = C.add_boolean(fl, cut)
    bo.use_self = True
    C.add_bevel(fl, 0.008, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35, remove=[cut]))
    return out


def build():
    fins = mat_fins()
    tube_m = mat_alu("TubeAlu", 0.52, 0.30)
    plate = mat_alu("PlateAlu", 0.44, 0.36)
    tank_m = mat_alu("TankAlu", 0.50, 0.34)
    hdr = mat_alu("HeaderAlu", 0.38, 0.40)
    pipe_m = mat_alu("PipeAlu", 0.62, 0.24)
    flange = C.principled("ZincSteel", (0.60, 0.60, 0.58), metallic=1.0, rough=0.33)
    C.add_noise_bump(flange, scale=500, strength=0.04, distance=0.0006, rough_var=0.05)
    oring = C.mat_rubber("ORing")
    objs = core(fins, tube_m, plate) + tank(-1, tank_m, hdr) + tank(1, tank_m, hdr)
    objs += pipes(pipe_m, hdr, flange, oring)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("radiatore-riscaldamento", objs, "radiatore-riscaldamento.py",
            "car heater core: small aluminium fin-and-tube core with end tanks, two aluminium pipes ending in a flange plate with O-rings",
            az=32, el=18, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
