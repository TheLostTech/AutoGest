"""Rear bench seat of a generic modern small hatchback, removed from the car.
Dark anthracite woven fabric throughout: one-piece cushion with pleated inserts for the
three seating positions, 60/40 split-fold backrest (two separate backs with a visible gap,
the 60 part on the left carrying the centre position), three headrests on chrome posts
with black guide collars, black plastic release latches with satin buttons at the outer
top corners, steel hinge brackets, black cushion tub and wire hooks. Front is -Y."""
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


def fabric(name="SeatFabric", hexc="#2C2E31", period=0.0034, weave=0.6):
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
    h = _math(nt, "ADD", _math(nt, "MULTIPLY", w, weave), _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.8))
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


# ================================================================== bench geometry
HW = 0.66                                # half width
PIV = Vector((0.0, 0.25, 0.085))         # backrest hinge line
TILT = math.radians(-22)
MB = Matrix.Translation(PIV) @ Matrix.Rotation(TILT, 4, "X")
SPLIT = 0.125                            # 60/40 split (x), 60 part on the left
GAP = 0.018
SEATS = [(-0.40, 0.30), (0.0, 0.19), (0.40, 0.30)]   # seating positions: centre x, insert width


def cushion(fab):
    out = []

    def core_shape(p, u, v, w):
        if w > 0:
            # two outer seat dishes, slight crown in the middle position, rolled front
            dish = sum(0.012 * math.exp(-((p.x - sx) / 0.16) ** 2) for sx in (-0.40, 0.40))
            p.z -= dish * (1 - v * v)
            p.z += 0.010 * sstep(0.3, -1.0, v)
        p.x *= 1 - 0.03 * sstep(0.0, 1.0, v)        # narrows slightly to the rear
        return p
    out.append(box_soft("CushionCore", [fab], (-HW, -0.27, 0.035), (HW, 0.21, 0.200),
                        n=(14, 6, 3), shape=core_shape))
    ys = [-0.262, -0.120, 0.010, 0.150]
    for (cx, w) in SEATS:
        for i in range(3):
            y0, y1 = ys[i] - 0.003, ys[i + 1] + 0.003
            z1 = 0.214 - 0.003 * i - (0.004 if cx == 0 else 0.0)
            z0 = 0.10 if i == 0 else 0.16

            def ins_shape(p, u, v, ww):
                if ww > 0:
                    p.z += 0.005 * (1 - u * u)
                return p
            out.append(box_soft("Insert", [fab], (cx - w / 2, y0, z0), (cx + w / 2, y1, z1), n=(5, 3, 3),
                                shape=ins_shape))
    return out


def backrest(fab):
    out = []
    parts = [(-HW, SPLIT - GAP / 2), (SPLIT + GAP / 2, HW)]
    for k, (x0, x1) in enumerate(parts):
        outer = x0 if k == 0 else x1

        def core_shape(p, u, v, w, outer=outer):
            t = (w + 1) / 2
            # outer top corner rounded off / tapering towards the C-pillar
            d = abs(p.x - outer)
            p.z -= 0.06 * t ** 3 * math.exp(-d / 0.10)
            p.z -= 0.025 * t ** 4 * math.exp(-abs(p.x - SPLIT) / 0.035)
            if v < 0:
                p.y -= 0.008 * (1 - u * u)
            return p
        nx = 10 if k == 0 else 7
        out.append(box_soft("BackCore", [fab], (x0, -0.035, 0.0), (x1, 0.055, 0.60), n=(nx, 3, 7),
                            shape=core_shape, M=MB))
    zs = [0.05, 0.16, 0.27, 0.38, 0.49, 0.545]
    for (cx, w) in SEATS:
        top = 0.50 if cx != 0 else 0.48
        zz = [0.05, 0.17, 0.29, 0.40, top]
        for i in range(4):
            z0, z1 = zz[i] - 0.004, zz[i + 1] + 0.004
            lum = 0.008 * math.exp(-((i - 0.8) / 1.0) ** 2)

            def ins_shape(p, u, v, ww, lum=lum):
                if v < 0:
                    p.y -= 0.005 * (1 - u * u) + lum
                return p
            out.append(box_soft("BackInsert", [fab], (cx - w / 2, -0.052, z0), (cx + w / 2, 0.0, z1), n=(5, 3, 3),
                                shape=ins_shape, M=MB))
    return out


def headrests(fab, chrome, plastic):
    out = []
    zb = 0.645
    for (cx, w) in SEATS:
        hw = 0.125 if cx != 0 else 0.10
        hh = 0.16 if cx != 0 else 0.13

        def hr_shape(p, u, v, ww):
            t = (ww + 1) / 2
            p.x = cx + (p.x - cx) * (1 - 0.10 * t * t)
            if v < 0:
                p.y -= 0.010 * (1 - u * u)
            p.y -= 0.02 * t
            return p
        out.append(box_soft("Headrest", [fab], (cx - hw, -0.04, zb), (cx + hw, 0.045, zb + hh), n=(5, 3, 4),
                            shape=hr_shape, M=MB))
        for dx in (-0.07, 0.07):
            x = cx + dx * (0.85 if cx == 0 else 1.0)
            out.append(tube("Post", [MB @ Vector((x, 0.008, 0.50)), MB @ Vector((x, 0.008, zb + 0.035))], 0.0068,
                            chrome, res=4))
            bm = bmesh.new()
            Mc = MB @ Matrix.Translation((x, 0.008, 0.592))
            C.box_bm(bm, 0.028, 0.032, 0.022, matrix=Mc)
            col = C.mesh_obj("Collar", bm, [plastic])
            C.add_bevel(col, 0.004, segments=3, angle=30)
            out.append(C.finalize(col, angle=35))
    return out


def latches(plastic, silver, steel):
    """Backrest release latches at the outer top corners and hinge brackets at the bottom."""
    out = []
    for sx in (-1, 1):
        x = sx * (HW - 0.075)
        bm = bmesh.new()
        Mc = MB @ Matrix.Translation((x, 0.012, 0.556))
        C.box_bm(bm, 0.075, 0.040, 0.030, matrix=Mc)
        lt = C.mesh_obj("LatchBezel", bm, [plastic])
        lt.modifiers.new("Sub", "SUBSURF").levels = 2
        lt.modifiers["Sub"].render_levels = 2
        out.append(C.finalize(lt, angle=50))
        bm = bmesh.new()
        C.box_bm(bm, 0.040, 0.016, 0.012, center=(0, -0.006, 0.014), matrix=Mc)
        bt = C.mesh_obj("LatchButton", bm, [silver])
        C.add_bevel(bt, 0.003, segments=2, angle=30)
        out.append(C.finalize(bt, angle=40))
    # hinge brackets: outer ends and at the split
    for x, s in ((SPLIT, 0),):
        bm = bmesh.new()
        w = 0.008 if s else 0.020
        C.box_bm(bm, w, 0.10, 0.06, center=(x, PIV.y + 0.005, PIV.z - 0.02))
        C.box_bm(bm, w + 0.02, 0.12, 0.008, center=(x, PIV.y + 0.01, 0.004))
        br = C.mesh_obj("Hinge", bm, [steel])
        C.add_bevel(br, 0.003, segments=2, angle=30)
        out.append(C.finalize(br, angle=35))
        cap = C.lathe("HingeBolt", [(0.0, 0.0, 0), (0.016, 0.0, 0), (0.016, 0.008, 0), (0.0, 0.010, 0)], [steel], steps=6)
        cap.matrix_world = Matrix.Translation((x - (0.004 if x < 0 else -0.004) * s, PIV.y, PIV.z)) @ \
            Matrix.Rotation(math.radians(-90 if x <= 0 else 90), 4, "Y")
        out.append(C.finalize(cap, angle=20))
    return out


def base(plastic, steel):
    """Black moulded cushion tub and front wire hooks visible under the fabric."""
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 2 * HW - 0.04, 0.44, 0.04, center=(0, -0.03, 0.022))
    tb = C.mesh_obj("Tub", bm, [plastic])
    C.add_bevel(tb, 0.008, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    for x in ():
        pts = rounded([(x - 0.05, -0.20, 0.03), (x - 0.05, -0.30, 0.01), (x + 0.05, -0.30, 0.01), (x + 0.05, -0.20, 0.03)],
                      [0, 0.02, 0.02, 0], closed=False, seg=8)
        out.append(tube("Hook", pts, 0.004, steel))
    return out


def stitching(fabric_objs, thr):
    tree = bvh(fabric_objs)
    out = []
    fwd = (MB.to_3x3() @ Vector((0, 1, 0))).normalized()
    for (cx, w) in SEATS:
        for sx in (-1, 1):
            for off in (0.010, 0.017):
                x = cx + sx * (w / 2 + off)
                out.append(stitches(tree, [(x, -0.24, 0.6), (x, 0.14, 0.6)], (0, 0, -1), thr))
                ztop = 0.49 if cx != 0 else 0.47
                out.append(stitches(tree, [MB @ Vector((x, -0.3, 0.06)), MB @ Vector((x, -0.3, ztop))], fwd, thr))
    return out


def build():
    fab = fabric(weave=0.22)
    plastic = grained("BenchTrim", v=0.026, rough=0.56)
    silver = satin_silver()
    chrome = C.principled("PostChrome", (0.90, 0.90, 0.91), metallic=1.0, rough=0.07)
    steel = steel_dark()
    thr = thread()
    fabs = cushion(fab) + backrest(fab)
    objs = list(fabs)
    objs += headrests(fab, chrome, plastic)
    objs += latches(plastic, silver, steel)
    objs += base(plastic, steel)
    objs += stitching(fabs, thr)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("divanetto", objs, "divanetto.py",
            "rear bench seat: anthracite woven fabric cushion and 60/40 split-fold backrest with pleated inserts "
            "and stitched seams, three headrests on chrome posts, backrest release latches, hinge brackets",
            az=-30, el=17, lens=70, fill=0.90,
            res=(512, 512) if FAST else (1024, 1024),
            samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))
