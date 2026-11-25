"""Crankshaft position sensor (inductive): slim black moulded body with a flat sensing tip
and O-ring, mounting ear with a pressed steel bushing, moulded head with a strain-relief
boot, a short black lead with a push-on cable clip, ending in a 3-pin connector with
latch ramp and pin cavities.

The sensor lies on its side on the floor, lead curving round to the connector.
1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RX = Matrix.Rotation(math.pi / 2, 4, "X")     # local Z -> -Y
RXn = Matrix.Rotation(-math.pi / 2, 4, "X")   # local Z -> +Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")     # local Z -> +X


# ----------------------------------------------------------------- helpers
def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circ(r, n=40, cx=0.0, cy=0.0, ph=0.0):
    return [(cx + r * math.cos(math.tau * k / n + ph), cy + r * math.sin(math.tau * k / n + ph)) for k in range(n)]


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
    P = list(poly) + [poly[0]]
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


def frame_to(P, Z):
    """Matrix placing local origin at P with local +Z along Z."""
    d = Vector(Z).normalized()
    return Matrix.Translation(Vector(P)) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def boolean(ob, cutter, op="DIFFERENCE"):
    m = C.add_boolean(ob, cutter, op)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), bev_angle=30):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        boolean(ob, c)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=bev_angle)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter(name, fill, mat=None):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat] if mat else [])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None, mod=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def smooth_path(ctrl, n=12):
    """Catmull-Rom through control points (open)."""
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def resample_path(path, step):
    P = [Vector(p) for p in path]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(L[-1] / step) + 1)
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(P) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append(P[j].lerp(P[j + 1], min(1.0, max(0.0, t))))
    return out, L[-1]


def path_frames(path, up=(0, 0, 1)):
    """Parallel-transport frames [(P, U, V, T)] along a polyline."""
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    upv = Vector(up)
    if abs(T[0].dot(upv)) > 0.95:
        upv = Vector((1, 0, 0))
    U = (upv - T[0] * upv.dot(T[0])).normalized()
    out = []
    for i, t in enumerate(T):
        U = (U - t * U.dot(t)).normalized()
        out.append((P[i], U, t.cross(U), t))
    return out


def hose_bm(bm, path, r_out, r_in=None, n=40, mat=0, mat_in=None, sx=1.0, sy=1.0, up=(0, 0, 1)):
    """Tube along path; r_out(s) / r_in(s) take arc fraction s in 0..1.
    With r_in the tube is hollow with annular end faces; otherwise capped."""
    fr = path_frames(path, up)
    m = len(fr)
    def ring(k, rf, inner=False):
        s = k / (m - 1)
        r = rf(s)
        P, U, V, _ = fr[k]
        return [bm.verts.new(P + U * (r * sx * math.cos(math.tau * j / n)) + V * (r * sy * math.sin(math.tau * j / n)))
                for j in range(n)]
    O = [ring(k, r_out) for k in range(m)]
    faces = []
    def skin(R, flip=False):
        for i in range(len(R) - 1):
            a, b = R[i], R[i + 1]
            for j in range(n):
                j2 = (j + 1) % n
                q = (a[j], a[j2], b[j2], b[j])
                f = bm.faces.new(q[::-1] if flip else q)
                faces.append(f)
    skin(O)
    if r_in is None:
        faces.append(bm.faces.new(O[0][::-1]))
        faces.append(bm.faces.new(O[-1]))
        for f in faces:
            f.material_index = mat
        return faces
    I = [ring(k, r_in) for k in range(m)]
    skin(I, flip=True)
    for f in faces:
        f.material_index = mat
    endf = []
    for A, B, fl in ((O[0], I[0], True), (O[-1], I[-1], False)):
        for j in range(n):
            j2 = (j + 1) % n
            q = (A[j], A[j2], B[j2], B[j])
            f = bm.faces.new(q[::-1] if fl else q)
            f.material_index = mat if mat_in is None else mat_in
            endf.append(f)
    return faces + endf


def tube(name, pts, r, mat, res=4, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


# ----------------------------------------------------------------- materials
def _b(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def nylon(name, color=0.05, rough=0.55, grain=260.0, dust=1.45):
    """Glass-filled nylon / PP: fine speckled texture, slightly satin, dust in creases."""
    m = C.principled(name, (color, color, color * 1.04), rough=rough)
    nt = m.node_tree
    b = _b(m)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = grain
    nz.inputs["Detail"].default_value = 3.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.08
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.06
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color * dust, color * dust * 0.97, color * dust * 0.9, 1)
    mix.inputs["B"].default_value = (color, color, color * 1.04, 1)
    nt.links.new(ao.outputs["AO"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = _b(m)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.15
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = grime
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.78, base * 0.72, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.093, 0.08, 1)
    em = C.edge_mask(nt, 0.012, 4.0)
    wm = nt.nodes.new("ShaderNodeMath"); wm.operation = "MULTIPLY"; wm.use_clamp = True
    wm.inputs[1].default_value = wear
    nt.links.new(em, wm.inputs[0])
    mix3 = nt.nodes.new("ShaderNodeMix"); mix3.data_type = "RGBA"
    nt.links.new(wm.outputs[0], mix3.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    mix3.inputs["B"].default_value = (0.72, 0.72, 0.71, 1)
    nt.links.new(mix3.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.25
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.30
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def zinc(name="Zinc", c=0.60, rough=0.28):
    m = C.principled(name, (c, c, c * 1.03), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=600, strength=0.03, distance=0.0005, rough_var=0.06)
    return m


def rubber(name="Rubber", c=0.026, rough=0.72, scale=400.0):
    m = C.principled(name, (c, c, c), rough=rough)
    C.add_noise_bump(m, scale=scale, strength=0.08, distance=0.001, rough_var=0.06)
    return m


def dark_cavity(name="Cavity"):
    return C.principled(name, (0.008, 0.008, 0.008), rough=0.85)


def shoot(name, objs, desc, **kw):
    if FAST:
        kw.update(res=(512, 512), samples=32)
    C.shoot(name, objs, name + ".py", desc, **kw)

AX_Z = 0.13                          # height of the sensor axis above the floor
DIR = Vector((-0.86, -0.51, 0.0)).normalized()   # tip direction (toward camera-left)


def body_parts(pa, oring, bush, dark):
    """Built along local +Z (tip at z=0, lead exits at +Z), placed later."""
    out = []
    P = [(0.0, 0.0, 0), (0.072, 0.0, 0), (0.082, 0.01, 0), (0.082, 0.10, 0), (0.088, 0.11, 0), (0.088, 0.30, 0),
         (0.10, 0.31, 0), (0.10, 0.33, 0), (0.0, 0.33, 0)]
    out.append(lathe_at("SensBody", P, pa, steps=96, bevel=0.003))
    # sensing face: slightly glossier insert
    out.append(lathe_at("TipFace", [(0.0, -0.004, 0), (0.06, -0.004, 0), (0.06, 0.002, 0), (0.0, 0.002, 0)],
                        C.principled("TipPA", (0.03, 0.03, 0.032), rough=0.3), steps=64))
    # O-ring in its groove
    P = []
    for k in range(24):
        a = math.tau * k / 24
        P.append((0.090 + 0.013 * math.cos(a), 0.20 + 0.013 * math.sin(a), 0))
    out.append(lathe_at("ORing", P, oring, steps=96, angle=60))
    # mounting flange with ear
    pts = circ(0.13, 48) + circ(0.085, 32, 0.24, 0.0)
    sec = resample(hull2d(pts), 140)
    def fl(bm):
        prism_bm(bm, sec, 0.33, 0.39)
    def hole(bm):
        C.cyl_bm(bm, 0.045, 0.2, 0.5, seg=32, matrix=Matrix.Translation((0.24, 0, 0)))
    hc = cutter("EarHole", hole, dark)
    out.append(solid("Flange", fl, [pa], bevel=0.012, seg=2, cutters=[hc]))
    out.append(lathe_at("Bushing", [(0.032, 0.325, 0), (0.046, 0.325, 0), (0.046, 0.385, 0), (0.058, 0.39, 0), (0.058, 0.40, 0),
                                    (0.032, 0.40, 0)], bush, Matrix.Translation((0.24, 0, 0)), steps=40, bevel=0.002))
    # moulded head + boot
    P = [(0.0, 0.39, 0), (0.115, 0.39, 0), (0.115, 0.47, 0), (0.10, 0.50, 0), (0.06, 0.52, 0), (0.05, 0.60, 0),
         (0.042, 0.64, 0), (0.0, 0.64, 0)]
    def ribs(r, z, t):
        if 0.53 < z < 0.63:
            return r + 0.006 * (0.5 + 0.5 * math.cos((z - 0.53) * math.tau / 0.025))
        return r
    out.append(lathe_at("Head", P, pa, steps=96, mod=ribs, bevel=0.004))
    # part-number pad: a flat land on the head (blank)
    def pad(bm):
        C.box_bm(bm, 0.02, 0.09, 0.06, center=(-0.112, 0, 0.43))
    out.append(solid("Pad", pad, [pa], bevel=0.004))
    return out


def connector(pa, dark, tin):
    """3-pin connector lying on the floor, mating face toward +X local."""
    out = []
    L, W, H = 0.40, 0.27, 0.20
    def housing(bm):
        C.box_bm(bm, L, W, H, center=(0, 0, H / 2))
        C.box_bm(bm, 0.12, 0.10, 0.035, center=(0.04, 0, H + 0.012))            # latch ramp
        C.box_bm(bm, 0.05, 0.14, 0.05, center=(0.13, 0, H + 0.02))              # latch tab
        for x in (-0.12, -0.06, 0.0):
            for sy in (-1, 1):
                C.box_bm(bm, 0.022, 0.02, H - 0.06, center=(x, sy * W / 2, H / 2))  # grip ribs
        C.cyl_bm(bm, 0.07, 0, 0.12, seg=32, matrix=Matrix.Translation((-L / 2, 0, H / 2)) @ Matrix.Rotation(-math.pi / 2, 4, "Y"))
    def cav(bm):
        C.box_bm(bm, 0.2, W - 0.05, H - 0.05, center=(L / 2, 0, H / 2))
    cc = cutter("ConnCav", cav, dark)
    out.append(solid("ConnHousing", housing, [pa], bevel=0.014, seg=2, cutters=[cc]))
    def pins(bm):
        for k in (-1, 0, 1):
            C.box_bm(bm, 0.08, 0.018, 0.018, center=(L / 2 - 0.08, k * 0.065, H / 2))
    out.append(solid("Pins", pins, [tin]))
    # seal inside cavity (grey-green silicone)
    def seal(bm):
        C.box_bm(bm, 0.02, W - 0.05, H - 0.05, center=(L / 2 - 0.10, 0, H / 2))
    out.append(solid("Seal", seal, [dark]))
    return out


def build():
    pa = nylon("SensorPA", color=0.022, rough=0.42, grain=420.0, dust=1.6)
    oring = rubber("ORingNBR", c=0.02, rough=0.55, scale=800.0)
    bush = zinc("Bushing", c=0.62, rough=0.25)
    dark = dark_cavity()
    tin = C.principled("Tin", (0.75, 0.74, 0.70), metallic=1.0, rough=0.2)
    cable = C.principled("CableJacket", (0.018, 0.018, 0.018), rough=0.38)
    C.add_noise_bump(cable, scale=200, strength=0.04, distance=0.0008)
    objs = []
    # sensor: local Z -> -DIR (tip toward DIR), ear pointing up-ish
    sp = body_parts(pa, oring, bush, dark)
    Mz = Matrix.Rotation(math.radians(-90), 4, "Z")
    S = frame_to(Vector((0.0, 0.0, AX_Z)), -DIR) @ Matrix.Rotation(math.radians(0), 4, "Z")
    # frame_to puts local +Z along -DIR; choose roll so the ear sticks up and slightly back
    roll = None
    best = -9
    for k in range(36):
        R = S @ Matrix.Rotation(math.tau * k / 36, 4, "Z")
        ear = (R.to_3x3() @ Vector((1, 0, 0)))
        sc = ear.z
        if sc > best:
            best, roll = sc, R
    for o in sp:
        o.matrix_world = roll @ o.matrix_world
    objs += sp
    # lead: from the head exit, along the axis, then curving to the connector on the floor
    exitp = roll @ Vector((0, 0, 0.62))
    ax = -DIR
    rc = 0.032
    pv = Vector((-ax.y, ax.x, 0.0))
    def q(a, b, z):
        v = exitp + ax * a + pv * b
        v.z = z
        return v
    ctrl = [exitp, exitp + ax * 0.20, q(0.45, 0.10, rc + 0.03), q(0.62, 0.42, rc), q(0.45, 0.78, rc),
            q(0.05, 0.92, rc), q(-0.30, 0.88, 0.10)]
    path = smooth_path(ctrl, 14)
    objs.append(tube("Lead", [tuple(p) for p in path], rc, cable, res=4))
    # push-on cable clip midway
    k = len(path) // 2
    T = (path[k + 1] - path[k - 1]).normalized()
    M = frame_to(path[k], T)
    def clip(bm):
        C.cyl_bm(bm, 0.055, -0.05, 0.05, seg=24, matrix=M)
        C.cyl_bm(bm, 0.025, -0.13, 0.0, seg=16, matrix=M @ Matrix.Translation((0, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    clipm = nylon("ClipPA", color=0.03, rough=0.5)
    objs.append(solid("CableClip", clip, [clipm], bevel=0.008))
    # connector at the end, cable entering its rear boot
    end = path[-1]
    Td = (path[-1] - path[-3]).normalized()
    Td.z = 0
    Td.normalize()
    ang = math.atan2(Td.y, Td.x)
    con = connector(pa, dark, tin)
    Mc = Matrix.Translation((end.x + Td.x * 0.31, end.y + Td.y * 0.31, 0.0)) @ Matrix.Rotation(ang, 4, "Z")
    for o in con:
        o.matrix_world = Mc @ o.matrix_world
    objs += con
    # lift whole group so the lowest point sits on the floor (lead radius)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("sensore-giri", objs, "sensore-giri.py",
            "crankshaft position sensor: black plastic sensor body with O-ring and mounting ear, short lead with 3-pin connector",
            az=30, el=34, lens=70, fill=0.86, **kw)
