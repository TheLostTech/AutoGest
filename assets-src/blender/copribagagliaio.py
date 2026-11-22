"""Retractable luggage-compartment cover (copribagagliaio avvolgibile) of a generic estate /
hatchback: a satin-silver anodised aluminium cassette with black grained plastic end caps and
spring-loaded mounting pins, and the black woven blind pulled part-way out, lying on the floor
and ending in a rigid black pull bar with a central finger grip and the two latching lugs at
its ends. Cassette runs along X, the blind pulls out towards -Y, Z up."""
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


# ================================================================== luggage cover
HW = 0.50                  # half length of the cassette tube
CY, CZ = 0.20, 0.034       # cassette axis
BW = 0.455                 # half width of the blind
BAR_Y = -0.19
SLOT = Vector((0.0, CY - 0.034, CZ + 0.010))


def profile(scale=1.0):
    """Cassette cross-section in (y, z) about the axis: rounded D shape, flat bottom."""
    pts = rounded([(-0.036, -0.030), (0.036, -0.030), (0.040, 0.008), (0.020, 0.032), (-0.022, 0.032), (-0.040, 0.010)],
                  [0.008, 0.012, 0.022, 0.018, 0.018, 0.010], closed=True, seg=8)
    return [(p.x * scale, p.y * scale) for p in pts]


def along_x(poly, x0, x1, oy=CY, oz=CZ):
    """prism matrix: local (x, y) -> world (y, z); local z -> world x."""
    return Matrix.Translation((0, oy, oz)) @ Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def cassette(alu, black, steel):
    out = []
    bm = bmesh.new()
    prism_bm(bm, profile(), -HW + 0.030, HW - 0.030, M=along_x(None, 0, 0))
    slot = cutter("SlotCut", lambda b: C.box_bm(b, 2 * BW + 0.02, 0.020, 0.006, center=(0.0, SLOT.y, SLOT.z)))
    out.append(solid("Tube", bm, [alu], bevel=0.0025, seg=3, cutters=[slot], smooth=40))
    # shallow extruded grooves along the top face
    for dz in (-0.006, 0.006):
        bm = bmesh.new()
        C.box_bm(bm, 2 * HW - 0.07, 0.0016, 0.0016, center=(0.0, CY + 0.004 + dz, CZ + 0.0325))
        out.append(solid("Groove", bm, [black], bevel=0.0004))
    # dark gap inside the slot
    bm = bmesh.new()
    C.box_bm(bm, 2 * BW + 0.01, 0.004, 0.005, center=(0.0, SLOT.y + 0.006, SLOT.z))
    out.append(C.mesh_obj("SlotGap", bm, [C.principled("Void", (0.004, 0.004, 0.004), rough=0.9)]))
    for sx in (-1, 1):
        x0, x1 = (HW - 0.034, HW) if sx > 0 else (-HW, -HW + 0.034)
        bm = bmesh.new()
        prism_bm(bm, profile(1.06), x0, x1, M=along_x(None, 0, 0))
        out.append(solid("EndCap", bm, [black], bevel=0.004, seg=3, smooth=40))
        # spring-loaded mounting pin and its collar
        M = Matrix.Translation((sx * HW, CY, CZ - 0.004)) @ Matrix.Rotation(sx * math.pi / 2, 4, "Y")
        pin = C.lathe("Pin", [(0.0, -0.002, 0), (0.013, -0.002, 0), (0.013, 0.006, 0), (0.0075, 0.007, 0), (0.0075, 0.028, 0),
                              (0.0062, 0.030, 0), (0.0, 0.030, 0)], [steel], steps=40)
        pin.matrix_world = M
        out.append(C.finalize(pin, angle=40))
        # release button on top of each cap
        bm = bmesh.new()
        C.box_bm(bm, 0.018, 0.026, 0.008, center=(sx * (HW - 0.017), CY + 0.002, CZ + 0.036))
        out.append(solid("Release", bm, [black], sub=2, smooth=50))
    return out


def blind_z(y, x):
    """Height of the blind's mid-surface: leaves the slot, drapes down onto the floor."""
    t = (SLOT.y - y) / (SLOT.y - BAR_Y)
    z_floor = 0.0055
    z = z_floor + (SLOT.z - z_floor) * (1 - sstep(0.0, 0.42, t)) ** 1.2
    # faint transverse ripples and edge curl
    z += 0.0004 * math.sin(t * 13.0 + x * 2.0) * sstep(0.1, 0.4, t)
    z += 0.0018 * sstep(0.85, 1.0, abs(x) / BW)
    return z


def blind(fab):
    nx, ny = 90, 48
    bm = bmesh.new()
    V = []
    for j in range(ny + 1):
        y = SLOT.y + (BAR_Y + 0.010 - SLOT.y) * j / ny
        row = []
        for i in range(nx + 1):
            x = -BW + 2 * BW * i / nx
            row.append(bm.verts.new((x, y, blind_z(y, x))))
        V.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    ob = C.mesh_obj("Blind", bm, [fab])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.0016
    so.offset = 0.0
    blind_ob = C.finalize(ob, angle=50)
    out = [blind_ob]
    # stitched hems along both side edges
    for sx in (-1, 1):
        x = sx * (BW - 0.004)
        pts = []
        for j in range(ny + 1):
            y = SLOT.y - 0.004 + (BAR_Y + 0.010 - SLOT.y + 0.004) * j / ny
            pts.append(Vector((x, y, blind_z(y, x) + 0.0008)))
        out.append(tube("Hem", pts, 0.0024, fab, res=3))
    return out


def bar(black, silver):
    out = []
    bw = BW + 0.020
    sec = rounded([(-0.016, -0.0075), (0.016, -0.0075), (0.016, 0.0075), (-0.016, 0.0075)], [0.004, 0.006, 0.006, 0.004],
                  closed=True, seg=6)
    bm = bmesh.new()
    prism_bm(bm, sec, -bw, bw, M=along_x(None, 0, 0, oy=BAR_Y, oz=0.0075))
    out.append(solid("PullBar", bm, [black], bevel=0.0015, seg=2, smooth=40))
    # satin trim strip on top
    bm = bmesh.new()
    C.box_bm(bm, 2 * bw - 0.06, 0.010, 0.0016, center=(0.0, BAR_Y - 0.002, 0.0152))
    out.append(solid("BarStrip", bm, [silver], bevel=0.0006))
    # central finger grip lip
    def gshape(p, u, v, w):
        p.z -= 0.004 * u * u
        return p
    out.append(box_soft("Grip", [black], (-0.065, BAR_Y - 0.034, 0.002), (0.065, BAR_Y - 0.010, 0.012), n=(4, 2, 2),
                        levels=2, shape=gshape, angle=50))
    # latching lugs at both ends
    for sx in (-1, 1):
        bm = bmesh.new()
        x = sx * (bw + 0.016)
        C.box_bm(bm, 0.034, 0.028, 0.016, center=(x, BAR_Y, 0.008))
        C.box_bm(bm, 0.014, 0.012, 0.012, center=(x + sx * 0.022, BAR_Y - 0.004, 0.012))
        out.append(solid("Lug", bm, [black], sub=2, smooth=50))
    return out


def build():
    alu = satin_silver("CassetteAlu")
    black = grained("CoverBlack", v=0.020, rough=0.5)
    silver = satin_silver()
    steel = zinc("PinSteel")
    fab = fabric("BlindFabric", hexc="#222326", period=0.0028)
    objs = cassette(alu, black, steel)
    objs += blind(fab)
    objs += bar(black, silver)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("copribagagliaio", objs, "copribagagliaio.py",
            "retractable luggage cover: satin aluminium cassette with black end caps and mounting pins, black fabric "
            "blind partly pulled out ending in a black pull bar with grip and latching lugs",
            az=24, el=32, lens=70, fill=0.92, **res_samples())
