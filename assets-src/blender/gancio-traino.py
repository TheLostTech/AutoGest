"""Tow bar (fixed swan-neck towing hitch), generic small hatchback: black powder-coated
steel box-section crossbar with plastic end caps, two side brackets with bolt holes that
run forward to the chassis rails, a central mounting plate bolted to the forged swan
neck, the 50 mm tow ball (bare machined steel) and the black 13-pin electrical socket
with hinged lid on its bracket, its corrugated cable looped to the crossbar.
Car rear is -Y, crossbar along X."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
LX = 0.96              # crossbar length
BH, BD = 0.070, 0.050  # crossbar height (Z), depth (Y)
RX = Matrix.Rotation(math.radians(90), 4, "X")
RY = Matrix.Rotation(math.radians(90), 4, "Y")


def bool_cut(ob, cut):
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_powder(name="PowderBlack"):
    m = C.principled(name, (0.022, 0.022, 0.024), rough=0.38, Coat_Weight=0.25)
    C.add_noise_bump(m, scale=260, strength=0.18, distance=0.0006, rough_var=0.05)   # orange-peel
    nt = m.node_tree
    b = P.bsdf(m)
    em = C.edge_mask(nt, 0.0025, 1.6)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 60.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.5
    mr.inputs["From Max"].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs["B"].default_value = (0.16, 0.10, 0.07, 1)        # light rust bloom on chipped edges
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def crossbar(pc, cap_m):
    out = []
    sec = P.rrect(-BD / 2, BD / 2, -BH / 2, BH / 2, 0.007, seg=5)
    frames = [(Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec) for x in (-LX / 2, LX / 2)]
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Crossbar", bm, [pc])
    C.add_bevel(ob, 0.0015, segments=2, angle=60)
    out.append(C.finalize(ob, angle=50))
    for s in (-1, 1):
        fr = []
        for j in range(6):
            t = j / 5
            sc = 1.0 - 0.10 * t * t
            fr.append((Vector((s * (LX / 2 - 0.002 + 0.008 * t), 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                       [(a * sc, b * sc) for a, b in P.rrect(-BD / 2 - 0.001, BD / 2 + 0.001, -BH / 2 - 0.001, BH / 2 + 0.001, 0.008, seg=5)]))
        bm = bmesh.new()
        C.sweep(bm, fr, mat=0)
        C.fix_normals(bm)
        out.append(C.finalize(C.mesh_obj("EndCap", bm, [cap_m]), angle=55))
    return out


def plate_yz(name, poly, x0, x1, mat, holes=(), bevel=0.0008):
    """2D outline (y, z) in m extruded along X between x0, x1; holes [(y, z, r)]."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, p[0], p[1])) for p in poly]
    b = [bm.verts.new((x1, p[0], p[1])) for p in poly]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    cut = None
    if holes:
        cb = bmesh.new()
        for (y, z, r) in holes:
            C.cyl_bm(cb, r, -0.05, 0.05, seg=32, matrix=Matrix.Translation(((x0 + x1) / 2, y, z)) @ RY)
        cut = C.mesh_obj(name + "Cut", cb, [mat])
        bool_cut(ob, cut)
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut] if cut else [])


def side_brackets(pc):
    out = []
    poly = P.rounded([Vector(p) for p in ((-0.030, -0.040), (0.30, -0.026), (0.32, 0.030), (0.30, 0.040), (-0.030, 0.040))],
                     [0.004, 0.016, 0.012, 0.016, 0.004], closed=True, seg=8)
    poly = [(p.x, p.y) for p in poly]
    holes = [(0.17, 0.006, 0.0062), (0.23, 0.004, 0.0062), (0.29, 0.006, 0.0062)]
    for s in (-1, 1):
        x = s * 0.405
        out.append(plate_yz("SideBracket", poly, x - 0.003, x + 0.003, pc, holes))
        # stiffening gusset welded under the crossbar
        g = [(0.02, -0.035), (0.11, -0.022), (0.02, -0.010)]
        out.append(plate_yz("Gusset", g, x - s * 0.012 - 0.002, x - s * 0.012 + 0.002, pc, bevel=0.0006))
    return out


def neck(pc, ball_m, bolt_m):
    out = []
    # mounting plate on the rear face of the crossbar, reaching below it
    poly = P.rounded([Vector(p) for p in ((-0.055, -0.12), (0.055, -0.12), (0.055, 0.03), (-0.055, 0.03))], [0.01] * 4, closed=True, seg=6)
    bm = bmesh.new()
    a = [bm.verts.new((p.x, -BD / 2 - 0.010, p.y)) for p in poly]
    b = [bm.verts.new((p.x, -BD / 2, p.y)) for p in poly]
    n = len(poly)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    C.fix_normals(bm)
    pl = C.mesh_obj("NeckPlate", bm, [pc])
    C.add_bevel(pl, 0.001, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    # swan neck: forged round bar from the plate bottom, back and up
    ctrl = [Vector(p) for p in ((0, -0.03, -0.085), (0, -0.07, -0.090), (0, -0.115, -0.075), (0, -0.140, -0.035),
                                (0, -0.150, 0.010), (0, -0.152, 0.050))]
    pts = P.bspline(ctrl, n=120)
    fr = P.path_frames(pts, (1, 0, 0))
    sec = P.circle(0.0155, 40)
    nb = [(a * 1.0, b * 1.0) for a, b in sec]
    out.append(P.tube_obj("Neck", fr, nb, [pc], smooth_angle=60))
    # neck foot block on the plate
    bm = bmesh.new()
    C.box_bm(bm, 0.044, 0.024, 0.040, center=(0, -BD / 2 - 0.022, -0.088))
    ft = C.mesh_obj("NeckFoot", bm, [pc])
    C.add_bevel(ft, 0.004, segments=3, angle=30)
    out.append(C.finalize(ft, angle=40))
    # ball with its collar
    top = pts[-1]
    ball = C.lathe("Ball", [(0.0, 0.0, 0), (0.0155, 0.0, 0), (0.0155, 0.006, 0), (0.019, 0.008, 0), (0.019, 0.012, 0), (0.0125, 0.016, 0),
                            (0.0125, 0.024, 0)] +
                   [(0.025 * math.sin(math.pi * k / 24 + 0.52), 0.046 - 0.025 * math.cos(math.pi * k / 24 + 0.52), 1) for k in range(0, 25)
                    if 0.025 * math.sin(math.pi * k / 24 + 0.52) > 0.0005] + [(0.0, 0.071, 1)],
                   [pc, ball_m], steps=64)
    ball.matrix_world = Matrix.Translation(top)
    out.append(C.finalize(ball, angle=40))
    # two hex bolts through the plate
    for x in (-0.034, 0.034):
        hx = C.lathe("Bolt", [(0.0, 0.0, 0), (0.0105, 0.0, 0), (0.0105, 0.009, 0), (0.0095, 0.010, 0), (0.0, 0.010, 0)], [bolt_m],
                     steps=6)
        hx.matrix_world = Matrix.Translation((x, -BD / 2 - 0.010, -0.06)) @ RX
        out.append(C.finalize(hx, angle=20))
    return out


def socket(plastic, lid_m, loom):
    out = []
    # bracket welded to the neck side
    p0 = Vector((0.020, -0.135, -0.040))
    bm = bmesh.new()
    C.box_bm(bm, 0.050, 0.004, 0.050, center=(0.040, -0.128, -0.045))
    br = C.mesh_obj("SocketBracket", bm, [plastic[1]])
    C.add_bevel(br, 0.001, segments=2, angle=30)
    out.append(C.finalize(br, angle=35))
    # socket body (axis along -Y, slightly tipped down)
    M = Matrix.Translation((0.040, -0.131, -0.045)) @ Matrix.Rotation(math.radians(-15), 4, "X") @ RX
    body = C.lathe("Socket", [(0.0, -0.030, 0), (0.016, -0.030, 0), (0.019, -0.020, 0), (0.019, 0.0, 0), (0.030, 0.0, 0),
                              (0.030, 0.004, 0), (0.024, 0.006, 0), (0.024, 0.034, 0), (0.021, 0.036, 0), (0.0, 0.036, 0)],
                   [plastic[0]], steps=64)
    body.matrix_world = M
    out.append(C.finalize(body, angle=40))
    # hinged lid on the face
    lid = C.lathe("Lid", [(0.0, 0.036, 0), (0.026, 0.036, 0), (0.026, 0.044, 0), (0.022, 0.048, 0), (0.0, 0.049, 0)], [lid_m], steps=64)
    lid.matrix_world = M
    out.append(C.finalize(lid, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.014, 0.006, 0.010, center=(0, 0.027, 0.042))      # hinge knuckle at the top
    hk = C.mesh_obj("Hinge", bm, [lid_m])
    C.add_bevel(hk, 0.0015, segments=2, angle=30)
    hk.matrix_world = M
    out.append(C.finalize(hk, angle=35))
    # corrugated cable from the socket back to the crossbar
    st = M @ Vector((0, 0, -0.030))
    ctrl = [st, st + Vector((0.01, 0.03, -0.01)), Vector((0.090, -0.080, -0.075)), Vector((0.150, -0.060, -0.045)),
            Vector((0.190, -0.036, -0.010)), Vector((0.230, -0.030, 0.012))]
    pts = P.bspline(ctrl, n=160)
    acc = 0.0
    frames = []
    for i, p in enumerate(pts):
        if i:
            acc += (p - pts[i - 1]).length
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        U = Vector((0, 0, 1)).cross(T)
        if U.length < 1e-6:
            U = Vector((1, 0, 0))
        U.normalize()
        V = T.cross(U)
        r = 0.0062 + 0.0008 * math.cos(acc / 0.0042 * math.tau)
        frames.append((p, U, V, [(r * math.cos(math.tau * k / 18), r * math.sin(math.tau * k / 18)) for k in range(18)]))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("Loom", bm, [loom]), angle=55))
    return out


def build():
    pc = mat_powder()
    cap_m = C.mat_black_plastic("CapPE", rough=0.5, color=0.025)
    ball_m = C.principled("BallSteel", (0.62, 0.62, 0.63), metallic=1.0, rough=0.22)
    C.add_noise_bump(ball_m, scale=300, strength=0.10, distance=0.0004, rough_var=0.08)
    bolt_m = C.principled("ZincBolt", (0.70, 0.70, 0.72), metallic=1.0, rough=0.3)
    sock = C.mat_black_plastic("SocketPA", rough=0.45, color=0.022)
    lid_m = C.mat_black_plastic("LidPA", rough=0.35, color=0.03)
    loom = C.mat_black_plastic("LoomPP", rough=0.5, color=0.02, tex=False)
    objs = crossbar(pc, cap_m)
    objs += side_brackets(pc)
    objs += neck(pc, ball_m, bolt_m)
    objs += socket((sock, pc), lid_m, loom)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("gancio-traino", objs, "gancio-traino.py",
            "tow bar (generic small hatchback): black powder-coated steel crossbar with side brackets, swan neck "
            "with 50 mm tow ball and 13-pin electrical socket",
            az=-34, el=24, lens=70, fill=0.88, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
