"""Front seat belt of a generic modern small hatchback, removed from the car and shown as
mounted: black grained-plastic retractor standing upright on its steel U-frame (foot bolt,
small blank label), dark grey woven polyester webbing (twill ribs, darker selvedges, real
thickness) rising straight out of the retractor guide to the upper anchor guide loop
(D-ring: satin steel plate with black-sleeved slot bar and shoulder bolt), passing over it
and hanging down in front in a twisting S-curve with the latch-plate tongue (black cover,
satin blade with latch window) riding on it, then lying on the floor to the lower anchor
plate with bolt on the sewn end loop (box-X stitching). No brand marks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import common as C

FAST = os.environ.get("FAST") == "1"


# ================================================================== interior materials
def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def fabric(name="SeatFabric", hexc="#2C2E31", period=0.0034):
    """Anthracite woven upholstery: plain-weave relief, heathered yarn colour, sheen."""
    base = C.srgb(hexc)
    m = C.principled(name, base, rough=0.88)
    b = bsdf(m)
    C._set(b, "Sheen Weight", 0.55)
    C._set(b, "Sheen Roughness", 0.38)
    C._set(b, "Sheen Tint", (0.75, 0.76, 0.80, 1))
    nt = m.node_tree
    co = C._coord(nt)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    k = math.tau / period
    s = [_math(nt, "SINE", _math(nt, "MULTIPLY", sep.outputs[i], k)) for i in range(3)]
    w = _math(nt, "ADD", _math(nt, "MULTIPLY", s[0], s[1]),
              _math(nt, "ADD", _math(nt, "MULTIPLY", s[1], s[2]), _math(nt, "MULTIPLY", s[2], s[0])))
    # heathered yarn: fine noise modulates colour
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 300.0
    nz.inputs["Detail"].default_value = 3.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = tuple(c * 0.72 for c in base[:3]) + (1,)
    mix.inputs["B"].default_value = tuple(c * 1.30 for c in base[:3]) + (1,)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    h = _math(nt, "ADD", _math(nt, "MULTIPLY", w, 0.6), _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.8))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def grained(name="GrainedPP", v=0.028, rough=0.58, scale=520.0):
    """Moulded interior plastic with a leather-like grain."""
    m = C.principled(name, (v, v, v * 1.06), rough=rough)
    nt = m.node_tree
    b = bsdf(m)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = scale
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 60.0
    h = _math(nt, "ADD", vo.outputs["Distance"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.3))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.07
    mr.inputs["To Max"].default_value = rough + 0.07
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def satin_silver(name="SatinSilver"):
    m = C.principled(name, (0.44, 0.445, 0.455), metallic=1.0, rough=0.36)
    C.add_noise_bump(m, scale=800, strength=0.04, distance=0.0003, rough_var=0.04)
    return m


def steel_dark(name="SeatSteel"):
    m = C.principled(name, (0.10, 0.10, 0.105), metallic=0.8, rough=0.48)
    C.add_noise_bump(m, scale=300, strength=0.12, distance=0.0008, rough_var=0.08)
    return m


def zinc(name="ZincRail"):
    m = C.principled(name, (0.50, 0.51, 0.53), metallic=1.0, rough=0.34)
    C.add_noise_bump(m, scale=250, strength=0.08, distance=0.0006, rough_var=0.08)
    return m


def thread(name="Thread"):
    m = C.principled(name, C.srgb("#4A4D52"), rough=0.75)
    C._set(bsdf(m), "Sheen Weight", 0.4)
    return m


# ================================================================== geometry helpers
def cage(n):
    """Closed quad lattice on the surface of the cube [-1, 1]^3 with n=(nx, ny, nz) cells."""
    nx, ny, nz = n
    bm = bmesh.new()
    V = {}

    def vt(i, j, k):
        key = (i, j, k)
        if key not in V:
            V[key] = bm.verts.new((2 * i / nx - 1, 2 * j / ny - 1, 2 * k / nz - 1))
        return V[key]

    for i in (0, nx):
        for j in range(ny):
            for k in range(nz):
                bm.faces.new((vt(i, j, k), vt(i, j + 1, k), vt(i, j + 1, k + 1), vt(i, j, k + 1)))
    for j in (0, ny):
        for i in range(nx):
            for k in range(nz):
                bm.faces.new((vt(i, j, k), vt(i + 1, j, k), vt(i + 1, j, k + 1), vt(i, j, k + 1)))
    for k in (0, nz):
        for i in range(nx):
            for j in range(ny):
                bm.faces.new((vt(i, j, k), vt(i + 1, j, k), vt(i + 1, j + 1, k), vt(i, j + 1, k)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def soft(name, mats, n, fn, levels=3, angle=70):
    """Subdivision-surface solid: lattice cage deformed by fn(u, v, w) -> Vector (world)."""
    bm = cage(n)
    for v in bm.verts:
        v.co = fn(v.co.x, v.co.y, v.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj(name, bm, mats)
    m = ob.modifiers.new("Sub", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    return C.finalize(ob, angle=angle)


def box_soft(name, mats, lo, hi, n=(3, 3, 3), levels=3, shape=None, M=None):
    lo, hi = Vector(lo), Vector(hi)

    def fn(u, v, w):
        p = Vector(((lo.x + hi.x) / 2 + (hi.x - lo.x) / 2 * u,
                    (lo.y + hi.y) / 2 + (hi.y - lo.y) / 2 * v,
                    (lo.z + hi.z) / 2 + (hi.z - lo.z) / 2 * w))
        if shape:
            p = shape(p, u, v, w)
        return (M @ p) if M is not None else p
    return soft(name, mats, n, fn, levels)


def rounded(corners, radii, closed=True, seg=10):
    P = [Vector(c) for c in corners]
    n = len(P)
    out = []
    for i in range(n):
        r = radii[i]
        if (not closed and (i == 0 or i == n - 1)) or r <= 0:
            out.append(P[i])
            continue
        a, c, b = P[i - 1], P[i], P[(i + 1) % n]
        da, db = (a - c), (b - c)
        ra = min(r, da.length * 0.49)
        rb = min(r, db.length * 0.49)
        p0 = c + da.normalized() * ra
        p2 = c + db.normalized() * rb
        for j in range(seg + 1):
            t = j / seg
            out.append(p0 * (1 - t) ** 2 + c * 2 * t * (1 - t) + p2 * t * t)
    return out


def tube(name, pts, r, mat, res=4):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def extrude_x(name, mats, poly_yz, x0, x1, bevel=0.004, segs=3):
    """Prism from a 2D outline in (y, z) between x0 and x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, p[0], p[1])) for p in poly_yz]
    b = [bm.verts.new((x1, p[0], p[1])) for p in poly_yz]
    n = len(a)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj(name, bm, mats)
    if bevel:
        C.add_bevel(ob, bevel, segments=segs, angle=30)
    return C.finalize(ob, angle=35)


def bvh(objs):
    verts, polys = [], []
    for o in objs:
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def stitches(tree, line, cast_dir, mat, name="Stitch", pitch=0.0055, dash=0.0036, w=0.0011, h=0.0006):
    """Row of thread dashes projected onto the surfaces in tree along the 3D polyline line
    (each point cast along cast_dir)."""
    D = Vector(cast_dir).normalized()
    # resample line by pitch
    L = [Vector(p) for p in line]
    acc = [0.0]
    for i in range(1, len(L)):
        acc.append(acc[-1] + (L[i] - L[i - 1]).length)
    bm = bmesh.new()
    s = pitch / 2
    k = 0
    while s < acc[-1] - pitch / 2:
        while acc[k + 1] < s:
            k += 1
        t = (s - acc[k]) / max(1e-9, acc[k + 1] - acc[k])
        P = L[k].lerp(L[k + 1], t)
        T = (L[k + 1] - L[k]).normalized()
        hit = tree.ray_cast(P - D * 0.3, D, 1.0)
        s += pitch
        if hit[0] is None:
            continue
        Hp, N = hit[0], hit[1].normalized()
        if N.dot(D) > 0:
            N = -N
        Tt = (T - N * T.dot(N)).normalized()
        B = N.cross(Tt)
        M = Matrix.Identity(4)
        for i, ax in enumerate((Tt, B, N)):
            M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
        M.translation = Hp + N * (h * 0.15)
        C.box_bm(bm, dash, w, h, matrix=M)
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, w * 0.45, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def sstep(a, b, x):
    return C.smoothstep(a, b, x)


# ================================================================== belt helpers
def bspline(ctrl, n=400):
    P = [Vector(c) for c in ctrl]
    seq = [P[0], P[0]] + P + [P[-1], P[-1]]
    segs = len(seq) - 3
    m = max(8, (n * 6) // segs)
    out = []
    for k in range(segs):
        p0, p1, p2, p3 = seq[k:k + 4]
        for j in range(m):
            t = j / m
            t2, t3 = t * t, t * t * t
            out.append(p0 * ((1 - t) ** 3 / 6) + p1 * ((3 * t3 - 6 * t2 + 4) / 6) +
                       p2 * ((-3 * t3 + 3 * t2 + 3 * t + 1) / 6) + p3 * (t3 / 6))
    out.append(P[-1])
    return resample(out, n)


def resample(P, n):
    acc = [0.0]
    for i in range(1, len(P)):
        acc.append(acc[-1] + (P[i] - P[i - 1]).length)
    tot = acc[-1]
    out, k = [], 0
    for j in range(n):
        s = tot * j / (n - 1)
        while k < len(acc) - 2 and acc[k + 1] < s:
            k += 1
        seg = acc[k + 1] - acc[k]
        t = 0.0 if seg < 1e-12 else (s - acc[k]) / seg
        out.append(P[k].lerp(P[k + 1], min(1.0, max(0.0, t))))
    return out


def belt_frames(pts, zbar):
    """(P, T, W, N) by parallel transport (W across the strap, N its normal). On the hanging
    leg the strap twists progressively so that it lies flat once it reaches the floor."""
    n = len(pts)
    Ts = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    Ws = []
    W = Vector((1, 0, 0))
    for T in Ts:
        W = (W - T * W.dot(T)).normalized()
        Ws.append(W)
    i_apex = max(range(n), key=lambda i: pts[i].z)
    i_td = next((i for i in range(i_apex, n) if pts[i].z <= H + 1e-5), n - 1)
    up = Vector((0, 0, 1))
    T = Ts[i_td]
    Wf = up.cross(T).normalized()
    if Wf.dot(Ws[i_td]) < 0:
        Wf = -Wf
    phi = math.atan2(T.dot(Ws[i_td].cross(Wf)), Ws[i_td].dot(Wf))
    phi += math.pi * (1 if phi < 0 else -1) * 0.0
    fr = []
    for i in range(n):
        t = 0.0 if i <= i_apex else min(1.0, (i - i_apex) / max(1, i_td - i_apex))
        t = t * t * (3 - 2 * t)
        R = Matrix.Rotation(phi * t, 3, Ts[i])
        Wi = (R @ Ws[i]).normalized()
        fr.append((pts[i], Ts[i], Wi, Ts[i].cross(Wi).normalized()))
    return fr


def strap(name, frames, mat, width=0.047, thick=0.0018, lift=0.0):
    """Woven webbing ribbon with UVs (u = length in m, v = across in m)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    sec = [(-width / 2, -thick / 2), (width / 2, -thick / 2), (width / 2 + 0.0004, 0.0),
           (width / 2, thick / 2), (-width / 2, thick / 2), (-width / 2 - 0.0004, 0.0)]
    rings, s, prev = [], 0.0, None
    us = []
    for (P, T, W, N) in frames:
        if prev is not None:
            s += (P - prev).length
        prev = P
        us.append(s)
        rings.append([bm.verts.new(P + W * a + N * (b + lift)) for (a, b) in sec])
    m = len(sec)
    for i in range(len(rings) - 1):
        for k in range(m):
            k2 = (k + 1) % m
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for l in f.loops:
                ii = i if l.vert in rings[i] else i + 1
                kk = rings[ii].index(l.vert)
                l[uvl].uv = (us[ii], sec[kk][0])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj(name, bm, [mat])
    return C.finalize(ob, angle=50)


def webbing_mat(name="Webbing"):
    """Dark grey polyester webbing: fine twill ribs along the strap, slight sheen."""
    m = C.principled(name, C.srgb("#3A3D42"), rough=0.6)
    b = bsdf(m)
    C._set(b, "Sheen Weight", 0.5)
    C._set(b, "Sheen Roughness", 0.3)
    nt = m.node_tree
    uv = C._coord(nt, "UV")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv, sep.inputs[0])
    # twill: diagonal ribs (u + 0.35 v) every ~1.1 mm, plus warp lines across
    d = _math(nt, "ADD", sep.outputs[0], _math(nt, "MULTIPLY", sep.outputs[1], 0.35))
    rib = _math(nt, "SINE", _math(nt, "MULTIPLY", d, math.tau / 0.0019))
    warp = _math(nt, "SINE", _math(nt, "MULTIPLY", sep.outputs[1], math.tau / 0.0013))
    h = _math(nt, "ADD", _math(nt, "MULTIPLY", rib, 0.7), _math(nt, "MULTIPLY", warp, 0.3))
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 90.0
    h = _math(nt, "ADD", h, _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.6))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.75
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # woven selvedge: slightly darker, tighter band along both edges + yarn shade variation
    edge = _math(nt, "GREATER_THAN", _math(nt, "ABSOLUTE", sep.outputs[1]), 0.0205)
    shade = _math(nt, "ADD", _math(nt, "MULTIPLY", rib, 0.08), 1.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(edge, mix.inputs["Factor"])
    base = C.srgb("#3A3D42")
    mix.inputs["A"].default_value = base
    mix.inputs["B"].default_value = tuple(c * 0.6 for c in base[:3]) + (1,)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(mix.outputs["Result"], mul.inputs["A"])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    for k in range(3):
        nt.links.new(shade, cmb.inputs[k])
    nt.links.new(cmb.outputs[0], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.5
    mr.inputs["To Max"].default_value = 0.7
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def plate_matrix(P, T, W, up=Vector((0, 0, 1))):
    M = Matrix.Identity(4)
    for i, ax in enumerate((W, T, up)):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = P
    return M


def extrude_z(name, mats, poly, z0, z1, M, holes=(), bevel=0.0008, segs=2, slots=()):
    """Flat plate from a 2D outline (a, b) with optional round holes (a, b, r), placed by M."""
    bm = bmesh.new()
    a = [bm.verts.new((p[0], p[1], z0)) for p in poly]
    b = [bm.verts.new((p[0], p[1], z1)) for p in poly]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    ob = C.mesh_obj(name, bm, mats)
    cut = None
    if holes or slots:
        cb = bmesh.new()
        for (ha, hb, r) in holes:
            C.cyl_bm(cb, r, z0 - 0.01, z1 + 0.01, seg=40, matrix=M @ Matrix.Translation((ha, hb, 0)))
        for (a0, a1, b0, b1) in slots:
            C.box_bm(cb, a1 - a0, b1 - b0, (z1 - z0) + 0.02, center=((a0 + a1) / 2, (b0 + b1) / 2, (z0 + z1) / 2), matrix=M)
        cut = C.mesh_obj(name + "Cut", cb, mats)
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=segs, angle=30)
    return C.finalize(ob, angle=35, remove=[cut] if cut else [])


def hexbolt(name, mat, r=0.0065, h=0.005, M=Matrix.Identity(4), washer=0.011):
    out = []
    w = C.lathe(name + "W", [(0.0, 0.0, 0), (washer, 0.0, 0), (washer, 0.0015, 0), (0.0, 0.0015, 0)], [mat], steps=48)
    w.matrix_world = M
    out.append(C.finalize(w, angle=30))
    hb = C.lathe(name, [(0.0, 0.0015, 0), (r, 0.0015, 0), (r, 0.0015 + h, 0), (r * 0.9, 0.002 + h, 0),
                        (0.0, 0.002 + h, 0)], [mat], steps=6)
    hb.matrix_world = M
    out.append(C.finalize(hb, angle=20))
    return out


# ================================================================== belt parts
H = 0.00065           # webbing centre height when lying on the floor


ZB = 0.46              # D-ring slot bar height
CAM = Vector((math.sin(math.radians(-30)) * math.cos(math.radians(14)),
              -math.cos(math.radians(-30)) * math.cos(math.radians(14)), math.sin(math.radians(14))))


def belt_path():
    zb = ZB
    ctrl = [(0.0, 0.0, 0.090), (0.0, 0.003, 0.125), (0.0, 0.0075, 0.17), (0.0, 0.0075, 0.30), (0.0, 0.0075, zb - 0.04),
            (0.0, 0.0075, zb - 0.005), (0.0, 0.004, zb + 0.008), (0.0, -0.004, zb + 0.008), (0.0, -0.0075, zb - 0.005),
            (0.0, -0.010, zb - 0.05), (0.012, -0.020, 0.36), (0.050, -0.040, 0.29), (0.085, -0.060, 0.22),
            (0.095, -0.075, 0.15), (0.075, -0.095, 0.085), (0.055, -0.125, 0.030), (0.050, -0.160, H),
            (0.060, -0.210, H), (0.040, -0.265, H), (-0.010, -0.300, H), (-0.060, -0.315, H)]
    pts = bspline(ctrl, 700)
    return [Vector((p.x, p.y, max(p.z, H))) for p in pts]


def frame_at(fr, s):
    """Frame at arc-length fraction s."""
    i = max(1, min(len(fr) - 2, int(s * (len(fr) - 1))))
    return fr[i]


def retractor(plastic, steel, zincm, lab_m):
    out = []

    def shape(p, u, v, w):
        return p
    out.append(box_soft("RetractorBody", [plastic], (-0.036, -0.030, 0.004), (0.036, 0.030, 0.112), n=(4, 4, 6),
                        levels=2, shape=shape))
    # spool covers (round) on both sides, bigger locking-mechanism cover on +X
    for sx, r, d in ((1, 0.031, 0.006), (-1, 0.035, 0.014)):
        cap = C.lathe("SpoolCap", [(0.0, 0.0, 0), (r, 0.0, 0), (r, d * 0.6, 0), (r - 0.004, d, 0), (0.0, d, 0)],
                      [plastic], steps=64)
        cap.matrix_world = Matrix.Translation((sx * 0.040, 0.0, 0.046)) @ Matrix.Rotation(math.radians(90 * sx), 4, "Y")
        out.append(C.finalize(cap, angle=40))
    # steel U-frame: side cheeks + back plate + foot
    poly = rounded([(-0.032, 0.004), (0.036, 0.004), (0.036, 0.096), (-0.010, 0.096), (-0.032, 0.070)],
                   [0, 0, 0.008, 0.01, 0.01], closed=True, seg=6)
    for sx in (-1, 1):
        out.append(extrude_x("Cheek", [steel], [(p.x, p.y) for p in poly], sx * 0.0365 - 0.0015 + (0.0 if sx > 0 else 0),
                             sx * 0.0365 + 0.0015, bevel=0.0006, segs=2))
    bm = bmesh.new()
    C.box_bm(bm, 0.080, 0.003, 0.100, center=(0, 0.0365, 0.054))
    C.box_bm(bm, 0.060, 0.050, 0.003, center=(0, 0.0605, 0.0015))
    bp = C.mesh_obj("BackPlate", bm, [steel])
    C.add_bevel(bp, 0.0012, segments=2, angle=30)
    out.append(C.finalize(bp, angle=35))
    out += hexbolt("FootBolt", zincm, r=0.0075, M=Matrix.Translation((0, 0.066, 0.003)))
    # webbing guide at the top
    bm = bmesh.new()
    C.box_bm(bm, 0.062, 0.018, 0.012, center=(0, 0.0, 0.114))
    gd = C.mesh_obj("Guide", bm, [plastic])
    gd.modifiers.new("Sub", "SUBSURF").levels = 2
    gd.modifiers["Sub"].render_levels = 2
    out.append(C.finalize(gd, angle=50))
    # small blank label on the front face
    im = C.label_image("RetLabel", 768, 512, seed=5, lines=4)
    out.append(C.label_plane("Label", lab_m(im), 0.032, 0.022,
                             Matrix.Translation((0.0, -0.0305, 0.070))))
    return out


def d_ring(plastic, silver, zincm):
    """Upper anchor guide: satin plate standing in the XZ plane, the webbing passing through
    its slot over the black-covered lower bar; shoulder bolt facing the camera."""
    M = Matrix.Identity(4)
    for i, ax in enumerate((Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0)))):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = Vector((0, 0, ZB))
    out = []
    poly = rounded([(-0.036, -0.012), (0.036, -0.012), (0.030, 0.030), (0.0, 0.068), (-0.030, 0.030)],
                   [0.008, 0.008, 0.02, 0.018, 0.02], closed=True, seg=8)
    out.append(extrude_z("DRingPlate", [silver], [(p.x, p.y) for p in poly], -0.0016, 0.0016, M,
                         holes=[(0.0, 0.045, 0.0068)], slots=[(-0.027, 0.027, 0.0005, 0.0135)]))
    # black plastic sleeve over the lower bar
    out.append(box_soft("DRingCover", [plastic], (-0.036, -0.0155, -0.0062), (0.036, 0.0005, 0.0062), n=(4, 2, 2),
                        levels=2, M=M))
    Mb = Matrix.Translation((0, -0.0016, ZB + 0.045)) @ Matrix.Rotation(math.radians(90), 4, "X")
    out += hexbolt("DRingBolt", zincm, r=0.0085, h=0.006, washer=0.0125, M=Mb)
    # spacer sleeve behind the plate
    sp = C.lathe("DRingSpacer", [(0.0, 0.0, 0), (0.010, 0.0, 0), (0.010, 0.010, 0), (0.0, 0.010, 0)], [zincm], steps=32)
    sp.matrix_world = Matrix.Translation((0, 0.0016, ZB + 0.045)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.finalize(sp, angle=40))
    return out


def tongue(fr, plastic, silver):
    """Latch plate riding on the hanging webbing, blade pointing down, facing the camera."""
    i = min(range(len(fr)), key=lambda k: abs(fr[k][0].z - 0.20) + (9 if fr[k][1].z > 0 else 0))
    P, T, W, N = fr[i]
    Nc = N if N.dot(CAM) > 0 else -N
    Wc = T.cross(Nc).normalized()
    M = Matrix.Identity(4)
    for k, ax in enumerate((Wc, T, Nc)):
        M[0][k], M[1][k], M[2][k] = ax.x, ax.y, ax.z
    M.translation = P
    out = []
    out.append(box_soft("TongueHead", [plastic], (-0.031, -0.016, -0.0045), (0.031, 0.020, 0.0105), n=(4, 3, 2),
                        levels=2, M=M))
    poly = rounded([(-0.0115, 0.012), (0.0115, 0.012), (0.0115, 0.068), (0.004, 0.074), (-0.004, 0.074),
                    (-0.0115, 0.068)], [0, 0, 0.003, 0.002, 0.002, 0.003], closed=True, seg=4)
    out.append(extrude_z("TongueBlade", [silver], [(p.x, p.y) for p in poly], 0.0024, 0.0054, M,
                         slots=[(-0.0055, 0.0055, 0.048, 0.060)]))
    return out


def end_anchor(fr, steel, zincm, web, thr):
    up = Vector((0, 0, 1))
    P, T, W, N = fr[-1]
    Wc = T.cross(up).normalized()
    M = plate_matrix(P, T, Wc)
    out = []
    poly = rounded([(-0.030, -0.006), (0.030, -0.006), (0.024, 0.030), (0.0, 0.052), (-0.024, 0.030)],
                   [0.006, 0.006, 0.012, 0.012, 0.012], closed=True, seg=8)
    out.append(extrude_z("AnchorPlate", [steel], [(p.x, p.y) for p in poly], -0.0006, 0.0024, M,
                         holes=[(0.0, 0.032, 0.007)]))
    out += hexbolt("AnchorBolt", zincm, r=0.009, h=0.007, washer=0.014, M=M @ Matrix.Translation((0, 0.032, 0.0024)))
    # sewn return loop: webbing folded back on itself for 75 mm, box-X stitching
    n = len(fr)
    s, k = 0.0, n - 1
    while k > 0 and s < 0.075:
        s += (fr[k][0] - fr[k - 1][0]).length
        k -= 1
    loop = [(q[0], q[1], q[1].cross(up).normalized(), up) for q in fr[k:]]
    out.append(strap("WebbingFold", loop, web, lift=0.0018))
    a, b0, b1 = 0.017, -0.062, -0.022

    def Lp(x, y):
        return M @ Vector((x, y, 0.02))
    rect = [(-a, b0), (a, b0), (a, b1), (-a, b1), (-a, b0), (a, b1), (-a, b1), (a, b0)]
    tree = bvh([o for o in out if o.name.startswith("WebbingFold")])
    for i in range(len(rect) - 1):
        out.append(stitches(tree, [Lp(*rect[i]), Lp(*rect[i + 1])], (0, 0, -1), thr, pitch=0.0032, dash=0.0024,
                            w=0.0010, h=0.0006))
    return out


def build():
    plastic = grained("BeltABS", v=0.024, rough=0.5, scale=900.0)
    silver = satin_silver()
    steel = steel_dark("BeltSteel")
    zincm = C.principled("Zinc", (0.62, 0.62, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(zincm, scale=600, strength=0.05, distance=0.0003, rough_var=0.06)
    web = webbing_mat()
    thr = C.principled("BeltThread", C.srgb("#5A5D62"), rough=0.6)
    pts = belt_path()
    fr = belt_frames(pts, ZB)
    objs = [strap("Webbing", fr, web)]
    objs += retractor(plastic, steel, zincm, C.mat_label)
    objs += d_ring(plastic, silver, zincm)
    objs += tongue(fr, plastic, silver)
    objs += end_anchor(fr, steel, zincm, web, thr)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("cintura", objs, "cintura.py",
            "car seat belt: black retractor unit with steel frame, dark grey woven webbing, upper anchor guide "
            "loop (D-ring), latch plate tongue and lower anchor plate with bolt",
            az=-30, el=14, lens=70, fill=0.86,
            res=(512, 512) if FAST else (1024, 1024),
            samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))
