"""HVAC / heater box assembly (gruppo clima / scatola riscaldamento) as removed from behind
the dashboard of a small car: large black polypropylene housing split on a screwed
parting flange, defrost slot and face-vent outlets on top, a footwell duct stub at the
bottom front, the spiral blower volute on the passenger side with the blower motor can
underneath and the fresh/recirculation intake box (grille, flap actuator) on top, two flap
actuator motors with linkage levers and rods on the driver side, heater-core pipes and
A/C pipes with the block expansion valve passing through a foam bulkhead seal, a wiring
loom with connectors, the rubber condensate drain elbow and steel mounting brackets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 10 cm.  Cabin side (front) toward -Y.
BX0, BX1 = -1.75, 1.45            # main body x range
BY = 1.25                         # main body half depth
BZ0, BZ1 = -1.30, 1.40            # main body z range
VC = Vector((2.55, -0.10, 0.0))   # blower volute axis
VR0, VR1 = 1.02, 1.42             # volute radius start/end
VZ0, VZ1 = -1.05, 0.25


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=48, bevel=None, mod=None, M=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M if M is not None else axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=40)
    return C.finalize(ob, angle=40)


def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), matrix=None, bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center, matrix=matrix)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def boxes(name, mat, specs, bevel=0.02, seg=2):
    bm = bmesh.new()
    for sx, sy, sz, c in specs:
        C.box_bm(bm, sx, sy, sz, center=c)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=5):
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


def opening(name, frame_m, dark_m, w, h, depth, M):
    """rectangular outlet: raised frame lip with a dark recessed throat, local +Z = outward"""
    out = []
    bm = bmesh.new()
    C.box_bm(bm, w + 0.16, h + 0.16, depth, center=(0, 0, depth / 2))
    fr = C.mesh_obj(name + "Frame", bm, [frame_m])
    fr.matrix_world = M
    cb = bmesh.new()
    C.box_bm(cb, w, h, depth * 4, center=(0, 0, 0))
    cut = C.mesh_obj(name + "Cut", cb, [frame_m])
    cut.matrix_world = M
    bo = C.add_boolean(fr, cut)
    bo.use_self = True
    C.add_bevel(fr, 0.025, segments=2, angle=30)
    out.append(C.finalize(fr, angle=35, remove=[cut]))
    bm = bmesh.new()
    C.box_bm(bm, w + 0.02, h + 0.02, 0.02, center=(0, 0, -0.06))
    th = C.mesh_obj(name + "Throat", bm, [dark_m])
    th.matrix_world = M
    out.append(th)
    return out


# ----------------------------------------------------------------- housing
def housing(pp, pp2, dark, steel):
    out = []
    W = BX1 - BX0
    xc = (BX0 + BX1) / 2
    zc = (BZ0 + BZ1) / 2
    out.append(rbox("BodyL", pp, -0.25 - BX0, 2 * BY, BZ1 - BZ0, center=((BX0 - 0.25) / 2, 0, zc), bevel=0.22, seg=4))
    out.append(rbox("BodyR", pp2, BX1 + 0.25, 2 * BY - 0.04, BZ1 - BZ0 - 0.04, center=((BX1 - 0.25) / 2, 0, zc), bevel=0.24, seg=4))
    # parting flange around the body at x = -0.25
    bm = bmesh.new()
    C.box_bm(bm, 0.10, 2 * BY + 0.14, BZ1 - BZ0 + 0.14, center=(-0.25, 0, zc))
    fl = C.mesh_obj("Flange", bm, [pp])
    C.add_bevel(fl, 0.05, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35))
    # screw bosses + screws along the flange (front and top edges)
    bm = bmesh.new()
    sc = []
    for z in (-0.9, -0.2, 0.5, 1.15):
        sc.append(Vector((-0.25, -BY - 0.06, z)))
    for y in (-0.7, 0.1, 0.9):
        sc.append(Vector((-0.25, y, BZ1 + 0.06)))
    for p in sc:
        n = Vector((0, -1, 0)) if p.y < -BY else Vector((0, 0, 1))
        C.box_bm(bm, 0.24, 0.18, 0.18, center=p - n * 0.02)
    bs = C.mesh_obj("ScrewBosses", bm, [pp])
    C.add_bevel(bs, 0.04, segments=2, angle=30)
    out.append(C.finalize(bs, angle=35))
    for p in sc:
        n = Vector((0, -1, 0)) if p.y < -BY else Vector((0, 0, 1))
        prof = [(0.0, 0.07, 0), (0.07, 0.07, 0), (0.07, 0.085, 0), (0.05, 0.10, 0), (0.05, 0.13, 0), (0.042, 0.14, 0), (0.0, 0.14, 0)]
        ob = C.lathe("Screw", prof, [steel], steps=6)
        ob.matrix_world = axis_mat(p, n)
        out.append(C.finalize(ob, angle=40))
    # stiffening ribs on the front face of both halves
    specs = []
    for x in (-1.35, -0.85):
        specs.append((0.07, 0.10, 1.9, Vector((x, -BY - 0.03, -0.25))))
    for x in (0.25, 0.75):
        specs.append((0.07, 0.10, 1.6, Vector((x, -BY - 0.01, -0.35))))
    specs.append((1.2, 0.10, 0.07, Vector((-1.1, -BY - 0.03, 0.75))))
    out.append(boxes("FrontRibs", pp, specs, bevel=0.025))
    # top outlets: defrost slot (front) and two face-vent outlets (rear)
    up = Matrix.Translation((0, 0, BZ1 - 0.04))
    out += opening("Defrost", pp, dark, 2.1, 0.32, 0.18, up @ Matrix.Translation((-0.45, -0.70, 0)))
    for x in (-1.05, 0.45):
        out += opening("Vent", pp, dark, 0.78, 0.48, 0.24, up @ Matrix.Translation((x, 0.45, 0)))
    # footwell duct stub at the front bottom
    M = Matrix.Translation((-0.85, -BY - 0.01, -0.85)) @ Matrix.Rotation(math.radians(90), 4, "X")
    bm = bmesh.new()
    C.box_bm(bm, 1.05, 0.50, 0.42, center=(0, 0, 0.21))
    st = C.mesh_obj("FootDuct", bm, [pp])
    st.matrix_world = M
    C.add_bevel(st, 0.08, segments=3, angle=30)
    out.append(C.finalize(st, angle=35))
    out += opening("Foot", pp, dark, 0.86, 0.32, 0.12, M @ Matrix.Translation((0, 0, 0.40)))
    # condensate drain elbow at the bottom
    out.append(lathe_at("DrainBoss", [(0.0, 0.0, 0), (0.16, 0.0, 0), (0.16, 0.10, 0), (0.0, 0.10, 0)], [pp],
                        origin=(0.55, 0.55, BZ0 + 0.02), axis=(0, 0, -1), steps=32))
    return out


def drain(rub):
    pts = smooth_path([(0.55, 0.55, BZ0 - 0.05), (0.55, 0.55, BZ0 - 0.25), (0.55, 0.85, BZ0 - 0.42), (0.55, 1.35, BZ0 - 0.48)], 8)
    out = [tube("DrainHose", pts, 0.11, rub)]
    return out


# ----------------------------------------------------------------- blower
def blower(pp, dark, zinc, pin):
    out = []
    span = VR1 - VR0

    def spiral(r, z, t):
        if r < 0.5:
            return r
        u = t / math.tau
        return r + span * u

    P = [(0.0, VZ0, 0), (VR0 - 0.08, VZ0, 0), (VR0, VZ0 + 0.08, 0), (VR0, VZ1 - 0.08, 0), (VR0 - 0.08, VZ1, 0), (0.0, VZ1, 0)]
    M = Matrix.Translation(VC) @ Matrix.Rotation(math.radians(200), 4, "Z")
    out.append(lathe_at("Volute", P, [pp], M=M, steps=144, mod=spiral, bevel=0.03))
    # outlet throat joining the volute to the main body
    out.append(rbox("VoluteDuct", pp, 1.30, 1.70, VZ1 - VZ0 - 0.06, center=(BX1 + 0.35, -0.05, (VZ0 + VZ1) / 2), bevel=0.14, seg=3))
    # moulded spiral rib on top of the volute
    P = [(VR0 - 0.30, VZ1 - 0.02, 0), (VR0 - 0.18, VZ1 - 0.02, 0), (VR0 - 0.18, VZ1 + 0.05, 0), (VR0 - 0.30, VZ1 + 0.05, 0)]
    out.append(lathe_at("TopRib", P, [pp], M=M, steps=144, mod=lambda r, z, t: r + span * 0.8 * t / math.tau))
    # blower motor underneath: flange, can, rear boss
    c = (VC.x, VC.y, 0)
    out.append(lathe_at("MotorFlange", [(0.0, VZ0 - 0.12, 0), (0.95, VZ0 - 0.12, 0), (0.98, VZ0 - 0.06, 0), (0.98, VZ0 + 0.02, 0),
                                        (0.0, VZ0 + 0.02, 0)], [pp], origin=c, steps=96, bevel=0.02))
    vents = lambda r, z, t: r - (0.03 if (abs(r - 0.38) < 1e-6 and VZ0 - 0.55 < z < VZ0 - 0.35 and math.cos(8 * t) > 0.7) else 0)
    P = [(0.0, VZ0 - 0.82, 0), (0.14, VZ0 - 0.82, 0), (0.14, VZ0 - 0.76, 0), (0.30, VZ0 - 0.74, 0), (0.38, VZ0 - 0.68, 0)]
    P += [(0.38, VZ0 - 0.68 + 0.56 * i / 14, 0) for i in range(15)] + [(0.40, VZ0 - 0.1, 0), (0.0, VZ0 - 0.1, 0)]
    out.append(lathe_at("MotorCan", P, [zinc], origin=c, steps=96, mod=vents))
    # bayonet ears on the motor flange
    specs = []
    for k in range(3):
        a = math.tau * k / 3 + 0.4
        specs.append((0.30, 0.22, 0.08, Vector((VC.x + 1.05 * math.cos(a), VC.y + 1.05 * math.sin(a), VZ0 - 0.08))))
    out.append(boxes("MotorEars", pp, specs, bevel=0.03))
    # intake box on top: fresh-air opening with grille facing front, recirc opening at back
    ib_c = Vector((VC.x - 0.05, VC.y + 0.05, VZ1 + 0.45))
    out.append(rbox("IntakeBox", pp, 2.05, 2.0, 0.92, center=ib_c, bevel=0.16, seg=3))
    Mf = Matrix.Translation(ib_c + Vector((0, -1.0, 0.0))) @ Matrix.Rotation(math.radians(90), 4, "X")
    out += opening("Fresh", pp, dark, 1.55, 0.58, 0.10, Mf)
    specs = [(0.05, 0.05, 0.60, Vector((ib_c.x - 0.70 + 0.14 * i, ib_c.y - 1.07, ib_c.z))) for i in range(11)]
    out.append(boxes("Grille", pp, specs, bevel=0.012, seg=1))
    out += opening("Recirc", pp, dark, 1.45, 0.42, 0.10, Matrix.Translation(ib_c + Vector((0, 0.35, 0.44))))
    return out


# ----------------------------------------------------------------- actuators, linkages, pipes
def actuator(name, black, pin, M):
    """small flap motor: local X-Y footprint, output toward local -Z (into the housing)"""
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 0.72, 0.52, 0.26, center=(0, 0, 0.13))
    C.box_bm(bm, 0.32, 0.22, 0.20, center=(-0.24, -0.34, 0.12))     # connector shroud
    C.box_bm(bm, 0.12, 0.16, 0.06, center=(0.44, 0.22, 0.03))        # ears
    C.box_bm(bm, 0.12, 0.16, 0.06, center=(-0.44, 0.22, 0.03))
    C.box_bm(bm, 0.16, 0.12, 0.06, center=(0.28, -0.32, 0.03))
    ob = C.mesh_obj(name, bm, [black])
    ob.matrix_world = M
    C.add_bevel(ob, 0.035, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.40, 0.30, 0.012, center=(0.06, 0.04, 0.262))
    lb = C.mesh_obj(name + "Label", bm, [label_m])
    lb.matrix_world = M
    out.append(lb)
    bm = bmesh.new()
    C.box_bm(bm, 0.03, 0.12, 0.03, center=(-0.28, -0.40, 0.10))
    C.box_bm(bm, 0.03, 0.12, 0.03, center=(-0.20, -0.40, 0.10))
    pn = C.mesh_obj(name + "Pins", bm, [pin])
    pn.matrix_world = M
    out.append(pn)
    return out


def linkage(black, steel, origin, n, arm_dir, rod_to):
    out = []
    M = axis_mat(origin, n)
    out.append(lathe_at("Pivot", [(0.0, 0.0, 0), (0.12, 0.0, 0), (0.12, 0.08, 0), (0.0, 0.08, 0)], [black], M=M, steps=32))
    d = Vector(arm_dir).normalized()
    p0 = Vector(origin) + Vector(n).normalized() * 0.11
    p1 = p0 + d * 0.48
    out.append(tube("Lever", [p0, p1], 0.045, black, res=2))
    out.append(tube("Rod", [p1, Vector(rod_to)], 0.022, steel, res=2))
    out.append(lathe_at("RodEnd", [(0.0, -0.04, 0), (0.06, -0.04, 0), (0.06, 0.04, 0), (0.0, 0.04, 0)], [black],
                        origin=p1, axis=n, steps=24))
    return out


def pipes(alu, blk, steel, cap, foam):
    out = []
    xs = BX0 - 0.02
    # foam bulkhead seal plate on the driver side
    out.append(rbox("Seal", foam, 0.12, 0.85, 1.55, center=(xs - 0.06, 0.62, 0.10), bevel=0.04))
    # heater-core pipes: out of the side, bend back toward the bulkhead (+Y)
    for i, z in enumerate((-0.38, -0.05)):
        pts = smooth_path([(xs, 0.55, z), (xs - 0.35, 0.55, z), (xs - 0.55, 0.85, z), (xs - 0.55, 1.65, z)], 8)
        out.append(tube("HeaterPipe%d" % i, pts, 0.085, alu))
    out.append(rbox("HeaterFlange", steel, 0.30, 0.05, 0.62, center=(xs - 0.55, 1.62, -0.215), bevel=0.012))
    # A/C pipes into the expansion valve block
    for i, (z, r) in enumerate(((0.45, 0.07), (0.72, 0.05))):
        pts = smooth_path([(xs, 0.55, z), (xs - 0.25, 0.55, z), (xs - 0.40, 0.75, z), (xs - 0.40, 1.15, z)], 8)
        out.append(tube("ACPipe%d" % i, pts, r, alu))
    out.append(rbox("TXV", blk, 0.30, 0.26, 0.48, center=(xs - 0.40, 1.28, 0.60), bevel=0.025))
    out.append(lathe_at("TXVDome", [(0.0, 0.0, 0), (0.13, 0.0, 0), (0.14, 0.04, 0), (0.10, 0.10, 0), (0.0, 0.12, 0)], [steel],
                        origin=(xs - 0.40, 1.28, 0.84), steps=48))
    for z in (0.47, 0.74):
        out.append(lathe_at("TXVCap", [(0.0, 0.0, 0), (0.075, 0.0, 0), (0.075, 0.12, 0), (0.06, 0.135, 0), (0.0, 0.135, 0)], [cap],
                            origin=(xs - 0.40, 1.40, z), axis=(0, 1, 0), steps=32, bevel=0.008))
    return out


def loom(loom_m, black):
    out = []
    ctrl = [(-1.35, -0.85, BZ1 + 0.06), (-1.45, -0.2, BZ1 + 0.08), (-1.2, 0.95, BZ1 + 0.06), (0.0, 1.05, BZ1 + 0.07),
            (1.3, 0.95, BZ1 + 0.06), (2.0, 0.7, VZ1 + 0.95)]
    out.append(tube("Loom", smooth_path(ctrl, 10), 0.065, loom_m, res=4))
    # branch down to the side actuator
    ctrl = [(-1.45, -0.2, BZ1 + 0.08), (BX0 + 0.25, -0.35, BZ1 + 0.02), (BX0 - 0.15, -0.45, 0.9), (BX0 - 0.26, -0.62, 0.66)]
    out.append(tube("LoomBranch", smooth_path(ctrl, 8), 0.04, loom_m, res=3))
    out.append(rbox("MainPlug", black, 0.38, 0.26, 0.22, center=(-1.35, -0.85 - 0.12, BZ1 + 0.06), bevel=0.03))
    return out


def brackets(steel):
    out = []
    for (x, y) in ((-1.25, 0.95), (1.05, 0.95)):
        bm = bmesh.new()
        C.box_bm(bm, 0.36, 0.05, 0.55, center=(x, y + 0.32, BZ1 + 0.22))
        C.box_bm(bm, 0.36, 0.36, 0.05, center=(x, y + 0.15, BZ1 + 0.0))
        ob = C.mesh_obj("Bracket", bm, [steel])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.06, -1, 1, seg=24, matrix=Matrix.Translation((x, y, BZ1 + 0.36)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        cut = C.mesh_obj("BrHole", cb, [steel])
        bo = C.add_boolean(ob, cut)
        bo.use_self = True
        C.add_bevel(ob, 0.015, segments=1, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
    return out


label_m = None


def build():
    global label_m
    pp = C.mat_black_plastic("HousingPP", rough=0.58, color=0.036)
    pp2 = C.mat_black_plastic("HousingPP2", rough=0.52, color=0.032)
    dark = C.principled("Throat", (0.004, 0.004, 0.004), rough=0.9)
    act = C.mat_black_plastic("ActPBT", rough=0.42, color=0.024)
    steel = C.principled("ZincSteel", (0.60, 0.60, 0.58), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=300, strength=0.04, distance=0.0008)
    zinc = C.principled("MotorZinc", (0.58, 0.58, 0.56), metallic=1.0, rough=0.36)
    C.add_noise_bump(zinc, scale=300, strength=0.05, distance=0.0008)
    alu = C.principled("PipeAlu", (0.60, 0.60, 0.59), metallic=1.0, rough=0.26)
    C.add_noise_bump(alu, scale=300, strength=0.05, distance=0.0008, rough_var=0.06)
    blk = C.principled("BlockAlu", (0.50, 0.50, 0.49), metallic=1.0, rough=0.34)
    cap = C.mat_black_plastic("CapPE", rough=0.5, color=0.03)
    foam = C.principled("Foam", (0.07, 0.07, 0.07), rough=0.95)
    C.add_noise_bump(foam, scale=120, strength=0.5, distance=0.004)
    rub = C.mat_rubber("DrainRubber")
    pin = C.principled("TinPin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.22)
    label_m = C.mat_label(C.label_image("ActLabel", 512, 384, seed=5, lines=3, barcode=False))
    loom_m = C.mat_black_plastic("Loom", rough=0.5, color=0.02)
    nt = loom_m.node_tree
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 28.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED").inputs["Normal"])

    objs = housing(pp, pp2, dark, steel) + drain(rub) + blower(pp2, dark, zinc, pin)
    # actuators: one on the driver-side face, one on the front face, one on the intake box
    side = Matrix.Translation((BX0 - 0.02, -0.55, 0.55)) @ Matrix.Rotation(math.radians(-90), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "Z")
    objs += actuator("ActSide", act, pin, side)
    objs += linkage(act, steel, (BX0 - 0.02, -0.80, -0.45), (-1, 0, 0), (0, 0.3, -1), (BX0 - 0.13, 0.15, -0.95))
    front = Matrix.Translation((0.55, -BY - 0.02, 0.70)) @ Matrix.Rotation(math.radians(90), 4, "X")
    objs += actuator("ActFront", act, pin, front)
    objs += linkage(act, steel, (1.05, -BY - 0.02, -0.15), (0, -1, 0), (1, 0, -0.6), (1.30, -BY - 0.13, -0.75))
    top = Matrix.Translation((VC.x + 0.45, VC.y - 0.35, VZ1 + 0.91)) @ Matrix.Rotation(math.radians(12), 4, "Z")
    objs += actuator("ActIntake", act, pin, top)
    objs += pipes(alu, blk, steel, cap, foam) + loom(loom_m, act) + brackets(steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("gruppo-clima", objs, "gruppo-clima.py",
            "car HVAC heater box assembly: large black plastic housing with air outlets, blower volute and motor, flap actuator motors with linkages, heater and A/C pipes",
            az=-30, el=24, lens=70, fill=0.86,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
