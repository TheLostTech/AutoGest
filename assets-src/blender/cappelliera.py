"""Rear parcel shelf (cappelliera) of a generic modern small hatchback, as removed from the car:
a pressed fibreboard panel covered on top with anthracite needle-felt, bare dark fibreboard
underneath, shaped outline with side steps for the C-pillar trims, two round speaker cut-outs
with black plastic trim rings near the hinge edge, black plastic pivot blocks with pins at the
two hinge corners, and two black lifting strings with eyelet clips at the tailgate edge,
lying loose on the shelf. Hinge (seat-back) edge is +Y, tailgate edge -Y, Z up."""
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
    nz2.inputs["Scale"].default_value = 40.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.25
    mr.inputs["From Max"].default_value = 0.75
    nt.links.new(_math(nt, "ADD", _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.7),
                       _math(nt, "MULTIPLY", nz2.outputs["Fac"], 0.3)), mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = tuple(c * 0.65 for c in base[:3]) + (1,)
    mix.inputs["B"].default_value = tuple(c * 1.35 for c in base[:3]) + (1,)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.75
    bump.inputs["Distance"].default_value = 0.0012
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
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
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    for f in fs:
        f.material_index = mat
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=a + b)
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


# ================================================================== parcel shelf
T = 0.016          # board + felt thickness


def assign_by_normal(ob, idx_down, thresh=-0.6):
    for p in ob.data.polygons:
        if p.normal.z < thresh:
            p.material_index = idx_down


def outline():
    half = [(0.0, 0.225), (0.492, 0.225), (0.505, 0.200), (0.505, 0.115), (0.468, 0.085),
            (0.462, -0.150), (0.430, -0.222), (0.0, -0.240)]
    rad = [0, 0.02, 0.012, 0.02, 0.02, 0.05, 0.06, 0]
    right = rounded(half, rad, closed=False, seg=10)
    pts = [Vector((p.x, p.y)) for p in right]
    # closed loop: hinge edge -> right side -> tailgate edge -> left side
    full = [Vector((0.0, 0.225))] + pts[1:-1] + [Vector((0.0, -0.240))] + [Vector((-p.x, p.y)) for p in reversed(pts[1:-1])]
    out = []
    for p in full:          # gentle convex tailgate edge
        y = p.y
        if y < -0.215:
            y -= 0.012 * (1 - (p.x / 0.45) ** 2)
        out.append((p.x, y))
    return out


SPK = [(-0.325, 0.075), (0.325, 0.075)]
R_SPK = 0.072


def board(felt, fibre):
    bm = bmesh.new()
    prism_bm(bm, outline(), 0.0, T)
    cuts = []
    for (x, y) in SPK:
        cuts.append(cutter("SpkCut", lambda b, x=x, y=y: C.cyl_bm(b, R_SPK, -0.02, 0.05, seg=96,
                                                                 matrix=Matrix.Translation((x, y, 0)))))
    ob = C.mesh_obj("Shelf", bm, [felt, fibre])
    for c in cuts:
        bo = C.add_boolean(ob, c)
        bo.use_self = True
        bo.use_hole_tolerant = True
    C.add_bevel(ob, 0.005, segments=4, angle=30)
    ob = C.finalize(ob, angle=35, remove=cuts)
    assign_by_normal(ob, 1)
    return ob


def speaker_rings(black):
    out = []
    for (x, y) in SPK:
        r0 = R_SPK
        ring = C.lathe("SpkRing", [(r0 - 0.004, T - 0.010, 0), (r0 - 0.004, T + 0.0035, 0), (r0 + 0.002, T + 0.0055, 0),
                                   (r0 + 0.012, T + 0.0045, 0), (r0 + 0.015, T + 0.0005, 0), (r0 + 0.002, T - 0.0005, 0),
                                   (r0 + 0.002, T - 0.010, 0)], [black], steps=128)
        ring.matrix_world = Matrix.Translation((x, y, 0))
        out.append(C.finalize(ring, angle=40))
        # four screw heads on the ring flange
        for k in range(4):
            a = math.radians(45 + 90 * k)
            sx, sy = x + (r0 + 0.0085) * math.cos(a), y + (r0 + 0.0085) * math.sin(a)
            sc = C.lathe("SpkScrew", [(0.0, T + 0.004, 0), (0.0032, T + 0.004, 0), (0.0030, T + 0.0058, 0), (0.0, T + 0.0064, 0)],
                         [black], steps=24)
            sc.matrix_world = Matrix.Translation((sx, sy, 0))
            out.append(C.finalize(sc, angle=40))
    return out


def pivots(black, pin_m):
    out = []
    for sx in (-1, 1):
        x = sx * 0.470
        bm = bmesh.new()
        C.box_bm(bm, 0.070, 0.056, 0.034, center=(x, 0.188, -0.012))
        pb = C.mesh_obj("PivotBlock", bm, [black])
        pb.modifiers.new("Sub", "SUBSURF").levels = 2
        pb.modifiers["Sub"].render_levels = 2
        C.add_bevel(pb, 0.002, segments=2, angle=40)
        out.append(C.finalize(pb, angle=45))
        # pin pointing outward along X
        M = Matrix.Translation((x + sx * 0.030, 0.188, -0.008)) @ Matrix.Rotation(sx * math.pi / 2, 4, "Y")
        pin = C.lathe("Pin", [(0.0, 0.0, 0), (0.0085, 0.0, 0), (0.0085, 0.040, 0), (0.0110, 0.044, 0), (0.0110, 0.050, 0),
                              (0.0085, 0.054, 0), (0.0, 0.054, 0)], [pin_m], steps=40)
        pin.matrix_world = M
        out.append(C.finalize(pin, angle=40))
    return out


def strings(black, cord):
    out = []
    zt = T + 0.0055
    for sx in (-1, 1):
        ex, ey = sx * 0.385, -0.200
        # eyelet / grommet through the shelf
        g = C.lathe("Grommet", [(0.0035, T - 0.004, 0), (0.0035, zt + 0.001, 0), (0.0085, zt + 0.0005, 0), (0.0095, T + 0.0005, 0),
                                (0.0070, T - 0.004, 0)], [black], steps=40)
        g.matrix_world = Matrix.Translation((ex, ey, 0))
        out.append(C.finalize(g, angle=40))
        # cord lying loosely on the felt, ending in a plastic hook clip
        ctrl = [(ex, ey, zt + 0.002), (ex - sx * 0.02, ey + 0.035, zt), (ex - sx * 0.075, ey + 0.085, zt),
                (ex - sx * 0.155, ey + 0.095, zt), (ex - sx * 0.215, ey + 0.060, zt), (ex - sx * 0.245, ey + 0.010, zt)]
        pts = rounded(ctrl, [0, 0.03, 0.05, 0.05, 0.04, 0], closed=False, seg=8)
        out.append(tube("Cord", pts, 0.0032, cord, res=3))
        end = Vector(ctrl[-1])
        d = (end - Vector(ctrl[-2])).normalized()
        Mh = frame(d, Vector((0, 0, 1)).cross(d), (0, 0, 1), end + d * 0.016 + Vector((0, 0, 0.001)))
        bm = bmesh.new()
        C.box_bm(bm, 0.046, 0.020, 0.010, matrix=Mh)
        hk = cutter("HookHole", lambda b: C.box_bm(b, 0.016, 0.009, 0.03, center=(0.008, 0, 0), matrix=Mh))
        out.append(solid("HookClip", bm, [black], cutters=[hk], sub=2, smooth=50))
    return out


def build():
    felt = carpet("ShelfFelt", hexc="#242528", scale=1100.0)
    fibre = C.principled("Fibreboard", C.srgb("#1E1D1C"), rough=0.9)
    C.add_noise_bump(fibre, scale=400, strength=0.35, distance=0.001, detail=8.0, rough_var=0.04)
    black = grained("ShelfTrim", v=0.024, rough=0.52)
    pin_m = C.principled("PinPlastic", (0.03, 0.03, 0.032), rough=0.35)
    cord = C.principled("Cord", (0.018, 0.018, 0.019), rough=0.7)
    C.add_noise_bump(cord, scale=2500, strength=0.4, distance=0.0004)
    objs = [board(felt, fibre)]
    objs += speaker_rings(black)
    objs += pivots(black, pin_m)
    objs += strings(black, cord)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("cappelliera", objs, "cappelliera.py",
            "rear parcel shelf of a hatchback: anthracite felt-covered board with two round speaker cut-outs, "
            "pivot pins at the hinge corners and two lifting strings with clips",
            az=26, el=30, lens=70, fill=0.90, **res_samples())
