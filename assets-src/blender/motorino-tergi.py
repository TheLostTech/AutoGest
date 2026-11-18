"""Windscreen wiper motor with linkage: black e-coated steel frame tube between two die-cast
pivot housings (rubber-bushed mounting ears, splined spindles with threaded tips and seal
caps), welded bracket plate carrying the motor (black can, die-cast worm gearbox with
round cover and connector socket), output crank and two linkage rods with ball sockets
driving the pivot levers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
PIV = [Vector((-1.0, 0.0, 0.0)), Vector((1.0, 0.04, 0.05))]
G = Vector((0.30, -0.13, 0.0))    # gearbox / output shaft (x, y)
ZL = -0.175                        # linkage plane (approx)


# ----------------------------------------------------------------- helpers
def oval(w, h, n=2.0, N=N):
    pts = []
    for k in range(N):
        a = TAU * k / N
        c, s = math.cos(a), math.sin(a)
        pts.append((w / 2 * math.copysign(abs(c) ** (2 / n), c), h / 2 * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


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


def loft(name, frames, mat, cap=True):
    bm = bmesh.new()
    C.sweep(bm, frames, cap=cap)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def frame_matrix(P, X, Z):
    X, Z = X.normalized(), Z.normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P.x), (X.y, Y.y, Z.y, P.y), (X.z, Y.z, Z.z, P.z), (0, 0, 0, 1)))


def path_pts(start, d, n, segs, step=0.02):
    """Planar pipe centre-line: segs = [('L', len) | ('A', radius, deg)] bending toward n."""
    P = Vector(start)
    d = Vector(d).normalized()
    n = Vector(n).normalized()
    b = d.cross(n).normalized()
    pts = [(P.copy(), d.copy())]
    for s in segs:
        if s[0] == "L":
            k = max(1, int(s[1] / step))
            for i in range(1, k + 1):
                pts.append((P + d * (s[1] * i / k), d.copy()))
            P = P + d * s[1]
        else:
            R, ang = s[1], math.radians(s[2])
            Cc = P + n * R
            k = max(2, int(R * abs(ang) / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, b)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, b)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts, b


def pipe(name, pts, b, r, mat, wall=0.009):
    sec = circle_pts(0, 0, r, 48)
    fr = [(P, b, t.cross(b), sec) for (P, t) in pts]
    ob = loft(name, fr, mat, cap=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def tube(name, pts, r, mat, res=3, caps=True):
    """Smooth bezier tube through pts (auto handles)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    cu.resolution_u = 16
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def boxes(name, specs, mat, bevel=0.01, holes=(), seg=2, M=None):
    """specs: [(sx, sy, sz, center[, matrix])]; holes: [(r, z0, z1, matrix)] boolean cylinders."""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, z0, z1, HM) in holes:
            C.cyl_bm(cb, r, z0, z1, seg=32, matrix=HM)
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2):
    """Extrude a 2D polygon along local Z, optional boolean holes [(r, cx, cy)] through it."""
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (z0, z1)]
    ob = loft(name, fr, mat)
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, cx, cy) in holes:
            C.cyl_bm(cb, r, z0 - 0.5, z1 + 0.5, seg=32, matrix=T((cx, cy, 0)))
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


# ----------------------------------------------------------------- materials
def mat_ecoat(name="Ecoat"):
    m = C.principled(name, (0.028, 0.028, 0.03), metallic=0.2, rough=0.42)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Coat Weight", 0.25)
    C._set(b, "Coat Roughness", 0.25)
    C.add_noise_bump(m, scale=500, strength=0.05, distance=0.0006, rough_var=0.06)
    return m


def mat_diecast(name, base=0.46, rough=0.42):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 9.0
    nz.inputs["Detail"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base * 0.80, base * 0.80, base * 0.78, 1)
    mix.inputs["B"].default_value = (base * 1.08, base * 1.08, base * 1.06, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 600.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_thread(name="Thread"):
    m = C.principled(name, (0.62, 0.62, 0.63), metallic=1.0, rough=0.3)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 160.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.8
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def pivot(P, cast, steel, spline_m, thread, rubber, ecoat, side):
    out = []
    M = T(P)
    H = [(0.0, -0.15, 0), (0.05, -0.15, 0), (0.05, -0.13, 0), (0.068, -0.12, 0), (0.068, 0.07, 0), (0.06, 0.09, 0),
         (0.045, 0.10, 0), (0.0, 0.10, 0)]
    out.append(lathe_at("PivotHousing", H, [cast], M, steps=64, bevel=0.004))
    # mounting ear toward +Y with rubber bush and steel sleeve
    ear_c = Vector((0, 0.15, -0.02))
    out.append(boxes("Ear", [(0.10, 0.16, 0.035, (0, 0.085, -0.02))], cast, bevel=0.01, M=M,
                     holes=[(0.046, -0.2, 0.2, T(ear_c))]))
    out.append(boxes("EarRib", [(0.025, 0.10, 0.07, (0, 0.06, -0.06))], cast, bevel=0.008, M=M))
    out.append(lathe_at("Bush", [(0.018, -0.07, 0), (0.05, -0.07, 0), (0.056, -0.055, 0), (0.044, -0.03, 0),
                                 (0.044, 0.0, 0), (0.056, 0.02, 0), (0.05, 0.035, 0), (0.018, 0.035, 0)],
                        [rubber], M @ T(ear_c), steps=48))
    out.append(lathe_at("Sleeve", [(0.011, -0.075, 0), (0.019, -0.075, 0), (0.019, 0.04, 0), (0.011, 0.04, 0)],
                        [steel], M @ T(ear_c), steps=32))
    # seal cap, spindle, splined tip, threaded end
    out.append(lathe_at("Seal", [(0.0, 0.095, 0), (0.05, 0.095, 0), (0.05, 0.11, 0), (0.035, 0.125, 0), (0.0, 0.125, 0)],
                        [rubber], M, steps=48))
    out.append(lathe_at("Spindle", [(0.0, 0.10, 0), (0.025, 0.10, 0), (0.025, 0.27, 0), (0.0, 0.27, 0)], [steel], M, steps=48))

    def spl(r, z, t):
        if r < 0.021 or z < 0.272 or z > 0.318:
            return r
        return r + 0.0028 * (1 if math.cos(22 * t) > 0 else -1)
    S = [(0.0, 0.27, 0), (0.025, 0.27, 0), (0.024, 0.275, 0), (0.024, 0.315, 0), (0.019, 0.322, 0), (0.0, 0.322, 0)]
    out.append(_spline(S, spl, spline_m, M))
    out.append(lathe_at("Stud", [(0.0, 0.32, 0), (0.0135, 0.32, 0), (0.0135, 0.39, 0), (0.011, 0.395, 0), (0.0, 0.395, 0)],
                        [thread], M, steps=40))
    # lever under the housing, ball pin at its end
    d = Vector((0, -1, 0)) if side < 0 else Vector((0.25, -1, 0)).normalized()
    ang = math.atan2(d.y, d.x)
    Ml = M @ Matrix.Rotation(ang, 4, "Z")
    out.append(prism("Lever", rrect(0.19, 0.06, 0.03, 6), -0.172, -0.150, ecoat, M=Ml @ T((0.075, 0, 0)), bevel=0.006))
    out.append(lathe_at("LeverHub", [(0.0, -0.18, 0), (0.035, -0.18, 0), (0.035, -0.148, 0), (0.0, -0.148, 0)],
                        [steel], M, steps=40, bevel=0.004))
    return out


def _spline(S, mod, mat, M):
    ob = C.lathe("Splines", S, [mat], steps=176, mod=mod)
    ob.matrix_world = M
    return C.finalize(ob, angle=30)


def ball_end(at, black, steel):
    out = []
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.034, matrix=T(at))
    out.append(C.mesh_obj("Socket", bm, [black]))
    out.append(lathe_at("SocketBoot", [(0.0, -0.03, 0), (0.03, -0.03, 0), (0.026, 0.02, 0), (0.0, 0.02, 0)],
                        [black], T(at + Vector((0, 0, 0.03))), steps=32, bevel=0.004))
    return out


def lever_ball(P, side):
    d = Vector((0, -1, 0)) if side < 0 else Vector((0.25, -1, 0)).normalized()
    return P + d * 0.15 + Vector((0, 0, -0.195))


def frame(ecoat, steel):
    out = []
    a, b = PIV
    pts = [(a.x + 0.05, a.y + 0.03, a.z - 0.03), (a.x + 0.30, 0.06, -0.04), (-0.30, 0.09, -0.05), (0.05, 0.08, -0.04),
           (0.50, 0.08, -0.02), (b.x - 0.25, b.y + 0.05, b.z - 0.02), (b.x - 0.05, b.y + 0.03, b.z - 0.02)]
    out.append(tube("FrameTube", pts, 0.032, ecoat, res=4))
    # bracket plate welded under the tube, carrying the motor gearbox
    out.append(prism("Bracket", rrect(0.46, 0.34, 0.06, 6), -0.055, -0.040, ecoat,
                     M=T((G.x - 0.02, -0.04, 0)), bevel=0.006,
                     holes=[(0.03, 0.17, 0.10)]))
    out.append(lathe_at("BracketBush", [(0.012, -0.07, 0), (0.045, -0.07, 0), (0.05, -0.05, 0), (0.045, -0.025, 0),
                                        (0.012, -0.025, 0)], [C.mat_rubber("BushRubber2")],
                        T((G.x + 0.15, 0.06, 0)), steps=40))
    return out


def motor(ecoat, cast, steel, black, pin_m):
    out = []
    zc = 0.03
    # gearbox body on top of the bracket + round worm-wheel cover
    out.append(prism("Gearbox", rrect(0.30, 0.25, 0.07, 8), -0.042, 0.05, cast, M=T((G.x, G.y, 0)), bevel=0.008))
    out.append(lathe_at("WheelCover", [(0.0, 0.045, 0), (0.115, 0.045, 0), (0.115, 0.075, 0), (0.10, 0.09, 0), (0.0, 0.092, 0)],
                        [cast], T((G.x + 0.02, G.y, 0)), steps=96, bevel=0.004))
    for k in range(4):
        th = TAU * k / 4 + 0.4
        out.append(hex_at("CoverScrew", 0.014, 0.05, 0.068, steel,
                          T((G.x + 0.02 + 0.128 * math.cos(th), G.y + 0.128 * math.sin(th), 0))))
    # worm housing tube toward the motor
    Rm = Matrix.Rotation(math.radians(-90), 4, "Y")   # local +Z -> world -X
    at = T((G.x - 0.12, G.y - 0.05, zc)) @ Rm
    out.append(lathe_at("WormTube", [(0.0, 0.0, 0), (0.055, 0.0, 0), (0.055, 0.10, 0), (0.0, 0.10, 0)], [cast], at, steps=64, bevel=0.006))
    can = [(0.0, 0.10, 0), (0.078, 0.10, 0), (0.078, 0.40, 0), (0.07, 0.415, 0), (0.035, 0.42, 0), (0.03, 0.44, 0), (0.0, 0.44, 0)]
    out.append(lathe_at("MotorCan", can, [ecoat], at, steps=96, bevel=0.003))
    out.append(lathe_at("CanFlange", [(0.05, 0.095, 0), (0.088, 0.095, 0), (0.088, 0.115, 0), (0.05, 0.115, 0)], [steel], at, steps=96, bevel=0.003))
    # connector socket on the gearbox side (opening toward +X)
    cx, cy, cz = G.x + 0.17, G.y - 0.02, 0.005
    bm = bmesh.new()
    C.box_bm(bm, 0.07, 0.12, 0.07, center=(cx, cy, cz))
    sh = C.mesh_obj("Conn", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 0.08, 0.095, 0.05, center=(cx + 0.02, cy, cz))
    cut = C.mesh_obj("ConnCut", cb, [black])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.004, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    out.append(boxes("ConnPins", [(0.05, 0.008, 0.008, (cx + 0.005, cy + (i - 2) * 0.018, cz)) for i in range(5)],
                     pin_m, bevel=0.0))
    # output shaft through the bracket, crank arm with ball pin underneath
    out.append(lathe_at("OutShaft", [(0.0, -0.215, 0), (0.024, -0.215, 0), (0.024, -0.04, 0), (0.0, -0.04, 0)], [steel],
                        T((G.x + 0.02, G.y, 0)), steps=40))
    out.append(prism("Crank", rrect(0.17, 0.06, 0.03, 6), -0.232, -0.212, ecoat,
                     M=T((G.x + 0.02, G.y, 0)) @ Matrix.Rotation(math.radians(-130), 4, "Z") @ T((0.06, 0, 0)), bevel=0.006))
    out.append(hex_at("CrankNut", 0.022, -0.25, -0.228, steel, T((G.x + 0.02, G.y, 0))))
    return out


def crank_ball():
    d = Matrix.Rotation(math.radians(-130), 3, "Z") @ Vector((0.12, 0, 0))
    return Vector((G.x + 0.02, G.y, -0.25)) + d


def rods(ecoat, black, steel):
    out = []
    cb = crank_ball()
    out += ball_end(cb, black, steel)
    for i, P in enumerate(PIV):
        side = -1 if i == 0 else 1
        lb = lever_ball(P, side)
        out += ball_end(lb, black, steel)
        a = cb + (lb - cb).normalized() * 0.03
        b = lb + (cb - lb).normalized() * 0.03
        mid = (a + b) / 2 + Vector((0, 0, -0.01))
        out.append(tube("Rod", [tuple(a), tuple(mid), tuple(b)], 0.014, ecoat, res=3))
    return out


def build():
    ecoat = mat_ecoat()
    cast = mat_diecast("DieCast", base=0.48)
    gear_m = mat_diecast("GearboxAlu", base=0.40, rough=0.48)
    steel = C.principled("Steel", (0.62, 0.62, 0.63), metallic=1.0, rough=0.22)
    C.add_noise_bump(steel, scale=800, strength=0.03, distance=0.0004)
    spline_m = C.mat_machined("Splined", color=0.6, rough=0.25, rings=300)
    thread = mat_thread()
    rubber = C.mat_rubber("Rubber")
    black = C.mat_black_plastic("PA66", rough=0.45, color=0.03)
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    objs = []
    for i, P in enumerate(PIV):
        objs += pivot(P, cast, steel, spline_m, thread, rubber, ecoat, -1 if i == 0 else 1)
    objs += frame(ecoat, steel)
    objs += motor(ecoat, gear_m, steel, black, pin_m)
    objs += rods(ecoat, black, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("motorino-tergi", objs, "motorino-tergi.py",
            "windscreen wiper motor with linkage: black frame tube, two pivot housings with splined spindles, "
            "motor with die-cast gearbox, crank arm and linkage rods with ball sockets",
            az=26, el=34, lens=70, fill=0.88,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
