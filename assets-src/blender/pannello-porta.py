"""Front door interior trim panel (door card) of a generic modern small hatchback, as
removed from the left front door, seen from the cabin side. Dark grey grained plastic
carrier, black grained window-sill roll along the top, anthracite woven fabric insert with
top-stitched edges, black padded armrest with the window switch pack (two rockers on a
piano-black plate in a satin-silver bezel), black grab handle rising from the armrest,
interior opening-handle recess with satin lever near the front, round speaker grille
(hexagonal hole pattern) low at the front, and a door pocket along the bottom.
Cabin side is -Y, car front (hinge side) is +X."""
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
    m = C.principled(name, (0.55, 0.555, 0.565), metallic=1.0, rough=0.3)
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


# ================================================================== door card geometry
# Panel in the XZ plane, cabin side towards -Y, car front (hinge side) at +X.
def top_z(x):
    return 0.600 - 0.022 * sstep(0.30, 0.47, x)


def outline():
    return rounded([(-0.470, 0.030), (0.395, 0.030), (0.470, 0.150), (0.485, 0.470), (0.470, top_z(0.47)),
                    (-0.470, 0.600)], [0.03, 0.05, 0.10, 0.04, 0.02, 0.02], closed=True, seg=12)


def carrier(grey, black):
    poly = [(p.x, p.y) for p in outline()]
    bm = bmesh.new()
    a = [bm.verts.new((p[0], 0.0, p[1])) for p in poly]
    b = [bm.verts.new((p[0], 0.028, p[1])) for p in poly]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj("Carrier", bm, [grey])
    # recess behind the inner handle
    cb = bmesh.new()
    C.box_bm(cb, 0.098, 0.03, 0.058, center=(0.376, -0.003, 0.436))
    cut = C.mesh_obj("HandleRecess", cb, [black])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.007, segments=3, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def sill_roll(black):
    def shape(p, u, v, w):
        t = sstep(0.25, 0.47, p.x)
        p.z = 0.495 + (p.z - 0.495) * ((top_z(p.x) + 0.004 - 0.495) / (0.604 - 0.495))
        if v < 0:
            p.y = p.y * (1 - 0.45 * t) * (1 - 0.6 * sstep(-0.40, -0.47, p.x))
        if w > 0 and v < 0:
            p.y += 0.012
        return p
    return box_soft("SillRoll", [black], (-0.468, -0.058, 0.495), (0.472, 0.022, 0.604), n=(12, 3, 3), shape=shape)


def fabric_insert(fab):
    def shape(p, u, v, w):
        t = sstep(0.12, 0.30, p.x)
        p.z = 0.41 + (p.z - 0.41) * (1 - 0.25 * t)
        if v < 0:
            p.y -= 0.004 * (1 - u * u) * (1 - w * w)
        return p
    return box_soft("FabricInsert", [fab], (-0.415, -0.020, 0.325), (0.300, 0.004, 0.497), n=(10, 2, 4), shape=shape)


def armrest(black):
    def shape(p, u, v, w):
        tr = sstep(-0.20, -0.37, p.x)       # rear end fades into the panel
        if v < 0:
            p.y *= (1 - 0.75 * tr)
        if w < 0:
            p.z += 0.03 * tr                 # rear underside sweeps up
        if w > 0:
            p.z += 0.006 * sstep(-0.1, 0.12, p.x)
        return p
    return box_soft("Armrest", [black], (-0.385, -0.098, 0.250), (0.175, 0.004, 0.318), n=(10, 4, 3), shape=shape)


def switch_pack(black, gloss, silver):
    out = []
    zt = 0.3285
    bm = bmesh.new()
    C.box_bm(bm, 0.118, 0.062, 0.008, center=(0.085, -0.050, zt - 0.003))
    sv = C.mesh_obj("SwitchBezel", bm, [silver])
    C.add_bevel(sv, 0.003, segments=3, angle=30)
    out.append(C.finalize(sv, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.106, 0.050, 0.008, center=(0.085, -0.050, zt - 0.0015))
    pl = C.mesh_obj("SwitchPlate", bm, [gloss])
    C.add_bevel(pl, 0.002, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    for x in (0.058, 0.112):
        bm = bmesh.new()
        M = Matrix.Translation((x, -0.050, zt + 0.006)) @ Matrix.Rotation(math.radians(-10), 4, "X")
        C.box_bm(bm, 0.030, 0.036, 0.010, matrix=M)
        sw = C.mesh_obj("Rocker", bm, [black])
        sw.modifiers.new("Sub", "SUBSURF").levels = 2
        sw.modifiers["Sub"].render_levels = 2
        out.append(C.finalize(sw, angle=50))
    return out


def pull_handle(black):
    pts = rounded([(0.150, -0.072, 0.300), (0.225, -0.080, 0.370), (0.300, -0.070, 0.470), (0.322, -0.045, 0.505)],
                  [0, 0.06, 0.05, 0], closed=False, seg=12)
    out = [tube("PullHandle", pts, 0.0145, black, res=5)]
    return out


def inner_handle(black, silver):
    out = []
    lever_m = C.principled("LeverSatin", (0.26, 0.265, 0.275), metallic=1.0, rough=0.5)
    # bezel around the recess
    poly = rounded([(0.322, 0.402), (0.430, 0.402), (0.430, 0.470), (0.322, 0.470)], [0.018] * 4, closed=True, seg=8)
    inner = rounded([(0.330, 0.410), (0.422, 0.410), (0.422, 0.462), (0.330, 0.462)], [0.014] * 4, closed=True, seg=8)
    bm = bmesh.new()
    o0 = [bm.verts.new((p.x, -0.010, p.y)) for p in poly]
    o1 = [bm.verts.new((p.x, 0.004, p.y)) for p in poly]
    i0 = [bm.verts.new((p.x, -0.010, p.y)) for p in inner]
    i1 = [bm.verts.new((p.x, 0.004, p.y)) for p in inner]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))
        bm.faces.new((o0[k2], o0[k], i0[k], i0[k2]))
        bm.faces.new((o1[k], o1[k2], i1[k2], i1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bz = C.mesh_obj("HandleBezel", bm, [black])
    C.add_bevel(bz, 0.0025, segments=3, angle=30)
    out.append(C.finalize(bz, angle=35))
    # dark recess floor
    bm = bmesh.new()
    C.box_bm(bm, 0.096, 0.004, 0.054, center=(0.376, 0.014, 0.436))
    fl = C.mesh_obj("RecessFloor", bm, [black])
    out.append(C.finalize(fl, angle=30))
    # satin lever with a finger lip at the rear end
    def shape(p, u, v, w):
        if u < -0.3 and v < 0:
            p.y -= 0.006 * sstep(-0.3, -1.0, u)
        return p
    out.append(box_soft("Lever", [lever_m], (0.336, -0.006, 0.426), (0.414, 0.012, 0.447), n=(5, 2, 2), levels=2,
                        shape=shape))
    return out


def speaker(black, grille_m, silver):
    out = []
    cx, cz, R = 0.255, 0.150, 0.088
    M = Matrix.Translation((cx, 0.0, cz)) @ Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> -Y
    ring = C.lathe("SpeakerRing", [(R - 0.016, -0.002, 0), (R + 0.004, -0.002, 0), (R + 0.006, 0.006, 0),
                                   (R - 0.002, 0.013, 0), (R - 0.012, 0.011, 0), (R - 0.016, 0.004, 0)],
                   [black], steps=128)
    ring.matrix_world = M
    out.append(C.finalize(ring, angle=40))
    prof = [(0.0, 0.0105, 0)]
    for i in range(1, 13):
        r = (R - 0.012) * i / 12
        prof.append((r, 0.0105 - 0.004 * (r / (R - 0.012)) ** 2, 0))
    prof.append((R - 0.012, 0.0, 0))
    prof.append((0.0, 0.0, 0))
    g = C.lathe("SpeakerGrille", prof, [grille_m], steps=128)
    g.matrix_world = M
    out.append(C.finalize(g, angle=40))
    return out


def grille_mat(name="SpeakerGrille"):
    """Black plastic grille with a hexagonal pattern of round holes (shader)."""
    m = grained(name, v=0.03, rough=0.5, scale=900.0)
    nt = m.node_tree
    b = bsdf(m)
    co = C._coord(nt)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    pitch = 0.0085
    # two offset square lattices = hex-ish pattern
    def holes(ox, oz):
        fx = _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "ADD", _math(nt, "MULTIPLY", sep.outputs[0], 1 / pitch), ox)), 0.5)
        fz = _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "ADD", _math(nt, "MULTIPLY", sep.outputs[1], 1 / (pitch * 1.732)), oz)), 0.5)
        d2 = _math(nt, "ADD", _math(nt, "MULTIPLY", fx, fx), _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", fz, 1.732), _math(nt, "MULTIPLY", fz, 1.732)))
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.05
        mr.inputs["From Max"].default_value = 0.11
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(d2, mr.inputs["Value"])
        return mr.outputs["Result"]
    mask = _math(nt, "MAXIMUM", holes(0.0, 0.0), holes(0.5, 0.5))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mask, mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.03, 0.03, 0.032, 1)
    mix.inputs["B"].default_value = (0.002, 0.002, 0.002, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.0008
    bump.invert = True
    nt.links.new(mask, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def door_pocket(black):
    def shape(p, u, v, w):
        if v < 0:
            p.y *= 1 - 0.3 * sstep(0.02, 0.12, p.x) - 0.3 * sstep(-0.34, -0.425, p.x)
            if w > 0:
                p.y += 0.006
        return p
    ob_parts = []
    ob = box_soft("PocketLip", [black], (-0.425, -0.062, 0.040), (0.120, 0.004, 0.178), n=(10, 3, 4), shape=shape)
    cb = bmesh.new()
    C.box_bm(cb, 0.43, 0.034, 0.20, center=(-0.152, -0.024, 0.178))
    cut = C.mesh_obj("PocketCut", cb, [black])
    C.add_boolean(ob, cut)
    return C.finalize(ob, angle=50, remove=[cut])


def stitching_insert(fab_obj, thr):
    tree = bvh([fab_obj])
    out = []
    fwd = (0, 1, 0)
    for z in (0.341, 0.481):
        out.append(stitches(tree, [(-0.395, -0.3, z), (0.24, -0.3, z)], fwd, thr))
    return out


def build():
    fab = fabric("DoorFabric")
    grey = grained("DoorCarrier", v=0.040, rough=0.6)
    black = grained("DoorBlack", v=0.024, rough=0.52)
    gloss = C.principled("PianoBlack", (0.01, 0.01, 0.011), rough=0.12)
    silver = satin_silver()
    thr = thread()
    ins = fabric_insert(fab)
    objs = [carrier(grey, black), sill_roll(black), ins, armrest(black)]
    objs += switch_pack(black, gloss, silver)
    objs += pull_handle(black)
    objs += inner_handle(black, silver)
    objs += speaker(black, grille_mat(), silver)
    objs.append(door_pocket(black))
    objs += stitching_insert(ins, thr)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("pannello-porta", objs, "pannello-porta.py",
            "front door interior trim panel: grained black and grey plastic with anthracite fabric insert, armrest "
            "with window switch panel, pull handle, interior handle recess with satin lever, speaker grille, door pocket",
            az=20, el=14, lens=70, fill=0.88,
            res=(512, 512) if FAST else (1024, 1024),
            samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))
