"""Air filter box: black polypropylene lower housing and lid with matching flanges, the
orange polyurethane frame of the panel filter element showing in the joint, four
zinc spring clips holding the lid, flat inlet snorkel with flared mouth on the front,
round outlet spigot with hose beads on the end, ribbed lid top with a blank service
label.

1 unit = 100 mm (about 320 x 220 x 160 mm housing)."""
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

ZF = 0.86     # lower flange bottom
CLIPS = [(-0.95, -1), (0.95, -1), (-0.95, 1), (0.95, 1)]


def stack(bm, specs, n=8):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), [(x + cx, y) for x, y in rrect(w, h, r, n)])
          for z, w, h, r, cx in specs]
    C.sweep(bm, fr)


def lower(pp, dark):
    out = []
    def body(bm):
        stack(bm, [(0.0, 2.95, 1.95, 0.32, 0), (0.10, 3.05, 2.05, 0.36, 0), (ZF, 3.20, 2.20, 0.40, 0)])
        stack(bm, [(ZF - 0.01, 3.36, 2.36, 0.46, 0), (ZF + 0.10, 3.36, 2.36, 0.46, 0)])
        # clip hinge lugs
        for x, s in CLIPS:
            C.box_bm(bm, 0.26, 0.10, 0.20, center=(x, s * 1.11, ZF - 0.16))
        # vertical stiffening ribs on the walls
        for x in (-1.25, -0.40, 0.40, 1.25):
            for s in (-1, 1):
                C.box_bm(bm, 0.06, 0.08, ZF - 0.12, center=(x, s * 1.02, (ZF - 0.12) / 2 + 0.06))
    out.append(solid("LowerHousing", body, [pp], bevel=0.02, seg=2, angle=40))
    return out


def filter_edge(pu):
    def f(bm):
        stack(bm, [(ZF + 0.10, 3.28, 2.28, 0.43, 0), (ZF + 0.165, 3.28, 2.28, 0.43, 0)])
    return solid("FilterFrame", f, [pu], bevel=0.012, seg=2)


def lid(pp, dark):
    out = []
    z0 = ZF + 0.165
    def body(bm):
        stack(bm, [(z0, 3.36, 2.36, 0.46, 0), (z0 + 0.10, 3.36, 2.36, 0.46, 0)])
        stack(bm, [(z0 + 0.09, 3.20, 2.20, 0.40, 0), (z0 + 0.38, 3.10, 2.10, 0.40, 0), (z0 + 0.52, 2.86, 1.86, 0.34, 0.03),
                   (z0 + 0.57, 2.50, 1.50, 0.28, 0.05)])
        # top ribs
        for x in (-0.85, -0.25, 0.35):
            C.box_bm(bm, 0.06, 1.30, 0.07, center=(x, 0, z0 + 0.59))
        C.box_bm(bm, 1.9, 0.06, 0.07, center=(-0.25, 0.25, z0 + 0.59))
        # clip catch lugs on the lid flange
        for x, s in CLIPS:
            C.box_bm(bm, 0.26, 0.08, 0.14, center=(x, s * 1.13, z0 + 0.17))
    out.append(solid("Lid", body, [pp], bevel=0.02, seg=2, angle=40))
    return out, z0


def clips(steel, z0):
    out = []
    for x, s in CLIPS:
        def f(bm, x=x, s=s):
            y = s * 1.205
            C.box_bm(bm, 0.15, 0.022, 0.44, center=(x, y, ZF + 0.02))          # strap over the joint
            C.box_bm(bm, 0.15, 0.10, 0.022, center=(x, y - s * 0.05, z0 + 0.24))  # hook over the lid lug
            C.box_bm(bm, 0.20, 0.05, 0.05, center=(x, y - s * 0.01, ZF - 0.20))   # hinge roll
        out.append(solid("Clip", f, [steel], bevel=0.008, seg=2))
        Mh = Matrix.Translation((x, s * 1.20, ZF - 0.20)) @ RY
        out.append(lathe_at("HingePin", [(0.0, -0.13, 0), (0.035, -0.13, 0), (0.035, 0.13, 0), (0.0, 0.13, 0)], steel, Mh, steps=20))
    return out


def snorkel(pp, dark):
    """Flat inlet duct leaving the front wall and turning toward -X, flared mouth."""
    out = []
    ctrl = [(-0.70, -0.75, 0.48), (-0.72, -1.25, 0.48), (-0.85, -1.62, 0.50), (-1.25, -1.85, 0.52), (-1.85, -1.92, 0.54)]
    path, L = resample_path(smooth_path(ctrl, 16), 0.02)
    def ro(s):
        return 0.33 + 0.07 * C.smoothstep(0.86, 1.0, s)
    def ri(s):
        return ro(s) - 0.035
    bm = bmesh.new()
    hose_bm(bm, path, ro, ri, n=64, sx=0.62, sy=1.25)
    ob = C.mesh_obj("Snorkel", bm, [pp])
    C.add_bevel(ob, 0.006, segments=1, angle=50)
    out.append(C.finalize(ob, angle=50))
    # bead at the mouth and dark throat
    fr = path_frames(path)
    P, U, V, T = fr[int(len(fr) * 0.80)]
    Md = Matrix(((U.x * 0.62, V.x * 1.25, T.x, P.x), (U.y * 0.62, V.y * 1.25, T.y, P.y), (U.z * 0.62, V.z * 1.25, T.z, P.z), (0, 0, 0, 1)))
    out.append(lathe_at("Throat", [(0.0, 0.0, 0), (0.30, 0.0, 0), (0.30, 0.003, 0), (0.0, 0.003, 0)], dark, Md, steps=48))
    return out


def outlet(pp, dark, z0):
    out = []
    zc = z0 + 0.33
    ctrl = [(1.30, 0.10, zc), (1.62, 0.10, zc), (1.95, 0.10, zc + 0.06), (2.25, 0.10, zc + 0.16)]
    path, L = resample_path(smooth_path(ctrl, 16), 0.012)
    def ro(s):
        r = 0.30
        for sb in (0.72, 0.93):
            r += 0.025 * math.exp(-((s - sb) / 0.025) ** 2)
        r += 0.04 * C.smoothstep(0.30, 0.0, s)
        return r
    bm = bmesh.new()
    hose_bm(bm, path, ro, lambda s: 0.26, n=72)
    ob = C.mesh_obj("Outlet", bm, [pp])
    C.add_bevel(ob, 0.006, segments=1, angle=50)
    out.append(C.finalize(ob, angle=50))
    fr = path_frames(path)
    P, U, V, T = fr[int(len(fr) * 0.55)]
    Md = Matrix(((U.x, V.x, T.x, P.x), (U.y, V.y, T.y, P.y), (U.z, V.z, T.z, P.z), (0, 0, 0, 1)))
    out.append(lathe_at("OutletThroat", [(0.0, 0.0, 0), (0.262, 0.0, 0), (0.262, 0.003, 0), (0.0, 0.003, 0)], dark, Md, steps=64))
    # web joining the spigot to the lid end
    def web(bm):
        C.box_bm(bm, 0.30, 0.06, 0.30, center=(1.66, 0.10, zc - 0.36))
    out.append(solid("OutletWeb", web, [pp], bevel=0.01))
    return out


def label(z0):
    im = C.label_image("FilterLabel", 768, 384, seed=7, lines=4)
    m = C.mat_label(im, "FilterLabelMat", rough=0.5)
    M = Matrix.Translation((0.95, -0.35, z0 + 0.5715)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    return [C.label_plane("Label", m, 0.62, 0.31, M)]


def build():
    pp = nylon("BoxPP", color=0.032, rough=0.58, grain=600.0, dust=1.7)
    pu = C.principled("FilterPU", (0.62, 0.24, 0.05), rough=0.75)
    C.add_noise_bump(pu, scale=250, strength=0.15, distance=0.001, rough_var=0.05)
    steel = zinc("ClipZinc", c=0.62, rough=0.26)
    dark = dark_cavity()
    l, z0 = lid(pp, dark)
    objs = lower(pp, dark) + [filter_edge(pu)] + l + clips(steel, z0) + snorkel(pp, dark) + outlet(pp, dark, z0) + label(z0)
    C.transform_all(objs, Matrix.Rotation(math.radians(-6), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("scatola-filtro-aria", objs, "scatola-filtro-aria.py",
            "air filter box: black plastic housing and lid with spring clips, orange filter element edge in the joint, inlet snorkel and outlet duct",
            az=35, el=24, lens=70, fill=0.84, **kw)
