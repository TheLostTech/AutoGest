"""Rear twist-beam axle (assale posteriore / ponte torcente) of a small front-wheel-drive
car, as removed (without brakes): open inverted-U torsion beam welded between two
box-section trailing arms, front pivot eyes with rubber bushes and steel sleeves,
pressed spring seats with rubber insulators, damper clevis brackets, and bolted
stub-axle flanges with machined spindles. Worn black paint, machined parts lightly
rusted. Sections are swept along paths; holes are boolean cutters."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm. X across the car, +Y forward, Z up
ARM = [(5.85, 3.45, 0.45), (5.93, 2.3, 0.40), (6.02, 1.1, 0.31), (6.12, 0.0, 0.18), (6.22, -0.9, 0.08), (6.28, -1.30, 0.05)]
BEAM_Y, BEAM_Z = 1.10, 0.38
HUB = Vector((6.46, -1.0, 0.05))        # inner face of the stub-axle flange plate (x)


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


def mat_rusty_iron(name, base=0.10, rust=0.5, scale=4.0, seed=0.0, metal=0.7):
    m = C.principled(name, (base, base, base * 1.03), metallic=metal, rough=0.6)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (seed, seed * 1.7, seed * 0.3)
    nt.links.new(co, mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 12.0
    nz.inputs["Roughness"].default_value = 0.68
    patch = nt.nodes.new("ShaderNodeMapRange")
    patch.inputs["From Min"].default_value = 0.45
    patch.inputs["From Max"].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], patch.inputs["Value"])
    em = C.edge_mask(nt, 0.025, 4.0)
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.use_clamp = True
    add.inputs[1].default_value = 0.6
    nt.links.new(em, add.inputs[0])
    nt.links.new(patch.outputs["Result"], add.inputs[2])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.use_clamp = True
    fac.inputs[1].default_value = rust
    nt.links.new(add.outputs[0], fac.inputs[0])
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs[0], nz2.inputs["Vector"])
    nz2.inputs["Scale"].default_value = 40.0
    nz2.inputs["Detail"].default_value = 6.0
    rc = nt.nodes.new("ShaderNodeValToRGB")
    rc.color_ramp.elements[0].position = 0.35
    rc.color_ramp.elements[0].color = (0.055, 0.024, 0.012, 1)
    rc.color_ramp.elements[1].position = 0.70
    rc.color_ramp.elements[1].color = (0.17, 0.065, 0.025, 1)
    nt.links.new(nz2.outputs["Fac"], rc.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(fac.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.03, 1)
    nt.links.new(rc.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    met = nt.nodes.new("ShaderNodeMapRange")
    met.inputs["To Min"].default_value = metal
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(fac.outputs[0], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.52
    ro.inputs["To Max"].default_value = 0.9
    nt.links.new(fac.outputs[0], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 260.0
    g.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 0.002
    hm = nt.nodes.new("ShaderNodeMath")
    hm.operation = "MULTIPLY_ADD"
    nt.links.new(g.outputs["Fac"], hm.inputs[0])
    hm.inputs[1].default_value = 1.0
    nt.links.new(nz2.outputs["Fac"], hm.inputs[2])
    nt.links.new(hm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def catmull(pts, n=8):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[i + k]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def rrect(w, h, r, n=5):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def mirror_x(ob):
    ob2 = ob.copy()
    ob2.data = ob.data.copy()
    C.link(ob2)
    me = ob2.data
    me.transform(ob.matrix_world)
    ob2.matrix_world = Matrix.Identity(4)
    for v in me.vertices:
        v.co.x = -v.co.x
    me.flip_normals()
    me.update()
    return ob2


def trailing_arm(paint):
    path = catmull(ARM, 10)
    frames = []
    n = len(path)
    for i, p in enumerate(path):
        T = (path[min(n - 1, i + 1)] - path[max(0, i - 1)]).normalized()
        U = Vector((1, 0, 0))
        U = (U - T * U.dot(T)).normalized()
        V = T.cross(U).normalized()
        if V.z < 0:
            V = -V
        t = i / (n - 1)
        w = 0.50 + 0.08 * t
        h = 0.52 + 0.42 * t ** 1.5
        frames.append((p, U, V, rrect(w, h, 0.11)))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Arm", bm, [paint])
    C.add_bevel(ob, 0.02, segments=2, angle=40)
    return C.finalize(ob, angle=35)


def beam(paint):
    """inverted U, open downward, flaring into the arms"""
    bm = bmesh.new()
    frames = []
    N = 60
    for i in range(N + 1):
        x = -5.95 + 11.9 * i / N
        f = C.smoothstep(4.6, 5.9, abs(x))
        sw = 1.0 + 0.45 * f
        sh = 1.0 + 0.15 * f
        W, H, T = 0.95 * sw, 0.80 * sh, 0.055
        sec = []
        # U opening down: outer path then inner path (closed polygon in (y, z))
        m = 10
        for k in range(m + 1):          # outer arc
            a = math.pi - math.pi * k / m
            sec.append((W / 2 * math.cos(a), H * 0.25 + H * 0.35 * math.sin(a) * 1.0))
        sec.append((W / 2, -H * 0.55))
        sec.append((W / 2 - T, -H * 0.55))
        for k in range(m + 1):          # inner arc back
            a = math.pi * k / m
            sec.append(((W / 2 - T) * math.cos(a), H * 0.25 + (H * 0.35 - T) * math.sin(a)))
        sec.append((-W / 2 + T, -H * 0.55))
        sec.append((-W / 2, -H * 0.55))
        frames.append((Vector((x, BEAM_Y, BEAM_Z)), Vector((0, -1, 0)), Vector((0, 0, 1)), sec))
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Beam", bm, [paint])
    C.add_bevel(ob, 0.015, segments=2, angle=35)
    return C.finalize(ob, angle=35)


def pivot(paint, rubber, steel):
    out = []
    c = Vector(ARM[0]) + Vector((0, 0.20, 0))
    ax = Vector((1, 0.12, 0))
    P = [(0.34, -0.40, 0), (0.44, -0.40, 0), (0.44, 0.40, 0), (0.34, 0.40, 0)]
    ob = C.lathe("Eye", P, [paint], steps=72)
    ob.matrix_world = axis_mat(c, ax)
    C.add_bevel(ob, 0.02, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    P = [(0.17, -0.42, 0), (0.345, -0.42, 0), (0.345, 0.43, 0), (0.30, 0.45, 0), (0.17, 0.45, 0)]
    rb = C.lathe("Bush", P, [rubber], steps=72)
    rb.matrix_world = axis_mat(c, ax)
    cb = bmesh.new()
    for a in (0.0, math.pi):
        C.cyl_bm(cb, 0.06, 0.2, 0.6, seg=20, matrix=Matrix.Rotation(a + 1.57, 4, "Z") @ Matrix.Translation((0.255, 0, 0)))
    cut = C.mesh_obj("Voids", cb, [rubber])
    cut.matrix_world = axis_mat(c, ax)
    boolean(rb, cut)
    out.append(C.finalize(rb, angle=45, remove=[cut]))
    P = [(0.10, -0.52, 0), (0.17, -0.52, 0), (0.17, 0.55, 0), (0.10, 0.55, 0)]
    ob = C.lathe("Sleeve", P, [steel], steps=48)
    ob.matrix_world = axis_mat(c, ax)
    out.append(C.finalize(ob, angle=40))
    return out


def spring_seat(paint, rubber):
    out = []
    c = Vector((5.05, -0.15, 0.46))
    # gusset plate tying arm and beam under the pan
    bm = bmesh.new()
    C.box_bm(bm, 1.25, 1.55, 0.07, center=(5.30, 0.15, 0.40))
    C.box_bm(bm, 0.07, 1.4, 0.36, center=(4.70, 0.12, 0.24))
    g = C.mesh_obj("Gusset", bm, [paint])
    C.add_bevel(g, 0.015, segments=2, angle=30)
    out.append(C.finalize(g, angle=35))
    P = [(0.0, 0.62, 0), (0.12, 0.62, 0), (0.24, 0.52, 0), (0.30, 0.10, 0), (0.58, 0.07, 0), (0.66, 0.10, 0),
         (0.70, 0.20, 0), (0.67, 0.21, 0), (0.62, 0.12, 0), (0.30, 0.04, 0), (0.0, 0.04, 0)]
    ob = C.lathe("Pan", P, [paint], steps=128)
    ob.matrix_world = Matrix.Translation(c)
    out.append(C.finalize(ob, angle=35))
    P = [(0.32, 0.09, 0), (0.60, 0.09, 0), (0.61, 0.15, 0), (0.33, 0.15, 0)]
    ob = C.lathe("Insulator", P, [rubber], steps=128)
    ob.matrix_world = Matrix.Translation(c)
    out.append(C.finalize(ob, angle=40))
    return out


def damper_bracket(paint, steel):
    out = []
    bm = bmesh.new()
    for dx in (-0.17, 0.17):
        C.box_bm(bm, 0.06, 0.62, 0.62, center=(5.72 + dx, -1.55, 0.30))
    br = C.mesh_obj("DamperClevis", bm, [paint])
    hb = bmesh.new()
    C.cyl_bm(hb, 0.075, -0.5, 0.5, seg=28, matrix=axis_mat((5.72, -1.68, 0.44), (1, 0, 0)))
    holes = C.mesh_obj("ClevisHole", hb, [paint])
    boolean(br, holes)
    C.add_bevel(br, 0.02, segments=2, angle=30)
    out.append(C.finalize(br, angle=35, remove=[holes]))
    return out


def stub_axle(plate_m, spindle_m, bolt_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 0.12, 1.05, 1.05, center=(HUB.x + 0.06, HUB.y, HUB.z))
    pl = C.mesh_obj("FlangePlate", bm, [plate_m])
    b = pl.modifiers.new("Bevel", "BEVEL")
    b.width = 0.16
    b.segments = 6
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(30)
    hb = bmesh.new()
    for sy in (-1, 1):
        for sz in (-1, 1):
            C.cyl_bm(hb, 0.06, -1, 1, seg=24, matrix=axis_mat((HUB.x, HUB.y + 0.36 * sy, HUB.z + 0.36 * sz), (1, 0, 0)))
    holes = C.mesh_obj("PlateHoles", hb, [plate_m])
    boolean(pl, holes)
    out.append(C.finalize(pl, angle=35, remove=[holes]))
    # spindle: collar, bearing seats, thread, built along +Z then pointed outboard (+X)
    P = [(0.0, 0.10, 0), (0.30, 0.10, 0), (0.30, 0.20, 0), (0.24, 0.24, 0), (0.205, 0.26, 0), (0.205, 0.50, 0),
         (0.19, 0.52, 0), (0.17, 0.52, 0), (0.17, 0.78, 0), (0.15, 0.80, 0), (0.12, 0.80, 0)]
    z = 0.80
    for i in range(7):
        P += [(0.125, z + 0.015, 0), (0.112, z + 0.03, 0)]
        z += 0.03
    P += [(0.10, z + 0.02, 0), (0.0, z + 0.02, 0)]
    ob = C.lathe("Spindle", P, [spindle_m], steps=96)
    ob.matrix_world = axis_mat(HUB, (1, 0, 0))
    out.append(C.finalize(ob, angle=40))
    # four bolts: hex heads outboard, nuts inboard
    bm = bmesh.new()
    for sy in (-1, 1):
        for sz in (-1, 1):
            o = Vector((HUB.x, HUB.y + 0.36 * sy, HUB.z + 0.36 * sz))
            C.cyl_bm(bm, 0.11, 0.12, 0.20, seg=6, matrix=axis_mat(o, (1, 0, 0)))
            C.cyl_bm(bm, 0.055, -0.22, 0.13, seg=16, matrix=axis_mat(o, (1, 0, 0)))
            C.cyl_bm(bm, 0.11, -0.14, -0.04, seg=6, matrix=axis_mat(o, (1, 0, 0)))
    bo = C.mesh_obj("Bolts", bm, [bolt_m])
    C.add_bevel(bo, 0.012, segments=1, angle=30)
    out.append(C.finalize(bo, angle=35))
    return out


def build():
    paint = mat_worn_black("AxlePaint")
    rubber = C.mat_rubber("BushRubber")
    steel = C.principled("ZincSleeve", (0.55, 0.55, 0.53), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    spindle = mat_rusty_iron("Spindle", base=0.34, rust=0.35, scale=6.0, seed=3.0, metal=0.95)
    C.add_radial_aniso(spindle, 0.5, "Z")
    plate = mat_rusty_iron("FlangePlate", base=0.12, rust=0.5, scale=3.0, seed=1.0)
    bolt = mat_rusty_iron("Bolts", base=0.30, rust=0.45, scale=8.0, seed=7.0, metal=0.9)
    side = [trailing_arm(paint)] + pivot(paint, rubber, steel) + spring_seat(paint, rubber) + damper_bracket(paint, steel) + stub_axle(plate, spindle, bolt)
    other = [mirror_x(o) for o in side]
    objs = [beam(paint)] + side + other
    C.transform_all(objs, Matrix.Rotation(math.radians(-24), 4, "Z"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("assale-posteriore", objs, "assale-posteriore.py",
            "rear twist-beam axle: black torsion beam between two trailing arms with front rubber bushes, spring seats, damper brackets and bolted stub axles",
            az=32, el=36, lens=70, fill=0.90,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
