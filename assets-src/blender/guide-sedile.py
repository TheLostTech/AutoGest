"""Seat slide rails (guide sedile) of a generic modern small hatchback front seat, as removed
from the seat: two zinc-plated steel lower rails (rolled channel with inward lips and a row of
latch windows), each carrying a black e-coated sliding upper rail with its riser web and seat
mounting holes; stamped mounting feet at both ends with flanged hex bolts; a latch plate with
return spring on each rail and the bent tubular release bar joining them at the front with a
black grip sleeve. Rails run along Y (front of the car -Y), Z up."""
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


# ================================================================== seat rails
XR = 0.190                 # rail half spacing
Y0, Y1 = -0.215, 0.215     # lower rail extent
ZB = 0.012                 # underside of the lower rail (feet below)


def along_y(x, z):
    """prism matrix: local (x, y) -> world (x, z); local z -> world y."""
    return Matrix.Translation((x, 0, z)) @ Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def lower_section():
    t = 0.0022
    return [(-0.020, 0.000), (0.020, 0.000), (0.020, 0.026), (0.0105, 0.026), (0.0105, 0.026 - t),
            (0.020 - t, 0.026 - t), (0.020 - t, t), (-0.020 + t, t), (-0.020 + t, 0.026 - t), (-0.0105, 0.026 - t),
            (-0.0105, 0.026), (-0.020, 0.026)]


def lower_rail(x, zincm, side):
    bm = bmesh.new()
    prism_bm(bm, lower_section(), Y0, Y1, M=along_y(x, ZB))
    # latch windows along the inner lip
    def win(b):
        for k in range(14):
            y = -0.120 + k * 0.0115
            C.box_bm(b, 0.008, 0.0055, 0.010, center=(x - side * 0.0152, y, ZB + 0.026))
    cut = cutter("Windows", win)
    return solid("LowerRail", bm, [zincm], bevel=0.0007, seg=2, cutters=[cut], smooth=30)


def upper_rail(x, steel, side):
    out = []
    ya, yb = Y0 + 0.030, Y1 - 0.010
    bm = bmesh.new()
    # slider body inside the channel, web rising through the lips, folded top flange
    C.box_bm(bm, 0.028, yb - ya, 0.014, center=(x, (ya + yb) / 2, ZB + 0.013))
    C.box_bm(bm, 0.0045, yb - ya, 0.036, center=(x, (ya + yb) / 2, ZB + 0.036))
    C.box_bm(bm, 0.016, yb - ya - 0.02, 0.0035, center=(x + side * 0.006, (ya + yb) / 2, ZB + 0.0525))
    # riser brackets at both ends with seat frame holes
    for (yc, h) in ((ya + 0.035, 0.060), (yb - 0.030, 0.050)):
        C.box_bm(bm, 0.004, 0.060, h, center=(x + side * 0.004, yc, ZB + 0.030 + h / 2))
    def holes(b):
        for (yc, h) in ((ya + 0.035, 0.060), (yb - 0.030, 0.050)):
            M = Matrix.Translation((x, yc, ZB + 0.030 + h - 0.016)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
            C.cyl_bm(b, 0.0055, -0.03, 0.03, seg=28, matrix=M)
    cut = cutter("Holes", holes)
    out.append(solid("UpperRail", bm, [steel], bevel=0.0012, seg=2, cutters=[cut], smooth=30))
    return out


def feet(x, zincm, steel):
    out = []
    for (y, d) in ((Y0 - 0.010, -1), (Y1 + 0.010, 1)):
        bm = bmesh.new()
        # stamped foot: flat pad on the floor, ramp up to the rail end
        C.box_bm(bm, 0.050, 0.050, 0.0035, center=(x, y + d * 0.012, 0.00175))
        C.box_bm(bm, 0.040, 0.030, 0.0035, center=(x, y - d * 0.012, ZB - 0.0015),
                 matrix=None)
        C.box_bm(bm, 0.040, 0.0035, ZB + 0.002, center=(x, y - d * 0.004, ZB / 2))
        cut = cutter("FootHole", lambda b, y=y, d=d: C.cyl_bm(b, 0.0065, -0.02, 0.02, seg=28,
                                                             matrix=Matrix.Translation((x, y + d * 0.014, 0))))
        out.append(solid("Foot", bm, [zincm], bevel=0.0012, seg=2, cutters=[cut], smooth=30))
        # flanged hex bolt in the foot
        P = Vector((x, y + d * 0.014, 0.0035))
        w = C.lathe("Washer", [(0.0055, 0.0, 0), (0.0125, 0.0, 0), (0.0125, 0.0018, 0), (0.0055, 0.0018, 0)], [zincm], steps=48)
        w.matrix_world = Matrix.Translation(P)
        out.append(C.finalize(w, angle=40))
        out.append(hex_bolt("Bolt", zincm, Matrix.Translation(P + Vector((0, 0, 0.0018))) @ Matrix.Rotation(0.3, 4, "Z"),
                            af=0.0135, h=0.0075))
        tip = C.lathe("Thread", [(0.0, 0.0, 0), (0.0045, 0.0, 0), (0.0045, 0.004, 0), (0.0, 0.004, 0)], [zincm], steps=24)
        tip.matrix_world = Matrix.Translation(P + Vector((0, 0, 0.0093)))
        out.append(C.finalize(tip, angle=40))
    return out


def latch(x, side, zincm, steel, spring_m):
    """Latch plate pivoting on the outer face of the upper rail, spring to the rail."""
    out = []
    xo = x - side * 0.0045
    bm = bmesh.new()
    poly = rounded([(-0.075, 0.020), (0.010, 0.020), (0.020, 0.032), (0.020, 0.046), (-0.020, 0.046), (-0.075, 0.034)],
                   [0.004, 0.006, 0.004, 0.004, 0.006, 0.004], closed=True, seg=4)
    prism_bm(bm, poly, 0.0, 0.0025,
             M=Matrix.Translation((xo, 0.0, ZB)) @ Matrix(((0, 0, -side, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    out.append(solid("LatchPlate", bm, [zincm], bevel=0.0007, seg=2, smooth=30))
    # pivot rivet
    rv = C.lathe("Rivet", [(0.0, 0.0, 0), (0.0055, 0.0, 0), (0.0050, 0.0018, 0), (0.0, 0.0026, 0)], [zincm], steps=32)
    rv.matrix_world = Matrix.Translation((xo - side * 0.0025, -0.010, ZB + 0.038)) @ Matrix.Rotation(-side * math.pi / 2, 4, "Y")
    out.append(C.finalize(rv, angle=40))
    # return spring: coil lying along Y next to the latch
    Ms = Matrix.Translation((xo - side * 0.007, 0.030, ZB + 0.032)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    out.append(helix("Spring", 0.0042, 0.0008, 0.0, 0.040, 11, spring_m, M=Ms))
    return out


def release_bar(steel, black):
    out = []
    yb = Y0 + 0.010
    pts = rounded([(-XR - 0.012, yb + 0.040, ZB + 0.036), (-XR - 0.012, yb - 0.050, ZB + 0.036),
                   (-XR + 0.050, yb - 0.090, ZB + 0.030), (XR - 0.050, yb - 0.090, ZB + 0.030),
                   (XR + 0.012, yb - 0.050, ZB + 0.036), (XR + 0.012, yb + 0.040, ZB + 0.036)],
                  [0, 0.045, 0.045, 0.045, 0.045, 0], closed=False, seg=12)
    out.append(tube("ReleaseBar", pts, 0.0072, steel, res=4))
    # black grip sleeve
    gp = [Vector((-0.10, yb - 0.090, ZB + 0.030)), Vector((0.10, yb - 0.090, ZB + 0.030))]
    out.append(tube("Grip", gp, 0.0105, black, res=5))
    for x in (-0.10, 0.10):
        c = C.lathe("GripEnd", [(0.0, -0.002, 0), (0.0108, -0.002, 0), (0.0122, 0.0, 0), (0.0108, 0.002, 0), (0.0, 0.002, 0)],
                    [black], steps=32)
        c.matrix_world = Matrix.Translation((x, yb - 0.090, ZB + 0.030)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        out.append(C.finalize(c, angle=40))
    return out


def build():
    zincm = zinc()
    steel = steel_dark()
    black = grained("GripBlack", v=0.02, rough=0.55)
    spring_m = C.principled("SpringSteel", (0.07, 0.07, 0.075), metallic=1.0, rough=0.35)
    objs = []
    for side, x in ((-1, -XR), (1, XR)):
        objs.append(lower_rail(x, zincm, side))
        objs += upper_rail(x, steel, side)
        objs += feet(x, zincm, steel)
        objs += latch(x, side, zincm, steel, spring_m)
    objs += release_bar(steel, black)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("guide-sedile", objs, "guide-sedile.py",
            "pair of car seat slide rails: zinc-plated lower channels with latch windows, black sliding upper rails "
            "with mounting holes, mounting feet with bolts, latch springs and front release bar with grip",
            az=-34, el=30, lens=70, fill=0.90, **res_samples())
