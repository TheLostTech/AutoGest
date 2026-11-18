"""In-tank fuel pump module: black acetal top flange with fuel outlet, return nipple and an
electrical connector; two stainless guide rods with springs; dark reservoir bucket with
the zinc-plated pump cylinder rising out of it, corrugated fuel hose and leads to the
flange; level sender with ceramic resistor card, wire float arm and black float; woven
filter sock underneath."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
ZF = 1.0           # flange underside
BC = (0.0, 0.02)   # bucket centre
BR = 0.235         # bucket radius
ZB0, ZB1 = 0.09, 0.62
PC = (0.05, -0.03)  # pump centre
RODS = [(-0.165, 0.215), (0.165, 0.215)]


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
def mat_mesh(name="SockMesh"):
    m = C.principled(name, (0.70, 0.70, 0.66), rough=0.75)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Sheen Weight", 0.4)
    w1 = nt.nodes.new("ShaderNodeTexWave")
    w1.bands_direction = "X"
    w1.inputs["Scale"].default_value = 90.0
    w2 = nt.nodes.new("ShaderNodeTexWave")
    w2.bands_direction = "Y"
    w2.inputs["Scale"].default_value = 90.0
    for w in (w1, w2):
        nt.links.new(C._coord(nt), w.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(w1.outputs["Fac"], mul.inputs[0])
    nt.links.new(w2.outputs["Fac"], mul.inputs[1])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(mul.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mul.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.40, 0.40, 0.37, 1)
    mix.inputs["B"].default_value = (0.62, 0.62, 0.58, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_corrugated(name="FuelHose"):
    m = C.principled(name, (0.03, 0.03, 0.032), rough=0.45)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 70.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.9
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def flange(black):
    P = [(0.0, ZF - 0.015, 0), (0.205, ZF - 0.015, 0), (0.21, ZF, 0), (0.30, ZF, 0), (0.306, ZF + 0.006, 0),
         (0.306, ZF + 0.036, 0), (0.298, ZF + 0.043, 0), (0.175, ZF + 0.043, 0), (0.168, ZF + 0.07, 0),
         (0.16, ZF + 0.075, 0), (0.0, ZF + 0.075, 0)]
    out = [lathe_at("Flange", P, [black], Matrix(), steps=128)]
    # radial stiffening ribs on the top face
    specs = []
    for k in range(10):
        th = TAU * k / 10 + 0.15
        M = Matrix.Rotation(th, 4, "Z")
        specs.append((0.11, 0.016, 0.026, (0.235, 0, ZF + 0.052), M))
    out.append(boxes("FlangeRibs", specs, black, bevel=0.005))
    return out


def fittings(black, pin_m):
    out = []
    # fuel outlet: vertical stub, 90 deg bend toward +X, barbed quick-connect end
    pts, b = path_pts((0.09, 0.06, ZF + 0.06), (0, 0, 1), (1, 0, 0), [("L", 0.06), ("A", 0.06, 90), ("L", 0.15)])
    out.append(pipe("Outlet", pts, b, 0.030, black, wall=0.010))
    for i in (-12, -6):
        P, t = pts[i]
        out.append(lathe_at("Barb", [(0.025, -0.012, 0), (0.040, 0.0, 0), (0.040, 0.010, 0), (0.025, 0.010, 0)],
                            [black], frame_matrix(P, b, t), steps=48))
    out.append(lathe_at("OutletBase", [(0.0, ZF + 0.07, 0), (0.05, ZF + 0.07, 0), (0.05, ZF + 0.095, 0), (0.0, ZF + 0.095, 0)],
                        [black], T((0.09, 0.06, 0)), steps=48, bevel=0.005))
    # return / vent nipple toward -X
    pts, b = path_pts((-0.06, 0.13, ZF + 0.06), (0, 0, 1), (-1, 0, 0), [("L", 0.05), ("A", 0.045, 90), ("L", 0.10)])
    out.append(pipe("Return", pts, b, 0.021, black, wall=0.008))
    out.append(lathe_at("ReturnBase", [(0.0, ZF + 0.07, 0), (0.038, ZF + 0.07, 0), (0.038, ZF + 0.09, 0), (0.0, ZF + 0.09, 0)],
                        [black], T((-0.06, 0.13, 0)), steps=48, bevel=0.004))
    # electrical connector socket facing -Y with pins
    cx, cy, cz = -0.07, -0.10, ZF + 0.115
    w, d, h = 0.17, 0.11, 0.085
    bm = bmesh.new()
    C.box_bm(bm, w, d, h, center=(cx, cy, cz))
    sh = C.mesh_obj("Socket", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, w - 0.03, d, h - 0.03, center=(cx, cy - 0.025, cz))
    cut = C.mesh_obj("SocketCut", cb, [black])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.004, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    out.append(boxes("SocketBase", [(w - 0.02, d - 0.02, 0.05, (cx, cy + 0.005, ZF + 0.06)),
                                    (0.06, 0.02, 0.022, (cx, cy - d / 2 + 0.03, cz + h / 2 + 0.008))], black, bevel=0.005))
    specs = [(0.012, 0.07, 0.012, (cx + (i - 1.5) * 0.032, cy - 0.01, cz)) for i in range(4)]
    out.append(boxes("SocketPins", specs, pin_m, bevel=0.0))
    return out


def rods(steel, spring_m):
    out = []
    for (x, y) in RODS:
        out.append(lathe_at("Rod", [(0.0, 0.40, 0), (0.016, 0.40, 0), (0.016, ZF, 0), (0.0, ZF, 0)], [steel], T((x, y, 0)), steps=32))
        out.append(lathe_at("RodSleeve", [(0.0, ZF - 0.06, 0), (0.03, ZF - 0.06, 0), (0.03, ZF, 0), (0.0, ZF, 0)],
                            [steel], T((x, y, 0)), steps=32, bevel=0.004))
        # coil spring
        cu = bpy.data.curves.new("Spring", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.0055
        cu.bevel_resolution = 2
        sp = cu.splines.new("POLY")
        turns, z0, z1, r = 9, 0.66, ZF - 0.06, 0.031
        n = turns * 24
        sp.points.add(n)
        for i in range(n + 1):
            a = TAU * turns * i / n
            sp.points[i].co = (x + r * math.cos(a), y + r * math.sin(a), z0 + (z1 - z0) * i / n, 1)
        ob = C.link(bpy.data.objects.new("Spring", cu))
        cu.materials.append(spring_m)
        out.append(C.finalize(ob, angle=50))
    return out


def bucket(grey):
    def ribs(r, z, t):
        if r < BR - 0.001 or not (ZB0 + 0.05 < z < ZB1 - 0.06):
            return r
        v = math.cos(20 * t)
        return r + 0.008 * max(0.0, v * 4 - 3)
    P = [(0.0, ZB0, 0), (BR - 0.02, ZB0, 0), (BR, ZB0 + 0.02, 0), (BR, ZB1 - 0.05, 0), (BR + 0.012, ZB1 - 0.04, 0),
         (BR + 0.012, ZB1, 0), (BR - 0.012, ZB1, 0), (BR - 0.012, ZB0 + 0.04, 0), (0.0, ZB0 + 0.04, 0)]
    out = [lathe_at("Bucket", P, [grey], T((BC[0], BC[1], 0)), steps=160, angle=40)]
    # guide bosses for the rods, joined to the bucket wall
    for (x, y) in RODS:
        out.append(lathe_at("Boss", [(0.0, 0.36, 0), (0.038, 0.36, 0), (0.038, ZB1 - 0.01, 0), (0.0, ZB1 - 0.01, 0)],
                            [grey], T((x, y, 0)), steps=40, bevel=0.006))
        d = Vector((x - BC[0], y - BC[1], 0))
        L = d.length
        M = T((BC[0], BC[1], 0)) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z")
        out.append(boxes("BossWeb", [(L - BR + 0.01, 0.022, ZB1 - 0.38, ((L + BR) / 2 - 0.01, 0, (0.37 + ZB1) / 2 - 0.005), M)],
                         grey, bevel=0.005))
    return out


def pump(zinc, black, hose_m, red_m, wire_m):
    out = []
    P = [(0.0, 0.25, 0), (0.085, 0.25, 0), (0.085, 0.78, 0), (0.0, 0.78, 0)]
    out.append(lathe_at("PumpCan", P, [zinc], T((PC[0], PC[1], 0)), steps=96))
    # crimped seam ring + black top cap with outlet nipple and terminals
    out.append(lathe_at("Crimp", [(0.08, 0.70, 0), (0.091, 0.70, 0), (0.093, 0.715, 0), (0.091, 0.73, 0), (0.08, 0.73, 0)],
                        [zinc], T((PC[0], PC[1], 0)), steps=96))
    cap = [(0.0, 0.78, 0), (0.088, 0.78, 0), (0.088, 0.81, 0), (0.07, 0.83, 0), (0.0, 0.83, 0)]
    out.append(lathe_at("PumpCap", cap, [black], T((PC[0], PC[1], 0)), steps=96, bevel=0.004))
    nip = (PC[0] + 0.03, PC[1] + 0.03)
    out.append(lathe_at("Nipple", [(0.0, 0.83, 0), (0.022, 0.83, 0), (0.022, 0.88, 0), (0.027, 0.89, 0), (0.022, 0.90, 0),
                                   (0.0, 0.90, 0)], [black], T((nip[0], nip[1], 0)), steps=40))
    for k, (dx, dy) in enumerate(((-0.045, -0.02), (-0.02, -0.055))):
        out.append(boxes("Term", [(0.012, 0.022, 0.035, (PC[0] + dx, PC[1] + dy, 0.845))], zinc, bevel=0.002))
    # corrugated hose: pump nipple -> flange underside (under the outlet)
    hp = [(nip[0], nip[1], 0.88), (nip[0], nip[1], 0.92), (0.08, 0.06, 0.95), (0.09, 0.06, ZF - 0.01)]
    out.append(tube("Hose", hp, 0.025, hose_m, res=4))
    for z in (0.885, ZF - 0.035):
        cpt = (nip[0], nip[1]) if z < 0.9 else (0.09, 0.06)
        out.append(lathe_at("Clamp", [(0.0, z - 0.01, 0), (0.03, z - 0.01, 0), (0.03, z + 0.01, 0), (0.0, z + 0.01, 0)],
                            [zinc], T((cpt[0], cpt[1], 0)), steps=32))
    # leads from the flange to the pump terminals
    for (dx, dy), m, xo in (((-0.045, -0.02), red_m, -0.02), ((-0.02, -0.055), wire_m, -0.05)):
        t0 = Vector((PC[0] + dx, PC[1] + dy, 0.86))
        pts = [t0, t0 + Vector((0, 0, 0.04)), Vector((xo - 0.05, -0.09, 0.93)), Vector((xo, -0.08, ZF - 0.005))]
        out.append(tube("Lead", pts, 0.0075, m, res=2))
    return out


def sender(black, ceramic, trace, wire_m, float_m):
    out = []
    a = math.radians(-128)
    cx, cy = BC[0] + (BR + 0.03) * math.cos(a), BC[1] + (BR + 0.03) * math.sin(a)
    Rz = Matrix.Rotation(a, 4, "Z")
    M = T((cx, cy, 0)) @ Rz
    out.append(boxes("SenderBody", [(0.06, 0.15, 0.20, (0, 0, 0.42))], black, bevel=0.008, M=M))
    out.append(boxes("Card", [(0.006, 0.11, 0.09, (0.033, 0.0, 0.40))], ceramic, bevel=0.0, M=M))
    out.append(boxes("Traces", [(0.002, 0.10, 0.004, (0.037, 0.0, 0.37 + 0.007 * i)) for i in range(7)] +
                     [(0.002, 0.012, 0.08, (0.037, 0.04, 0.40))], trace, bevel=0.0, M=M))
    # wiper pivot + float arm
    piv = M @ Vector((0.045, -0.02, 0.45))
    out.append(lathe_at("Pivot", [(0.0, 0.0, 0), (0.028, 0.0, 0), (0.028, 0.02, 0), (0.0, 0.02, 0)], [black],
                        T(piv) @ Rz @ Matrix.Rotation(math.radians(90), 4, "Y"), steps=32, bevel=0.004))
    d = Rz @ Vector((1, 0, 0))
    s = Rz @ Vector((0, -1, 0))
    p0 = piv + d * 0.02
    pts = [p0, p0 + d * 0.05, p0 + d * 0.09 + s * 0.04 + Vector((0, 0, -0.04)),
           p0 + d * 0.32 + s * 0.10 + Vector((0, 0, -0.17)), p0 + d * 0.44 + s * 0.13 + Vector((0, 0, -0.23))]
    out.append(tube("FloatArm", [tuple(p) for p in pts], 0.0065, wire_m, res=2))
    fp = pts[-1] + d * 0.06
    Mf = T(fp) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z") @ Matrix.Rotation(math.radians(-12), 4, "Y")
    out.append(prism("Float", rrect(0.17, 0.10, 0.03, 6), -0.035, 0.035, float_m, M=Mf, bevel=0.012, seg=3))
    return out


def sock(mesh_m, black):
    fr = []
    cx, cy = 0.10, -0.02
    for z, s in ((0.0, 0.80), (0.015, 0.95), (0.04, 1.0), (0.065, 0.94), (0.085, 0.72), (0.092, 0.45)):
        fr.append((Vector((cx, cy, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), oval(0.46 * s, 0.34 * s, 2.6)))
    ob = loft("Sock", fr, mesh_m)
    out = [C.finalize(ob, angle=50)]
    # moulded clip ring that holds the sock to the bucket inlet
    out.append(lathe_at("SockClip", [(0.0, 0.06, 0), (0.06, 0.06, 0), (0.06, 0.09, 0), (0.0, 0.09, 0)], [black],
                        T((0.02, 0.0, 0)), steps=48, bevel=0.005))
    return out


def build():
    black = C.mat_black_plastic("Acetal", rough=0.40, color=0.03)
    grey = C.mat_black_plastic("BucketPOM", rough=0.46, color=0.045)
    steel = C.principled("Stainless", (0.62, 0.62, 0.63), metallic=1.0, rough=0.18)
    C.add_noise_bump(steel, scale=800, strength=0.03, distance=0.0004)
    spring_m = C.principled("SpringSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    zinc = C.principled("ZincPlate", (0.66, 0.66, 0.68), metallic=1.0, rough=0.22)
    C.add_noise_bump(zinc, scale=600, strength=0.04, distance=0.0005, rough_var=0.05)
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    hose_m = mat_corrugated()
    red_m = C.principled("RedWire", (0.45, 0.03, 0.03), rough=0.4)
    wire_m = C.principled("WireSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.25)
    blk_wire = C.principled("BlackWire", (0.025, 0.025, 0.025), rough=0.4)
    ceramic = C.principled("Ceramic", (0.80, 0.78, 0.72), rough=0.5)
    trace = C.principled("Trace", (0.12, 0.10, 0.08), metallic=0.6, rough=0.35)
    float_m = C.mat_black_plastic("FloatFoam", rough=0.78, color=0.035)
    objs = flange(black) + fittings(black, pin_m) + rods(steel, spring_m) + bucket(grey)
    objs += pump(zinc, black, hose_m, red_m, blk_wire)
    objs += sender(black, ceramic, trace, wire_m, float_m)
    objs += sock(mat_mesh(), black)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("pompa-carburante", objs, "pompa-carburante.py",
            "in-tank fuel pump module: black flange with fuel outlet, return nipple and connector, guide rods with "
            "springs, reservoir bucket with pump cylinder, level sender with float arm, filter sock",
            az=32, el=16, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
