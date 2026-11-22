"""Turbo / intercooler boost hose: black fabric-reinforced rubber hose with a moulded
bellows section, a horizontal bend and an upward elbow; one end a plain cuff with a
worm-drive hose clamp (perforated band, screw housing, hex screw), the other end
crimped with a steel ferrule onto a black quick-fit connector held by a wire spring
clip, O-ring visible in its mouth.

Hose lies on the floor; 1 unit = 100 mm (60 mm OD hose)."""
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

RO, WALL = 0.30, 0.055


def hose_rubber(name="HoseEPDM"):
    """Black EPDM with the faint diagonal wrap imprint of the fabric reinforcement."""
    m = C.principled(name, (0.024, 0.024, 0.025), rough=0.62)
    nt = m.node_tree
    b = _b(m)
    co = C._coord(nt)
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "DIAGONAL"
    wv.inputs["Scale"].default_value = 55.0
    wv.inputs["Distortion"].default_value = 1.2
    wv.inputs["Detail"].default_value = 2.0
    nt.links.new(co, wv.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 500.0
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    mw = nt.nodes.new("ShaderNodeMath"); mw.operation = "MULTIPLY"; mw.inputs[1].default_value = 0.35
    nt.links.new(wv.outputs["Fac"], mw.inputs[0])
    nt.links.new(mw.outputs[0], add.inputs[0])
    nt.links.new(nz.outputs["Fac"], add.inputs[1])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.12
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(add.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 0.70
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # faint grey bloom (dried dust / release agent) in the bellows valleys
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.05
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(ao.outputs["AO"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.05, 0.048, 0.045, 1)
    mix.inputs["B"].default_value = (0.024, 0.024, 0.025, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def hose_path():
    ctrl = [(-1.75, -0.45, RO), (-1.0, -0.45, RO), (-0.2, -0.45, RO), (0.45, -0.30, RO), (0.85, 0.15, RO),
            (1.00, 0.70, RO + 0.02), (1.02, 1.05, RO + 0.22), (1.00, 1.22, RO + 0.62), (0.98, 1.28, RO + 1.00)]
    path = smooth_path(ctrl, 16)
    path, L = resample_path(path, 0.012)
    return path, L


BEL0, BEL1, NBEL = 0.24, 0.40, 6     # bellows span (arc fraction) and convolutions


def r_out(s):
    r = RO
    if BEL0 < s < BEL1:
        u = (s - BEL0) / (BEL1 - BEL0)
        r += 0.045 * (0.5 - 0.5 * math.cos(math.tau * NBEL * u)) * C.smoothstep(0.0, 0.04, u) * C.smoothstep(0.0, 0.04, 1 - u)
    # moulded cuff at the clamp end
    r += 0.012 * C.smoothstep(0.10, 0.07, s)
    return r


def hose(rub, path):
    bm = bmesh.new()
    hose_bm(bm, path, r_out, lambda s: r_out(s) - WALL, n=64, mat=0)
    ob = C.mesh_obj("Hose", bm, [rub])
    C.add_bevel(ob, 0.006, segments=2, angle=50)
    return C.finalize(ob, angle=60)


def worm_clamp(steel, path, L):
    out = []
    fr = path_frames(path)
    k = int(len(path) * 0.045)
    P, U, V, T = fr[k]
    M = Matrix(((U.x, V.x, T.x, P.x), (U.y, V.y, T.y, P.y), (U.z, V.z, T.z, P.z), (0, 0, 0, 1)))
    rb = RO + 0.012 + 0.010
    # band
    out.append(lathe_at("ClampBand", [(rb - 0.012, -0.06, 0), (rb, -0.06, 0), (rb, 0.06, 0), (rb - 0.012, 0.06, 0)],
                        steel, M, steps=128, bevel=0.002))
    # perforations: shallow slots on the band
    def slots(bm):
        for j in range(26):
            a = math.radians(30 + 300 * j / 25)
            R = M @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((rb, 0, 0))
            C.box_bm(bm, 0.008, 0.02, 0.055, matrix=R)
    dk = C.principled("SlotDark", (0.05, 0.05, 0.05), metallic=0.8, rough=0.5)
    out.append(solid("Slots", slots, [dk]))
    # screw housing on +Y local (which maps to U: up-ish)
    def housing(bm):
        C.box_bm(bm, 0.20, 0.07, 0.15, center=(0, rb + 0.03, 0), matrix=M)
    out.append(solid("ClampHousing", housing, [steel], bevel=0.01))
    Ms = M @ Matrix.Translation((0.0, rb + 0.035, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    out.append(lathe_at("ClampScrew", [(0.0, -0.20, 0), (0.035, -0.20, 0), (0.035, 0.10, 0), (0.0, 0.10, 0)], steel, Ms, steps=24))
    out.append(hex_at("ClampHex", 0.045, -0.23, -0.12, steel, Ms, bevel=0.005))
    out.append(lathe_at("ClampHexWasher", [(0.0, -0.13, 0), (0.06, -0.13, 0), (0.06, -0.115, 0), (0.0, -0.115, 0)], steel, Ms, steps=32))
    return out


def connector(pa, steel, wire, oring, path):
    out = []
    fr = path_frames(path)
    P, U, V, T = fr[-1]
    M = Matrix(((U.x, V.x, T.x, P.x), (U.y, V.y, T.y, P.y), (U.z, V.z, T.z, P.z), (0, 0, 0, 1)))
    # crimped steel ferrule over the hose end
    def crimp(r, z, t):
        return r - 0.008 * (0.5 + 0.5 * math.cos(z * math.tau / 0.04)) if -0.15 < z < -0.03 else r
    out.append(lathe_at("Ferrule", [(RO - 0.01, -0.18, 0), (RO + 0.028, -0.18, 0), (RO + 0.028, 0.0, 0), (RO - 0.01, 0.0, 0)],
                        steel, M, steps=128, mod=crimp, bevel=0.003))
    # connector body: spigot inside the hose, then socket with clip windows
    P2 = [(RO - WALL - 0.005, -0.18, 0), (RO + 0.02, -0.0, 0), (RO + 0.07, 0.01, 0), (RO + 0.07, 0.30, 0),
          (RO + 0.05, 0.33, 0), (RO - 0.01, 0.33, 0), (RO - 0.01, 0.26, 0), (RO - 0.04, 0.25, 0), (RO - 0.05, -0.18, 0)]
    def ribs(r, z, t):
        # axial ribs on the socket
        if 0.03 < z < 0.29 and r > RO + 0.05:
            return r + 0.018 * max(0.0, math.cos(8 * t)) ** 6
        return r
    out.append(lathe_at("ConnBody", P2, pa, M, steps=160, mod=ribs, bevel=0.004))
    out.append(lathe_at("ConnBore", [(0.0, 0.10, 0), (RO - 0.045, 0.10, 0), (RO - 0.045, 0.102, 0), (0.0, 0.102, 0)],
                        dark_cavity("BoreDark"), M, steps=64))
    # O-ring seen in the mouth
    pr = [(RO - 0.035 + 0.016 * math.cos(math.tau * k / 20), 0.22 + 0.016 * math.sin(math.tau * k / 20), 0) for k in range(20)]
    out.append(lathe_at("ConnORing", pr, oring, M, steps=96, angle=60))
    # wire spring clip: loop round the socket, two legs through the windows
    pts = []
    rr = RO + 0.095
    for j in range(0, 41):
        a = math.radians(-150 + 300 * j / 40)
        pts.append(tuple(M @ Vector((rr * math.cos(a), rr * math.sin(a), 0.18))))
    a0, a1 = math.radians(-150), math.radians(150)
    leg0 = [tuple(M @ Vector(((rr - 0.02 * k) * math.cos(a0), (rr - 0.02 * k) * math.sin(a0), 0.18))) for k in range(1, 5)]
    leg1 = [tuple(M @ Vector(((rr - 0.02 * k) * math.cos(a1), (rr - 0.02 * k) * math.sin(a1), 0.18))) for k in range(1, 5)]
    out.append(tube("WireClip", leg0[::-1] + pts + leg1, 0.014, wire, res=3))
    return out


def build():
    rub = hose_rubber()
    steel = zinc("ClampSteel", c=0.62, rough=0.24)
    pa = nylon("ConnPA", color=0.03, rough=0.42, grain=380.0)
    wire = C.principled("SpringWire", (0.55, 0.55, 0.57), metallic=1.0, rough=0.2)
    oring = rubber("ORing", c=0.02, rough=0.5)
    path, L = hose_path()
    objs = [hose(rub, path)] + worm_clamp(steel, path, L) + connector(pa, steel, wire, oring, path)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("manicotto-turbo", objs, "manicotto-turbo.py",
            "turbo intercooler boost hose: black reinforced rubber hose with bellows section and bends, worm-drive clamp and quick-fit connector",
            az=32, el=26, lens=70, fill=0.84, **kw)
