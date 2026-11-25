"""Windscreen washer pump (pompa lavavetri) as removed from the washer reservoir of a small
car: black glass-filled nylon cylindrical motor body with moulded ribs and a slide-in
locating rail, wider pump head with a single barbed outlet nozzle, inlet spigot in its
black rubber tank grommet, and a 2-pin connector socket with locking ramp on the motor
end."""
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


def body(black):
    out = []
    P = [(0.0, -0.02, 0), (0.12, -0.02, 0), (0.165, 0.0, 0), (0.168, 0.17, 0), (0.15, 0.19, 0), (0.142, 0.20, 0),
         (0.142, 0.70, 0), (0.13, 0.725, 0), (0.0, 0.73, 0)]
    out.append(lathe_at("Body", P, [black], Matrix(), steps=96, bevel=0.006))
    # longitudinal ribs and the locating rail (dovetail) on one side
    sp = []
    for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        if a == math.pi / 2:
            continue
        sp.append((0.03, 0.022, 0.46, (0.0, 0.0, 0.0), R(a, 4, "Z") @ T((0.145, 0, 0.45))))
    out.append(boxes("Ribs", sp, black, bevel=0.006))
    out.append(boxes("Rail", [(0.05, 0.09, 0.50, (0, 0, 0), R(math.pi / 2, 4, "Z") @ T((0.16, 0, 0.44))),
                              (0.03, 0.14, 0.50, (0, 0, 0), R(math.pi / 2, 4, "Z") @ T((0.195, 0, 0.44)))], black, bevel=0.008))
    # ring band around the seam between pump head and motor
    out.append(lathe_at("Band", [(0.14, 0.205, 0), (0.158, 0.205, 0), (0.158, 0.235, 0), (0.14, 0.235, 0)], [black], Matrix(),
                        steps=96, bevel=0.004))
    return out


def head(black, rubber):
    out = []
    # inlet spigot going into the tank, with its rubber grommet
    out.append(lathe_at("Spigot", [(0.0, -0.20, 0), (0.05, -0.20, 0), (0.058, -0.17, 0), (0.05, -0.15, 0), (0.05, -0.02, 0),
                                   (0.0, -0.02, 0)], [black], Matrix(), steps=48, bevel=0.003))
    out.append(lathe_at("Grommet", [(0.05, -0.15, 0), (0.105, -0.15, 0), (0.11, -0.13, 0), (0.085, -0.115, 0), (0.085, -0.085, 0),
                                    (0.115, -0.07, 0), (0.112, -0.045, 0), (0.05, -0.04, 0)], [rubber], Matrix(), steps=64))
    # outlet nozzle out of the pump head
    Mo = T((0.0, 0.0, 0.085)) @ R(math.radians(-90), 4, "Y") @ R(math.radians(8), 4, "X")
    Mo = T((0.0, 0.0, 0.085)) @ axis_mat((0, 0, 0), (-1, 0, 0.18))
    out.append(lathe_at("Nozzle", [(0.0, 0.10, 0), (0.042, 0.10, 0), (0.042, 0.24, 0), (0.05, 0.255, 0), (0.036, 0.29, 0),
                                   (0.034, 0.30, 0), (0.05, 0.315, 0), (0.033, 0.36, 0), (0.018, 0.37, 0), (0.0, 0.37, 0)],
                        [black], Mo, steps=48, bevel=0.002))
    out.append(lathe_at("NozzleHole", [(0.0, 0.371, 0), (0.016, 0.371, 0), (0.016, 0.372, 0), (0.0, 0.372, 0)],
                        [hole_mat()], Mo, steps=24))
    out.append(lathe_at("NozzleRoot", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.13, 0), (0.05, 0.16, 0), (0.0, 0.16, 0)], [black],
                        Mo, steps=48, bevel=0.004))
    return out


def plug_end(black, pin):
    Mc = T((0, 0, 0.71)) @ R(-math.pi / 2, 4, "Y")
    out = socket("Socket", Mc, 0.20, 0.11, 0.17, black, pin, cols=2, rows=1)
    out.append(boxes("SocketRoot", [(0.05, 0.22, 0.13, (0.0, 0, 0))], black, bevel=0.008, M=Mc))
    return out


def build():
    black = plastic("PA66GF", rough=0.48, color=0.028)
    rubber = C.mat_rubber("Grommet")
    pin = tin()
    objs = body(black) + head(black, rubber) + plug_end(black, pin)
    # lay the pump on its side, nozzle up, diagonal to the camera
    C.transform_all(objs, T((0, 0, 0.17)) @ R(math.radians(32), 4, "Z") @ R(math.radians(90), 4, "Y"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shoot("pompa-lavavetri", objs,
          "windscreen washer pump: black cylindrical plastic pump with outlet nozzle, inlet spigot with rubber grommet, "
          "2-pin connector socket",
          az=30, el=28, lens=70, fill=0.84)
