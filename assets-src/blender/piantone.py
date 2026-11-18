"""Electric power steering column (piantone sterzo elettrico): black e-coated column jacket
with the splined, threaded top shaft, cast steering-lock housing, stamped upper mounting
bracket with slotted flanges and the tilt lever with its plastic grip; at the bottom the
cast-aluminium EPS gearbox (worm-wheel housing + worm housing) with the electric motor,
its black end cap and connectors, and the intermediate shaft with two universal joints
ending in a pinch-bolt yoke.

Built along +Z (gearbox at the bottom, wheel end at the top), then laid diagonally.
Units ~ decimetres (column ~55 cm, with intermediate shaft ~80 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RJ = 0.27            # jacket radius
Z_GB0, Z_GB1 = 0.55, 1.15   # gearbox span
Z_TOP = 4.85         # top of jacket
BEND = math.radians(30)     # intermediate shaft angle


def mat_cast_alu(name, base=0.42, rough=0.45, grain=480.0, wear=0.35):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 5.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.80, base * 0.80, base * 0.78, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.05, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.75, 0.75, 0.75, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.07
    rr.inputs["To Max"].default_value = rough - 0.07
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def ecoat(name, color=0.03, rough=0.42, wear=0.6):
    """black e-coat on steel with slightly rubbed edges."""
    m = C.mat_paint(name, (color, color, color * 1.05, 1), rough=rough, coat=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    em = C.edge_mask(nt, 0.01, 5.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 14.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.65
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    f2 = nt.nodes.new("ShaderNodeMath")
    f2.operation = "MULTIPLY"
    f2.inputs[1].default_value = wear
    nt.links.new(f.outputs[0], f2.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f2.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (color, color, color * 1.05, 1)
    mix.inputs["B"].default_value = (0.40, 0.40, 0.41, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(f2.outputs[0], b.inputs["Metallic"])
    C.add_noise_bump(m, scale=600, strength=0.05, distance=0.0005)
    return m


def axis_matrix(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def fin(ob, bevel=None, angle=35):
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


# ----------------------------------------------------------------- column
def column(paint, mach, spl, thread, alu, zinc, chrome, black):
    out = []
    P = [(0.0, Z_GB1 - 0.05, 0), (RJ, Z_GB1 - 0.05, 0), (RJ, Z_TOP - 0.25, 0), (RJ + 0.02, Z_TOP - 0.22, 0),
         (RJ + 0.02, Z_TOP - 0.05, 0), (RJ - 0.01, Z_TOP, 0), (0.0, Z_TOP, 0)]
    out.append(fin(C.lathe("Jacket", P, [paint], steps=96), angle=40))
    # top bearing seal + splined shaft + thread
    P = [(0.0, Z_TOP - 0.01, 0), (0.17, Z_TOP - 0.01, 0), (0.17, Z_TOP + 0.04, 0), (0.0, Z_TOP + 0.04, 0)]
    out.append(fin(C.lathe("TopSeal", P, [black], steps=64), angle=40))
    def sp(r, z, t):
        if abs(r - 0.105) > 1e-6:
            return r
        return r - 0.012 * (1 - (max(-1.0, min(1.0, math.cos(36 * t) * 2.5)) * 0.5 + 0.5))
    z = Z_TOP + 0.04
    P = [(0.0, z, 0), (0.12, z, 0), (0.12, z + 0.08, 1), (0.105, z + 0.10, 0), (0.105, z + 0.42, 0),
         (0.09, z + 0.44, 0), (0.0, z + 0.44, 0)]
    out.append(fin(C.lathe("TopShaft", P, [spl, mach], steps=36 * 8, mod=sp), angle=40))
    P = [(0.0, z + 0.43, 0), (0.066, z + 0.43, 0)]
    zz = z + 0.445
    while zz < z + 0.65:
        P += [(0.077, zz, 0), (0.066, zz + 0.0075, 0)]
        zz += 0.015
    P += [(0.066, z + 0.67, 0), (0.056, z + 0.68, 0), (0.0, z + 0.68, 0)]
    out.append(fin(C.lathe("TopThread", P, [thread], steps=48), angle=60))
    # steering-lock housing (cast) on the -Y side, near the top
    zl = Z_TOP - 0.62
    P = [(0.0, zl - 0.26, 0), (RJ + 0.07, zl - 0.26, 0), (RJ + 0.10, zl - 0.22, 0), (RJ + 0.10, zl + 0.22, 0),
         (RJ + 0.07, zl + 0.26, 0), (0.0, zl + 0.26, 0)]
    out.append(fin(C.lathe("LockCollar", P, [alu], steps=96), bevel=0.008))
    T = axis_matrix(Vector((0, -0.10, zl)), Vector((0, -1, 0.35)))
    P = [(0.0, 0.0, 0), (0.18, 0.0, 0), (0.18, 0.40, 0), (0.17, 0.43, 0), (0.0, 0.43, 0)]
    lb = C.lathe("LockBarrel", P, [alu], steps=64)
    lb.matrix_world = T
    out.append(fin(lb, bevel=0.01))
    P = [(0.0, 0.42, 0), (0.14, 0.42, 0), (0.14, 0.46, 0), (0.12, 0.475, 0), (0.0, 0.475, 0)]
    lf = C.lathe("LockFace", P, [chrome], steps=64)
    lf.matrix_world = T
    out.append(fin(lf))
    bm = bmesh.new()
    C.box_bm(bm, 0.10, 0.018, 0.04, center=(0, 0, 0.48))
    ks = C.mesh_obj("KeySlot", bm, [black])
    ks.matrix_world = T
    out.append(fin(ks))
    return out


def bracket(steel, zinc, grip):
    out = []
    # saddle on the -X side (becomes the top once laid down), flanges spread in Y
    z0, z1 = 2.55, 3.65
    R = RJ + 0.03
    zc = (z0 + z1) / 2
    xt = -R - 0.13                       # top plate plane (above the jacket once laid down)
    bm = bmesh.new()
    C.box_bm(bm, 0.04, 1.60, z1 - z0, center=(xt, 0, zc))
    # pressed stiffening ribs along the plate
    for sy in (-0.30, 0.30):
        C.box_bm(bm, 0.05, 0.08, (z1 - z0) * 0.8, center=(xt - 0.02, sy, zc))
    sd = C.mesh_obj("TopPlate", bm, [steel])
    bm = bmesh.new()
    for sy in (-0.62, 0.62):
        for dz in (-0.06, -0.03, 0.0, 0.03, 0.06):
            M = Matrix.Translation((xt, sy, zc + dz)) @ Matrix.Rotation(math.radians(90), 4, "Y")
            C.cyl_bm(bm, 0.055, -0.2, 0.2, seg=24, matrix=M)
    cut = C.mesh_obj("Slots", bm, [steel])
    C.add_boolean(sd, cut)
    C.add_bevel(sd, 0.008, segments=2, angle=30)
    out.append(C.finalize(sd, angle=35, remove=[cut]))
    # side cheeks bent down either side of the jacket
    for sy in (-1, 1):
        bm = bmesh.new()
        C.box_bm(bm, 0.20 - xt, 0.035, (z1 - z0) * 0.55, center=((xt + 0.20) / 2, sy * (R + 0.04), zc))
        pl = C.mesh_obj("Cheek", bm, [steel])
        out.append(fin(pl, bevel=0.01))
    # tilt clamp bolt through the cheeks + lever with grip on the +X side
    bm = bmesh.new()
    M = Matrix.Translation((0.18, 0, zc)) @ Matrix.Rotation(math.radians(90), 4, "X")
    C.cyl_bm(bm, 0.035, -0.50, 0.50, seg=20, matrix=M)
    C.cyl_bm(bm, 0.08, 0.44, 0.50, seg=6, matrix=M)
    bo = C.mesh_obj("ClampBolt", bm, [zinc])
    out.append(fin(bo, bevel=0.006))
    frames = []
    n = 12
    for i in range(n + 1):
        u = i / n
        P = Vector((0.18 + 0.55 * u, -0.40, zc - 0.95 * u))
        sec = [(-0.06, -0.018), (0.06, -0.018), (0.06, 0.018), (-0.06, 0.018)]
        Tn = Vector((0.55, 0, -0.95)).normalized()
        frames.append((P, Tn.cross(Vector((0, 1, 0))).normalized(), Vector((0, 1, 0)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    lv = C.mesh_obj("Lever", bm, [steel])
    out.append(fin(lv, bevel=0.008))
    Tg = axis_matrix(Vector((0.18 + 0.55 * 0.55, -0.40, zc - 0.95 * 0.55)), Vector((0.55, 0, -0.95)))
    P = [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.085, 0.05, 0), (0.085, 0.45, 0), (0.07, 0.52, 0), (0.0, 0.54, 0)]
    gp = C.lathe("Grip", P, [grip], steps=48)
    gp.matrix_world = Tg @ Matrix.Diagonal((1.0, 0.7, 1.0, 1.0))
    out.append(fin(gp))
    return out


# ----------------------------------------------------------------- EPS unit
def eps(alu, can, cap, black, zinc):
    out = []
    # worm-wheel housing, coaxial with the column
    P = [(0.0, Z_GB0, 0), (0.40, Z_GB0, 0), (0.50, Z_GB0 + 0.05, 0), (0.54, Z_GB0 + 0.14, 0),
         (0.54, Z_GB1 - 0.18, 0), (0.48, Z_GB1 - 0.08, 0), (0.36, Z_GB1, 0), (0.30, Z_GB1 + 0.06, 0),
         (0.30, Z_GB1 + 0.14, 0), (0.0, Z_GB1 + 0.14, 0)]
    out.append(fin(C.lathe("WheelHousing", P, [alu], steps=128), bevel=0.008))
    # cover bolts on the lower face
    bm = bmesh.new()
    for k in range(4):
        th = math.tau * k / 4 + 0.4
        M = Matrix.Translation((0.44 * math.cos(th), 0.44 * math.sin(th), Z_GB0)) @ Matrix.Rotation(math.pi, 4, "X")
        C.cyl_bm(bm, 0.045, -0.005, 0.05, seg=6, matrix=M)
    cb = C.mesh_obj("CoverBolts", bm, [zinc])
    out.append(fin(cb, bevel=0.005))
    # worm housing tangential along +X (hangs below once laid down), offset toward -Y
    zc = (Z_GB0 + Z_GB1) / 2 - 0.02
    Tw = axis_matrix(Vector((0.0, -0.30, zc)), Vector((1, 0, 0)))
    P = [(0.0, -0.55, 0), (0.18, -0.55, 0), (0.22, -0.50, 0), (0.22, 0.45, 0), (0.30, 0.50, 0),
         (0.30, 0.58, 0), (0.0, 0.58, 0)]
    wh = C.lathe("WormHousing", P, [alu], steps=64)
    wh.matrix_world = Tw
    out.append(fin(wh, bevel=0.008))
    # motor flange, can, end cap
    P = [(0.0, 0.56, 0), (0.40, 0.56, 0), (0.40, 0.62, 0), (0.0, 0.62, 0)]
    fl = C.lathe("MotorFlange", P, [alu], steps=96)
    fl.matrix_world = Tw
    out.append(fin(fl, bevel=0.006))
    P = [(0.0, 0.61, 0), (0.36, 0.61, 0), (0.37, 0.63, 0), (0.37, 1.38, 0), (0.35, 1.41, 0), (0.0, 1.41, 0)]
    mc = C.lathe("MotorCan", P, [can], steps=96)
    mc.matrix_world = Tw
    out.append(fin(mc, angle=40))
    P = [(0.0, 1.40, 0), (0.33, 1.40, 0), (0.34, 1.44, 0), (0.30, 1.52, 0), (0.18, 1.56, 0), (0.0, 1.56, 0)]
    ec = C.lathe("EndCap", P, [cap], steps=96)
    ec.matrix_world = Tw
    out.append(fin(ec, angle=40))
    # flange bolts
    bm = bmesh.new()
    for k in range(2):
        th = math.pi * k + math.pi / 2
        C.cyl_bm(bm, 0.04, 0.62, 0.67, seg=6, matrix=Matrix.Translation((0.34 * math.cos(th), 0.34 * math.sin(th), 0)))
    fb = C.mesh_obj("FlangeBolts", bm, [zinc])
    fb.matrix_world = Tw
    out.append(fin(fb, bevel=0.005))
    # motor power connector on top of the can + torque-sensor connector on the housing
    bm = bmesh.new()
    C.box_bm(bm, 0.24, 0.20, 0.30, center=(-0.40, 0.0, 1.05))
    C.box_bm(bm, 0.10, 0.06, 0.18, center=(-0.53, 0.0, 1.05))
    pc = C.mesh_obj("PowerConn", bm, [black])
    pc.matrix_world = Tw
    out.append(fin(pc, bevel=0.015))
    bm = bmesh.new()
    C.box_bm(bm, 0.26, 0.16, 0.14, center=(-0.52, -0.18, Z_GB1 - 0.10))
    C.box_bm(bm, 0.08, 0.05, 0.10, center=(-0.52, -0.27, Z_GB1 - 0.05))
    tc = C.mesh_obj("SensorConn", bm, [black])
    out.append(fin(tc, bevel=0.012))
    # cast mounting lug on the housing (-X side, i.e. top once laid down)
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.50, 0.28, center=(-0.56, 0.12, zc))
    lg = C.mesh_obj("Lug", bm, [alu])
    bm = bmesh.new()
    C.cyl_bm(bm, 0.06, -0.3, 0.3, seg=24, matrix=Matrix.Translation((-0.62, 0.12, zc)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    cut = C.mesh_obj("LugHole", bm, [alu])
    C.add_boolean(lg, cut)
    C.add_bevel(lg, 0.02, segments=2, angle=30)
    out.append(C.finalize(lg, angle=35, remove=[cut]))
    # output shaft
    P = [(0.0, 0.20, 0), (0.10, 0.20, 0), (0.10, Z_GB0 + 0.02, 0), (0.0, Z_GB0 + 0.02, 0)]
    out.append(fin(C.lathe("OutShaft", P, [zinc], steps=48), angle=40))
    return out


# ----------------------------------------------------------------- universal joints
def yoke(M, forged, cap_m, clamp=False):
    """fork opening toward local +Z, pins along local X, cross centre at origin."""
    out = []
    bm = bmesh.new()
    if clamp:
        C.box_bm(bm, 0.26, 0.26, 0.40, center=(0, 0, -0.42))
    else:
        C.cyl_bm(bm, 0.13, -0.50, -0.20, seg=40)
    C.box_bm(bm, 0.36, 0.20, 0.08, center=(0, 0, -0.21))
    for sx in (-1, 1):
        C.box_bm(bm, 0.07, 0.20, 0.24, center=(sx * 0.155, 0, -0.10))
        C.cyl_bm(bm, 0.10, -0.035, 0.035, seg=32,
                 matrix=Matrix.Translation((sx * 0.155, 0, 0.0)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    ob = C.mesh_obj("Yoke", bm, [forged])
    ob.matrix_world = M
    if clamp:
        bm = bmesh.new()
        C.box_bm(bm, 0.03, 0.40, 0.40, center=(0, 0.12, -0.45))
        C.cyl_bm(bm, 0.09, -0.80, -0.30, seg=32)
        cut = C.mesh_obj("Slot", bm, [forged])
        cut.matrix_world = M
        C.add_boolean(ob, cut)
        C.add_bevel(ob, 0.012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
        bm = bmesh.new()
        Mb = Matrix.Translation((0, 0.12, -0.45)) @ Matrix.Rotation(math.radians(90), 4, "Y")
        C.cyl_bm(bm, 0.03, -0.20, 0.20, seg=16, matrix=Mb)
        C.cyl_bm(bm, 0.065, 0.13, 0.19, seg=6, matrix=Mb)
        C.cyl_bm(bm, 0.065, -0.19, -0.13, seg=6, matrix=Mb)
        b = C.mesh_obj("PinchBolt", bm, [cap_m])
        b.matrix_world = M
        out.append(fin(b, bevel=0.005))
    else:
        C.add_bevel(ob, 0.012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    # bearing cups pressed into the ears
    bm = bmesh.new()
    for sx in (-1, 1):
        C.cyl_bm(bm, 0.055, -0.03, 0.03, seg=24,
                 matrix=Matrix.Translation((sx * 0.20, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    cp = C.mesh_obj("Cups", bm, [cap_m])
    cp.matrix_world = M
    out.append(fin(cp, bevel=0.004))
    return out


def ujoint(M, forged, cap_m, clamp_second=False):
    """M places the joint centre; first yoke comes from -Z, second continues along +Z
    bent by BEND about local Y."""
    out = yoke(M, forged, cap_m)
    bm = bmesh.new()
    C.cyl_bm(bm, 0.045, -0.15, 0.15, seg=20, matrix=Matrix.Rotation(math.radians(90), 4, "Y"))
    C.cyl_bm(bm, 0.045, -0.15, 0.15, seg=20, matrix=Matrix.Rotation(math.radians(90), 4, "X"))
    bmesh.ops.create_cube(bm, size=0.11)
    cr = C.mesh_obj("Cross", bm, [cap_m])
    cr.matrix_world = M
    out.append(fin(cr))
    M2 = M @ Matrix.Rotation(BEND, 4, "Y") @ Matrix.Rotation(math.pi, 4, "X") @ Matrix.Rotation(math.radians(90), 4, "Z")
    out += yoke(M2, forged, cap_m, clamp=clamp_second)
    return out, M @ Matrix.Rotation(BEND, 4, "Y")


def intermediate(forged, cap_m, shaft_m, rubber):
    out = []
    M1 = Matrix.Translation((0, 0, 0.05)) @ Matrix.Rotation(math.pi, 4, "X")   # joint opening downward
    j, Mo = ujoint(M1, forged, cap_m)
    out += j
    # shaft (tube + telescopic inner) along Mo's +Z
    L = 2.0
    P = [(0.0, 0.45, 0), (0.12, 0.45, 0), (0.12, 1.35, 0), (0.10, 1.38, 0), (0.0, 1.38, 0)]
    t = C.lathe("ShaftTube", P, [shaft_m], steps=48)
    t.matrix_world = Mo
    out.append(fin(t, angle=40))
    P = [(0.0, 1.30, 0), (0.085, 1.30, 0), (0.085, L - 0.45, 0), (0.0, L - 0.45, 0)]
    t = C.lathe("ShaftInner", P, [shaft_m], steps=48)
    t.matrix_world = Mo
    out.append(fin(t, angle=40))
    # small rubber dust boot at the slip joint
    P = [(0.0, 1.30, 0), (0.135, 1.30, 0), (0.14, 1.36, 0), (0.12, 1.40, 0), (0.135, 1.44, 0), (0.10, 1.50, 0), (0.09, 1.52, 0), (0.0, 1.52, 0)]
    t = C.lathe("SlipBoot", P, [rubber], steps=48)
    t.matrix_world = Mo
    out.append(fin(t, angle=50))
    # second joint, opening back toward the shaft, then pinch yoke continuing
    M2 = Mo @ Matrix.Translation((0, 0, L))
    j2, _ = ujoint(M2 @ Matrix.Rotation(math.radians(90), 4, "Z"), forged, cap_m, clamp_second=True)
    out += j2
    return out


def build():
    paint = ecoat("ColumnEcoat", 0.03, 0.42)
    steel = C.principled("BracketZinc", (0.50, 0.51, 0.52), metallic=1.0, rough=0.34)
    C.add_noise_bump(steel, scale=500, strength=0.05, distance=0.0006, rough_var=0.08)
    alu = mat_cast_alu("GearboxAlu", base=0.40, rough=0.42)
    can = C.principled("MotorCan", (0.58, 0.59, 0.61), metallic=1.0, rough=0.30)
    C.add_noise_bump(can, scale=700, strength=0.04, distance=0.0005, rough_var=0.06)
    cap = C.mat_black_plastic("EndCapPBT", rough=0.45, color=0.03)
    black = C.mat_black_plastic("ConnPA", rough=0.42, color=0.02)
    grip = C.mat_black_plastic("Grip", rough=0.62, color=0.03)
    zinc = C.principled("Zinc", (0.66, 0.67, 0.69), metallic=1.0, rough=0.24)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005)
    mach = C.mat_machined("Machined", color=0.60, rough=0.18, rings=1400)
    spl = C.principled("Splines", (0.46, 0.46, 0.47), metallic=1.0, rough=0.26)
    C.add_noise_bump(spl, scale=700, strength=0.04, distance=0.0005, rough_var=0.05)
    thread = C.principled("Thread", (0.52, 0.52, 0.53), metallic=1.0, rough=0.3)
    tn = thread.node_tree
    wv = tn.nodes.new("ShaderNodeTexWave")
    wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = 70.0
    tn.links.new(C._coord(tn), wv.inputs["Vector"])
    bp = tn.nodes.new("ShaderNodeBump")
    tn.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    tn.links.new(bp.outputs["Normal"], next(n for n in tn.nodes if n.type == "BSDF_PRINCIPLED").inputs["Normal"])
    chrome = C.mat_chrome()
    forged = C.mat_cast_iron("ForgedYoke", rust=0.2, base=0.16)
    cap_m = C.principled("BrightSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.25)
    shaft_m = C.principled("ShaftSteel", (0.22, 0.22, 0.225), metallic=1.0, rough=0.36)
    C.add_noise_bump(shaft_m, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    rubber = C.mat_rubber("Boot")

    objs = column(paint, mach, spl, thread, alu, zinc, chrome, black)
    objs += bracket(steel, zinc, grip)
    objs += eps(alu, can, cap, black, zinc)
    objs += intermediate(forged, cap_m, shaft_m, rubber)
    # lay it down: column axis to the right and slightly up, -X side (bracket) on top
    C.transform_all(objs, Matrix.Rotation(math.radians(-24), 4, "Z") @ Matrix.Rotation(math.radians(72), 4, "Y"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("piantone", objs, "piantone.py",
            "electric power steering column: black column jacket with splined top shaft, lock housing, "
            "mounting bracket and tilt lever, cast EPS gearbox with electric motor and connectors, "
            "intermediate shaft with two universal joints",
            az=22, el=24, lens=70, fill=0.88, samples=S, res=(R, R))
