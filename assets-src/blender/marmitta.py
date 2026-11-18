"""Rear exhaust silencer: flattened-oval muffler box with rolled end seams and a lock seam,
long inlet pipe with a bend and an expanded slip-joint end, short tailpipe with a rolled
lip, steel hanger pins (one wearing a rubber hanger), aluminised steel with heat tint and
light surface rust."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
W, H, NS = 0.58, 0.30, 2.9    # box section (Y width, Z height, superellipse exponent)
XL = 0.48                     # half length of the box
RI, RT = 0.050, 0.055         # inlet / tailpipe radius


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


def boxes(name, specs, mat, bevel=0.01, holes=(), seg=2, M=None):
    """specs: [(sx, sy, sz, center[, matrix])]; holes: [(r, z0, z1, matrix)] boolean cylinders."""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, z0, z1, HM) in holes:
            C.cyl_bm(cb, r, z0, z1, seg=32, matrix=HM)
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2):
    """Extrude a 2D polygon along local Z, optional boolean holes [(r, cx, cy)] through it."""
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (z0, z1)]
    ob = loft(name, fr, mat)
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
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


# ----------------------------------------------------------------- materials
def mat_aluminised(name, base=0.50, rough=0.48, rust=0.5, heat=0.0, xhot=-1.4, xcold=0.0):
    """Hot-dip aluminised steel: matte silver-grey, mottled, heat tint toward the engine,
    orange-brown rust freckles concentrated on edges and seams."""
    m = C.principled(name, (base, base, base * 0.99), metallic=0.9, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 5.0
    mott.inputs["Detail"].default_value = 8.0
    c1 = nt.nodes.new("ShaderNodeMix")
    c1.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], c1.inputs["Factor"])
    c1.inputs["A"].default_value = (base * 0.68, base * 0.66, base * 0.62, 1)
    c1.inputs["B"].default_value = (base * 1.08, base * 1.08, base * 1.07, 1)
    last = c1.outputs["Result"]
    if heat:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        hr = nt.nodes.new("ShaderNodeMapRange")
        hr.inputs["From Min"].default_value = xhot
        hr.inputs["From Max"].default_value = xcold
        hr.inputs["To Min"].default_value = heat
        hr.inputs["To Max"].default_value = 0.0
        nt.links.new(sep.outputs["X"], hr.inputs["Value"])
        hm = nt.nodes.new("ShaderNodeMath")
        hm.operation = "MULTIPLY"
        hm.use_clamp = True
        nt.links.new(hr.outputs["Result"], hm.inputs[0])
        nt.links.new(mott.outputs["Fac"], hm.inputs[1])
        c2 = nt.nodes.new("ShaderNodeMix")
        c2.data_type = "RGBA"
        nt.links.new(hm.outputs[0], c2.inputs["Factor"])
        nt.links.new(last, c2.inputs["A"])
        c2.inputs["B"].default_value = (0.42, 0.30, 0.20, 1)
        last = c2.outputs["Result"]
    # rust freckles: fine noise threshold, boosted on edges
    sp = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), sp.inputs["Vector"])
    sp.inputs["Scale"].default_value = 38.0
    sp.inputs["Detail"].default_value = 10.0
    sp.inputs["Roughness"].default_value = 0.65
    em = C.edge_mask(nt, 0.02, 5.0)
    ad = nt.nodes.new("ShaderNodeMath")
    ad.operation = "MULTIPLY_ADD"
    ad.inputs[1].default_value = 0.16
    nt.links.new(em, ad.inputs[0])
    nt.links.new(sp.outputs["Fac"], ad.inputs[2])
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.60
    th.inputs["From Max"].default_value = 0.74
    th.inputs["To Max"].default_value = rust
    nt.links.new(ad.outputs[0], th.inputs["Value"])
    c3 = nt.nodes.new("ShaderNodeMix")
    c3.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], c3.inputs["Factor"])
    nt.links.new(last, c3.inputs["A"])
    c3.inputs["B"].default_value = (0.24, 0.085, 0.03, 1)
    nt.links.new(c3.outputs["Result"], b.inputs["Base Color"])
    mt = nt.nodes.new("ShaderNodeMapRange")
    mt.inputs["To Min"].default_value = 0.9
    mt.inputs["To Max"].default_value = 0.1
    nt.links.new(th.outputs["Result"], mt.inputs["Value"])
    nt.links.new(mt.outputs["Result"], b.inputs["Metallic"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.12
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    rm = nt.nodes.new("ShaderNodeMix")
    nt.links.new(th.outputs["Result"], rm.inputs["Factor"])
    nt.links.new(rr.outputs["Result"], rm.inputs["A"])
    rm.inputs["B"].default_value = 0.85
    nt.links.new(rm.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 420.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def box(mat):
    fr = []

    def add(x, s, g=0.0):
        fr.append((Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), oval(W * s + g, H * s + g, NS)))

    # left end plate (slightly domed), rolled seam, body, rolled seam, right end plate
    add(-XL - 0.020, 0.55)
    add(-XL - 0.018, 0.80)
    add(-XL - 0.012, 0.93)
    add(-XL - 0.006, 0.96, 0.020)
    add(-XL + 0.010, 0.96, 0.024)
    add(-XL + 0.020, 1.0, 0.004)
    add(-XL + 0.030, 1.0)
    for i in range(1, 8):
        x = -XL + 0.03 + (2 * XL - 0.06) * i / 8
        add(x, 1.0 + 0.012 * math.sin(math.pi * i / 8))
    add(XL - 0.030, 1.0)
    add(XL - 0.020, 1.0, 0.004)
    add(XL - 0.010, 0.96, 0.024)
    add(XL + 0.006, 0.96, 0.020)
    add(XL + 0.012, 0.93)
    add(XL + 0.018, 0.80)
    add(XL + 0.020, 0.55)
    ob = loft("Box", fr, mat)
    C.add_bevel(ob, 0.002, segments=1, angle=50)
    out = [C.finalize(ob, angle=38)]
    # longitudinal lock seam on the front face
    out.append(boxes("LockSeam", [(2 * XL - 0.07, 0.024, 0.042, (0, -W / 2 - 0.004, -0.02))], mat, bevel=0.008))
    return out


def ring(name, r_in, r_out, z0, z1, mat, M):
    P = [(r_in, z0, 0), (r_out, z0, 0), (r_out + 0.004, (z0 + z1) / 2, 0), (r_out, z1, 0), (r_in, z1, 0)]
    return lathe_at(name, P, [mat], M, steps=48)


def pin(name, pts, mat, r=0.011):
    out = [tube(name, pts, r, mat, res=3)]
    tip = Vector(pts[-1])
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r * 1.6, matrix=T(tip))
    out.append(C.mesh_obj(name + "Tip", bm, [mat]))
    return out


def rubber_hanger(rub, M):
    poly = rrect(0.10, 0.22, 0.045, 8)
    return prism("Hanger", poly, -0.018, 0.018, rub, M=M, bevel=0.008,
                 holes=[(0.016, 0.0, -0.068), (0.016, 0.0, 0.068)])


def build():
    body_m = mat_aluminised("BoxSteel", base=0.40, rust=0.75, heat=0.35)
    pipe_m = mat_aluminised("PipeSteel", base=0.38, rust=0.8, heat=0.9)
    pin_m = mat_aluminised("PinSteel", base=0.34, rust=0.7)
    rub = C.mat_rubber("HangerRubber")
    objs = box(body_m)
    # inlet: from the left end plate, straight then bending toward +Y; expanded slip-joint end
    pts, b = path_pts((-XL + 0.04, -0.10, 0.0), (-1, 0, 0), (0, 1, 0),
                      [("L", 0.28), ("A", 0.30, 28), ("L", 0.42)])
    objs.append(pipe("InletPipe", pts, b, RI, pipe_m, wall=0.006))
    P, t = pts[-1]
    M = frame_matrix(P, b, t)
    sl = [(RI - 0.002, -0.10, 0), (RI + 0.004, -0.10, 0), (RI + 0.012, -0.085, 0), (RI + 0.012, 0.0, 0),
          (RI + 0.006, 0.0, 0), (RI + 0.006, -0.08, 0), (RI - 0.002, -0.095, 0)]
    objs.append(lathe_at("SlipJoint", sl, [pipe_m], M, steps=64))
    # tailpipe: out of the right end plate, slight kink toward -Y, rolled lip
    pts, b = path_pts((XL - 0.04, 0.12, -0.03), (1, 0, 0), (0, -1, 0), [("L", 0.16), ("A", 0.25, 14), ("L", 0.12)])
    objs.append(pipe("Tailpipe", pts, b, RT, pipe_m, wall=0.006))
    P, t = pts[-1]
    objs.append(ring("TailLip", RT - 0.006, RT + 0.006, -0.012, 0.0, pipe_m, frame_matrix(P, b, t)))
    # weld collars where the pipes enter the end plates
    objs.append(ring("Collar1", RI - 0.004, RI + 0.014, -0.015, 0.015, body_m,
                     T((-XL - 0.02, -0.10, 0.0)) @ Matrix.Rotation(math.radians(-90), 4, "Y")))
    objs.append(ring("Collar2", RT - 0.004, RT + 0.014, -0.015, 0.015, body_m,
                     T((XL + 0.02, 0.12, -0.03)) @ Matrix.Rotation(math.radians(90), 4, "Y")))
    # hanger pin on the box top with a rubber hanger hung on it
    zt = H / 2
    p1 = [(0.24, -0.06, zt - 0.01), (0.24, -0.06, zt + 0.07), (0.24, -0.12, zt + 0.10), (0.24, -0.30, zt + 0.10)]
    objs += pin("Pin1", p1, pin_m)
    objs.append(boxes("Pin1Pad", [(0.07, 0.07, 0.012, (0.24, -0.06, zt + 0.002))], pin_m, bevel=0.004))
    objs.append(rubber_hanger(rub, T((0.24, -0.26, zt + 0.10 + 0.068)) @ Matrix.Rotation(math.radians(90), 4, "X")))
    # hanger pin welded to the inlet pipe, pointing forward (-Y)
    xi = -XL - 0.12
    p2 = [(xi, -0.10, 0.0), (xi, -0.17, 0.0), (xi, -0.24, 0.02), (xi, -0.32, 0.02)]
    objs += pin("Pin2", p2, pin_m)
    # hanger pin on the tailpipe, pointing up
    xt = XL + 0.12
    p3 = [(xt, 0.12, -0.03), (xt, 0.12, 0.06), (xt + 0.03, 0.12, 0.10), (xt + 0.13, 0.12, 0.10)]
    objs += pin("Pin3", p3, pin_m)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("marmitta", objs, "marmitta.py",
            "car rear exhaust silencer: oval aluminised steel muffler box with rolled seams, inlet pipe, "
            "tailpipe, hanger pins with a rubber hanger, light heat tint and surface rust",
            az=26, el=30, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
