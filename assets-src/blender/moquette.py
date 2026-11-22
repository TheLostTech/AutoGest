"""Front floor carpet (moquette pavimento) of a generic modern small hatchback, as removed
from the car: one-piece moulded dark-grey needle-felt carpet with a thick black felt
backing, formed over the transmission tunnel down the middle, rising up the toe boards
towards the firewall, turned up slightly along the sills and humped over the seat cross
member at the rear. Cut-outs for the gear lever and the handbrake on the tunnel and round
holes for the seat-rail bolts; a black ribbed heel pad in the driver's footwell. Cut edges
show the felt backing. Car front is -Y, driver on -X."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import common as C

FAST = os.environ.get("FAST") == "1"


# ================================================================== interior materials (as sedile.py)
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



# ================================================================== extra helpers
def axes(origin, X, Y, Z):
    """4x4 matrix with the given (column) axes and origin."""
    M = Matrix.Identity(4)
    for i, ax in enumerate((Vector(X), Vector(Y), Vector(Z))):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = Vector(origin)
    return M


def prism_z(name, mats, poly, z0, z1, bevel=0.003, segs=3, angle=35, M=None, sub=0):
    """Prism from a 2D outline in (x, y) between z0 and z1 (optionally placed by M)."""
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
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    ob = C.mesh_obj(name, bm, mats)
    if bevel:
        C.add_bevel(ob, bevel, segments=segs, angle=30)
    if sub:
        m = ob.modifiers.new("Sub", "SUBSURF")
        m.levels = m.render_levels = sub
    return ob if angle is None else C.finalize(ob, angle=angle)


def rrect(cx, cy, w, h, r, seg=8):
    return [(p.x, p.y) for p in rounded([(cx - w / 2, cy - h / 2, 0), (cx + w / 2, cy - h / 2, 0),
                                         (cx + w / 2, cy + h / 2, 0), (cx - w / 2, cy + h / 2, 0)],
                                        [r] * 4, closed=True, seg=seg)]


def grid_bm(fn, nu, nv, mat=0, bm=None):
    """Open quad grid: fn(s, t) -> Vector with s, t in 0..1."""
    bm = bm or bmesh.new()
    rows = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            f.material_index = mat
    return bm


def shell(name, mats, fn, nu, nv, thick, offset=-1.0, mat_off=0, rim_off=0, angle=40, bevel=0.0, flip=False,
          finalize=True):
    bm = grid_bm(fn, nu, nv)
    if flip:
        for f in bm.faces:
            f.normal_flip()
    ob = C.mesh_obj(name, bm, mats)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = thick
    so.offset = offset
    so.use_even_offset = True
    so.material_offset = mat_off
    so.material_offset_rim = rim_off
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=50)
    return C.finalize(ob, angle=angle) if finalize else ob


def cut(ob, cutters, solver="EXACT", angle=35, bevel=0.0, bevel_seg=2):
    """One boolean difference per cutter (robust against overlapping cutters)."""
    for c in cutters:
        m = ob.modifiers.new("Bool", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.object = c
        m.solver = solver
        if solver == "EXACT":
            m.use_self = True
            m.use_hole_tolerant = True
        try:
            m.material_mode = "TRANSFER"
        except Exception:
            pass
        c.hide_render = True
        c.hide_viewport = True
    if bevel:
        C.add_bevel(ob, bevel, segments=bevel_seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter_obj(name, mat, build):
    bm = bmesh.new()
    build(bm)
    return C.mesh_obj(name, bm, [mat])


def cavity_mat(name="Cavity", v=0.006):
    return C.principled(name, (v, v, v), rough=0.85)


def hide_floor_from_glossy():
    """The white shadow catcher must not show up in glossy reflections of dark plastics."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


def render_args():
    return dict(res=(512, 512) if FAST else (1024, 1024),
                samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))


def ring_tube(name, pts, r, mat, res=4, cyclic=True):
    """Bevelled curve along pts (closed loop by default)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = not cyclic
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    sp.use_cyclic_u = cyclic
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def path_frames(pts, up=(0, 0, 1)):
    """Parallel-transport-ish frames (P, side, normal) along a polyline."""
    P = [Vector(p) for p in pts]
    out = []
    upv = Vector(up)
    for i in range(len(P)):
        T = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        S = T.cross(upv)
        if S.length < 1e-6:
            S = T.orthogonal()
        S.normalize()
        N = S.cross(T).normalized()
        out.append((P[i], S, N))
    return out


def superellipse(a, b, n=4.0, k=48, ox=0.0, oy=0.0):
    out = []
    for i in range(k):
        t = math.tau * i / k
        c, s = math.cos(t), math.sin(t)
        out.append((ox + a * math.copysign(abs(c) ** (2 / n), c), oy + b * math.copysign(abs(s) ** (2 / n), s)))
    return out


def rring(name, mat, outer, inner, z0, z1, bevel=0.0012, M=None, angle=35):
    """Flat frame between two closed outlines (same vertex count) in XY, from z0 to z1."""
    bm = bmesh.new()
    o0 = [bm.verts.new((p[0], p[1], z0)) for p in outer]
    o1 = [bm.verts.new((p[0], p[1], z1)) for p in outer]
    i0 = [bm.verts.new((p[0], p[1], z0)) for p in inner]
    i1 = [bm.verts.new((p[0], p[1], z1)) for p in inner]
    n = len(outer)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))
        bm.faces.new((o0[k2], o0[k], i0[k], i0[k2]))
        bm.faces.new((o1[k], o1[k2], i1[k2], i1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def loft(name, mats, sections, cap=True):
    """Skin closed sections [[Vector, ...], ...] (equal vertex counts) into a solid."""
    bm = bmesh.new()
    rings = [[bm.verts.new(p) for p in sec] for sec in sections]
    n = len(rings[0])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.mesh_obj(name, bm, mats)


def ribbed_rubber(name="RubberMat", pitch=0.004, axis=0, strength=0.5):
    """Black rubber with fine parallel ribs (shader relief)."""
    m = C.principled(name, (0.020, 0.020, 0.021), rough=0.72)
    nt = m.node_tree
    b = bsdf(m)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt), sep.inputs[0])
    s = _math(nt, "SINE", _math(nt, "MULTIPLY", sep.outputs[axis], math.tau / pitch))
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 500.0
    h = _math(nt, "ADD", s, _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.4))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0006
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def soften_heather(m, lo=0.9, hi=1.1):
    """Lower the yarn-colour contrast of a fabric() material (for light-grey fabrics)."""
    b = bsdf(m)
    base = None
    for n in m.node_tree.nodes:
        if n.type == "MIX" and getattr(n, "data_type", "") == "RGBA":
            a = n.inputs["A"].default_value
            base = [a[i] / 0.72 for i in range(3)]
            n.inputs["A"].default_value = tuple(c * lo for c in base) + (1,)
            n.inputs["B"].default_value = tuple(c * hi for c in base) + (1,)
    return m


# ================================================================== carpet geometry
XW = 0.70
YF, YR = -0.56, 0.66


def height(x, y):
    ax = abs(x)
    # transmission tunnel down the middle, taller at the front
    ht = 0.215 - 0.060 * sstep(-0.35, 0.60, y)
    f = sstep(0.215, 0.105, ax)
    z = ht * (f ** 0.85)
    # toe boards rising to the firewall
    z += 0.36 * sstep(-0.16, -0.56, y) ** 1.25 * (1 - 0.35 * f)
    # sills
    z += 0.055 * sstep(0.60, 0.70, ax)
    # seat cross member hump at the rear
    z += 0.045 * sstep(0.24, 0.34, y) * (1 - f) * sstep(0.62, 0.55, ax)
    # a removed carpet is never perfectly crisp: soft sags and shallow creases
    z += 0.004 * math.sin(9.0 * x + 2.0) * math.sin(7.0 * y + 1.0)
    z += 0.0025 * math.sin(23.0 * x + 13.0 * y) * sstep(0.30, 0.65, ax)
    z -= 0.010 * sstep(0.55, 0.70, ax) * sstep(-0.1, -0.5, y) * (1 - sstep(-0.16, -0.56, y))
    return z


def surf(s, t):
    u = 2 * s - 1
    y = YF + (YR - YF) * t
    # front edge follows the firewall curve, corners trimmed
    y += 0.05 * u * u * (1 - t) ** 3
    x = u * XW * (1 - 0.06 * sstep(0.15, 0.0, t) * abs(u) ** 4)
    return Vector((x, y, height(x, y)))


def cutters(felt):
    cs = []
    cs.append(prism_z("GearHole", [felt], rrect(0.0, -0.155, 0.105, 0.135, 0.025, seg=8), -0.5, 1.0, bevel=0, angle=None))
    cs.append(prism_z("BrakeHole", [felt], rrect(0.0, 0.140, 0.050, 0.200, 0.020, seg=8), -0.5, 1.0, bevel=0, angle=None))
    for sx in (-1, 1):
        for x in (0.175, 0.545):
            for y in (-0.050, 0.505):
                cs.append(cutter_obj("BoltHole", felt, lambda bm, x=x, y=y: C.cyl_bm(
                    bm, 0.013, -0.5, 1.0, seg=24, matrix=Matrix.Translation((sx * x, y, 0)))))
    return cs


def carpet_mat(name="Carpet", hexc="#1F2023"):
    """Needle-felt automotive carpet. At catalogue scale (about 1.5 mm per pixel) the
    fibres themselves are invisible, so it is the speckle of light and dark fibre
    tufts (a few mm), a soft tufted relief, a velvety sheen at grazing angles and no
    specular gloss at all that make it read as carpet rather than moulded plastic."""
    base = C.srgb(hexc)
    m = C.principled(name, base, rough=1.0)
    b = bsdf(m)
    C._set(b, "Specular IOR Level", 0.18)
    C._set(b, "Sheen Weight", 0.7)
    C._set(b, "Sheen Roughness", 0.30)
    C._set(b, "Sheen Tint", (0.42, 0.43, 0.45, 1))
    nt = m.node_tree
    co = C._coord(nt)
    # fibre tufts: random grey per Voronoi cell (2-3 mm), two scales, distorted by noise
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 160.0
    dn.inputs["Detail"].default_value = 2.0
    dv = nt.nodes.new("ShaderNodeMix")
    dv.data_type = "VECTOR"
    dv.inputs["Factor"].default_value = 0.004
    nt.links.new(co, dv.inputs["A"])
    nt.links.new(dn.outputs["Color"], dv.inputs["B"])
    v1 = nt.nodes.new("ShaderNodeTexVoronoi")
    v1.inputs["Scale"].default_value = 260.0
    v1.inputs["Randomness"].default_value = 1.0
    nt.links.new(dv.outputs["Result"], v1.inputs["Vector"])
    v2 = nt.nodes.new("ShaderNodeTexVoronoi")
    v2.inputs["Scale"].default_value = 700.0
    nt.links.new(co, v2.inputs["Vector"])
    # cell colour -> grey value (luminance-ish: just take red)
    s1 = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(v1.outputs["Color"], s1.inputs[0])
    s2 = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(v2.outputs["Color"], s2.inputs[0])
    big = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, big.inputs["Vector"])
    big.inputs["Scale"].default_value = 7.0
    big.inputs["Detail"].default_value = 3.0
    fleck = _math(nt, "ADD", _math(nt, "MULTIPLY", s1.outputs[0], 0.62), _math(nt, "MULTIPLY", s2.outputs[0], 0.38))
    cr = nt.nodes.new("ShaderNodeValToRGB")
    ramp = cr.color_ramp
    ramp.elements[0].position = 0.15
    ramp.elements[0].color = tuple(c * 0.35 for c in base[:3]) + (1,)
    ramp.elements[1].position = 0.88
    ramp.elements[1].color = tuple(min(1.0, c * 2.9) for c in base[:3]) + (1,)
    e = ramp.elements.new(0.55)
    e.color = tuple(c * 1.0 for c in base[:3]) + (1,)
    nt.links.new(fleck, cr.inputs["Fac"])
    # faint large-scale shading (pile direction / wear)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.82
    mr.inputs["To Max"].default_value = 1.12
    nt.links.new(big.outputs["Fac"], mr.inputs["Value"])
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(cr.outputs["Color"], mix.inputs["A"])
    cm = nt.nodes.new("ShaderNodeCombineColor")
    for k in range(3):
        nt.links.new(mr.outputs["Result"], cm.inputs[k])
    nt.links.new(cm.outputs[0], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    # tufted relief: Voronoi distance (soft bumps per tuft) + fine fibre noise
    fn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, fn.inputs["Vector"])
    fn.inputs["Scale"].default_value = 2600.0
    fn.inputs["Detail"].default_value = 3.0
    hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", v1.outputs["Distance"], -0.8),
                _math(nt, "ADD", _math(nt, "MULTIPLY", fn.outputs["Fac"], 0.6), _math(nt, "MULTIPLY", s2.outputs[0], 0.3)))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(hgt, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def felt_mat(name="FeltBacking"):
    """Recycled shoddy felt backing (seen on the cut edges): mid grey with coloured
    fibre flecks, very fibrous."""
    m = C.principled(name, (0.16, 0.155, 0.15), rough=1.0)
    b = bsdf(m)
    C._set(b, "Specular IOR Level", 0.15)
    C._set(b, "Sheen Weight", 0.3)
    C._set(b, "Sheen Roughness", 0.5)
    nt = m.node_tree
    co = C._coord(nt)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 600.0
    nt.links.new(co, vo.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = 0.35
    mix.inputs["A"].default_value = (0.15, 0.145, 0.14, 1)
    nt.links.new(vo.outputs["Color"], mix.inputs["B"])
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.6
    hsv.inputs["Value"].default_value = 0.30
    nt.links.new(mix.outputs["Result"], hsv.inputs["Color"])
    nt.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1500.0
    nz.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(_math(nt, "ADD", nz.outputs["Fac"], _math(nt, "MULTIPLY", vo.outputs["Distance"], 0.5)), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def heel_pad(rubber):
    """Ribbed pad conforming to the driver's footwell floor / toe-board start."""
    cx, cy, hw, hl = -0.40, -0.17, 0.115, 0.115

    def fn(s, t):
        x = cx + (2 * s - 1) * hw
        y = cy + (2 * t - 1) * hl
        return Vector((x, y, height(x, y) + 0.0015))
    ob = shell("HeelPad", [rubber], fn, 24, 24, 0.004, offset=1.0, angle=40, finalize=False)
    C.add_bevel(ob, 0.0015, segments=2, angle=40)
    return C.finalize(ob, angle=40)


def build():
    carpet = carpet_mat()
    felt = felt_mat()
    rubber = ribbed_rubber("HeelPadRubber", pitch=0.008, axis=0, strength=0.9)
    # soft rolled cut edges: a round bevel on the rim of the 14 mm carpet + felt
    ob = shell("Carpet", [carpet, felt], surf, 180, 160, 0.014, offset=-1.0, mat_off=1, rim_off=1, angle=40,
               finalize=False)
    C.add_bevel(ob, 0.0055, segments=4, angle=50)
    ob = C.finalize(ob, angle=40)
    ob = cut(ob, cutters(felt), solver="MANIFOLD", angle=40, bevel=0.003, bevel_seg=3)
    return [ob, heel_pad(rubber)]


if __name__ == "__main__":
    hide_floor_from_glossy()
    C.clear()
    objs = build()
    C.shoot("moquette", objs, "moquette.py",
            "car front floor carpet: moulded dark grey carpet with black felt backing, shaped over the transmission "
            "tunnel and toe boards, gear lever and handbrake cut-outs, seat bolt holes, driver heel pad",
            az=-148, el=34, lens=60, fill=0.88, **render_args())
