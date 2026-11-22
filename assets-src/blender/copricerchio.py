"""Plastic wheel trim / hubcap (copricerchio), 14 inch: injection-moulded ABS shell in
silver paint with a blank raised centre disc, ten ridged spokes over recessed pockets
with vent openings, outer ring and rolled lip; on the back a skirt rib, eight
retaining clips and the spring-steel retaining ring. No logo. Polar-grid sheet
z = f(profile, angle), solidified; openings are boolean prisms."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm, face toward +Z
NSP = 10
PROFILE = [(0.0, 0.58), (0.30, 0.58), (0.40, 0.575), (0.46, 0.545), (0.52, 0.50), (0.60, 0.49),
           (0.90, 0.47), (1.20, 0.44), (1.42, 0.41), (1.52, 0.40), (1.66, 0.39), (1.76, 0.36),
           (1.83, 0.29), (1.86, 0.18), (1.865, 0.06), (1.86, 0.0)]


def catmull_open(pts, n=12):
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[i + k]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def ang_dist(th, period):
    """distance (radians) from th to the nearest spoke centre"""
    f = (th / period) % 1.0
    return min(f, 1.0 - f) * period


def pocket(r, th):
    """0 on spokes / rings, 1 in the recessed pockets between spokes"""
    if r < 0.60 or r > 1.48:
        return 0.0
    per = math.tau / NSP
    hw = 0.085 / max(r, 0.3) + 0.06       # spoke half width (angle), spokes widen outward in length units
    d = ang_dist(th, per)
    a = C.smoothstep(hw, hw + 0.05, d)
    rr = C.smoothstep(0.60, 0.70, r) * (1 - C.smoothstep(1.36, 1.48, r))
    return a * rr


def ridge(r, th):
    per = math.tau / NSP
    d = ang_dist(th, per) * r
    if r < 0.58 or r > 1.48:
        return 0.0
    return max(0.0, 1 - d / 0.05) ** 2 * C.smoothstep(0.58, 0.7, r) * (1 - C.smoothstep(1.35, 1.48, r))


def shell(paint):
    prof = catmull_open(PROFILE, 10)
    na = 480
    bm = bmesh.new()
    rows = []
    centre = bm.verts.new((0, 0, prof[0].y))
    for p in prof[1:]:
        r, h = p.x, p.y
        row = []
        for k in range(na):
            th = math.tau * k / na
            z = h - 0.13 * pocket(r, th) + 0.025 * ridge(r, th)
            row.append(bm.verts.new((r * math.cos(th), r * math.sin(th), z)))
        rows.append(row)
    for k in range(na):
        bm.faces.new((centre, rows[0][k], rows[0][(k + 1) % na]))
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(na):
            k2 = (k + 1) % na
            bm.faces.new((a[k], b[k], b[k2], a[k2]))
    bm.normal_update()
    ob = C.mesh_obj("Shell", bm, [paint])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.028
    so.offset = -1.0
    so.use_even_offset = True
    # vent openings in the pockets: rounded trapezoids, one boolean each
    cutters = []
    per = math.tau / NSP
    for i in range(NSP):
        thc = per * (i + 0.5)
        pts = []
        for j in range(25):
            u = j / 24
            r = 0.78 + 0.56 * u
            hw = (per / 2) - (0.085 / r + 0.06) - 0.07
            pts.append((r, thc + hw * (0.75 + 0.25 * u)))
        pts += [(r, 2 * thc - t) for (r, t) in pts[::-1]]
        cb = bmesh.new()
        vb = [cb.verts.new((r * math.cos(t), r * math.sin(t), -0.5)) for r, t in pts]
        vt = [cb.verts.new((r * math.cos(t), r * math.sin(t), 1.0)) for r, t in pts]
        cb.faces.new(vb[::-1])
        cb.faces.new(vt)
        for a in range(len(pts)):
            b2 = (a + 1) % len(pts)
            cb.faces.new((vb[a], vb[b2], vt[b2], vt[a]))
        c = C.mesh_obj("Vent%d" % i, cb, [paint])
        bv = c.modifiers.new("Bevel", "BEVEL")
        bv.width = 0.05
        bv.segments = 4
        bv.limit_method = "ANGLE"
        bv.angle_limit = math.radians(40)
        cutters.append(c)
    for c in cutters:
        b = C.add_boolean(ob, c)
        try:
            b.solver = "MANIFOLD"   # exact solver is far too slow on this dense shell
        except Exception:
            b.use_self = True
    C.add_bevel(ob, 0.006, segments=2, angle=40)
    return C.finalize(ob, angle=38, remove=cutters)


def back(plastic, wire_m, paint):
    out = []
    # skirt rib on the back
    P = [(1.55, 0.36, 0), (1.59, 0.36, 0), (1.59, -0.08, 0), (1.55, -0.08, 0)]
    out.append(C.finalize(C.lathe("Skirt", P, [plastic], steps=200), angle=40))
    # eight retaining clips: tab + outward hook
    bm = bmesh.new()
    for k in range(8):
        a = math.tau * (k + 0.5) / 8 + 0.12
        R = Matrix.Rotation(a, 4, "Z")
        C.box_bm(bm, 0.07, 0.24, 0.44, center=(1.60, 0, 0.03), matrix=R)          # tab
        C.box_bm(bm, 0.11, 0.24, 0.07, center=(1.66, 0, -0.17), matrix=R)         # hook lip
        C.box_bm(bm, 0.05, 0.10, 0.10, center=(1.535, 0, -0.03), matrix=R)        # wire guide
    cl = C.mesh_obj("Clips", bm, [plastic])
    C.add_bevel(cl, 0.012, segments=2, angle=30)
    out.append(C.finalize(cl, angle=35))
    # spring-steel retaining ring through the guides, with a gap and bent-in ends
    cu = bpy.data.curves.new("Wire", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.016
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    n = 200
    gap = 0.22
    pts = []
    for i in range(n + 1):
        a = gap / 2 + (math.tau - gap) * i / n
        pts.append((1.515 * math.cos(a), 1.515 * math.sin(a), -0.04))
    a0, a1 = gap / 2, math.tau - gap / 2
    pts = [(1.40 * math.cos(a0), 1.40 * math.sin(a0), -0.04)] + pts + [(1.40 * math.cos(a1), 1.40 * math.sin(a1), -0.04)]
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = C.link(bpy.data.objects.new("Wire", cu))
    cu.materials.append(wire_m)
    out.append(C.finalize(ob, angle=60))
    return out


def build():
    paint = C.mat_paint("TrimSilver", (0.50, 0.51, 0.53, 1), rough=0.30, coat=0.8, metallic=0.85)
    C.add_noise_bump(paint, scale=2200, strength=0.04, distance=0.0002, rough_var=0.05)
    plastic = C.mat_black_plastic("BackABS", rough=0.5, color=0.10)
    wire = C.principled("SpringWire", (0.55, 0.55, 0.56), metallic=1.0, rough=0.3)
    objs = [shell(paint)] + back(plastic, wire, paint)
    # stand it up facing the camera, leaning back a little on its clips
    C.transform_all(objs, Matrix.Rotation(math.radians(-20), 4, "Z") @ Matrix.Rotation(math.radians(78), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("copricerchio", objs, "copricerchio.py",
            "plastic wheel trim hubcap: silver painted, ten spokes with vent openings, blank centre, retaining clips and steel ring on the back",
            az=34, el=14, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
