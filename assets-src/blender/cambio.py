"""Manual transverse (FWD) gearbox: ribbed cast-aluminium gear case, open conical
bellhousing with bolt bosses and splined input shaft, differential lobe with two
drive-shaft output flanges, shift-linkage tower with levers and cable bracket on top,
end cover, mounting bosses with bolt holes, drain and fill plugs and a reverse-light
switch with its connector.

Built with the input shaft along +X (bellhousing open toward -X), Z up."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RY = Matrix.Rotation(math.pi / 2, 4, "Y")      # lathe Z -> world +X
DIFF = (-0.58, -0.40)                           # diff axis (y, z)
CASE_CIRCLES = [(0.0, 0.0, 0.36), (-0.30, -0.20, 0.30)]   # (y, z, r) section of the gear case
X_CASE0, X_CASE1 = -0.27, 0.90


# ----------------------------------------------------------------- local helpers
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
    """Resample a closed polygon to n points evenly by arc length."""
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


def case_section(grow=0.0, n=160):
    pts = []
    for (y, z, r) in CASE_CIRCLES:
        pts += circle_pts(y, z, r + grow, 96)
    return resample(hull2d(pts), n)


def prism_x(name, sec, x0, x1, mat, scale1=1.0, center=(0, 0)):
    """Extrude a (y, z) section along X, optionally tapering toward x1."""
    bm = bmesh.new()
    frames = []
    for x, s in ((x0, 1.0), (x1, scale1)):
        ss = [(center[0] + (u - center[0]) * s, center[1] + (v - center[1]) * s) for (u, v) in sec]
        frames.append((Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), ss))
    C.sweep(bm, frames)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_x(name, prof, mats, at=(0, 0), steps=128, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = Matrix.Translation((0, at[0], at[1])) @ RY
    return ob


def ring_x(name, r0, r1, x0, x1, mat, at=(0, 0), steps=64, ch=0.0):
    P = [(r0, x0, 0), (r1 - ch, x0, 0), (r1, x0 + ch, 0), (r1, x1 - ch, 0), (r1 - ch, x1, 0), (r0, x1, 0)]
    return C.finalize(lathe_x(name, P, [mat], at=at, steps=steps), angle=40)


def hex_along(name, r, a0, a1, mat, M, bevel=0.006):
    """Hex prism along local Z from a0 to a1, placed by matrix M."""
    bm = bmesh.new()
    C.cyl_bm(bm, r, a0, a1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


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


# ----------------------------------------------------------------- parts
def bellhousing(alu):
    outer = {(0.84, -0.70), (0.56, -0.30)}

    def ribs(r, z, t):
        if (round(r, 3), round(z, 3)) not in outer:
            return r
        v = math.cos(14 * t)
        return r + 0.026 * max(0.0, (v - 0.80) / 0.20)

    P = [(0.775, -0.80, 0), (0.885, -0.80, 0), (0.885, -0.725, 0), (0.84, -0.70, 0), (0.56, -0.30, 0),
         (0.545, -0.21, 0), (0.13, -0.21, 0), (0.13, -0.265, 0), (0.50, -0.265, 0), (0.76, -0.70, 0)]
    ob = lathe_x("Bell", P, [alu], steps=280, mod=ribs)
    C.add_bevel(ob, 0.008, segments=2, angle=28)
    out = [C.finalize(ob, angle=30)]
    # bolt bosses round the rim (tubes with through-holes) + webs down onto the cone
    angs = [math.radians(a) for a in (95, 135, 175, 215, 300, 340, 20, 58)]
    for a in angs:
        y, z = 0.925 * math.cos(a), 0.925 * math.sin(a)
        P = [(0.034, -0.80, 0), (0.062, -0.80, 0), (0.07, -0.792, 0), (0.07, -0.708, 0), (0.062, -0.70, 0), (0.034, -0.70, 0)]
        out.append(C.finalize(lathe_x("BellBoss", P, [alu], at=(y, z), steps=40), angle=40))
    bm = bmesh.new()
    for a in angs:
        M = Matrix.Translation((-0.66, 0.85 * math.cos(a), 0.85 * math.sin(a))) @ Matrix.Rotation(a, 4, "X")
        C.box_bm(bm, 0.12, 0.07, 0.035, matrix=M @ Matrix.Rotation(math.radians(-35), 4, "Z"))
    web = C.mesh_obj("BossWebs", bm, [alu])
    C.add_bevel(web, 0.008, segments=2, angle=30)
    out.append(C.finalize(web, angle=35))
    return out


def input_shaft(steel, spline):
    out = [ring_x("GuideTube", 0.0, 0.095, -0.27, -0.50, steel, steps=96, ch=0.008)]
    P = [(0.0, -0.50, 0), (0.05, -0.50, 0), (0.05, -0.75, 0), (0.035, -0.77, 0), (0.0, -0.77, 0)]

    def spl(r, z, t):
        if r < 0.049:
            return r
        return r - 0.008 * (1 if math.cos(22 * t) < 0 else 0)
    out.append(C.finalize(lathe_x("InputShaft", P, [spline], steps=22 * 8, mod=spl), angle=30))
    # clutch release fork poking through the bell side, with rubber boot
    return out


def release_fork(steel, rubber, alu):
    out = []
    a = math.radians(115)
    y, z = 0.62 * math.cos(a), 0.62 * math.sin(a)
    # boss on the bell + rubber boot
    boot = C.lathe("ForkBoot", [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.085, 0.03, 0), (0.06, 0.06, 0), (0.07, 0.09, 0),
                               (0.045, 0.13, 0), (0.0, 0.13, 0)], [rubber], steps=48)
    n = Vector((0, math.cos(a), math.sin(a)))
    M = Matrix.Translation((-0.48, y, z)) @ n.to_track_quat("Z", "X").to_matrix().to_4x4()
    boot.matrix_world = M
    out.append(C.finalize(boot, angle=45))
    bm = bmesh.new()
    C.box_bm(bm, 0.05, 0.035, 0.28, center=(0, 0, 0.20), matrix=M)
    fk = C.mesh_obj("ForkArm", bm, [steel])
    C.add_bevel(fk, 0.008, segments=2, angle=30)
    out.append(C.finalize(fk, angle=35))
    return out


def gear_case(alu, steel):
    out = []
    sec = case_section()
    cy = sum(p[0] for p in sec) / len(sec)
    cz = sum(p[1] for p in sec) / len(sec)
    body = prism_x("GearCase", sec, X_CASE0, X_CASE1, alu, scale1=0.94, center=(cy, cz))
    C.add_bevel(body, 0.03, segments=3, angle=30)
    out.append(C.finalize(body, angle=30))
    # circumferential ribs + joint flanges
    for x, w, g, s in ((-0.20, 0.06, 0.035, 1.0), (0.12, 0.035, 0.022, 0.982), (0.40, 0.035, 0.022, 0.966),
                       (0.66, 0.035, 0.022, 0.951), (0.86, 0.06, 0.04, 0.94)):
        sg = [(cy + (u - cy) * s, cz + (v - cz) * s) for (u, v) in case_section(g)]
        r = prism_x("CaseRib", sg, x - w / 2, x + w / 2, alu, center=(cy, cz))
        C.add_bevel(r, min(0.012, w / 3), segments=2, angle=30)
        out.append(C.finalize(r, angle=30))
    # longitudinal ribs on the visible (-Y) flank
    bm = bmesh.new()
    for (z, yy) in ((0.16, -0.355), (-0.08, -0.57)):
        C.box_bm(bm, X_CASE1 - X_CASE0 - 0.12, 0.05, 0.035, center=((X_CASE0 + X_CASE1) / 2 + 0.02, yy, z))
    lr = C.mesh_obj("LongRibs", bm, [alu])
    C.add_bevel(lr, 0.012, segments=2, angle=30)
    out.append(C.finalize(lr, angle=30))
    # bolt heads round the end-cover joint
    sb = case_section(0.022, n=11)
    for (u, v) in sb:
        u2, v2 = cy + (u - cy) * 0.94, cz + (v - cz) * 0.94
        out.append(hex_along("JointBolt", 0.028, 0.0, 0.035, steel, Matrix.Translation((0.89, u2, v2)) @ RY, bevel=0.005))
    # end cover (5th-gear dome)
    P = [(0.0, 0.88, 0), (0.30, 0.88, 0), (0.30, 0.94, 0), (0.27, 1.02, 0), (0.20, 1.07, 0), (0.08, 1.085, 0), (0.0, 1.085, 0)]
    ec = lathe_x("EndCover", P, [alu], at=(-0.10, -0.06), steps=128)
    C.add_bevel(ec, 0.01, segments=2, angle=30)
    out.append(C.finalize(ec, angle=35))
    for k in range(6):
        a = math.tau * k / 6 + 0.3
        out.append(hex_along("CoverBolt", 0.024, 0.0, 0.03, steel,
                             Matrix.Translation((0.995, -0.10 + 0.255 * math.cos(a), -0.06 + 0.255 * math.sin(a))) @ RY
                             @ Matrix.Rotation(0, 4, "Z"), bevel=0.004))
    return out


def diff_lobe(alu, steel, rubber):
    out = []
    P = [(0.10, -0.42, 0), (0.20, -0.42, 0), (0.25, -0.39, 0), (0.31, -0.31, 0), (0.345, -0.18, 0), (0.35, 0.02, 0),
         (0.33, 0.15, 0), (0.27, 0.23, 0), (0.20, 0.26, 0), (0.10, 0.26, 0)]
    big = {0.31, 0.345, 0.35, 0.33}

    def ribs(r, z, t):
        if round(r, 3) not in big:
            return r
        v = math.cos(10 * t)
        return r + 0.022 * max(0.0, (v - 0.85) / 0.15)
    ob = lathe_x("DiffLobe", P, [alu], at=DIFF, steps=200, mod=ribs)
    C.add_bevel(ob, 0.008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=30))
    # output flanges (6-bolt drive flanges) both sides, standing off on necks, with seals
    for side, x0 in ((-1, -0.42), (1, 0.26)):
        s0, s1 = sorted((x0 - side * 0.01, x0 + side * 0.03))
        out.append(ring_x("SealBoss", 0.0, 0.16, s0, s1, alu, at=DIFF, ch=0.01))
        e0, e1 = sorted((x0 + side * 0.03, x0 + side * 0.05))
        out.append(ring_x("Seal", 0.06, 0.12, e0, e1, rubber, at=DIFF, ch=0.006))
        f0 = x0 + side * 0.10
        f1 = f0 + side * 0.06
        a, b = min(f0, f1), max(f0, f1)
        fl = lathe_x("OutFlange", [(0.0, a, 0), (0.17, a, 0), (0.17, b, 0), (0.0, b, 0)], [steel], at=DIFF, steps=128)
        cb = bmesh.new()
        for k in range(6):
            t = math.tau * k / 6
            C.cyl_bm(cb, 0.021, a - 0.05, b + 0.05, seg=24,
                     matrix=Matrix.Translation((0, DIFF[0] + 0.122 * math.cos(t), DIFF[1] + 0.122 * math.sin(t))) @ RY)
        cut = C.mesh_obj("FlHoles", cb, [steel])
        C.add_boolean(fl, cut)
        C.add_bevel(fl, 0.006, segments=2, angle=30)
        out.append(C.finalize(fl, angle=35, remove=[cut]))
        n0, n1 = sorted((x0 + side * 0.03, f0))
        out.append(ring_x("FlNeck", 0.0, 0.075, n0, n1, steel, at=DIFF, ch=0.0))
        c0 = b if side > 0 else a - 0.03
        out.append(ring_x("FlCap", 0.0, 0.06, c0, c0 + 0.03, steel, at=DIFF, ch=0.012))
    # drain plug underneath (hex + washer)
    M = Matrix.Translation((-0.05, DIFF[0] + 0.05, DIFF[1] - 0.345)) @ Matrix.Rotation(math.pi, 4, "X")
    out.append(hex_along("DrainPlug", 0.04, 0.0, 0.045, steel, M, bevel=0.006))
    return out


def plugs_and_switch(alu, steel, black, copper):
    out = []
    # fill plug on the visible flank, sitting on a spot-faced boss
    y0 = -0.585
    M = Matrix.Translation((0.48, y0, 0.05)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    b = C.lathe("FillBoss", [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.085, 0.045, 0), (0.075, 0.055, 0), (0.0, 0.055, 0)], [alu], steps=48)
    b.matrix_world = M
    out.append(C.finalize(b, angle=40))
    out.append(hex_along("FillPlug", 0.045, 0.055, 0.10, steel, M, bevel=0.006))
    # reverse-light switch: hex body + black 2-pin connector
    M = Matrix.Translation((0.70, -0.43, 0.26)) @ Matrix.Rotation(math.radians(60), 4, "X")
    b = C.lathe("SwBoss", [(0.0, -0.05, 0), (0.07, -0.05, 0), (0.07, 0.03, 0), (0.06, 0.04, 0), (0.0, 0.04, 0)], [alu], steps=48)
    b.matrix_world = M
    out.append(C.finalize(b, angle=40))
    out.append(hex_along("SwHex", 0.045, 0.04, 0.085, steel, M, bevel=0.006))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.038, 0.085, 0.13, seg=32, matrix=M)
    sw = C.mesh_obj("SwBody", bm, [black])
    C.add_bevel(sw, 0.006, segments=2, angle=30)
    out.append(C.finalize(sw, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 0.075, 0.10, center=(0, 0, 0.18), matrix=M)
    C.box_bm(bm, 0.03, 0.05, 0.02, center=(0, 0.045, 0.19), matrix=M)  # latch
    cn = C.mesh_obj("SwConnector", bm, [black])
    C.add_bevel(cn, 0.01, segments=2, angle=30)
    out.append(C.finalize(cn, angle=35))
    # short pigtail of wires out of the connector
    for i, dx in enumerate((-0.022, 0.022)):
        cu = bpy.data.curves.new("Wire", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.012
        cu.bevel_resolution = 3
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(2)
        pts = [Vector((dx, 0, 0.23)), Vector((dx, -0.04, 0.33)), Vector((dx * 2, -0.16, 0.36))]
        for p, c in zip(sp.bezier_points, pts):
            p.co = M @ c
            p.handle_left_type = p.handle_right_type = "AUTO"
        ob = C.link(bpy.data.objects.new("Wire", cu))
        cu.materials.append(black)
        out.append(C.finalize(ob, angle=45))
    # breather cap on top
    out.append(C.finalize(C.lathe("Breather", [(0.0, 0.26, 0), (0.03, 0.26, 0), (0.03, 0.40, 0), (0.05, 0.41, 0),
                                               (0.05, 0.45, 0), (0.0, 0.46, 0)], [black], steps=32), angle=40))
    out[-1].matrix_world = Matrix.Translation((0.64, -0.15, 0.0))
    return out


def shift_tower(alu, steel, black, zinc):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.26, 0.20, center=(0.42, -0.02, 0.40))
    tw = C.mesh_obj("Tower", bm, [alu])
    C.add_bevel(tw, 0.03, segments=3, angle=30)
    out.append(C.finalize(tw, angle=30))
    out.append(C.finalize(C.lathe("TowerCap", [(0.0, 0.50, 0), (0.10, 0.50, 0), (0.10, 0.56, 0), (0.085, 0.575, 0), (0.0, 0.575, 0)], [alu], steps=64), angle=40))
    out[-1].matrix_world = Matrix.Translation((0.46, -0.04, 0))
    # selector shaft + two levers with ball studs
    out.append(C.finalize(C.lathe("SelShaft", [(0.0, 0.57, 0), (0.035, 0.57, 0), (0.035, 0.68, 0), (0.0, 0.68, 0)], [zinc], steps=32), angle=40))
    out[-1].matrix_world = Matrix.Translation((0.46, -0.04, 0))
    bm = bmesh.new()
    M1 = Matrix.Translation((0.46, -0.04, 0.655)) @ Matrix.Rotation(math.radians(-70), 4, "Z")
    C.box_bm(bm, 0.30, 0.07, 0.022, center=(0.13, 0, 0), matrix=M1)
    C.cyl_bm(bm, 0.055, -0.011, 0.011, seg=32, matrix=M1)
    lv = C.mesh_obj("Lever1", bm, [black])
    C.add_bevel(lv, 0.008, segments=2, angle=30)
    out.append(C.finalize(lv, angle=35))
    tip = M1 @ Vector((0.26, 0, 0))
    out.append(C.finalize(C.lathe("Ball1", [(0.0, 0.0, 0), (0.022, 0.0, 0), (0.022, 0.05, 0), (0.036, 0.07, 0), (0.036, 0.095, 0),
                                            (0.02, 0.11, 0), (0.0, 0.112, 0)], [zinc], steps=32), angle=50))
    out[-1].matrix_world = Matrix.Translation(tip)
    # second (selector) lever on a side pivot
    bm = bmesh.new()
    C.cyl_bm(bm, 0.05, 0.0, 0.08, seg=32, matrix=Matrix.Translation((0.30, -0.13, 0.50)))
    pv = C.mesh_obj("Pivot2", bm, [alu])
    C.add_bevel(pv, 0.01, segments=2, angle=30)
    out.append(C.finalize(pv, angle=35))
    bm = bmesh.new()
    M2 = Matrix.Translation((0.30, -0.13, 0.595)) @ Matrix.Rotation(math.radians(-150), 4, "Z")
    C.box_bm(bm, 0.24, 0.06, 0.02, center=(0.10, 0, 0), matrix=M2)
    C.cyl_bm(bm, 0.045, -0.01, 0.01, seg=32, matrix=M2)
    lv = C.mesh_obj("Lever2", bm, [black])
    C.add_bevel(lv, 0.007, segments=2, angle=30)
    out.append(C.finalize(lv, angle=35))
    tip = M2 @ Vector((0.20, 0, 0))
    out.append(C.finalize(C.lathe("Ball2", [(0.0, 0.0, 0), (0.02, 0.0, 0), (0.02, 0.045, 0), (0.032, 0.06, 0), (0.032, 0.085, 0),
                                            (0.018, 0.10, 0), (0.0, 0.10, 0)], [zinc], steps=32), angle=50))
    out[-1].matrix_world = Matrix.Translation(tip)
    out.append(hex_along("PivotNut", 0.03, 0.605, 0.635, zinc, Matrix.Translation((0.30, -0.13, 0)), bevel=0.004))
    # cable bracket: bent black plate with two U slots
    bm = bmesh.new()
    C.box_bm(bm, 0.20, 0.035, 0.30, center=(0.14, 0.17, 0.48))
    C.box_bm(bm, 0.20, 0.16, 0.035, center=(0.14, 0.10, 0.345))
    br = C.mesh_obj("CableBracket", bm, [black])
    cb = bmesh.new()
    for z in (0.53,):
        for x in (0.09, 0.19):
            C.box_bm(cb, 0.04, 0.2, 0.16, center=(x, 0.17, z + 0.06))
            C.cyl_bm(cb, 0.02, -0.1, 0.1, seg=24, matrix=Matrix.Translation((x, 0.17, z - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    cut = C.mesh_obj("Slots", cb, [black])
    C.add_boolean(br, cut)
    C.add_bevel(br, 0.008, segments=2, angle=30)
    out.append(C.finalize(br, angle=35, remove=[cut]))
    for x in (0.08, 0.20):
        out.append(hex_along("BrBolt", 0.026, 0.36, 0.39, zinc, Matrix.Translation((x, 0.06, 0)), bevel=0.004))
    return out


def mounts(alu, steel):
    out = []
    # gearbox mount pad on the end of the case: block with 3 bolt holes
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.24, 0.14, center=(0.74, 0.10, 0.36))
    mp = C.mesh_obj("MountPad", bm, [alu])
    cb = bmesh.new()
    for (x, y) in ((0.66, 0.04), (0.82, 0.04), (0.74, 0.17)):
        C.cyl_bm(cb, 0.026, 0.30, 0.50, seg=24, matrix=Matrix.Translation((x, y, 0)))
    cut = C.mesh_obj("MountHoles", cb, [alu])
    C.add_boolean(mp, cut)
    C.add_bevel(mp, 0.02, segments=3, angle=30)
    out.append(C.finalize(mp, angle=30, remove=[cut]))
    # lug with through-hole on the lower flank
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.20, 0.10, center=(0.20, -0.48, -0.42))
    C.cyl_bm(bm, 0.075, -0.47, -0.37, seg=40, matrix=Matrix.Translation((0.20, -0.58, 0)))
    lg = C.mesh_obj("Lug", bm, [alu])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.035, -0.6, -0.2, seg=24, matrix=Matrix.Translation((0.20, -0.58, 0)))
    cut = C.mesh_obj("LugHole", cb, [alu])
    C.add_boolean(lg, cut)
    C.add_bevel(lg, 0.015, segments=2, angle=30)
    out.append(C.finalize(lg, angle=30, remove=[cut]))
    # starter-motor bosses on the bell (top, +Y side)
    bm = bmesh.new()
    for a in (math.radians(70), math.radians(40)):
        C.cyl_bm(bm, 0.08, -0.60, -0.28, seg=40, matrix=Matrix.Translation((0, 0.74 * math.cos(a), 0.74 * math.sin(a))) @ RY)
    sb = C.mesh_obj("StarterBoss", bm, [alu])
    cb = bmesh.new()
    for a in (math.radians(70), math.radians(40)):
        C.cyl_bm(cb, 0.04, -0.7, -0.2, seg=24, matrix=Matrix.Translation((0, 0.74 * math.cos(a), 0.74 * math.sin(a))) @ RY)
    cut = C.mesh_obj("SBHoles", cb, [alu])
    C.add_boolean(sb, cut)
    C.add_bevel(sb, 0.012, segments=2, angle=30)
    out.append(C.finalize(sb, angle=30, remove=[cut]))
    return out


def build():
    alu = cast_alu("CastAlu", base=0.40, rough=0.50)
    steel = C.principled("Steel", (0.50, 0.51, 0.52), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=700, strength=0.04, distance=0.0006, rough_var=0.06)
    spline = C.mat_machined("Spline", color=0.58, rough=0.2, rings=0.0)
    zinc = C.principled("Zinc", (0.64, 0.65, 0.67), metallic=1.0, rough=0.25)
    black = C.mat_black_plastic("BlackPA", rough=0.42, color=0.025)
    blk_steel = C.principled("BlackSteel", (0.03, 0.03, 0.032), metallic=0.6, rough=0.42)
    rubber = C.mat_rubber("Seal")
    copper = C.principled("Copper", (0.8, 0.45, 0.28), metallic=1.0, rough=0.3)

    objs = []
    objs += bellhousing(alu)
    objs += input_shaft(steel, spline)
    objs += release_fork(blk_steel, rubber, alu)
    objs += gear_case(alu, zinc)
    objs += diff_lobe(alu, steel, rubber)
    objs += plugs_and_switch(alu, zinc, black, copper)
    objs += shift_tower(alu, steel, blk_steel, zinc)
    objs += mounts(alu, steel)
    C.transform_all(objs, Matrix.Rotation(math.radians(62), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("cambio", objs, "cambio.py",
            "manual transverse FWD gearbox: ribbed cast-aluminium case, open conical bellhousing with splined "
            "input shaft, differential lobe with two drive-shaft output flanges, shift tower with levers, plugs, "
            "reverse-light switch",
            az=35, el=24, lens=70, fill=0.84)
