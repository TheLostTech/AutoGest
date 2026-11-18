"""Front left seat of a generic modern small hatchback, removed from the car.
Dark anthracite woven fabric: seat cushion and backrest, each with a pleated centre insert
between side bolsters (soft subdivided pillows meeting in sewn seams, twin top-stitching),
separate headrest on two chrome posts with black guide collars, black grained plastic
side shield on the outer (-X) side with recline lever, steel seat frame and slide rails
underneath with front adjustment bar. Car front is -Y, the outer (door) side is -X."""
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


# ================================================================== seat geometry
PIV = Vector((0.0, 0.19, 0.215))          # backrest pivot
TILT = math.radians(-21)                 # backrest leans back (+Y)
MB = Matrix.Translation(PIV) @ Matrix.Rotation(TILT, 4, "X")


def cushion(fab):
    out = []

    def core_shape(p, u, v, w):
        # top dips slightly in the seating area, front edge rolls down
        if w > 0:
            p.z -= 0.012 * (1 - u * u) * (1 - v * v)
            p.z += 0.008 * sstep(0.2, -1.0, v)
        return p
    out.append(box_soft("CushionCore", [fab], (-0.252, -0.27, 0.135), (0.252, 0.215, 0.292),
                        n=(6, 6, 3), shape=core_shape))
    # side bolsters (taller, with the inner face sloping into the insert)
    for sx in (-1, 1):
        def bol_shape(p, u, v, w, sx=sx):
            inner = (u * sx) < 0
            if w > 0:
                p.z += 0.016 * (1 - abs(v)) ** 0.6 - (0.022 if inner else 0.0)
                p.z -= 0.02 * sstep(-0.3, -1.0, v)
            if inner and w > 0:
                p.x -= sx * 0.010
            return p
        out.append(box_soft("Bolster", [fab], (sx * 0.208 - 0.045, -0.262, 0.19), (sx * 0.208 + 0.045, 0.20, 0.312),
                            n=(3, 5, 3), shape=bol_shape))
    # pleated centre insert: 4 pillows front to back, front one rolls over the nose
    ys = [-0.268, -0.150, -0.050, 0.050, 0.170]
    for i in range(4):
        y0, y1 = ys[i] - 0.003, ys[i + 1] + 0.003
        z1 = 0.302 - 0.006 * i
        z0 = 0.20 if i == 0 else 0.25

        def ins_shape(p, u, v, w, i=i):
            if w > 0:
                p.z += 0.006 * (1 - u * u)
            if i == 0 and v < 0:
                p.z -= 0.0 * w
            return p
        out.append(box_soft("Insert", [fab], (-0.150, y0, z0), (0.150, y1, z1), n=(5, 3, 3), shape=ins_shape))
    return out


def backrest(fab):
    out = []

    def core_shape(p, u, v, w):
        t = (w + 1) / 2
        p.x *= 1 - 0.07 * t * t
        if v > 0:      # rear face slightly convex
            p.y += 0.012 * (1 - u * u)
        return p
    out.append(box_soft("BackCore", [fab], (-0.252, -0.040, 0.03), (0.252, 0.075, 0.62),
                        n=(6, 3, 7), shape=core_shape, M=MB))
    for sx in (-1, 1):
        def bol_shape(p, u, v, w, sx=sx):
            t = (w + 1) / 2
            # bolster protrudes most at mid height, fades into the shoulder
            if v < 0:
                p.y -= 0.035 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.7
            p.x -= sx * 0.03 * t * t
            if (u * sx) < 0 and v < 0:
                p.y += 0.012
            return p
        out.append(box_soft("BackBolster", [fab], (sx * 0.205 - 0.050, -0.075, 0.06), (sx * 0.205 + 0.050, 0.030, 0.55),
                            n=(3, 3, 6), shape=bol_shape, M=MB))
    # horizontal pleats on the insert, lumbar bulge low down
    zs = [0.05, 0.155, 0.255, 0.350, 0.445, 0.545]
    for i in range(5):
        z0, z1 = zs[i] - 0.004, zs[i + 1] + 0.004
        lum = 0.010 * math.exp(-((i - 1.0) / 1.2) ** 2)

        def ins_shape(p, u, v, w, lum=lum):
            if v < 0:
                p.y -= 0.006 * (1 - u * u) + lum
            return p
        out.append(box_soft("BackInsert", [fab], (-0.152, -0.060, z0), (0.152, 0.0, z1), n=(5, 3, 3),
                            shape=ins_shape, M=MB))
    return out


def headrest(fab, chrome, plastic):
    out = []
    zb = 0.675

    def hr_shape(p, u, v, w):
        t = (w + 1) / 2
        p.x *= 1 - 0.10 * t * t
        if v < 0:
            p.y -= 0.012 * (1 - u * u)
        p.y -= 0.025 * t      # tips forward a little
        return p
    out.append(box_soft("Headrest", [fab], (-0.135, -0.045, zb), (0.135, 0.050, zb + 0.185), n=(5, 3, 4),
                        shape=hr_shape, M=MB))
    for x in (-0.085, 0.085):
        pts = [MB @ Vector((x, 0.012, 0.52)), MB @ Vector((x, 0.012, zb + 0.04))]
        out.append(tube("Post", pts, 0.0072, chrome, res=4))
        # guide collar on top of the backrest
        bm = bmesh.new()
        Mc = MB @ Matrix.Translation((x, 0.012, 0.612))
        C.box_bm(bm, 0.030, 0.034, 0.024, matrix=Mc)
        if x < 0:   # release button on the outer collar
            C.box_bm(bm, 0.012, 0.016, 0.006, center=(-0.019, 0, 0.004), matrix=Mc)
        col = C.mesh_obj("Collar", bm, [plastic])
        C.add_bevel(col, 0.004, segments=3, angle=30)
        out.append(C.finalize(col, angle=35))
    return out


def side_shield(plastic, silver):
    """Outer side cover of the cushion frame and recline mechanism, plus the recline lever."""
    out = []
    py, pz = PIV.y, PIV.z
    poly = rounded([(-0.255, 0.075), (-0.255, 0.185), (0.06, 0.20), (py - 0.055, pz + 0.075),
                    (py + 0.07, pz + 0.05), (py + 0.075, 0.075)],
                   [0, 0.02, 0.05, 0.05, 0.04, 0.02], closed=True, seg=10)
    out.append(extrude_x("SideShield", [plastic], [(p.x, p.y) for p in poly], -0.276, -0.248, bevel=0.006, segs=3))
    # round pivot cap
    cap = C.lathe("PivotCap", [(0.0, 0.0, 0), (0.040, 0.0, 0), (0.042, 0.006, 0), (0.036, 0.012, 0), (0.0, 0.014, 0)],
                  [plastic], steps=48)
    cap.matrix_world = Matrix.Translation((-0.276, py, pz)) @ Matrix.Rotation(math.radians(-90), 4, "Y")
    out.append(C.finalize(cap, angle=40))
    # recline lever: flat grip running forward and slightly up from the pivot
    a = math.radians(14)
    L = 0.17
    d = Vector((0, -math.cos(a), math.sin(a)))
    nrm = Vector((0, math.sin(a), math.cos(a)))
    x = -0.292
    p0 = Vector((x, py - 0.03, pz - 0.035))
    bm = bmesh.new()
    M = Matrix.Identity(4)
    for i, ax in enumerate((Vector((1, 0, 0)), d, nrm)):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = p0 + d * (L / 2)
    C.box_bm(bm, 0.016, L, 0.030, matrix=M)
    lev = C.mesh_obj("Lever", bm, [plastic])
    lev.modifiers.new("Sub", "SUBSURF").levels = 2
    lev.modifiers["Sub"].render_levels = 2
    C.add_bevel(lev, 0.002, segments=2, angle=40)
    out.append(C.finalize(lev, angle=45))
    # satin insert strip on the lever grip
    bm = bmesh.new()
    M2 = M.copy()
    M2.translation = p0 + d * (L * 0.62) + Vector((-0.0085, 0, 0))
    C.box_bm(bm, 0.003, L * 0.45, 0.010, matrix=M2)
    st = C.mesh_obj("LeverStrip", bm, [silver])
    C.add_bevel(st, 0.0012, segments=2, angle=30)
    out.append(C.finalize(st, angle=40))
    return out


def frame_and_rails(steel, zincm, plastic):
    out = []
    # seat pan / frame box under the cushion (mostly in shadow)
    bm = bmesh.new()
    C.box_bm(bm, 0.40, 0.38, 0.09, center=(0.0, -0.01, 0.11))
    C.box_bm(bm, 0.05, 0.06, 0.12, center=(0.22, PIV.y, PIV.z - 0.02))   # inner recliner plate
    fr = C.mesh_obj("Frame", bm, [steel])
    C.add_bevel(fr, 0.006, segments=2, angle=30)
    out.append(C.finalize(fr, angle=35))
    for x in (-0.19, 0.19):
        # lower (fixed) rail: channel with end feet
        bm = bmesh.new()
        C.box_bm(bm, 0.040, 0.56, 0.026, center=(x, -0.02, 0.019))
        C.box_bm(bm, 0.050, 0.05, 0.010, center=(x, -0.31, 0.005))
        C.box_bm(bm, 0.050, 0.05, 0.010, center=(x, 0.27, 0.005))
        rl = C.mesh_obj("LowerRail", bm, [zincm])
        C.add_bevel(rl, 0.003, segments=2, angle=30)
        out.append(C.finalize(rl, angle=35))
        # upper (sliding) rail and riser bracket to the frame
        bm = bmesh.new()
        C.box_bm(bm, 0.024, 0.50, 0.022, center=(x, -0.03, 0.043))
        C.box_bm(bm, 0.012, 0.42, 0.045, center=(x, -0.03, 0.075))
        ur = C.mesh_obj("UpperRail", bm, [steel])
        C.add_bevel(ur, 0.003, segments=2, angle=30)
        out.append(C.finalize(ur, angle=35))
        # bolts on the feet
        for y in (-0.31, 0.27):
            bt = C.lathe("Bolt", [(0.0, 0.010, 0), (0.011, 0.010, 0), (0.011, 0.018, 0), (0.0, 0.018, 0)], [zincm], steps=6)
            bt.matrix_world = Matrix.Translation((x, y, 0))
            out.append(C.finalize(bt, angle=20))
    # front slide-adjust bar
    pts = rounded([(-0.19, -0.20, 0.045), (-0.19, -0.29, 0.045), (-0.12, -0.33, 0.04), (0.12, -0.33, 0.04),
                   (0.19, -0.29, 0.045), (0.19, -0.20, 0.045)], [0, 0.05, 0.04, 0.04, 0.05, 0], closed=False, seg=10)
    out.append(tube("SlideBar", pts, 0.0085, steel))
    return out


def stitching(fabric_objs, thr):
    tree = bvh(fabric_objs)
    out = []
    down = (0, 0, -1)
    for sx in (-1, 1):
        for off in (0.010, 0.017):
            x = sx * (0.152 + off)
            out.append(stitches(tree, [(x, -0.24, 0.5), (x, 0.17, 0.5)], down, thr))
    # backrest: lines cast along the backrest's forward direction
    fwd = (MB.to_3x3() @ Vector((0, 1, 0))).normalized()
    for sx in (-1, 1):
        for off in (0.010, 0.017):
            x = sx * (0.154 + off)
            line = [MB @ Vector((x, -0.2, z)) for z in (0.07, 0.53)]
            out.append(stitches(tree, line, fwd, thr))
    return out


def build():
    fab = fabric()
    hr_fab = fabric("HeadFabric")
    plastic = grained("SeatTrim", v=0.026, rough=0.56)
    silver = satin_silver()
    chrome = C.principled("PostChrome", (0.90, 0.90, 0.91), metallic=1.0, rough=0.07)
    steel = steel_dark()
    zincm = zinc()
    thr = thread()
    fabs = cushion(fab) + backrest(fab)
    objs = list(fabs)
    objs += headrest(hr_fab, chrome, plastic)
    objs += side_shield(plastic, silver)
    objs += frame_and_rails(steel, zincm, plastic)
    objs += stitching(fabs, thr)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("sedile", objs, "sedile.py",
            "front left car seat: anthracite woven fabric cushion and backrest with pleated inserts, side bolsters "
            "and stitched seams, headrest on two chrome posts, black plastic side trim with recline lever, seat rails",
            az=-38, el=16, lens=70, fill=0.86,
            res=(512, 512) if FAST else (1024, 1024),
            samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))
