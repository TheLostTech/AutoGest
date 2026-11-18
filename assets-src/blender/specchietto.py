"""Door wing mirror, left side, as removed from the car: aerodynamic head with a
dark-blue metallic painted cap over a black textured housing, convex mirror glass in a
recessed black surround, black textured arm on a triangular door-mount foot with a
foam gasket, three threaded studs and a short corrugated wiring pigtail ending in a
connector."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

NU = 200
HEAD_PTS = [(-0.56, 0.17), (-0.47, 0.29), (0.28, 0.31), (0.44, 0.24), (0.47, -0.10),
            (0.36, -0.23), (-0.28, -0.22), (-0.53, -0.07)]
HC = (-0.03, 0.03)   # head centre (x, z)
FOOT_X = 0.80        # door-side face of the foot


def chaikin(pts, it=5):
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
    ls = [math.dist(a, b) for a, b in segs]
    tot = sum(ls)
    out, acc, j = [], 0.0, 0
    for i in range(n):
        tgt = tot * i / n
        while acc + ls[j] < tgt:
            acc += ls[j]
            j += 1
        a, b = segs[j]
        f = (tgt - acc) / ls[j]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


HEAD = resample(chaikin(HEAD_PTS), NU)


def hp(i, s):
    x, z = HEAD[i % NU]
    return HC[0] + s * (x - HC[0]), HC[1] + s * (z - HC[1])


def head_profile():
    """(scale, y, mat) rings from the glass rim to the dome; mat 0 housing, 1 paint."""
    P = [(1.000, -0.012, 0), (1.022, -0.004, 0), (1.036, 0.020, 0), (1.040, 0.036, 0),
         (1.032, 0.042, 1), (1.044, 0.050, 1), (1.050, 0.110, 1)]
    K = 14
    for k in range(1, K + 1):
        ph = (math.pi / 2) * k / K
        s = 1.050 * max(math.cos(ph), 0.0) ** 0.75
        y = 0.12 + 0.30 * math.sin(ph) ** 1.15
        P.append((max(s, 0.0), y, 1))
    return P


def head(housing_m, paint_m):
    prof = head_profile()
    bm = bmesh.new()
    rows = []
    for (s, y, _m) in prof[:-1]:
        rows.append([bm.verts.new((hp(i, s)[0], y, hp(i, s)[1])) for i in range(NU)])
    apex = bm.verts.new((HC[0], prof[-1][1], HC[1]))
    for j in range(len(rows) - 1):
        for i in range(NU):
            i2 = (i + 1) % NU
            f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            f.material_index = prof[j + 1][2] if j >= 3 else 0
    for i in range(NU):
        f = bm.faces.new((rows[-1][i], rows[-1][(i + 1) % NU], apex))
        f.material_index = 1
    C.fix_normals(bm)
    ob = C.mesh_obj("Head", bm, [housing_m, paint_m])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.014
    so.offset = -1
    C.add_bevel(ob, 0.004, segments=2, angle=35)
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    return C.finalize(ob, angle=50)


def glass_and_back(mirror_m, back_m):
    out = []
    nv = 16
    bm = bmesh.new()
    rows = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(NU):
            x, z = hp(i, 0.955 * v)
            # convex glass, tilted up a few degrees in its adjuster
            y = 0.016 - 0.030 * (1 - v * v) + math.tan(math.radians(7)) * (z - HC[1])
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for j in range(nv):
        for i in range(NU):
            i2 = (i + 1) % NU
            try:
                bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    g = C.mesh_obj("Glass", bm, [mirror_m])
    so = g.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.007
    so.offset = -1
    C.add_bevel(g, 0.002, segments=1, angle=40)
    out.append(C.finalize(g, angle=60))
    # black carrier plate behind the glass (seen in the gap to the rim)
    bm = bmesh.new()
    ring = [bm.verts.new((hp(i, 1.03)[0], 0.035, hp(i, 1.03)[1])) for i in range(NU)]
    c = bm.verts.new((HC[0], 0.035, HC[1]))
    for i in range(NU):
        bm.faces.new((ring[i], ring[(i + 1) % NU], c))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    out.append(C.finalize(C.mesh_obj("Carrier", bm, [back_m]), angle=60))
    return out


def rrect_section(w, h, r, n=5):
    pts = []
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        cx, cz = sx * (w / 2 - r), sz * (h / 2 - r)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def arm(mat):
    """Lofted stalk along +X from inside the head to the foot; section in (y, z)."""
    keys = [  # x, y centre, z centre, width(y), height(z), corner r
        (0.12, 0.20, -0.110, 0.200, 0.120, 0.050),
        (0.36, 0.20, -0.150, 0.215, 0.115, 0.050),
        (0.55, 0.205, -0.185, 0.230, 0.130, 0.055),
        (0.70, 0.21, -0.200, 0.280, 0.190, 0.070),
        (FOOT_X - 0.05, 0.21, -0.205, 0.330, 0.250, 0.080),
    ]
    frames = []
    N = 40
    for k in range(N + 1):
        x = keys[0][0] + (keys[-1][0] - keys[0][0]) * k / N
        for a, b in zip(keys, keys[1:]):
            if a[0] <= x <= b[0] + 1e-9:
                f = C.smoothstep(a[0], b[0], x)
                vals = [a[i] + (b[i] - a[i]) * f for i in range(1, 6)]
                break
        y, z, w, h, r = vals
        sec = rrect_section(w, h, r)
        frames.append((Vector((x, y, z)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Arm", bm, [mat])
    C.add_bevel(ob, 0.01, segments=3, angle=40)
    return C.finalize(ob, angle=40)


FOOT_PTS = [(-0.05, -0.36), (0.47, -0.36), (0.45, 0.08)]


def fillet(poly, r, n=8):
    """Round every corner of a convex polygon with radius r."""
    out = []
    m = len(poly)
    for i in range(m):
        A, B, Cc = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % m])
        u1, u2 = (A - B).normalized(), (Cc - B).normalized()
        th = u1.angle(u2) / 2
        d = r / math.tan(th)
        bis = (u1 + u2).normalized()
        ctr = B + bis * (r / math.sin(th))
        p1, p2 = B + u1 * d, B + u2 * d
        a1 = math.atan2(p1.y - ctr.y, p1.x - ctr.x)
        a2 = math.atan2(p2.y - ctr.y, p2.x - ctr.x)
        da = (a2 - a1 + math.pi) % math.tau - math.pi
        for k in range(n + 1):
            a = a1 + da * k / n
            out.append((ctr.x + r * math.cos(a), ctr.y + r * math.sin(a)))
    return out


def foot(mat, foam):
    tri = fillet(FOOT_PTS, 0.06, n=10)
    out = []
    for (x0, x1, m, shrink) in ((FOOT_X - 0.06, FOOT_X, mat, 0.0), (FOOT_X, FOOT_X + 0.012, foam, 0.012)):
        cy = sum(p[0] for p in tri) / len(tri)
        cz = sum(p[1] for p in tri) / len(tri)
        pts = [(cy + (y - cy) * (1 - shrink / 0.15), cz + (z - cz) * (1 - shrink / 0.15)) for y, z in tri]
        bm = bmesh.new()
        v0 = [bm.verts.new((x0, y, z)) for y, z in pts]
        v1 = [bm.verts.new((x1, y, z)) for y, z in pts]
        n = len(pts)
        for k in range(n):
            bm.faces.new((v0[k], v0[(k + 1) % n], v1[(k + 1) % n], v1[k]))
        bm.faces.new(v0[::-1])
        bm.faces.new(v1)
        C.fix_normals(bm)
        ob = C.mesh_obj("Foot", bm, [m])
        C.add_bevel(ob, 0.012 if m is mat else 0.004, segments=3, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


STUDS = [(0.04, -0.30), (0.38, -0.30), (0.36, -0.02)]


def studs(zinc):
    out = []
    Ry = Matrix.Rotation(math.radians(90), 4, "Y")   # local +Z -> world +X
    for (y, z) in STUDS:
        prof = [(0.0, 0.0, 0), (0.024, 0.0, 0), (0.024, 0.012, 0)]
        zz = 0.012
        while zz < 0.11:
            prof += [(0.0095, zz, 0), (0.0118, zz + 0.0042, 0)]
            zz += 0.0085
        prof += [(0.0095, 0.115, 0), (0.0075, 0.12, 0), (0.0, 0.12, 0)]
        st = C.lathe("Stud", prof, [zinc], steps=32)
        st.matrix_world = Matrix.Translation((FOOT_X + 0.004, y, z)) @ Ry
        out.append(C.finalize(st, angle=50))
    return out


def pigtail(sleeve_m, conn_m, wire_ms):
    out = []
    # path leaves the foot along +X, turns down and back
    ctrl = [Vector(p) for p in ((FOOT_X - 0.02, 0.21, -0.17), (FOOT_X + 0.08, 0.21, -0.17),
                                (FOOT_X + 0.16, 0.20, -0.21), (FOOT_X + 0.20, 0.17, -0.30),
                                (FOOT_X + 0.19, 0.10, -0.38), (FOOT_X + 0.15, 0.02, -0.43))]

    def bez(t):  # Catmull-Rom through ctrl
        n = len(ctrl) - 1
        f = min(t * n, n - 1e-6)
        i = int(f)
        u = f - i
        p0 = ctrl[max(i - 1, 0)]; p1 = ctrl[i]; p2 = ctrl[i + 1]; p3 = ctrl[min(i + 2, n)]
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                      + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

    N = 140
    P = [bez(i / N) for i in range(N + 1)]
    frames = []
    U = Vector((0, 0, 1))
    for i, p in enumerate(P):
        t = (P[min(i + 1, N)] - P[max(i - 1, 0)]).normalized()
        U = (U - t * U.dot(t)).normalized()
        V = t.cross(U)
        frames.append((p, t, U, V))
    total = sum((P[i + 1] - P[i]).length for i in range(N))
    acc = 0.0
    sec_frames = []
    for i, (p, t, U, V) in enumerate(frames):
        if i:
            acc += (P[i] - P[i - 1]).length
        r = 0.021 + 0.0028 * math.cos(acc / 0.011 * math.tau)
        sec = [(r * math.cos(a * math.tau / 20), r * math.sin(a * math.tau / 20)) for a in range(20)]
        sec_frames.append((p, U, V, sec))
    bm = bmesh.new()
    C.sweep(bm, sec_frames, mat=0)
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("Sleeve", bm, [sleeve_m]), angle=50))
    # connector body at the end, axis along the last tangent
    p, t, U, V = frames[-1]
    M = Matrix((
        (U.x, V.x, t.x, p.x),
        (U.y, V.y, t.y, p.y),
        (U.z, V.z, t.z, p.z),
        (0, 0, 0, 1)))
    bm = bmesh.new()
    C.box_bm(bm, 0.075, 0.050, 0.060, center=(0, 0, -0.005))   # strain-relief boot
    C.box_bm(bm, 0.11, 0.075, 0.095, center=(0, 0, 0.065))
    C.box_bm(bm, 0.03, 0.02, 0.06, center=(0, 0.045, 0.07))     # latch
    ob = C.mesh_obj("Connector", bm, [conn_m])
    cb = bmesh.new()
    C.box_bm(cb, 0.085, 0.05, 0.05, center=(0, 0, 0.11))
    cut = C.mesh_obj("ConnCut", cb, [conn_m])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    ob.matrix_world = M
    cut.matrix_world = M
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # wires peeking out of the sleeve at the foot
    return out


def build():
    housing_m = C.mat_black_plastic("GrainPP", rough=0.6, color=0.03)
    C.add_noise_bump(housing_m, scale=260, strength=0.10, distance=0.0012)
    paint = C.mat_paint("CapPaint", C.srgb("#1F3B6B"), rough=0.32, coat=1.0, metallic=0.75)
    C.add_noise_bump(paint, scale=4000, strength=0.03, distance=0.0002)
    mirror = C.principled("MirrorGlass", (0.80, 0.83, 0.86), metallic=1.0, rough=0.015)
    carrier = C.mat_black_plastic("CarrierABS", rough=0.5, color=0.012, tex=False)
    foam = C.principled("Foam", (0.02, 0.02, 0.021), rough=0.95)
    C.add_noise_bump(foam, scale=900, strength=0.4, distance=0.0015)
    zinc = C.principled("ZincYellow", (0.78, 0.70, 0.42), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=500, strength=0.08, distance=0.0005, rough_var=0.06)
    sleeve = C.mat_black_plastic("Loom", rough=0.5, color=0.02, tex=False)
    conn = C.mat_black_plastic("ConnPA", rough=0.55, color=0.035)
    objs = [head(housing_m, paint)]
    objs += glass_and_back(mirror, carrier)
    objs.append(arm(housing_m))
    objs += foot(housing_m, foam)
    objs += studs(zinc)
    objs += pigtail(sleeve, conn, None)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("specchietto", objs, "specchietto.py",
            "left door wing mirror: dark blue metallic cap, black textured housing and arm, mirror glass, "
            "triangular door-mount foot with studs, wiring pigtail with connector",
            az=42, el=22, lens=70, fill=0.84, samples=int(os.environ.get("SAMPLES", 128)))
