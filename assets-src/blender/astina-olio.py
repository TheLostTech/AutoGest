"""Oil dipstick with guide tube: long zinc-plated steel tube with a gentle bend, black
plastic mouth collar, stamped mounting bracket with bolt hole and a bead plus O-ring at
the block end; next to it the pulled-out dipstick: thin flat spring-steel blade with
MIN/MAX notches and an etched cross-hatched zone near the tip, rubber-sealed stopper
and bright yellow-orange loop handle.

Both lie on the floor along X, then are turned diagonally to the camera.
1 unit = 100 mm (about 620 mm long)."""
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

RT = 0.065      # tube outer radius (13 mm)
TL = 5.6        # tube straight length


def tube_path():
    ctrl = [(-2.9, 0.0, RT), (-1.0, 0.0, RT), (1.4, 0.0, RT), (2.15, 0.06, RT), (2.55, 0.26, RT), (2.85, 0.55, RT)]
    path = smooth_path(ctrl, 20)
    path, L = resample_path(path, 0.02)
    return path


def guide_tube(steel, rub, pa, dark, brk):
    out = []
    path = tube_path()
    bm = bmesh.new()
    def rout(s):
        return RT + 0.012 * math.exp(-((s - 0.035) / 0.006) ** 2)
    hose_bm(bm, path, rout, lambda s: RT - 0.012, n=32, mat=0)
    ob = C.mesh_obj("GuideTube", bm, [steel])
    out.append(C.finalize(ob, angle=60))
    fr = path_frames(path)
    # O-ring near the block end
    P0, U0, V0, T0 = fr[int(len(fr) * 0.06)]
    M0 = Matrix(((U0.x, V0.x, T0.x, P0.x), (U0.y, V0.y, T0.y, P0.y), (U0.z, V0.z, T0.z, P0.z), (0, 0, 0, 1)))
    pr = [(RT + 0.012 * math.cos(math.tau * k / 16), 0.012 * math.sin(math.tau * k / 16), 0) for k in range(16)]
    out.append(lathe_at("TubeORing", pr, rub, M0, steps=48, angle=60))
    # black plastic mouth collar at the top end
    P1, U1, V1, T1 = fr[-1]
    M1 = Matrix(((U1.x, V1.x, T1.x, P1.x), (U1.y, V1.y, T1.y, P1.y), (U1.z, V1.z, T1.z, P1.z), (0, 0, 0, 1)))
    P = [(RT - 0.012, -0.22, 0), (RT + 0.022, -0.22, 0), (RT + 0.03, -0.20, 0), (RT + 0.03, 0.0, 0), (RT + 0.05, 0.05, 0),
         (RT + 0.05, 0.10, 0), (RT + 0.02, 0.10, 0), (RT - 0.012, 0.04, 0)]
    out.append(lathe_at("MouthCollar", P, pa, M1, steps=48, bevel=0.003))
    # stamped bracket welded to the tube at ~80 % length
    P2, U2, V2, T2 = fr[int(len(fr) * 0.70)]
    side = Vector((-T2.y, T2.x, 0)).normalized()
    ang = math.atan2(side.y, side.x)
    Mb = Matrix.Translation(P2 + Vector((0, 0, -RT + 0.015))) @ Matrix.Rotation(ang, 4, "Z")
    def br(bm):
        sec = resample(hull2d(circ(0.12, 32, 0.34, 0.0) + [(0.0, -0.16), (0.0, 0.16)]), 80)
        prism_bm(bm, sec, -0.0125, 0.0125, Mb)
        C.box_bm(bm, 0.12, 0.30, 0.10, center=(0.02, 0.0, 0.04), matrix=Mb)
    def hole(bm):
        C.cyl_bm(bm, 0.055, -0.2, 0.2, seg=28, matrix=Mb @ Matrix.Translation((0.34, 0, 0)))
    hc = cutter("BrHole", hole, dark)
    out.append(solid("Bracket", br, [brk], bevel=0.006, cutters=[hc]))
    return out


def dipstick(blade_m, etch_m, rub, handle_m, pa):
    out = []
    y = -0.55
    x0, x1 = -3.05, 2.35       # blade tip .. stopper
    w, t = 0.055, 0.010
    def blade(bm):
        C.box_bm(bm, x1 - x0, w, t, center=((x0 + x1) / 2, y, t / 2))
    def notches(bm):
        for x in (x0 + 0.30, x0 + 0.62):
            for sy in (-1, 1):
                C.cyl_bm(bm, 0.014, -0.1, 0.1, seg=12, matrix=Matrix.Translation((x, y + sy * w / 2, 0)))
    nc = cutter("Notches", notches, blade_m)
    ob = solid("Blade", blade, [blade_m], bevel=0.003, seg=1, cutters=[nc])
    out.append(ob)
    # rounded tip
    out.append(lathe_at("Tip", [(0.0, -0.0, 0), (w / 2, 0.0, 0), (w / 2, t, 0), (0.0, t, 0)], blade_m,
                        Matrix.Translation((x0, y, 0)), steps=24))
    # etched cross-hatch between the notches
    def hatch(bm):
        for k in range(14):
            x = x0 + 0.32 + k * 0.021
            for sgn in (-1, 1):
                M = Matrix.Translation((x, y, t + 0.0004)) @ Matrix.Rotation(sgn * math.radians(50), 4, "Z")
                C.box_bm(bm, 0.003, w * 1.25, 0.001, matrix=M)
    hb = bmesh.new()
    hatch(hb)
    # clip to blade width
    for v in hb.verts:
        v.co.y = max(y - w / 2 + 0.003, min(y + w / 2 - 0.003, v.co.y))
    out.append(C.mesh_obj("Hatch", hb, [etch_m]))
    # stopper with rubber seal, then stem and loop handle
    out.append(lathe_at("Ferrule", [(0.0, x1 - 0.05, 0), (0.035, x1 - 0.05, 0), (0.035, x1 + 0.10, 0), (0.0, x1 + 0.10, 0)],
                        blade_m, Matrix.Translation((0, y, 0.04)) @ Matrix.Rotation(math.pi / 2, 4, "Y"), steps=24))
    My = Matrix.Translation((0, y, 0.075)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    P = [(0.0, x1 + 0.08, 0), (0.05, x1 + 0.08, 0), (0.055, x1 + 0.14, 0), (0.07, x1 + 0.15, 0), (0.07, x1 + 0.22, 0),
         (0.0, x1 + 0.22, 0)]
    out.append(lathe_at("Seal", P, rub, My, steps=40, bevel=0.003))
    P = [(0.0, x1 + 0.22, 0), (0.075, x1 + 0.22, 0), (0.075, x1 + 0.30, 0), (0.06, x1 + 0.34, 0), (0.06, x1 + 0.42, 0), (0.0, x1 + 0.42, 0)]
    out.append(lathe_at("Stem", P, handle_m, My, steps=40, bevel=0.004))
    # loop handle (flat ring lying on the floor)
    cx = x1 + 0.42 + 0.20
    pts = []
    for k in range(73):
        a = math.tau * k / 72
        pts.append((cx + 0.22 * math.cos(a), y + 0.17 * math.sin(a), 0.06))
    out.append(tube("Loop", pts, 0.055, handle_m, res=4))
    def web(bm):
        C.box_bm(bm, 0.14, 0.10, 0.08, center=(x1 + 0.44, y, 0.06))
    out.append(solid("HandleWeb", web, [handle_m], bevel=0.02))
    return out


def build():
    steel = zinc("TubeZinc", c=0.50, rough=0.32)
    rub = rubber("Seal", c=0.02, rough=0.6)
    pa = nylon("CollarPA", color=0.03, rough=0.45)
    dark = dark_cavity()
    brk = zinc("BracketZinc", c=0.46, rough=0.36)
    blade_m = C.principled("SpringSteel", (0.70, 0.70, 0.71), metallic=1.0, rough=0.18)
    C.add_noise_bump(blade_m, scale=300, strength=0.03, distance=0.0004, rough_var=0.06)
    etch_m = C.principled("Etch", (0.22, 0.22, 0.23), metallic=1.0, rough=0.5)
    handle_m = C.principled("HandlePA", (0.95, 0.52, 0.03), rough=0.38)
    C.add_noise_bump(handle_m, scale=500, strength=0.04, distance=0.0005)
    objs = guide_tube(steel, rub, pa, dark, brk) + dipstick(blade_m, etch_m, rub, handle_m, pa)
    C.transform_all(objs, Matrix.Rotation(math.radians(-28), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("astina-olio", objs, "astina-olio.py",
            "engine oil dipstick with guide tube: steel blade with MIN/MAX marks and yellow-orange handle, bent steel tube with bracket",
            az=30, el=34, lens=70, fill=0.90, **kw)
