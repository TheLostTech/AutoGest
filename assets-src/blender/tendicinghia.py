"""Auxiliary belt tensioner: cast-aluminium mounting base with two bolt ears and a
locating dowel, round spring drum with the pivot bolt, cast swing arm with a square
drive hole for the release tool and a wear-indicator pointer over the base scale, and
a smooth black composite idler pulley (polished running surface, ribbed web, steel
bearing race, centre bolt with washer).

Built with the base in the XY plane and the drum along +Z, then turned so the pulley
face looks at the camera. 1 unit = 100 mm."""
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

PX, PY = 0.30, 0.82      # pulley centre on the arm
RP = 0.36                # pulley radius (72 mm)


def base(alu, dark, face_m):
    out = []
    ears = [(0.62, -0.30, 0.135), (-0.52, -0.40, 0.125), (-0.30, 0.42, 0.11)]
    pts = circ(0.46, 72)
    for x, y, r in ears:
        pts += circ(r, 28, x, y)
    sec = resample(hull2d(pts), 180)
    def fl(bm):
        prism_bm(bm, sec, 0.0, 0.09)
    def holes(bm):
        for x, y, r in ears[:2]:
            C.cyl_bm(bm, 0.052, -0.1, 0.3, seg=28, matrix=Matrix.Translation((x, y, 0)))
        # lightening pocket on the third ear
        C.cyl_bm(bm, 0.05, 0.05, 0.3, seg=24, matrix=Matrix.Translation((ears[2][0], ears[2][1], 0)))
    hc = cutter("BaseHoles", holes, dark)
    out.append(solid("Base", fl, [alu], bevel=0.02, seg=3, cutters=[hc]))
    # bosses around the bolt holes (machined tops)
    for x, y, r in ears[:2]:
        out.append(lathe_at("EarBoss", [(0.052, 0.05, 0), (0.105, 0.05, 0), (0.105, 0.13, 1), (0.052, 0.13, 1)],
                            alu, Matrix.Translation((x, y, 0)), mats=[alu, face_m], steps=40, bevel=0.006))
    # locating dowel on the back
    out.append(lathe_at("Dowel", [(0.0, -0.12, 0), (0.035, -0.12, 0), (0.045, -0.10, 0), (0.045, 0.0, 0), (0.0, 0.0, 0)],
                        face_m, Matrix.Translation((-0.05, -0.30, 0)), steps=24))
    # wear-indicator scale: raised lug with two notches
    def lug(bm):
        M = Matrix.Rotation(math.radians(-25), 4, "Z")
        C.box_bm(bm, 0.20, 0.06, 0.05, center=(0, 0.44, 0.115), matrix=M)
    def notches(bm):
        M = Matrix.Rotation(math.radians(-25), 4, "Z")
        for x in (-0.06, 0.06):
            C.box_bm(bm, 0.016, 0.10, 0.04, center=(x, 0.44, 0.15), matrix=M)
    nc = cutter("Notches", notches, dark)
    out.append(solid("ScaleLug", lug, [alu], bevel=0.008, cutters=[nc]))
    return out


def drum(alu, steel, dark):
    out = []
    def rib(r, z, t):
        if not (0.12 < z < 0.36) or r < 0.40:
            return r
        v = math.cos(18 * t)
        return r + 0.018 * max(0.0, v) ** 4
    P = [(0.0, 0.08, 0), (0.43, 0.08, 0), (0.43, 0.10, 0), (0.405, 0.13, 0), (0.405, 0.35, 0), (0.39, 0.38, 0),
         (0.13, 0.38, 0), (0.0, 0.38, 0)]
    out.append(lathe_at("Drum", P, alu, steps=192, mod=rib, bevel=0.008))
    return out


def arm(alu, dark):
    out = []
    pts = circ(0.34, 64) + circ(0.20, 48, PX, PY)
    sec = resample(hull2d(pts), 160)
    def a(bm):
        prism_bm(bm, sec, 0.38, 0.50)
        # pointer tab reaching over the scale lug
        M = Matrix.Rotation(math.radians(-25), 4, "Z")
        C.box_bm(bm, 0.045, 0.16, 0.05, center=(0.0, 0.40, 0.205), matrix=M)
        C.box_bm(bm, 0.045, 0.05, 0.12, center=(0.0, 0.46, 0.27), matrix=M)
    def cuts(bm):
        # square release-tool drive and pocket in the arm web
        C.box_bm(bm, 0.095, 0.095, 0.2, center=(0.16, 0.40, 0.52), matrix=Matrix.Rotation(math.radians(20), 4, "Z"))
        C.cyl_bm(bm, 0.19, 0.48, 0.60, seg=64)
    hc = cutter("ArmCuts", cuts, dark)
    out.append(solid("Arm", a, [alu], bevel=0.018, seg=3, cutters=[hc]))
    # raised rib along the arm
    return out


def pivot(steel, dark):
    out = []
    out.append(lathe_at("PivotWasher", [(0.0, 0.48, 0), (0.17, 0.48, 0), (0.17, 0.505, 0), (0.0, 0.505, 0)], steel, steps=64, bevel=0.003))
    out.append(hex_at("PivotBolt", 0.095, 0.505, 0.585, steel, bevel=0.008))
    out.append(lathe_at("BoltFlange", [(0.0, 0.50, 0), (0.115, 0.50, 0), (0.115, 0.515, 0), (0.0, 0.515, 0)], steel, steps=48))
    return out


def pulley(comp, run_m, steel, dark):
    out = []
    M = Matrix.Translation((PX, PY, 0))
    z0, z1 = 0.52, 0.80
    # outer running band with slight crown and side flanges of the moulding
    P = [(RP - 0.04, z0, 0), (RP - 0.005, z0, 0), (RP, z0 + 0.01, 1), (RP + 0.004, (z0 + z1) / 2, 1), (RP, z1 - 0.01, 1),
         (RP - 0.005, z1, 0), (RP - 0.04, z1, 0)]
    out.append(lathe_at("PulleyRim", P, comp, M, mats=[comp, run_m], steps=192, bevel=0.003))
    # recessed web on the front with 8 radial ribs
    P = [(0.13, z0 + 0.06, 0), (RP - 0.035, z0 + 0.06, 0), (RP - 0.035, z1 - 0.05, 0), (RP - 0.065, z1 - 0.05, 0),
         (RP - 0.065, z0 + 0.12, 0), (0.15, z0 + 0.12, 0), (0.15, z1 - 0.02, 0), (0.13, z1 - 0.02, 0)]
    out.append(lathe_at("PulleyWeb", P, comp, M, steps=160))
    def ribs(bm):
        for k in range(8):
            th = math.tau * k / 8
            R = M @ Matrix.Rotation(th, 4, "Z")
            C.box_bm(bm, RP - 0.21, 0.03, z1 - z0 - 0.12, center=((RP + 0.11) / 2 - 0.0, 0, z0 + 0.06 + (z1 - z0 - 0.12) / 2), matrix=R)
    out.append(solid("WebRibs", ribs, [comp], bevel=0.005))
    # steel bearing: inner race + seal
    out.append(lathe_at("BearingOuter", [(0.115, z0 + 0.05, 0), (0.13, z0 + 0.05, 0), (0.13, z1 - 0.015, 0), (0.115, z1 - 0.015, 0)], steel, M, steps=96))
    out.append(lathe_at("BearingSeal", [(0.07, z1 - 0.03, 0), (0.118, z1 - 0.03, 0), (0.118, z1 - 0.022, 0), (0.07, z1 - 0.022, 0)],
                        C.principled("SealRubber", (0.03, 0.03, 0.03), rough=0.7), M, steps=96))
    out.append(lathe_at("InnerRace", [(0.05, z0 + 0.03, 0), (0.075, z0 + 0.03, 0), (0.075, z1 - 0.005, 0), (0.05, z1 - 0.005, 0)], steel, M, steps=64))
    # centre bolt + washer
    out.append(lathe_at("PWasher", [(0.0, z1 - 0.005, 0), (0.095, z1 - 0.005, 0), (0.095, z1 + 0.012, 0), (0.0, z1 + 0.012, 0)], steel, M, steps=48, bevel=0.002))
    out.append(hex_at("PBolt", 0.072, z1 + 0.012, z1 + 0.075, steel, M, bevel=0.007))
    out.append(lathe_at("BoltEnd", [(0.0, z1 + 0.075, 0), (0.03, z1 + 0.075, 0), (0.03, z1 + 0.078, 0), (0.0, z1 + 0.078, 0)], dark, M, steps=24))
    return out


def build():
    alu = cast_alu("TensAlu", base=0.40, rough=0.52, grime=0.65, grain=170.0, wear=0.3)
    face_m = C.principled("MachinedFace", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    C.add_radial_aniso(face_m, 0.5, "Z", rings_scale=50.0, ring_strength=0.03)
    steel = zinc("BoltZinc", c=0.58, rough=0.3)
    dark = dark_cavity()
    comp = nylon("PulleyPA", color=0.03, rough=0.5, grain=300.0)
    run_m = C.principled("RunSurface", (0.035, 0.035, 0.037), rough=0.22)
    C.add_noise_bump(run_m, scale=60, strength=0.05, distance=0.001)
    objs = base(alu, dark, face_m) + drum(alu, steel, dark) + arm(alu, dark) + pivot(steel, dark) + pulley(comp, run_m, steel, dark)
    R = (Matrix.Rotation(math.radians(-6), 4, "Z") @ Matrix.Rotation(math.radians(60), 4, "X")
         @ Matrix.Rotation(math.radians(-38), 4, "Z"))
    C.transform_all(objs, R)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("tendicinghia", objs, "tendicinghia.py",
            "auxiliary belt tensioner: cast aluminium base with bolt ears, spring drum, swing arm and smooth black idler pulley with centre bolt",
            az=35, el=20, lens=70, fill=0.82, **kw)
