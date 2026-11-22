"""LPG toroidal tank (spare-wheel well type): pale grey painted steel toroid pressed from
two shells with a raised weld seam at the outer and inner equators, a blank data
label on top, and the multivalve on its inclined flange on the inner wall: cast
aluminium body bolted to the tank, level gauge with a white dial and needle under a
clear cover, black shut-off solenoid with leads, brass filling and outlet unions.

1 unit = 100 mm (650 x 220 mm tank)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
RS = 1.10           # section radius
RC = 2.15           # ring centre radius
ZC = RS             # section centre height
PHI = math.radians(32)      # multivalve flange position on the inner wall (above equator)
AZ = math.radians(118)      # azimuth of the multivalve around the tank axis (far side)


# ----------------------------------------------------------------- helpers
def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), M=I4):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    ob.matrix_world = M
    for c in cutters:
        c.matrix_world = M
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=3, caps=True):
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


# ----------------------------------------------------------------- materials
def mat_tank_paint(name="TankPaint"):
    """Pale grey stove enamel, satin, slight orange peel, a few dull scuffs."""
    v = C.srgb("#A7ACAE")
    m = C.mat_paint(name, v, rough=0.32, coat=0.35)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 120.0
    nz.inputs["Detail"].default_value = 3.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.05
    bp.inputs["Distance"].default_value = 0.004
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    sc = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), sc.inputs["Vector"])
    sc.inputs["Scale"].default_value = 1.6
    sc.inputs["Detail"].default_value = 9.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.56
    mr.inputs["From Max"].default_value = 0.72
    nt.links.new(sc.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = v
    mix.inputs["B"].default_value = (v[0] * 0.80, v[1] * 0.79, v[2] * 0.76, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.30
    rr.inputs["To Max"].default_value = 0.55
    nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_cast_alu(name, base=0.50, rough=0.45):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 8.0
    mott.inputs["Detail"].default_value = 6.0
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.84, base * 0.84, base * 0.82, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    nt.links.new(col.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 160.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def dial_image(name="Dial", n=512):
    """Level gauge face: white, black tick arc, red reserve sector, no text."""
    import numpy as np
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx - n / 2) / (n / 2)
    y = (yy - n / 2) / (n / 2)
    r = np.sqrt(x * x + y * y)
    a = np.degrees(np.arctan2(y, x))
    img = np.ones((n, n, 4), dtype=np.float32)
    img[..., :3] = 0.93
    arc = (a > -40) & (a < 220)
    ticks = arc & (r > 0.62) & (r < 0.80) & ((np.mod(a + 40, 26) < 2.6))
    img[ticks, :3] = 0.06
    band = (r > 0.80) & (r < 0.86) & arc
    img[band, :3] = 0.10
    red = (r > 0.62) & (r < 0.86) & (a > -40) & (a < 10)
    img[red, 0], img[red, 1], img[red, 2] = 0.62, 0.05, 0.04
    green = (r > 0.62) & (r < 0.86) & (a > 170) & (a < 220)
    img[green, 0], img[green, 1], img[green, 2] = 0.08, 0.38, 0.12
    rim = r > 0.95
    img[rim, :3] = 0.25
    im = bpy.data.images.new(name, n, n, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.pack()
    return im


def disc_uv(name, r, z, mat, M, seg=64):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    c = bm.verts.new((0, 0, z))
    ring = [bm.verts.new((r * math.cos(TAU * k / seg), r * math.sin(TAU * k / seg), z)) for k in range(seg)]
    for k in range(seg):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % seg]))
        for l in f.loops:
            co = l.vert.co
            l[uvl].uv = (0.5 + co.x / (2 * r), 0.5 + co.y / (2 * r))
    ob = C.mesh_obj(name, bm, [mat])
    ob.matrix_world = M
    return ob


# ----------------------------------------------------------------- parts
def toroid(paint):
    out = []
    n = 96
    P = [(RC + RS * math.cos(TAU * k / n), ZC + RS * math.sin(TAU * k / n), 0) for k in range(n)]
    ob = C.lathe("Toroid", P, [paint], steps=192)
    out.append(C.finalize(ob, angle=50))
    # weld seams (outer and inner equator)
    for rr, sgn in ((RC + RS, 1), (RC - RS, -1)):
        ring = [(rr + sgn * 0.004 + 0.022 * math.cos(TAU * k / 12), ZC + 0.03 * math.sin(TAU * k / 12), 0) for k in range(12)]
        out.append(C.finalize(C.lathe("Seam", ring, [paint], steps=192), angle=50))
    return out


def mv_frame():
    """Local frame on the inner wall: Z = outward normal (toward axis and up)."""
    rr = RC - RS * math.cos(PHI)
    z = ZC + RS * math.sin(PHI)
    ca, sa = math.cos(AZ), math.sin(AZ)
    P = Vector((rr * ca, rr * sa, z))
    nz = Vector((-math.cos(PHI) * ca, -math.cos(PHI) * sa, math.sin(PHI)))
    tx = Vector((-sa, ca, 0.0))
    ty = nz.cross(tx)
    return Matrix(((tx.x, ty.x, nz.x, P.x), (tx.y, ty.y, nz.y, P.y), (tx.z, ty.z, nz.z, P.z), (0, 0, 0, 1)))


def multivalve(paint, alu, brass, black, bolt, glass, dial_m, red, dark):
    out = []
    M = mv_frame() @ Matrix.Scale(1.3, 4)
    # welded flange ring on the tank (painted) + bolted valve flange (alu)
    out.append(lathe_at("TankFlange", [(0.0, -0.20, 0), (0.62, -0.20, 0), (0.62, 0.04, 0), (0.56, 0.07, 0), (0.0, 0.07, 0)],
                        paint, M, steps=96, bevel=0.012))
    out.append(lathe_at("ValveFlange", [(0.0, 0.06, 0), (0.52, 0.06, 0), (0.52, 0.13, 0), (0.48, 0.15, 0), (0.0, 0.15, 0)],
                        alu, M, steps=96, bevel=0.01))
    for k in range(6):
        a = TAU * k / 6 + 0.26
        Mb = M @ T((0.44 * math.cos(a), 0.44 * math.sin(a), 0))
        out.append(hex_at("Bolt", 0.045, 0.14, 0.20, bolt, Mb, bevel=0.008))
    # cast body
    def bodyf(bm):
        prism_bm(bm, rrect(0.96, 0.56, 0.16), 0.14, 0.52)
        C.box_bm(bm, 0.30, 0.20, 0.28, center=(0.52, -0.05, 0.36))     # filling-valve boss
        C.box_bm(bm, 0.22, 0.24, 0.24, center=(0.0, -0.36, 0.30))      # outlet boss
    out.append(solid("ValveBody", bodyf, [alu], bevel=0.035, M=M))
    # level gauge: housing, dial, needle, clear cover
    Mg = M @ T((0.18, 0.06, 0.52))
    out.append(lathe_at("GaugeHousing", [(0.0, 0.0, 0), (0.26, 0.0, 0), (0.26, 0.07, 0), (0.24, 0.09, 0), (0.21, 0.09, 0),
                                         (0.21, 0.05, 0), (0.0, 0.05, 0)], black, Mg, steps=64, bevel=0.006))
    out.append(disc_uv("DialFace", 0.205, 0.052, dial_m, Mg))
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.018, 0.008, center=(0.06, 0.0, 0.058), matrix=Matrix.Rotation(math.radians(150), 4, "Z"))
    C.cyl_bm(bm, 0.022, 0.052, 0.066, seg=16)
    nd = C.mesh_obj("Needle", bm, [red])
    nd.matrix_world = Mg
    out.append(C.finalize(nd, angle=40))
    out.append(lathe_at("GaugeGlass", [(0.0, 0.085, 0), (0.212, 0.085, 0), (0.212, 0.075, 0), (0.0, 0.10, 0)], glass, Mg, steps=64))
    # shut-off solenoid on the -X end
    Ms = M @ T((-0.34, 0.02, 0.50))
    out.append(lathe_at("SolenoidStem", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.48, 0), (0.0, 0.48, 0)], brass, Ms, steps=32))
    out.append(lathe_at("Coil", [(0.0, 0.04, 0), (0.17, 0.04, 0), (0.18, 0.06, 0), (0.18, 0.36, 0), (0.17, 0.38, 0), (0.0, 0.38, 0)],
                        black, Ms, steps=64, bevel=0.008))
    out.append(hex_at("CoilNut", 0.085, 0.38, 0.45, brass, Ms, bevel=0.006))
    # coil leads (red + black) curling out
    p0 = Ms @ Vector((-0.17, 0.0, 0.22))
    for i, (col, off) in enumerate(((red, 0.0), (black, 0.045))):
        pts = [Ms @ Vector((-0.16, off, 0.22)), Ms @ Vector((-0.34, off, 0.20)), Ms @ Vector((-0.50, off + 0.08, 0.05)),
               Ms @ Vector((-0.58, off + 0.20, -0.18))]
        out.append(tube("Lead", pts, 0.022, col, res=3))
    # filling valve union (+X, horizontal) with black dust cap
    Mf = M @ T((0.66, -0.05, 0.36)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(hex_at("FillHex", 0.11, 0.0, 0.10, brass, Mf, bevel=0.008))
    out.append(lathe_at("FillStem", [(0.0, 0.10, 0), (0.07, 0.10, 0), (0.07, 0.26, 0), (0.0, 0.26, 0)], brass, Mf, steps=48))
    out.append(lathe_at("FillCap", [(0.0, 0.18, 0), (0.095, 0.18, 0), (0.10, 0.20, 0), (0.10, 0.31, 0), (0.08, 0.33, 0), (0.0, 0.33, 0)],
                        black, Mf, steps=48, bevel=0.006))
    # outlet union (-Y)
    Mo = M @ T((0.0, -0.48, 0.30)) @ Matrix.Rotation(math.radians(90), 4, "X")
    out.append(hex_at("OutHex", 0.085, 0.0, 0.09, brass, Mo, bevel=0.006))
    out.append(lathe_at("OutStem", [(0.0, 0.09, 0), (0.05, 0.09, 0), (0.05, 0.20, 0), (0.0, 0.20, 0)], brass, Mo, steps=32))
    out.append(hex_at("OutNut", 0.075, 0.13, 0.21, brass, Mo, bevel=0.006))
    return out


def label(paint):
    im = C.label_image("TankLabel", 1024, 520, seed=11, lines=6)
    m = C.mat_label(im, rough=0.40)
    a = AZ + math.radians(185)        # on the top, near side
    rr = RC
    P = Vector((rr * math.cos(a), rr * math.sin(a), 2 * RS + 0.004))
    tx = Vector((-math.sin(a), math.cos(a), 0))
    ty = Vector((0, 0, -1))
    tz = tx.cross(ty)
    M = Matrix(((tx.x, ty.x, tz.x, P.x), (tx.y, ty.y, tz.y, P.y), (tx.z, ty.z, tz.z, P.z), (0, 0, 0, 1)))
    return [C.label_plane("Label", m, 0.95, 0.48, M)]


def build():
    paint = mat_tank_paint()
    alu = mat_cast_alu("ValveAlu", 0.55, 0.42)
    brass = C.principled("Brass", (0.80, 0.60, 0.30), metallic=1.0, rough=0.30)
    C.add_noise_bump(brass, scale=500, strength=0.05, distance=0.0005, rough_var=0.08)
    black = C.mat_black_plastic("CoilPA", rough=0.42, color=0.022)
    bolt = C.principled("ZincBolt", (0.62, 0.62, 0.64), metallic=1.0, rough=0.28)
    glass = C.mat_clear("GaugeCover", rough=0.02, ior=1.5)
    dial_m = C.mat_label(dial_image(), "DialMat", rough=0.3)
    red = C.principled("RedLead", (0.45, 0.03, 0.03), rough=0.4)
    dark = C.principled("Hole", (0.01, 0.01, 0.01), rough=0.8)
    objs = toroid(paint)
    objs += multivalve(paint, alu, brass, black, bolt, glass, dial_m, red, dark)
    objs += label(paint)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("serbatoio-gpl", objs, "serbatoio-gpl.py",
            "LPG toroidal (doughnut) tank: pale grey painted steel toroid with weld seam, blank data label, multivalve "
            "with level gauge, solenoid and brass unions on the inner wall",
            az=30, el=42, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
