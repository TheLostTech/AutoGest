"""Centre silencer / resonator: short near-round aluminised steel box with rolled end
seams and a lock seam, long front pipe with two kinks ending in a two-bolt flange
(to the catalyst), long rear pipe with a bend ending in an expanded slip joint
(to the rear silencer), two welded hanger pins, heat tint toward the engine and
light surface rust."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
W, H, NS = 0.37, 0.31, 2.3    # box section (Y width, Z height, superellipse exponent)
XL = 0.40                     # half length of the box
RI = 0.048                    # pipe radius


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
    """Planar pipe centre-line: segs = [('L', len) | ('A', radius, deg)]; positive deg bends
    toward n, negative away from it."""
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
            nn = n if ang >= 0 else -n
            bb = d.cross(nn).normalized()
            ang = abs(ang)
            Cc = P + nn * R
            k = max(2, int(R * ang / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, bb)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, bb)
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


def boxes(name, specs, mat, bevel=0.01, seg=2):
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32)


# ----------------------------------------------------------------- materials
def mat_aluminised(name, base=0.50, rough=0.48, rust=0.5, heat=0.0, xhot=-1.4, xcold=0.0):
    """Hot-dip aluminised steel: matte silver-grey, mottled, heat tint toward the engine,
    orange-brown rust freckles concentrated on edges and seams (as marmitta.py)."""
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

    add(-XL - 0.020, 0.50)
    add(-XL - 0.018, 0.78)
    add(-XL - 0.012, 0.92)
    add(-XL - 0.006, 0.96, 0.018)
    add(-XL + 0.010, 0.96, 0.022)
    add(-XL + 0.020, 1.0, 0.004)
    add(-XL + 0.030, 1.0)
    for i in range(1, 8):
        x = -XL + 0.03 + (2 * XL - 0.06) * i / 8
        add(x, 1.0 + 0.010 * math.sin(math.pi * i / 8))
    add(XL - 0.030, 1.0)
    add(XL - 0.020, 1.0, 0.004)
    add(XL - 0.010, 0.96, 0.022)
    add(XL + 0.006, 0.96, 0.018)
    add(XL + 0.012, 0.92)
    add(XL + 0.018, 0.78)
    add(XL + 0.020, 0.50)
    ob = loft("Box", fr, mat)
    C.add_bevel(ob, 0.002, segments=1, angle=50)
    out = [C.finalize(ob, angle=38)]
    # longitudinal lock seam on the lower front
    a = math.radians(225)
    y = W / 2 * math.copysign(abs(math.cos(a)) ** (2 / NS), math.cos(a))
    z = H / 2 * math.copysign(abs(math.sin(a)) ** (2 / NS), math.sin(a))
    M = T((0, y, z)) @ Matrix.Rotation(math.radians(45), 4, "X")
    out.append(boxes("LockSeam", [(2 * XL - 0.07, 0.020, 0.036, (0, 0, 0), M)], mat, bevel=0.007))
    return out


def flange(name, P, t, b, mat):
    """Two-bolt diamond flange, outer face flush with the pipe end."""
    poly = resample(hull2d(circle_pts(0, 0, 0.092, 64) + circle_pts(0.13, 0, 0.040, 32) + circle_pts(-0.13, 0, 0.040, 32)), 128)
    M = frame_matrix(P, b, t)
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (-0.028, 0.0)]
    ob = loft(name, fr, mat)
    ob.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, RI - 0.005, -0.3, 0.2, seg=48)
    for sx in (-1, 1):
        C.cyl_bm(cb, 0.019, -0.3, 0.2, seg=32, matrix=T((sx * 0.13, 0, 0)))
    cut = C.mesh_obj(name + "Cut", cb, [mat])
    cut.matrix_world = M
    C.add_boolean(ob, cut).use_self = True
    C.add_bevel(ob, 0.004, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def ring(name, r_in, r_out, z0, z1, mat, M):
    P = [(r_in, z0, 0), (r_out, z0, 0), (r_out + 0.003, (z0 + z1) / 2, 0), (r_out, z1, 0), (r_in, z1, 0)]
    return lathe_at(name, P, [mat], M, steps=48)


def pin(name, pts, mat, r=0.010):
    out = [tube(name, pts, r, mat, res=3)]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r * 1.6, matrix=T(Vector(pts[-1])))
    out.append(C.mesh_obj(name + "Tip", bm, [mat]))
    return out


def build():
    body_m = mat_aluminised("BoxSteel", base=0.42, rust=0.7, heat=0.30, xhot=-1.6, xcold=0.3)
    pipe_m = mat_aluminised("PipeSteel", base=0.39, rust=0.75, heat=0.85, xhot=-1.9, xcold=0.6)
    pin_m = mat_aluminised("PinSteel", base=0.34, rust=0.7)
    fl_m = C.mat_cast_iron("FlangeSteel", rust=0.6, base=0.16)
    objs = box(body_m)
    # front pipe: out of the left end plate, two kinks, flange toward the catalyst
    pts, b = path_pts((-XL + 0.03, 0.0, 0.0), (-1, 0, 0), (0, 1, 0),
                      [("L", 0.30), ("A", 0.35, 22), ("L", 0.22), ("A", 0.35, -22), ("L", 0.45)])
    objs.append(pipe("FrontPipe", pts, b, RI, pipe_m, wall=0.006))
    P, t = pts[-1]
    objs.append(flange("Flange", P, t, b, fl_m))
    hp = pts[len(pts) // 2][0]
    # rear pipe: out of the right end plate, long straight with a bend, slip joint end
    pts2, b2 = path_pts((XL - 0.03, 0.0, 0.0), (1, 0, 0), (0, -1, 0),
                        [("L", 0.55), ("A", 0.45, 16), ("L", 0.55)])
    objs.append(pipe("RearPipe", pts2, b2, RI, pipe_m, wall=0.006))
    P, t = pts2[-1]
    M = frame_matrix(P, b2, t)
    sl = [(RI - 0.002, -0.10, 0), (RI + 0.004, -0.10, 0), (RI + 0.011, -0.085, 0), (RI + 0.011, 0.0, 0),
          (RI + 0.005, 0.0, 0), (RI + 0.005, -0.08, 0), (RI - 0.002, -0.095, 0)]
    objs.append(lathe_at("SlipJoint", sl, [pipe_m], M, steps=64))
    # clamp-slot cuts suggested by a narrow clamp band at the slip joint
    P2, t2 = pts2[-4]
    objs.append(ring("ClampBand", RI + 0.011, RI + 0.020, -0.022, 0.022, fl_m, frame_matrix(P2, b2, t2)))
    # weld collars where the pipes enter the end plates
    objs.append(ring("Collar1", RI - 0.004, RI + 0.013, -0.014, 0.014, body_m, T((-XL - 0.02, 0.0, 0.0)) @ Matrix.Rotation(math.radians(-90), 4, "Y")))
    objs.append(ring("Collar2", RI - 0.004, RI + 0.013, -0.014, 0.014, body_m, T((XL + 0.02, 0.0, 0.0)) @ Matrix.Rotation(math.radians(90), 4, "Y")))
    # hanger pins: one on the front pipe pointing up, one on the rear pipe pointing up
    x, y = hp.x, hp.y
    objs += pin("Pin1", [(x, y, RI - 0.01), (x, y, RI + 0.08), (x + 0.03, y, RI + 0.12), (x + 0.13, y, RI + 0.12)], pin_m)
    q = pts2[len(pts2) // 3][0]
    objs += pin("Pin2", [(q.x, q.y, RI - 0.01), (q.x, q.y, RI + 0.08), (q.x - 0.03, q.y, RI + 0.12), (q.x - 0.13, q.y, RI + 0.12)], pin_m)
    # lay the whole assembly diagonally in the frame
    C.transform_all(objs, Matrix.Rotation(math.radians(-18), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("silenziatore-centrale", objs, "silenziatore-centrale.py",
            "car exhaust centre silencer (resonator): short round aluminised steel box with rolled seams, long front pipe "
            "with two-bolt flange, long rear pipe with slip joint, hanger pins, light heat tint and surface rust",
            az=24, el=34, lens=70, fill=0.90,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
