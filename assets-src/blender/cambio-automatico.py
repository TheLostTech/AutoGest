"""Automatic transaxle (cambio automatico) for a transverse FWD small car: large
sand-cast aluminium case with ribs and bolt bosses, deep bellhousing with the torque
converter fitted inside (welded converter shell, drive lugs with studs, pilot hub);
stamped-steel valve-body oil pan bolted on the front flank (bolt ring, embossed ribs,
drain plug); two steel oil-cooler lines with flare nuts and a clip bracket; the round
black transmission electrical connector, a speed sensor, the park/neutral range switch
with the selector lever on top; differential lobe with drive-shaft seals; mounting
bosses and breather.

Built with the input shaft along +X (bellhousing open toward -X), Z up; units ~ dm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # lathe Z -> world +X
RXm = Matrix.Rotation(-math.pi / 2, 4, "X")     # lathe Z -> world +Y
RXp = Matrix.Rotation(math.pi / 2, 4, "X")      # lathe Z -> world -Y
DIFF = (0.78, -0.62)                           # diff axis (y, z)
CASE_CIRCLES = [(0.0, 0.0, 0.66), (0.62, -0.50, 0.50), (-0.25, -0.45, 0.42)]
X_CASE0, X_CASE1 = -0.30, 1.55
X_BELL = -1.30                                  # bell rim plane
R_RIM = 1.42


# ----------------------------------------------------------------- local helpers
def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def circle_pts(cx, cy, r, n=64):
    return [(cx + r * math.cos(math.tau * k / n), cy + r * math.sin(math.tau * k / n)) for k in range(n)]


def resample(poly, n):
    L = [0.0]
    P = poly + [poly[0]]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + math.dist(a, b))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


def case_section(grow=0.0, n=192):
    pts = []
    for (y, z, r) in CASE_CIRCLES:
        pts += circle_pts(y, z, r + grow, 96)
    return resample(hull2d(pts), n)


def prism_x(name, sec, x0, x1, mat, scale1=1.0, center=(0, 0)):
    bm = bmesh.new()
    frames = []
    for x, s in ((x0, 1.0), (x1, scale1)):
        ss = [(center[0] + (u - center[0]) * s, center[1] + (v - center[1]) * s) for (u, v) in sec]
        frames.append((Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), ss))
    C.sweep(bm, frames)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mats, M, steps=96, bevel=None, angle=40, mod=None, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def lathe_x(name, prof, mats, at=(0, 0), steps=128, mod=None, bevel=None, angle=40, cutters=()):
    return lathe_at(name, prof, mats, Matrix.Translation((0, at[0], at[1])) @ RY, steps=steps, mod=mod,
                    bevel=bevel, angle=angle, cutters=cutters)


def hex_along(name, r, a0, a1, mat, M, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, a0, a1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    return fin(C.mesh_obj(name, bm, [mat]), bevel=bevel)


def axis_matrix(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def frames_along(pts, sec):
    out = []
    n = len(pts)
    prevU = None
    for i, P in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prevU is None:
            U = T.cross(Vector((0, 0, 1)))
            if U.length < 1e-4:
                U = T.cross(Vector((1, 0, 0)))
        else:
            U = prevU - T * prevU.dot(T)
        U.normalize()
        V = T.cross(U).normalized()
        prevU = U
        out.append((P, U, V, sec))
    return out


def pipe(name, ctrl, r, mat, n=60):
    """smooth tube through control points (Catmull-Rom)."""
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    pts = []
    seg = len(P) - 3
    for i in range(seg):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        m = max(2, n // seg)
        for k in range(m):
            t = k / m
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(P[-2])
    sec = [(r * math.cos(math.tau * j / 16), r * math.sin(math.tau * j / 16)) for j in range(16)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec))
    return fin(C.mesh_obj(name, bm, [mat]), angle=60), pts


def cast_alu(name, base=0.50, rough=0.46):
    """Sand-cast aluminium: mottled tone, grainy bump, grime collected in crevices (AO)."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.12
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 1.0
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.04, base * 1.04, base * 1.02, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.79, base * 0.74, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.095, 0.085, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.22
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 420.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.16
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- bellhousing + converter
def bellhousing(alu):
    out = []
    outer = {(1.36, -0.70), (1.12, -0.38)}

    def ribs(r, z, t):
        if (round(r, 3), round(z, 3)) not in {(a, round(b, 3)) for a, b in outer}:
            return r
        v = math.cos(12 * t)
        return r + 0.03 * max(0.0, (v - 0.80) / 0.20)
    P = [(1.33, X_BELL, 0), (R_RIM + 0.03, X_BELL, 0), (R_RIM + 0.03, X_BELL + 0.09, 0), (1.38, X_BELL + 0.12, 0),
         (1.36, -0.70, 0), (1.12, -0.38, 0), (0.85, -0.25, 0), (0.30, -0.25, 0), (0.30, -0.32, 0), (0.76, -0.32, 0),
         (1.05, -0.42, 0), (1.28, -0.70, 0), (1.31, X_BELL + 0.10, 0)]
    out.append(lathe_x("Bell", P, [alu], steps=288, mod=ribs, bevel=0.01, angle=30))
    angs = [math.radians(a) for a in (100, 140, 180, 215, 250, 290, 325, 0, 35, 68)]
    for a in angs:
        y, z = (R_RIM + 0.07) * math.cos(a), (R_RIM + 0.07) * math.sin(a)
        P = [(0.04, X_BELL, 0), (0.07, X_BELL, 0), (0.08, X_BELL + 0.01, 0), (0.08, X_BELL + 0.10, 0),
             (0.07, X_BELL + 0.11, 0), (0.04, X_BELL + 0.11, 0)]
        out.append(lathe_x("BellBoss", P, [alu], at=(y, z), steps=40))
    bm = bmesh.new()
    for a in angs:
        M = Matrix.Translation((X_BELL + 0.24, (R_RIM - 0.02) * math.cos(a), (R_RIM - 0.02) * math.sin(a))) @ Matrix.Rotation(a, 4, "X")
        C.box_bm(bm, 0.26, 0.08, 0.04, matrix=M @ Matrix.Rotation(math.radians(-30), 4, "Z"))
    out.append(fin(C.mesh_obj("BossWebs", bm, [alu]), bevel=0.01))
    # starter-motor flange boss on the top +Y side
    a = math.radians(55)
    bm = bmesh.new()
    C.cyl_bm(bm, 0.30, X_BELL + 0.02, -0.72, seg=48, matrix=Matrix.Translation((0, 1.52 * math.cos(a), 1.52 * math.sin(a))) @ RY)
    cb = bmesh.new()
    C.cyl_bm(cb, 0.21, X_BELL - 0.2, -0.6, seg=48, matrix=Matrix.Translation((0, 1.52 * math.cos(a), 1.52 * math.sin(a))) @ RY)
    out.append(fin(C.mesh_obj("StarterBoss", bm, [alu]), bevel=0.02, cutters=[C.mesh_obj("StarterBore", cb, [])]))
    return out


def converter(shell, stud_m, weld_m, hub_m):
    out = []
    xf = X_BELL + 0.16               # converter front face plane
    P = [(0.0, xf, 0), (0.25, xf, 0), (0.30, xf + 0.02, 0), (0.95, xf + 0.06, 0), (1.12, xf + 0.12, 0),
         (1.20, xf + 0.22, 0), (1.22, xf + 0.34, 0), (1.20, xf + 0.44, 0), (1.12, xf + 0.56, 0), (0.90, xf + 0.66, 0),
         (0.40, xf + 0.72, 0), (0.0, xf + 0.72, 0)]
    out.append(lathe_x("Converter", P, [shell], steps=192, bevel=0.006))
    # weld seam round the converter equator
    P = [(1.215, xf + 0.32, 0), (1.235, xf + 0.335, 0), (1.235, xf + 0.355, 0), (1.215, xf + 0.37, 0)]
    out.append(lathe_x("Seam", P, [weld_m], steps=192, angle=60))
    # embossed ring on the front cover
    P = [(0.62, xf + 0.035, 0), (0.66, xf + 0.02, 0), (0.72, xf + 0.02, 0), (0.76, xf + 0.04, 0)]
    out.append(lathe_x("CoverRing", P, [shell], steps=192, angle=60))
    # pilot hub in the middle
    P = [(0.0, xf - 0.16, 0), (0.12, xf - 0.16, 0), (0.14, xf - 0.14, 0), (0.14, xf + 0.02, 0), (0.0, xf + 0.02, 0)]
    out.append(lathe_x("PilotHub", P, [hub_m], steps=64))
    # four drive lugs with studs
    for k in range(4):
        a = math.tau * k / 4 + math.pi / 4
        y, z = 0.86 * math.cos(a), 0.86 * math.sin(a)
        bm = bmesh.new()
        M = Matrix.Translation((xf + 0.02, y, z)) @ Matrix.Rotation(a, 4, "X")
        C.box_bm(bm, 0.10, 0.20, 0.18, center=(-0.04, 0, 0), matrix=M)
        out.append(fin(C.mesh_obj("Lug", bm, [shell]), bevel=0.02))
        P = [(0.0, xf - 0.22, 0), (0.035, xf - 0.22, 0), (0.035, xf - 0.08, 0), (0.0, xf - 0.08, 0)]
        out.append(lathe_x("Stud", P, [stud_m], at=(y, z), steps=24))
    return out


# ----------------------------------------------------------------- main case
def gear_case(alu, steel):
    out = []
    sec = case_section()
    cy = sum(p[0] for p in sec) / len(sec)
    cz = sum(p[1] for p in sec) / len(sec)
    body = prism_x("Case", sec, X_CASE0, X_CASE1, alu, scale1=0.93, center=(cy, cz))
    out.append(fin(body, bevel=0.04, seg=3, angle=30))
    for x, w, g, s in ((-0.22, 0.08, 0.04, 1.0), (0.42, 0.04, 0.025, 0.98), (0.98, 0.04, 0.025, 0.96),
                       (1.48, 0.08, 0.045, 0.932)):
        sg = [(cy + (u - cy) * s, cz + (v - cz) * s) for (u, v) in case_section(g)]
        r = prism_x("CaseRib", sg, x - w / 2, x + w / 2, alu, center=(cy, cz))
        out.append(fin(r, bevel=min(0.015, w / 3), angle=30))
    # joint bolts round the end cover
    for (u, v) in case_section(0.03, n=13):
        u2, v2 = cy + (u - cy) * 0.932, cz + (v - cz) * 0.932
        out.append(hex_along("JointBolt", 0.03, 0.0, 0.04, steel, Matrix.Translation((1.52, u2, v2)) @ RY, bevel=0.005))
    # end cover dome over the main gear train
    P = [(0.0, 1.52, 0), (0.58, 1.52, 0), (0.58, 1.60, 0), (0.52, 1.72, 0), (0.38, 1.80, 0), (0.12, 1.83, 0), (0.0, 1.83, 0)]
    out.append(lathe_x("EndCover", P, [alu], at=(0.0, 0.02), steps=160, bevel=0.012))
    for k in range(8):
        a = math.tau * k / 8 + 0.2
        out.append(hex_along("CoverBolt", 0.028, 0.0, 0.035, steel,
                             Matrix.Translation((1.60, 0.52 * math.cos(a), 0.02 + 0.52 * math.sin(a))) @ RY, bevel=0.004))
    # longitudinal stiffening ribs on top
    bm = bmesh.new()
    for y in (-0.25, 0.25):
        C.box_bm(bm, X_CASE1 - X_CASE0 - 0.2, 0.05, 0.05, center=((X_CASE0 + X_CASE1) / 2, y, 0.62))
    out.append(fin(C.mesh_obj("TopRibs", bm, [alu]), bevel=0.015))
    return out


def diff_lobe(alu, rubber, dark):
    out = []
    P = [(0.12, -0.36, 0), (0.24, -0.36, 0), (0.32, -0.30, 0), (0.40, -0.12, 0), (0.42, 0.20, 0), (0.40, 0.60, 0),
         (0.34, 1.20, 0), (0.26, 1.42, 0), (0.12, 1.42, 0)]
    out.append(lathe_x("DiffLobe", P, [alu], at=DIFF, steps=192, bevel=0.01))
    for x0, x1 in ((-0.36, -0.40), (1.42, 1.46)):
        a, b = sorted((x0, x1))
        out.append(lathe_x("SealBoss", [(0.0, a, 0), (0.20, a, 0), (0.20, b, 0), (0.0, b, 0)], [alu], at=DIFF, steps=96))
        c, d = (a - 0.03, a) if x0 < 0 else (b, b + 0.03)
        out.append(lathe_x("Seal", [(0.09, c, 0), (0.17, c, 0), (0.17, d, 0), (0.09, d, 0)], [rubber], at=DIFF, steps=96))
        e, f = (c - 0.02, c + 0.02) if x0 < 0 else (d - 0.02, d + 0.02)

        def spl(r, z, t):
            return r - 0.012 * (1 if math.cos(18 * t) > 0 else 0)
        out.append(lathe_x("SideGear", [(0.0, e, 0), (0.085, e, 0), (0.085, f, 0), (0.0, f, 0)], [dark], at=DIFF,
                           steps=18 * 8, mod=spl))
    return out


def oil_pan(pan_m, steel, alu):
    """stamped valve-body pan bolted onto the front (-Y) flank of the case."""
    out = []
    y0 = -0.68            # case face plane under the pan
    x0, x1, z0, z1 = 0.05, 1.30, -0.55, 0.22
    # cast mounting rail on the case
    bm = bmesh.new()
    C.box_bm(bm, x1 - x0 + 0.12, 0.16, z1 - z0 + 0.12, center=((x0 + x1) / 2, y0 + 0.02, (z0 + z1) / 2))
    out.append(fin(C.mesh_obj("PanRail", bm, [alu]), bevel=0.03, seg=3))
    # pan: flange + raised tray with drafted sides
    bm = bmesh.new()
    C.box_bm(bm, x1 - x0 + 0.10, 0.03, z1 - z0 + 0.10, center=((x0 + x1) / 2, y0 - 0.075, (z0 + z1) / 2))
    out.append(fin(C.mesh_obj("PanFlange", bm, [pan_m]), bevel=0.012))
    sec = [(x0 + 0.06, z0 + 0.06), (x1 - 0.06, z0 + 0.06), (x1 - 0.06, z1 - 0.06), (x0 + 0.06, z1 - 0.06)]
    frames = [(Vector((0, y0 - 0.08, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), sec)]
    sec2 = [(x0 + 0.12, z0 + 0.12), (x1 - 0.12, z0 + 0.12), (x1 - 0.12, z1 - 0.12), (x0 + 0.12, z1 - 0.12)]
    frames.append((Vector((0, y0 - 0.26, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), sec2))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    out.append(fin(C.mesh_obj("PanTray", bm, [pan_m]), bevel=0.05, seg=4, angle=30))
    # embossed stiffening ribs on the pan face
    bm = bmesh.new()
    for i in range(4):
        x = x0 + 0.30 + i * 0.22
        C.box_bm(bm, 0.05, 0.03, z1 - z0 - 0.34, center=(x, y0 - 0.26, (z0 + z1) / 2))
    out.append(fin(C.mesh_obj("PanRibs", bm, [pan_m]), bevel=0.014))
    # pan bolts round the flange
    for i in range(7):
        x = x0 - 0.0 + (x1 - x0) * i / 6
        for z in (z0 - 0.02, z1 + 0.02):
            out.append(hex_along("PanBolt", 0.03, 0.0, 0.04, steel, Matrix.Translation((x, y0 - 0.09, z)) @ RXp, bevel=0.005))
    for z in ((z0 + z1) / 2 - 0.2, (z0 + z1) / 2 + 0.2):
        for x in (x0 - 0.02, x1 + 0.02):
            out.append(hex_along("PanBolt", 0.03, 0.0, 0.04, steel, Matrix.Translation((x, y0 - 0.09, z)) @ RXp, bevel=0.005))
    # drain plug
    out.append(hex_along("DrainPlug", 0.05, 0.0, 0.06, steel, Matrix.Translation((x1 - 0.30, y0 - 0.26, z0 + 0.18)) @ RXp, bevel=0.006))
    return out


def cooler_lines(tube_m, steel, black, alu):
    out = []
    for k, (x, z) in enumerate(((0.62, 0.45), (0.82, 0.45))):
        # fitting boss + flare nut on the case top-front
        M = Matrix.Translation((x, -0.48, z)) @ Matrix.Rotation(math.radians(-50), 4, "X")
        out.append(lathe_at("FitBoss", [(0.0, -0.15, 0), (0.08, -0.15, 0), (0.08, 0.02, 0), (0.0, 0.02, 0)], [alu], M, steps=40, bevel=0.006))
        out.append(hex_along("FlareNut", 0.05, 0.02, 0.10, steel, M))
        p0 = M @ Vector((0, 0, 0.10))
        d = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
        ctrl = [p0, p0 + d * 0.22, Vector((x + 0.25 + 0.12 * k, -0.95 - 0.12 * k, 0.95 + 0.04 * k)),
                Vector((x + 0.85 + 0.14 * k, -0.95 - 0.10 * k, 1.00)), Vector((x + 1.35 + 0.12 * k, -0.75 - 0.10 * k, 0.92))]
        p, pts = pipe("CoolerLine", ctrl, 0.035, tube_m)
        out.append(p)
        # hose barb end with bead
        T = (pts[-1] - pts[-2]).normalized()
        Me = axis_matrix(pts[-1], T)
        out.append(lathe_at("Barb", [(0.0, -0.02, 0), (0.042, -0.02, 0), (0.05, 0.03, 0), (0.036, 0.05, 0), (0.036, 0.14, 0),
                                     (0.0, 0.14, 0)], [tube_m], Me, steps=32))
    # clip bracket holding both lines together
    bm = bmesh.new()
    C.box_bm(bm, 0.12, 0.30, 0.10, center=(1.12, -0.97, 0.99))
    out.append(fin(C.mesh_obj("LineClip", bm, [black]), bevel=0.02))
    return out


def electrics(black, steel, alu, rubber):
    out = []
    # round transmission connector on the top-front of the case
    M = Matrix.Translation((0.28, -0.42, 0.52)) @ Matrix.Rotation(math.radians(-35), 4, "X")
    out.append(lathe_at("ConnBoss", [(0.0, -0.2, 0), (0.15, -0.2, 0), (0.15, 0.03, 0), (0.0, 0.03, 0)], [alu], M, steps=48, bevel=0.008))
    P = [(0.0, 0.03, 0), (0.12, 0.03, 0), (0.12, 0.06, 0), (0.10, 0.07, 0), (0.10, 0.20, 0), (0.11, 0.21, 0), (0.11, 0.26, 0),
         (0.09, 0.28, 0), (0.0, 0.28, 0)]
    def ribs(r, z, t):
        if abs(r - 0.10) > 1e-4:
            return r
        return r + 0.008 * (1 if math.cos(16 * t) > 0.6 else 0)
    out.append(lathe_at("RoundConn", P, [black], M, steps=128, mod=ribs, bevel=0.004))
    # bayonet ring
    out.append(lathe_at("Bayonet", [(0.10, 0.07, 0), (0.125, 0.07, 0), (0.125, 0.12, 0), (0.10, 0.12, 0)], [black], M, steps=64))
    # speed sensor (black plastic, one bolt) on the side
    M2 = Matrix.Translation((1.15, -0.55, 0.42)) @ Matrix.Rotation(math.radians(-60), 4, "X")
    out.append(lathe_at("Sensor", [(0.0, -0.1, 0), (0.05, -0.1, 0), (0.05, 0.08, 0), (0.0, 0.08, 0)], [black], M2, steps=32))
    bm = bmesh.new()
    C.box_bm(bm, 0.18, 0.10, 0.04, center=(0.05, 0, 0.08), matrix=M2)
    C.box_bm(bm, 0.08, 0.10, 0.14, center=(-0.02, 0, 0.16), matrix=M2)
    out.append(fin(C.mesh_obj("SensorHead", bm, [black]), bevel=0.012))
    # range (park/neutral) switch + selector lever on top
    bm = bmesh.new()
    C.box_bm(bm, 0.36, 0.30, 0.10, center=(1.05, 0.10, 0.70))
    C.box_bm(bm, 0.14, 0.12, 0.12, center=(1.30, 0.22, 0.75))
    out.append(fin(C.mesh_obj("RangeSwitch", bm, [black]), bevel=0.02))
    out.append(lathe_at("SelShaft", [(0.0, 0.70, 0), (0.04, 0.70, 0), (0.04, 0.92, 0), (0.0, 0.92, 0)], [steel],
                        Matrix.Translation((1.00, 0.08, 0)), steps=32))
    bm = bmesh.new()
    M3 = Matrix.Translation((1.00, 0.08, 0.86)) @ Matrix.Rotation(math.radians(-40), 4, "Z")
    C.box_bm(bm, 0.38, 0.08, 0.03, center=(0.16, 0, 0), matrix=M3)
    C.cyl_bm(bm, 0.07, -0.015, 0.015, seg=32, matrix=M3)
    C.cyl_bm(bm, 0.05, -0.015, 0.015, seg=32, matrix=M3 @ Matrix.Translation((0.32, 0, 0)))
    lv = C.mesh_obj("SelLever", bm, [steel])
    out.append(fin(lv, bevel=0.008))
    out.append(hex_along("LeverNut", 0.045, 0.875, 0.92, steel, Matrix.Translation((1.00, 0.08, 0))))
    # breather cap
    out.append(lathe_at("Breather", [(0.0, 0.0, 0), (0.03, 0.0, 0), (0.03, 0.12, 0), (0.055, 0.13, 0), (0.055, 0.17, 0), (0.0, 0.18, 0)],
                        [black], Matrix.Translation((0.40, 0.25, 0.64)), steps=32))
    return out


def mounts(alu):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 0.34, 0.30, 0.18, center=(1.22, 0.30, 0.62))
    cb = bmesh.new()
    for (x, y) in ((1.12, 0.22), (1.32, 0.22), (1.22, 0.40)):
        C.cyl_bm(cb, 0.03, 0.4, 0.9, seg=24, matrix=Matrix.Translation((x, y, 0)))
    out.append(fin(C.mesh_obj("MountPad", bm, [alu]), bevel=0.02, cutters=[C.mesh_obj("MountHoles", cb, [])]))
    return out


def build():
    alu = cast_alu("CastAlu", base=0.40, rough=0.50)
    steel = C.principled("Zinc", (0.64, 0.65, 0.67), metallic=1.0, rough=0.25)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    shell = C.principled("ConverterSteel", (0.34, 0.34, 0.35), metallic=1.0, rough=0.36)
    C.add_noise_bump(shell, scale=500, strength=0.05, distance=0.0006, rough_var=0.08)
    weld_m = C.principled("Weld", (0.10, 0.09, 0.08), metallic=0.8, rough=0.5)
    C.add_noise_bump(weld_m, scale=120, strength=0.5, distance=0.004)
    hub_m = C.mat_machined("Hub", color=0.55, rough=0.2, rings=900)
    pan_m = C.principled("PanSteel", (0.10, 0.10, 0.105), metallic=0.7, rough=0.42)
    C.add_noise_bump(pan_m, scale=500, strength=0.05, distance=0.0005, rough_var=0.06)
    tube_m = C.principled("LineSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    C.add_noise_bump(tube_m, scale=700, strength=0.03, distance=0.0005)
    black = C.mat_black_plastic("BlackPA", rough=0.45, color=0.025)
    rubber = C.mat_rubber("Seal")
    dark = C.principled("DarkSteel", (0.08, 0.08, 0.085), metallic=1.0, rough=0.4)

    objs = []
    objs += bellhousing(alu)
    objs += converter(shell, steel, weld_m, hub_m)
    objs += gear_case(alu, steel)
    objs += diff_lobe(alu, rubber, dark)
    objs += oil_pan(pan_m, steel, alu)
    objs += cooler_lines(tube_m, steel, black, alu)
    objs += electrics(black, steel, alu, rubber)
    objs += mounts(alu)
    C.transform_all(objs, Matrix.Rotation(math.radians(62), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("cambio-automatico", objs, "cambio-automatico.py",
            "automatic transaxle: cast-aluminium case and bellhousing with torque converter inside, "
            "valve-body oil pan, cooler lines, round electrical connector, selector lever and range switch",
            az=35, el=24, lens=70, fill=0.84, **kw)
