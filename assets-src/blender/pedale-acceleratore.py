"""Electronic accelerator pedal module (pedale acceleratore drive-by-wire) of a generic modern
small hatchback, as removed from the car: black glass-filled nylon mounting plate with three
bolt bosses and zinc compression sleeves, stiffening gussets, the round pedal-position sensor
housing at the pivot with a ribbed side cover and a moulded 6-way connector shroud, and the
pendant plastic pedal arm (web with edge flanges) ending in an elongated pad with grip ribs.
No text or logos. Driver side is -Y, firewall +Y, Z up."""
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


def box_soft(name, mats, lo, hi, n=(3, 3, 3), levels=3, shape=None, M=None, angle=70, cutters=()):
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


# ================================================================== accelerator pedal
PIV = Vector((0.0, -0.010, 0.285))
PLATE_Y = 0.032
TILT = math.radians(24)


def arm_path():
    ctrl = [(PIV.y, PIV.z), (PIV.y - 0.010, 0.215), (PIV.y - 0.040, 0.140), (PIV.y - 0.068, 0.085)]
    pts = rounded(ctrl, [0, 0.05, 0.05, 0], closed=False, seg=10)
    return [Vector((0.0, p.x, p.y)) for p in pts]


def plate(nylon, zincm):
    out = []
    poly = rounded([(-0.046, 0.335), (0.046, 0.335), (0.046, 0.248), (0.022, 0.176), (-0.022, 0.176), (-0.046, 0.248)],
                   [0.014, 0.014, 0.02, 0.016, 0.016, 0.02], closed=True, seg=8)
    Mxz = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # (x, y)->(x, z), extrusion -> y
    bm = bmesh.new()
    prism_bm(bm, [(p.x, p.y) for p in poly], PLATE_Y - 0.006, PLATE_Y, M=Mxz)
    bosses = [(-0.032, 0.318), (0.032, 0.318), (0.0, 0.192)]

    def holes(b):
        for (x, z) in bosses:
            C.cyl_bm(b, 0.0042, -0.05, 0.05, seg=24, matrix=Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    for (x, z) in bosses:
        C.cyl_bm(bm, 0.0105, PLATE_Y - 0.012, PLATE_Y, seg=32,
                 matrix=Matrix.Translation((x, 0, z)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    hc = cutter("BoltHoles", holes)
    out.append(solid("Plate", bm, [nylon], bevel=0.0015, seg=2, cutters=[hc], smooth=34))
    # zinc compression sleeves in the bosses
    for (x, z) in bosses:
        s = C.lathe("Sleeve", [(0.0042, -0.0005, 0), (0.0068, -0.0005, 0), (0.0068, 0.0130, 0), (0.0042, 0.0130, 0)], [zincm], steps=32)
        s.matrix_world = Matrix.Translation((x, PLATE_Y + 0.0005, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        out.append(C.finalize(s, angle=40))
    # gussets from the plate to the sensor housing
    for x in (-0.024, 0.024):
        bm = bmesh.new()
        tri = [(PLATE_Y - 0.004, 0.330), (PLATE_Y - 0.004, 0.236), (PIV.y + 0.012, 0.262), (PIV.y + 0.012, 0.310)]
        prism_bm(bm, tri, x - 0.0018, x + 0.0018, M=Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
        out.append(solid("Gusset", bm, [nylon], bevel=0.0008, seg=2, smooth=30))
    # block joining housing and plate
    bm = bmesh.new()
    C.box_bm(bm, 0.052, PLATE_Y - PIV.y - 0.006, 0.044, center=(0.0, (PLATE_Y + PIV.y) / 2 - 0.003, PIV.z))
    out.append(solid("Neck", bm, [nylon], bevel=0.003, seg=2))
    return out


def housing(nylon, cover_m):
    out = []
    M = Matrix.Translation((-0.030, PIV.y, PIV.z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    h = C.lathe("SensorHousing", [(0.0, 0.0, 0), (0.030, 0.0, 0), (0.0325, 0.003, 0), (0.0325, 0.050, 0), (0.0, 0.050, 0)],
                [nylon], steps=72)
    h.matrix_world = M
    C.add_bevel(h, 0.0015, segments=2, angle=30)
    out.append(C.finalize(h, angle=40))
    # side cover (sensor) on +X with radial ribs and a centre boss
    M2 = Matrix.Translation((0.020, PIV.y, PIV.z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    cv = C.lathe("SensorCover", [(0.0, 0.0, 0), (0.0315, 0.0, 0), (0.0315, 0.006, 0), (0.029, 0.009, 0), (0.012, 0.010, 0),
                                 (0.011, 0.014, 0), (0.0, 0.0145, 0)], [cover_m], steps=72)
    cv.matrix_world = M2
    out.append(C.finalize(cv, angle=40))
    for k in range(8):
        a = math.tau * k / 8 + 0.2
        bm = bmesh.new()
        Mr = M2 @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.021, 0.0, 0.0105))
        C.box_bm(bm, 0.016, 0.0022, 0.003, matrix=Mr)
        out.append(solid("CoverRib", bm, [cover_m], bevel=0.0007))
    return out


def connector(nylon, pin_m):
    out = []
    # shroud on the top/rear of the housing, mouth facing +X and slightly up
    M = Matrix.Translation((0.026, PIV.y + 0.008, PIV.z + 0.040)) @ Matrix.Rotation(math.radians(-15), 4, "Y")
    w, h, d = 0.030, 0.016, 0.030      # mouth (y, z) and depth (x)
    bm = bmesh.new()
    C.box_bm(bm, d, w + 0.004, h + 0.004, center=(0.0, 0.0, 0.0), matrix=M)
    cut = cutter("Mouth", lambda b: C.box_bm(b, d, w, h, center=(0.008, 0.0, 0.0), matrix=M))
    out.append(solid("Shroud", bm, [nylon], bevel=0.001, seg=2, cutters=[cut]))
    # pedestal joining it to the housing
    bm = bmesh.new()
    C.box_bm(bm, 0.030, 0.030, 0.020, center=(-0.012, 0.0, -0.014), matrix=M)
    out.append(solid("ConnBase", bm, [nylon], bevel=0.002, seg=2))
    # latch ramp
    bm = bmesh.new()
    C.box_bm(bm, 0.012, 0.010, 0.004, center=(0.006, 0.0, h / 2 + 0.003), matrix=M)
    out.append(solid("Latch", bm, [nylon], bevel=0.0008))
    # six pins
    bm = bmesh.new()
    for i in range(3):
        for j in range(2):
            C.box_bm(bm, 0.016, 0.0016, 0.0016, center=(0.0, -0.008 + 0.008 * i, -0.0035 + 0.007 * j), matrix=M)
    out.append(C.mesh_obj("Pins", bm, [pin_m]))
    return out


def arm(nylon):
    P = arm_path()
    n = len(P)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (P[i] - P[i - 1]).length)
    U = Vector((1, 0, 0))
    web, flanges = [], [[], []]
    for i in range(n):
        T = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()
        V = T.cross(U).normalized()
        t = acc[i] / acc[-1]
        hw = 0.015 - 0.004 * t
        web.append((P[i], U, V, [(-0.0028, -hw), (0.0028, -hw), (0.0028, hw), (-0.0028, hw)]))
        for k, s in enumerate((-1, 1)):
            sec = rounded([(-0.0075, s * hw - 0.0018), (0.0075, s * hw - 0.0018), (0.0075, s * hw + 0.0018),
                           (-0.0075, s * hw + 0.0018)], [0.0012] * 4, closed=True, seg=2)
            flanges[k].append((P[i], U, V, [(p.x, p.y) for p in sec]))
    bm = bmesh.new()
    C.sweep(bm, web)
    for f in flanges:
        C.sweep(bm, f)
    # cross ribs inside the web
    for t in (0.25, 0.5, 0.75):
        i = int(t * (n - 1))
        T = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()
        V = T.cross(U).normalized()
        Mf = frame(U, T, V, P[i])
        hw = 0.015 - 0.004 * acc[i] / acc[-1]
        C.box_bm(bm, 0.013, 0.0025, 2 * hw, matrix=Mf)
    ob = solid("Arm", bm, [nylon], bevel=0.0008, seg=2, angle=35, smooth=40)
    return ob, P[-1], (P[-1] - P[-2]).normalized()


def pad(end, tdir, nylon, grip):
    out = []
    nrm = Vector((0, -math.cos(TILT), math.sin(TILT)))
    up = Vector((0, math.sin(TILT), math.cos(TILT)))
    W, H = 0.050, 0.120
    c = end + nrm * 0.013 + up * (H / 2 - 0.040)
    M = frame((1, 0, 0), up, nrm, c)

    def shape(p, u, v, w):
        if w > 0:
            p.z += 0.0015 * (1 - u * u)
        return p
    out.append(box_soft("Pad", [nylon], (-W / 2, -H / 2, -0.010), (W / 2, H / 2, 0.006), n=(4, 6, 2), levels=3,
                        shape=shape, M=M, angle=50))
    for i in range(9):
        y = -H / 2 + 0.012 + (H - 0.024) * i / 8
        bm = bmesh.new()
        C.box_bm(bm, W - 0.012, 0.0032, 0.0022, center=(0, y, 0.0072), matrix=M)
        out.append(solid("GripRib", bm, [grip], bevel=0.0009, seg=2, smooth=50))
    return out


def build():
    nylon = grained("GFNylon", v=0.022, rough=0.48, scale=700.0)
    cover_m = grained("CoverNylon", v=0.030, rough=0.42, scale=900.0)
    zincm = zinc("SleeveZinc")
    pin_m = C.principled("PinBrass", (0.80, 0.62, 0.38), metallic=1.0, rough=0.3)
    objs = plate(nylon, zincm)
    objs += housing(nylon, cover_m)
    objs += connector(nylon, pin_m)
    ob, end, tdir = arm(nylon)
    objs.append(ob)
    objs += pad(end, tdir, nylon, nylon)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("pedale-acceleratore", objs, "pedale-acceleratore.py",
            "electronic drive-by-wire accelerator pedal module: black plastic mounting plate with bolt sleeves, "
            "round pedal position sensor housing with connector, pendant plastic pedal arm and ribbed pad",
            az=38, el=14, lens=70, fill=0.86, **res_samples())
