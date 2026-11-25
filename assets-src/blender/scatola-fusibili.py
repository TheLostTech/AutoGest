"""Under-bonnet fuse and relay box (scatola fusibili vano motore) as removed from a small
car, lid off: black polypropylene tub with lid seat, latch catches and mounting feet;
on the deck four ISO relays and two micro relays, a row of colour-coded maxi fuses,
cartridge (J-case) fuses and two rows of mini blade fuses in their holders, a battery
feed stud with nut and thick red cable eyelet; two corrugated harness stubs leave
through rubber boots at one end and end in taped bundles with an inline plug."""
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

L, W, H = 2.0, 1.32, 0.84
ZD = H - 0.07          # deck level inside the rim


def mat_fuse(name, hexcol):
    m = C.principled(name, C.srgb(hexcol), rough=0.22)
    C._set(bsdf(m), "Transmission Weight", 0.45)
    C._set(bsdf(m), "Subsurface Weight", 0.2)
    C._set(bsdf(m), "Subsurface Radius", (0.02, 0.02, 0.02))
    return m


def housing(black, steel):
    out = []
    # tub: slightly tapered walls, open top with a deck inside
    fr = []
    for z, ins in ((0.0, 0.05), (0.06, 0.0), (H - 0.10, 0.0), (H, 0.0)):
        fr.append((Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), rrect(L - ins, W - ins, 0.10, 6)))
    tub = loft("Tub", fr, black)
    cb = bmesh.new()
    C.box_bm(cb, L - 0.07, W - 0.07, 0.4, center=(0, 0, ZD + 0.2))
    cut = C.mesh_obj("TubCut", cb, [black])
    boolean(tub, cut)
    C.add_bevel(tub, 0.012, segments=2, angle=30)
    out.append(C.finalize(tub, angle=35, remove=[cut]))
    # lid seat lip and latch catches on the long sides
    sp = []
    for sy in (-1, 1):
        for x in (-0.55, 0.55):
            sp.append((0.16, 0.06, 0.12, (x, sy * (W / 2 + 0.03), H - 0.16)))
            sp.append((0.16, 0.03, 0.05, (x, sy * (W / 2 + 0.065), H - 0.21)))
    for sx in (-1, 1):
        sp.append((0.06, 0.16, 0.12, (sx * (L / 2 + 0.03), 0.0, H - 0.16)))
    out.append(boxes("Catches", sp, black, bevel=0.01))
    # vertical moulded ribs on the walls
    sp = [(0.035, 0.03, H - 0.30, (x, -W / 2 - 0.01, 0.10 + (H - 0.30) / 2)) for x in (-0.8, -0.3, 0.2, 0.8)]
    out.append(boxes("WallRibs", sp, black, bevel=0.008))
    # mounting foot with steel sleeve on +x end, dovetail slide on the back
    out.append(boxes("Foot", [(0.26, 0.30, 0.05, (L / 2 + 0.11, -0.25, 0.025)), (0.05, 0.30, 0.22, (L / 2 + 0.01, -0.25, 0.11))],
                     black, bevel=0.01, holes=[(0.045, -0.2, 0.2, T((L / 2 + 0.15, -0.25, 0)))]))
    out.append(lathe_at("Sleeve", [(0.03, -0.002, 0), (0.05, -0.002, 0), (0.05, 0.058, 0), (0.03, 0.058, 0)], [steel],
                        T((L / 2 + 0.15, -0.25, 0)), steps=32))
    out.append(boxes("Slide", [(0.9, 0.06, 0.45, (0.2, W / 2 + 0.03, 0.35)), (0.9, 0.04, 0.55, (0.2, W / 2 + 0.07, 0.35))], black,
                     bevel=0.008))
    out.append(boxes("Deck", [(L - 0.07, W - 0.07, 0.04, (0, 0, ZD - 0.02))], black, bevel=0.0))
    return out


def relays(black, grey, holder):
    out = []
    for i, (x, y) in enumerate(((-0.74, 0.32), (-0.42, 0.32), (-0.74, -0.02), (-0.42, -0.02))):
        out.append(boxes("RelaySeat", [(0.31, 0.31, 0.04, (x, y, ZD + 0.02))], holder, bevel=0.008))
        out.append(boxes("Relay", [(0.27, 0.27, 0.27, (x, y, ZD + 0.04 + 0.135)), (0.06, 0.20, 0.02, (x - 0.06, y, ZD + 0.315))],
                         black if i != 2 else grey, bevel=0.018, seg=3))
    for i, (x, y) in enumerate(((0.74, 0.36), (0.74, 0.10))):
        out.append(boxes("Micro", [(0.22, 0.15, 0.24, (x, y, ZD + 0.12))], grey if i else black, bevel=0.014, seg=3))
    # spare positions (empty slots)
    out.append(boxes("Empty", [(0.27, 0.27, 0.04, (-0.58, -0.38, ZD + 0.02))], holder, bevel=0.008))
    return out


def fuses(holder, holes, pal, maxi_pal, jcase_pal, clear):
    out = []
    rnd = random.Random(7)
    # two rows of mini blade fuses
    for row, y in enumerate((0.42, 0.25)):
        out.append(boxes("MiniHolder", [(0.74, 0.12, 0.06, (0.17, y, ZD + 0.03))], holder, bevel=0.008))
        by = {}
        for i in range(8):
            x = -0.14 + i * 0.088
            if rnd.random() < 0.12:
                out.append(boxes("Slot", [(0.05, 0.018, 0.004, (x, y, ZD + 0.061))], holes, bevel=0.0))
                continue
            mi = rnd.choice((0, 0, 1, 1, 2, 3, 4))
            by.setdefault(mi, []).extend([(0.064, 0.018, 0.08, (x, y, ZD + 0.06 + 0.04)),
                                          (0.072, 0.026, 0.022, (x, y, ZD + 0.06 + 0.09))])
        for mi, sp in by.items():
            out.append(boxes("Mini%d" % mi, sp, pal[mi], bevel=0.004, seg=1))
    # maxi fuses
    out.append(boxes("MaxiHolder", [(0.74, 0.17, 0.07, (0.17, -0.02, ZD + 0.035))], holder, bevel=0.01))
    for i, mi in enumerate((1, 0, 2, 3, 1)):
        x = -0.11 + i * 0.14
        out.append(boxes("Maxi", [(0.11, 0.035, 0.12, (x, -0.02, ZD + 0.07 + 0.06)), (0.12, 0.05, 0.035, (x, -0.02, ZD + 0.205))],
                         maxi_pal[mi], bevel=0.007))
    # J-case cartridge fuses with clear windows
    for i, mi in enumerate((0, 1, 2, 0)):
        x = -0.12 + i * 0.19
        out.append(boxes("JHolder", [(0.18, 0.18, 0.05, (x, -0.36, ZD + 0.025))], holder, bevel=0.008))
        out.append(boxes("JCase", [(0.15, 0.15, 0.12, (x, -0.36, ZD + 0.05 + 0.06))], jcase_pal[mi], bevel=0.012, seg=2))
        out.append(boxes("JWin", [(0.10, 0.06, 0.012, (x, -0.36, ZD + 0.175))], clear, bevel=0.004))
    return out


def battery_feed(k, steel, red_m):
    out = []
    x, y = 0.74, -0.32
    out.append(boxes("StudBlock", [(0.24, 0.24, 0.10, (x, y, ZD + 0.05))], k.pl("#1A1A1C"), bevel=0.012))
    out.append(lathe_at("Stud", [(0.0, ZD + 0.10, 0), (0.035, ZD + 0.10, 0), (0.035, ZD + 0.27, 0), (0.0, ZD + 0.27, 0)],
                        [steel], T((x, y, 0)), steps=32))
    out.append(lathe_at("Eye", [(0.04, ZD + 0.10, 0), (0.10, ZD + 0.10, 0), (0.10, ZD + 0.12, 0), (0.04, ZD + 0.12, 0)],
                        [k.tin], T((x, y, 0)), steps=48, bevel=0.003))
    out.append(hex_at("Nut", 0.065, ZD + 0.12, ZD + 0.19, steel, T((x, y, 0)), bevel=0.006))
    # thick red battery cable from the eyelet, over the rim, down to the floor
    pts = [Vector((x + 0.08, y, ZD + 0.11)), Vector((x + 0.20, y - 0.02, ZD + 0.12)), Vector((L / 2 + 0.15, y - 0.06, ZD + 0.05)),
           Vector((L / 2 + 0.32, y - 0.15, 0.40)), Vector((L / 2 + 0.42, y - 0.40, 0.08)), Vector((L / 2 + 0.40, y - 0.80, 0.075)),
           Vector((L / 2 + 0.15, y - 1.05, 0.075))]
    ob, _ = ptube("BatteryCable", pts, 0.075, red_m, nsec=20, step=0.02)
    out.append(ob)
    out.append(lathe_at("Crimp", [(0.0, -0.08, 0), (0.08, -0.08, 0), (0.08, 0.08, 0), (0.0, 0.08, 0)], [k.tin],
                        axis_mat(pts[0] + Vector((0.07, -0.004, 0.0)), (1, -0.15, 0.05)), steps=24))
    # cut end: copper strands
    cu = C.principled("Copper", (0.85, 0.45, 0.25), metallic=1.0, rough=0.35)
    C.add_noise_bump(cu, scale=900, strength=0.4, distance=0.002)
    d = (pts[-1] - pts[-2]).normalized()
    out.append(lathe_at("Strands", [(0.0, 0.0, 0), (0.068, 0.0, 0), (0.066, 0.03, 0), (0.0, 0.035, 0)], [cu], axis_mat(pts[-1], d), steps=24))
    return out


def stubs(k):
    # two corrugated harness stubs out of rubber boots on the -x end
    rub = C.mat_rubber("Boot")
    for (y, pts, spec) in ((0.30, [(-L / 2 - 0.30, 0.42, 0.14), (-L / 2 - 0.85, 0.75, 0.11), (-L / 2 - 1.35, 0.55, 0.11),
                                   (-L / 2 - 1.75, 0.15, 0.11)],
                            dict(w=0.40, h=0.22, L=0.34, cols=6, rows=2, col="#2B2C30", rear="#7A7C80", wires=8)),
                           (-0.25, [(-L / 2 - 0.30, -0.35, 0.12), (-L / 2 - 0.75, -0.55, 0.11), (-L / 2 - 1.05, -1.0, 0.11)],
                            dict(w=0.32, h=0.20, L=0.30, cols=4, rows=2, col="#E2DCC8", rear="#1A1A1A", wires=6))):
        start = Vector((-L / 2 + 0.05, y, 0.22))
        d = k.bundle("Stub", [start, Vector((-L / 2 - 0.12, y + 0.02, 0.20))] + [Vector(p) for p in pts], 0.11, "corr")
        k.objs.append(lathe_at("Boot", [(0.10, 0.0, 0), (0.17, 0.0, 0), (0.17, 0.05, 0), (0.15, 0.09, 0), (0.125, 0.22, 0),
                                        (0.10, 0.25, 0)], [rub], axis_mat((-L / 2 + 0.02, y, 0.22), (-1, 0, -0.08)), steps=48))
        k.end_plug(d, 0.11, spec, gap=0.30)


def build():
    k = Kit()
    black = k.pl("#141416", rough=0.5)
    holder = k.pl("#232325", rough=0.5)
    grey = k.pl("#55575B", rough=0.45)
    steel = steel_zinc()
    pal = [mat_fuse("FRed", "#B42420"), mat_fuse("FBlue", "#2A5BA8"), mat_fuse("FYellow", "#D6AA22"), mat_fuse("FGreen", "#2F8540"),
           mat_fuse("FTan", "#C9A36B")]
    maxi = [mat_fuse("MYellow", "#D6AA22"), mat_fuse("MGreen", "#2F8540"), mat_fuse("MOrange", "#D8741E"), mat_fuse("MRed", "#B42420")]
    jcase = [plastic("JPink", "#D86A8E", rough=0.35), plastic("JGreen", "#3A8A4A", rough=0.35), plastic("JBlue", "#2F5E9E", rough=0.35)]
    clear = C.mat_clear("JWindow", rough=0.1)
    red = mat_wire("BattRed", "#9A2018")
    objs = housing(black, steel) + relays(black, grey, holder) + fuses(holder, k.holes, pal, maxi, jcase, clear)
    objs += battery_feed(k, steel, red)
    stubs(k)
    objs += k.objs
    C.transform_all(objs, R(math.radians(-8), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shoot("scatola-fusibili", objs,
          "under-bonnet fuse and relay box with lid removed: black box with relays, colour-coded maxi and mini fuses, "
          "battery cable on a stud, corrugated harness stubs",
          az=24, el=46, lens=70, fill=0.88)
