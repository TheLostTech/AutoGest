"""Centre console (consolle centrale / tunnel) of a generic modern small hatchback, as
removed from the car: one-piece black grained plastic moulding that sits over the
transmission tunnel, lofted from a rounded section that flares out to a mounting flange at
the floor. Along the top, front to rear: a sloped nose with a 12 V socket and cap in the
front face, a storage tray with a ribbed rubber mat, the gear-lever opening framed by a
satin-silver gaiter ring, a step down to two tandem cupholders with rubber bottom discs, and
the long handbrake slot in a black frame. Car front is -Y."""
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


# ================================================================== console geometry
Y0, Y1 = -0.40, 0.40
LEATHER = []


def top_h(y):
    """Height of the top surface along the console."""
    h = 0.200 - 0.048 * sstep(-0.40, -0.33, y)          # sloped nose
    h -= 0.030 * sstep(-0.085, -0.045, y)                # step down to cupholders / handbrake
    h += 0.010 * sstep(0.20, 0.40, y)                    # slight rise at the rear
    return h


def half_w(y):
    return 0.086 - 0.008 * sstep(-0.3, 0.4, y)


def section(y):
    h, wt = top_h(y), half_w(y)
    wb = wt + 0.040
    zm = 0.45 * h
    wm = wt + 0.010            # waist: side panel curves in above the flared foot
    cs = [(-wb - 0.010, 0.0), (wb + 0.010, 0.0), (wb + 0.010, 0.005), (wb, 0.008), (wb - 0.004, zm * 0.5),
          (wm, zm), (wt + 0.006, h - 0.03), (wt, h), (-wt, h), (-wt - 0.006, h - 0.03), (-wm, zm),
          (-wb + 0.004, zm * 0.5), (-wb, 0.008), (-wb - 0.010, 0.005)]
    pts = rounded([(x, z, 0) for x, z in cs], [0, 0, 0.002, 0.004, 0.02, 0.03, 0.02, 0.030, 0.030, 0.02, 0.03, 0.02,
                                                0.004, 0.002], closed=True, seg=5)
    return [Vector((p.x, y, p.y)) for p in pts]


def body(mat, n=72):
    """Lofted shell. Kept light on purpose (72 sections x ~75 points, no bevel modifier
    before the cut-outs): the earlier 140-section loft with a 4-segment bevel and six
    separate EXACT self-intersection booleans took over half an hour to evaluate."""
    secs = [section(Y0 + (Y1 - Y0) * i / n) for i in range(n + 1)]
    return loft("ConsoleBody", [mat], secs)


def features(ob, cav, black, silver, rubber):
    out = []
    cutters = []
    # storage tray
    ty = -0.295
    cutters.append(prism_z("TrayCut", [cav], rrect(0.0, ty, 0.120, 0.064, 0.016), top_h(ty) - 0.026, 0.4, bevel=0,
                           angle=None))
    # gear lever opening (deep)
    gy = -0.175
    gw, gl = 0.112, 0.128
    cutters.append(prism_z("GearCut", [cav], rrect(0.0, gy, gw, gl, 0.024), 0.03, 0.4, bevel=0, angle=None))
    # tandem cupholders
    cups = (-0.008, 0.078)
    for cy in cups:
        cutters.append(cutter_obj("CupCut", cav, lambda bm, cy=cy: C.cyl_bm(
            bm, 0.0375, top_h(cy) - 0.072, 0.4, seg=48, matrix=Matrix.Translation((0, cy, 0)))))
    # handbrake slot
    hy, hl = 0.252, 0.200
    cutters.append(prism_z("BrakeCut", [cav], rrect(0.0, hy, 0.034, hl, 0.015), 0.03, 0.4, bevel=0, angle=None))
    # 12 V socket bore in the front face (cutter axis along Y)
    cutters.append(cutter_obj("SocketCut", cav, lambda bm: C.cyl_bm(
        bm, 0.0135, -0.03, 0.03, seg=48, matrix=Matrix.Translation((0, Y0, 0.120)) @ Matrix.Rotation(math.radians(90), 4, "X"))))
    # all cut-outs are disjoint: join them into ONE cutter and subtract once with the fast
    # MANIFOLD solver, then a single small bevel on every sharp edge (end caps, openings)
    for c in cutters:
        c.hide_viewport = False
    bpy.ops.object.select_all(action="DESELECT")
    for c in cutters:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    allcut = cutters[0]
    m = ob.modifiers.new("Bool", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = allcut
    m.solver = "MANIFOLD"
    try:
        m.material_mode = "TRANSFER"
    except Exception:
        pass
    allcut.hide_render = True
    allcut.hide_viewport = True
    C.add_bevel(ob, 0.003, segments=2, angle=30)
    body_ob = C.finalize(ob, angle=35, remove=[allcut])
    out.append(body_ob)
    # tray mat
    out.append(prism_z("TrayMat", [rubber], rrect(0.0, ty, 0.112, 0.056, 0.012), top_h(ty) - 0.026, top_h(ty) - 0.022,
                       bevel=0.001))
    # satin gaiter frame around the gear opening
    hg = top_h(gy)
    out.append(rring("GaiterFrame", silver, rrect(0.0, gy, gw + 0.020, gl + 0.020, 0.032, seg=10),
                     rrect(0.0, gy, gw - 0.004, gl - 0.004, 0.022, seg=10), hg - 0.003, hg + 0.0045, bevel=0.0018))
    # leatherette gaiter in the gear opening
    out += gaiter(LEATHER[0], black, 0.0, gy, gw, gl, hg - 0.010, height=0.075)
    # cup bottoms
    for cy in cups:
        d = C.lathe("CupDisc", [(0.0, 0.0, 0), (0.0365, 0.0, 0), (0.0365, 0.003, 0), (0.035, 0.004, 0), (0.0, 0.004, 0)],
                    [rubber], steps=64)
        d.location = (0, cy, top_h(cy) - 0.072)
        out.append(C.finalize(d, angle=40))
    # handbrake slot frame
    hh = top_h(hy)
    out.append(rring("BrakeFrame", black, rrect(0.0, hy, 0.050, hl + 0.016, 0.022, seg=8),
                     rrect(0.0, hy, 0.032, hl - 0.002, 0.014, seg=8), hh - 0.002, hh + 0.003, bevel=0.0012))
    # 12 V socket: metal sleeve and black cap with a hinge strap
    Mk = Matrix.Translation((0, Y0 + 0.002, 0.120)) @ Matrix.Rotation(math.radians(90), 4, "X")
    sl = C.lathe("SocketRim", [(0.0110, -0.03, 0), (0.0165, -0.002, 0), (0.0170, 0.003, 0), (0.0110, 0.003, 0)],
                 [black], steps=48, closed=True)
    sl.matrix_world = Mk
    out.append(C.finalize(sl, angle=40))
    cp = C.lathe("SocketCap", [(0.0, 0.003, 0), (0.0150, 0.003, 0), (0.0155, 0.007, 0), (0.0135, 0.010, 0), (0.0, 0.011, 0)],
                 [black], steps=48)
    cp.matrix_world = Mk
    out.append(C.finalize(cp, angle=40))
    return out


def gaiter(mat, ring_m, cx, cy, gw, gl, z0, height=0.085):
    """Leatherette gear-lever gaiter rising out of the opening: rounded-rectangle base
    tucked under the frame, gathering into soft folds towards the top collar."""
    a0, b0 = gw / 2 - 0.004, gl / 2 - 0.004
    K, NS = 96, 26
    rings = []
    bm = bmesh.new()
    for j in range(NS + 1):
        t = j / NS
        sc = 1.0 + (0.24 - 1.0) * t ** 0.6 + 0.06 * math.sin(math.pi * t)
        z = z0 + height * t
        ring = []
        for k in range(K):
            th = math.tau * k / K
            c, s_ = math.cos(th), math.sin(th)
            n = 6.0 * (1 - t) + 2.0 * t
            r = (abs(c / a0) ** n + abs(s_ / b0) ** n) ** (-1.0 / n)
            fold = 1.0 + 0.13 * math.sin(7 * th + 4.0 * t) * math.sin(math.pi * min(1.0, t * 1.15)) ** 1.5
            rr = r * sc * fold
            ring.append(bm.verts.new((cx + rr * c, cy + rr * s_, z)))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(K):
            k2 = (k + 1) % K
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj("Gaiter", bm, [mat])
    sd = ob.modifiers.new("Sub", "SUBSURF")
    sd.levels = sd.render_levels = 1
    out = [C.finalize(ob, angle=70)]
    # top collar ring where the lever comes through
    rt = 0.24 * min(a0, b0) * 0.95
    col = C.lathe("GaiterCollar", [(rt * 0.55, 0.0, 0), (rt + 0.004, 0.0, 0), (rt + 0.004, 0.010, 0),
                                   (rt + 0.002, 0.012, 0), (rt * 0.55, 0.012, 0)], [ring_m], steps=48)
    col.location = (cx, cy, z0 + height - 0.004)
    C.add_bevel(col, 0.0008, segments=2, angle=30)
    out.append(C.finalize(col, angle=40))
    return out


def build():
    plastic = grained("ConsolePP", v=0.034, rough=0.56, scale=600.0)
    black = grained("FramePP", v=0.018, rough=0.45, scale=800.0)
    cav = grained("CavityPP", v=0.016, rough=0.62, scale=700.0)
    LEATHER.append(grained("GaiterLeather", v=0.020, rough=0.42, scale=1400.0))
    silver = satin_silver()
    rubber = ribbed_rubber("TrayRubber", pitch=0.0045, axis=0)
    ob = body(plastic)
    return features(ob, cav, black, silver, rubber)


if __name__ == "__main__":
    hide_floor_from_glossy()
    C.clear()
    objs = build()
    C.shoot("consolle", objs, "consolle.py",
            "car centre console: black grained plastic tunnel console with storage tray, gear lever opening with satin "
            "frame, two cupholders, handbrake slot and 12V socket",
            az=-50, el=38, lens=70, fill=0.86, **render_args())
