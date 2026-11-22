"""Propeller shaft (albero di trasmissione / cardano), two-piece type as removed from a
small rear-wheel-drive car: black-painted steel tubes with weld beads and balance
weights, a forged universal joint at each end (yokes, needle-bearing cups, spider)
carrying a four-hole companion flange, and in the middle the centre support bearing
(rubber donut in a stamped black bracket with two bolt ears) next to the splined slip
joint with its rubber boot.

Shaft axis along +X; units ~ decimetres (~1.5 m long)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # local Z -> world +X
RYn = Matrix.Rotation(math.radians(-90), 4, "Y")    # local Z -> world -X
S = 2.4             # universal joint scale (relative to the steering-column joint)
RT = 0.32           # tube radius


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def xlathe(name, prof, mats, steps=96, bevel=None, angle=40, cutters=(), M=RY):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M.copy()
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def ecoat(name, color=0.03, rough=0.42, wear=0.6):
    """black paint on steel with slightly rubbed edges."""
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
    f = nt.nodes.new("ShaderNodeMath"); f.operation = "MULTIPLY"; f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"
    f2.inputs[1].default_value = wear
    nt.links.new(f.outputs[0], f2.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(f2.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (color, color, color * 1.05, 1)
    mix.inputs["B"].default_value = (0.40, 0.40, 0.41, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(f2.outputs[0], b.inputs["Metallic"])
    C.add_noise_bump(m, scale=500, strength=0.05, distance=0.0005)
    return m


# ----------------------------------------------------------------- universal joints
def yoke(M, forged, cap_m, flange_m=None):
    """fork opening toward local +Z, pins along local X, cross centre at origin.
    flange_m: if given the yoke base is a 4-hole companion flange, else a tube neck."""
    out = []
    s = S
    bm = bmesh.new()
    C.box_bm(bm, 0.36 * s, 0.22 * s, 0.09 * s, center=(0, 0, -0.215 * s))
    for sx in (-1, 1):
        C.box_bm(bm, 0.07 * s, 0.20 * s, 0.26 * s, center=(sx * 0.155 * s, 0, -0.10 * s))
        C.cyl_bm(bm, 0.10 * s, -0.035 * s, 0.035 * s, seg=40,
                 matrix=Matrix.Translation((sx * 0.155 * s, 0, 0.0)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    ob = C.mesh_obj("Yoke", bm, [forged])
    ob.matrix_world = M
    out.append(fin(ob, bevel=0.03, seg=3))
    # neck
    P = [(0.0, -0.50 * s, 0), (0.13 * s, -0.50 * s, 0), (0.14 * s, -0.30 * s, 0), (0.12 * s, -0.24 * s, 0),
         (0.0, -0.24 * s, 0)]
    ob = C.lathe("YokeNeck", P, [forged], steps=64)
    ob.matrix_world = M
    out.append(fin(ob, bevel=0.01))
    if flange_m is not None:
        z0, z1 = -0.62 * s, -0.50 * s
        P = [(0.0, z0, 0), (0.44, z0, 0), (0.46, z0 + 0.02, 0), (0.46, z1 - 0.02, 0), (0.44, z1, 0), (0.0, z1, 0)]
        ob = C.lathe("CompanionFlange", P, [flange_m], steps=128)
        ob.matrix_world = M
        bm = bmesh.new()
        for k in range(4):
            a = math.tau * k / 4 + math.pi / 4
            C.cyl_bm(bm, 0.05, z0 - 0.1, z1 + 0.1, seg=24, matrix=Matrix.Translation((0.33 * math.cos(a), 0.33 * math.sin(a), 0)))
        cut = C.mesh_obj("FlHoles", bm, [])
        cut.matrix_world = M
        out.append(fin(ob, bevel=0.008, cutters=[cut]))
        # centring spigot
        P = [(0.0, z0 - 0.05, 0), (0.12, z0 - 0.05, 0), (0.13, z0, 0), (0.0, z0, 0)]
        ob = C.lathe("Spigot", P, [flange_m], steps=48)
        ob.matrix_world = M
        out.append(fin(ob))
    # bearing cups pressed into the ears, with circlips
    for sx in (-1, 1):
        Mc = M @ Matrix.Translation((sx * 0.19 * s, 0, 0)) @ Matrix.Rotation(sx * math.radians(90), 4, "Y")
        P = [(0.0, -0.03 * s, 0), (0.058 * s, -0.03 * s, 0), (0.058 * s, 0.03 * s, 0), (0.05 * s, 0.035 * s, 0),
             (0.0, 0.035 * s, 0)]
        ob = C.lathe("Cup", P, [cap_m], steps=40)
        ob.matrix_world = Mc
        out.append(fin(ob))
    return out


def ujoint(xj, forged, cap_m, flange_side=None, flange_m=None):
    """joint centred at x=xj. flange_side = -1/+1: which yoke carries the flange."""
    out = []
    MA = Matrix.Translation((xj, 0, 0)) @ RY                                   # opens toward +X (base at -X)
    MB = Matrix.Translation((xj, 0, 0)) @ RYn @ Matrix.Rotation(math.pi / 2, 4, "Z")   # opens toward -X
    out += yoke(MA, forged, cap_m, flange_m if flange_side == -1 else None)
    out += yoke(MB, forged, cap_m, flange_m if flange_side == 1 else None)
    # spider
    s = S
    bm = bmesh.new()
    C.cyl_bm(bm, 0.045 * s, -0.17 * s, 0.17 * s, seg=20, matrix=Matrix.Rotation(math.radians(90), 4, "Y"))
    C.cyl_bm(bm, 0.045 * s, -0.17 * s, 0.17 * s, seg=20, matrix=Matrix.Rotation(math.radians(90), 4, "X"))
    C.box_bm(bm, 0.13 * s, 0.13 * s, 0.13 * s)
    ob = C.mesh_obj("Spider", bm, [cap_m])
    ob.matrix_world = MA
    out.append(fin(ob, bevel=0.02))
    # grease nipple on the spider body
    P = [(0.0, 0.0, 0), (0.03, 0.0, 0), (0.03, 0.08, 0), (0.045, 0.09, 0), (0.045, 0.12, 0), (0.0, 0.14, 0)]
    ob = C.lathe("Nipple", P, [cap_m], steps=24)
    ob.matrix_world = MA @ Matrix.Rotation(math.radians(45), 4, "Z") @ Matrix.Translation((0, 0, 0.065 * s)) @ Matrix.Rotation(math.radians(0), 4, "X")
    out.append(fin(ob))
    return out


# ----------------------------------------------------------------- tubes, centre bearing
def tube(x0, x1, paint, weld_m, swage0=None, swage1=None):
    """painted tube from x0 to x1; swage = radius the tube end necks down to."""
    out = []
    P = [(0.0, x0, 0)]
    if swage0:
        P += [(swage0, x0, 0), (swage0, x0 + 0.12, 0), (RT, x0 + 0.40, 0)]
    else:
        P += [(RT, x0, 0)]
    if swage1:
        P += [(RT, x1 - 0.40, 0), (swage1, x1 - 0.12, 0), (swage1, x1, 0)]
    else:
        P += [(RT, x1, 0)]
    P += [(0.0, x1, 0)]
    out.append(xlathe("Tube", P, [paint], steps=96, angle=30))
    # weld beads at both ends
    for x, r in ((x0, swage0 or RT), (x1, swage1 or RT)):
        P = [(r - 0.01, x - 0.04, 0), (r + 0.012, x - 0.03, 0), (r + 0.022, x, 0), (r + 0.012, x + 0.03, 0), (r - 0.01, x + 0.04, 0)]
        out.append(xlathe("Weld", P, [weld_m], steps=96, angle=60))
    return out


def balance_weights(xs, paint):
    bm = bmesh.new()
    for (x, a) in xs:
        M = Matrix.Rotation(a, 4, "X") @ Matrix.Translation((x, 0, RT + 0.005))
        C.box_bm(bm, 0.26, 0.20, 0.03, matrix=M)
    return [fin(C.mesh_obj("BalanceWeights", bm, [paint]), bevel=0.008)]


def centre_bearing(xc, rubber, bracket_m, steel, mach):
    out = []
    # stub shaft through the bearing
    out.append(xlathe("Stub", [(0.0, xc - 0.70, 0), (0.17, xc - 0.70, 0), (0.17, xc + 0.62, 0), (0.0, xc + 0.62, 0)],
                      [mach], steps=64))
    # bearing inner race / dust shields
    for d in (-0.13, 0.13):
        P = [(0.16, xc + d - 0.02, 0), (0.30, xc + d - 0.02, 0), (0.30, xc + d + 0.02, 0), (0.16, xc + d + 0.02, 0)]
        out.append(xlathe("Shield", P, [steel], steps=64))
    # rubber donut with a convoluted face
    P = [(0.29, xc - 0.12, 0), (0.38, xc - 0.16, 0), (0.46, xc - 0.10, 0), (0.54, xc - 0.16, 0), (0.62, xc - 0.16, 0),
         (0.62, xc + 0.16, 0), (0.54, xc + 0.16, 0), (0.46, xc + 0.10, 0), (0.38, xc + 0.16, 0), (0.29, xc + 0.12, 0)]
    out.append(xlathe("Donut", P, [rubber], steps=128, bevel=0.01, angle=50))
    # stamped bracket: ring strap round the donut + flat top plate with two bolt ears (+Z side)
    P = [(0.62, xc - 0.17, 0), (0.67, xc - 0.17, 0), (0.67, xc + 0.17, 0), (0.62, xc + 0.17, 0)]
    out.append(xlathe("Strap", P, [bracket_m], steps=128, bevel=0.008))
    bm = bmesh.new()
    C.box_bm(bm, 0.34, 1.90, 0.05, center=(xc, 0, 0.70))
    for sy in (-1, 1):
        C.box_bm(bm, 0.34, 0.05, 0.22, center=(xc, sy * 0.52, 0.58))
    cb = bmesh.new()
    for sy in (-1, 1):
        C.cyl_bm(cb, 0.06, 0.5, 0.9, seg=32, matrix=Matrix.Translation((xc, sy * 0.80, 0)))
    out.append(fin(C.mesh_obj("Bracket", bm, [bracket_m]), bevel=0.012, cutters=[C.mesh_obj("BrHoles", cb, [])]))
    # stiffening flanges bent down along the plate edges
    bm = bmesh.new()
    for sx in (-1, 1):
        C.box_bm(bm, 0.04, 1.90, 0.12, center=(xc + sx * 0.15, 0, 0.64))
    out.append(fin(C.mesh_obj("BrFlanges", bm, [bracket_m]), bevel=0.01))
    return out


def slip_joint(x0, x1, mach, rubber, clamp_m, paint):
    out = []
    # splined shaft (visible ridges), sleeve, boot with clamps
    def spl(r, z, t):
        if r < 0.149:
            return r
        return r - 0.015 * (1 if math.cos(16 * t) < 0 else 0)
    ob = C.lathe("Spline", [(0.0, x0, 0), (0.16, x0, 0), (0.16, x0 + 0.35, 0), (0.0, x0 + 0.35, 0)], [mach], steps=16 * 8, mod=spl)
    ob.matrix_world = RY.copy()
    out.append(fin(ob, angle=30))
    P = [(0.0, x0 + 0.2, 0), (0.19, x0 + 0.2, 0), (0.23, x0 + 0.26, 0), (0.25, x0 + 0.34, 0), (0.20, x0 + 0.40, 0),
         (0.25, x0 + 0.46, 0), (0.20, x0 + 0.52, 0), (0.25, x0 + 0.58, 0), (0.21, x0 + 0.66, 0), (0.0, x0 + 0.66, 0)]
    out.append(xlathe("SlipBoot", P, [rubber], steps=96, angle=50))
    for x, r in ((x0 + 0.24, 0.215), (x0 + 0.63, 0.225)):
        P = [(r - 0.01, x - 0.025, 0), (r + 0.012, x - 0.025, 0), (r + 0.016, x, 0), (r + 0.012, x + 0.025, 0), (r - 0.01, x + 0.025, 0)]
        out.append(xlathe("BootClamp", P, [clamp_m], steps=96))
    P = [(0.0, x0 + 0.62, 0), (0.27, x0 + 0.62, 0), (0.29, x0 + 0.66, 0), (0.29, x1, 0), (0.0, x1, 0)]
    out.append(xlathe("SlipSleeve", P, [paint], steps=96, bevel=0.008))
    return out


def build():
    paint = ecoat("TubePaint", 0.028, 0.40, 0.7)
    forged = C.mat_cast_iron("ForgedYoke", rust=0.25, base=0.14)
    cap_m = C.principled("BrightSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.26)
    C.add_noise_bump(cap_m, scale=800, strength=0.03, distance=0.0005)
    flange_m = C.mat_machined("FlangeSteel", color=0.44, rough=0.30, rings=600)
    weld_m = C.principled("Weld", (0.06, 0.055, 0.05), metallic=0.8, rough=0.5)
    C.add_noise_bump(weld_m, scale=120, strength=0.5, distance=0.004)
    rubber = C.mat_rubber("Rubber")
    bracket_m = ecoat("BracketPaint", 0.03, 0.45, 0.5)
    steel = C.principled("Zinc", (0.62, 0.62, 0.60), metallic=1.0, rough=0.28)
    mach = C.mat_machined("Stub", color=0.55, rough=0.22, rings=0)
    objs = []
    objs += ujoint(0.0, forged, cap_m, flange_side=-1, flange_m=flange_m)
    xa = 0.50 * S
    objs += tube(xa, 5.60, paint, weld_m, swage0=0.135 * S, swage1=0.20)
    objs += balance_weights([(1.9, 0.3), (4.9, 2.4)], paint)
    xc = 6.10
    objs += centre_bearing(xc, rubber, bracket_m, steel, mach)
    objs += slip_joint(xc + 0.62, xc + 1.15, mach, rubber, steel, paint)
    xj = 14.0
    objs += tube(xc + 1.15, xj - 0.50 * S, paint, weld_m, swage0=0.29, swage1=0.135 * S)
    objs += balance_weights([(12.3, 1.2)], paint)
    objs += ujoint(xj, forged, cap_m, flange_side=1, flange_m=flange_m)
    C.transform_all(objs, Matrix.Rotation(math.radians(-36), 4, "Z") @ Matrix.Translation((-7.0, 0, 0)))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("albero-trasmissione", objs, "albero-trasmissione.py",
            "two-piece propeller shaft: black steel tubes, universal joints with companion flanges at both ends, "
            "centre support bearing in a stamped bracket, splined slip joint with rubber boot",
            az=0, el=48, lens=70, fill=0.94, **kw)
