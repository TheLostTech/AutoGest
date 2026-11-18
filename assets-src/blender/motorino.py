"""Starter motor: black-painted cylindrical motor yoke with rear end cap and through-bolt
heads, yellow-zinc solenoid piggy-backed on top (black cap, two terminal studs, one with
washer and nut, small spade terminal, copper strap to the field winding), cast-aluminium
nose housing with a two-ear mounting flange and bolt holes, machined steel pinion gear
protruding from the nose.

Built along +Z (rear cap -> pinion) with "up" = +Y, then laid on its side for the shot."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

SOL_Y = 0.635       # solenoid axis height (build space)
SOL_R = 0.205
EARS = (math.radians(196), math.radians(-16))   # flange ear directions
EAR_D = 0.565


# ----------------------------------------------------------------- local helpers
def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(pts) < 3:
        return pts

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


def worn_paint(name, color, rough=0.36, coat=0.35, wear=0.85, metal=0.50, edge=0.014, scale=11.0):
    """Painted steel with orange-peel bump and paint rubbed through to bare metal on edges."""
    m = C.mat_paint(name, color, rough=rough, coat=coat)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    em = C.edge_mask(nt, edge, 7.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f1 = nt.nodes.new("ShaderNodeMath"); f1.operation = "MULTIPLY"; f1.use_clamp = True
    nt.links.new(em, f1.inputs[0]); nt.links.new(mr.outputs["Result"], f1.inputs[1])
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"; f2.use_clamp = True
    f2.inputs[1].default_value = wear
    nt.links.new(f1.outputs[0], f2.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = color if len(color) == 4 else tuple(color) + (1,)
    mix.inputs["B"].default_value = (metal, metal, metal * 1.02, 1)
    nt.links.new(f2.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(f2.outputs[0], b.inputs["Metallic"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough
    rr.inputs["To Max"].default_value = 0.42
    nt.links.new(f2.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    cw = nt.nodes.new("ShaderNodeMapRange")
    cw.inputs["To Min"].default_value = coat
    cw.inputs["To Max"].default_value = 0.0
    nt.links.new(f2.outputs[0], cw.inputs["Value"])
    nt.links.new(cw.outputs["Result"], b.inputs["Coat Weight"])
    # orange peel
    pk = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), pk.inputs["Vector"])
    pk.inputs["Scale"].default_value = 260.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.05
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(pk.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def cast_alu(name, base=0.44, rough=0.48):
    """Die-cast aluminium: mottled tone, fine grain bump, grime in crevices (AO)."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.10
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 0.85
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.05, base * 1.03, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.78, base * 0.72, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.095, 0.085, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.10
    rr.inputs["To Max"].default_value = rough + 0.22
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 450.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.14
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def thread_mat(name, color, rough=0.3, pitch_scale=55.0):
    """Zinc/brass threaded rod: wave bands along build Z."""
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"; wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = pitch_scale
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.9
    bp.inputs["Distance"].default_value = 0.004
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def ring(name, r0, r1, z0, z1, mat, steps=64, at=(0, 0), ch=0.0):
    P = [(r0, z0, 0), (r1 - ch, z0, 0), (r1, z0 + ch, 0), (r1, z1 - ch, 0), (r1 - ch, z1, 0), (r0, z1, 0)]
    ob = C.lathe(name, P, [mat], steps=steps)
    ob.matrix_world = Matrix.Translation((at[0], at[1], 0))
    return C.finalize(ob, angle=40)


def hexnut(name, r, z0, z1, mat, at=(0, 0), bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=Matrix.Translation((at[0], at[1], 0)) @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


# ----------------------------------------------------------------- parts
def yoke(paint):
    P = [(0.0, -0.585, 0), (0.385, -0.585, 0), (0.40, -0.57, 0), (0.40, 0.445, 0), (0.39, 0.455, 0), (0.0, 0.455, 0)]
    ob = C.lathe("Yoke", P, [paint], steps=160)
    return C.finalize(ob, angle=40)


def rear_cap(paint, steel):
    P = [(0.0, -0.765, 0), (0.085, -0.765, 0), (0.105, -0.755, 0), (0.118, -0.735, 0), (0.125, -0.70, 0),
         (0.16, -0.685, 0), (0.30, -0.672, 0), (0.355, -0.655, 0), (0.383, -0.628, 0), (0.394, -0.60, 0),
         (0.394, -0.575, 0), (0.0, -0.575, 0)]
    ob = C.lathe("RearCap", P, [paint], steps=128)
    C.add_bevel(ob, 0.004, segments=2, angle=30)
    out = [C.finalize(ob, angle=40)]
    # through-bolt heads with washers
    for th in (math.radians(160), math.radians(-20)):
        x, y = 0.322 * math.cos(th), 0.322 * math.sin(th)
        out.append(ring("TBWasher", 0.0, 0.05, -0.684, -0.672, steel, at=(x, y), ch=0.002))
        out.append(hexnut("TBHead", 0.036, -0.72, -0.684, steel, at=(x, y), bevel=0.005))
    # rear bushing plug
    out.append(ring("Plug", 0.0, 0.06, -0.78, -0.765, steel, ch=0.004))
    return out


def nose(alu, steel, black):
    out = []
    # collar that seats on the yoke
    P = [(0.36, 0.43, 0), (0.408, 0.43, 0), (0.418, 0.445, 0), (0.418, 0.53, 0), (0.36, 0.53, 0)]
    col = C.lathe("NoseCollar", P, [alu], steps=160)
    C.add_bevel(col, 0.004, segments=2, angle=30)
    out.append(C.finalize(col, angle=40))
    # mounting flange: hull of body, ears and solenoid seat
    pts = circle_pts(0, 0, 0.43, 96) + circle_pts(0, SOL_Y, SOL_R + 0.035, 64)
    for a in EARS:
        pts += circle_pts(EAR_D * math.cos(a), EAR_D * math.sin(a), 0.105, 48)
    sec = hull2d(pts)
    bm = bmesh.new()
    frames = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (0.525, 0.625)]
    C.sweep(bm, frames)
    C.fix_normals(bm)
    fl = C.mesh_obj("Flange", bm, [alu])
    cb = bmesh.new()
    for a in EARS:
        C.cyl_bm(cb, 0.056, 0.40, 0.75, seg=40, matrix=Matrix.Translation((EAR_D * math.cos(a), EAR_D * math.sin(a), 0)))
    cut = C.mesh_obj("EarHoles", cb, [alu])
    C.add_boolean(fl, cut)
    C.add_bevel(fl, 0.012, segments=3, angle=30)
    out.append(C.finalize(fl, angle=35, remove=[cut]))
    # ear spot-faces (raised bosses on the drive side)
    for a in EARS:
        x, y = EAR_D * math.cos(a), EAR_D * math.sin(a)
        b = C.lathe("EarBoss", [(0.056, 0.62, 0), (0.10, 0.62, 0), (0.10, 0.655, 0), (0.092, 0.665, 0), (0.056, 0.665, 0)], [alu], steps=48)
        b.matrix_world = Matrix.Translation((x, y, 0))
        out.append(C.finalize(b, angle=40))
    # steel locating sleeve in one ear
    x, y = EAR_D * math.cos(EARS[1]), EAR_D * math.sin(EARS[1])
    out.append(ring("Dowel", 0.042, 0.054, 0.50, 0.70, steel, at=(x, y), ch=0.003))
    # snout
    P = [(0.17, 0.86, 0), (0.0, 0.86, 0), (0.0, 0.62, 0), (0.385, 0.62, 0), (0.37, 0.68, 0), (0.33, 0.75, 0),
         (0.285, 0.84, 0), (0.262, 0.93, 0), (0.255, 0.985, 0), (0.24, 1.0, 0), (0.185, 1.0, 0),
         (0.172, 0.99, 0)]
    sn = C.lathe("Snout", P, [alu], steps=160)
    # window on the underside where the pinion meshes with the ring gear
    cb = bmesh.new()
    C.box_bm(cb, 0.34, 0.30, 0.30, center=(0, -0.30, 0.90))
    w = C.mesh_obj("Window", cb, [alu])
    C.add_boolean(sn, w)
    C.add_bevel(sn, 0.006, segments=2, angle=30)
    out.append(C.finalize(sn, angle=38, remove=[w]))
    # casting ribs between snout and flange
    bm = bmesh.new()
    for a in (math.radians(30), math.radians(150), math.radians(-90 + 32), math.radians(-90 - 32)):
        Rz = Matrix.Rotation(a, 4, "Z")
        for i in range(1):
            M = Rz @ Matrix.Translation((0.33, 0, 0.70)) @ Matrix.Rotation(math.radians(-38), 4, "Y")
            C.box_bm(bm, 0.035, 0.03, 0.17, matrix=M)
    rb = C.mesh_obj("NoseRibs", bm, [alu])
    C.add_bevel(rb, 0.008, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # cheese-head screws clamping the collar to the yoke
    for a in (math.radians(140), math.radians(250)):
        M = Matrix.Translation((0.425 * math.cos(a), 0.425 * math.sin(a), 0.48)) @ \
            Vector((math.cos(a), math.sin(a), 0)).to_track_quat("Z", "X").to_matrix().to_4x4()
        out.append(C.finalize(C.lathe("CollarScrew", [(0.0, 0.0, 0), (0.03, 0.0, 0), (0.03, 0.022, 0), (0.024, 0.03, 0),
                                                      (0.0, 0.03, 0)], [steel], steps=32), angle=40))
        out[-1].matrix_world = M
    # inner drive: clutch drum visible through the window
    out.append(ring("Clutch", 0.06, 0.15, 0.80, 0.93, steel, steps=96, ch=0.01))
    return out


def pinion(gear, steel):
    NT = 11

    def teeth(r, z, t):
        if r < 0.12:
            return r
        v = math.cos(NT * t)
        sq = max(-1.0, min(1.0, v * 1.9)) * 0.5 + 0.5
        return r - 0.038 * (1 - sq)

    P = [(0.045, 0.93, 0), (0.15, 0.93, 0), (0.163, 0.945, 0), (0.163, 1.135, 0), (0.148, 1.155, 0),
         (0.06, 1.155, 0), (0.045, 1.14, 0)]
    ob = C.lathe("Pinion", P, [gear], steps=NT * 16, mod=teeth)
    out = [C.finalize(ob, angle=30)]
    # shaft end with circlip groove and bushing nose
    P = [(0.0, 0.92, 0), (0.046, 0.92, 0), (0.046, 1.19, 0), (0.040, 1.195, 0), (0.040, 1.205, 0),
         (0.046, 1.21, 0), (0.046, 1.235, 0), (0.036, 1.25, 0), (0.0, 1.25, 0)]
    sh = C.lathe("Shaft", P, [steel], steps=64)
    out.append(C.finalize(sh, angle=40))
    out.append(ring("StopRing", 0.046, 0.075, 1.155, 1.175, steel, ch=0.004))
    return out


def solenoid(can, black, zinc, thread, copper, rubber):
    out = []
    at = (0, SOL_Y)
    P = [(0.0, -0.30, 0), (0.185, -0.30, 0), (0.200, -0.29, 0), (0.205, -0.27, 0), (0.205, 0.40, 0),
         (0.212, 0.41, 0), (0.212, 0.50, 0), (0.205, 0.52, 0), (0.0, 0.52, 0)]
    ob = C.lathe("SolCan", P, [can], steps=128)
    ob.matrix_world = Matrix.Translation((at[0], at[1], 0))
    C.add_bevel(ob, 0.004, segments=2, angle=30)
    out.append(C.finalize(ob, angle=40))
    # rolled crimp lip holding the cap
    out.append(ring("Crimp", 0.17, 0.212, -0.325, -0.29, can, steps=128, at=at, ch=0.008))
    # black terminal cap
    P = [(0.0, -0.435, 0), (0.13, -0.435, 0), (0.16, -0.425, 0), (0.178, -0.40, 0), (0.183, -0.33, 0),
         (0.19, -0.31, 0), (0.0, -0.31, 0)]
    cap = C.lathe("SolCap", P, [black], steps=96)
    cap.matrix_world = Matrix.Translation((at[0], at[1], 0))
    out.append(C.finalize(cap, angle=40))
    # terminal studs (B+ toward camera with washer + nut, M with copper strap)
    studs = {"B": (-0.082, SOL_Y + 0.035), "M": (0.082, SOL_Y + 0.035)}
    for k, (x, y) in studs.items():
        out.append(ring("TermBoss" + k, 0.0, 0.058, -0.455, -0.43, black, at=(x, y), ch=0.008))
        out.append(hexnut("TermHex" + k, 0.048, -0.495, -0.455, copper, at=(x, y), bevel=0.005))
        out.append(ring("Stud" + k, 0.0, 0.024, -0.64, -0.49, thread, steps=32, at=(x, y), ch=0.004))
    xb, yb = studs["B"]
    out.append(ring("WasherB", 0.026, 0.056, -0.535, -0.525, zinc, at=(xb, yb), ch=0.002))
    out.append(ring("SpringWB", 0.026, 0.044, -0.545, -0.535, zinc, at=(xb, yb), ch=0.002))
    out.append(hexnut("NutB", 0.044, -0.59, -0.545, zinc, at=(xb, yb), bevel=0.006))
    # M: ring terminal + flat copper strap down into the yoke
    xm, ym = studs["M"]
    out.append(ring("RingTerm", 0.026, 0.06, -0.505, -0.495, copper, at=(xm, ym), ch=0.002))
    out.append(hexnut("NutM", 0.042, -0.545, -0.505, zinc, at=(xm, ym), bevel=0.006))
    path = [(ym - 0.03, -0.50), (ym - 0.10, -0.50), (ym - 0.17, -0.505), (ym - 0.205, -0.49),
            (ym - 0.225, -0.46), (ym - 0.235, -0.43)]
    frames = []
    for i, (y, z) in enumerate(path):
        a = path[max(i - 1, 0)]
        c = path[min(i + 1, len(path) - 1)]
        T = Vector((0, c[0] - a[0], c[1] - a[1])).normalized()
        U = Vector((1, 0, 0))
        V = T.cross(U).normalized()
        frames.append((Vector((xm, y, z)), U, V, [(-0.03, -0.006), (0.03, -0.006), (0.03, 0.006), (-0.03, 0.006)]))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    st = C.mesh_obj("Strap", bm, [copper])
    C.add_bevel(st, 0.003, segments=1, angle=30)
    out.append(C.finalize(st, angle=40))
    # rubber grommet on the yoke where the strap enters
    y0 = math.sqrt(0.40 ** 2 - xm ** 2) - 0.01
    g = C.lathe("Grommet", [(0.0, 0.0, 0), (0.055, 0.0, 0), (0.05, 0.03, 0), (0.035, 0.045, 0), (0.0, 0.045, 0)], [rubber], steps=48)
    g.matrix_world = Matrix.Translation((xm, y0, -0.43)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    out.append(C.finalize(g, angle=45))
    # small S (ignition) spade terminal on the cap
    bm = bmesh.new()
    C.box_bm(bm, 0.06, 0.035, 0.03, center=(0, SOL_Y - 0.085, -0.45))
    sb = C.mesh_obj("SBoss", bm, [black])
    C.add_bevel(sb, 0.006, segments=2, angle=30)
    out.append(C.finalize(sb, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.032, 0.006, 0.07, center=(0, SOL_Y - 0.085, -0.495))
    sp = C.mesh_obj("Spade", bm, [copper])
    C.add_bevel(sp, 0.002, segments=1, angle=30)
    out.append(C.finalize(sp, angle=35))
    return out


def label(r=0.4015, th0=math.radians(200), th1=math.radians(262), z0=-0.38, z1=0.10):
    """Blank adhesive label wrapped on the yoke (no readable text)."""
    im = C.label_image("StarterLabel", 1024, 640, seed=7, lines=4)
    mat = C.mat_label(im, rough=0.42)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    NU, NV = 24, 2
    grid = [[bm.verts.new((r * math.cos(th0 + (th1 - th0) * i / NU), r * math.sin(th0 + (th1 - th0) * i / NU),
                          z0 + (z1 - z0) * j / NV)) for j in range(NV + 1)] for i in range(NU + 1)]
    for i in range(NU):
        for j in range(NV):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                # u along the axis (z), v around -> text runs along the motor
                l[uv].uv = (b / NV, 1 - a / NU)
            f.smooth = True
    bm.normal_update()
    ob = C.mesh_obj("Label", bm, [mat])
    return ob


def build():
    paint = worn_paint("YokePaint", (0.018, 0.018, 0.02, 1), rough=0.44, coat=0.18, wear=0.9)
    cap_paint = worn_paint("CapPaint", (0.03, 0.03, 0.032, 1), rough=0.48, coat=0.1, wear=0.8)
    alu = cast_alu("CastAlu", base=0.44, rough=0.46)
    steel = C.principled("ZincSteel", (0.58, 0.59, 0.61), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    gear = C.mat_machined("PinionSteel", color=0.60, rough=0.18, rings=900.0)
    can = C.principled("YellowZinc", (0.66, 0.61, 0.47), metallic=1.0, rough=0.32)
    C.add_noise_bump(can, scale=500, strength=0.04, distance=0.0006, rough_var=0.06)
    black = C.mat_black_plastic("CapPBT", rough=0.38, color=0.02)
    zinc = C.principled("ZincNut", (0.66, 0.67, 0.69), metallic=1.0, rough=0.22)
    thread = thread_mat("StudThread", (0.72, 0.56, 0.36), rough=0.32)
    copper = C.principled("Copper", (0.80, 0.45, 0.28), metallic=1.0, rough=0.30)
    C.add_noise_bump(copper, scale=600, strength=0.05, distance=0.0006, rough_var=0.06)
    rubber = C.mat_rubber("Grommet")

    objs = [yoke(paint)]
    objs += rear_cap(cap_paint, steel)
    objs += nose(alu, steel, black)
    objs += pinion(gear, steel)
    objs += solenoid(can, black, zinc, thread, copper, rubber)
    objs.append(label())
    # axis Z -> horizontal, pinion toward the front-right; solenoid on top
    C.transform_all(objs, Matrix.Rotation(math.radians(98), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("motorino", objs, "motorino.py",
            "car starter motor: black-painted yoke, yellow-zinc solenoid with terminal studs and nut, "
            "cast-aluminium nose with two-ear mounting flange, machined steel pinion gear",
            az=35, el=22, lens=70, fill=0.84)
