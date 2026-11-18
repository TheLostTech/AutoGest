"""Catalytic converter: oval stainless canister with welded end cones and seam beads,
dimpled heat shield over the top, inlet pipe bending up to a two-bolt flange, outlet
pipe with its own flange, two lambda-sensor weld bosses, heat-discoloured steel."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
RP = 0.085                    # pipe radius
W, H, NS = 0.50, 0.34, 2.4    # canister section (Y width, Z height, superellipse exp)
X0, X1 = -0.42, 0.42          # canister ends


# ----------------------------------------------------------------- helpers
def oval(w, h, n=2.0, N=N):
    pts = []
    for k in range(N):
        a = TAU * k / N
        c, s = math.cos(a), math.sin(a)
        pts.append((w / 2 * math.copysign(abs(c) ** (2 / n), c), h / 2 * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def resample(poly, n):
    L = [0.0]
    P = poly + [poly[0]]
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


def loft(name, frames, mat, cap=True):
    bm = bmesh.new()
    C.sweep(bm, frames, cap=cap)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def frame_matrix(P, X, Z):
    X, Z = X.normalized(), Z.normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P.x), (X.y, Y.y, Z.y, P.y), (X.z, Y.z, Z.z, P.z), (0, 0, 0, 1)))


def path_pts(start, d, n, segs, step=0.02):
    """Planar pipe centre-line: segs = [('L', len) | ('A', radius, deg)] bending toward n."""
    P = Vector(start)
    d = Vector(d).normalized()
    n = Vector(n).normalized()
    b = d.cross(n).normalized()
    pts = [(P.copy(), d.copy())]
    for s in segs:
        if s[0] == "L":
            k = max(1, int(s[1] / step))
            for i in range(1, k + 1):
                pts.append((P + d * (s[1] * i / k), d.copy()))
            P = P + d * s[1]
        else:
            R, ang = s[1], math.radians(s[2])
            Cc = P + n * R
            k = max(2, int(R * abs(ang) / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, b)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, b)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts, b


def pipe(name, pts, b, r, mat, wall=0.009):
    sec = circle_pts(0, 0, r, 48)
    fr = [(P, b, t.cross(b), sec) for (P, t) in pts]
    ob = loft(name, fr, mat, cap=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


# ----------------------------------------------------------------- materials
def mat_heat_steel(name, base=0.56, rough=0.30, xhot=-1.15, xcold=0.55, amount=0.95):
    """Stainless with heat tint (straw -> bronze -> purple/blue) growing toward the inlet."""
    m = C.principled(name, (base, base, base * 1.01), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = xhot
    mr.inputs["From Max"].default_value = xcold
    mr.inputs["To Min"].default_value = amount
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.2
    nz.inputs["Detail"].default_value = 7.0
    ma = nt.nodes.new("ShaderNodeMath")
    ma.operation = "MULTIPLY_ADD"
    ma.inputs[1].default_value = 0.55
    ma.inputs[2].default_value = -0.27
    nt.links.new(nz.outputs["Fac"], ma.inputs[0])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.use_clamp = True
    nt.links.new(mr.outputs["Result"], add.inputs[0])
    nt.links.new(ma.outputs[0], add.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (base, base, base * 1.01, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.27, 0.29, 0.36, 1)
    for pos, col in ((0.32, (base, base, base * 1.01)), (0.48, (0.58, 0.52, 0.40)), (0.64, (0.47, 0.37, 0.28)),
                     (0.82, (0.35, 0.29, 0.33))):
        e = cr.elements.new(pos)
        e.color = col + (1,)
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.06
    rr.inputs["To Max"].default_value = rough + 0.16
    nt.links.new(add.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 650.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.05
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_shield(name="HeatShield"):
    """Embossed (dimpled) aluminised heat shield, slightly heat tinted."""
    m = C.principled(name, (0.66, 0.66, 0.65), metallic=1.0, rough=0.32)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    vo.inputs["Scale"].default_value = 42.0
    vo.inputs["Randomness"].default_value = 0.2
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 0.005
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.24
    mr.inputs["To Max"].default_value = 0.45
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.66, 0.66, 0.65, 1)
    mix.inputs["B"].default_value = (0.58, 0.50, 0.40, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.78
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_thread(name="Thread"):
    m = C.principled(name, (0.30, 0.28, 0.26), metallic=1.0, rough=0.45)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 140.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.8
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def body(steel):
    fr = []

    def add(x, w, h, n):
        fr.append((Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), oval(w, h, n)))

    def cone(xa, xb, rev):
        k = 14
        for i in range(k + 1):
            t = i / k
            e = t * t * (3 - 2 * t)
            x = xa + (xb - xa) * t
            f = (1 - e) if rev else e
            add(x, 2 * RP + 0.006 + (W - 2 * RP - 0.006) * f, 2 * RP + 0.006 + (H - 2 * RP - 0.006) * f, 2.0 + (NS - 2.0) * f)

    add(-0.72, 2 * RP + 0.006, 2 * RP + 0.006, 2.0)
    cone(-0.70, X0, False)
    for x, g in ((X0 + 0.004, 0.018), (X0 + 0.016, 0.018), (X0 + 0.024, 0.0)):
        add(x, W + g, H + g, NS)
    for x, g in ((X1 - 0.024, 0.0), (X1 - 0.016, 0.018), (X1 - 0.004, 0.018)):
        add(x, W + g, H + g, NS)
    cone(X1, 0.70, True)
    add(0.72, 2 * RP + 0.006, 2 * RP + 0.006, 2.0)
    ob = loft("Canister", fr, steel)
    return C.finalize(ob, angle=40)


def shield(mat):
    off0 = 0.032
    xa, xb = -0.355, 0.355
    a0, a1 = math.radians(-32), math.radians(212)
    nx, na = 90, 72
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        x = xa + (xb - xa) * i / nx
        de = min(x - xa, xb - x)
        off = 0.012 + (off0 - 0.012) * C.smoothstep(0.0, 0.03, de)
        for xb_ in (-0.22, -0.075, 0.075, 0.22):
            off += 0.011 * math.exp(-((x - xb_) / 0.016) ** 2)
        row = []
        for j in range(na + 1):
            a = a0 + (a1 - a0) * j / na
            c, s = math.cos(a), math.sin(a)
            w, h = W + 2 * off, H + 2 * off
            y = w / 2 * math.copysign(abs(c) ** (2 / NS), c)
            z = h / 2 * math.copysign(abs(s) ** (2 / NS), s)
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for i in range(nx):
        for j in range(na):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bm.normal_update()
    if sum(f.normal.z * f.calc_area() for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = C.mesh_obj("Shield", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.007
    so.offset = -1
    C.add_bevel(ob, 0.003, segments=2, angle=40)
    return C.finalize(ob, angle=60)


def flange(name, P, t, b, mat, mat_bolt=None):
    """Two-bolt diamond flange whose outer face is flush with the pipe end P (tangent t)."""
    poly = resample(hull2d(circle_pts(0, 0, 0.155, 64) + circle_pts(0.215, 0, 0.066, 32) + circle_pts(-0.215, 0, 0.066, 32)), 128)
    M = frame_matrix(P, b, t)
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (-0.045, 0.0)]
    ob = loft(name, fr, mat)
    ob.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, RP - 0.006, -0.3, 0.2, seg=48)
    for sx in (-1, 1):
        C.cyl_bm(cb, 0.030, -0.3, 0.2, seg=32, matrix=T((sx * 0.215, 0, 0)))
    cut = C.mesh_obj(name + "Cut", cb, [mat])
    cut.matrix_world = M
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def boss(name, at, steel, thread):
    z0, z1 = RP - 0.03, RP + 0.05
    P = [(0.0, z1 - 0.03, 1), (0.027, z1 - 0.03, 1), (0.027, z1, 0), (0.049, z1, 0), (0.054, z1 - 0.006, 0),
         (0.054, z0, 0), (0.0, z0, 0)]
    return lathe_at(name, P, [steel, thread], T(at), steps=48, bevel=0.003)


def build():
    steel = mat_heat_steel("HeatSteel", rough=0.36, amount=0.85)
    pipe_m = mat_heat_steel("PipeSteel", base=0.50, rough=0.40, amount=0.9)
    fl_m = C.mat_cast_iron("FlangeSteel", rust=0.55, base=0.17)
    thread = mat_thread()
    objs = [body(steel), shield(mat_shield())]
    # inlet: straight, bend up, short straight -> flange
    pts, b = path_pts((-0.70, 0, 0), (-1, 0, 0), (0, 0, 1), [("L", 0.15), ("A", 0.24, 38), ("L", 0.10)])
    objs.append(pipe("InletPipe", pts, b, RP, pipe_m))
    P, t = pts[-1]
    objs.append(flange("InletFlange", P, t, b, fl_m))
    # outlet: straight with a slight drop -> flange
    pts, b = path_pts((0.70, 0, 0), (1, 0, 0), (0, 0, -1), [("L", 0.10), ("A", 0.35, 10), ("L", 0.08)])
    objs.append(pipe("OutletPipe", pts, b, RP, pipe_m))
    P, t = pts[-1]
    objs.append(flange("OutletFlange", P, t, b, fl_m))
    # lambda sensor bosses (pre-cat on inlet pipe, post-cat on outlet cone)
    objs.append(boss("Boss1", (-0.78, 0, 0), pipe_m, thread))
    objs.append(boss("Boss2", (0.79, 0, -0.004), pipe_m, thread))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("catalizzatore", objs, "catalizzatore.py",
            "car catalytic converter: oval stainless canister with dimpled heat shield, inlet and outlet pipes "
            "with two-bolt flanges, lambda sensor bosses, heat-discoloured steel",
            az=48, el=28, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
