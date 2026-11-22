"""Rear bumper cover of a generic modern small hatchback, removed from the car.
Wide metallic-grey clear-coated plastic shell (same paint as the other body panels)
wrapping round to the rear wheel arches at both ends, with a flat load-sill ledge on top;
lower section in unpainted grained black plastic shaped as a diffuser with vertical
strakes and a central rear fog lamp; two red reflectors low on the corners, four
parking-sensor holes with black grommets, recessed number-plate area with two small
plate-lamp lenses, fixing holes in the top ledge and black mounting tabs at the ends.
Car rear (outside) is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

Z = Vector((0, 0, 1))
SKIN_T = 0.0035
NU, NT = 560, 320
Z_BLACK = 0.150          # paint / black diffuser split height

# ------------------------------------------------------------------ plan curve
_half = [(0.0, 0.0), (0.30, 0.003), (0.55, 0.020), (0.72, 0.058), (0.83, 0.132), (0.873, 0.25), (0.882, 0.40)]
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


# ------------------------------------------------------------------ section (d behind face, z)
SEC = P.bspline([(0.13, 0.0), (0.06, 0.0), (0.028, 0.008), (0.014, 0.04), (0.006, 0.10), (0.000, 0.15),
                 (-0.008, 0.20), (-0.013, 0.28), (-0.012, 0.36), (-0.004, 0.43), (0.014, 0.468), (0.045, 0.488),
                 (0.10, 0.497), (0.20, 0.50)], NT + 1)
_face = [p for p in SEC if 0.01 < p.y < 0.47]


def d_of_z(z):
    for a, b in zip(_face, _face[1:]):
        if a.y <= z <= b.y or b.y <= z <= a.y:
            t = (z - a.y) / (b.y - a.y) if abs(b.y - a.y) > 1e-9 else 0
            return a.x + (b.x - a.x) * t
    return _face[0].x if z < _face[0].y else _face[-1].x


def s_end(z):
    """Ends cut by the wheel arches."""
    return S_HALF - 0.14 * math.sqrt(max(0.0, 1 - ((z - 0.17) / 0.33) ** 2)) - 0.01


def step(z):
    """The black lower section sits 9 mm behind the painted face."""
    return 0.009 * (1 - P.sstep(Z_BLACK - 0.004, Z_BLACK + 0.002, z))


PL_S, PL_Z0, PL_Z1 = 0.272, 0.255, 0.405


def plate_recess(s, z):
    e = 0.007
    bx = P.sstep(-PL_S - e, -PL_S + e, s) * (1 - P.sstep(PL_S - e, PL_S + e, s))
    bz = P.sstep(PL_Z0 - e, PL_Z0 + e, z) * (1 - P.sstep(PL_Z1 - e, PL_Z1 + e, z))
    return 0.011 * bx * bz


def taper(d, s):
    if d > 0.03:
        return 0.03 + (d - 0.03) * (1 - 0.6 * P.sstep(0.72, 1.0, abs(s) / S_HALF))
    return d


def point(s, z, d):
    p, T, N = plan(s)
    d = taper(d, s) + plate_recess(s, z) + step(z)
    return Vector((p.x + N.x * d, p.y + N.y * d, z))


def lift3(q, dd=0.0):
    """2D (s, z) on the bumper face -> 3D, dd behind the outer surface."""
    return point(q.x, q.y, d_of_z(q.y) + dd)


def out_normal(q):
    p, T, N = plan(q.x)
    return Vector((-N.x, -N.y, 0.0))


# ------------------------------------------------------------------ openings (s, z outlines)
def rpoly(corners, r, n=160):
    return P.resample(P.rounded(corners, [r] * len(corners), closed=True, seg=12), n, closed=True)


def refl(sx):
    c = [(0.600, 0.188), (0.745, 0.183), (0.745, 0.214), (0.600, 0.219)]
    return rpoly([(sx * a, b) for (a, b) in (c if sx > 0 else c[::-1])], 0.012, 140)


FOGL = rpoly([(-0.065, 0.062), (0.065, 0.062), (0.065, 0.098), (-0.065, 0.098)], 0.012, 140)
SENSORS = [(-0.66, 0.325), (-0.40, 0.345), (0.40, 0.345), (0.66, 0.325)]
PLATE_LAMPS = [(-0.17, 0.388), (0.17, 0.388)]


def shell(paint, raw, black, rawb):
    rows = []
    for j in range(NT + 1):
        q = SEC[j]
        se = s_end(q.y)
        rows.append([point((2 * i / NU - 1) * se, q.y, q.x) for i in range(NU + 1)])
    bm = P.clean(P.grid_bm(rows))
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < Z_BLACK - 0.001:
            f.material_index = 2
    P.orient(bm, Vector((0, -1, 0.4)))
    ob = C.mesh_obj("BumperSkin", bm, [paint, raw, black, rawb])
    P.solidify(ob, SKIN_T, offset=-1, inner=1, rim=1)
    cuts = []
    cb = bmesh.new()
    for poly in (refl(-1), refl(1), FOGL):
        P.prism_bm(cb, poly, lift3, -0.05, 0.06)
    cuts.append(C.mesh_obj("CutA", cb, [paint]))
    cb = bmesh.new()
    for (s, z) in SENSORS:
        P.prism_bm(cb, [Vector((s + 0.0118 * math.cos(a), z + 0.0118 * math.sin(a))) for a in
                        [math.tau * k / 40 for k in range(40)]], lift3, -0.05, 0.06)
    cuts.append(C.mesh_obj("CutB", cb, [paint]))
    cb = bmesh.new()
    for s in (-0.62, -0.25, 0.25, 0.62):   # fixing holes in the top ledge
        p = point(s, 0.50, 0.15)
        C.cyl_bm(cb, 0.0065, p.z - 0.05, p.z + 0.05, seg=24, matrix=Matrix.Translation((p.x, p.y, 0)))
    for (s, z) in PLATE_LAMPS:
        P.prism_bm(cb, rpoly([(s - 0.026, z - 0.008), (s + 0.026, z - 0.008), (s + 0.026, z + 0.008), (s - 0.026, z + 0.008)], 0.004, 60),
                   lift3, -0.05, 0.06)
    cuts.append(C.mesh_obj("CutC", cb, [paint]))
    for c in cuts:
        bmc = bmesh.new()
        bmc.from_mesh(c.data)
        C.fix_normals(bmc)
        bmc.to_mesh(c.data)
        bmc.free()
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    C.add_bevel(ob, 0.0016, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=cuts)


def bezel(name, poly, mat, depth=0.03):
    """Black return wall lining an opening (gives the cut real depth)."""
    out = P.offset2d(poly, -0.0015 if P.signed_area(poly) > 0 else 0.0015, closed=True)
    rows = [[lift3(q, dd) for q in out] for dd in (0.0, depth * 0.5, depth)]
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.grid_obj(name, rows, [mat], lambda v: v - lift3(c, 0.0), closed_u=True)
    P.solidify(ob, 0.003, offset=1)
    return C.finalize(ob, angle=50)


def lens_in(name, poly, mats, dd, bulge=0.004, nv=8):
    """Slightly domed lens filling an opening, its face dd behind the shell face."""
    c = sum(poly, Vector((0, 0))) / len(poly)
    inset = P.offset2d(poly, -0.0012 if P.signed_area(poly) > 0 else 0.0012, closed=True)
    rows = P.fan_rows(inset, c, nv, lambda q: q, power=1.0)
    # pull vertices outwards with a dome profile
    out = []
    for j, row in enumerate(rows):
        t = j / nv
        h = bulge * (1 - t * t)
        out.append([lift3(q, dd - h) for q in row])
    ob = P.grid_obj(name, out, mats, Vector((0, -1, 0)), closed_u=True)
    P.solidify(ob, 0.004, offset=-1)
    C.add_bevel(ob, 0.0008, segments=2, angle=40)
    return C.finalize(ob, angle=45)


def strakes(black):
    """Vertical diffuser fins standing proud of the black lower section."""
    out = []
    for s in (-0.42, -0.25, 0.25, 0.42):
        bm = bmesh.new()
        n = 30
        rings = []
        for k in range(n + 1):
            z = 0.012 + (Z_BLACK - 0.022) * k / n
            q = Vector((s, z))
            o = lift3(q, 0.0005)
            nn = out_normal(q)
            p, T, N = plan(s)
            Tv = Vector((T.x, T.y, 0)).normalized()
            h = 0.004 + 0.026 * (1 - k / n) ** 1.3
            sec = [(-0.003, 0.0), (0.003, 0.0), (0.0025, h), (0.0, h + 0.0012), (-0.0025, h)]
            rings.append([bm.verts.new(o + Tv * a + nn * b) for (a, b) in sec])
        m = 5
        for i in range(n):
            for k in range(m):
                k2 = (k + 1) % m
                bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
        C.fix_normals(bm)
        ob = C.mesh_obj("Strake", bm, [black])
        C.add_bevel(ob, 0.0012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


def sensor_grommets(black):
    out = []
    for (s, z) in SENSORS:
        q = Vector((s, z))
        n = out_normal(q)
        o = lift3(q, 0.0)
        Zl = n.normalized()
        Xl = Z.cross(Zl).normalized()
        M = P.basis(Xl, Zl.cross(Xl), Zl, o)
        rg = C.lathe("SensorGrommet", [(0.0088, -0.0012, 0), (0.0119, -0.0012, 0), (0.0119, -0.028, 0),
                                       (0.0088, -0.028, 0)], [black], steps=48)
        rg.matrix_world = M
        C.add_bevel(rg, 0.0005, segments=1, angle=30)
        out.append(C.finalize(rg, angle=40))
        # empty socket behind (dark bottom so the hole reads as a hole)
        cup = C.lathe("SensorSocket", [(0.0, -0.026, 0), (0.0119, -0.026, 0), (0.0119, -0.029, 0), (0.0, -0.029, 0)],
                      [black], steps=32)
        cup.matrix_world = M
        out.append(C.finalize(cup, angle=40))
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


def mat_reflector():
    """Red prismatic retro-reflector: glossy red with a fine cell bump."""
    m = C.principled("Reflector", (0.42, 0.012, 0.014), rough=0.12, Coat_Weight=1.0)
    nt = m.node_tree
    b = P.bsdf(m)
    C._set(b, "Transmission Weight", 0.35)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = 380.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(vo.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_plate_lens():
    m = C.principled("PlateLens", (0.85, 0.86, 0.88), rough=0.25, IOR=1.5)
    C._set(P.bsdf(m), "Transmission Weight", 0.6)
    C.add_noise_bump(m, scale=900, strength=0.25, distance=0.0003)
    return m


def build():
    paint = P.body_paint()
    raw = P.textured_black("RawPP", rough=0.6, v=0.025)
    diff = P.textured_black("DiffuserPP", rough=0.6, v=0.021)
    trim = P.textured_black("TrimPP", rough=0.55, v=0.016)
    red = mat_reflector()
    objs = [shell(paint, raw, diff, raw)]
    objs += [bezel("ReflBezelL", refl(-1), trim, 0.02), bezel("ReflBezelR", refl(1), trim, 0.02),
             bezel("FogBezel", FOGL, trim, 0.02)]
    for sx in (-1, 1):
        objs.append(lens_in("Reflector", refl(sx), [red], 0.004, 0.002))
    objs.append(lens_in("RearFog", FOGL, [red], 0.006, 0.003))
    for (s, z) in PLATE_LAMPS:
        poly = rpoly([(s - 0.026, z - 0.008), (s + 0.026, z - 0.008), (s + 0.026, z + 0.008), (s - 0.026, z + 0.008)], 0.004, 60)
        objs.append(bezel("PlateLampBezel", poly, trim, 0.015))
        objs.append(lens_in("PlateLamp", poly, [mat_plate_lens()], 0.001, 0.0025))
    objs += strakes(diff)
    objs += sensor_grommets(trim)
    objs += tabs(raw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("paraurti-post", objs, "paraurti-post.py",
            "rear bumper cover (generic small hatchback), metallic grey paint: wrap-around shell with top load ledge, "
            "black lower diffuser with strakes and rear fog lamp, red corner reflectors, parking-sensor holes, "
            "number-plate recess with plate lamps, mounting tabs",
            az=-32, el=16, lens=70, fill=0.88, fill_w=0.92, fill_h=0.85, res=(r, r),
            samples=int(os.environ.get("SAMPLES", "128")))
