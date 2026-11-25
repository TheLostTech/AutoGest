"""Bonnet hinge, generic small hatchback, as removed from the car: pressed-steel gooseneck
arm (U-channel whose flanges die out into flat ends) riveted to a pressed body bracket,
both painted in the catalogue's body colour like the bonnet they came off, with chipped
paint on the edges. The bracket has two slotted bolt holes, a bent lower foot with a
hole and a stiffening bead; the arm ends in a flat bonnet plate with two bolt holes.
Pivot along Y, arm in the XZ plane (car front +X, up +Z)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
RX = Matrix.Rotation(math.radians(90), 4, "X")       # cylinder Z -> -Y
T = 1.8 * MM                                          # sheet thickness


def bool_cut(ob, cut):
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def arm_path():
    ctrl = [(0.0, 0.0), (-6, 10), (-16, 32), (-14, 62), (4, 86), (34, 99), (70, 103), (110, 104), (150, 104), (176, 104)]
    pts = P.bspline([Vector((x * MM, z * MM)) for x, z in ctrl], n=220)
    pts[0] = Vector((0, 0))
    return pts


HW = 11 * MM                                          # half height of the arm web
FL = 7 * MM                                           # flange depth (towards -Y, the camera side)


def channel_section(d, h=HW, t=T):
    """Flanged web in (a = in-plane height, b = Y): web on b in [0, t], flanges along a = +-h."""
    d = max(d, t * 1.02)
    return [(h, d), (h, 0.0), (-h, 0.0), (-h, d), (-h + t, d), (-h + t, t), (h - t, t), (h - t, d)]


def arm(paint):
    pts = arm_path()
    n = len(pts)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    tot = acc[-1]
    frames = []
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = Vector((-tg.y, tg.x))
        s = acc[i]
        d = 2.6 * MM + (FL - 2.6 * MM) * C.smoothstep(12 * MM, 30 * MM, s)
        h = HW * (0.75 + 0.25 * C.smoothstep(0.0, 30 * MM, s))
        frames.append((Vector((p.x, T, p.y)), Vector((nrm.x, 0, nrm.y)), Vector((0, -1, 0)), channel_section(d, h)))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Arm", bm, [paint])
    # round pivot boss plate and the bonnet pad (the widened top flange)
    pb = bmesh.new()
    C.cyl_bm(pb, 12.5 * MM, 0.0, T, seg=48, matrix=Matrix.Rotation(math.radians(-90), 4, "X"))
    pad = pts[-1]
    C.box_bm(pb, 46 * MM, 34 * MM, T, center=(pad.x - 21 * MM, -15 * MM, pad.y + HW - T / 2))
    padob = C.mesh_obj("Pads", pb, [paint])
    m = C.add_boolean(ob, padob, op="UNION")
    m.use_self = True
    cb = bmesh.new()
    C.cyl_bm(cb, 4.2 * MM, -0.03, 0.03, seg=32, matrix=RX)        # pivot hole
    for dx in (-34, -10):
        C.cyl_bm(cb, 3.6 * MM, -0.03, 0.03, seg=32, matrix=Matrix.Translation((pad.x + dx * MM, -19 * MM, pad.y)))
    cut = C.mesh_obj("ArmHoles", cb, [paint])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0005, segments=2, angle=40)
    return C.finalize(ob, angle=45, remove=[padob, cut])


def stadium(x, z, r, hl, n=16):
    """Vertical slot outline (x, z in mm, half straight length hl) -> 2D points in m."""
    if hl <= 0:
        return [Vector(((x + r * math.cos(math.tau * k / (2 * n))) * MM, (z + r * math.sin(math.tau * k / (2 * n))) * MM))
                for k in range(2 * n)]
    pts = []
    for k in range(n + 1):
        a = math.pi * k / n
        pts.append(Vector(((x + r * math.cos(a)) * MM, (z + hl + r * math.sin(a)) * MM)))
    for k in range(n + 1):
        a = math.pi + math.pi * k / n
        pts.append(Vector(((x + r * math.cos(a)) * MM, (z - hl + r * math.sin(a)) * MM)))
    return pts


def bracket(paint):
    out = []
    y0 = -1.2 * MM                      # plate just outboard of the arm web
    poly = P.rounded([(-42, -64), (38, -64), (46, -30), (16, 12), (-10, 14), (-40, -8)],
                     [6, 6, 10, 10, 12, 10], closed=True, seg=10)
    poly = [Vector((p.x * MM, p.y * MM)) for p in poly]
    bm = bmesh.new()
    top = [bm.verts.new((p.x, y0, p.y)) for p in poly]
    bot = [bm.verts.new((p.x, y0 - T, p.y)) for p in poly]
    nn = len(poly)
    for k in range(nn):
        k2 = (k + 1) % nn
        bm.faces.new((top[k], top[k2], bot[k2], bot[k]))
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    C.fix_normals(bm)
    # bent foot along the bottom edge, pointing outboard (-Y)
    C.box_bm(bm, 80 * MM, 22 * MM, T, center=(-2 * MM, y0 - 11 * MM, -64 * MM + T / 2))
    C.box_bm(bm, 80 * MM, 4 * MM, 4 * MM, center=(-2 * MM, y0 - 1.5 * MM, -62.5 * MM))   # bend radius filler
    ob = C.mesh_obj("Bracket", bm, [paint])
    cb = bmesh.new()
    lift = lambda q, d: Vector((q.x, d, q.y))
    for (x, z, r, hl) in ((0, 0, 4.2, 0.0), (-24, -40, 3.8, 2.5), (22, -40, 3.8, 2.5)):   # pivot, slotted bolt holes
        P.prism_bm(cb, stadium(x, z, r, hl), lift, -0.05, 0.05)
    C.cyl_bm(cb, 4.0 * MM, -0.05, 0.05, seg=32, matrix=Matrix.Translation((14 * MM, y0 - 12 * MM, -64 * MM)))
    cut = C.mesh_obj("BracketHoles", cb, [paint])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    C.add_bevel(ob, 0.0005, segments=2, angle=40)
    out.append(C.finalize(ob, angle=45, remove=[cut]))
    # stiffening bead pressed into the plate
    pts = [Vector((x * MM, y0 - T + 0.0002, z * MM)) for (x, z) in
           [(-30 + 50 * k / 40, -54 + 22 * math.sin(math.pi * k / 40) * 0.2) for k in range(41)]]
    fr = P.path_frames(pts, (0, -1, 0))
    out.append(P.tube_obj("Bead", fr, [(2.6 * MM * math.cos(math.pi * k / 10), 1.1 * MM * math.sin(math.pi * k / 10)) for k in range(11)],
                          [paint], smooth_angle=60))
    return out


def pivot(zinc):
    out = []
    # shouldered rivet: head on the outboard side, peened end and washer inboard
    y0 = -1.2 * MM
    head = C.lathe("RivetHead", [(0.0, 0.0, 0), (7.5 * MM, 0.0, 0), (7.5 * MM, 1.2 * MM, 0), (6.2 * MM, 2.8 * MM, 0), (0.0, 3.4 * MM, 0)],
                   [zinc], steps=48)
    head.matrix_world = Matrix.Translation((0, y0 - T, 0)) @ RX
    out.append(C.finalize(head, angle=40))
    sh = C.lathe("RivetShank", [(0.0, 0.0, 0), (4.1 * MM, 0.0, 0), (4.1 * MM, 8 * MM, 0), (0.0, 8 * MM, 0)], [zinc], steps=32)
    sh.matrix_world = Matrix.Translation((0, y0 - T, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.finalize(sh, angle=40))
    wa = C.lathe("Washer", [(4.1 * MM, 0.0, 0), (8.5 * MM, 0.0, 0), (8.5 * MM, 1.2 * MM, 0), (4.1 * MM, 1.2 * MM, 0)], [zinc], steps=48)
    wa.matrix_world = Matrix.Translation((0, T + 0.0002, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.finalize(wa, angle=40))
    pe = C.lathe("Peen", [(0.0, 0.0, 0), (6.0 * MM, 0.0, 0), (5.0 * MM, 1.4 * MM, 0), (0.0, 2.0 * MM, 0)], [zinc], steps=48)
    pe.matrix_world = Matrix.Translation((0, T + 1.4 * MM, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.finalize(pe, angle=40))
    return out


def chipped_paint():
    """Body paint with small chips at the sheet edges showing grey primer."""
    m = P.body_paint("HingePaint")
    nt = m.node_tree
    b = P.bsdf(m)
    em = C.edge_mask(nt, 0.0006, 2.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 220.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.55
    mr.inputs["From Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = b.inputs["Base Color"].default_value[:]
    mix.inputs["B"].default_value = (0.30, 0.30, 0.29, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    cw = nt.nodes.new("ShaderNodeMapRange")
    cw.inputs["To Min"].default_value = 1.0
    cw.inputs["To Max"].default_value = 0.0
    nt.links.new(f.outputs[0], cw.inputs["Value"])
    nt.links.new(cw.outputs["Result"], b.inputs["Coat Weight"])
    return m


def build():
    paint = chipped_paint()
    zinc = C.principled("ZincRivet", (0.70, 0.70, 0.72), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=500, strength=0.06, distance=0.0002, rough_var=0.05)
    objs = [arm(paint)]
    objs += bracket(paint)
    objs += pivot(zinc)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("cerniera-cofano", objs, "cerniera-cofano.py",
            "bonnet hinge (generic small hatchback): pressed-steel gooseneck arm riveted to a body bracket, "
            "painted metallic grey, bolt holes in both",
            az=-32, el=18, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
