"""Rear tail-light cluster, left side, of a modern hatchback: wraparound lens that runs
along the rear and bends round onto the body side, two-colour translucent lens (red
tail/brake, clear reverse band, amber indicator band), faceted chrome reflector panel
and chrome bulb reflectors visible through it, black housing with a flange, bayonet
bulb-holder sockets and zinc-plated mounting studs on the back."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

LP = 2.10          # developed length of the lamp along the body
NPATH = 800
LENS_BULGE = 0.045
D_PANEL = 0.100    # faceted reflector depth behind the lens edge
D_BACK = 0.30      # back plate depth

# lamp outline in developed (l, z) coordinates; corners rounded by Chaikin
OUTLINE_PTS = [(0.00, 0.27), (0.07, 0.40), (1.10, 0.515), (1.75, 0.575), (LP, 0.60),
               (LP, 0.02), (1.45, 0.02), (0.55, 0.075), (0.09, 0.13)]
CENTER = (1.05, 0.30)
# lens sections (l0, l1, z0, z1)
REVERSE = (0.17, 0.62, -1.0, 0.245)
INDICATOR = (0.66, 1.12, -1.0, 0.245)
# bulb reflectors: l, z, radius, kind
BOWLS = [(0.40, 0.165, 0.062, "clear"), (0.89, 0.155, 0.062, "amber"),
         (1.47, 0.32, 0.120, "clear"), (0.52, 0.375, 0.075, "clear")]


# ------------------------------------------------------------------ developed surface
def _path():
    pts, heads = [], []
    x, y = 0.95, 0.0
    dl = LP / NPATH
    for k in range(NPATH + 1):
        l = k * dl
        th = math.radians(180 - 82 * C.smoothstep(0.42 * LP, 0.86 * LP, l))
        pts.append((x, y))
        heads.append(th)
        x += math.cos(th) * dl
        y += math.sin(th) * dl
    return pts, heads


PATH, HEAD = _path()


def frame(l):
    """Point on the body line, outward normal (towards the viewer) and tangent."""
    f = max(0.0, min(NPATH - 1e-6, l / LP * NPATH))
    k = int(f)
    a = f - k
    x = PATH[k][0] * (1 - a) + PATH[k + 1][0] * a
    y = PATH[k][1] * (1 - a) + PATH[k + 1][1] * a
    th = HEAD[k] * (1 - a) + HEAD[k + 1] * a
    t = Vector((math.cos(th), math.sin(th), 0))
    n = Vector((-t.y, t.x, 0))
    return Vector((x, y, 0)), n, t


def surf(l, z, off=0.0):
    """off > 0 moves towards the viewer; the lamp leans back towards the top."""
    P, n, _ = frame(l)
    return P + Vector((0, 0, z)) + n * (off - 0.10 * (z - 0.30))


def local_matrix(l, z, off):
    """Frame at (l, z): X = -tangent, Y = up, Z = outward normal."""
    P = surf(l, z, off)
    _, n, t = frame(l)
    M = Matrix(((-t.x, 0, n.x, P.x), (-t.y, 0, n.y, P.y), (0, 1, 0, P.z), (0, 0, 0, 1)))
    # tilt with the lean of the lamp face
    return M @ Matrix.Rotation(math.atan(0.10), 4, "X")


def chaikin(pts, it=4):
    for _ in range(it):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        pts = out
    return pts


def resample(pts, n):
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    lens_ = [math.dist(a, b) for a, b in segs]
    tot = sum(lens_)
    out, acc, j = [], 0.0, 0
    for i in range(n):
        target = tot * i / n
        while acc + lens_[j] < target:
            acc += lens_[j]
            j += 1
        a, b = segs[j]
        f = (target - acc) / lens_[j]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


NU = 320
OUTLINE = resample(chaikin(OUTLINE_PTS, 5), NU)


def offset_outline(d):
    out = []
    n = len(OUTLINE)
    # orientation sign
    area = sum(OUTLINE[i][0] * OUTLINE[(i + 1) % n][1] - OUTLINE[(i + 1) % n][0] * OUTLINE[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    for i in range(n):
        a, b = OUTLINE[i - 1], OUTLINE[(i + 1) % n]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1
        nx, nz = sg * tz / L, -sg * tx / L   # outward
        out.append((OUTLINE[i][0] + d * nx, OUTLINE[i][1] + d * nz))
    return out


def inside(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def orient_to(bm, ref_fn, sign=1):
    """Flip faces so that normals agree with ref_fn(face) (sign>0) on average."""
    bm.normal_update()
    tot = sum(f.normal.dot(ref_fn(f)) * f.calc_area() for f in bm.faces)
    if tot * sign < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)


def outward_ref(f):
    c = f.calc_center_median()
    # nearest path sample in xy
    best = min(range(0, NPATH + 1, 8), key=lambda k: (PATH[k][0] - c.x) ** 2 + (PATH[k][1] - c.y) ** 2)
    _, n, _ = frame(best / NPATH * LP)
    return n


# ------------------------------------------------------------------ parts
def lens(mat):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    nv = 26
    cl, cz = CENTER
    rows = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for (l, z) in OUTLINE:
            L_ = cl + v * (l - cl)
            Z_ = cz + v * (z - cz)
            # pillow: flat over most of the face, rolling off at the edge
            off = LENS_BULGE * (1 - v ** 6) + 0.006
            vt = bm.verts.new(surf(L_, Z_, off))
            row.append((vt, (L_, Z_)))
        rows.append(row)
    for j in range(nv):
        for i in range(NU):
            i2 = (i + 1) % NU
            q = (rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i])
            try:
                f = bm.faces.new([a[0] for a in q])
            except ValueError:
                continue
            for lp, a in zip(f.loops, q):
                lp[uvl].uv = a[1]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    orient_to(bm, outward_ref, 1)
    ob = C.mesh_obj("Lens", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.012
    so.offset = -1
    return C.finalize(ob, angle=70)


def housing(mat):
    rings = [(0.000, -0.002), (0.022, -0.004), (0.036, 0.012), (0.036, 0.07),
             (0.010, 0.22), (-0.03, D_BACK - 0.02), (-0.06, D_BACK)]
    bm = bmesh.new()
    R = []
    for d, depth in rings:
        R.append([bm.verts.new(surf(l, z, -depth)) for (l, z) in offset_outline(d)])
    for j in range(len(R) - 1):
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((R[j][i], R[j][i2], R[j + 1][i2], R[j + 1][i]))
    # back plate: polar grid inside the last ring
    cl, cz = CENTER
    last = offset_outline(rings[-1][0])
    prev = R[-1]
    for j in range(1, 9):
        v = 1 - j / 9
        row = [bm.verts.new(surf(cl + v * (l - cl), cz + v * (z - cz), -D_BACK)) for (l, z) in last]
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((prev[i], prev[i2], row[i2], row[i]))
        prev = row
    c = bm.verts.new(surf(cl, cz, -D_BACK))
    for i in range(NU):
        bm.faces.new((prev[i], prev[(i + 1) % NU], c))
    C.fix_normals(bm)
    ob = C.mesh_obj("Housing", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.014
    so.offset = -1
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def reflector_panel(chrome):
    """Pyramid-faceted chrome panel behind the lens, with openings for the bowls."""
    bm = bmesh.new()
    poly = offset_outline(-0.012)
    cell = 0.027
    l0 = min(p[0] for p in poly); l1 = max(p[0] for p in poly)
    z0 = min(p[1] for p in poly); z1 = max(p[1] for p in poly)
    nl = int((l1 - l0) / cell) + 2
    nz = int((z1 - z0) / cell) + 2
    for a in range(nl):
        for b in range(nz):
            L0 = l0 + a * cell; Z0 = z0 + b * cell
            corners = [(L0, Z0), (L0 + cell, Z0), (L0 + cell, Z0 + cell), (L0, Z0 + cell)]
            if not all(inside(c, poly) for c in corners):
                continue
            cx, cz = L0 + cell / 2, Z0 + cell / 2
            if any(math.hypot(cx - bl, cz - bz) < br + 0.008 for (bl, bz, br, _) in BOWLS):
                continue
            vs = [bm.verts.new(surf(l, z, -D_PANEL)) for (l, z) in corners]
            ap = bm.verts.new(surf(cx, cz, -D_PANEL + 0.008))
            for k in range(4):
                bm.faces.new((vs[k], vs[(k + 1) % 4], ap))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    orient_to(bm, outward_ref, 1)
    ob = C.mesh_obj("Facets", bm, [chrome])
    # flat-shaded facets
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def inner_bezel(mat):
    """Gloss-black inner bezel: a wall just inside the lens edge with an inward lip that
    frames the reflector chamber (and hides where the facet grid stops)."""
    rings = [(-0.004, 0.004), (-0.006, D_PANEL - 0.02), (-0.03, D_PANEL - 0.014), (-0.052, D_PANEL - 0.012)]
    bm = bmesh.new()
    R = [[bm.verts.new(surf(l, z, -depth)) for (l, z) in offset_outline(d)] for d, depth in rings]
    for j in range(len(R) - 1):
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((R[j][i], R[j][i2], R[j + 1][i2], R[j + 1][i]))
    C.fix_normals(bm)
    ob = C.mesh_obj("InnerBezel", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.006
    C.add_bevel(ob, 0.002, segments=1, angle=30)
    return C.finalize(ob, angle=40)


def backing(chrome):
    """Smooth metallised backing just behind the facets (fills the gaps round the bowls)."""
    bm = bmesh.new()
    cl, cz = CENTER
    poly = offset_outline(0.01)
    rows = []
    for j in range(13):
        v = j / 12
        rows.append([bm.verts.new(surf(cl + v * (l - cl), cz + v * (z - cz), -D_PANEL - 0.004)) for (l, z) in poly])
    for j in range(12):
        for i in range(NU):
            i2 = (i + 1) % NU
            try:
                bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    orient_to(bm, outward_ref, 1)
    return C.finalize(C.mesh_obj("Backing", bm, [chrome]), angle=60)


def bowls(chrome, glass, amber, black):
    out = []
    for (l, z, r, kind) in BOWLS:
        f = r * 0.55
        prof = []
        N = 14
        for i in range(N + 1):
            rr = 0.022 + (r + 0.004 - 0.022) * i / N
            prof.append((rr, (rr * rr - (r + 0.004) ** 2) / (4 * f), 0))
        bowl = C.lathe("Bowl", prof, [chrome], steps=72, closed=False)
        so = bowl.modifiers.new("Solid", "SOLIDIFY")
        so.thickness = 0.005
        bowl.matrix_world = local_matrix(l, z, -D_PANEL)
        out.append(C.finalize(bowl, angle=50))
        ring = C.lathe("BowlRing", [(r - 0.002, 0.0, 0), (r + 0.016, 0.0, 0), (r + 0.018, 0.006, 0),
                                    (r + 0.002, 0.008, 0)], [chrome], steps=72)
        ring.matrix_world = local_matrix(l, z, -D_PANEL)
        out.append(C.finalize(ring, angle=50))
        zb = -((r + 0.004) ** 2) / (4 * f)
        k = 0.55 if r < 0.1 else 0.8
        bm_ = glass if kind == "clear" else amber
        bulb = C.lathe("Bulb", [(0.0, zb + 0.12 * k, 0), (0.014 * k, zb + 0.116 * k, 0), (0.024 * k, zb + 0.095 * k, 0),
                                (0.026 * k, zb + 0.05 * k, 0), (0.016 * k, zb + 0.012 * k, 0), (0.0, zb + 0.012 * k, 0)],
                       [bm_], steps=40)
        bulb.matrix_world = local_matrix(l, z, -D_PANEL)
        out.append(C.finalize(bulb, angle=60))
        fil = C.lathe("Filament", [(0.0, zb + 0.075 * k, 0), (0.006 * k, zb + 0.07 * k, 0), (0.006 * k, zb + 0.03 * k, 0),
                                   (0.0, zb + 0.03 * k, 0)], [black], steps=16)
        fil.matrix_world = local_matrix(l, z, -D_PANEL)
        out.append(C.finalize(fil, angle=60))
    return out


def dividers(mat):
    """Inner black bezel walls separating the reverse / indicator / tail chambers."""
    bm = bmesh.new()
    w, depth0, depth1 = 0.010, 0.012, D_PANEL
    segs = [((REVERSE[0] - 0.02, REVERSE[3] + 0.006), (INDICATOR[1] + 0.02, INDICATOR[3] + 0.006)),
            ((0.64, 0.05), (0.64, REVERSE[3] + 0.006)),
            ((INDICATOR[1] + 0.02, 0.025), (INDICATOR[1] + 0.02, INDICATOR[3] + 0.006)),
            ((REVERSE[0] - 0.02, 0.12), (REVERSE[0] - 0.02, REVERSE[3] + 0.006))]
    for (a, b) in segs:
        n = max(2, int(math.dist(a, b) / 0.02))
        dl, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dl, dz)
        pl, pz = -dz / L * w / 2, dl / L * w / 2
        ring_prev = None
        for i in range(n + 1):
            f = i / n
            l, z = a[0] + dl * f, a[1] + dz * f
            ring = [bm.verts.new(surf(l + sl * pl, z + sl * pz, -dd)) for (sl, dd) in
                    ((-1, depth0), (1, depth0), (1, depth1), (-1, depth1))]
            if ring_prev:
                for k in range(4):
                    bm.faces.new((ring_prev[k], ring_prev[(k + 1) % 4], ring[(k + 1) % 4], ring[k]))
            else:
                bm.faces.new(ring[::-1])
            ring_prev = ring
        bm.faces.new(ring_prev)
    C.fix_normals(bm)
    ob = C.mesh_obj("Dividers", bm, [mat])
    C.add_bevel(ob, 0.002, segments=1, angle=30)
    return C.finalize(ob, angle=40)


def sockets(black, rubber):
    out = []
    for (l, z, r, kind) in BOWLS:
        rs = 0.05 if r < 0.1 else 0.07
        M = local_matrix(l, z, -D_BACK + 0.004)
        # local -Z points out of the back
        body = C.lathe("Socket", [(0.0, -0.13, 0), (rs * 0.75, -0.13, 0), (rs * 0.8, -0.125, 0), (rs * 0.8, -0.04, 0),
                                  (rs, -0.035, 0), (rs, -0.0, 0), (0.0, 0.0, 0)], [black], steps=48)
        body.matrix_world = M
        C.add_bevel(body, 0.004, segments=2, angle=30)
        out.append(C.finalize(body, angle=40))
        seal = C.lathe("Seal", [(rs * 0.98, -0.006, 0), (rs * 1.12, -0.006, 0), (rs * 1.14, -0.016, 0),
                                (rs * 1.12, -0.026, 0), (rs * 0.98, -0.026, 0)], [rubber], steps=48)
        seal.matrix_world = M
        out.append(C.finalize(seal, angle=50))
        # bayonet twist wings
        bm = bmesh.new()
        for a in (0, 120, 240):
            Ra = Matrix.Rotation(math.radians(a), 4, "Z")
            C.box_bm(bm, rs * 0.55, 0.016, 0.07, center=(rs * 0.95, 0, -0.08), matrix=Ra)
        wg = C.mesh_obj("Wings", bm, [black])
        wg.matrix_world = M
        C.add_bevel(wg, 0.004, segments=2, angle=30)
        out.append(C.finalize(wg, angle=35))
        # two-pin plug face (dark recess)
        bm = bmesh.new()
        C.box_bm(bm, rs * 0.9, rs * 0.55, 0.01, center=(0, 0, -0.132))
        pf = C.mesh_obj("PlugFace", bm, [rubber])
        pf.matrix_world = M
        out.append(C.finalize(pf, angle=35))
    return out


def studs(zinc, black):
    out = []
    for (l, z) in ((0.30, 0.345), (1.10, 0.45), (1.95, 0.36), (1.75, 0.10)):
        M = local_matrix(l, z, -D_BACK + 0.004)
        prof = [(0.0, 0.0, 0), (0.030, 0.0, 0), (0.030, -0.018, 0)]
        zz = -0.018
        while zz > -0.14:
            prof += [(0.0105, zz, 0), (0.0125, zz - 0.0045, 0)]
            zz -= 0.009
        prof += [(0.0105, -0.145, 0), (0.0085, -0.15, 0), (0.0, -0.15, 0)]
        st = C.lathe("Stud", prof, [zinc], steps=32)
        st.matrix_world = M
        out.append(C.finalize(st, angle=50))
        boss = C.lathe("Boss", [(0.0, 0.004, 0), (0.042, 0.004, 0), (0.038, -0.006, 0), (0.0, -0.006, 0)],
                       [black], steps=40)
        boss.matrix_world = M
        out.append(C.finalize(boss, angle=50))
    # locating pin near the side end
    M = local_matrix(1.98, 0.48, -D_BACK + 0.004)
    pin = C.lathe("Pin", [(0.0, 0.0, 0), (0.022, 0.0, 0), (0.020, -0.08, 0), (0.012, -0.10, 0), (0.0, -0.10, 0)],
                  [black], steps=32)
    pin.matrix_world = M
    out.append(C.finalize(pin, angle=50))
    return out


def lens_material():
    m, nt, _b = C._mat("LensTri")
    nodes = nt.nodes
    for n in list(nodes):
        if n.type == "BSDF_PRINCIPLED":
            nodes.remove(n)
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")

    def glass(col, rough=0.0):
        b = nodes.new("ShaderNodeBsdfPrincipled")
        b.inputs["Base Color"].default_value = col
        b.inputs["Roughness"].default_value = rough
        b.inputs["IOR"].default_value = 1.49
        b.inputs["Transmission Weight"].default_value = 1.0
        return b

    red = glass((0.95, 0.015, 0.012, 1))
    clear = glass((1, 1, 1, 1), rough=0.12)  # reverse optic: lightly frosted, reads silver-white
    amb = glass((1.0, 0.36, 0.015, 1))
    uv = nodes.new("ShaderNodeUVMap")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])

    def region(l0, l1, z0, z1):
        acc = None
        for (sock, val, op) in ((0, l0, "GREATER_THAN"), (0, l1, "LESS_THAN"), (1, z0, "GREATER_THAN"), (1, z1, "LESS_THAN")):
            mth = nodes.new("ShaderNodeMath")
            mth.operation = op
            nt.links.new(sep.outputs[sock], mth.inputs[0])
            mth.inputs[1].default_value = val
            if acc is None:
                acc = mth.outputs[0]
            else:
                mul = nodes.new("ShaderNodeMath")
                mul.operation = "MULTIPLY"
                nt.links.new(acc, mul.inputs[0])
                nt.links.new(mth.outputs[0], mul.inputs[1])
                acc = mul.outputs[0]
        return acc

    m1 = nodes.new("ShaderNodeMixShader")
    nt.links.new(region(*REVERSE), m1.inputs[0])
    nt.links.new(red.outputs[0], m1.inputs[1])
    nt.links.new(clear.outputs[0], m1.inputs[2])
    m2 = nodes.new("ShaderNodeMixShader")
    nt.links.new(region(*INDICATOR), m2.inputs[0])
    nt.links.new(m1.outputs[0], m2.inputs[1])
    nt.links.new(amb.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], out.inputs["Surface"])
    return m


def matte_floor_in_reflections():
    """The shadow-catcher floor is lit white; mirrored in the lens it would wash the
    lower half out in pink. Hide it from glossy rays only (the contact shadow stays):
    C.shoot creates the floor right before the studio lights, so hook that helper."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


def build():
    black = C.mat_black_plastic("HousingPP", rough=0.5, color=0.024)
    inner = C.mat_black_plastic("InnerBezel", rough=0.3, color=0.015, tex=False)
    chrome = C.principled("VacMetal", (0.93, 0.93, 0.94), metallic=1.0, rough=0.05)
    satin = C.principled("VacMetalSatin", (0.85, 0.85, 0.86), metallic=1.0, rough=0.22)
    glass = C.mat_clear("BulbGlass", ior=1.52)
    amber = C.mat_clear("BulbAmber", ior=1.5)
    C._set(next(n for n in amber.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Base Color", (1.0, 0.33, 0.02, 1))
    rubber = C.mat_rubber("SealRubber")
    zinc = C.principled("ZincYellow", (0.78, 0.70, 0.42), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=500, strength=0.08, distance=0.0005, rough_var=0.06)
    objs = [lens(lens_material()), housing(black), reflector_panel(chrome), backing(satin), dividers(inner),
            inner_bezel(inner)]
    objs += bowls(chrome, glass, amber, inner)
    objs += sockets(black, rubber)
    objs += studs(zinc, black)
    return objs


if __name__ == "__main__":
    matte_floor_in_reflections()
    C.clear()
    objs = build()
    C.shoot("fanale", objs, "fanale.py",
            "left rear tail-light cluster: wraparound red lens with clear reverse and amber indicator bands, "
            "faceted chrome reflectors, black housing with bulb-holder sockets and mounting studs",
            az=28, el=20, lens=70, fill=0.86, samples=int(os.environ.get("SAMPLES", 128)))
