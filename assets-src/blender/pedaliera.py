"""Pedal box (pedaliera) of a generic manual small hatchback, as removed from the car: a
zinc-plated stamped steel bracket (firewall flange with four studs, top plate, three side
cheeks with lightening holes), the pivot shaft with bushings, the clutch and brake pedals as
black e-coated stamped arms with ribbed rubber pads (brake pad wider), the pushrod clevises
running forward through the flange, the clutch return spring and the brake light switch.
Driver side is -Y, firewall +Y, Z up."""
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


# ================================================================== pedal box
PIV = Vector((0.0, 0.065, 0.300))     # (x unused, y, z) pivot axis along X
XC, XB = -0.092, 0.030               # clutch / brake arm planes
FLANGE_Y = 0.170
TILT = math.radians(22)              # pad face leans back


def arm_path():
    ctrl = [(PIV.y, PIV.z + 0.025), (PIV.y, PIV.z), (PIV.y - 0.012, 0.205), (PIV.y - 0.050, 0.110),
            (PIV.y - 0.100, 0.045), (PIV.y - 0.118, 0.020)]
    pts = rounded(ctrl, [0, 0.02, 0.06, 0.06, 0.03, 0], closed=False, seg=10)
    return [Vector((0.0, p.x, p.y)) for p in pts]


def arm(name, x, mat, w0=0.016, w1=0.010):
    P = [p + Vector((x, 0, 0)) for p in arm_path()]
    n = len(P)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (P[i] - P[i - 1]).length)
    frames = []
    U = Vector((1, 0, 0))
    for i in range(n):
        T = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()
        V = T.cross(U).normalized()
        t = acc[i] / acc[-1]
        hw = w0 + (w1 - w0) * t
        sec = rounded([(-0.004, -hw), (0.004, -hw), (0.004, hw), (-0.004, hw)], [0.0015] * 4, closed=True, seg=3)
        frames.append((P[i], U, V, [(p.x, p.y) for p in sec]))
    bm = bmesh.new()
    C.sweep(bm, frames)
    # pressed stiffening flange on the rear edge of the arm (L section)
    frames2 = []
    for i in range(2, n - 2):
        T = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()
        V = T.cross(U).normalized()
        t = acc[i] / acc[-1]
        hw = w0 + (w1 - w0) * t
        sec = [(-0.011, -hw), (0.011, -hw), (0.011, -hw + 0.003), (-0.011, -hw + 0.003)]
        frames2.append((P[i], U, V, sec))
    C.sweep(bm, frames2)
    ob = solid(name, bm, [mat], bevel=0.0012, seg=2, angle=35, smooth=40)
    return ob, P[-1], (P[-1] - P[-2]).normalized()


def pad(name, end, x, width, height, rubber, steel):
    out = []
    nrm = Vector((0, -math.cos(TILT), math.sin(TILT)))
    up = Vector((0, math.sin(TILT), math.cos(TILT)))
    c = Vector((x, end.y, end.z)) + nrm * 0.004 - up * 0.008
    M = frame((1, 0, 0), up, nrm, c)      # local x across, y up the pad, z out of the face
    # steel pad plate
    bm = bmesh.new()
    C.box_bm(bm, width - 0.006, height - 0.006, 0.003, center=(0, 0, 0.0), matrix=M)
    out.append(solid(name + "Plate", bm, [steel], bevel=0.0012, seg=2))
    # moulded rubber pad wrapping the plate
    def shape(p, u, v, w):
        if w > 0:
            p.z += 0.0015 * (1 - u * u) * (1 - v * v)
        return p
    out.append(box_soft(name + "Rubber", [rubber], (-width / 2, -height / 2, 0.0012), (width / 2, height / 2, 0.0115),
                        n=(4, 4, 2), levels=3, shape=shape, M=M, angle=50))
    # grip ribs across the face
    k = 6
    for i in range(k):
        y = -height / 2 + 0.008 + (height - 0.016) * i / (k - 1)
        bm = bmesh.new()
        C.box_bm(bm, width - 0.014, 0.0035, 0.0028, center=(0, y, 0.0122), matrix=M)
        out.append(solid(name + "Rib", bm, [rubber], bevel=0.0011, seg=2, smooth=50))
    return out


def bracket(zincm, black_steel):
    out = []
    # side cheeks in the YZ plane
    cheek = rounded([(FLANGE_Y, 0.425), (FLANGE_Y, 0.232), (0.120, 0.250), (0.060, 0.268), (0.032, 0.300),
                     (0.040, 0.338), (0.070, 0.425)], [0, 0.012, 0.03, 0.02, 0.025, 0.02, 0.01], closed=True, seg=8)
    poly = [(p.x, p.y) for p in cheek]
    Myz = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    for x in (-0.132, -0.040, 0.070):
        bm = bmesh.new()
        prism_bm(bm, poly, x - 0.0015, x + 0.0015, M=Myz)
        hole = cutter("Lighten", lambda b, x=x: prism_bm(b, rrect2(0.125, 0.355, 0.050, 0.050, 0.020, seg=6),
                                                         x - 0.02, x + 0.02, M=Myz))
        out.append(solid("Cheek", bm, [zincm], bevel=0.0007, seg=2, cutters=[hole], smooth=30))
    # top plate with turned-down front lip
    bm = bmesh.new()
    C.box_bm(bm, 0.210, FLANGE_Y - 0.068, 0.003, center=(-0.031, (FLANGE_Y + 0.068) / 2, 0.4265))
    C.box_bm(bm, 0.210, 0.003, 0.022, center=(-0.031, 0.0695, 0.4165))
    out.append(solid("TopPlate", bm, [zincm], bevel=0.0008, seg=2))
    # firewall flange with stud holes
    bm = bmesh.new()
    prism_bm(bm, rrect2(-0.031, 0.335, 0.270, 0.230, 0.016, seg=6), FLANGE_Y, FLANGE_Y + 0.003,
             M=Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    def hole(b):
        for (x, z) in ((-0.150, 0.428), (0.088, 0.428), (-0.150, 0.242), (0.088, 0.242)):
            C.cyl_bm(b, 0.0045, -0.02, 0.02, seg=24, matrix=Matrix.Translation((x, FLANGE_Y, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    # (Matrix above: plane mapping local (x, y) -> (x, z), extrusion -> y)
    hc = cutter("StudHoles", hole)
    out.append(solid("Flange", bm, [zincm], bevel=0.0008, seg=2, cutters=[hc], smooth=30))
    # studs pointing to the firewall (+Y) with flange nuts on the driver side
    for (x, z) in ((-0.150, 0.428), (0.088, 0.428), (-0.150, 0.242), (0.088, 0.242)):
        M = Matrix.Translation((x, FLANGE_Y, z)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
        st = C.lathe("Stud", [(0.0, -0.008, 0), (0.0040, -0.008, 0), (0.0040, 0.032, 0), (0.0032, 0.034, 0), (0.0, 0.034, 0)],
                     [zincm], steps=20)
        st.matrix_world = M
        out.append(C.finalize(st, angle=40))
        out.append(hex_bolt("Nut", zincm, Matrix.Translation((x, FLANGE_Y, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"),
                            af=0.012, h=0.0065))
    # pivot shaft and its nut
    M = Matrix.Translation((-0.150, PIV.y, PIV.z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    sh = C.lathe("Shaft", [(0.0, 0.0, 0), (0.0062, 0.0, 0), (0.0062, 0.236, 0), (0.0, 0.236, 0)], [zincm], steps=32)
    sh.matrix_world = M
    out.append(C.finalize(sh, angle=40))
    out.append(hex_bolt("ShaftNut", zincm, Matrix.Translation((0.0715, PIV.y, PIV.z)) @ Matrix.Rotation(math.pi / 2, 4, "Y"),
                        af=0.017, h=0.008))
    out.append(hex_bolt("ShaftHead", zincm, Matrix.Translation((-0.1335, PIV.y, PIV.z)) @ Matrix.Rotation(-math.pi / 2, 4, "Y"),
                        af=0.017, h=0.008))
    return out


def bushings(nylon):
    out = []
    for x in (XC, XB):
        M = Matrix.Translation((x - 0.016, PIV.y, PIV.z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        b = C.lathe("Bush", [(0.0062, 0.0, 0), (0.0125, 0.0, 0), (0.0125, 0.032, 0), (0.0062, 0.032, 0)], [nylon], steps=40)
        b.matrix_world = M
        out.append(C.finalize(b, angle=40))
    return out


def pushrod(x, z, steel, zincm):
    """Clevis on the arm and rod running forward through the flange."""
    out = []
    # arm y at height z
    P = arm_path()
    y_arm = min(P, key=lambda p: abs(p.z - z)).y
    bm = bmesh.new()
    C.box_bm(bm, 0.020, 0.018, 0.016, center=(x, y_arm + 0.012, z))
    cut = cutter("ClevisSlot", lambda b: C.box_bm(b, 0.0085, 0.03, 0.03, center=(x, y_arm + 0.004, z)))
    out.append(solid("Clevis", bm, [zincm], bevel=0.0015, seg=2, cutters=[cut]))
    pin = C.lathe("ClevisPin", [(0.0, -0.002, 0), (0.0048, -0.002, 0), (0.0048, 0.024, 0), (0.0, 0.024, 0)], [zincm], steps=24)
    pin.matrix_world = Matrix.Translation((x - 0.011, y_arm + 0.006, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    out.append(C.finalize(pin, angle=40))
    out.append(tube("Rod", [Vector((x, y_arm + 0.020, z)), Vector((x, FLANGE_Y + 0.05, z + 0.004))], 0.0042, steel, res=3))
    return out


def spring(steel_spring):
    out = []
    A = Vector((XC + 0.016, 0.105, 0.424))
    B = Vector((XC + 0.010, PIV.y - 0.006, 0.232))
    Z = (B - A).normalized()
    X = Z.cross(Vector((1, 0, 0))).normalized()
    M = frame(X, Z.cross(X), Z, A)
    L = (B - A).length
    out.append(helix("Spring", 0.0072, 0.0012, 0.012, L - 0.012, 22, steel_spring, M=M))
    for (p, q) in ((A, A + Z * 0.013), (B - Z * 0.013, B)):
        out.append(tube("SpringHook", [p, q], 0.0013, steel_spring, res=2))
    return out


def light_switch(black):
    out = []
    # tab on the brake-side cheek, switch body pointing at the brake arm
    x = XB + 0.004
    bm = bmesh.new()
    C.box_bm(bm, 0.030, 0.003, 0.026, center=(x, 0.112, 0.262))
    out.append(solid("SwitchTab", bm, [black], bevel=0.0008))
    M = Matrix.Translation((x, 0.111, 0.262)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    body = C.lathe("Switch", [(0.0, -0.016, 0), (0.0095, -0.016, 0), (0.0095, 0.012, 0), (0.0060, 0.014, 0), (0.0060, 0.024, 0),
                              (0.0030, 0.026, 0), (0.0, 0.026, 0)], [black], steps=32)
    body.matrix_world = M
    out.append(C.finalize(body, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.016, 0.014, 0.012, center=(x, 0.134, 0.262))
    out.append(solid("SwitchPlug", bm, [black], bevel=0.0012))
    return out


def build():
    zincm = zinc("BracketZinc")
    C._set(bsdf(zincm), "Base Color", (0.40, 0.41, 0.43, 1))
    ecoat = C.principled("PedalEcoat", (0.030, 0.030, 0.032), metallic=0.3, rough=0.42)
    C.add_noise_bump(ecoat, scale=420, strength=0.08, distance=0.0006, rough_var=0.05)
    steel = steel_dark()
    rubber = C.mat_rubber("PadRubber")
    nylon = C.principled("Nylon", C.srgb("#D8D2C2"), rough=0.5)
    sp = C.principled("SpringSteel", (0.06, 0.06, 0.065), metallic=1.0, rough=0.32)
    blk = grained("SwitchBlack", v=0.02, rough=0.5)
    objs = bracket(zincm, steel)
    objs += bushings(nylon)
    for nm, x, wd, ht in (("Clutch", XC, 0.060, 0.052), ("Brake", XB, 0.078, 0.056)):
        ob, end, tdir = arm(nm + "Arm", x, ecoat)
        objs.append(ob)
        objs += pad(nm, end, x, wd, ht, rubber, steel)
    objs += pushrod(XC, 0.255, steel, zincm)
    objs += pushrod(XB, 0.250, steel, zincm)
    objs += spring(sp)
    objs += light_switch(blk)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("pedaliera", objs, "pedaliera.py",
            "pedal box of a manual car: zinc-plated steel bracket with firewall flange and studs, clutch and brake pedals "
            "with black arms and ribbed rubber pads, pivot shaft, pushrods, return spring and brake light switch",
            az=-38, el=14, lens=70, fill=0.86, **res_samples())
