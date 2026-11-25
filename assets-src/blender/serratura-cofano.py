"""Bonnet latch, generic small hatchback: pressed-steel latch with a black e-coated base
plate (flanged sides, two bolting ears, flared striker slot from the top) and a
yellow-passivated front plate riveted on spacers; the rotary claw in the slot between
the plates, the separate safety catch hook with its bent finger tab and coil spring on
the front, the release lever at the bottom with the Bowden release cable (black sheath,
crimped ferrule, inner cable and nipple) curling away. Plate faces -Y, striker from +Z."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
RX = Matrix.Rotation(math.radians(90), 4, "X")      # cylinder Z -> -Y


def bool_cut(ob, cut):
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_ecoat_worn(name="EcoatSteel"):
    base = 0.03
    m = C.principled(name, (base, base, base * 1.06), metallic=0.1, rough=0.42)
    nt = m.node_tree
    b = P.bsdf(m)
    C.add_noise_bump(m, scale=380, strength=0.12, distance=0.0004, rough_var=0.06)
    em = C.edge_mask(nt, 0.0009, 2.2)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 160.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.65
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.06, 1)
    mix.inputs["B"].default_value = (0.40, 0.40, 0.41, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_yellow_zinc(name="YellowZinc"):
    m = C.principled(name, C.srgb("#C9B271"), metallic=1.0, rough=0.30)
    nt = m.node_tree
    b = P.bsdf(m)
    # iridescent-ish passivation: hue drift by large noise
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 45.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = C.srgb("#B89A5A")
    ramp.color_ramp.elements[1].color = C.srgb("#D8C894")
    e = ramp.color_ramp.elements.new(0.5)
    e.color = C.srgb("#B6A27C")
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    C.add_noise_bump(m, scale=500, strength=0.06, distance=0.0003, rough_var=0.06)
    return m


def extrude(name, poly, y0, y1, mat, holes=(), bevel=0.0005):
    """2D outline (x, z) in mm extruded between y0, y1 (mm); holes [(x, z, r)] or cutter fn."""
    bm = bmesh.new()
    a = [bm.verts.new((p[0] * MM, y0 * MM, p[1] * MM)) for p in poly]
    b = [bm.verts.new((p[0] * MM, y1 * MM, p[1] * MM)) for p in poly]
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
        for h in holes:
            if callable(h):
                h(cb)
            else:
                x, z, r = h
                C.cyl_bm(cb, r * MM, -0.05, 0.05, seg=36, matrix=Matrix.Translation((x * MM, 0, z * MM)) @ RX)
        cut = C.mesh_obj(name + "Cut", cb, [mat])
        bool_cut(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut] if cut else [])


def rnd(pts, r, seg=8):
    q = P.rounded([Vector(p) for p in pts], [r] * len(pts) if not isinstance(r, list) else r, closed=True, seg=seg)
    return [(p.x, p.y) for p in q]


def slot_cutter(top, bottom, w, flare=6):
    def f(cb):
        C.box_bm(cb, w * MM, 0.1, (top - bottom + 20) * MM, center=(0, 0, (bottom + top + 20) / 2 * MM))
        C.cyl_bm(cb, w / 2 * MM, -0.05, 0.05, seg=36, matrix=Matrix.Translation((0, 0, bottom * MM)) @ RX)
        for s in (-1, 1):   # flared mouth
            C.box_bm(cb, flare * 1.6 * MM, 0.1, flare * 1.6 * MM, center=(0, 0, 0),
                     matrix=Matrix.Translation((s * w / 2 * MM, 0, top * MM)) @ Matrix.Rotation(math.radians(45), 4, "Y"))
    return f


def base_plate(ec):
    out = []
    poly = rnd([(-62, -46), (62, -46), (62, -18), (34, -12), (30, 40), (-30, 40), (-34, -12), (-62, -18)],
               [6, 6, 6, 8, 6, 6, 8, 6])
    out.append(extrude("BasePlate", poly, 0, 2.4, ec,
                       holes=[(-50, -32, 4.4), (50, -32, 4.4), slot_cutter(40, 6, 13, 7)]))
    # flanges bent back (+Y) along both sides of the upper part
    for s in (-1, 1):
        poly = rnd([(0, -12), (16, -12), (16, 36), (0, 38)], 2)
        ob = extrude("Flange", [(p[0], p[1]) for p in poly], 0, 1, ec, bevel=0.0004)
        ob.matrix_world = Matrix.Translation(((31.2 if s > 0 else -29.2) * MM, 1.0 * MM, 0)) @ Matrix.Rotation(math.radians(90), 4, "Z")
        out.append(ob)
    # pressed stiffening rib across the lower part
    pts = [Vector(((-44 + 88 * k / 30) * MM, -1.0 * MM + 0.0002, -40 * MM)) for k in range(31)]
    fr = P.path_frames(pts, (0, -1, 0))
    out.append(P.tube_obj("Rib", fr, [(2.4 * MM * math.cos(math.pi * k / 10), 1.2 * MM * math.sin(math.pi * k / 10)) for k in range(11)],
                          [ec], smooth_angle=60))
    return out


def front_plate(zinc):
    poly = rnd([(-28, -26), (30, -26), (30, 28), (-28, 28)], [6, 6, 5, 5])
    return extrude("FrontPlate", poly, -11.5, -9.5, zinc,
                   holes=[slot_cutter(28, 6, 13, 6), (-20, -18, 2.0)])


def spacers_and_rivets(zinc):
    out = []
    for (x, z) in ((-20, -18), (22, -18), (20, 20), (-20, 20)):
        prof = [(0.0, -1.0 * MM, 0), (4.2 * MM, -1.0 * MM, 0), (3.6 * MM, 0.6 * MM, 0), (2.4 * MM, 1.0 * MM, 0), (2.4 * MM, 10 * MM, 0),
                (3.6 * MM, 10 * MM, 0), (3.6 * MM, 11.5 * MM, 0), (4.4 * MM, 12.2 * MM, 0), (3.4 * MM, 13.6 * MM, 0), (0.0, 14.0 * MM, 0)]
        r = C.lathe("Rivet", prof, [zinc], steps=32)
        r.matrix_world = Matrix.Translation((x * MM, 2.4 * MM, z * MM)) @ RX
        out.append(C.finalize(r, angle=40))
    return out


def claw(zinc, dark):
    """Rotary claw between the plates (pivot at x=16, z=8), fork mouth around the slot."""
    out = []
    pc = Vector((15, 6))
    poly = []
    N = 72
    for k in range(N):
        a = math.tau * k / N
        r = 18 if math.cos(a) > -0.2 else 15
        poly.append((pc.x + r * math.cos(a), pc.y + r * math.sin(a)))
    def fork(cb):
        C.box_bm(cb, 26 * MM, 0.1, 13.5 * MM, center=(-2 * MM, 0, 8 * MM),
                 matrix=Matrix.Translation((pc.x * MM, 0, pc.y * MM)) @ Matrix.Rotation(math.radians(-60), 4, "Y")
                 @ Matrix.Translation((-pc.x * MM, 0, -pc.y * MM)))
    ob = extrude("Claw", poly, -7.5, -3.5, zinc, holes=[fork, (pc.x, pc.y, 3.0)])
    out.append(ob)
    pin = C.lathe("ClawPin", [(0.0, 0.0, 0), (5.0 * MM, 0.0, 0), (4.4 * MM, 1.4 * MM, 0), (0.0, 1.8 * MM, 0)], [zinc], steps=32)
    pin.matrix_world = Matrix.Translation((pc.x * MM, -11.5 * MM, pc.y * MM)) @ RX
    out.append(C.finalize(pin, angle=40))
    # rubber bump stop at the bottom of the slot
    bm = bmesh.new()
    C.box_bm(bm, 11 * MM, 7 * MM, 5 * MM, center=(0, -3.0 * MM, 5.5 * MM))
    st = C.mesh_obj("Bump", bm, [dark])
    C.add_bevel(st, 0.0012, segments=2, angle=30)
    out.append(C.finalize(st, angle=35))
    return out


def safety_catch(ec, zinc):
    """Secondary hook: lever on the front plate pivoting bottom-left, hook over the slot,
    finger tab bent forward."""
    out = []
    pv = (-18, 12)
    poly = rnd([(-23, 6), (-13, 6), (-9, 34), (4, 46), (10, 44), (8, 52), (-6, 54), (-20, 40)], [3, 3, 6, 2, 1.5, 2, 6, 4], seg=6)
    out.append(extrude("Catch", poly, -15.5, -13.0, ec, holes=[(pv[0], pv[1], 2.2)]))
    # finger tab bent forward from the top edge
    tab = rnd([(-12, 0), (6, 0), (6, 13), (-12, 13)], 3)
    ob = extrude("CatchTab", tab, -1.25, 1.25, ec)
    ob.matrix_world = Matrix.Translation((0, -13.0 * MM, 52.6 * MM)) @ Matrix.Rotation(math.radians(90), 4, "X")
    out.append(ob)
    pin = C.lathe("CatchPin", [(0.0, 0.0, 0), (4.0 * MM, 0.0, 0), (3.4 * MM, 1.2 * MM, 0), (0.0, 1.6 * MM, 0)], [zinc], steps=32)
    pin.matrix_world = Matrix.Translation((pv[0] * MM, -15.5 * MM, pv[1] * MM)) @ RX
    out.append(C.finalize(pin, angle=40))
    # coil spring around the pivot
    pts = []
    for k in range(200):
        t = k / 199
        a = t * math.tau * 3.2
        pts.append(Vector(((pv[0] + 5.2 * math.cos(a)) * MM, (-12.8 + 0.0 * t) * MM - 1.8 * MM * t, (pv[1] + 5.2 * math.sin(a)) * MM)))
    pts += [pts[-1] + Vector((9 * MM, 0, 7 * MM)) * (j / 8) for j in range(1, 9)]
    fr = P.path_frames(pts, (0, -1, 0))
    out.append(P.tube_obj("Spring", fr, P.circle(0.6 * MM, 10), [zinc], smooth_angle=70))
    return out


def release(ec, zinc, sheath, steel):
    out = []
    # release lever pivoting at the lower right, cable eye at its end
    poly = rnd([(10, -30), (54, -34), (58, -26), (16, -18)], [3, 4, 4, 4])
    out.append(extrude("Lever", poly, -4.4, -2.0, zinc, holes=[(16, -24, 2.0), (52, -30, 1.8)]))
    # sheath bracket tab bent forward from the base plate ear
    tab = rnd([(60, -52), (62.4, -52), (62.4, -34), (60, -34)], 0.8)
    ob = extrude("SheathTab", tab, -14, 0, ec)
    out.append(ob)
    # cable sheath from the tab curling away to the right and down
    ctrl = [Vector(p) * MM for p in ((66, -8, -43), (84, -9, -46), (102, -16, -60), (108, -30, -82), (96, -42, -100),
                                      (72, -48, -108), (44, -46, -106), (22, -40, -100))]
    pts = P.bspline(ctrl, n=160)
    fr = P.path_frames(pts, (0, 0, 1))
    out.append(P.tube_obj("Sheath", fr, P.circle(2.7 * MM, 20), [sheath], smooth_angle=60))
    # crimped ferrule at the tab and at the far end
    for (p, d) in ((pts[0], (pts[0] - pts[4]).normalized()), (pts[-1], (pts[-1] - pts[-5]).normalized())):
        X = Vector((0, 0, 1)).cross(d).normalized()
        M = P.basis(X, d.cross(X), d, p)
        f = C.lathe("Ferrule", [(0.0, -7 * MM, 0), (3.6 * MM, -7 * MM, 0), (3.6 * MM, 2 * MM, 0), (2.6 * MM, 4 * MM, 0), (0.0, 4 * MM, 0)],
                    [steel], steps=32)
        f.matrix_world = M
        out.append(C.finalize(f, angle=40))
    # inner cable from the tab to the lever eye, with its nipple
    a = pts[0] + (pts[0] - pts[4]).normalized() * 4 * MM
    b = Vector((52 * MM, -3.2 * MM, -30 * MM))
    seg = [a.lerp(b, k / 10) for k in range(11)]
    fr = P.path_frames(seg, (0, 0, 1))
    out.append(P.tube_obj("Inner", fr, P.circle(0.75 * MM, 10), [steel], smooth_angle=70))
    nip = C.lathe("Nipple", [(0.0, 0.0, 0), (2.6 * MM, 0.0, 0), (2.6 * MM, 5 * MM, 0), (0.0, 5 * MM, 0)], [steel], steps=24)
    d = (b - a).normalized()
    X = Vector((0, 0, 1)).cross(d).normalized()
    nip.matrix_world = P.basis(X, d.cross(X), d, b - d * 1 * MM)
    C.add_bevel(nip, 0.0004, segments=2, angle=30)
    out.append(C.finalize(nip, angle=40))
    # far end: short inner cable stub and nipple
    e = pts[-1]
    d = (pts[-1] - pts[-5]).normalized()
    seg = [e + d * (4 * MM + 22 * MM * k / 10) for k in range(11)]
    out.append(P.tube_obj("InnerEnd", P.path_frames(seg, (0, 0, 1)), P.circle(0.75 * MM, 10), [steel], smooth_angle=70))
    X = Vector((0, 0, 1)).cross(d).normalized()
    n2 = C.lathe("Nipple2", [(0.0, 0.0, 0), (3.0 * MM, 0.0, 0), (3.0 * MM, 6 * MM, 0), (0.0, 6 * MM, 0)], [steel], steps=24)
    n2.matrix_world = P.basis(X, d.cross(X), d, seg[-1])
    C.add_bevel(n2, 0.0004, segments=2, angle=30)
    out.append(C.finalize(n2, angle=40))
    return out


def build():
    ec = mat_ecoat_worn()
    zinc = mat_yellow_zinc()
    dark = C.mat_rubber("BumpRubber")
    sheath = C.mat_black_plastic("SheathPE", rough=0.35, color=0.02)
    steel = C.principled("CableSteel", (0.68, 0.68, 0.70), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=500, strength=0.05, distance=0.0003, rough_var=0.05)
    objs = base_plate(ec)
    objs.append(front_plate(zinc))
    objs += spacers_and_rivets(zinc)
    objs += claw(zinc, dark)
    objs += safety_catch(ec, zinc)
    objs += release(ec, zinc, sheath, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("serratura-cofano", objs, "serratura-cofano.py",
            "bonnet latch (generic small hatchback): black pressed-steel latch plate with striker slot, yellow-zinc "
            "front plate and rotary claw, safety catch hook, release Bowden cable",
            az=22, el=18, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
