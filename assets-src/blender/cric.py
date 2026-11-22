"""Scissor jack (cric) from a small car's spare-wheel well, half open: pressed-steel
U-channel base with flanges, four pressed-steel arms with meshing gear segments at
the base and saddle pivots, grooved saddle for the sill pinch-weld, two trunnions
with the long threaded screw, eye for the crank, and the folding crank handle lying
beside it. Black paint worn on the edges, zinc-plated screw and pins."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm. Jack along X, diamond in the XZ plane, Y across
L = 1.75                      # arm pin-to-pin length
ALPHA = math.radians(31)      # arm angle from horizontal (half open)
PX = 0.17                     # pin offset from centre at base / saddle
ZB = 0.46                     # base pin height
XS = PX + L * math.cos(ALPHA)
ZS = ZB + L * math.sin(ALPHA)
ZT = ZS + L * math.sin(ALPHA)
WL, WU = 0.60, 0.50           # lower / upper arm widths (Y)
TH = 0.035                    # sheet thickness


def mat_worn_black(name="ArmPaint"):
    m = C.mat_paint(name, (0.022, 0.022, 0.024, 1), rough=0.42, coat=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 14.0
    nz.inputs["Detail"].default_value = 10.0
    em = C.edge_mask(nt, 0.02, 5.0)
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.55
    th.inputs["From Max"].default_value = 0.62
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    nt.links.new(em, mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 1.3
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], th.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs["B"].default_value = (0.20, 0.19, 0.18, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.42
    ro.inputs["To Max"].default_value = 0.8
    nt.links.new(th.outputs["Result"], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # orange-peel
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 220.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def stadium(a, b, rad, n=14):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    nrm = Vector((-d.y, d.x))
    ang = math.atan2(d.y, d.x)
    pts = []
    for i in range(n + 1):
        t = ang - math.pi / 2 + math.pi * i / n
        pts.append(b + rad * Vector((math.cos(t), math.sin(t))))
    for i in range(n + 1):
        t = ang + math.pi / 2 + math.pi * i / n
        pts.append(a + rad * Vector((math.cos(t), math.sin(t))))
    return pts


def plate_xz(bm, poly, y0, y1):
    """polygon in XZ, extruded along Y"""
    vb = [bm.verts.new((p.x if hasattr(p, "x") else p[0], y0, p.y if hasattr(p, "y") else p[1])) for p in poly]
    vt = [bm.verts.new((v.co.x, y1, v.co.z)) for v in vb]
    m = len(poly)
    f1 = bm.faces.new(vb)
    f2 = bm.faces.new(vt[::-1])
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vb[i], vt[i], vt[j], vb[j]))


def gear_sector(bm, c, r, y0, y1, a0, a1, teeth=7):
    pts = [Vector(c)]
    n = teeth * 6
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        rr = r + (0.035 if math.cos((a - a0) / (a1 - a0) * teeth * math.tau) > 0 else 0.0)
        pts.append(Vector(c) + rr * Vector((math.cos(a), math.sin(a))))
    plate_xz(bm, pts, y0, y1)


def arm(paint, a, b, w, gear_at_a, gear_dir, web_side):
    """two side plates + a web plate; gear segment around pin a"""
    bm = bmesh.new()
    a, b = Vector(a), Vector(b)
    for s in (-1, 1):
        y0 = s * w / 2
        y1 = y0 - s * TH
        lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
        plate_xz(bm, stadium(a, b, 0.14), lo, hi)
        if gear_at_a:
            gear_sector(bm, a, 0.14, lo, hi, gear_dir - 0.9, gear_dir + 0.9)
    # web: strip along the arm joining both sides, offset to one edge of the plates
    d = (b - a).normalized()
    nrm = Vector((-d.y, d.x)) * web_side
    p0 = a + d * 0.20 + nrm * 0.10
    p1 = b - d * 0.20 + nrm * 0.10
    q0 = p0 + nrm * TH
    q1 = p1 + nrm * TH
    plate_xz(bm, [p0, p1, q1, q0], -w / 2 + TH * 0.5, w / 2 - TH * 0.5)
    C.fix_normals(bm)
    ob = C.mesh_obj("Arm", bm, [paint])
    C.add_bevel(ob, 0.008, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def base(paint):
    bm = bmesh.new()
    # bottom plate with upturned edges
    C.box_bm(bm, 3.0, 0.95, TH, center=(0, 0, TH / 2))
    # side walls: trapezoid hump carrying the lower pins
    wall = [Vector((-1.45, 0.0)), Vector((1.45, 0.0)), Vector((1.30, 0.14)), Vector((0.42, 0.50)),
            Vector((0.30, 0.58)), Vector((-0.30, 0.58)), Vector((-0.42, 0.50)), Vector((-1.30, 0.14))]
    for s in (-1, 1):
        y = s * (WL / 2 + 0.03)
        plate_xz(bm, wall, min(y, y + s * TH), max(y, y + s * TH))
    # end flanges
    for s in (-1, 1):
        C.box_bm(bm, TH, 0.95, 0.10, center=(s * 1.485, 0, 0.05))
    C.fix_normals(bm)
    ob = C.mesh_obj("Base", bm, [paint])
    C.add_bevel(ob, 0.01, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def saddle(paint):
    bm = bmesh.new()
    zt = ZT
    # cheeks down to the upper pins
    cheek = [Vector((-0.45, zt + 0.10)), Vector((0.45, zt + 0.10)), Vector((0.36, zt - 0.14)), Vector((-0.36, zt - 0.14))]
    for s in (-1, 1):
        y = s * (WU / 2 + 0.03)
        plate_xz(bm, cheek, min(y, y + s * TH), max(y, y + s * TH))
    # top: two blocks leaving a groove along Y for the pinch weld
    for s in (-1, 1):
        C.box_bm(bm, 0.36, 0.82, 0.16, center=(s * 0.25, 0, zt + 0.18))
    C.box_bm(bm, 0.86, 0.82, 0.05, center=(0, 0, zt + 0.12))
    C.fix_normals(bm)
    ob = C.mesh_obj("Saddle", bm, [paint])
    C.add_bevel(ob, 0.015, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def pins(zinc):
    bm = bmesh.new()
    for x, z in ((-PX, ZB), (PX, ZB), (-PX, ZT), (PX, ZT)):
        w = WL if z == ZB else WU
        C.cyl_bm(bm, 0.045, -w / 2 - 0.08, w / 2 + 0.08, seg=20, matrix=axis_mat((x, 0, z), (0, 1, 0)) @ Matrix.Translation((0, 0, 0)))
        for s in (-1, 1):
            C.cyl_bm(bm, 0.07, s * (w / 2 + 0.06) - 0.02, s * (w / 2 + 0.06) + 0.02, seg=20, matrix=axis_mat((x, 0, z), (0, 1, 0)))
    ob = C.mesh_obj("Pins", bm, [zinc])
    C.add_bevel(ob, 0.006, segments=1, angle=30)
    return C.finalize(ob, angle=35)


def trunnions(paint, zinc):
    out = []
    for s in (-1, 1):
        ob = C.lathe("Trunnion", [(0.0, -WL / 2 - 0.02, 0), (0.12, -WL / 2 - 0.02, 0), (0.12, WL / 2 + 0.02, 0), (0.0, WL / 2 + 0.02, 0)], [zinc], steps=40)
        ob.matrix_world = axis_mat((s * XS, 0, ZS), (0, 1, 0))
        C.add_bevel(ob, 0.01, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    return out


def screw(zinc, dark):
    out = []
    x0, x1 = -XS - 0.22, XS + 0.40
    P = [(0.0, x0, 0), (0.05, x0, 0)]
    z = x0 + 0.02
    while z < XS - 0.05:
        P += [(0.068, z + 0.018, 0), (0.054, z + 0.036, 0)]
        z += 0.036
    P += [(0.06, z + 0.02, 0), (0.06, XS + 0.12, 0), (0.0, XS + 0.12, 0)]
    ob = C.lathe("Screw", P, [zinc], steps=32)
    ob.matrix_world = Matrix.Translation((0, 0, ZS)) @ axis_mat((0, 0, 0), (1, 0, 0))
    out.append(C.finalize(ob, angle=50))
    # thrust washer + nut at the near trunnion, crank eye at the end
    P = [(0.06, XS + 0.12, 0), (0.15, XS + 0.12, 0), (0.15, XS + 0.17, 0), (0.06, XS + 0.17, 0)]
    ob = C.lathe("Washer", P, [zinc], steps=48)
    ob.matrix_world = Matrix.Translation((0, 0, ZS)) @ axis_mat((0, 0, 0), (1, 0, 0))
    out.append(C.finalize(ob, angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.12, XS + 0.17, XS + 0.27, seg=6, matrix=Matrix.Translation((0, 0, ZS)) @ axis_mat((0, 0, 0), (1, 0, 0)))
    nut = C.mesh_obj("Nut", bm, [zinc])
    C.add_bevel(nut, 0.012, segments=1, angle=30)
    out.append(C.finalize(nut, angle=35))
    # eye: torus in the XZ... ring standing in the XY plane? -> ring axis along Y
    ob = C.lathe("Eye", [(0.085, -0.03, 0), (0.15, -0.03, 0), (0.15, 0.03, 0), (0.085, 0.03, 0)], [zinc], steps=40)
    ob.matrix_world = axis_mat((XS + 0.40, 0, ZS), (0, 1, 0))
    C.add_bevel(ob, 0.01, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    # fill gap nut->eye with a short shank
    ob = C.lathe("Shank", [(0.0, XS + 0.26, 0), (0.06, XS + 0.26, 0), (0.06, XS + 0.33, 0), (0.0, XS + 0.33, 0)], [zinc], steps=24)
    ob.matrix_world = Matrix.Translation((0, 0, ZS)) @ axis_mat((0, 0, 0), (1, 0, 0))
    out.append(C.finalize(ob, angle=40))
    return out


def crank(paint):
    """folding crank lying on the floor in front: hook, long shaft, offset handle"""
    pts = [(-1.7, -1.05, 0.05), (1.0, -1.05, 0.05), (1.2, -1.05, 0.05), (1.32, -1.25, 0.05),
           (1.32, -1.55, 0.05), (1.45, -1.62, 0.05), (2.0, -1.62, 0.05)]
    cu = bpy.data.curves.new("Crank", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.05
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    # hook at the start: small bend
    sp2 = cu.splines.new("BEZIER")
    hook = [(-1.7, -1.05, 0.05), (-1.85, -1.02, 0.05), (-1.92, -0.88, 0.05), (-1.82, -0.78, 0.05)]
    sp2.bezier_points.add(len(hook) - 1)
    for bp, p in zip(sp2.bezier_points, hook):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new("Crank", cu))
    cu.materials.append(paint)
    out = [C.finalize(ob, angle=60)]
    # plastic grip on the handle
    g = C.lathe("Grip", [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.10, 0.05, 0), (0.10, 0.45, 0), (0.085, 0.5, 0), (0.0, 0.5, 0)],
                [paint], steps=40)
    g.matrix_world = axis_mat((1.48, -1.62, 0.10), (1, 0, 0))
    out.append(C.finalize(g, angle=40))
    return out


def build():
    paint = mat_worn_black("JackPaint")
    zinc = C.principled("Zinc", (0.62, 0.63, 0.64), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=500, strength=0.06, distance=0.0005, rough_var=0.07)
    grip = C.mat_black_plastic("Grip", rough=0.55, color=0.03)
    objs = [base(paint), saddle(paint), pins(zinc)]
    # lower arms (pivot at base pins), upper arms (pivot at saddle pins)
    for s in (-1, 1):
        gdir = math.pi if s > 0 else 0.0          # gear segments face each other
        objs.append(arm(paint, (s * PX, ZB), (s * XS, ZS), WL, True, gdir, web_side=-s))
        objs.append(arm(paint, (s * PX, ZT), (s * XS, ZS), WU, True, gdir, web_side=s))
    objs += trunnions(paint, zinc) + screw(zinc, paint)
    cr = crank(paint)
    cr[1].data.materials[0] = grip
    objs += cr
    C.transform_all(objs, Matrix.Rotation(math.radians(-8), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("cric", objs, "cric.py",
            "scissor jack half open: black pressed-steel base, four arms with gear ends, grooved saddle, zinc threaded screw with crank eye, crank handle beside it",
            az=24, el=16, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
