"""Dashboard of a generic modern small hatchback (left-hand drive) as removed from the car.
Two-tone moulded shell lofted from a crisp section: soft-touch black upper part (flat top
sweeping forward to the windscreen edge with the demister grille, upper face with a sharp
lip and a small step to the lower part) and lighter grey grained lower part; flat, sharp-
edged end caps where the dash meets the A-pillars, with side-window demister slots. Arched
binnacle hood clearly overhanging the empty instrument-cluster opening, arched steering-
column opening, two rectangular centre vents and two round outer vents with satin bezels and
black louvres, a separate centre stack dropping below the dash with a piano-black panel and
the empty radio and climate openings (mounting clips inside), and a separate glovebox lid set
into the passenger-side lower face with visible shut-lines, satin pull and lock barrel.
Cabin side -Y, driver on -X."""
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
    mr.inputs["To Min"].default_value = rough - 0.03
    mr.inputs["To Max"].default_value = rough + 0.03
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def satin_silver(name="SatinSilver"):
    m = C.principled(name, (0.42, 0.425, 0.435), metallic=1.0, rough=0.36)
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


# ================================================================== dashboard geometry
# X across the car (driver on the left, -X), cabin side -Y, windscreen side +Y, Z up.
HX = 0.70                                  # half width: flat end caps at x = +-HX
ZSPLIT = 0.281                             # two-tone break (upper soft-touch / lower grey)
CLUSTER_X = (-0.380, 0.150)                # binnacle centre x, half width
COLUMN = (-0.38, 0.085, 0.080)             # steering-column arch: x, z, r
P5 = Vector((-0.182, 0.262))               # lower face, top (y, z)
P6 = Vector((-0.135, 0.100))               # lower face, bottom


def profile(x):
    e = sstep(0.58, HX, abs(x))
    C0 = [(0.370, 0.335), (0.180 + 0.03 * e, 0.400), (-0.175, 0.408), (-0.200, 0.290), (-0.178, 0.276),
          (P5.x, P5.y), (P6.x, P6.y), (-0.105, 0.080), (0.100, 0.100), (0.260, 0.210)]
    R = [0.008, 0.12, 0.016, 0.006, 0.003, 0.004, 0.02, 0.01, 0.03, 0.03]
    pts = []
    for i, (y, z) in enumerate(C0):
        if 2 <= i <= 7:
            y += 0.05 * e
        pts.append((y, z))
    return [(p.x, p.y) for p in rounded(pts, R, closed=True, seg=6)]


def body(upper, lower):
    bm = bmesh.new()
    xs = [-HX + 2 * HX * i / 44 for i in range(45)]
    secs = [[bm.verts.new((x, y, z)) for (y, z) in profile(x)] for x in xs]
    m = len(secs[0])
    for i in range(len(secs) - 1):
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((secs[i][k], secs[i][k2], secs[i + 1][k2], secs[i + 1][k]))
    # flat end caps (fans) so they can be two-tone too
    for ring in (secs[0], secs[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        for k in range(m):
            bm.faces.new((ring[k], ring[(k + 1) % m], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = 0 if f.calc_center_median().z >= ZSPLIT else 1
    ob = C.mesh_obj("Dash", bm, [upper, lower])
    C.add_bevel(ob, 0.004, segments=3, angle=40)
    return C.finalize(ob, angle=40)


def centre_stack(mat):
    poly = rounded([(-0.198, 0.274), (-0.222, 0.020), (-0.205, -0.035), (0.020, -0.035), (0.020, 0.274)],
                   [0, 0.016, 0.02, 0, 0], closed=True, seg=8)
    return extrude_x("CentreStack", [mat], [(p.x, p.y) for p in poly], -0.138, 0.138, bevel=0.006, segs=3)


def hood(mat):
    """Instrument binnacle: an arched visor shell over the cluster opening, overhanging it."""
    xc, hw = CLUSTER_X
    zb, h0 = 0.392, 0.112
    y0, y1 = -0.268, 0.095
    NS, NT = 48, 24
    bm = bmesh.new()
    rows = []
    for j in range(NT + 1):
        t = j / NT
        y = y0 + (y1 - y0) * t
        h = h0 * (1 - t ** 1.6)
        row = []
        for i in range(NS + 1):
            s = i / NS
            sn = math.sin(math.pi * s)
            x = xc - (hw + 0.012 * (1 - t)) * math.cos(math.pi * s)
            z = zb + h * sn ** 0.45
            yy = y + 0.022 * (1 - sn) * (1 - t)           # legs set back from the visor lip
            row.append(bm.verts.new((x, yy, z)))
        rows.append(row)
    for j in range(NT):
        for i in range(NS):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.normal_update()
    if sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    ob = C.mesh_obj("Hood", bm, [mat])
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.011
    sol.offset = -1.0
    sol.use_even_offset = True
    C.add_bevel(ob, 0.003, segments=3, angle=30)
    return C.finalize(ob, angle=40)


def lower_frame(xc):
    """Matrix on the (planar) lower face: X along the car width, Y up the face, Z out of it."""
    d = (P5 - P6).normalized()
    n = Vector((-d.y, d.x))
    if n.x > 0:
        n = -n
    zc = 0.1825
    t = (P5.y - zc) / (P5.y - P6.y)
    yc = P5.x + (P6.x - P5.x) * t
    M = Matrix.Identity(4)
    for i, ax in enumerate((Vector((1, 0, 0)), Vector((0, d.x, d.y)), Vector((0, n.x, n.y)))):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = Vector((xc, yc, zc))
    return M


GL_X, GL_HU, GL_HV = 0.365, 0.158, 0.060


def glovebox(lower, black, silver, cutter_bm):
    M = lower_frame(GL_X)
    gap = 0.0028
    C.box_bm(cutter_bm, 2 * (GL_HU + gap), 2 * (GL_HV + gap), 0.05, center=(0, 0, -0.015), matrix=M)
    out = [box_soft("GloveLid", [lower], (-GL_HU, -GL_HV, -0.020), (GL_HU, GL_HV, 0.0006), n=(8, 4, 2), levels=2, M=M)]
    # finger recess + satin pull at the top edge
    bm = bmesh.new()
    C.box_bm(bm, 0.090, 0.020, 0.004, center=(0, GL_HV - 0.024, 0.0), matrix=M)
    rc = C.mesh_obj("GloveRecess", bm, [black])
    C.add_bevel(rc, 0.0018, segments=2, angle=30)
    out.append(C.finalize(rc, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.078, 0.008, 0.007, center=(0, GL_HV - 0.018, 0.002), matrix=M)
    hd = C.mesh_obj("GloveHandle", bm, [silver])
    C.add_bevel(hd, 0.002, segments=2, angle=30)
    out.append(C.finalize(hd, angle=35))
    # key lock barrel beside the handle
    lk = C.lathe("GloveLock", [(0.0, 0.0, 0), (0.008, 0.0, 0), (0.008, 0.004, 0), (0.0, 0.005, 0)], [silver], steps=32)
    lk.matrix_world = M @ Matrix.Translation((0.065, GL_HV - 0.024, 0.0))
    out.append(C.finalize(lk, angle=40))
    return out


def islands(cut, mat):
    """Split a multi-island cutter bmesh into separate objects (one boolean each)."""
    objs = []
    seen = set()
    cut.verts.ensure_lookup_table()
    for v0 in cut.verts:
        if v0.index in seen:
            continue
        stack, comp = [v0], []
        seen.add(v0.index)
        while stack:
            v = stack.pop()
            comp.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        bm1 = bmesh.new()
        mp = {v: bm1.verts.new(v.co) for v in comp}
        for f in {f for v in comp for f in v.link_faces}:
            bm1.faces.new([mp[v] for v in f.verts])
        objs.append(C.mesh_obj("Cutter", bm1, [mat]))
    return objs


def cut_all(targets, cutters):
    for t in targets:
        for co in cutters:
            mo = C.add_boolean(t, co)
            try:
                mo.use_hole_tolerant = True
            except Exception:
                pass
    for co in cutters:
        co.hide_viewport = False
    out = [C.finalize(t, angle=40) for t in targets]
    for co in cutters:
        bpy.data.objects.remove(co, do_unlink=True)
    return out


def surf_y(tree, x, z):
    hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
    return hit[0].y if hit[0] is not None else None


def surf_z(tree, x, y):
    hit = tree.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)), 3.0)
    return hit[0].z if hit[0] is not None else None


def conform_soft(name, mats, tree, x0, x1, z0, z1, proud, embed=0.012, n=(6, 2, 4), levels=3, xz=None):
    """Soft panel lying on the dashboard face between x0..x1, z0..z1 (proud of it by 'proud')."""
    def fn(u, v, w):
        x = x0 + (x1 - x0) * (u + 1) / 2
        z = z0 + (z1 - z0) * (w + 1) / 2
        if xz:
            x, z = xz(x, z, u, w)
        ys = surf_y(tree, x, z)
        return Vector((x, ys - proud if v < 0 else ys + embed, z))
    return soft(name, mats, n, fn, levels)


def rrect_ring(name, mat, cx, cz, w, h, r, y0, y1, frame=0.009):
    """Rounded-rectangle bezel ring (opening w x h) facing -Y."""
    outer = rounded([(cx - w / 2 - frame, cz - h / 2 - frame), (cx + w / 2 + frame, cz - h / 2 - frame),
                     (cx + w / 2 + frame, cz + h / 2 + frame), (cx - w / 2 - frame, cz + h / 2 + frame)],
                    [r + frame] * 4, closed=True, seg=8)
    inner = rounded([(cx - w / 2, cz - h / 2), (cx + w / 2, cz - h / 2), (cx + w / 2, cz + h / 2),
                     (cx - w / 2, cz + h / 2)], [r] * 4, closed=True, seg=8)
    bm = bmesh.new()
    o0 = [bm.verts.new((p.x, y0, p.y)) for p in outer]
    o1 = [bm.verts.new((p.x, y1, p.y)) for p in outer]
    i0 = [bm.verts.new((p.x, y0, p.y)) for p in inner]
    i1 = [bm.verts.new((p.x, y1, p.y)) for p in inner]
    n = len(outer)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))
        bm.faces.new((o0[k2], o0[k], i0[k], i0[k2]))
        bm.faces.new((o1[k], o1[k2], i1[k2], i1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, min(0.002, frame * 0.3), segments=3, angle=30)
    return C.finalize(ob, angle=35)


def rect_vent(tree, cx, cz, w, h, silver, black, dark, cutter_bm):
    ys = surf_y(tree, cx, cz)
    out = []
    C.box_bm(cutter_bm, w, 0.12, h, center=(cx, ys + 0.03, cz))
    out.append(rrect_ring("VentBezel", silver, cx, cz, w, h, 0.010, ys - 0.007, ys + 0.012, frame=0.008))
    bm = bmesh.new()
    C.box_bm(bm, w, 0.004, h, center=(cx, ys + 0.055, cz))
    out.append(C.mesh_obj("VentBack", bm, [dark]))
    for i in range(4):
        z = cz - h / 2 + h * (i + 0.5) / 4
        bm = bmesh.new()
        M = Matrix.Translation((cx, ys + 0.016, z)) @ Matrix.Rotation(math.radians(-18), 4, "X")
        C.box_bm(bm, w - 0.003, 0.024, 0.0028, matrix=M)
        sl = C.mesh_obj("Slat", bm, [black])
        C.add_bevel(sl, 0.0009, segments=2, angle=30)
        out.append(C.finalize(sl, angle=35))
    # adjuster tab on the second slat
    bm = bmesh.new()
    M = Matrix.Translation((cx + w * 0.12, ys + 0.004, cz - h / 2 + h * 1.5 / 4)) @ Matrix.Rotation(math.radians(-18), 4, "X")
    C.box_bm(bm, 0.016, 0.010, 0.008, matrix=M)
    tb = C.mesh_obj("VentTab", bm, [silver])
    C.add_bevel(tb, 0.002, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    return out


def round_vent(tree, cx, cz, r, silver, black, dark, cutter_bm):
    ys = surf_y(tree, cx, cz)
    out = []
    M = Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> -Y
    C.cyl_bm(cutter_bm, r, -(ys + 0.10), -(ys - 0.02), seg=48, matrix=M)
    ring = C.lathe("RoundBezel", [(r - 0.001, -(ys + 0.012), 0), (r + 0.010, -(ys + 0.004), 0), (r + 0.010, -(ys - 0.003), 0),
                                  (r + 0.006, -(ys - 0.007), 0), (r - 0.001, -(ys - 0.006), 0)], [silver], steps=96)
    ring.matrix_world = M
    out.append(C.finalize(ring, angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, r, -(ys + 0.056), -(ys + 0.052), seg=48, matrix=M)
    out.append(C.mesh_obj("VentBack", bm, [dark]))
    for i in range(5):
        x = cx - r + 2 * r * (i + 0.5) / 5
        hh = math.sqrt(max(0.0, r * r - (x - cx) ** 2)) * 2 - 0.004
        bm = bmesh.new()
        C.box_bm(bm, 0.0028, 0.022, hh, center=(x, ys + 0.016, cz))
        sl = C.mesh_obj("Louver", bm, [black])
        C.add_bevel(sl, 0.0009, segments=2, angle=30)
        out.append(C.finalize(sl, angle=35))
    knob = C.lathe("VentKnob", [(0.0, -(ys + 0.004), 0), (0.009, -(ys + 0.004), 0), (0.009, -(ys - 0.004), 0),
                                (0.0, -(ys - 0.005), 0)], [silver], steps=32)
    knob.matrix_world = M
    out.append(C.finalize(knob, angle=40))
    return out


def opening(tree, cx, cz, w, h, depth, cutter_bm, zincm, clips=True):
    ys = surf_y(tree, cx, cz)
    C.box_bm(cutter_bm, w, depth + 0.06, h, center=(cx, ys - 0.03 + (depth + 0.06) / 2, cz))
    out = []
    if clips:
        for sx in (-1, 1):
            bm = bmesh.new()
            C.box_bm(bm, 0.004, 0.06, 0.030, center=(cx + sx * (w / 2 - 0.002), ys + 0.06, cz))
            cl = C.mesh_obj("MountClip", bm, [zincm])
            C.add_bevel(cl, 0.001, segments=1, angle=30)
            out.append(C.finalize(cl, angle=35))
    return out, ys


def slot_mat(name="DefrostGrille"):
    m = grained(name, v=0.022, rough=0.6, scale=900.0)
    nt = m.node_tree
    b = bsdf(m)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt), sep.inputs[0])
    f = _math(nt, "FRACT", _math(nt, "MULTIPLY", sep.outputs[0], 1 / 0.0085))
    mask = _math(nt, "LESS_THAN", f, 0.55)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mask, mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.024, 0.024, 0.026, 1)
    mix.inputs["B"].default_value = (0.001, 0.001, 0.001, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.001
    bump.invert = True
    nt.links.new(mask, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def top_strip(tree, name, mat, x0, x1, y0, y1, lift=0.0012, thick=0.003, nx=80, ny=4):
    bm = bmesh.new()
    rows = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            z = surf_z(tree, x, y)
            row.append(bm.verts.new((x, y, z + lift)))
        rows.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.normal_update()
    if sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    ob = C.mesh_obj(name, bm, [mat])
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    C.add_bevel(ob, thick * 0.4, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def build():
    upper = grained("SoftTouchBlack", v=0.020, rough=0.72, scale=700.0)
    lower = grained("LowerGrey", v=0.078, rough=0.62, scale=520.0)
    dark = C.principled("CavityBlack", (0.006, 0.006, 0.006), rough=0.8)
    black = grained("VentPP", v=0.018, rough=0.45, scale=900.0)
    gloss = C.principled("PianoBlack", (0.010, 0.010, 0.011), rough=0.10)
    C._set(bsdf(gloss), "Coat Weight", 0.5)
    silver = satin_silver()
    zincm = zinc()
    dash = body(upper, lower)
    stack = centre_stack(upper)
    tree = bvh([dash, stack])
    objs = []
    cut = bmesh.new()
    # cluster opening under the hood, steering-column arch
    xc, hw = CLUSTER_X
    C.box_bm(cut, 2 * (hw - 0.022), 0.32, 0.118, center=(xc, -0.18, 0.305 + 0.059))
    cx, cz, r = COLUMN
    C.cyl_bm(cut, r, -0.25, 0.35, seg=64, matrix=Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    # vents on the upper face
    for vx in (-0.076, 0.076):
        objs += rect_vent(tree, vx, 0.346, 0.116, 0.056, silver, black, dark, cut)
    for vx in (-0.612, 0.612):
        objs += round_vent(tree, vx, 0.346, 0.040, silver, black, dark, cut)
    # centre stack: gloss panel with the empty radio and climate openings
    panel = conform_soft("StackPanel", [gloss], tree, -0.118, 0.118, 0.008, 0.252, 0.004, embed=0.006,
                         n=(6, 1, 6), levels=2)
    o1, _ = opening(tree, 0.0, 0.182, 0.190, 0.100, 0.13, cut, zincm)
    o2, _ = opening(tree, 0.0, 0.060, 0.190, 0.058, 0.10, cut, zincm, clips=False)
    objs += o1 + o2
    objs += glovebox(lower, black, silver, cut)
    cutters = islands(cut, upper)
    objs += cut_all([dash, stack, panel], cutters)
    objs.append(hood(upper))
    # windscreen and side-window demister grilles on the top
    tree2 = bvh([o for o in objs if o.name.startswith("Dash")])
    objs.append(top_strip(tree2, "Defrost", slot_mat(), -0.48, 0.48, 0.245, 0.290))
    for sx in (-1, 1):
        objs.append(top_strip(tree2, "SideDemist", slot_mat("SideDemist"), sx * 0.645 - 0.03, sx * 0.645 + 0.03,
                              0.215, 0.265, nx=12, ny=4))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("plancia", objs, "plancia.py",
            "car dashboard as removed: two-tone moulded dash (soft-touch black top, grey lower) with flat end caps, "
            "instrument binnacle hood over the empty cluster opening, centre stack with empty radio and climate "
            "openings, rectangular and round air vents with satin bezels, glovebox lid with shut-lines, demister grilles",
            az=-32, el=20, lens=70, fill=0.92, fill_w=0.95, fill_h=0.92,
            res=(512, 512) if FAST else (1024, 1024),
            samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))
