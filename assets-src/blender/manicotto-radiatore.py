"""Radiator coolant hose (manicotto radiatore) as removed from a small car: moulded black
EPDM hose with several 3D bends, open ends showing the wall thickness, slightly thicker
cuffs where it slips over the necks, mould parting lines along both sides, a small
moulded bleed branch, white paint alignment marks, and a zinc-plated constant-tension
spring clamp with its two squeeze ears sitting on each cuff."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 10 cm
RO, RI = 0.21, 0.16           # hose outer / inner radius (42 / 32 mm)
SEG = 64


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=48, bevel=None, M=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M if M is not None else axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=40)
    return C.finalize(ob, angle=40)


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


def resample(pts, step):
    """even arc-length resampling of a polyline"""
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(L[-1] / step))
    out, j = [], 0
    for i in range(n + 1):
        s = L[-1] * i / n
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append(pts[j].lerp(pts[j + 1], t))
    return out, L[-1]


def ptframes(pts, up=(0, 0, 1)):
    """parallel-transport frames (P, T, U, V) along a polyline"""
    n = len(pts)
    Ts = []
    for i in range(n):
        a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        Ts.append((b - a).normalized())
    U = Vector(up).cross(Ts[0])
    if U.length < 1e-4:
        U = Vector((1, 0, 0)).cross(Ts[0])
    U.normalize()
    out = []
    for i in range(n):
        if i:
            q = Ts[i - 1].rotation_difference(Ts[i])
            U = (q @ U)
            U = (U - Ts[i] * U.dot(Ts[i])).normalized()
        out.append((pts[i], Ts[i], U, Ts[i].cross(U)))
    return out


def hollow_sweep(name, fr, rfun, ri, mat, seg=SEG):
    """tube with wall thickness; rfun(s, theta) -> outer radius"""
    bm = bmesh.new()
    ro_rings, ri_rings = [], []
    N = len(fr)
    for i, (P, T, U, V) in enumerate(fr):
        s = i / (N - 1)
        o, ii = [], []
        for k in range(seg):
            t = math.tau * k / seg
            c, sn = math.cos(t), math.sin(t)
            r = rfun(s, t)
            o.append(bm.verts.new(P + U * (r * c) + V * (r * sn)))
            ii.append(bm.verts.new(P + U * (ri * c) + V * (ri * sn)))
        ro_rings.append(o)
        ri_rings.append(ii)
    for i in range(N - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            a, b = ro_rings[i], ro_rings[i + 1]
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
            a, b = ri_rings[i], ri_rings[i + 1]
            bm.faces.new((a[k], b[k], b[k2], a[k2]))
    for i in (0, N - 1):
        o, ii = ro_rings[i], ri_rings[i]
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new((o[k], ii[k], ii[k2], o[k2]))
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    return ob


# ----------------------------------------------------------------- materials
def mat_hose(name="EPDM"):
    """moulded EPDM: satin black with slight grey bloom patches and fine grain"""
    m = C.principled(name, (0.03, 0.03, 0.03), rough=0.55)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.72
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mc.inputs["Factor"])
    mc.inputs["A"].default_value = (0.024, 0.024, 0.025, 1)
    mc.inputs["B"].default_value = (0.065, 0.064, 0.062, 1)
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.48
    rr.inputs["To Max"].default_value = 0.78
    nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 450.0
    g.inputs["Detail"].default_value = 3.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
CTRL = [(-2.05, -0.55, 0.0), (-1.55, -0.45, 0.0), (-1.05, -0.25, 0.08), (-0.55, 0.05, 0.45), (-0.05, 0.2, 0.95),
        (0.55, 0.1, 1.2), (1.15, -0.15, 1.05), (1.55, -0.35, 0.65), (1.70, -0.45, 0.20), (1.72, -0.47, -0.15)]
CUFF = 0.45                     # cuff length (units)


def hose(mat):
    pts, L = resample(smooth_path(CTRL, 16), 0.03)
    fr = ptframes(pts, up=(0, 0, 1))
    cuff = CUFF / L

    def rfun(s, t):
        e = min(s, 1 - s)
        r = RO + 0.012 * (1 - C.smoothstep(cuff, cuff + 0.04, e))
        if e < 0.004:
            r -= 0.012            # rounded lip at the cut end
        # mould parting lines at theta = 0 and pi
        for tc in (0.0, math.pi):
            d = math.atan2(math.sin(t - tc), math.cos(t - tc))
            r += 0.0035 * math.exp(-(d / 0.035) ** 2)
        return r

    ob = hollow_sweep("Hose", fr, rfun, RI, mat)
    C.add_bevel(ob, 0.008, segments=2, angle=50)
    return [C.finalize(ob, angle=50)], fr, L


def clamp(fr, L, at_start, steel):
    out = []
    i = int(round((0.22 / L) * (len(fr) - 1)))
    if not at_start:
        i = len(fr) - 1 - i
    P, T, U, V = fr[i]
    M = Matrix((U, V, T)).transposed().to_4x4()
    M.translation = P
    rb = RO + 0.012
    th = 0.022
    w = 0.10
    # band (slightly helical overlap is hidden; a plain ring reads right)
    P_ = [(rb - 0.002, -w / 2, 0), (rb + th, -w / 2, 0), (rb + th, w / 2, 0), (rb - 0.002, w / 2, 0)]
    out.append(lathe_at("ClampBand", P_, [steel], M=M, steps=96, bevel=0.004))
    # squeeze ears at theta = 2.2 rad, bent radially outward
    ang = 2.2 if at_start else -2.2
    R = Matrix.Rotation(ang, 4, "Z")
    for k, off in enumerate((-0.035, 0.035)):
        bm = bmesh.new()
        C.box_bm(bm, 0.17, th, w * (0.9 if k else 0.62), center=(rb + 0.08, off, 0.0))
        C.box_bm(bm, 0.05, th + 0.004, w * (0.9 if k else 0.62), center=(rb + 0.18, off * 1.25, 0.0))
        ear = C.mesh_obj("ClampEar", bm, [steel])
        ear.matrix_world = M @ R
        C.add_bevel(ear, 0.007, segments=2, angle=30)
        out.append(C.finalize(ear, angle=35))
    return out


def branch(fr, L, mat):
    """small moulded bleed branch on the outside of the main bend"""
    out = []
    i = int(0.58 * (len(fr) - 1))
    P, T, U, V = fr[i]
    d = (V * 0.85 + T * 0.3).normalized()
    base = P + d * (RO - 0.03)
    M = axis_mat(base, d)
    ro, ri = 0.085, 0.055
    prof = [(ri, 0.40, 0), (ro - 0.006, 0.40, 0), (ro, 0.394, 0), (ro, 0.33, 0), (ro + 0.012, 0.32, 0), (ro + 0.012, 0.30, 0),
            (ro, 0.29, 0), (ro, 0.10, 0), (ro + 0.03, 0.04, 0), (ro + 0.075, 0.0, 0), (ro + 0.09, -0.03, 0), (ri, -0.03, 0)]
    out.append(lathe_at("Branch", prof, [mat], M=M, steps=48, bevel=0.004))
    return out


def marks(fr, L, paint):
    out = []
    for s, tt in ((0.30 / L, 1.2), (1 - 0.32 / L, -1.0), (0.5, 1.5)):
        i = int(s * (len(fr) - 1))
        P, T, U, V = fr[i]
        n = (U * math.cos(tt) + V * math.sin(tt)).normalized()
        M = Matrix((n.cross(T), T, n)).transposed().to_4x4()
        M.translation = P + n * (RO + 0.0)
        bm = bmesh.new()
        C.box_bm(bm, 0.03, 0.12, 0.006, center=(0, 0, 0.0))
        mk = C.mesh_obj("Mark", bm, [paint])
        mk.matrix_world = M
        C.add_bevel(mk, 0.002, segments=1, angle=30)
        out.append(C.finalize(mk, angle=35))
    return out


def build():
    rub = mat_hose()
    steel = C.principled("ZincSpring", (0.64, 0.63, 0.58), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    paint = C.principled("WhitePaint", (0.78, 0.78, 0.74), rough=0.6)
    C.add_noise_bump(paint, scale=300, strength=0.2, distance=0.001)
    objs, fr, L = hose(rub)
    objs += clamp(fr, L, True, steel) + clamp(fr, L, False, steel)
    objs += branch(fr, L, rub) + marks(fr, L, paint)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("manicotto-radiatore", objs, "manicotto-radiatore.py",
            "radiator coolant hose: moulded black rubber hose with bends, open ends, spring clamps on both cuffs, small bleed branch",
            az=24, el=26, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
