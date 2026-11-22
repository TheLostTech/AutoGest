"""Sunroof assembly (tilt-and-slide cassette) of a generic modern small hatchback, removed
from the car. Black e-coated steel frame with a rain gutter all round and bolting tabs;
dark-tinted glass panel with black ceramic border and rubber edge seal in the front
opening; satin aluminium guide rails down both sides of the open rear section; electric
drive motor with gearbox under the front member and the two drive cables in their tubes;
pop-up wind deflector; rubber drain tubes leaving the four gutter corners.
Car front is -Y, roof outside is +Z."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

UP = Vector((0, 0, 1))
FX, FY0, FY1, FR = 0.43, -0.51, 0.47, 0.065       # frame centre-line rounded rect
GX, GY0, GY1, GR = 0.383, -0.468, -0.022, 0.05     # glass outline
FRIT = 0.034
GL_T = 0.0045


def sheet_section(poly, t, r=0.003):
    pts = P.rounded(poly, [r] * len(poly), closed=False, seg=6)
    pts = P.resample(pts, 48)
    inner = P.offset2d(pts, -t)
    return [(p.x, p.y) for p in pts + inner[::-1]]


def rrect_path(x0, x1, y0, y1, r, n=400):
    pts = P.rounded([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [r] * 4, closed=True, seg=16)
    return P.resample(pts, n, closed=True)


def frame(ecoat):
    path = [Vector((p.x, p.y, 0.0)) for p in rrect_path(-FX, FX, FY0, FY1, FR, 520)]
    fr = P.path_frames(path, (0, 0, 1), closed=True)     # A points outward (CCW path)
    # gutter section (a outward, b up): inner lip, gutter floor, outer wall, bolting flange
    sec = sheet_section([(-0.026, 0.004), (-0.026, -0.024), (0.024, -0.024), (0.026, 0.002), (0.058, 0.002)], 0.0016, r=0.004)
    sec = sec[::-1]
    bm = bmesh.new()
    P.tube_bm(bm, fr, sec, closed=True)
    C.fix_normals(bm)
    ob = C.mesh_obj("Frame", bm, [ecoat])
    C.add_bevel(ob, 0.0006, segments=1, angle=40)
    out = [C.finalize(ob, angle=40)]
    # pressed stiffening bead along the flange, bolting tabs
    bm = bmesh.new()
    tabs = [(-FX - 0.068, y) for y in (-0.36, 0.0, 0.33)] + [(FX + 0.068, y) for y in (-0.36, 0.0, 0.33)] + \
           [(x, FY1 + 0.068) for x in (-0.22, 0.22)] + [(x, FY0 - 0.068) for x in (-0.25, 0.25)]
    for (x, y) in tabs:
        sx = 0.05 if abs(y) < FY1 + 0.05 and abs(x) > FX else 0.036
        sy = 0.036 if abs(x) > FX else 0.05
        C.box_bm(bm, sx, sy, 0.0016, center=(x, y, 0.0028))
    tb = C.mesh_obj("Tabs", bm, [ecoat])
    cb = bmesh.new()
    for (x, y) in tabs:
        xx = x + (0.008 if x > FX else -0.008 if x < -FX else 0)
        yy = y + (0.008 if y > FY1 else -0.008 if y < FY0 else 0)
        C.cyl_bm(cb, 0.0055, -0.02, 0.02, seg=24, matrix=Matrix.Translation((xx, yy, 0.0)))
    cut = C.mesh_obj("TabHoles", cb, [ecoat])
    m = C.add_boolean(tb, cut)
    m.use_self = True
    C.add_bevel(tb, 0.0007, segments=1, angle=30)
    out.append(C.finalize(tb, angle=35, remove=[cut]))
    # cross member under the front of the rear opening (carries the rails' middle)
    bm = bmesh.new()
    C.box_bm(bm, 2 * FX - 0.02, 0.05, 0.0016, center=(0, 0.21, -0.022))
    C.box_bm(bm, 2 * FX - 0.02, 0.0016, 0.018, center=(0, 0.186, -0.014))
    C.box_bm(bm, 2 * FX - 0.02, 0.0016, 0.018, center=(0, 0.234, -0.014))
    cm = C.mesh_obj("CrossMember", bm, [ecoat])
    C.add_bevel(cm, 0.0006, segments=1, angle=30)
    out.append(C.finalize(cm, angle=35))
    return out


def crown(x, y):
    return 0.010 - 0.012 * (x / 0.40) ** 2 - 0.006 * ((y + 0.245) / 0.25) ** 2


def glass_pt(q, off=0.0):
    return Vector((q.x, q.y, crown(q.x, q.y) - off))


def privacy_glass():
    m = C.mat_clear("SunroofTint", ior=1.52)
    nt = m.node_tree
    a = P.bsdf(m)
    C._set(a, "Base Color", (0.30, 0.35, 0.34, 1))
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.006, 0.008, 0.009, 1)
    b.inputs["Roughness"].default_value = 0.03
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.55
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def glass(tint, frit, rubber):
    outer = rrect_path(-GX, GX, GY0, GY1, GR, 360)
    inner = rrect_path(-GX + FRIT, GX - FRIT, GY0 + FRIT, GY1 - FRIT, max(0.01, GR - FRIT * 0.6), 360)
    rows = [[glass_pt(a.lerp(b, k / 4)) for a, b in zip(outer, inner)] for k in range(5)]
    ring = P.grid_obj("Frit", rows, [frit], UP, closed_u=True)
    P.solidify(ring, GL_T, offset=-1)
    C.add_bevel(ring, 0.0012, segments=2, angle=50)
    out = [C.finalize(ring, angle=50)]
    c = Vector((0.0, (GY0 + GY1) / 2))
    gl = P.fan_obj("SunroofGlass", inner, c, 24, glass_pt, [tint], UP, power=1.2)
    P.solidify(gl, GL_T, offset=-1)
    out.append(C.finalize(gl, angle=60))
    # encapsulated edge seal
    path = [glass_pt(q, GL_T * 0.5) for q in rrect_path(-GX - 0.003, GX + 0.003, GY0 - 0.003, GY1 + 0.003, GR + 0.003, 360)]
    fr = P.path_frames(path, (0, 0, 1), closed=True)
    sec = [(-0.004, -0.004), (0.002, -0.006), (0.006, -0.002), (0.0065, 0.003), (0.003, 0.0045), (-0.004, 0.003)]
    out.append(P.tube_obj("EdgeSeal", fr, sec, [rubber], closed=True, smooth_angle=60))
    return out


def rails(alu, black):
    out = []
    for sx in (-1, 1):
        x = sx * 0.402
        sec = [(-0.014, -0.022), (0.014, -0.022), (0.014, -0.004), (0.010, -0.004), (0.010, -0.014), (0.004, -0.014),
               (0.004, -0.002), (-0.004, -0.002), (-0.004, -0.014), (-0.010, -0.014), (-0.010, -0.004), (-0.014, -0.004)]
        sec = [(a * sx, b) for (a, b) in sec]
        if sx < 0:
            sec = sec[::-1]
        pts = [Vector((x, -0.47 + 0.92 * k / 60, 0.0)) for k in range(61)]
        fr = [(p, Vector((1, 0, 0)), Vector((0, 0, 1))) for p in pts]
        ob = P.tube_obj("Rail", fr, sec, [alu], smooth_angle=30, bevel=0.0007)
        out.append(ob)
        # sliding glass carriers / shoes at the front of the rails
        for y in (-0.42, -0.08):
            bm = bmesh.new()
            C.box_bm(bm, 0.0075, 0.045, 0.012, center=(x, y, -0.012))
            C.box_bm(bm, 0.022, 0.03, 0.004, center=(x - sx * 0.006, y, -0.001))
            sh = C.mesh_obj("Shoe", bm, [black])
            C.add_bevel(sh, 0.001, segments=2, angle=30)
            out.append(C.finalize(sh, angle=35))
    return out


def deflector(black, mesh_m):
    out = []
    y = FY0 + 0.028
    pts = [Vector((-0.36 + 0.72 * k / 80, y, 0.018 - 0.006 * ((-0.36 + 0.72 * k / 80) / 0.36) ** 2)) for k in range(81)]
    fr = P.path_frames(pts, (0, 0.25, 1))
    out.append(P.tube_obj("DeflectorBar", fr, P.rrect(-0.006, 0.006, -0.003, 0.003, 0.002), [black], smooth_angle=50))
    pts2 = [p + Vector((0, 0.010, -0.022)) for p in pts]
    rows = [pts2, [p + Vector((0, 0.005, -0.011)) for p in pts], [p + Vector((0, 0.0, -0.003)) for p in pts]]
    ob = P.grid_obj("DeflectorMesh", rows, [mesh_m], Vector((0, -1, 0.3)))
    P.solidify(ob, 0.001, offset=0)
    out.append(C.finalize(ob, angle=50))
    for sx in (-1, 1):
        bm = bmesh.new()
        C.box_bm(bm, 0.012, 0.035, 0.008, center=(sx * 0.37, y + 0.014, 0.004),
                 matrix=None)
        arm = C.mesh_obj("DeflArm", bm, [black])
        C.add_bevel(arm, 0.0012, segments=2, angle=30)
        out.append(C.finalize(arm, angle=35))
    return out


def motor(black, can, connector, cable):
    out = []
    y = FY0 - 0.075
    z = -0.018
    bm = bmesh.new()
    P.superellipsoid(bm, 0.050, 0.030, 0.016, e1=0.3, e2=0.3, matrix=Matrix.Translation((0.0, y, z)))
    gb = C.mesh_obj("Gearbox", bm, [black])
    out.append(C.finalize(gb, angle=45))
    # motor can along +X, end cap
    can_o = C.lathe("MotorCan", [(0.0, 0.0, 0), (0.016, 0.0, 0), (0.0175, 0.003, 0), (0.0175, 0.062, 0), (0.016, 0.066, 0),
                                  (0.006, 0.068, 0), (0.006, 0.073, 0), (0.0, 0.073, 0)], [can], steps=48)
    can_o.matrix_world = Matrix.Translation((0.04, y + 0.004, z + 0.002)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(C.finalize(can_o, angle=40))
    # brush-holder end cap in black plastic
    cap = C.lathe("MotorCap", [(0.0, 0.0, 0), (0.0172, 0.0, 0), (0.0172, 0.012, 0), (0.014, 0.016, 0), (0.0, 0.016, 0)], [black], steps=48)
    cap.matrix_world = Matrix.Translation((0.024, y + 0.004, z + 0.002)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(C.finalize(cap, angle=40))
    # connector
    bm = bmesh.new()
    C.box_bm(bm, 0.024, 0.016, 0.014, center=(-0.040, y - 0.022, z + 0.004))
    cn = C.mesh_obj("Connector", bm, [connector])
    C.add_bevel(cn, 0.0015, segments=2, angle=30)
    out.append(C.finalize(cn, angle=35))
    # mounting bracket up to the frame
    bm = bmesh.new()
    for dx in (-0.045, 0.045):
        C.box_bm(bm, 0.014, 0.05, 0.003, center=(dx, y + 0.03, 0.0035))
    br = C.mesh_obj("MotorBracket", bm, [black])
    C.add_bevel(br, 0.001, segments=1, angle=30)
    out.append(C.finalize(br, angle=35))
    # drive cable tubes to the two rails
    for sx in (-1, 1):
        pts = [Vector((sx * 0.012, y + 0.02, z - 0.004)), Vector((sx * 0.06, FY0 - 0.02, -0.030)), Vector((sx * 0.12, FY0 + 0.010, -0.030)),
               Vector((sx * 0.30, FY0 + 0.012, -0.028)), Vector((sx * 0.385, FY0 + 0.035, -0.024)),
               Vector((sx * 0.402, -0.46, -0.018))]
        pts = P.bspline(pts, 90)
        fr = P.path_frames(pts, (0, 0, 1))
        out.append(P.tube_obj("CableTube", fr, P.circle(0.0042, 16), [cable], smooth_angle=60))
    return out


def drains(rubber):
    out = []
    corners = [(-1, FY0, -1), (1, FY0, -1), (-1, FY1, 1), (1, FY1, 1)]
    for sx, y, sy in corners:
        x = sx * (FX - 0.03)
        yy = y + sy * -0.03 + sy * 0.03
        o = Vector((x + sx * 0.012, yy + sy * 0.012, -0.025))
        pts = [o, o + Vector((0, 0, -0.012)), o + Vector((sx * 0.012, sy * 0.02, -0.026)),
               o + Vector((sx * 0.02, sy * 0.06, -0.032)), o + Vector((sx * 0.012, sy * 0.10, -0.034))]
        pts = P.bspline(pts, 70)
        fr = P.path_frames(pts, (0, 0, 1))
        sec = P.circle(0.0062, 20)
        inner = [(a * 0.62, b * 0.62) for (a, b) in P.circle(0.0062, 20)]
        bm = bmesh.new()
        P.tube_bm(bm, fr, sec, cap=False)
        P.tube_bm(bm, fr, inner[::-1], cap=False)
        # annular end caps (open tube)
        n = len(sec)
        verts = list(bm.verts)
        m = len(fr)
        outer_r = verts[:m * n]
        inner_r = verts[m * n:]
        for (ring_o, ring_i, rev) in ((outer_r[:n], inner_r[:n], True), (outer_r[-n:], inner_r[-n:], False)):
            for k in range(n):
                k2 = (k + 1) % n
                f = (ring_o[k], ring_o[k2], ring_i[n - 1 - k2], ring_i[n - 1 - k])
                try:
                    bm.faces.new(f[::-1] if rev else f)
                except ValueError:
                    pass
        C.fix_normals(bm)
        ob = C.mesh_obj("DrainTube", bm, [rubber])
        out.append(C.finalize(ob, angle=50))
        # spigot on the gutter corner
        sp = C.lathe("Spigot", [(0.0, 0.0, 0), (0.0075, 0.0, 0), (0.0075, 0.014, 0), (0.0, 0.014, 0)], [rubber], steps=24)
        sp.matrix_world = Matrix.Translation(o + Vector((0, 0, -0.004)))
        out.append(C.finalize(sp, angle=40))
    return out


def build():
    ec = P.ecoat("FrameEcoat", v=0.04, rough=0.42)
    alu = C.principled("RailAlu", (0.72, 0.72, 0.74), metallic=1.0, rough=0.3)
    C.add_noise_bump(alu, scale=400, strength=0.05, distance=0.0003, rough_var=0.06)
    black = C.mat_black_plastic("PA66", rough=0.45)
    rubber = C.mat_rubber()
    tint = privacy_glass()
    frit = C.principled("CeramicFrit", (0.008, 0.008, 0.009), rough=0.06)
    can = C.principled("MotorCan", (0.62, 0.62, 0.64), metallic=1.0, rough=0.28)
    connector = C.mat_black_plastic("ConnGrey", rough=0.5, color=0.12)
    cable = C.mat_black_plastic("CableTube", rough=0.35, color=0.02)
    mesh_m = P.textured_black("DeflMesh", rough=0.7, v=0.02)
    objs = frame(ec)
    objs += glass(tint, frit, rubber)
    objs += rails(alu, black)
    objs += deflector(black, mesh_m)
    objs += motor(black, can, connector, cable)
    objs += drains(rubber)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("tetto-apribile", objs, "tetto-apribile.py",
            "sunroof assembly / cassette (generic small hatchback): tinted glass panel with black border in a black steel "
            "frame with rain gutter, aluminium guide rails, drive motor and cable tubes, wind deflector, drain tubes",
            az=-30, el=34, lens=70, fill=0.88, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
