"""Brake master cylinder with vacuum servo (pompa freno + servofreno), as removed from a
small car: large round black-painted pressed-steel servo drum with crimped seam and
stamped stiffening rings, vacuum check valve with grommet on the front shell; cast
aluminium tandem master cylinder bolted to the front with flange nuts, two brake-line
ports; translucent white fluid reservoir with brake fluid inside, MIN/MAX marks and
black cap with level-sensor plug; rear face with four mounting studs, pushrod with
rubber boot and clevis."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

XF = 1.36            # servo front face (axis = +X, 1 unit ~ 10 cm)
ZR = 0.40            # reservoir bottom
RL, RW, RH = 1.10, 0.62, 0.58   # reservoir size
RX = XF + 0.80       # reservoir centre x
LEVEL = 0.40         # fluid height inside reservoir


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None, mat=0):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=axis_mat(origin, axis), r1=r1, mat=mat)


def lathe_at(name, prof, mats, origin, axis, steps=64, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
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


# ----------------------------------------------------------------- servo
def servo(paint, zinc, rubber):
    out = []
    P = [(0.0, -0.06, 0), (0.24, -0.06, 0), (0.27, -0.02, 0), (0.33, 0.0, 0), (0.52, 0.01, 0), (0.55, 0.035, 0),
         (0.60, 0.04, 0), (0.86, 0.055, 0), (0.89, 0.08, 0), (1.03, 0.10, 0), (1.10, 0.15, 0), (1.14, 0.25, 0),
         (1.15, 0.40, 0), (1.15, 0.63, 0), (1.21, 0.645, 0), (1.225, 0.68, 0), (1.21, 0.715, 0), (1.15, 0.73, 0),
         (1.15, 0.98, 0), (1.14, 1.10, 0), (1.10, 1.20, 0), (1.03, 1.255, 0), (0.90, 1.28, 0), (0.87, 1.305, 0),
         (0.62, 1.325, 0), (0.58, 1.36, 0), (0.0, 1.36, 0)]
    out.append(C.finalize(lathe_at("Servo", P, [paint], (0, 0, 0), (1, 0, 0), steps=160), angle=40))
    # crimp tabs folded over the seam
    bm = bmesh.new()
    for k in range(24):
        a = math.tau * k / 24
        M = Matrix.Rotation(a, 4, "X") @ Matrix.Translation((0.68, 0, 1.205))
        C.box_bm(bm, 0.10, 0.10, 0.04, matrix=M)
    tb = C.mesh_obj("Crimps", bm, [paint])
    C.add_bevel(tb, 0.012, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    # rear studs (with spacer collars) and front studs for the master cylinder
    for k in range(4):
        a = math.radians(45 + 90 * k)
        o = Vector((0.03, 0.42 * math.cos(a), 0.42 * math.sin(a)))
        P = [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.09, 0.03, 0), (0.045, 0.035, 0), (0.045, 0.40, 0), (0.035, 0.415, 0), (0.0, 0.415, 0)]
        out.append(C.finalize(lathe_at("RearStud", P, [zinc], o, (-1, 0, 0), steps=32), angle=40))
    # pushrod hub boot, rod, jam nut, clevis
    P = [(0.0, 0.04, 0), (0.24, 0.04, 0), (0.24, 0.10, 0)]
    x = 0.10
    r = 0.22
    for i in range(5):
        P += [(r, x + 0.03, 0), (r - 0.04, x + 0.06, 0)]
        x += 0.06
        r -= 0.022
    P += [(0.08, x + 0.03, 0), (0.07, x + 0.09, 0), (0.0, x + 0.09, 0)]
    out.append(C.finalize(lathe_at("PushBoot", P, [rubber], (0, 0, 0), (-1, 0, 0)), angle=50))
    P = [(0.0, 0.40, 0), (0.05, 0.40, 0), (0.05, 1.05, 0), (0.0, 1.05, 0)]
    out.append(C.finalize(lathe_at("Pushrod", P, [zinc], (0, 0, 0), (-1, 0, 0), steps=32), angle=40))
    bm = bmesh.new()
    cyl_axis(bm, 0.085, (0, 0, 0), (-1, 0, 0), 0.96, 1.03, seg=6)
    nut = C.mesh_obj("JamNut", bm, [zinc])
    C.add_bevel(nut, 0.008, segments=2, angle=30)
    out.append(C.finalize(nut, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.20, 0.18, center=(-1.18, 0, 0))
    cl = C.mesh_obj("Clevis", bm, [zinc])
    cb = bmesh.new()
    C.box_bm(cb, 0.24, 0.09, 0.4, center=(-1.24, 0, 0))
    cyl_axis(cb, 0.035, (-1.22, 0, 0), (0, 1, 0), -0.3, 0.3, seg=24)
    cut = C.mesh_obj("ClevisCut", cb, [zinc])
    C.add_boolean(cl, cut)
    C.add_bevel(cl, 0.015, segments=2, angle=30)
    out.append(C.finalize(cl, angle=35, remove=[cut]))
    # vacuum check valve in a grommet on the front shell
    o = Vector((XF - 0.06, 0.52, 0.56))
    P = [(0.0, 0.0, 0), (0.17, 0.0, 0), (0.18, 0.025, 0), (0.17, 0.05, 0), (0.0, 0.05, 0)]
    out.append(C.finalize(lathe_at("Grommet", P, [rubber], o, (1, 0, 0)), angle=50))
    P = [(0.0, 0.03, 0), (0.12, 0.03, 0), (0.12, 0.13, 0), (0.10, 0.15, 0), (0.0, 0.15, 0)]
    out.append(C.finalize(lathe_at("ValveBody", P, [valve_m], o, (1, 0, 0)), angle=45))
    pts = [o + Vector((0.12, 0, 0))]
    c0 = o + Vector((0.12, 0, 0.12))
    for k in range(1, 11):
        a = math.pi / 2 * k / 10
        pts.append(c0 + Vector((0.12 * math.sin(a), 0, -0.12 * math.cos(a))))
    pts.append(pts[-1] + Vector((0, 0, 0.20)))
    out.append(tube("ValveElbow", pts, 0.065, valve_m))
    P = [(0.0, 0.0, 0), (0.075, 0.0, 0), (0.085, 0.02, 0), (0.07, 0.05, 0), (0.07, 0.07, 0), (0.06, 0.08, 0), (0.0, 0.08, 0)]
    out.append(C.finalize(lathe_at("Barb", P, [valve_m], pts[-1], (0, 0, 1)), angle=45))
    return out


# ----------------------------------------------------------------- master cylinder
def master(alu, zinc, rubber):
    out = []
    P = [(0.0, 0.0, 0), (0.26, 0.0, 0), (0.26, 0.10, 0), (0.24, 0.13, 0), (0.24, 0.55, 0), (0.255, 0.57, 0),
         (0.255, 0.62, 0), (0.24, 0.64, 0), (0.24, 1.38, 0), (0.22, 1.45, 0), (0.16, 1.50, 0), (0.0, 1.50, 0)]
    out.append(C.finalize(lathe_at("MCBody", P, [alu], (XF + 0.10, 0, 0), (1, 0, 0), steps=96), angle=40))
    # flange plate
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 1.18, 0.40, center=(XF + 0.055, 0, 0))
    fl = C.mesh_obj("Flange", bm, [alu])
    C.add_bevel(fl, 0.17, segments=8, angle=30)
    out.append(C.finalize(fl, angle=35))
    # reservoir bosses on top, brake-line port bosses on +Y side
    bm = bmesh.new()
    for x in (XF + 0.48, XF + 1.08):
        cyl_axis(bm, 0.13, (x, 0, 0.0), (0, 0, 1), 0.0, 0.33, seg=40)
    for x in (XF + 0.70, XF + 1.22):
        cyl_axis(bm, 0.115, (x, 0, -0.02), (0, 1, 0), 0.0, 0.33, seg=40)
    bs = C.mesh_obj("Bosses", bm, [alu])
    cb = bmesh.new()
    for x in (XF + 0.70, XF + 1.22):
        cyl_axis(cb, 0.052, (x, 0, -0.02), (0, 1, 0), 0.10, 0.45, seg=32)
        cyl_axis(cb, 0.075, (x, 0, -0.02), (0, 1, 0), 0.305, 0.335, seg=32, r1=0.052)
    cut = C.mesh_obj("PortCut", cb, [alu])
    C.add_boolean(bs, cut)
    C.add_bevel(bs, 0.012, segments=2, angle=30)
    out.append(C.finalize(bs, angle=35, remove=[cut]))
    # mounting nuts on the flange studs
    for y in (-0.45, 0.45):
        P = [(0.0, 0.0, 0), (0.045, 0.0, 0), (0.045, 0.24, 0), (0.035, 0.25, 0), (0.0, 0.25, 0)]
        out.append(C.finalize(lathe_at("Stud", P, [zinc], (XF, y, 0), (1, 0, 0), steps=24), angle=40))
        bm = bmesh.new()
        cyl_axis(bm, 0.10, (XF + 0.11, y, 0), (1, 0, 0), 0.0, 0.10, seg=6)
        cyl_axis(bm, 0.12, (XF + 0.11, y, 0), (1, 0, 0), 0.0, 0.02, seg=40)
        nut = C.mesh_obj("FlangeNut", bm, [zinc])
        C.add_bevel(nut, 0.01, segments=2, angle=30)
        out.append(C.finalize(nut, angle=35))
    # reservoir grommets
    for x in (XF + 0.48, XF + 1.08):
        P = [(0.06, 0.32, 0), (0.15, 0.32, 0), (0.155, 0.36, 0), (0.14, ZR + 0.02, 0), (0.06, ZR + 0.02, 0)]
        out.append(C.finalize(lathe_at("ResGrommet", P, [rubber], (x, 0, 0), (0, 0, 1)), angle=50))
    return out


# ----------------------------------------------------------------- reservoir
def reservoir(shell_m, fluid_m, cap_m):
    out = []
    zc = ZR + RH / 2
    bm = bmesh.new()
    C.box_bm(bm, RL, RW, RH, center=(RX, 0, zc))
    # filler neck
    C.cyl_bm(bm, 0.19, zc, ZR + RH + 0.10, seg=48, matrix=Matrix.Translation((RX + 0.22, 0.03, 0)))
    # side mounting ear
    C.box_bm(bm, 0.20, 0.06, 0.22, center=(RX - RL / 2 - 0.06, 0, ZR + 0.20))
    sh = C.mesh_obj("Reservoir", bm, [shell_m])
    rm = sh.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.010
    sm = sh.modifiers.new("Smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = 10
    so = sh.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.022
    so.offset = -1
    out.append(C.finalize(sh, angle=60))
    # brake fluid inside
    bm = bmesh.new()
    C.box_bm(bm, RL - 0.08, RW - 0.08, LEVEL, center=(RX, 0, ZR + 0.035 + LEVEL / 2))
    fl = C.mesh_obj("Fluid", bm, [fluid_m])
    C.add_bevel(fl, 0.06, segments=4, angle=30)
    out.append(C.finalize(fl, angle=40))
    # moulded MIN / MAX marks on the +Y face
    bm = bmesh.new()
    y = RW / 2 + 0.004
    for z in (ZR + 0.24, ZR + 0.44):
        C.box_bm(bm, 0.22, 0.016, 0.018, center=(RX - 0.30, y, z))
    C.box_bm(bm, 0.018, 0.016, 0.20, center=(RX - 0.30 - 0.11, y, ZR + 0.34))
    mk = C.mesh_obj("MinMax", bm, [shell_m])
    C.add_bevel(mk, 0.005, segments=1, angle=30)
    out.append(C.finalize(mk, angle=35))
    # spigots down into the grommets
    bm = bmesh.new()
    for x in (XF + 0.48, XF + 1.08):
        C.cyl_bm(bm, 0.075, 0.30, ZR + 0.04, seg=32, matrix=Matrix.Translation((x, 0, 0)))
    sp = C.mesh_obj("Spigots", bm, [shell_m])
    out.append(C.finalize(sp, angle=40))
    # ribbed black cap with level-sensor plug
    zt = ZR + RH + 0.08
    P = [(0.0, zt, 0), (0.235, zt, 0), (0.245, zt + 0.02, 0), (0.245, zt + 0.15, 0), (0.225, zt + 0.17, 0), (0.0, zt + 0.17, 0)]
    cap = C.lathe("Cap", P, [cap_m], steps=144,
                  mod=lambda r, z, t: r + (0.012 * (0.5 + 0.5 * math.copysign(1, math.cos(18 * t))) if r > 0.24 else 0))
    cap.matrix_world = Matrix.Translation((RX + 0.22, 0.03, 0))
    out.append(C.finalize(cap, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.18, 0.12, 0.13, center=(RX + 0.22, 0.03, zt + 0.23))
    C.box_bm(bm, 0.07, 0.07, 0.06, center=(RX + 0.22, 0.03, zt + 0.15))
    pl = C.mesh_obj("SensorPlug", bm, [cap_m])
    C.add_bevel(pl, 0.015, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    return out


valve_m = None


def build():
    global valve_m
    paint = C.mat_paint("ServoBlack", (0.025, 0.025, 0.027, 1), rough=0.40, coat=0.15)
    C.add_noise_bump(paint, scale=300, strength=0.05, distance=0.001, rough_var=0.05)
    alu = C.principled("CastAlu", (0.50, 0.50, 0.49), metallic=1.0, rough=0.42)
    C.add_noise_bump(alu, scale=380, strength=0.10, distance=0.001, rough_var=0.08)
    zinc = C.principled("ZincSteel", (0.64, 0.62, 0.56), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    rubber = C.mat_rubber()
    valve_m = C.mat_black_plastic("ValvePA", rough=0.4, color=0.03)
    shell = C.principled("ReservoirPP", (0.93, 0.91, 0.84), rough=0.42, IOR=1.49)
    C._set(next(n for n in shell.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Transmission Weight", 0.85)
    C.add_noise_bump(shell, scale=500, strength=0.05, distance=0.0005)
    fluid = C.principled("BrakeFluid", (0.95, 0.70, 0.30), rough=0.05, IOR=1.45)
    C._set(next(n for n in fluid.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Transmission Weight", 1.0)
    cap = C.mat_black_plastic("CapPP", rough=0.42, color=0.025)
    objs = servo(paint, zinc, rubber) + master(alu, zinc, rubber) + reservoir(shell, fluid, cap)
    C.transform_all(objs, Matrix.Rotation(math.radians(-102), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("pompa-freno", objs, "pompa-freno.py",
            "brake master cylinder with vacuum servo: black servo drum, aluminium master cylinder, translucent fluid reservoir with cap, rear studs and pushrod",
            az=35, el=22, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
