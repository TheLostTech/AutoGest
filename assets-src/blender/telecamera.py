"""Rear-view (reversing) camera (telecamera retromarcia) as removed from the tailgate of a
small car: compact black die-cast/PBT housing with rounded edges, lens barrel with a
coated glass front element and clamping ring, rubber seal at the rear cover, black
plastic mounting bracket with two screw holes, and a pigtail cable ending in a coded
coaxial (FAKRA-type) plug with a second 4-pin plug for power."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
R = Matrix.Rotation
PREV = bool(os.environ.get("PREV"))


# ----------------------------------------------------------------- geometry helpers
def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def frame_matrix(P, X, Z):
    """Matrix with local X along X, local Z as close as possible to Z, origin P."""
    X = Vector(X).normalized()
    Z = Vector(Z)
    Z = (Z - X * Z.dot(X)).normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P[0]), (X.y, Y.y, Z.y, P[1]), (X.z, Y.z, Z.z, P[2]), (0, 0, 0, 1)))


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return T(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def loft(name, frames, mat, cap=True):
    bm = bmesh.new()
    C.sweep(bm, frames, cap=cap)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats if isinstance(mats, (list, tuple)) else [mats], steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def boolean(ob, cutter, op="DIFFERENCE"):
    m = C.add_boolean(ob, cutter, op)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def boxes(name, specs, mat, bevel=0.01, holes=(), seg=2, M=None, angle=32):
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
        boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=[cut] if cut else [])


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2, angle=32):
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
        boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=[cut] if cut else [])


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ R(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def catmull(pts, step=0.01):
    P = [Vector(p) for p in pts]
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        k = max(2, int((p2 - p1).length / step))
        for j in range(k):
            t = j / k
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2].copy())
    return out


def frames_along(path, up=(0, 0, 1)):
    """Parallel-transport frames: [(P, T, N, B, s)]"""
    n = len(path)
    out = []
    s = 0.0
    N = None
    for i in range(n):
        a = path[max(0, i - 1)]
        b = path[min(n - 1, i + 1)]
        Tg = (b - a).normalized()
        if i:
            s += (path[i] - path[i - 1]).length
        if N is None:
            u = Vector(up)
            if abs(u.dot(Tg)) > 0.95:
                u = Vector((1, 0, 0))
            N = (u - Tg * u.dot(Tg)).normalized()
        else:
            N = (N - Tg * N.dot(Tg)).normalized()
        out.append((path[i], Tg, N, Tg.cross(N), s))
    return out


def ptube(name, pts, r, mat, nsec=16, step=0.01, rfun=None, caps=True, up=(0, 0, 1), dense=None):
    """Tube through control pts (catmull-rom). r constant or rfun(s, th, total) -> radius.
    UVs: u = arc length (scene units), v = angle / TAU."""
    path = dense if dense is not None else catmull(pts, step)
    fr = frames_along(path, up)
    total = fr[-1][4]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for (P, Tg, N, B, s) in fr:
        ring = []
        for k in range(nsec):
            th = TAU * k / nsec
            rr = rfun(s, th, total) if rfun else r
            ring.append(bm.verts.new(P + rr * (math.cos(th) * N + math.sin(th) * B)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(nsec):
            k2 = (k + 1) % nsec
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.smooth = True
            for l, (uu, vv) in zip(f.loops, ((fr[i][4], k / nsec), (fr[i][4], (k + 1) / nsec),
                                             (fr[i + 1][4], (k + 1) / nsec), (fr[i + 1][4], k / nsec))):
                l[uvl].uv = (uu, vv)
    if caps:
        for ring, P, flip in ((rings[0], fr[0][0], True), (rings[-1], fr[-1][0], False)):
            c = bm.verts.new(P)
            for k in range(nsec):
                k2 = (k + 1) % nsec
                vs = (c, ring[k2], ring[k]) if flip else (c, ring[k], ring[k2])
                f = bm.faces.new(vs)
                f.smooth = True
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    return ob, fr


def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


# ----------------------------------------------------------------- materials
def plastic(name, hexcol=None, rough=0.45, color=0.03, tex=True):
    m = C.mat_black_plastic(name, rough=rough, color=color, tex=tex)
    if hexcol:
        C._set(bsdf(m), "Base Color", C.srgb(hexcol))
    return m


def steel_zinc(name="ZincSteel"):
    m = C.principled(name, (0.60, 0.61, 0.62), metallic=1.0, rough=0.26)
    C.add_noise_bump(m, scale=900, strength=0.03, distance=0.0005)
    return m


def tin(name="TinPin"):
    return C.principled(name, (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)


def brass(name="Brass"):
    return C.principled(name, (0.80, 0.62, 0.32), metallic=1.0, rough=0.25)


def hole_mat(name="Hole"):
    return C.principled(name, (0.003, 0.003, 0.003), rough=0.85)


def mat_ecoat(name="Ecoat"):
    m = C.principled(name, (0.028, 0.028, 0.03), metallic=0.2, rough=0.42)
    C._set(bsdf(m), "Coat Weight", 0.25)
    C._set(bsdf(m), "Coat Roughness", 0.25)
    C.add_noise_bump(m, scale=500, strength=0.05, distance=0.0006, rough_var=0.06)
    return m


def mat_diecast(name, base=0.46, rough=0.42):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = bsdf(m)
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


def matte_floor_in_reflections():
    """Hide the white shadow-catcher floor from glossy rays (contact shadow stays)."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


def shoot(name, objs, desc, **kw):
    if PREV:
        kw.setdefault("res", (512, 512))
        kw.setdefault("samples", 32)
    C.shoot(name, objs, name + ".py", desc, **kw)


# ----------------------------------------------------------------- connectors
def plug(name, M, w, h, L, shell, holes_m, cols=2, rows=1, latch=True, rear=None, seal=None):
    """Wire-side connector housing. Local: rear (wire entry) at x=0, mating face at x=L,
    width along y, latch on +z. Returns (objs, rear_points_world)."""
    out = []
    out.append(boxes(name, [(L, w, h, (L / 2, 0, 0))], shell, bevel=min(w, h) * 0.08, seg=2, M=M))
    sp = []
    # side ribs
    for sy in (-1, 1):
        sp.append((L * 0.55, 0.012 + w * 0.03, h * 0.55, (L * 0.45, sy * (w / 2 + 0.004), 0)))
    if latch:
        lw = min(w * 0.45, 0.12)
        sp.append((L * 0.62, lw, 0.016 + h * 0.06, (L * 0.52, 0, h / 2 + 0.006 + h * 0.03)))
        sp.append((0.03, lw * 1.15, 0.03 + h * 0.08, (L * 0.24, 0, h / 2 + 0.012 + h * 0.04)))
        for sy in (-1, 1):
            sp.append((L * 0.7, 0.012, 0.02 + h * 0.06, (L * 0.5, sy * (lw / 2 + 0.012), h / 2 + 0.006)))
    out.append(boxes(name + "Ribs", sp, shell, bevel=0.004, seg=1, M=M))
    # rear seal / secondary lock in the wire entry face
    if rear is not None:
        out.append(boxes(name + "Rear", [(0.03, w * 0.86, h * 0.8, (-0.01, 0, 0))], rear, bevel=0.006, M=M))
    # cavities on the mating face
    hs = []
    pw, ph = w / (cols + 0.6), h / (rows + 0.6)
    s = min(pw, ph) * 0.5
    for i in range(cols):
        for j in range(rows):
            y = (i - (cols - 1) / 2) * pw
            z = (j - (rows - 1) / 2) * ph
            hs.append((0.01, s, s, (L + 0.003, y, z)))
    out.append(boxes(name + "Cav", hs, holes_m, bevel=0.0, M=M))
    pts = []
    n = cols * rows
    for i in range(cols):
        for j in range(rows):
            y = (i - (cols - 1) / 2) * pw * 0.8
            z = (j - (rows - 1) / 2) * ph * 0.7
            pts.append(M @ Vector((-0.02, y, z)))
    return out, pts


def socket(name, M, w, h, d, shell, pin_m, cols=3, rows=1, ramp=True):
    """Device-side shroud with pins. Local: mouth at x=d (open toward +x), back at x=0."""
    out = []
    bm = bmesh.new()
    C.box_bm(bm, d, w, h, center=(d / 2, 0, 0))
    sh = C.mesh_obj(name, bm, [shell])
    sh.matrix_world = M
    t = max(0.012, min(w, h) * 0.09)
    cb = bmesh.new()
    C.box_bm(cb, d, w - 2 * t, h - 2 * t, center=(d / 2 + 0.25 * d, 0, 0))
    cut = C.mesh_obj(name + "Cut", cb, [shell])
    cut.matrix_world = M
    boolean(sh, cut)
    C.add_bevel(sh, t * 0.3, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    if ramp:
        out.append(boxes(name + "Ramp", [(d * 0.35, min(w * 0.4, 0.10), 0.018, (d * 0.7, 0, h / 2 + 0.008))], shell,
                         bevel=0.004, seg=1, M=M))
    pw, ph = (w - 2 * t) / (cols + 0.5), (h - 2 * t) / (rows + 0.5)
    ps = min(pw, ph) * 0.28
    sp = []
    for i in range(cols):
        for j in range(rows):
            sp.append((d * 0.6, ps, ps, (d * 0.25 + d * 0.3, (i - (cols - 1) / 2) * pw, (j - (rows - 1) / 2) * ph)))
    out.append(boxes(name + "Pins", sp, pin_m, bevel=0.0, M=M))
    return out


def label(name, w, h, M, seed=3, lines=4):
    im = C.label_image(name + "Img", 1024, int(1024 * h / w), seed=seed, lines=lines)
    return C.label_plane(name, C.mat_label(im), w, h, M)


# ----------------------------------------------------------------- wiring harness kit
WIRE_COLS = ["#151515", "#5A3A22", "#B0241E", "#2A56A8", "#D8B31E", "#2E8A3E", "#E8E6E0", "#8A8C90",
             "#6A3A8C", "#D86A1E", "#D88AA8", "#3FA0B8"]


def mat_wire(name, hexcol):
    m = C.principled(name, C.srgb(hexcol), rough=0.32)
    C._set(bsdf(m), "Coat Weight", 0.2)
    C.add_noise_bump(m, scale=300, strength=0.03, distance=0.0004)
    return m


def _uv_split(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sp.inputs[0])
    return sp


def mat_tape(name, pitch=0.07, rough=0.42, color=0.018, fleece=False, hexcol=None):
    """Spiral-wound tape: sawtooth overlap edge from the tube UVs (u = length, v = angle)."""
    m = C.principled(name, (color, color, color * 1.05) if not hexcol else C.srgb(hexcol), rough=rough)
    nt = m.node_tree
    b = bsdf(m)
    sp = _uv_split(nt)
    ma = nt.nodes.new("ShaderNodeMath")
    ma.operation = "MULTIPLY_ADD"
    nt.links.new(sp.outputs["X"], ma.inputs[0])
    ma.inputs[1].default_value = 1.0 / pitch
    nt.links.new(sp.outputs["Y"], ma.inputs[2])
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    nt.links.new(ma.outputs[0], fr.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(fr.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 0.35
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.35 if not fleece else 0.2
    bp.inputs["Distance"].default_value = 0.004
    nt.links.new(pw.outputs[0], bp.inputs["Height"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1400.0 if fleece else 500.0
    nz.inputs["Detail"].default_value = 8.0
    bp2 = nt.nodes.new("ShaderNodeBump")
    bp2.inputs["Strength"].default_value = 0.45 if fleece else 0.05
    bp2.inputs["Distance"].default_value = 0.002 if fleece else 0.0005
    nt.links.new(nz.outputs["Fac"], bp2.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bp2.inputs["Normal"])
    nt.links.new(bp2.outputs["Normal"], b.inputs["Normal"])
    if fleece:
        C._set(b, "Sheen Weight", 0.6)
        C._set(b, "Sheen Roughness", 0.4)
        C._set(b, "Sheen Tint", (0.7, 0.7, 0.72, 1))
    else:
        # slight sheen variation along the overlap
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough + 0.08
        mr.inputs["To Max"].default_value = rough - 0.08
        nt.links.new(fr.outputs[0], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_corr(name="CorrugatedPP"):
    m = C.principled(name, (0.016, 0.016, 0.017), rough=0.36)
    C._set(bsdf(m), "Coat Weight", 0.15)
    C.add_noise_bump(m, scale=600, strength=0.04, distance=0.0005, rough_var=0.05)
    return m


def corr_rfun(r, pitch):
    def f(s, th, total):
        return r * (0.86 + 0.14 * abs(math.sin(math.pi * s / pitch)) ** 0.45)
    return f


def point_at(dense, f):
    i = max(1, min(len(dense) - 2, int(f * (len(dense) - 1))))
    return dense[i].copy(), (dense[i + 1] - dense[i - 1]).normalized()


class Kit:
    def __init__(self, fleece=False):
        self.corr = mat_corr()
        self.tape = mat_tape("PVCTape", pitch=0.06)
        self.fleece = mat_tape("FleeceTape", pitch=0.11, rough=0.88, color=0.03, fleece=True) if fleece else None
        self.wires = [mat_wire("Wire%d" % i, c) for i, c in enumerate(WIRE_COLS)]
        self.holes = hole_mat()
        self.tin = tin()
        self.plastics = {}
        self.objs = []
        self.rnd = random.Random(11)

    def pl(self, hexcol, rough=0.45):
        if hexcol not in self.plastics:
            self.plastics[hexcol] = plastic("PA_" + hexcol.strip("#"), hexcol, rough=rough)
        return self.plastics[hexcol]

    # -- bundles
    def bundle(self, name, ctrl, r, kind="tape", nsec=None):
        if kind == "corr":
            pitch = max(0.03, r * 0.42)
            ob, fr = ptube(name, ctrl, r, self.corr, nsec=nsec or 22, step=pitch / 9, rfun=corr_rfun(r, pitch))
        else:
            mat = self.fleece if kind == "fleece" else self.tape
            wob = lambda s, th, total, r=r: r * (1.0 + 0.025 * math.sin(s * 7.0 + 1.3) + 0.02 * math.sin(s * 23.0))
            ob, fr = ptube(name, ctrl, r, mat, nsec=nsec or 16, step=0.02, rfun=wob)
        self.objs.append(ob)
        return [f[0] for f in fr]

    def wrap(self, dense, i0, i1, r, kind="tape"):
        i0, i1 = max(0, i0), min(len(dense) - 1, i1)
        mat = self.fleece if kind == "fleece" else self.tape
        ob, _ = ptube("Wrap", None, r, mat, nsec=18, dense=dense[i0:i1 + 1],
                      rfun=lambda s, th, total: r * (1 + 0.04 * smooth_end(s, total)))
        self.objs.append(ob)

    def junction(self, dense, f, r, kind="tape", span=0.13):
        n = len(dense)
        i = int(f * (n - 1))
        L = (dense[-1] - dense[0]).length / max(1, n) or 0.01
        seg = sum((dense[k + 1] - dense[k]).length for k in range(max(0, i - 5), min(n - 1, i + 5))) / 10
        k = max(3, int(span / max(seg, 1e-4)))
        self.wrap(dense, i - k, i + k, r * 1.08 + 0.008, kind)

    def branch(self, parent, f, offsets, r, kind="tape", z=None, wrap_kind="tape", parent_r=0.1):
        J, tg = point_at(parent, f)
        zz = r if z is None else z
        ctrl = [J] + [Vector((J.x + o[0], J.y + o[1], o[2] if len(o) > 2 else zz)) for o in offsets]
        d = self.bundle("Branch", ctrl, r, kind)
        self.junction(parent, f, parent_r, wrap_kind)
        return d

    # -- terminations
    def end_tg(self, dense, flat=True):
        E = dense[-1]
        k = max(2, min(len(dense) - 1, 6))
        tg = (dense[-1] - dense[-k]).normalized()
        if flat:
            tg = Vector((tg.x, tg.y, 0)).normalized()
        return E, tg

    def wires_to(self, E, tg, rb, targets, z_end=None):
        """individual wires from bundle end E (direction tg) to [(point, dir)]"""
        up = Vector((0, 0, 1))
        side = tg.cross(up).normalized()
        n = len(targets)
        for i, (q, qd) in enumerate(targets):
            a = TAU * i / max(1, n) + 0.4
            off = side * math.cos(a) * rb * 0.5 + up * math.sin(a) * rb * 0.45
            s0 = E - tg * 0.05 + off
            s1 = E + tg * 0.02 + off
            q0 = q - qd * 0.07
            mid = (s1 + q0) / 2 + side * self.rnd.uniform(-0.02, 0.02) + up * self.rnd.uniform(-0.005, 0.01)
            m = self.wires[(i * 5 + int(E.x * 7)) % len(self.wires)] if n > 1 else self.wires[0]
            ob, _ = ptube("Wire", [s0, s1, mid, q0, q + qd * 0.02], 0.0125, m, nsec=8, step=0.012)
            self.objs.append(ob)

    def end_plug(self, dense, rb, spec, gap=0.24, kind="tape", end_wrap=True):
        """spec: dict(w, h, L, cols, rows, col, rear)"""
        E, tg = self.end_tg(dense)
        h = spec["h"]
        P0 = Vector((E.x, E.y, 0)) + tg * gap + Vector((0, 0, h / 2 + 0.003))
        M = frame_matrix(P0, tg, (0, 0, 1)) @ R(math.radians(spec.get("roll", 0)), 4, "X")
        shell = self.pl(spec["col"])
        rear = self.pl(spec["rear"]) if spec.get("rear") else None
        objs, pts = plug("Plug", M, spec["w"], h, spec["L"], shell, self.holes, spec.get("cols", 2),
                         spec.get("rows", 1), latch=spec.get("latch", True), rear=rear)
        self.objs += objs
        nw = spec.get("wires", len(pts))
        pts = pts[:nw]
        self.wires_to(E, tg, rb, [(q, tg) for q in pts])
        if end_wrap:
            self.end_wrap(dense, rb, kind)
        return M

    def end_wrap(self, dense, rb, kind="tape"):
        n = len(dense)
        acc, i = 0.0, n - 1
        while i > 0 and acc < 0.10:
            acc += (dense[i] - dense[i - 1]).length
            i -= 1
        self.wrap(dense, i, n - 1, rb * 1.1 + 0.006, kind)

    def eyelet(self, dense, rb, gap=0.22, rr=0.07, col=None):
        E, tg = self.end_tg(dense)
        P0 = Vector((E.x, E.y, 0.006)) + tg * (gap + rr)
        M = frame_matrix(P0, tg, (0, 0, 1))
        self.objs.append(lathe_at("Eyelet", [(rr * 0.48, -0.005, 0), (rr, -0.005, 0), (rr, 0.005, 0), (rr * 0.48, 0.005, 0)],
                                  [self.tin], M, steps=48, bevel=0.002))
        self.objs.append(boxes("EyeNeck", [(rr * 0.9, rr * 0.7, 0.01, (-rr * 1.2, 0, 0))], self.tin, bevel=0.002, M=M))
        barrel = M @ Vector((-rr * 1.65 - 0.05, 0, 0.012))
        bt = M.to_3x3() @ Vector((1, 0, 0))
        ob, _ = ptube("Barrel", [barrel - bt * 0.05, barrel + bt * 0.05], 0.024, self.tin, nsec=16, step=0.01)
        self.objs.append(ob)
        w = self.wires[col if col is not None else 0]
        ob, _ = ptube("EarthWire", [E - tg * 0.05, E + tg * 0.04, (E + barrel) / 2 + Vector((0, 0, -0.005)),
                                    barrel - bt * 0.04], 0.022, w, nsec=10, step=0.012)
        self.objs.append(ob)
        self.end_wrap(dense, rb)


def smooth_end(s, total):
    return 1.0 - abs(2 * s / max(total, 1e-6) - 1.0) ** 4


def housing(body, black, seal):
    out = []
    W, D, H = 0.30, 0.28, 0.25
    poly = rrect(W, H, 0.06, 8)
    # housing extruded along -Y (front face at y = 0)
    M = R(-math.pi / 2, 4, "X")
    out.append(prism("Housing", poly, 0.0, D, body, M=M, bevel=0.016, seg=3))
    out.append(prism("RearCover", rrect(W - 0.02, H - 0.02, 0.05, 8), D, D + 0.05, black, M=M, bevel=0.012, seg=2))
    out.append(prism("Seal", rrect(W - 0.015, H - 0.015, 0.052, 8), D - 0.004, D + 0.006, seal, M=M, bevel=0.002))
    # front bezel
    out.append(prism("Bezel", rrect(W - 0.03, H - 0.03, 0.05, 8), -0.012, 0.0, black, M=M, bevel=0.006))
    return out


def lens(black, glass, coat, ring_m):
    out = []
    M = axis_mat((0, -0.012, 0.0), (0, -1, 0))
    out.append(lathe_at("Barrel", [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.085, 0.03, 0), (0.075, 0.045, 0), (0.06, 0.05, 0), (0.0, 0.05, 0)],
                        [ring_m], M, steps=96, bevel=0.003))
    out.append(lathe_at("Coating", [(0.0, 0.035, 0), (0.055, 0.035, 0), (0.055, 0.045, 0), (0.0, 0.052, 0)], [coat], M, steps=64))
    P = [(0.0, 0.066, 0)]
    for i in range(1, 13):
        a = math.pi / 2 * i / 12
        P.append((0.058 * math.sin(a), 0.044 + 0.022 * math.cos(a), 0))
    P.append((0.0, 0.044, 0))
    out.append(lathe_at("FrontElement", P, [glass], M, steps=96))
    return out


def bracket(black, steel):
    out = []
    # L-bracket hugging the top, with two screw ears
    sp = [(0.42, 0.20, 0.025, (0.0, 0.12, 0.1375)), (0.025, 0.20, 0.10, (0.175, 0.12, 0.09)), (0.025, 0.20, 0.10, (-0.175, 0.12, 0.09)),
          (0.62, 0.12, 0.025, (0.0, 0.18, 0.1375))]
    out.append(boxes("Bracket", sp, black, bevel=0.006,
                     holes=[(0.022, 0.0, 0.3, T((sx * 0.255, 0.18, 0.0))) for sx in (-1, 1)]))
    for sx in (-1, 1):
        out.append(lathe_at("Sleeve", [(0.022, 0.124, 0), (0.035, 0.124, 0), (0.035, 0.152, 0), (0.022, 0.152, 0)], [steel],
                            T((sx * 0.255, 0.18, 0)), steps=32))
    return out


def cable(k, start, d0, zf):
    jacket = mat_wire("Jacket", "#151515")
    C._set(bsdf(jacket), "Roughness", 0.5)
    z = zf + 0.022
    pts = [start, start + d0 * 0.16, Vector((0.10, 0.58, z + 0.01)), Vector((0.38, 0.74, z)),
           Vector((0.64, 0.60, z)), Vector((0.76, 0.34, z))]
    ob, fr = ptube("Cable", pts, 0.022, jacket, nsec=12, step=0.01)
    k.objs.append(ob)
    k.objs.append(lathe_at("Strain", [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.045, 0.06, 0), (0.03, 0.14, 0), (0.024, 0.16, 0), (0.0, 0.16, 0)],
                           [k.pl("#1A1A1A")], axis_mat(start - d0 * 0.01, d0), steps=32))
    dense = [f[0] for f in fr]
    # split: coax to a FAKRA plug, power pair to a small 4-pin plug
    E, tg = k.end_tg(dense)
    side = tg.cross(Vector((0, 0, 1))).normalized()
    for (s, spec) in ((1, dict(w=0.13, h=0.12, L=0.22, cols=1, rows=1, col="#5A3B7A", latch=True)),
                      (-1, dict(w=0.17, h=0.10, L=0.20, cols=2, rows=2, col="#1E1E20", wires=2))):
        ctrl = [E, E + tg * 0.08 + side * s * 0.04, E + tg * 0.30 + side * s * 0.16]
        ctrl = [Vector((c.x, c.y, zf + 0.018)) for c in ctrl]
        ob, fr2 = ptube("Lead", ctrl, 0.016 if s > 0 else 0.013, jacket, nsec=10, step=0.01)
        k.objs.append(ob)
        d2 = [f[0] for f in fr2]
        E2, tg2 = k.end_tg(d2)
        Mp = frame_matrix(Vector((E2.x, E2.y, zf + spec["h"] / 2 + 0.002)), tg2, (0, 0, 1))
        objs, pts = plug("Plug", Mp, spec["w"], spec["h"], spec["L"], k.pl(spec["col"]), k.holes, spec["cols"], spec["rows"],
                         latch=True)
        k.objs += objs
    k.objs.append(lathe_at("SplitBoot", [(0.0, -0.05, 0), (0.035, -0.05, 0), (0.035, 0.03, 0), (0.0, 0.05, 0)], [k.pl("#1A1A1A")],
                           axis_mat(E, tg), steps=24))


def build():
    k = Kit()
    body = mat_diecast("HousingAlu", base=0.06, rough=0.45)
    black = plastic("PBT", rough=0.45, color=0.026)
    seal = C.mat_rubber("Seal")
    steel = steel_zinc()
    glass = C.mat_clear("LensGlass", ior=1.52)
    coat = C.principled("LensCoat", (0.02, 0.03, 0.05), metallic=0.0, rough=0.05)
    C._set(bsdf(coat), "Thin Film Thickness", 480.0)
    C._set(bsdf(coat), "Thin Film IOR", 1.4)
    ring_m = C.principled("LensRing", (0.04, 0.04, 0.045), metallic=0.6, rough=0.3)
    objs = housing(body, black, seal) + lens(black, glass, coat, ring_m) + bracket(black, steel)
    # tilt the camera down like when fitted, then add the cable on the floor
    Rt = R(math.radians(-18), 4, "X")
    C.transform_all(objs, Rt)
    zf = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    cable(k, Rt @ Vector((0, 0.32, 0)), (Rt.to_3x3() @ Vector((0, 1, 0))).normalized(), zf)
    objs += k.objs
    C.transform_all(objs, R(math.radians(-24), 4, "Z"))
    return objs


if __name__ == "__main__":
    matte_floor_in_reflections()
    C.clear()
    objs = build()
    shoot("telecamera", objs,
          "rear view reversing camera: small black housing with glass lens, mounting bracket, pigtail cable with coaxial "
          "and 4-pin plugs",
          az=-28, el=26, lens=70, fill=0.84)
