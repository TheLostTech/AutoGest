"""Left boot (luggage compartment) side trim panel of a generic modern small hatchback, seen
from the boot side: a moulded shell that wraps over the rear wheel-arch hump, covered with
anthracite needle-felt carpet on the lower part and dark grained plastic on the upper part
(moulded step between the two), a horizontal ledge along the top edge on which the parcel
shelf rests, a rectangular cut-out for the boot light, a plastic bag hook and two fixing
clip heads. Boot side is -Y, car front (rear-seat side) is +X, Z up."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = os.environ.get("FAST") == "1"


# ================================================================== interior materials
# (same palette as sedile.py / pannello-porta.py / plancia.py)
def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def fabric(name="SeatFabric", hexc="#2C2E31", period=0.0034):
    """Anthracite woven upholstery: plain-weave relief, heathered yarn colour, sheen."""
    base = C.srgb(hexc)
    m = C.principled(name, base, rough=0.88)
    b = bsdf(m)
    C._set(b, "Sheen Weight", 0.55)
    C._set(b, "Sheen Roughness", 0.38)
    C._set(b, "Sheen Tint", (0.75, 0.76, 0.80, 1))
    nt = m.node_tree
    co = C._coord(nt)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    k = math.tau / period
    s = [_math(nt, "SINE", _math(nt, "MULTIPLY", sep.outputs[i], k)) for i in range(3)]
    w = _math(nt, "ADD", _math(nt, "MULTIPLY", s[0], s[1]),
              _math(nt, "ADD", _math(nt, "MULTIPLY", s[1], s[2]), _math(nt, "MULTIPLY", s[2], s[0])))
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 300.0
    nz.inputs["Detail"].default_value = 3.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = tuple(c * 0.72 for c in base[:3]) + (1,)
    mix.inputs["B"].default_value = tuple(c * 1.30 for c in base[:3]) + (1,)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    h = _math(nt, "ADD", _math(nt, "MULTIPLY", w, 0.6), _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.8))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def carpet(name="NeedleFelt", hexc="#2A2B2E", scale=1400.0):
    """Needle-punched boot carpet / parcel-shelf felt: dense random fibre relief, matte, sheen."""
    base = C.srgb(hexc)
    m = C.principled(name, base, rough=0.95)
    b = bsdf(m)
    C._set(b, "Sheen Weight", 0.7)
    C._set(b, "Sheen Roughness", 0.45)
    C._set(b, "Sheen Tint", (0.8, 0.8, 0.82, 1))
    nt = m.node_tree
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 10.0
    nz.inputs["Roughness"].default_value = 0.7
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz2.inputs["Vector"])
    nz2.inputs["Scale"].default_value = 260.0
    nz2.inputs["Detail"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.25
    mr.inputs["From Max"].default_value = 0.75
    nt.links.new(_math(nt, "ADD", _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.45),
                       _math(nt, "MULTIPLY", nz2.outputs["Fac"], 0.55)), mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = tuple(c * 0.65 for c in base[:3]) + (1,)
    mix.inputs["B"].default_value = tuple(c * 1.35 for c in base[:3]) + (1,)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(_math(nt, "ADD", nz.outputs["Fac"], _math(nt, "MULTIPLY", nz2.outputs["Fac"], 0.6)), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def grained(name="GrainedPP", v=0.028, rough=0.58, scale=520.0):
    """Moulded interior plastic with a leather-like grain."""
    m = C.principled(name, (v, v, v * 1.06), rough=rough)
    nt = m.node_tree
    b = bsdf(m)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = scale
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 60.0
    h = _math(nt, "ADD", vo.outputs["Distance"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.3))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.07
    mr.inputs["To Max"].default_value = rough + 0.07
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def satin_silver(name="SatinSilver"):
    m = C.principled(name, (0.55, 0.555, 0.565), metallic=1.0, rough=0.3)
    C.add_noise_bump(m, scale=800, strength=0.04, distance=0.0003, rough_var=0.04)
    return m


def steel_dark(name="SeatSteel"):
    m = C.principled(name, (0.10, 0.10, 0.105), metallic=0.8, rough=0.48)
    C.add_noise_bump(m, scale=300, strength=0.12, distance=0.0008, rough_var=0.08)
    return m


def zinc(name="ZincRail"):
    m = C.principled(name, (0.50, 0.51, 0.53), metallic=1.0, rough=0.34)
    C.add_noise_bump(m, scale=250, strength=0.08, distance=0.0006, rough_var=0.08)
    return m


# ================================================================== geometry helpers
def sstep(a, b, x):
    return C.smoothstep(a, b, x)


def cage(n):
    """Closed quad lattice on the surface of the cube [-1, 1]^3 with n=(nx, ny, nz) cells."""
    nx, ny, nz = n
    bm = bmesh.new()
    V = {}

    def vt(i, j, k):
        key = (i, j, k)
        if key not in V:
            V[key] = bm.verts.new((2 * i / nx - 1, 2 * j / ny - 1, 2 * k / nz - 1))
        return V[key]

    for i in (0, nx):
        for j in range(ny):
            for k in range(nz):
                bm.faces.new((vt(i, j, k), vt(i, j + 1, k), vt(i, j + 1, k + 1), vt(i, j, k + 1)))
    for j in (0, ny):
        for i in range(nx):
            for k in range(nz):
                bm.faces.new((vt(i, j, k), vt(i + 1, j, k), vt(i + 1, j, k + 1), vt(i, j, k + 1)))
    for k in (0, nz):
        for i in range(nx):
            for j in range(ny):
                bm.faces.new((vt(i, j, k), vt(i + 1, j, k), vt(i + 1, j + 1, k), vt(i, j + 1, k)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def box_soft(name, mats, lo, hi, n=(3, 3, 3), levels=3, shape=None, M=None, angle=70, cutters=(), mat_fn=None):
    """Subdivision-surface solid from a lattice cage spanning lo..hi, deformed by shape(p, u, v, w)."""
    lo, hi = Vector(lo), Vector(hi)
    bm = cage(n)
    for v in bm.verts:
        u, vv, w = v.co.x, v.co.y, v.co.z
        p = Vector(((lo.x + hi.x) / 2 + (hi.x - lo.x) / 2 * u,
                    (lo.y + hi.y) / 2 + (hi.y - lo.y) / 2 * vv,
                    (lo.z + hi.z) / 2 + (hi.z - lo.z) / 2 * w))
        if shape:
            p = shape(p, u, vv, w)
        v.co = (M @ p) if M is not None else p
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if mat_fn:
        for f in bm.faces:
            f.material_index = mat_fn(f.calc_center_median())
    ob = C.mesh_obj(name, bm, mats)
    m = ob.modifiers.new("Sub", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    for c in cutters:
        bo = C.add_boolean(ob, c)
        bo.use_self = True
        bo.use_hole_tolerant = True
    return C.finalize(ob, angle=angle, remove=list(cutters))


def rounded(corners, radii, closed=True, seg=10):
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


def rrect2(cx, cy, w, h, r, seg=6):
    return rounded([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2),
                    (cx - w / 2, cy + h / 2)], [r] * 4, closed=True, seg=seg)


def tube(name, pts, r, mat, res=4, smooth=50):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=smooth)


def prism_bm(bm, poly, z0, z1, M=None, mat=0):
    """2D outline (x, y) extruded along local z from z0 to z1, transformed by M."""
    P = [(p[0], p[1]) for p in poly]
    a = [bm.verts.new((x, y, z0)) for x, y in P]
    b = [bm.verts.new((x, y, z1)) for x, y in P]
    n = len(P)
    fs = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for k in range(n)]
    fs += [bm.faces.new(a[::-1]), bm.faces.new(b)]
    for f in fs:
        f.material_index = mat
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=a + b)
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    return fs


def solid(name, bm, mats, bevel=0.0, seg=2, angle=30, cutters=(), smooth=38, sub=0):
    ob = C.mesh_obj(name, bm, mats)
    if sub:
        m = ob.modifiers.new("Sub", "SUBSURF")
        m.levels = sub
        m.render_levels = sub
    for c in cutters:
        bo = C.add_boolean(ob, c)
        bo.use_self = True
        bo.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=angle)
    return C.finalize(ob, angle=smooth, remove=list(cutters))


def cutter(name, fill):
    bm = bmesh.new()
    fill(bm)
    return C.mesh_obj(name, bm, [])


def frame(X, Y, Z, origin):
    M = Matrix.Identity(4)
    for i, ax in enumerate((Vector(X).normalized(), Vector(Y).normalized(), Vector(Z).normalized())):
        M[0][i], M[1][i], M[2][i] = ax.x, ax.y, ax.z
    M.translation = Vector(origin)
    return M


def helix(name, r_coil, r_wire, z0, z1, turns, mat, M=None, n_per=24):
    pts = []
    N = int(turns * n_per)
    for i in range(N + 1):
        t = i / N
        a = math.tau * turns * t
        p = Vector((r_coil * math.cos(a), r_coil * math.sin(a), z0 + (z1 - z0) * t))
        pts.append((M @ p) if M is not None else p)
    return tube(name, pts, r_wire, mat, res=3, smooth=60)


def hex_bolt(name, mat, M, af=0.013, h=0.008, washer=0.0):
    """Hex flange bolt head standing on local +Z at origin."""
    prof = []
    if washer:
        prof += [(0.0, 0.0, 0), (washer, 0.0, 0), (washer, 0.0016, 0), (af * 0.58, 0.0016, 0)]
    else:
        prof += [(0.0, 0.0, 0), (af * 0.58, 0.0, 0)]
    prof += [(af * 0.58, h, 0), (af * 0.50, h + 0.0012, 0), (0.0, h + 0.0012, 0)]
    ob = C.lathe(name, prof, [mat], steps=6 if not washer else 6)
    ob.matrix_world = M
    return C.finalize(ob, angle=20)


def res_samples():
    return dict(res=(512, 512) if FAST else (1024, 1024),
                samples=int(os.environ.get("SAMPLES", "32" if FAST else "128")))


# ================================================================== boot side trim
X0, X1 = -0.36, 0.36          # tailgate side .. seat side
SPLIT = 0.30                  # carpet below, plastic above


def z_top(x):
    return 0.505 - 0.075 * sstep(-0.10, 0.36, x)


def x_front(z):
    return X1 - 0.11 * (z / 0.5)


def inward(x, z):
    """Offset towards the boot (-Y): wheel-arch hump plus the upper tumblehome."""
    arch = 0.0
    ax, ar, ah = 0.035, 0.30, 0.255
    d = ((x - ax) / ar) ** 2 + (z / ah) ** 2
    if d < 1.0:
        arch = 0.150 * sstep(1.0, 0.55, d) ** 0.8
    lean = 0.045 * (z / 0.5) ** 1.6
    step = 0.006 * sstep(SPLIT - 0.004, SPLIT + 0.004, z)
    return arch + lean + step


def shell_shape(p, u, v, w):
    t = (u + 1) / 2
    s = (w + 1) / 2
    sb = 7 / 12          # cage row that lies exactly on the carpet / plastic split

    def zmap(x):
        zt = z_top(x)
        return s / sb * SPLIT if s <= sb else SPLIT + (s - sb) / (1 - sb) * (zt - SPLIT)
    xa = X0 + (X1 - X0) * t
    z = zmap(xa)
    x = X0 + (x_front(z) - X0) * t
    z = zmap(x)
    y = p.y - inward(x, z)
    return Vector((x, y, z))


LAMP = (-0.215, 0.405)


def shell(felt, plastic):
    def lamp_cut(b):
        y = -inward(LAMP[0], LAMP[1])
        bm2 = b
        C.box_bm(bm2, 0.105, 0.20, 0.042, center=(LAMP[0], y, LAMP[1]))
    cut = cutter("LampCut", lamp_cut)
    ob = box_soft("Shell", [felt, plastic], (X0, -0.006, 0.0), (X1, 0.006, 0.5), n=(14, 1, 12), levels=3,
                  shape=shell_shape, angle=60, cutters=[cut], mat_fn=lambda c: 1 if c.z > SPLIT else 0)
    return ob


def ledge(plastic):
    """Shelf-support ledge running along the top edge, sloping with it."""
    def shape(p, u, v, w):
        x = p.x
        zt = z_top(x)
        p.z = zt + (p.z - 0.5)
        p.y = p.y - inward(x, zt)
        if v < 0:
            p.y -= 0.010 * (1 - u * u)
        return p
    return box_soft("Ledge", [plastic], (X0 + 0.01, -0.058, 0.492), (x_front(0.46) - 0.015, 0.002, 0.512), n=(12, 3, 2),
                    levels=2, shape=shape, angle=50)


def lamp_frame(black):
    """Moulded lip around the light opening plus the lamp's spring-clip seats."""
    x, z = LAMP
    y = -0.006 - inward(x, z)
    out = []
    outer = rrect2(0.0, 0.0, 0.121, 0.058, 0.010)
    inner = rrect2(0.0, 0.0, 0.103, 0.040, 0.004)
    bm = bmesh.new()
    o0 = [bm.verts.new((p.x, 0.0, p.y)) for p in outer]
    o1 = [bm.verts.new((p.x, -0.004, p.y)) for p in outer]
    i0 = [bm.verts.new((p.x, 0.0, p.y)) for p in inner]
    i1 = [bm.verts.new((p.x, -0.004, p.y)) for p in inner]
    n = len(outer)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))
        bm.faces.new((o1[k2], o1[k], i1[k], i1[k2]))
        bm.faces.new((o0[k], o0[k2], i0[k2], i0[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y + 0.001, z)), verts=bm.verts)
    out.append(solid("LampLip", bm, [black], bevel=0.0012, seg=2))
    # dark cavity behind the opening (body side)
    bm = bmesh.new()
    C.box_bm(bm, 0.13, 0.004, 0.07, center=(x, y + 0.035, z))
    out.append(C.mesh_obj("Cavity", bm, [black]))
    return out


def hook(plastic):
    x, z = 0.120, 0.415
    y = -0.006 - inward(x, z) + 0.001
    pts = rounded([(x, y, z + 0.020), (x, y - 0.030, z + 0.004), (x, y - 0.034, z - 0.022), (x, y - 0.020, z - 0.030)],
                  [0, 0.012, 0.01, 0], closed=False, seg=8)
    out = [tube("Hook", pts, 0.0055, plastic, res=4)]
    bm = bmesh.new()
    C.box_bm(bm, 0.030, 0.008, 0.046, center=(x, y + 0.002, z + 0.010))
    out.append(solid("HookBase", bm, [plastic], sub=2, smooth=50))
    return out


def clips(black):
    out = []
    for (x, z) in ((-0.30, 0.19), (0.24, 0.36)):
        y = -0.006 - inward(x, z)
        c = C.lathe("Clip", [(0.0, 0.0, 0), (0.011, 0.0, 0), (0.0105, 0.0025, 0), (0.008, 0.0038, 0), (0.0, 0.0042, 0)],
                    [black], steps=40)
        c.matrix_world = Matrix.Translation((x, y + 0.0005, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
        out.append(C.finalize(c, angle=40))
    return out


def build():
    felt = carpet("BootCarpet", hexc="#2A2B2E", scale=900.0)
    plastic = grained("BootTrim", v=0.030, rough=0.56)
    black = grained("BootBlack", v=0.018, rough=0.5)
    objs = [shell(felt, plastic), ledge(plastic)]
    objs += lamp_frame(black)
    objs += hook(plastic)
    objs += clips(black)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("rivestimento-bagagliaio", objs, "rivestimento-bagagliaio.py",
            "boot side trim panel of a hatchback: moulded shell over the wheel arch, anthracite carpet lower part, "
            "dark grained plastic upper part with shelf ledge, boot light cut-out and bag hook",
            az=40, el=20, lens=70, fill=0.88, **res_samples())
