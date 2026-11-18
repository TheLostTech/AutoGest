"""Rear hatch / tailgate of a generic modern small hatchback, removed from the car.
Metallic-grey clear-coated outer skin (same paint as the other body panels) curving in
plan and rolling from the raked window section into the near-vertical lower panel, with a
crisp crease under the glass; bonded, tinted rear window with black ceramic surround and
heater lines; painted roof spoiler lip with a red third brake lamp; recessed number-plate
area with a chrome handle strip above it; rear wiper boss with arm and blade; e-coated
hinges on the top edge and a gas-strut ball stud on the side. Car rear (outside) is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
DEPTH = 0.06
NU, NV = 230, 280
ZT = 0.985

# side profile (rearward distance d, height z), from the roof edge down to the bottom edge
_PROF = P.bspline([(0.0, ZT), (0.11, 0.84), (0.23, 0.66), (0.315, 0.52), (0.358, 0.44),
                   (0.374, 0.34), (0.383, 0.20), (0.386, 0.07), (0.373, 0.0)], 800)
_PZ = [p.y for p in _PROF]
_PD = [p.x for p in _PROF]


def d_of_z(z):
    if z >= _PZ[0]:
        return _PD[0] - (z - _PZ[0]) * 0.75
    if z <= _PZ[-1]:
        return _PD[-1]
    lo, hi = 0, len(_PZ) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if _PZ[m] > z:
            lo = m
        else:
            hi = m
    t = (z - _PZ[lo]) / (_PZ[hi] - _PZ[lo])
    return _PD[lo] + (_PD[hi] - _PD[lo]) * t


def hw(z):
    return 0.505 - 0.05 * max(0.0, z / ZT) ** 1.2


class RRect:
    """Rounded 'rectangle' in (x, z) whose half width varies linearly with z
    (handled in normalized x so the outline polygon and the SDF agree)."""

    def __init__(self, z0, z1, hw0, hw1, rb, rt, cz=0.0):
        self.z0, self.z1, self.hw0, self.hw1, self.rb, self.rt = z0, z1, hw0, hw1, rb, rt

    def hwz(self, z):
        t = (z - self.z0) / (self.z1 - self.z0)
        return self.hw0 + (self.hw1 - self.hw0) * t

    def sdf(self, x, z):
        H = self.hw0
        xn = abs(x) * H / self.hwz(z)
        r = self.rb if z < (self.z0 + self.z1) / 2 else self.rt
        zc = (self.z0 + self.z1) / 2
        hz = (self.z1 - self.z0) / 2
        qx = xn - H + r
        qz = abs(z - zc) - hz + r
        return math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - r

    def poly(self, inset=0.0, n_edge=40, n_arc=16):
        H = self.hw0 - inset
        z0, z1 = self.z0 + inset, self.z1 - inset
        rb, rt = max(0.002, self.rb - inset), max(0.002, self.rt - inset)
        pts = []

        def arc(cx, cz, r, a0, a1):
            for k in range(n_arc):
                a = a0 + (a1 - a0) * k / n_arc
                pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))

        def edge(p, q):
            for k in range(n_edge):
                t = k / n_edge
                pts.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))

        edge((-H + rb, z0), (H - rb, z0))
        arc(H - rb, z0 + rb, rb, -math.pi / 2, 0)
        edge((H, z0 + rb), (H, z1 - rt))
        arc(H - rt, z1 - rt, rt, 0, math.pi / 2)
        edge((H - rt, z1), (-H + rt, z1))
        arc(-H + rt, z1 - rt, rt, math.pi / 2, math.pi)
        edge((-H, z1 - rt), (-H, z0 + rb))
        arc(-H + rb, z0 + rb, rb, math.pi, 1.5 * math.pi)
        return [Vector((xn * self.hwz(z) / self.hw0, z)) for (xn, z) in pts]


GLASS = RRect(0.515, 0.935, 0.452, 0.402, 0.07, 0.10)
PLATE = RRect(0.112, 0.258, 0.282, 0.282, 0.025, 0.025)
FRIT = 0.048          # width of the black ceramic band
OPEN_IN = 0.036       # window opening inset under the band


def D(x, z, recess=True):
    """Rearward distance (towards -Y) of the outer skin."""
    d = d_of_z(z)
    X = x / 0.5
    d -= 0.075 * X * X + 0.02 * X ** 4
    # crease under the glass: crisp at 0.385, soft return at 0.44
    d -= 0.16 * (P.softplus(z - 0.385, 0.0018) - P.softplus(z - 0.445, 0.02))
    if recess:
        # plate recess
        s = PLATE.sdf(x, z)
        d -= 0.013 * (1 - P.sstep(-0.010, 0.003, s))
        # shallow bonding recess the glass sits in
        g = GLASS.sdf(x, z)
        d -= 0.0062 * (1 - P.sstep(0.001, 0.005, g))
    return d


def skin_pt(x, z, recess=True):
    return Vector((x, -D(x, z, recess), z))


def skin_n(q):
    return P.surf_normal(lambda p: skin_pt(p.x, p.y, False), q, sign_ref=OUT)


def lift3(q, dd=0.0):
    """2D (x, z) -> 3D, dd behind the (un-recessed) outer surface."""
    return skin_pt(q.x, q.y, False) - skin_n(q) * dd


def uv(u, v):
    X = 2 * u - 1
    zb = 0.02 * X * X
    ztp = ZT - 0.018 * X * X
    e_b = (1 - abs(X)) * hw(0.0)
    e_t = (1 - abs(X)) * hw(ZT)
    rb, rt = 0.065, 0.11
    if e_b < rb:
        zb += rb * (1 - math.sqrt(max(0.0, 1 - ((rb - e_b) / rb) ** 2)))
    if e_t < rt:
        ztp -= rt * (1 - math.sqrt(max(0.0, 1 - ((rt - e_t) / rt) ** 2)))
    z = zb + (ztp - zb) * v
    return X * hw(z), z


def shell(paint, ecoat):
    rows = []
    for j in range(NV + 1):
        v = j / NV
        rows.append([skin_pt(*uv(i / NU, v)) for i in range(NU + 1)])
    ob = P.grid_obj("TailgateSkin", rows, [paint, ecoat], OUT)
    P.solidify(ob, DEPTH, offset=-1, inner=1, rim=1)
    cb = bmesh.new()
    P.prism_bm(cb, GLASS.poly(OPEN_IN), lift3, -0.04, 0.12)
    C.fix_normals(cb)
    cut = C.mesh_obj("WindowCut", cb, [ecoat])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.005, segments=3, angle=40)
    return C.finalize(ob, angle=40, remove=[cut])


# ------------------------------------------------------------------ rear window
GL_OFF = -0.0006     # glass front face relative to the un-recessed skin (flush)
GL_T = 0.0048


def glass_pt(q, off=0.0):
    return lift3(q, GL_OFF - off)


def window(tint, frit):
    outer = GLASS.poly(0.0)
    inner = GLASS.poly(FRIT)
    rows = []
    for k in range(5):
        t = k / 4
        rows.append([glass_pt(a.lerp(b, t)) for a, b in zip(outer, inner)])
    ring = P.grid_obj("Frit", rows, [frit], OUT, closed_u=True)
    P.solidify(ring, GL_T, offset=-1)
    C.add_bevel(ring, 0.0015, segments=2, angle=50)
    ring = C.finalize(ring, angle=50)
    c = Vector((0.0, (GLASS.z0 + GLASS.z1) / 2))
    gl = P.fan_obj("RearGlass", inner, c, 30, glass_pt, [tint], OUT, power=1.2)
    P.solidify(gl, GL_T, offset=-1)
    gl = C.finalize(gl, angle=60)
    return [ring, gl]


def heater_lines(mat):
    out = []
    zs = [GLASS.z0 + FRIT + 0.022 + k * 0.026 for k in range(13)]
    zs = [z for z in zs if z < GLASS.z1 - FRIT - 0.012]
    bm = bmesh.new()
    for z in zs:
        h = GLASS.hwz(z) - FRIT - 0.03
        pts = [Vector((-h + 2 * h * k / 80, z)) for k in range(81)]
        fr = P.frames_on_surface(pts, lambda q: glass_pt(q, GL_T + 0.0003), OUT)
        P.tube_bm(bm, fr, P.rrect(-0.0005, 0.0005, -0.0002, 0.0002, 0.0001, seg=1))
    for sx in (-1, 1):   # bus bars
        pts = []
        for k in range(41):
            z = zs[0] - 0.006 + (zs[-1] - zs[0] + 0.012) * k / 40
            pts.append(Vector((sx * (GLASS.hwz(z) - FRIT - 0.03), z)))
        fr = P.frames_on_surface(pts, lambda q: glass_pt(q, GL_T + 0.0003), OUT)
        P.tube_bm(bm, fr, P.rrect(-0.006, 0.006, -0.0002, 0.0002, 0.001, seg=1))
    C.fix_normals(bm)
    ob = C.mesh_obj("HeaterLines", bm, [mat])
    return [C.finalize(ob, angle=60)]


# ------------------------------------------------------------------ spoiler
SPOILER_SEC = P.bspline([(-0.018, -0.012), (-0.012, 0.014), (0.03, 0.034), (0.09, 0.033), (0.14, 0.018),
                         (0.158, 0.004), (0.15, -0.006), (0.10, -0.012), (0.05, -0.032), (0.01, -0.07),
                         (-0.012, -0.05)], 64, closed=True)


def spoiler(paint, lamp):
    bm = bmesh.new()
    n = 120
    xe = hw(ZT) - 0.01
    rings = []
    for k in range(n + 1):
        x = -xe + 2 * xe * k / n
        ex = abs(x) - (xe - 0.07)
        sc = math.sqrt(max(0.04, 1 - (ex / 0.07) ** 2)) if ex > 0 else 1.0
        z0 = ZT - 0.018 * (x / 0.5) ** 2 - 0.006
        y0 = -D(x, z0, False) + 0.004
        rings.append([bm.verts.new((x, y0 - a * (0.55 + 0.45 * sc), z0 + b * sc)) for (a, b) in SPOILER_SEC])
    m = len(SPOILER_SEC)
    for i in range(n):
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    C.fix_normals(bm)
    ob = C.mesh_obj("Spoiler", bm, [paint])
    C.add_bevel(ob, 0.002, segments=2, angle=40)
    out = [C.finalize(ob, angle=45)]
    # third brake lamp under the trailing edge
    bm = bmesh.new()
    y0 = -D(0, ZT, False)
    C.box_bm(bm, 0.22, 0.016, 0.011, center=(0, y0 - 0.128, ZT - 0.006 - 0.010))
    lb = C.mesh_obj("BrakeLamp", bm, [lamp])
    C.add_bevel(lb, 0.003, segments=2, angle=30)
    out.append(C.finalize(lb, angle=35))
    return out


# ------------------------------------------------------------------ details
def handle_strip(chrome, rubber):
    out = []
    z = PLATE.z1 + 0.022
    pts = [Vector((-0.20 + 0.40 * k / 100, z)) for k in range(101)]
    fr = P.frames_on_surface(pts, lambda q: lift3(q, 0.0), OUT)
    out.append(P.tube_obj("HandleStrip", fr, P.rrect(-0.012, 0.012, -0.002, 0.0045, 0.003), [chrome], smooth_angle=50))
    # rubber release pad tucked under the strip
    pts = [Vector((-0.045 + 0.09 * k / 30, z - 0.019)) for k in range(31)]
    fr = P.frames_on_surface(pts, lambda q: lift3(q, 0.008), OUT)
    out.append(P.tube_obj("ReleasePad", fr, P.rrect(-0.006, 0.006, -0.004, 0.006, 0.003), [rubber], smooth_angle=50))
    return out


def wiper(black, rubber, metal):
    out = []
    q = Vector((0.0, 0.468))
    o = lift3(q, 0.0)
    n = skin_n(q)
    Zl = n
    Xl = Vector((1, 0, 0))
    Yl = Zl.cross(Xl)
    M = P.basis(Xl, Yl, Zl, o)
    boss = C.lathe("WiperBoss", [(0.0, 0.0, 0), (0.024, 0.0, 0), (0.024, 0.006, 0), (0.019, 0.013, 0),
                                 (0.009, 0.016, 0), (0.0, 0.016, 0)], [rubber], steps=48)
    boss.matrix_world = M
    out.append(C.finalize(boss, angle=40))
    # arm: from the spindle cap, up onto the glass and along its bottom edge (parked)
    cap = C.lathe("WiperCap", [(0.0, 0.012, 0), (0.016, 0.012, 0), (0.016, 0.034, 0), (0.012, 0.040, 0), (0.0, 0.041, 0)],
                  [black], steps=40)
    cap.matrix_world = M
    out.append(C.finalize(cap, angle=40))
    zb = GLASS.z0 + FRIT + 0.022
    path2 = [Vector((0.0, 0.468)), Vector((-0.03, 0.49)), Vector((-0.07, zb)), Vector((-0.15, zb + 0.003))]
    path2 = P.resample(P.bspline(path2, 60), 60)
    fr = P.frames_on_surface(path2, lambda p: lift3(p, -(0.036 - 0.016 * P.sstep(0.48, zb, p.y))), OUT)
    out.append(P.tube_obj("WiperArm", fr, P.rrect(-0.0085, 0.0085, -0.004, 0.004, 0.003), [black], smooth_angle=50))
    # blade along the glass bottom
    pts = [Vector((-0.10 - 0.30 * k / 80, zb + 0.002)) for k in range(81)]
    fr = P.frames_on_surface(pts, lambda p: lift3(p, -0.012), OUT)
    out.append(P.tube_obj("BladeFrame", fr, [(-0.007, -0.006), (0.007, -0.006), (0.006, 0.004), (0.0, 0.009), (-0.006, 0.004)],
                          [black], smooth_angle=60))
    fr = P.frames_on_surface(pts, lambda p: lift3(p, -0.003), OUT)
    out.append(P.tube_obj("BladeRubber", fr, [(-0.0015, -0.003), (0.0015, -0.003), (0.003, 0.003), (-0.003, 0.003)],
                          [rubber], smooth_angle=60))
    return out


def hinges(metal):
    out = []
    for sx in (-1, 1):
        x = sx * 0.33
        z0 = ZT - 0.018 * (x / 0.5) ** 2
        y0 = -D(x, z0, False)
        bm = bmesh.new()
        C.box_bm(bm, 0.05, 0.075, 0.006, center=(x, y0 + 0.05, z0 - 0.004))            # leaf on the tailgate
        C.cyl_bm(bm, 0.011, -0.03, 0.03, seg=32,
                 matrix=Matrix.Translation((x, y0 + 0.09, z0 + 0.004)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
        C.box_bm(bm, 0.05, 0.06, 0.006, center=(0, 0.03, 0),
                 matrix=Matrix.Translation((x, y0 + 0.09, z0 + 0.004)) @ Matrix.Rotation(math.radians(8), 4, "X"))
        for dy in (0.032, 0.062):
            C.cyl_bm(bm, 0.0085, z0 - 0.001, z0 + 0.005, seg=6, matrix=Matrix.Translation((x, y0 + dy, 0)))
        ob = C.mesh_obj("Hinge", bm, [metal])
        C.add_bevel(ob, 0.002, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


def strut_stud(metal):
    """Gas-strut ball stud on the left side rim, in the middle of the box section."""
    out = []
    z = 0.62
    x = -hw(z)
    e = skin_pt(x, z, False)
    n = skin_n(Vector((x, z)))
    c = e - n * (DEPTH * 0.55) + Vector((-0.002, 0, 0))
    bm = bmesh.new()
    M = Matrix.Translation(c) @ Matrix.Rotation(math.radians(-90), 4, "Y")
    C.cyl_bm(bm, 0.012, 0.0, 0.006, seg=6, matrix=M)
    C.cyl_bm(bm, 0.0045, 0.006, 0.018, seg=24, matrix=M)
    ob = C.mesh_obj("StudBase", bm, [metal])
    C.add_bevel(ob, 0.001, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0065, segments=32, ring_count=16, location=c + Vector((-0.022, 0, 0)))
    ball = bpy.context.active_object
    ball.data.materials.append(metal)
    out.append(C.finalize(ball, angle=60))
    return out


def privacy_glass():
    """Dark tinted rear glass: clear glass mixed with a glossy near-black component so
    the view through it stays dim on any background."""
    m = C.mat_clear("RearGlassTint", ior=1.52)
    nt = m.node_tree
    a = P.bsdf(m)
    C._set(a, "Base Color", (0.30, 0.35, 0.34, 1))
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.006, 0.008, 0.008, 1)
    b.inputs["Roughness"].default_value = 0.03
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.5
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build():
    paint = P.body_paint()
    ec = P.ecoat()
    rubber = C.mat_rubber()
    chrome = C.mat_chrome()
    black = C.mat_black_plastic("WiperBlack", rough=0.4)
    metal = C.principled("HingeEcoat", (0.05, 0.052, 0.056), metallic=0.4, rough=0.42)
    zinc = C.principled("Zinc", (0.6, 0.6, 0.62), metallic=1.0, rough=0.3)
    tint = privacy_glass()
    frit = C.principled("CeramicFrit", (0.008, 0.008, 0.009), rough=0.06)
    heater = C.principled("HeaterPrint", (0.05, 0.03, 0.022), rough=0.5)
    lamp = C.principled("RedLamp", (0.55, 0.015, 0.02), rough=0.08, Coat_Weight=1.0)
    objs = [shell(paint, ec)]
    objs += window(tint, frit)
    objs += heater_lines(heater)
    objs += spoiler(paint, lamp)
    objs += handle_strip(chrome, rubber)
    objs += wiper(black, rubber, zinc)
    objs += hinges(metal)
    objs += strut_stud(zinc)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("portellone", objs, "portellone.py",
            "rear hatch/tailgate (generic small hatchback), metallic grey paint: curved skin with crease, tinted rear window "
            "with black ceramic surround and heater lines, roof spoiler lip with third brake lamp, number-plate recess, "
            "rear wiper, top hinges",
            az=-34, el=16, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
