"""A/C refrigerant line (tubo aria condizionata) as removed from a small car: bent aluminium
pipe with tight bends between straight runs, a block fitting with bolt hole and capped
O-ring spigot at one end, a service (charging) port with knurled black dust cap brazed
on the pipe, a smooth black rubber barrier-hose section held by two crimped aluminium
ferrules (octagonal crimp flats), a rubber-lined P-clip, and a short pipe ending in a
hex female nut fitting."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 10 cm
PR = 0.080                      # alu pipe radius (16 mm OD)
HR = 0.165                      # hose radius
FRR = 0.205                     # ferrule radius


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


def fillet(pts, R, n=10):
    """polyline with every corner rounded to bend radius R (tube-bender style)"""
    P = [Vector(p) for p in pts]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d0, d1 = (b - a).normalized(), (c - b).normalized()
        ang = d0.angle(d1)
        if ang < 1e-3:
            out.append(b)
            continue
        t = R * math.tan(ang / 2)
        p0, p1 = b - d0 * t, b + d1 * t
        # arc centre: from p0 perpendicular to d0 toward the inside of the bend
        inside = (d1 - d0 * d0.dot(d1)).normalized()
        ctr = p0 + inside * R
        v0, v1 = p0 - ctr, p1 - ctr
        for k in range(n + 1):
            out.append(ctr + v0.slerp(v1, k / n))
    out.append(P[-1])
    return out


def mat_alu(name, base=0.60, rough=0.26):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=300, strength=0.05, distance=0.0008, rough_var=0.08)
    return m


def mat_hose(name="BarrierHose"):
    m = C.principled(name, (0.022, 0.022, 0.023), rough=0.5)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.40
    rr.inputs["To Max"].default_value = 0.66
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    C.add_noise_bump(m, scale=500, strength=0.08, distance=0.0008)
    return m


def oct_mod(a):
    def f(r, z, t):
        if r < FRR - 0.01:
            return r
        q = (t % (math.tau / 8)) - math.tau / 16
        return min(r, a / math.cos(q))
    return f


def hex_mod(a, rmin):
    def f(r, z, t):
        if r < rmin:
            return r
        q = (t % (math.pi / 3)) - math.pi / 6
        return min(r, a / math.cos(q))
    return f


# ----------------------------------------------------------------- parts
def ferrule(name, alu, P, d):
    """crimped sleeve at P with axis d (toward the hose)"""
    L = 0.42
    prof = [(PR - 0.005, -0.06, 0), (PR + 0.03, -0.06, 0), (PR + 0.05, -0.02, 0), (FRR - 0.02, 0.0, 0), (FRR, 0.03, 0)]
    for k in range(3):
        z = 0.08 + k * 0.11
        prof += [(FRR, z, 0), (FRR - 0.018, z + 0.02, 0), (FRR - 0.018, z + 0.05, 0), (FRR, z + 0.07, 0)]
    prof += [(FRR, L - 0.02, 0), (FRR - 0.01, L, 0), (HR - 0.01, L, 0), (HR - 0.01, L - 0.05, 0), (PR - 0.005, L - 0.05, 0)]
    return lathe_at(name, prof, [alu], origin=P, axis=d, steps=96, mod=oct_mod(FRR * 0.955), bevel=0.003)


def block_fitting(alu, cap, rub, steel, P, d):
    out = []
    M = axis_mat(P, d)          # local +Z = pipe direction into the block
    bm = bmesh.new()
    C.box_bm(bm, 0.36, 0.26, 0.30, center=(0.08, 0, -0.10))
    bk = C.mesh_obj("Block", bm, [alu])
    bk.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, 0.045, -1, 1, seg=32, matrix=Matrix.Translation((0.17, 0, -0.10)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    cut = C.mesh_obj("BoltHole", cb, [alu])
    cut.matrix_world = M
    bo = C.add_boolean(bk, cut)
    bo.use_self = True
    C.add_bevel(bk, 0.02, segments=2, angle=30)
    out.append(C.finalize(bk, angle=35, remove=[cut]))
    # male spigot out of the far face (continuing -d), O-ring, plastic cap
    Ms = M @ Matrix.Translation((0, 0, -0.25)) @ Matrix.Rotation(math.pi, 4, "X")
    prof = [(0.0, 0.0, 0), (PR + 0.01, 0.0, 0), (PR + 0.01, 0.06, 0), (PR - 0.01, 0.065, 0), (PR - 0.01, 0.09, 0),
            (PR + 0.01, 0.095, 0), (PR + 0.01, 0.13, 0), (PR - 0.01, 0.14, 0), (0.0, 0.14, 0)]
    sp = C.lathe("Spigot", prof, [alu], steps=48)
    sp.matrix_world = Ms
    out.append(C.finalize(sp, angle=40))
    prof = [(PR - 0.012, 0.066, 0), (PR + 0.016, 0.066, 0), (PR + 0.02, 0.078, 0), (PR + 0.016, 0.09, 0), (PR - 0.012, 0.09, 0)]
    orr = C.lathe("ORing", prof, [rub], steps=48)
    orr.matrix_world = Ms
    out.append(C.finalize(orr, angle=40))
    prof = [(0.0, 0.10, 0), (PR + 0.035, 0.10, 0), (PR + 0.045, 0.11, 0), (PR + 0.045, 0.22, 0), (PR + 0.03, 0.235, 0), (0.0, 0.235, 0)]
    cp = C.lathe("SpigotCap", prof, [cap], steps=48)
    cp.matrix_world = Ms
    C.add_bevel(cp, 0.006, segments=2, angle=30)
    out.append(C.finalize(cp, angle=40))
    # pipe collar where it is brazed into the block
    prof = [(PR - 0.01, 0.04, 0), (PR + 0.03, 0.04, 0), (PR + 0.03, 0.065, 0), (PR, 0.09, 0), (PR - 0.01, 0.09, 0)]
    co = C.lathe("Collar", prof, [alu], steps=48)
    co.matrix_world = M
    out.append(C.finalize(co, angle=40))
    return out


def service_port(alu, cap, P, n):
    out = []
    M = axis_mat(P, n)
    prof = [(0.0, 0.0, 0), (0.115, 0.0, 0), (0.115, 0.05, 0), (0.095, 0.085, 0), (0.075, 0.09, 0), (0.075, 0.12, 0)]
    for k in range(5):
        z = 0.125 + k * 0.022
        prof += [(0.082, z, 0), (0.072, z + 0.011, 0)]
    prof += [(0.072, 0.25, 0), (0.0, 0.25, 0)]
    ob = C.lathe("PortBody", prof, [alu], steps=64)
    ob.matrix_world = M
    out = [C.finalize(ob, angle=40)]
    knurl = lambda r, z, t: r - (0.006 if (r > 0.1 and math.cos(24 * t) > 0.3) else 0)
    prof = [(0.0, 0.17, 0), (0.104, 0.17, 0), (0.108, 0.18, 0), (0.108, 0.33, 0), (0.096, 0.345, 0), (0.0, 0.345, 0)]
    cp = C.lathe("PortCap", prof, [cap], steps=144, mod=knurl)
    cp.matrix_world = M
    C.add_bevel(cp, 0.006, segments=2, angle=30)
    out.append(C.finalize(cp, angle=40))
    # retaining strap tab of the cap
    bm = bmesh.new()
    C.box_bm(bm, 0.05, 0.06, 0.16, center=(0.13, 0, 0.12))
    tb = C.mesh_obj("CapStrap", bm, [cap])
    tb.matrix_world = M
    C.add_bevel(tb, 0.012, segments=1, angle=30)
    out.append(C.finalize(tb, angle=35))
    return out


def nut_end(alu, steel, P, d):
    out = []
    prof = [(PR - 0.01, 0.0, 0), (PR + 0.035, 0.0, 0), (PR + 0.04, 0.03, 0), (PR + 0.02, 0.05, 0), (PR - 0.01, 0.05, 0)]
    out.append(lathe_at("Bead", prof, [alu], origin=P, axis=d, steps=48))
    prof = [(PR + 0.005, 0.06, 0), (0.17, 0.06, 0), (0.19, 0.08, 0), (0.19, 0.26, 0), (0.17, 0.28, 0), (0.115, 0.28, 0), (0.115, 0.20, 0), (PR + 0.005, 0.20, 0)]
    out.append(lathe_at("Nut", prof, [steel], origin=P, axis=d, steps=144, mod=hex_mod(0.165, 0.15)))
    return out


def p_clip(steel, rub, P, d):
    out = []
    prof = [(HR, -0.06, 0), (HR + 0.025, -0.06, 0), (HR + 0.025, 0.06, 0), (HR, 0.06, 0)]
    out.append(lathe_at("ClipLiner", prof, [rub], origin=P, axis=d, steps=64))
    prof = [(HR + 0.025, -0.045, 0), (HR + 0.045, -0.045, 0), (HR + 0.045, 0.045, 0), (HR + 0.025, 0.045, 0)]
    out.append(lathe_at("ClipBand", prof, [steel], origin=P, axis=d, steps=64))
    M = axis_mat(P, d)
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.04, 0.09, center=(HR + 0.18, -0.025, 0))
    C.box_bm(bm, 0.30, 0.04, 0.09, center=(HR + 0.18, 0.025, 0))
    tb = C.mesh_obj("ClipTab", bm, [steel])
    tb.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, 0.03, -1, 1, seg=24, matrix=Matrix.Translation((HR + 0.24, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    cut = C.mesh_obj("ClipHole", cb, [steel])
    cut.matrix_world = M
    bo = C.add_boolean(tb, cut)
    bo.use_self = True
    C.add_bevel(tb, 0.012, segments=1, angle=30)
    out.append(C.finalize(tb, angle=35, remove=[cut]))
    return out


def build():
    alu = mat_alu("PipeAlu", 0.62, 0.24)
    blk = mat_alu("BlockAlu", 0.50, 0.34)
    fer = mat_alu("FerruleAlu", 0.56, 0.30)
    hose_m = mat_hose()
    cap = C.mat_black_plastic("CapPA", rough=0.45, color=0.03)
    rub = C.mat_rubber("ORing")
    steel = C.principled("ZincSteel", (0.62, 0.62, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=400, strength=0.04, distance=0.0006)
    objs = []
    # aluminium pipe A: block fitting -> bends -> ferrule 1
    A = [(-2.55, -0.85, 0.30), (-2.05, -0.85, 0.30), (-1.75, -0.45, 0.30), (-1.20, -0.45, 0.62), (-0.55, 0.05, 0.62)]
    pa = fillet(A, 0.20)
    objs.append(tube("PipeA", pa, PR, alu))
    d0 = (pa[1] - pa[0]).normalized()
    objs += block_fitting(blk, cap, rub, steel, pa[0], d0)
    # service port on the first straight run, pointing up
    sp = Vector(A[0]).lerp(Vector(A[1]), 0.55)
    objs += service_port(blk, cap, sp, (0, 0, 1))
    e1 = pa[-1]
    d1 = (pa[-1] - pa[-2]).normalized()
    objs.append(ferrule("Ferrule1", fer, e1, d1))
    # rubber hose section
    h0 = e1 + d1 * 0.40
    ctrl = [h0 - d1 * 0.1, h0, h0 + d1 * 0.35, Vector((0.55, 0.55, 0.42)), Vector((1.25, 0.25, 0.30)), Vector((1.55, -0.25, 0.36)),
            Vector((1.62, -0.55, 0.40))]
    hp = smooth_path(ctrl, 14)[1:]
    objs.append(tube("Hose", hp, HR, hose_m, res=8))
    d2 = (hp[-1] - hp[-3]).normalized()
    f2 = hp[-1] + d2 * 0.40
    objs.append(ferrule("Ferrule2", fer, f2, -d2))
    # P-clip around the hose
    k = int(len(hp) * 0.55)
    objs += p_clip(steel, rub, hp[k], (hp[k + 1] - hp[k - 1]).normalized())
    # short pipe B to the nut fitting
    B = [f2, f2 + d2 * 0.25, f2 + d2 * 0.25 + Vector((0.35, -0.25, 0.0)), f2 + d2 * 0.25 + Vector((0.75, -0.25, 0.0))]
    pb = fillet(B, 0.18)
    objs.append(tube("PipeB", pb, PR, alu))
    objs += nut_end(alu, steel, pb[-1] - (pb[-1] - pb[-2]).normalized() * 0.06, (pb[-1] - pb[-2]).normalized())
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("tubo-clima", objs, "tubo-clima.py",
            "car A/C pipe: bent aluminium pipe with block fitting, service port with cap, crimped rubber hose section, nut fitting",
            az=22, el=34, lens=70, fill=0.86,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
