"""Front bumper cover of a generic modern small hatchback, removed from the car.
Wide metallic-grey clear-coated plastic shell (same paint as the other body panels)
wrapping round to the wheel arches at both ends, with a horizontal top flange; lower
grille opening with black honeycomb insert, slim upper intake with gloss-black slats,
two fog-lamp recesses with textured bezels and round lamps, recessed number-plate area,
four parking-sensor caps and black mounting tabs at the ends. Car front is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

Z = Vector((0, 0, 1))
SKIN_T = 0.0035
NU, NT = 560, 300

# ------------------------------------------------------------------ plan curve
_half = [(0.0, 0.0), (0.30, 0.004), (0.55, 0.028), (0.72, 0.075), (0.82, 0.155), (0.862, 0.27), (0.868, 0.41)]
_ctrl = [(-x, y) for (x, y) in reversed(_half[1:])] + _half
PLAN = P.bspline(_ctrl, 2001)
_acc = [0.0]
for _i in range(1, len(PLAN)):
    _acc.append(_acc[-1] + (PLAN[_i] - PLAN[_i - 1]).length)
S_HALF = _acc[-1] / 2
DS = _acc[-1] / (len(PLAN) - 1)


def plan(s):
    """(point, tangent, back-normal) of the plan curve at arc length s (0 = centre)."""
    f = (s + S_HALF) / DS
    i = max(0, min(len(PLAN) - 2, int(f)))
    t = f - i
    p = PLAN[i].lerp(PLAN[i + 1], t)
    a, b = PLAN[max(0, i - 1)], PLAN[min(len(PLAN) - 1, i + 2)]
    T = (b - a).normalized()
    return p, T, Vector((-T.y, T.x))


# ------------------------------------------------------------------ section
SEC = P.bspline([(0.10, 0.0), (0.03, 0.0), (-0.013, 0.012), (-0.013, 0.05), (0.004, 0.09), (0.006, 0.17),
                 (-0.004, 0.27), (-0.002, 0.36), (0.018, 0.43), (0.05, 0.475), (0.10, 0.50), (0.17, 0.505)], NT + 1)
_face = [p for p in SEC if 0.01 < p.y < 0.44]


def d_of_z(z):
    for a, b in zip(_face, _face[1:]):
        if a.y <= z <= b.y or b.y <= z <= a.y:
            t = (z - a.y) / (b.y - a.y) if abs(b.y - a.y) > 1e-9 else 0
            return a.x + (b.x - a.x) * t
    return _face[0].x if z < _face[0].y else _face[-1].x


def s_end(z):
    return S_HALF - 0.13 * math.sqrt(max(0.0, 1 - ((z - 0.21) / 0.31) ** 2)) - 0.01


def plate_recess(s, z):
    e = 0.007
    bx = P.sstep(-0.265 - e, -0.265 + e, s) * (1 - P.sstep(0.265 - e, 0.265 + e, s))
    bz = P.sstep(0.19 - e, 0.19 + e, z) * (1 - P.sstep(0.31 - e, 0.31 + e, z))
    return 0.009 * bx * bz


def taper(d, s):
    if d > 0.03:
        return 0.03 + (d - 0.03) * (1 - 0.65 * P.sstep(0.72, 1.0, abs(s) / S_HALF))
    return d


def top_h(s):
    """Top edge height: high in the centre (between the headlamps), lower under the lamps."""
    return 0.432 + 0.073 * (1 - P.sstep(0.30, 0.56, abs(s)))


def warp(s, z):
    if z <= 0.24:
        return z
    return 0.24 + (z - 0.24) * (top_h(s) - 0.24) / (0.505 - 0.24)


def point(s, z, d):
    p, T, N = plan(s)
    d = taper(d, s) + plate_recess(s, z)
    return Vector((p.x + N.x * d, p.y + N.y * d, warp(s, z)))


def lift3(q, dd=0.0):
    """2D (s, z) on the bumper face -> 3D, dd behind the outer surface."""
    return point(q.x, q.y, d_of_z(q.y) + dd)


def out_normal(q):
    p, T, N = plan(q.x)
    return Vector((-N.x, -N.y, 0.0))


# ------------------------------------------------------------------ openings (s, z outlines)
def rpoly(corners, r, n=160):
    return P.resample(P.rounded(corners, [r] * len(corners), closed=True, seg=12), n, closed=True)


GRILLE = rpoly([(-0.39, 0.040), (0.39, 0.040), (0.47, 0.168), (-0.47, 0.168)], 0.035, 260)
UPPER = rpoly([(-0.30, 0.355), (0.30, 0.355), (0.275, 0.405), (-0.275, 0.405)], 0.022, 200)


def fog(sx):
    c = [(0.575, 0.075), (0.765, 0.088), (0.775, 0.175), (0.585, 0.168)]
    return rpoly([(sx * a, b) for (a, b) in (c if sx > 0 else c[::-1])], 0.035, 160)


FOG_C = [(-0.672, 0.126), (0.672, 0.126)]
SENSORS = [(-0.62, 0.30), (-0.38, 0.33), (0.38, 0.33), (0.62, 0.30)]


def shell(paint, raw):
    rows = []
    for j in range(NT + 1):
        q = SEC[j]
        se = s_end(q.y)
        rows.append([point((2 * i / NU - 1) * se, q.y, q.x) for i in range(NU + 1)])
    ob = P.grid_obj("BumperSkin", rows, [paint, raw], Vector((0, -1, 0.4)))
    P.solidify(ob, SKIN_T, offset=-1, inner=1, rim=1)
    cb = bmesh.new()
    for poly in (GRILLE, UPPER, fog(-1), fog(1)):
        P.prism_bm(cb, poly, lift3, -0.05, 0.06)
    for (s, z) in SENSORS:
        P.prism_bm(cb, [Vector((s + 0.0115 * math.cos(a), z + 0.0115 * math.sin(a))) for a in
                        [math.tau * k / 32 for k in range(32)]], lift3, -0.05, 0.06)
    for s in (-0.62, -0.25, 0.25, 0.62):   # fixing holes in the top flange
        p = point(s, 0.505, 0.135)
        C.cyl_bm(cb, 0.0065, p.z - 0.05, p.z + 0.05, seg=24, matrix=Matrix.Translation((p.x, p.y, 0)))
    C.fix_normals(cb)
    cut = C.mesh_obj("Cutters", cb, [paint])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.0016, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=[cut])


def bezel(name, poly, mat, depth=0.035):
    """Black return wall lining an opening (gives the cut real depth)."""
    out = P.offset2d(poly, -0.0015 if P.signed_area(poly) > 0 else 0.0015, closed=True)
    rows = [[lift3(q, dd) for q in out] for dd in (0.0, depth * 0.5, depth)]
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.grid_obj(name, rows, [mat], lambda v: v - lift3(c, 0.0))
    P.solidify(ob, 0.003, offset=1)
    return C.finalize(ob, angle=50)


def inside(poly, q):
    n = len(poly)
    c = False
    for i in range(n):
        a, b = poly[i - 1], poly[i]
        if (a.y > q.y) != (b.y > q.y):
            x = a.x + (q.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if q.x < x:
                c = not c
    return c


def honeycomb(mat):
    bm = bmesh.new()
    R = 0.0165             # cell circumradius
    wall = 0.0032
    dx = math.sqrt(3) * R
    dz = 1.5 * R
    d0, d1 = 0.012, 0.032
    big = P.offset2d(GRILLE, -0.03 if P.signed_area(GRILLE) > 0 else 0.03, closed=True)
    rows = int(0.20 / dz) + 2
    cols = int(1.1 / dx) + 2
    for r in range(rows):
        z = 0.02 + r * dz
        for c in range(-cols // 2, cols // 2 + 1):
            s = c * dx + (dx / 2 if r % 2 else 0)
            q = Vector((s, z))
            if not inside(big, q):
                continue
            hexo = [Vector((s + R * math.cos(math.radians(30 + 60 * k)), z + R * math.sin(math.radians(30 + 60 * k)))) for k in range(6)]
            hexi = [q + (h - q) * ((R - wall) / R) for h in hexo]
            V = {}
            for key, ring in (("o", hexo), ("i", hexi)):
                for dd in (d0, d1):
                    V[(key, dd)] = [bm.verts.new(lift3(h, dd)) for h in ring]
            for k in range(6):
                k2 = (k + 1) % 6
                fo, fi, bo, bi = V[("o", d0)], V[("i", d0)], V[("o", d1)], V[("i", d1)]
                bm.faces.new((fo[k], fo[k2], fi[k2], fi[k]))
                bm.faces.new((fi[k], fi[k2], bi[k2], bi[k]))
                bm.faces.new((bo[k], bo[k2], fo[k2], fo[k]))
                bm.faces.new((bi[k], bi[k2], bo[k2], bo[k]))
    C.fix_normals(bm)
    ob = C.mesh_obj("Honeycomb", bm, [mat])
    return C.finalize(ob, angle=30)


def upper_slats(mat):
    out = []
    for z in (0.372, 0.389):
        pts = [Vector((-0.31 + 0.62 * k / 120, z)) for k in range(121)]
        fr = P.frames_on_surface(pts, lambda q: lift3(q, 0.010), Vector((0, -1, 0)))
        out.append(P.tube_obj("Slat", fr, P.rrect(-0.004, 0.004, -0.0015, 0.0015, 0.0012), [mat], smooth_angle=50))
    # dark back panel closing the slot
    big = P.offset2d(UPPER, -0.012 if P.signed_area(UPPER) > 0 else 0.012, closed=True)
    c = sum(UPPER, Vector((0, 0))) / len(UPPER)
    back = P.fan_obj("SlotBack", big, c, 8, lambda q: lift3(q, 0.028), [mat], Vector((0, -1, 0)))
    P.solidify(back, 0.003, offset=-1)
    out.append(C.finalize(back, angle=40))
    return out


def fog_unit(sx, raw, chrome, glass, black):
    out = []
    poly = fog(sx)
    big = P.offset2d(poly, -0.012 if P.signed_area(poly) > 0 else 0.012, closed=True)
    c = sum(poly, Vector((0, 0))) / len(poly)
    back = P.fan_obj("FogPlate", big, c, 10, lambda q: lift3(q, 0.034), [raw], Vector((0, -1, 0)))
    P.solidify(back, 0.003, offset=-1)
    out.append(C.finalize(back, angle=40))
    # round lamp facing out
    q = Vector(FOG_C[0 if sx < 0 else 1])
    n = out_normal(q)
    o = lift3(q, 0.034)
    Zl = n.normalized()
    Xl = Z.cross(Zl).normalized()
    Yl = Zl.cross(Xl)
    M = P.basis(Xl, Yl, Zl, o)
    r = 0.040
    ring = C.lathe("FogRing", [(r - 0.003, 0.0, 0), (r + 0.008, 0.0, 0), (r + 0.008, 0.012, 0), (r + 0.004, 0.017, 0), (r - 0.003, 0.014, 0)], [black], steps=64)
    ring.matrix_world = M
    out.append(C.finalize(ring, angle=40))
    prof = [(0.008 + (r - 0.008) * i / 12, -0.012 + 0.024 * ((0.008 + (r - 0.008) * i / 12) / r) ** 2, 0) for i in range(13)]
    bowl = C.lathe("FogReflector", prof, [chrome], steps=64, closed=False)
    bowl.matrix_world = M
    out.append(C.finalize(bowl, angle=50))
    lens = C.lathe("FogLens", [(0.0, 0.016, 0), (0.02, 0.0155, 0), (r - 0.001, 0.013, 0), (r - 0.001, 0.009, 0), (0.0, 0.009, 0)], [glass], steps=64)
    lens.matrix_world = M
    out.append(C.finalize(lens, angle=50))
    return out


def sensors(paint, black):
    out = []
    for (s, z) in SENSORS:
        q = Vector((s, z))
        n = out_normal(q)
        o = lift3(q, 0.0)
        Zl = n.normalized()
        Xl = Z.cross(Zl).normalized()
        M = P.basis(Xl, Zl.cross(Xl), Zl, o)
        cap = C.lathe("Sensor", [(0.0, -0.0005, 0), (0.0095, -0.0008, 0), (0.0105, -0.002, 0), (0.0105, -0.02, 0), (0.0, -0.02, 0)], [paint], steps=48)
        cap.matrix_world = M
        out.append(C.finalize(cap, angle=40))
        rg = C.lathe("SensorRing", [(0.0105, -0.0015, 0), (0.0116, -0.0015, 0), (0.0116, -0.02, 0), (0.0105, -0.02, 0)], [black], steps=48)
        rg.matrix_world = M
        out.append(C.finalize(rg, angle=40))
    return out


def tabs(raw):
    out = []
    for sx in (-1, 1):
        for z, h in ((0.40, 0.04), (0.08, 0.036)):
            se = s_end(z) * sx
            p, T, N = plan(se)
            T = T * sx
            d = d_of_z(z)
            base = point(se, z, d + 0.006)
            Tv = Vector((T.x, T.y, 0)).normalized()
            Nv = Vector((N.x, N.y, 0)).normalized()
            M = P.basis(Tv, Nv, Z, base + Tv * 0.016)
            bm = bmesh.new()
            C.box_bm(bm, 0.045, 0.004, h, matrix=M)
            tb = C.mesh_obj("Tab", bm, [raw])
            cb = bmesh.new()
            C.cyl_bm(cb, 0.008, -0.05, 0.05, seg=24, matrix=M @ Matrix.Translation((0.012, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"))
            cut = C.mesh_obj("TabCut", cb, [raw])
            C.add_boolean(tb, cut)
            C.add_bevel(tb, 0.0012, segments=2, angle=30)
            out.append(C.finalize(tb, angle=35, remove=[cut]))
    return out


def build():
    paint = P.body_paint()
    raw = P.textured_black("RawPP", rough=0.6, v=0.025)
    trim = P.textured_black("TrimPP", rough=0.55, v=0.018)
    chrome = C.mat_chrome()
    glass = C.mat_clear("FogLensPC")
    objs = [shell(paint, raw)]
    objs += [bezel("GrilleBezel", GRILLE, trim), bezel("UpperBezel", UPPER, trim, 0.03),
             bezel("FogBezelL", fog(-1), trim), bezel("FogBezelR", fog(1), trim)]
    objs.append(honeycomb(trim))
    objs += upper_slats(C.mat_rubber("SlatPP"))
    for sx in (-1, 1):
        objs += fog_unit(sx, trim, chrome, glass, trim)
    objs += sensors(paint, trim)
    objs += tabs(raw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("paraurti", objs, "paraurti.py",
            "front bumper cover (generic small hatchback), metallic grey paint: wrap-around shell, lower honeycomb grille, "
            "upper intake with slats, fog-lamp recesses, plate recess, parking sensors, mounting tabs",
            az=-30, el=14, lens=70, fill=0.88, fill_w=0.92, fill_h=0.85)
