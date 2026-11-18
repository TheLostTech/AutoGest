"""Electric window regulator, dual-rail cable type: two curved zinc-plated C-section guide
rails with end brackets and white pulleys, black glass-clamp carriers with clamp bolts,
steel cables (one crossing between the rails), black cable sheaths running to the cable
drum housing, and the electric motor (can, worm housing, connector socket) mounted on it."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
XR = 0.52                     # rail half spacing
Z0, Z1 = 0.0, 1.55            # rail ends
YF = -0.045                   # cable line in front of the rails
D = Vector((0.0, 0.12, 0.56))  # cable drum centre
SC = 1.4                       # scale of the drum/motor unit
RY_ = Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> world -Y


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


def yc(z):
    """Rails follow the glass curvature (ends further back)."""
    return 0.07 * ((z - 0.78) / 0.78) ** 2


# ----------------------------------------------------------------- materials
def mat_zinc(name="ZincRail"):
    m = C.principled(name, (0.60, 0.61, 0.62), metallic=1.0, rough=0.32)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 30.0
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.22
    mr.inputs["To Max"].default_value = 0.42
    nt.links.new(vo.outputs["Distance"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(vo.outputs["Distance"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.66, 0.67, 0.68, 1)
    mix.inputs["B"].default_value = (0.50, 0.51, 0.52, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 700.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.05
    bp.inputs["Distance"].default_value = 0.0004
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_cable(name="Cable"):
    m = C.principled(name, (0.55, 0.55, 0.56), metallic=1.0, rough=0.3)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.bands_direction = "DIAGONAL"
    wv.inputs["Scale"].default_value = 400.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.7
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
RAIL_SEC = [(-0.036, 0.0), (0.036, 0.0), (0.036, -0.032), (0.023, -0.032), (0.023, -0.026), (0.028, -0.026),
            (0.028, -0.008), (-0.028, -0.008), (-0.028, -0.026), (-0.023, -0.026), (-0.023, -0.032), (-0.036, -0.032)]


def rail(x, zinc, steel, rubber):
    out = []
    fr = []
    for i in range(41):
        z = Z0 + (Z1 - Z0) * i / 40
        fr.append((Vector((x, yc(z), z)), Vector((1, 0, 0)), Vector((0, 1, 0)), RAIL_SEC))
    ob = loft("Rail", fr, zinc)
    C.add_bevel(ob, 0.0025, segments=1, angle=40)
    out.append(C.finalize(ob, angle=40))
    # end brackets with mounting holes, rubber grommets and pulleys
    for z, sz in ((Z0, -1), (Z1, 1)):
        y = yc(z) + 0.004
        sx = -1 if x < 0 else 1
        poly = rrect(0.17, 0.13, 0.03, 6)
        M = T((x + sx * 0.035, y, z + sz * 0.03)) @ Matrix.Rotation(math.radians(90), 4, "X")
        out.append(prism("EndBracket", poly, -0.005, 0.005, zinc, M=M, bevel=0.003, holes=[(0.022, sx * 0.045, sz * 0.02)]))
        g = T((x + sx * 0.08, y, z + sz * 0.05)) @ RY_
        out.append(lathe_at("Grommet", [(0.012, -0.02, 0), (0.03, -0.02, 0), (0.03, -0.006, 0), (0.024, -0.004, 0),
                                        (0.024, 0.006, 0), (0.03, 0.008, 0), (0.03, 0.018, 0), (0.012, 0.018, 0)],
                            [rubber], g, steps=40))
        out.append(lathe_at("GrommetStud", [(0.0, -0.035, 0), (0.012, -0.035, 0), (0.012, 0.02, 0), (0.0, 0.02, 0)],
                            [steel], g, steps=24))
    return out


def pulley(at, pom, steel):
    M = T(at) @ RY_
    P = [(0.0, -0.012, 0), (0.048, -0.012, 0), (0.05, -0.008, 0), (0.042, 0.0, 0), (0.05, 0.008, 0), (0.048, 0.012, 0),
         (0.0, 0.012, 0)]
    return [lathe_at("Pulley", P, [pom], M, steps=64, bevel=0.002),
            lathe_at("Axle", [(0.0, -0.022, 0), (0.016, -0.022, 0), (0.016, 0.012, 0), (0.0, 0.012, 0)], [steel], M, steps=24)]


def carrier(x, z, black, steel):
    out = []
    y = yc(z)
    sx = -1 if x < 0 else 1
    out.append(boxes("Slider", [(0.10, 0.05, 0.22, (x, y - 0.045, z)), (0.05, 0.035, 0.20, (x, y - 0.02, z))], black, bevel=0.01))
    # glass clamp: jaw block with slot opening upward and through bolt
    cz = z + 0.15
    bm = bmesh.new()
    C.box_bm(bm, 0.17, 0.07, 0.11, center=(x + sx * 0.02, y - 0.06, cz))
    C.box_bm(bm, 0.05, 0.05, 0.06, center=(x, y - 0.05, z + 0.09))
    jaw = C.mesh_obj("Clamp", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 0.24, 0.014, 0.09, center=(x + sx * 0.02, y - 0.06, cz + 0.05))
    cut = C.mesh_obj("ClampSlot", cb, [black])
    C.add_boolean(jaw, cut)
    C.add_bevel(jaw, 0.008, segments=2, angle=30)
    out.append(C.finalize(jaw, angle=35, remove=[cut]))
    out.append(hex_at("ClampBolt", 0.022, 0.0, 0.016, steel, T((x + sx * 0.02, y - 0.095, cz + 0.01)) @ RY_))
    out.append(lathe_at("ClampWasher", [(0.0, -0.004, 0), (0.03, -0.004, 0), (0.03, 0.0, 0), (0.0, 0.0, 0)], [steel],
                        T((x + sx * 0.02, y - 0.095, cz + 0.01)) @ RY_, steps=32))
    return out


def drum_motor(black, can_m, steel, pin_m):
    out = []
    M = T(D) @ RY_
    # cable drum housing (round, black) with three mounting lugs
    P = [(0.0, -0.045, 0), (0.12, -0.045, 0), (0.13, -0.035, 0), (0.13, 0.035, 0), (0.0, 0.035, 0)]
    out.append(lathe_at("DrumHousing", P, [black], M, steps=96, bevel=0.006))
    out.append(lathe_at("DrumCap", [(0.0, -0.065, 0), (0.07, -0.065, 0), (0.08, -0.045, 0), (0.0, -0.045, 0)],
                        [black], M, steps=64, bevel=0.004))
    for k in range(3):
        th = TAU * k / 3 + math.radians(90)
        Ml = M @ Matrix.Rotation(th, 4, "Z")
        out.append(prism("Lug", rrect(0.09, 0.06, 0.028, 6), 0.0, 0.03, black, M=Ml @ T((0.15, 0, 0)), bevel=0.006,
                         holes=[(0.012, 0.02, 0.0)]))
        out.append(hex_at("LugStud", 0.016, -0.02, 0.0, steel, Ml @ T((0.17, 0, 0))))
    # cable outlet ports
    for a in (math.radians(140), math.radians(-40)):
        p = D + Vector((0.13 * math.cos(a), -0.0, 0.13 * math.sin(a)))
        out.append(boxes("Port", [(0.05, 0.05, 0.05, tuple(p))], black, bevel=0.008))
    # worm housing below the drum, motor can toward +X, connector
    wz = D.z - 0.17
    Rx = Matrix.Rotation(math.radians(90), 4, "Y")    # local +Z -> world +X
    out.append(boxes("GearLink", [(0.10, 0.07, 0.10, (D.x + 0.0, D.y, D.z - 0.11))], black, bevel=0.01))
    out.append(lathe_at("WormHousing", [(0.0, -0.12, 0), (0.052, -0.12, 0), (0.058, -0.10, 0), (0.058, 0.10, 0), (0.0, 0.10, 0)],
                        [black], T((D.x, D.y, wz)) @ Rx, steps=64, bevel=0.005))
    can = [(0.0, 0.10, 0), (0.06, 0.10, 0), (0.06, 0.29, 0), (0.05, 0.305, 0), (0.022, 0.31, 0), (0.018, 0.33, 0), (0.0, 0.33, 0)]
    out.append(lathe_at("MotorCan", can, [can_m], T((D.x, D.y, wz)) @ Rx, steps=96, bevel=0.003))
    cx, cy, cz = D.x - 0.12, D.y - 0.03, wz - 0.07
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 0.08, 0.07, center=(cx, cy, cz))
    sh = C.mesh_obj("Conn", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 0.09, 0.08, 0.05, center=(cx, cy - 0.02, cz))
    cut = C.mesh_obj("ConnCut", cb, [black])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.004, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    out.append(boxes("ConnPins", [(0.008, 0.05, 0.008, (cx + (i - 1) * 0.024, cy - 0.01, cz)) for i in range(3)], pin_m, bevel=0.0))
    return out


def cables(cable_m, black, steel):
    out = []
    # cables along both rails
    for x in (-XR, XR):
        pts = [(x, yc(z) + YF, z) for z in (Z0 + 0.03, 0.5, 1.0, Z1 - 0.03)]
        out.append(tube("RailCable", pts, 0.0045, cable_m, res=2))
    # bare cable crossing: left bottom pulley -> right top pulley
    a = Vector((-XR + 0.05, yc(Z0) + YF, Z0 - 0.04))
    b = Vector((XR - 0.05, yc(Z1) + YF, Z1 + 0.04))
    out.append(tube("CrossCable", [tuple(a), tuple((a + b) / 2), tuple(b)], 0.0045, cable_m, res=2))
    # sheaths: drum -> left top, drum -> right bottom
    p1 = D + SC * Vector((0.13 * math.cos(math.radians(140)), -0.0, 0.13 * math.sin(math.radians(140))))
    s1 = [tuple(p1), (p1.x - 0.12, p1.y - 0.01, p1.z + 0.12), (-0.40, 0.04, 1.30), (-XR + 0.06, yc(Z1) + YF, Z1 + 0.10),
          (-XR + 0.03, yc(Z1) + YF, Z1 + 0.06)]
    p2 = D + SC * Vector((0.13 * math.cos(math.radians(-40)), -0.0, 0.13 * math.sin(math.radians(-40))))
    s2 = [tuple(p2), (p2.x + 0.12, p2.y - 0.01, p2.z - 0.12), (0.36, 0.03, 0.12), (XR - 0.06, yc(Z0) + YF, Z0 - 0.10),
          (XR - 0.03, yc(Z0) + YF, Z0 - 0.06)]
    for s in (s1, s2):
        out.append(tube("Sheath", s, 0.014, black, res=3))
        e = Vector(s[-1])
        d = (Vector(s[-1]) - Vector(s[-2])).normalized()
        out.append(lathe_at("Ferrule", [(0.0, -0.03, 0), (0.019, -0.03, 0), (0.019, 0.005, 0), (0.0, 0.005, 0)], [steel],
                            T(e) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4(), steps=24))
    return out


def build():
    zinc = mat_zinc()
    steel = C.principled("Steel", (0.62, 0.62, 0.63), metallic=1.0, rough=0.22)
    rubber = C.mat_rubber("Rubber")
    pom = C.principled("WhitePOM", (0.82, 0.81, 0.77), rough=0.42)
    C.add_noise_bump(pom, scale=800, strength=0.03, distance=0.0004)
    black = C.mat_black_plastic("PA6", rough=0.48, color=0.03)
    can_m = C.principled("CanZinc", (0.64, 0.64, 0.66), metallic=1.0, rough=0.25)
    C.add_noise_bump(can_m, scale=600, strength=0.03, distance=0.0005, rough_var=0.04)
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    cable_m = mat_cable()
    objs = []
    for x in (-XR, XR):
        objs += rail(x, zinc, steel, rubber)
        sx = 1 if x < 0 else -1
        for z in (Z0 - 0.045, Z1 + 0.045):
            objs += pulley(Vector((x + sx * 0.0, yc(z) + YF - 0.005, z)), pom, steel)
        objs += carrier(x, 1.02, black, steel)
    dm = drum_motor(black, can_m, steel, pin_m)
    C.transform_all(dm, T(D) @ Matrix.Diagonal((SC, SC, SC, 1.0)) @ T(-D))
    objs += dm
    objs += cables(cable_m, black, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("alzacristallo", objs, "alzacristallo.py",
            "car electric window regulator, dual-rail cable type: two zinc-plated guide rails with pulleys, "
            "glass clamp carriers, steel cables and sheaths, cable drum with electric motor and connector",
            az=24, el=16, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
