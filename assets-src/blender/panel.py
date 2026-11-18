"""Helpers shared by the painted body-panel packshots (porta, cofano, paraurti):
the common metallic body paint, B-spline / filleted outlines, smooth structured
patches built from analytic surfaces, swept trims and rounded solids."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Vector, Matrix
import common as C


# ----------------------------------------------------------------- materials
def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def body_paint(name="BodyPaint"):
    """Mid metallic grey, clear-coated: identical on every body panel of the catalogue."""
    m = C.mat_paint(name, C.srgb("#62666B"), rough=0.36, coat=1.0, metallic=0.75)
    C._set(bsdf(m), "Coat Roughness", 0.025)
    C.add_noise_bump(m, scale=2600, strength=0.05, distance=0.0002, rough_var=0.05)  # flake
    return m


def ecoat(name="Ecoat", v=0.045, rough=0.45):
    m = C.principled(name, (v, v, v * 1.06), rough=rough)
    C.add_noise_bump(m, scale=500, strength=0.05, distance=0.0005, rough_var=0.04)
    return m


def textured_black(name="TexturedPP", rough=0.62, v=0.02):
    """Unpainted, grained black polypropylene (bumper trims, mirror sail)."""
    m = C.principled(name, (v, v, v * 1.05), rough=rough)
    C.add_noise_bump(m, scale=650, strength=0.35, distance=0.0006, detail=4.0, rough_var=0.08)
    return m


# ----------------------------------------------------------------- scalar helpers
def softplus(x, s):
    t = x / s
    if t > 30:
        return x
    if t < -30:
        return 0.0
    return s * math.log1p(math.exp(t))


def bump(r2):
    """C1 bell: 1 at r2=0, 0 for r2>=1."""
    return (1 - r2) ** 2 if r2 < 1 else 0.0


def sstep(a, b, x):
    return C.smoothstep(a, b, x)


def lerp(a, b, t):
    return a + (b - a) * t


# ----------------------------------------------------------------- curves
def resample(pts, n, closed=False):
    P = [Vector(p) for p in pts]
    if closed:
        P = P + [P[0]]
    acc = [0.0]
    for i in range(1, len(P)):
        acc.append(acc[-1] + (P[i] - P[i - 1]).length)
    tot = acc[-1]
    cnt = n if closed else n - 1
    out = []
    k = 0
    for j in range(n):
        s = tot * j / cnt
        while k < len(acc) - 2 and acc[k + 1] < s:
            k += 1
        seg = acc[k + 1] - acc[k]
        t = 0.0 if seg < 1e-12 else (s - acc[k]) / seg
        out.append(P[k].lerp(P[k + 1], min(1.0, max(0.0, t))))
    return out


def bspline(ctrl, n=400, closed=False):
    """Uniform cubic B-spline (C2) of a control polygon, resampled by arc length."""
    P = [Vector(c) for c in ctrl]
    if closed:
        seq = P + P[:3]
        segs = len(P)
    else:
        seq = [P[0], P[0]] + P + [P[-1], P[-1]]
        segs = len(seq) - 3
    m = max(8, (n * 6) // segs)
    out = []
    for k in range(segs):
        p0, p1, p2, p3 = seq[k:k + 4]
        for j in range(m):
            t = j / m
            t2, t3 = t * t, t * t * t
            b0 = (1 - t) ** 3 / 6
            b1 = (3 * t3 - 6 * t2 + 4) / 6
            b2 = (-3 * t3 + 3 * t2 + 3 * t + 1) / 6
            b3 = t3 / 6
            out.append(p0 * b0 + p1 * b1 + p2 * b2 + p3 * b3)
    if not closed:
        out.append(P[-1])
    return resample(out, n, closed)


def rounded(corners, radii, closed=True, seg=16):
    """Polyline with each corner replaced by a quadratic-Bezier fillet of size radius."""
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


def normals2d(pts, closed=False):
    """Left normals (-ty, tx) of a 2D polyline."""
    n = len(pts)
    out = []
    for i in range(n):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        out.append(Vector((-t.y, t.x)))
    return out


def offset2d(pts, d, closed=False):
    return [p + nn * d for p, nn in zip(pts, normals2d(pts, closed))]


def signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        p, q = pts[i - 1], pts[i]
        a += p.x * q.y - q.x * p.y
    return a / 2


# ----------------------------------------------------------------- meshes
def orient(bm, want):
    """want: Vector or f(center)->Vector; flips all faces if they point the other way."""
    bm.normal_update()
    s = 0.0
    for f in bm.faces:
        c = f.calc_center_median()
        w = want(c) if callable(want) else want
        s += f.normal.dot(w) * f.calc_area()
    if s < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))


def grid_bm(rows, closed_u=False, mat=0, bm=None):
    bm = bm or bmesh.new()
    V = [[bm.verts.new(p) for p in row] for row in rows]
    nu = len(V[0])
    for j in range(len(V) - 1):
        a, b = V[j], V[j + 1]
        for i in range(nu if closed_u else nu - 1):
            i2 = (i + 1) % nu
            try:
                f = bm.faces.new((a[i], a[i2], b[i2], b[i]))
                f.material_index = mat
            except ValueError:
                pass
    return bm


def clean(bm):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    return bm


def grid_obj(name, rows, mats, want, closed_u=False):
    bm = clean(grid_bm(rows, closed_u))
    orient(bm, want)
    return C.mesh_obj(name, bm, mats)


def fan_rows(poly, center, nv, lift, power=1.5):
    """Rows from a pole at center out to the closed 2D outline poly; lift(Vector2)->Vector3."""
    rows = []
    for j in range(nv + 1):
        t = j / nv
        s = 1 - (1 - t) ** power
        rows.append([lift(center + (p - center) * s) for p in poly])
    return rows


def fan_obj(name, poly, center, nv, lift, mats, want, power=1.5):
    return grid_obj(name, fan_rows(poly, center, nv, lift, power), mats, want, closed_u=True)


def solidify(ob, t, offset=-1.0, inner=0, rim=0, even=False):
    m = ob.modifiers.new("Solid", "SOLIDIFY")
    m.thickness = t
    m.offset = offset
    m.use_rim = True
    m.use_even_offset = even
    m.use_quality_normals = True
    m.material_offset = inner
    m.material_offset_rim = rim
    return m


def surf_normal(lift, p, eps=1e-4, sign_ref=None):
    """Unit normal of the surface lift(Vector2) at 2D point p; flipped to agree with sign_ref."""
    du = lift(p + Vector((eps, 0))) - lift(p - Vector((eps, 0)))
    dv = lift(p + Vector((0, eps))) - lift(p - Vector((0, eps)))
    n = du.cross(dv).normalized()
    if sign_ref is not None and n.dot(sign_ref) < 0:
        n = -n
    return n


def frames_on_surface(path2, lift, out_ref, closed=False, side_sign=1.0):
    """Sweep frames (P, A, B) for a 2D path lying on surface lift: A = in-surface left
    normal of the path (times side_sign), B = surface normal (towards out_ref)."""
    nrm = normals2d(path2, closed)
    fr = []
    for p, nn in zip(path2, nrm):
        P = lift(p)
        A = (lift(p + nn * 1e-3 * side_sign) - P).normalized()
        B = surf_normal(lift, p, sign_ref=out_ref)
        A = (A - B * A.dot(B)).normalized()
        fr.append((P, A, B))
    return fr


def tube_bm(bm, frames, sec, closed=False, cap=True, mat=0):
    """Sweep the closed 2D section sec [(a, b), ...] along frames [(P, A, B), ...]."""
    rings = [[bm.verts.new(P + A * a + B * b) for (a, b) in sec] for (P, A, B) in frames]
    m = len(sec)
    n = len(rings)
    faces = []
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(m):
            k2 = (k + 1) % m
            faces.append(bm.faces.new((r0[k], r0[k2], r1[k2], r1[k])))
    if cap and not closed:
        faces.append(bm.faces.new(rings[0][::-1]))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def tube_obj(name, frames, sec, mats, closed=False, cap=True, smooth_angle=40, bevel=None):
    bm = bmesh.new()
    tube_bm(bm, frames, sec, closed, cap)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=smooth_angle)


def path_frames(pts, up, closed=False):
    """Frames along a 3D polyline: B = up projected off the tangent, A = T x B."""
    n = len(pts)
    fr = []
    for i in range(n):
        if closed:
            T = pts[(i + 1) % n] - pts[i - 1]
        else:
            T = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        T.normalize()
        u = up(pts[i]) if callable(up) else Vector(up)
        B = (u - T * u.dot(T)).normalized()
        A = T.cross(B)
        fr.append((pts[i], A, B))
    return fr


def circle(r, n=16):
    return [(r * math.cos(math.tau * k / n), r * math.sin(math.tau * k / n)) for k in range(n)]


def rrect(a0, a1, b0, b1, r, seg=4):
    """Rounded rectangle section in (a, b)."""
    pts = rounded([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], [r] * 4, closed=True, seg=seg)
    return [(p.x, p.y) for p in pts]


def superellipsoid(bm, a, b, c, e1=0.4, e2=0.4, nu=64, nv=32, matrix=None, mat=0):
    """Rounded box-like solid (x half-size a, y half-size b, z half-size c)."""
    def f(w, e):
        return math.copysign(abs(w) ** e, w)
    rings = []
    for j in range(1, nv):
        th = -math.pi / 2 + math.pi * j / nv
        ring = []
        for i in range(nu):
            ph = -math.pi + math.tau * i / nu
            ct = f(math.cos(th), e1)
            ring.append(Vector((a * ct * f(math.cos(ph), e2), b * ct * f(math.sin(ph), e2), c * f(math.sin(th), e1))))
        rings.append(ring)
    V = [[bm.verts.new(p) for p in r] for r in rings]
    bot = bm.verts.new((0, 0, -c))
    top = bm.verts.new((0, 0, c))
    fs = []
    for j in range(len(V) - 1):
        for i in range(nu):
            i2 = (i + 1) % nu
            fs.append(bm.faces.new((V[j][i], V[j][i2], V[j + 1][i2], V[j + 1][i])))
    for i in range(nu):
        i2 = (i + 1) % nu
        fs.append(bm.faces.new((V[0][i2], V[0][i], bot)))
        fs.append(bm.faces.new((V[-1][i], V[-1][i2], top)))
    vs = [v for r in V for v in r] + [bot, top]
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=vs)
    for fc in fs:
        fc.material_index = mat
    return vs


def basis(X, Y, Z, origin):
    """4x4 matrix whose columns are the given axes, translated to origin."""
    M = Matrix.Identity(4)
    for i, v in enumerate((X, Y, Z)):
        M[0][i], M[1][i], M[2][i] = v.x, v.y, v.z
    M[0][3], M[1][3], M[2][3] = origin.x, origin.y, origin.z
    return M


def prism_bm(bm, poly2, lift3, d0, d1, mat=0):
    """Closed curved prism: 2D outline poly2 mapped by lift3(p2, depth) at depths d0 and d1
    (boolean cutters that follow a curved panel)."""
    r0 = [bm.verts.new(lift3(p, d0)) for p in poly2]
    r1 = [bm.verts.new(lift3(p, d1)) for p in poly2]
    n = len(poly2)
    fs = []
    for k in range(n):
        k2 = (k + 1) % n
        fs.append(bm.faces.new((r0[k], r0[k2], r1[k2], r1[k])))
    fs.append(bm.faces.new(r0[::-1]))
    fs.append(bm.faces.new(r1))
    for f in fs:
        f.material_index = mat
    return fs
