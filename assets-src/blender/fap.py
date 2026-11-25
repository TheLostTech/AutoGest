"""Diesel particulate filter (FAP/DPF) with close-coupled oxidation catalyst: long round
stainless canister in two welded sections (short oxicat brick + long filter brick)
joined by a clamping band, deep-drawn end cones, full-length heat shield with
stamped longitudinal beads, three-bolt inlet flange on a short bent pipe, two-bolt
outlet flange, two small steel differential-pressure pipes running from the cones
to a bracket on the shield with union nuts, two exhaust-temperature sensor bosses,
sooty heat-tinted steel."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 96
RP = 0.085                  # main pipe radius
RC = 0.30                   # canister radius (round section)
X0, X1 = -0.62, 0.66        # canister cylinder ends
XB = -0.26                  # joint band between oxicat and filter sections
XI, XO = -0.92, 0.96        # cone small ends


# ----------------------------------------------------------------- helpers
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


def tube(name, pts, r, mat, res=3, caps=True):
    """Smooth bezier tube through pts (auto handles)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    cu.resolution_u = 16
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, "X")


def ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Y")


# ----------------------------------------------------------------- materials
def mat_sooty_steel(name, base=0.46, rough=0.42, amount=0.9):
    """Stainless with heavy heat tint (bronze/blue-grey) and dull soot film, stronger
    toward the inlet end (-X)."""
    m = C.principled(name, (base, base, base * 1.01), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.2
    mr.inputs["From Max"].default_value = 1.1
    mr.inputs["To Min"].default_value = amount
    mr.inputs["To Max"].default_value = 0.12
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.6
    nz.inputs["Detail"].default_value = 8.0
    ma = nt.nodes.new("ShaderNodeMath")
    ma.operation = "MULTIPLY_ADD"
    ma.inputs[1].default_value = 0.6
    ma.inputs[2].default_value = -0.30
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
    cr.elements[1].color = (0.16, 0.15, 0.17, 1)
    for pos, col in ((0.25, (base * 0.95, base * 0.92, base * 0.86)), (0.45, (0.44, 0.36, 0.26)),
                     (0.62, (0.34, 0.25, 0.22)), (0.80, (0.22, 0.21, 0.27))):
        e = cr.elements.new(pos)
        e.color = col + (1,)
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.22
    nt.links.new(add.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 650.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.06
    bp.inputs["Distance"].default_value = 0.0005
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_shield(name="HeatShield"):
    """Aluminised steel heat shield: matte, fine orange-peel, mottled light heat tint."""
    m = C.principled(name, (0.62, 0.62, 0.61), metallic=1.0, rough=0.38)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    vo.inputs["Scale"].default_value = 90.0
    vo.inputs["Randomness"].default_value = 0.6
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.18
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.30
    mr.inputs["To Max"].default_value = 0.52
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.62, 0.62, 0.61, 1)
    mix.inputs["B"].default_value = (0.50, 0.44, 0.36, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.52
    mr2.inputs["From Max"].default_value = 0.80
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
def canister(steel):
    """Round body lathed around X: inlet cone, oxicat section, band, filter section, outlet cone."""
    P = []

    def cone(xa, xb, ra, rb, k=16):
        for i in range(k + 1):
            t = i / k
            e = t * t * (3 - 2 * t)
            P.append((ra + (rb - ra) * e, xa + (xb - xa) * t, 0))

    P.append((0.0, XI - 0.01, 0))
    P.append((RP + 0.004, XI - 0.01, 0))
    cone(XI, X0, RP + 0.004, RC)
    # rolled weld seam at the cone joint
    P += [(RC + 0.012, X0 + 0.010, 0), (RC + 0.012, X0 + 0.024, 0), (RC, X0 + 0.034, 0)]
    # oxicat section, then the joint band (raised), then filter section
    P += [(RC, XB - 0.06, 0), (RC + 0.020, XB - 0.05, 0), (RC + 0.022, XB - 0.035, 0), (RC + 0.012, XB - 0.02, 0),
          (RC + 0.012, XB + 0.02, 0), (RC + 0.022, XB + 0.035, 0), (RC + 0.020, XB + 0.05, 0), (RC, XB + 0.06, 0)]
    P += [(RC, X1 - 0.034, 0), (RC + 0.012, X1 - 0.024, 0), (RC + 0.012, X1 - 0.010, 0)]
    cone(X1, XO, RC, RP + 0.004)
    P.append((RP + 0.004, XO + 0.01, 0))
    P.append((0.0, XO + 0.01, 0))
    # lathe builds around Z: rotate so the axis is X
    return lathe_at("Canister", P, [steel], ry(90), steps=N, angle=38)


def shield(mat):
    """Half-shell over the top of the filter, offset from the body, with stamped
    longitudinal beads and turned-down ends."""
    xa, xb = XB + 0.09, X1 - 0.05
    a0, a1 = math.radians(-25), math.radians(205)
    nx, na = 70, 150
    beads = [math.radians(d) for d in (20, 50, 75, 105, 130, 160)]
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        x = xa + (xb - xa) * i / nx
        de = min(x - xa, xb - x)
        fall = C.smoothstep(0.0, 0.05, de)
        row = []
        for j in range(na + 1):
            a = a0 + (a1 - a0) * j / na
            r = RC + 0.014 + 0.030 * fall
            bw = C.smoothstep(0.02, 0.10, de)
            for ab in beads:
                r += 0.016 * bw * math.exp(-((a - ab) / 0.035) ** 2)
            # small skirt flare at the long edges
            ed = min(a - a0, a1 - a)
            r += 0.010 * (1 - C.smoothstep(0.0, 0.12, ed))
            row.append(bm.verts.new((x, r * math.cos(a), r * math.sin(a))))
        rows.append(row)
    for i in range(nx):
        for j in range(na):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bm.normal_update()
    if sum(f.normal.z * f.calc_area() for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = C.mesh_obj("Shield", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.008
    so.offset = -1
    C.add_bevel(ob, 0.003, segments=2, angle=40)
    out = [C.finalize(ob, angle=60)]
    # spot-welded straps holding the shield
    for x in (XB + 0.22, X1 - 0.16):
        out.append(lathe_at("Strap", [(RC + 0.040, -0.022, 0), (RC + 0.054, -0.022, 0), (RC + 0.058, 0.0, 0),
                                      (RC + 0.054, 0.022, 0), (RC + 0.040, 0.022, 0)], [mat],
                            T((x, 0, 0)) @ ry(90), steps=N, angle=40))
    return out


def flange3(name, P, t, b, mat):
    """Three-bolt triangular inlet flange, outer face flush with P."""
    poly = resample(hull2d(circle_pts(0, 0, 0.150, 64) + sum((circle_pts(0.20 * math.cos(a), 0.20 * math.sin(a), 0.058, 32)
                                                                for a in (math.radians(90), math.radians(210), math.radians(330))), [])), 160)
    M = frame_matrix(P, b, t)
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (-0.05, 0.0)]
    ob = loft(name, fr, mat)
    ob.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, RP - 0.006, -0.3, 0.2, seg=48)
    for a in (90, 210, 330):
        a = math.radians(a)
        C.cyl_bm(cb, 0.026, -0.3, 0.2, seg=32, matrix=T((0.20 * math.cos(a), 0.20 * math.sin(a), 0)))
    cut = C.mesh_obj(name + "Cut", cb, [mat])
    cut.matrix_world = M
    C.add_boolean(ob, cut).use_self = True
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def flange2(name, P, t, b, mat):
    poly = resample(hull2d(circle_pts(0, 0, 0.150, 64) + circle_pts(0.215, 0, 0.066, 32) + circle_pts(-0.215, 0, 0.066, 32)), 128)
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
    C.add_boolean(ob, cut).use_self = True
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def temp_boss(name, M, steel, thread, dark):
    """Weld boss (local +Z out of the surface) with a threaded sensor port."""
    out = []
    P = [(0.0, 0.035, 2), (0.024, 0.035, 1), (0.024, 0.075, 1), (0.034, 0.075, 0), (0.040, 0.069, 0),
         (0.040, -0.03, 0), (0.0, -0.03, 0)]
    out.append(lathe_at(name, P, [steel, thread, dark], M, steps=48, bevel=0.003))
    return out


def dp_pipe(name, pts, steel, brass):
    """Small differential-pressure steel pipe with a weld boss at the start and a union nut
    at the end."""
    out = [tube(name, pts, 0.016, steel, res=3)]
    p0, p1 = Vector(pts[0]), Vector(pts[1])
    d = (p1 - p0).normalized()
    M = frame_matrix(p0, d.orthogonal(), d)
    out.append(lathe_at(name + "Boss", [(0.0, -0.03, 0), (0.036, -0.03, 0), (0.036, 0.03, 0), (0.026, 0.045, 0), (0.0, 0.045, 0)],
                        [steel], M, steps=32, bevel=0.003))
    q0, q1 = Vector(pts[-1]), Vector(pts[-2])
    d = (q0 - q1).normalized()
    M = frame_matrix(q0, d.orthogonal(), d)
    out.append(hex_at(name + "Nut", 0.034, -0.05, 0.0, brass, M, bevel=0.004))
    out.append(lathe_at(name + "Tip", [(0.0, 0.0, 0), (0.020, 0.0, 0), (0.020, 0.04, 0), (0.012, 0.05, 0), (0.0, 0.05, 0)],
                        [brass], M, steps=24))
    return out


def build():
    steel = mat_sooty_steel("FapSteel", base=0.46, rough=0.40, amount=0.85)
    pipe_m = mat_sooty_steel("PipeSteel", base=0.44, rough=0.42, amount=0.95)
    shield_m = mat_shield()
    fl_m = C.mat_cast_iron("FlangeSteel", rust=0.5, base=0.17)
    thread = mat_thread()
    small = C.principled("DpSteel", (0.46, 0.46, 0.47), metallic=1.0, rough=0.34)
    C.add_noise_bump(small, scale=500, strength=0.04, distance=0.0004, rough_var=0.06)
    zinc = C.principled("ZincNut", (0.62, 0.58, 0.44), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=700, strength=0.04, distance=0.0004)
    dark = C.principled("Bore", (0.02, 0.02, 0.02), rough=0.7)

    objs = [canister(steel)]
    objs += shield(shield_m)
    # inlet: short straight, bend up, three-bolt flange (bolts to the turbo downpipe)
    pts, b = path_pts((XI, 0, 0), (-1, 0, 0), (0, 0, 1), [("L", 0.08), ("A", 0.22, 45), ("L", 0.07)])
    objs.append(pipe("InletPipe", pts, b, RP, pipe_m))
    P, t = pts[-1]
    objs.append(flange3("InletFlange", P, t, b, fl_m))
    # outlet: straight, slight drop, two-bolt flange
    pts, b = path_pts((XO, 0, 0), (1, 0, 0), (0, 0, -1), [("L", 0.12), ("A", 0.4, 8), ("L", 0.06)])
    objs.append(pipe("OutletPipe", pts, b, RP, pipe_m))
    P, t = pts[-1]
    objs.append(flange2("OutletFlange", P, t, b, fl_m))

    # differential pressure pipes: from the two cones, up over the shield to a bracket
    ci = Vector((XI + 0.13, -0.13, 0.11))
    co = Vector((XO - 0.12, -0.12, 0.12))
    bx, by, bz = 0.02, -0.12, RC + 0.135
    p_in = [tuple(ci), (ci.x + 0.02, ci.y - 0.03, ci.z + 0.10), (X0 + 0.04, -0.17, 0.28), (XB - 0.04, -0.15, 0.30),
            (XB + 0.12, -0.15, RC + 0.08),
            (bx - 0.05, by - 0.03, bz)]
    p_out = [tuple(co), (co.x - 0.02, co.y - 0.03, co.z + 0.10), (X1 - 0.03, -0.14, RC + 0.11), (0.30, -0.08, RC + 0.105),
             (bx + 0.05, by + 0.03, bz)]
    p_in.append((bx - 0.05, by - 0.03, bz + 0.07))
    p_out.append((bx + 0.05, by + 0.03, bz + 0.07))
    objs += dp_pipe("DpIn", p_in, small, zinc)
    objs += dp_pipe("DpOut", p_out, small, zinc)
    # bracket spot-welded to the shield that holds both pipe ends
    bm = bmesh.new()
    C.box_bm(bm, 0.24, 0.10, 0.012, center=(bx, by, bz + 0.012))
    C.box_bm(bm, 0.20, 0.012, 0.11, center=(bx, by + 0.05, bz - 0.04))
    br = C.mesh_obj("Bracket", bm, [small])
    cb = bmesh.new()
    for (dx, dy) in ((-0.05, -0.03), (0.05, 0.03)):
        C.cyl_bm(cb, 0.019, bz - 0.1, bz + 0.1, seg=24, matrix=T((bx + dx, by + dy, 0)))
    cut = C.mesh_obj("BracketCut", cb, [small])
    C.add_boolean(br, cut).use_self = True
    C.add_bevel(br, 0.004, segments=2, angle=30)
    objs.append(C.finalize(br, angle=35, remove=[cut]))

    # exhaust-temperature sensor bosses: upstream on the inlet pipe, mid on the band
    objs += temp_boss("TempBoss1", T((XI + 0.10, -0.125 * 0.866, 0.125 * 0.5)) @ rx(60), pipe_m, thread, dark)
    a = math.radians(145)
    objs += temp_boss("TempBoss2", T((XB - 0.13, (RC - 0.01) * math.cos(a), (RC - 0.01) * math.sin(a))) @ rx(55),
                      steel, thread, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("fap", objs, "fap.py",
            "diesel particulate filter (DPF): large round stainless canister with oxidation-catalyst section, ribbed heat "
            "shield, three-bolt inlet and two-bolt outlet flanges, differential-pressure pipes, temperature sensor bosses",
            az=40, el=30, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
