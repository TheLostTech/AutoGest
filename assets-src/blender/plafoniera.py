"""Interior dome light (roof lamp): grey grained plastic housing with a domed frosted opal
lens with a fine pyramid stipple, three-position rocker switch in a recess at one end, pry
notch at the other, spring clips and a festoon bulb holder on the back."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# ----------------------------------------------------------------- lamp helpers
# (1 unit = 100 mm; the lamp is built lying flat with its lens facing +Z, then tilted)
TAU = math.tau
T = Matrix.Translation
PREV = os.environ.get("PREV")


def rrect(w, h, r, n=10, cx=0.0, cy=0.0):
    r = max(0.0015, min(r, w / 2 - 1e-4, h / 2 - 1e-4))
    pts = []
    for qx, qy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return pts


def chaikin(pts, it=4):
    for _ in range(it):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        pts = out
    return pts


def fillet_poly(pts, radii, n=10):
    """Polygon with each corner rounded (quadratic blend over a tangent length per corner)."""
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    out = []
    m = len(pts)
    for i in range(m):
        p, a, b = Vector(pts[i]), Vector(pts[i - 1]), Vector(pts[(i + 1) % m])
        u, w = (a - p), (b - p)
        t = min(radii[i], u.length * 0.49, w.length * 0.49)
        s0, s1 = p + u.normalized() * t, p + w.normalized() * t
        for k in range(n + 1):
            q = k / n
            c = s0 * (1 - q) ** 2 + p * 2 * q * (1 - q) + s1 * q * q
            out.append((c.x, c.y))
    return out


def resample(poly, n):
    L = [0.0]
    P = list(poly) + [poly[0]]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + math.dist(a, b))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


def ccw(poly):
    a = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))
    return list(poly) if a > 0 else list(reversed(poly))


def offset_poly(poly, d):
    """Offset a smooth CCW polygon outward by d (negative = inward, keep |d| < corner radius)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = Vector((p1[0] - p0[0], p1[1] - p0[1])).normalized()
        e2 = Vector((p2[0] - p1[0], p2[1] - p1[1])).normalized()
        n1 = Vector((e1.y, -e1.x))
        n2 = Vector((e2.y, -e2.x))
        m = (n1 + n2)
        m = m.normalized() if m.length > 1e-9 else n1
        s = d / max(0.35, m.dot(n1))
        out.append((p1[0] + m.x * s, p1[1] + m.y * s))
    return out


def spine_q(p, spine):
    (x0, y0), (x1, y1) = spine
    vx, vy = x1 - x0, y1 - y0
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - x0) * vx + (p[1] - y0) * vy) / L2))
    return (x0 + vx * t, y0 + vy * t)


def inset(poly, spine, dabs=0.0, frac=0.0):
    """Move each point toward the shape's spine: an absolute distance plus a fraction of the rest."""
    out = []
    for p in poly:
        q = spine_q(p, spine)
        L = math.dist(p, q)
        if L < 1e-9:
            out.append(p)
            continue
        d = min(L * 0.985, dabs + frac * max(0.0, L - dabs))
        out.append((p[0] + (q[0] - p[0]) * d / L, p[1] + (q[1] - p[1]) * d / L))
    return out


def inside(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def orient_out(bm, ref):
    """Flip all faces if, on average, they point toward ref (a Vector inside the shape)."""
    bm.normal_update()
    s = sum((f.calc_center_median() - ref).dot(f.normal) * f.calc_area() for f in bm.faces)
    if s < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)


def loft_rings(name, rings, mats, cap0=True, cap1=True, ref=None, mi=None, closed=False):
    """rings: [(poly2d, z)] all with the same point count -> skinned (optionally capped) mesh.
    closed=True joins the last ring back to the first (a ring-shaped solid, no caps)."""
    bm = bmesh.new()
    R = [[bm.verts.new((x, y, z)) for (x, y) in poly] for (poly, z) in rings]
    m = len(R[0])
    if closed:
        R.append(R[0])
        cap0 = cap1 = False
    for i in range(len(R) - 1):
        a, b = R[i], R[i + 1]
        for k in range(m):
            k2 = (k + 1) % m
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            if mi:
                f.material_index = mi[i]
    if cap0:
        bm.faces.new(R[0][::-1])
    if cap1:
        bm.faces.new(R[-1])
    if closed:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return C.mesh_obj(name, bm, mats)
    if ref is None:
        zs = [z for (_p, z) in rings]
        cx = sum(x for x, _y in rings[0][0]) / m
        cy = sum(y for _x, y in rings[0][0]) / m
        ref = Vector((cx, cy, (min(zs) + max(zs)) / 2))
    orient_out(bm, ref)
    return C.mesh_obj(name, bm, mats)


def slab(name, poly, rings, mat, bevel=0.006, seg=2, angle=32, closed=False):
    """Solid from offset rings [(d, z)] of one outline (d>0 outward); closed=True -> ring solid."""
    ob = loft_rings(name, [(offset_poly(poly, d), z) for (d, z) in rings], [mat], closed=closed)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle)


def lens_shell(name, poly, spine, mat, zedge, bulge, rr=0.02, thick=0.018, ns=14, z0=0.0):
    """Lens: straight skirt from z0 to zedge, rounded shoulder, domed top toward the spine."""
    prof = [(0.0, 0.0, z0), (0.0, 0.0, zedge)]
    for k in range(1, 5):
        a = math.radians(90 * k / 4)
        prof.append((rr * (1 - math.cos(a)), 0.0, zedge + rr * math.sin(a)))
    for k in range(1, ns + 1):
        s = k / ns
        prof.append((rr, s, zedge + rr + bulge * (1 - (1 - s) ** 2)))
    rings = [(inset(poly, spine, a, f), z) for (a, f, z) in prof]
    ob = loft_rings(name, rings, [mat], cap0=False, cap1=True,
                    ref=Vector((0, 0, z0 - 0.5)))
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = thick
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def dish(name, poly, spine, mat, depth, z0=0.0, ns=12, thick=0.006, power=2.0):
    """Reflector dish dropping from the outline (z0) toward the spine (z0 - depth)."""
    rings = []
    for k in range(ns + 1):
        s = k / ns
        rings.append((inset(poly, spine, 0.0, s * 0.985), z0 - depth * (1 - (1 - s) ** power)))
    ob = loft_rings(name, rings, [mat], cap0=False, cap1=True, ref=Vector((0, 0, z0 + 1.0)))
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = thick
    so.offset = -1
    return C.finalize(ob, angle=40)


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2, angle=32):
    """Extrude a 2D polygon along local Z, optional boolean holes [(r, cx, cy)] through it."""
    ob = loft_rings(name, [(poly, z0), (poly, z1)], [mat])
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
        m = C.add_boolean(ob, cut)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=[cut] if cut else [])


def boxes(name, specs, mat, bevel=0.006, seg=2, M=None, angle=32):
    """specs: [(sx, sy, sz, center[, matrix])]"""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if M is not None:
        ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle)


def lathe_at(name, prof, mats, M, steps=48, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def catmull(ctrl, n=80):
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    segs = len(P) - 3
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        k = max(2, n // segs)
        for j in range(k):
            t = j / k
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def tube(name, pts, r, mat, res=3, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def strip(name, pts, side, w, t, mat, bevel=0.0015):
    """Flat sheet-metal strip of width w (along `side`) and thickness t following pts."""
    side = Vector(side).normalized()
    fr = []
    sec = [(-w / 2, -t / 2), (w / 2, -t / 2), (w / 2, t / 2), (-w / 2, t / 2)]
    n = len(pts)
    for i in range(n):
        a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        tg = (Vector(b) - Vector(a)).normalized()
        V = tg.cross(side).normalized()
        fr.append((Vector(pts[i]), side, V, sec))
    bm = bmesh.new()
    C.sweep(bm, fr)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=50)
    return C.finalize(ob, angle=45)


def bent(start, d, n, segs, step=0.01):
    """Planar centre-line: segs = [('L', len) | ('A', radius, deg)] bending toward n."""
    P = Vector(start)
    d = Vector(d).normalized()
    n = Vector(n).normalized()
    b = d.cross(n).normalized()
    pts = [P.copy()]
    for s in segs:
        if s[0] == "L":
            k = max(1, int(s[1] / step))
            for i in range(1, k + 1):
                pts.append(P + d * (s[1] * i / k))
            P = P + d * s[1]
        else:
            R, ang = s[1], math.radians(s[2])
            Cc = P + n * R
            k = max(3, int(R * abs(ang) / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, b)
                pts.append(Cc + rot @ (P - Cc))
            rot = Matrix.Rotation(ang, 3, b)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts


def facet_panel(name, poly, cell, depth, z, mat, kind="square", margin=0.0):
    """Moulded optic of small pyramids ('square') or hexagonal cube corners ('hex') inside poly."""
    bm = bmesh.new()
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    lim = offset_poly(poly, -margin) if margin else poly
    if kind == "square":
        nx = int((max(xs) - min(xs)) / cell) + 2
        ny = int((max(ys) - min(ys)) / cell) + 2
        x0 = (min(xs) + max(xs)) / 2 - nx * cell / 2
        y0 = (min(ys) + max(ys)) / 2 - ny * cell / 2
        for i in range(nx):
            for j in range(ny):
                cx, cy = x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell
                h = cell / 2
                cs = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
                if not all(inside(c, lim) for c in cs):
                    continue
                v = [bm.verts.new((c[0], c[1], z)) for c in cs]
                ap = bm.verts.new((cx, cy, z + depth))
                for k in range(4):
                    bm.faces.new((v[k], v[(k + 1) % 4], ap))
    else:
        R = cell / 2
        dx = math.sqrt(3) * R
        dy = 1.5 * R
        nx = int((max(xs) - min(xs)) / dx) + 3
        ny = int((max(ys) - min(ys)) / dy) + 3
        x0 = (min(xs) + max(xs)) / 2 - nx * dx / 2
        y0 = (min(ys) + max(ys)) / 2 - ny * dy / 2
        for j in range(ny):
            for i in range(nx):
                cx = x0 + i * dx + (dx / 2 if j % 2 else 0.0)
                cy = y0 + j * dy
                cs = [(cx + R * math.cos(math.radians(90 + 60 * k)), cy + R * math.sin(math.radians(90 + 60 * k)))
                      for k in range(6)]
                if not all(inside(c, lim) for c in cs):
                    continue
                v = [bm.verts.new((c[0], c[1], z - (0.0 if k % 2 == 0 else depth * 0.5))) for k, c in enumerate(cs)]
                ap = bm.verts.new((cx, cy, z - depth))
                for k in range(6):
                    bm.faces.new((v[k], v[(k + 1) % 6], ap))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = C.link(bpy.data.objects.new(name, me))
    me.materials.append(mat)
    return ob


# ----------------------------------------------------------------- shader bits
def _mn(nt, op, a, b=None, clamp=False):
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


def optic_height(nt, pattern, scale, rot=0.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    X, Y = sep.outputs["X"], sep.outputs["Y"]
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        X, Y = (_mn(nt, "ADD", _mn(nt, "MULTIPLY", X, c), _mn(nt, "MULTIPLY", Y, -s)),
                _mn(nt, "ADD", _mn(nt, "MULTIPLY", X, s), _mn(nt, "MULTIPLY", Y, c)))
    x = _mn(nt, "MULTIPLY", X, scale)
    y = _mn(nt, "MULTIPLY", Y, scale)

    def tri(v):
        return _mn(nt, "ABSOLUTE", _mn(nt, "SUBTRACT", _mn(nt, "FRACT", v), 0.5))
    if pattern == "pyramid":
        return _mn(nt, "ADD", tri(x), tri(y))
    if pattern == "ribs":
        return tri(x)
    if pattern == "hribs":
        return tri(y)
    if pattern == "pillow":
        a = _mn(nt, "ABSOLUTE", _mn(nt, "SINE", _mn(nt, "MULTIPLY", x, math.pi)))
        b = _mn(nt, "ABSOLUTE", _mn(nt, "SINE", _mn(nt, "MULTIPLY", y, math.pi)))
        return _mn(nt, "POWER", _mn(nt, "MULTIPLY", a, b), 0.5)
    raise ValueError(pattern)


def bsdf_of(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def lens_mat(name, col, rough=0.0, ior=1.49, pattern=None, scale=40.0, strength=0.35, rot=0.0):
    m = C.principled(name, col, rough=rough, IOR=ior)
    b = bsdf_of(m)
    C._set(b, "Transmission Weight", 1.0)
    if pattern:
        nt = m.node_tree
        h = optic_height(nt, pattern, scale, rot)
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = strength
        bump.inputs["Distance"].default_value = 0.25 / scale
        nt.links.new(h, bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def common_mats():
    M = {}
    M["black"] = C.mat_black_plastic("HousingPP", rough=0.5, color=0.024)
    M["inner"] = C.mat_black_plastic("InnerBlack", rough=0.3, color=0.015, tex=False)
    M["chrome"] = C.principled("VacMetal", (0.93, 0.93, 0.94), metallic=1.0, rough=0.05)
    M["satin"] = C.principled("VacMetalSatin", (0.85, 0.85, 0.86), metallic=1.0, rough=0.22)
    zinc = C.principled("ZincSteel", (0.62, 0.63, 0.64), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=500, strength=0.08, distance=0.0005, rough_var=0.06)
    M["zinc"] = zinc
    M["glass"] = C.mat_clear("BulbGlass", ior=1.52)
    M["copper"] = C.principled("Copper", (0.80, 0.50, 0.32), metallic=1.0, rough=0.3)
    M["tin"] = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    M["brass"] = C.principled("BrassBase", (0.78, 0.62, 0.36), metallic=1.0, rough=0.28)
    M["filament"] = C.principled("Filament", (0.55, 0.45, 0.35), metallic=1.0, rough=0.35)
    M["wire"] = C.principled("WireBlack", (0.02, 0.02, 0.022), rough=0.35, Coat_Weight=0.3)
    M["rubber"] = C.mat_rubber("SealRubber")
    foam = C.principled("FoamGasket", (0.03, 0.03, 0.03), rough=0.95)
    C.add_noise_bump(foam, scale=900, strength=0.35, distance=0.001)
    M["foam"] = foam
    return M


def matte_floor_in_reflections():
    """Hide the shadow-catcher floor from glossy rays only (as in fanale.py), so glossy
    lenses do not mirror it as a grey band; the contact shadow stays."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


# ----------------------------------------------------------------- stock sub-parts
def w5w_bulb(M, mats):
    """Glass wedge-base bulb, standing on local +Z."""
    g, fil, cu = mats["glass"], mats["filament"], mats["copper"]
    out = [lathe_at("W5WGlass", [(0.0, 0.205, 0), (0.022, 0.2, 0), (0.042, 0.18, 0), (0.048, 0.15, 0), (0.048, 0.09, 0),
                                 (0.042, 0.07, 0), (0.030, 0.06, 0), (0.0, 0.06, 0)], [g], M, steps=40, angle=60)]
    out.append(boxes("W5WWedge", [(0.095, 0.03, 0.07, (0, 0, 0.03))], g, bevel=0.006, M=M))
    out.append(boxes("W5WLeads", [(0.008, 0.034, 0.06, (sx * 0.03, 0, 0.03)) for sx in (-1, 1)], cu, bevel=0.0, M=M))
    pts = [Vector((-0.016 + 0.032 * i / 60, 0.004 * math.cos(TAU * 7 * i / 60), 0.15 + 0.004 * math.sin(TAU * 7 * i / 60)))
           for i in range(61)]
    pts = [M @ p for p in pts]
    out.append(tube("W5WCoil", pts, 0.0015, fil, res=1))
    for sx in (-1, 1):
        out.append(tube("W5WPost", [M @ Vector((sx * 0.016, 0, 0.15)), M @ Vector((sx * 0.02, 0, 0.06))], 0.0016, fil, res=1))
    return out


def p21w_bulb(M, mats):
    """BA15s single-filament bulb, base at local z=0, glass toward +Z."""
    g, fil, br = mats["glass"], mats["filament"], mats["brass"]
    out = [lathe_at("P21Base", [(0.0, 0.0, 0), (0.035, 0.0, 0), (0.05, 0.012, 0), (0.074, 0.02, 0), (0.074, 0.18, 0),
                                (0.07, 0.19, 0), (0.0, 0.19, 0)], [br], M, steps=48)]
    out.append(boxes("P21Pins", [(0.04, 0.025, 0.025, (sx * 0.085, 0, 0.05)) for sx in (-1, 1)], br, bevel=0.004, M=M))
    out.append(lathe_at("P21Glass", [(0.0, 0.47, 0), (0.05, 0.462, 0), (0.095, 0.43, 0), (0.125, 0.37, 0), (0.13, 0.30, 0),
                                     (0.11, 0.22, 0), (0.07, 0.18, 0), (0.0, 0.18, 0)], [g], M, steps=48, angle=60))
    pts = [M @ Vector((-0.025 + 0.05 * i / 80, 0.006 * math.cos(TAU * 9 * i / 80), 0.36 + 0.006 * math.sin(TAU * 9 * i / 80)))
           for i in range(81)]
    out.append(tube("P21Coil", pts, 0.0022, fil, res=1))
    for sx in (-1, 1):
        out.append(tube("P21Post", [M @ Vector((sx * 0.025, 0, 0.36)), M @ Vector((sx * 0.03, 0, 0.19))], 0.0025, fil, res=1))
    return out


def twist_socket(M, mats, r=0.11, h=0.16, grip=True):
    """Black twist-lock bulb holder seen from the back; local +Z points out of the lamp (backwards)."""
    blk = mats["black"]
    out = [lathe_at("SockBody", [(0.0, 0.0, 0), (r + 0.035, 0.0, 0), (r + 0.035, 0.025, 0), (r, 0.035, 0), (r * 0.82, h, 0),
                                 (0.0, h, 0)], [blk], M, steps=48, bevel=0.004)]
    for k in range(3):
        R = M @ Matrix.Rotation(TAU * k / 3 + 0.4, 4, "Z")
        out.append(boxes("SockLug", [(0.06, 0.05, 0.028, (r + 0.045, 0, 0.012))], blk, bevel=0.006, M=R))
    if grip:
        out.append(boxes("SockGrip", [(r * 1.8, 0.03, 0.08, (0, 0, h + 0.03))], blk, bevel=0.008, M=M))
    return out


def connector(M, mats, w=0.20, d=0.11, h=0.17):
    """Connector shell, mouth toward local -Z; latch on +Y."""
    blk = mats["black"]
    bm = bmesh.new()
    C.box_bm(bm, w, d, h, center=(0, 0, 0))
    sh = C.mesh_obj("Conn", bm, [blk])
    sh.matrix_world = M
    cb = bmesh.new()
    C.box_bm(cb, w - 0.035, d - 0.035, h, center=(0, 0, -h * 0.35))
    cut = C.mesh_obj("ConnCut", cb, [blk])
    cut.matrix_world = M
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out = [C.finalize(sh, angle=35, remove=[cut])]
    out.append(boxes("ConnLatch", [(w * 0.3, 0.02, h * 0.55, (0, d / 2 + 0.01, h * 0.05))], blk, bevel=0.005, M=M))
    out.append(boxes("ConnPins", [(0.012, 0.006, h * 0.6, (sx * w * 0.18, 0, -h * 0.1)) for sx in (-1, 1)], mats["tin"],
                     bevel=0.0, M=M))
    return out


HW, HH, HR = 1.50, 0.78, 0.16          # housing 150 x 78 mm
LW, LH, LR = 0.86, 0.46, 0.08          # lens
LX = -0.17                              # lens centre offset along X
SX = 0.50                               # switch centre


def grained(name, col, rough=0.55, scale=320.0):
    """Moulded interior plastic with a fine leather-like grain (as sedile.py)."""
    m = C.principled(name, col, rough=rough)
    nt = m.node_tree
    b = bsdf_of(m)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = scale
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 40.0
    h = _mn(nt, "ADD", vo.outputs["Distance"], _mn(nt, "MULTIPLY", nz.outputs["Fac"], 0.3))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.0006
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.06
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def opal(name):
    m = C.principled(name, (0.93, 0.93, 0.90), rough=0.32, Subsurface_Weight=1.0, Subsurface_Scale=0.04)
    b = bsdf_of(m)
    try:
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.95, 0.85)
    except Exception:
        pass
    nt = m.node_tree
    h = optic_height(nt, "pyramid", 55.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def build():
    mats = common_mats()
    grey = grained("GreyPP", C.srgb("#8D8C88"), rough=0.55)
    dgrey = grained("DarkGreyPP", C.srgb("#3A3B3D"), rough=0.45, scale=500.0)
    lensm = opal("OpalLens")
    zinc = mats["zinc"]
    hp = ccw(rrect(HW, HH, HR, n=12))
    out = []
    # housing: thin edge, sloping shoulder, flat face
    rings = [(offset_poly(hp, d), z) for d, z in ((0.0, -0.06), (0.0, 0.0), (-0.012, 0.03), (-0.04, 0.055),
                                                     (-0.08, 0.066), (-0.12, 0.068))]
    hs = loft_rings("Housing", rings, [grey])
    cb = bmesh.new()
    C.box_bm(cb, 0.24, 0.32, 0.2, center=(SX, 0, 0.068 + 0.1 - 0.022))       # switch recess
    C.box_bm(cb, 0.04, 0.16, 0.06, center=(-HW / 2 + 0.008, 0, 0.0))          # pry notch
    cut = C.mesh_obj("Cut", cb, [grey])
    m = C.add_boolean(hs, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(hs, 0.006, segments=2, angle=30)
    out.append(C.finalize(hs, angle=32, remove=[cut]))
    # raised bezel ring that holds the lens
    lp = ccw(rrect(LW, LH, LR, n=10, cx=LX))
    out.append(slab("Bezel", lp, [(0.03, 0.06), (0.03, 0.074), (0.018, 0.084), (0.0, 0.084), (-0.004, 0.06)], grey,
                    bevel=0.003, closed=True))
    out.append(lens_shell("Lens", lp, ((LX - LW / 2 + LH / 2, 0), (LX + LW / 2 - LH / 2, 0)), lensm,
                          zedge=0.09, bulge=0.035, rr=0.02, thick=0.02, z0=0.06))
    # rocker switch: three-position (on / door / off), sitting tilted in its recess
    Mr = T((SX, 0, 0.06)) @ Matrix.Rotation(math.radians(9), 4, "X")
    out.append(boxes("RockerBase", [(0.17, 0.26, 0.03, (0, 0, -0.01))], dgrey, bevel=0.006, M=T((SX, 0, 0.046))))
    rk = loft_rings("Rocker", [(rrect(0.15, 0.24, 0.025, n=6), 0.0), (rrect(0.15, 0.24, 0.025, n=6), 0.03),
                               (rrect(0.135, 0.225, 0.02, n=6), 0.042)], [dgrey])
    for v in rk.data.vertices:
        if v.co.z > 0.02:
            v.co.z += 0.022 * (abs(v.co.y) / 0.12) ** 2     # concave saddle so it reads as a rocker
    rk.matrix_world = Mr
    C.add_bevel(rk, 0.005, segments=2, angle=30)
    out.append(C.finalize(rk, angle=35))
    white = C.principled("SymbolWhite", (0.8, 0.8, 0.78), rough=0.4)
    out.append(boxes("Mark", [(0.014, 0.05, 0.004, (0, 0.075, 0.066))], white, bevel=0.0, M=Mr))
    out.append(lathe_at("MarkO", [(0.012, 0.0, 0), (0.02, 0.0, 0), (0.02, 0.004, 0), (0.012, 0.004, 0)], [white],
                        Mr @ T((0, -0.08, 0.064)), steps=24))
    # spring clips on the long sides, just showing past the edge
    for sy in (-1, 1):
        pts = catmull([(0.0, sy * (HH / 2 - 0.06), -0.06), (0.0, sy * (HH / 2 - 0.02), -0.10),
                       (0.0, sy * (HH / 2 + 0.03), -0.075), (0.0, sy * (HH / 2 + 0.01), -0.02)], n=30)
        for x in (-0.45, 0.45):
            out.append(strip("Clip", [p + Vector((x, 0, 0)) for p in pts], (1, 0, 0), 0.10, 0.006, zinc))
    out.append(boxes("BackBox", [(1.1, 0.5, 0.05, (LX + 0.1, 0, -0.085))], grey, bevel=0.01))
    return out


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.transform_all(objs, Matrix.Rotation(math.radians(-22), 4, "Z") @ Matrix.Rotation(math.radians(14), 4, "X"))
    C.shoot("plafoniera", objs, "plafoniera.py",
            "car interior dome light: grey plastic housing with domed frosted lens and a three-position rocker switch",
            az=30, el=36, lens=70, fill=0.84,
            res=(512, 512) if PREV else (1024, 1024), samples=32 if PREV else 128)
