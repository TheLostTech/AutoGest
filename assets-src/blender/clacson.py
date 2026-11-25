"""Electric disc horn (clacson) as removed from a small car: black painted pressed-steel
body with crimped rim, stamped front with raised centre dome, ring bead and rivet, coil
cup on the back, zinc-plated spring-steel bracket held by a nut on the centre stud and
bent back with a slotted mounting hole, single 6.3 mm spade terminal on a black
insulator block."""
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


def smooth_prof(pts, n=4):
    """Round the corners of a polyline profile [(r, z)] with small quadratic fillets."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        p0 = b + (a - b) * 0.3
        p2 = b + (c - b) * 0.3
        for k in range(n + 1):
            t = k / n
            q = p0 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p2 * t * t
            out.append((q.x, q.y))
    out.append(pts[-1])
    return [(max(0.0, r), z, 0) for r, z in out]


def body(paint):
    P = [(0.0, -0.31), (0.19, -0.31), (0.245, -0.29), (0.255, -0.17), (0.31, -0.125), (0.40, -0.085),
         (0.458, -0.045), (0.472, -0.005), (0.472, 0.038), (0.455, 0.056), (0.418, 0.054), (0.400, 0.030),
         (0.345, 0.024), (0.332, 0.036), (0.318, 0.024), (0.235, 0.026), (0.205, 0.058), (0.165, 0.080),
         (0.080, 0.092), (0.0, 0.096)]
    return lathe_at("HornBody", smooth_prof(P), [paint], Matrix(), steps=160, angle=40)


def front_details(paint, steel):
    out = []
    # rivet head and adjusting screw boss in the middle of the dome
    out.append(lathe_at("Rivet", [(0.0, 0.09, 0), (0.05, 0.09, 0), (0.05, 0.105, 0), (0.035, 0.118, 0),
                                  (0.0, 0.122, 0)], [paint], Matrix(), steps=64, bevel=0.003))
    return out


def back(paint, steel, zinc, black, pin):
    out = []
    # centre stud + nut clamping the bracket
    out.append(lathe_at("Stud", [(0.0, -0.40, 0), (0.035, -0.40, 0), (0.035, -0.30, 0), (0.0, -0.30, 0)],
                        [steel], Matrix(), steps=32))
    out.append(hex_at("Nut", 0.058, -0.395, -0.355, steel, Matrix(), bevel=0.005))
    out.append(lathe_at("Washer", [(0.036, -0.357, 0), (0.075, -0.357, 0), (0.075, -0.345, 0), (0.036, -0.345, 0)],
                        [steel], Matrix(), steps=48, bevel=0.002))
    # spring-steel bracket: flat strip up to beyond the rim, bent back, slotted hole
    Rx = R(math.pi / 2, 4, "X")
    out.append(boxes("Bracket", [(0.17, 0.70, 0.022, (0, 0.30, -0.334)),
                                 (0.17, 0.022, 0.30, (0, 0.639, -0.473))], zinc, bevel=0.006,
                     holes=[(0.032, -0.2, 0.2, T((0, 0.639, -0.53)) @ Rx),
                            (0.032, -0.2, 0.2, T((0, 0.639, -0.49)) @ Rx)]))
    out.append(boxes("BracketSlot", [(0.064, 0.05, 0.04, (0, 0.639, -0.51))], zinc, bevel=0.0) if False else
               boxes("BracketRib", [(0.05, 0.40, 0.012, (0, 0.33, -0.350))], zinc, bevel=0.004))
    # terminal insulator and spade
    Mt = T((0.30, -0.05, -0.20)) @ R(math.radians(180 + 30), 4, "Y")
    out.append(boxes("Insulator", [(0.12, 0.10, 0.09, (0, 0, 0))], black, bevel=0.012, M=Mt))
    out.append(boxes("Spade", [(0.11, 0.063, 0.008, (-0.10, 0, 0.0))], pin, bevel=0.002, M=Mt,
                     holes=[(0.011, -0.1, 0.1, T((-0.11, 0, 0)))]))
    out.append(boxes("Rivet2", [(0.03, 0.03, 0.02, (-0.045, 0, 0.012))], pin, bevel=0.004, M=Mt))
    return out


def build():
    paint = C.mat_paint("HornPaint", (0.018, 0.018, 0.02, 1), rough=0.38, coat=0.35)
    C.add_noise_bump(paint, scale=420, strength=0.05, distance=0.0006, rough_var=0.05)
    steel = steel_zinc("Steel")
    zinc = C.principled("ZincYellow", (0.80, 0.72, 0.45), metallic=1.0, rough=0.30)
    C.add_noise_bump(zinc, scale=500, strength=0.08, distance=0.0005, rough_var=0.06)
    black = plastic("Insulator", rough=0.4, color=0.03)
    pin = tin()
    objs = [body(paint)] + front_details(paint, steel) + back(paint, steel, zinc, black, pin)
    # stand the horn upright, front toward the camera, bracket on top
    C.transform_all(objs, R(math.radians(-15), 4, "Z") @ R(math.radians(80), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shoot("clacson", objs, "disc horn: black pressed-steel body with stamped front dome, zinc-plated mounting bracket, spade terminal",
          az=40, el=18, lens=70, fill=0.80)
