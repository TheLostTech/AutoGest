"""Front bumper reinforcement beam of a generic modern small hatchback, removed from the car.
Curved aluminium extrusion (double-cell 'B' profile with a shallow channel down the front
face, open ends showing the walls), mounting slots and a threaded tow-eye boss; two
aluminium crash boxes with crush beads behind it, each ending in a zinc-plated steel
bolting flange with four holes. Car front is -Y; the assembly is laid at an angle."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

XE = 0.575          # beam half length
BX = 0.445          # crash box centre x
DEPTH = 0.052       # beam depth (y)
HT = 0.114          # beam height (z)
ALU_V = 0.60        # raw aluminium base colour (0.78 + the white floor in reflections blew it out)


def yc(x):
    """Beam centre line: bowed forward in the middle, swept back at the ends."""
    return 0.048 * (x / XE) ** 2


def mat_alu(name, v=0.74, rough=0.33, streak=380.0):
    """Extruded aluminium: satin, with fine die lines along X."""
    m = C.principled(name, (v, v * 1.005, v * 1.02), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = P.bsdf(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, streak, streak)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    # coarse blotches: handling marks / oxide
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 14.0
    nz2.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.12
    nt.links.new(nz2.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def sec_outer():
    """Beam section in (a = forward, b = up)."""
    d, h = DEPTH / 2, HT / 2
    pts = [(-d, -h), (-d, h), (d, h), (d, 0.019), (d - 0.0055, 0.013), (d - 0.0055, -0.013), (d, -0.019), (d, -h)]
    r = [0.005, 0.005, 0.005, 0.002, 0.002, 0.002, 0.002, 0.005]
    return [(p.x, p.y) for p in P.rounded(pts, r, closed=True, seg=6)]


def sec_cell(sb):
    d, h = DEPTH / 2, HT / 2
    w = 0.0032
    pts = [(-d + w, 0.0022), (-d + w, h - w), (d - w, h - w), (d - w, 0.019 + 0.001), (d - 0.0055 - w, 0.0135), (d - 0.0055 - w, 0.0022)]
    r = [0.0015, 0.003, 0.003, 0.0015, 0.0015, 0.0015]
    pts = P.rounded(pts, r, closed=True, seg=4)
    out = [(p.x, sb * p.y) for p in pts]
    return out if sb > 0 else out[::-1]


def beam_frames(x0, x1, n=160):
    pts = [Vector((x0 + (x1 - x0) * k / n, yc(x0 + (x1 - x0) * k / n), 0.0)) for k in range(n + 1)]
    return P.path_frames(pts, (0, 0, 1))


def beam(alu, dark):
    bm = bmesh.new()
    P.tube_bm(bm, beam_frames(-XE, XE), sec_outer())
    C.fix_normals(bm)
    ob = C.mesh_obj("Beam", bm, [alu, dark])
    cutters = []
    for sb in (1, -1):
        cb = bmesh.new()
        P.tube_bm(cb, beam_frames(-XE - 0.03, XE + 0.03), sec_cell(sb))
        C.fix_normals(cb)
        cutters.append(C.mesh_obj("Cell", cb, [alu]))
    # mounting slots through the front wall, tow-eye hole
    cb = bmesh.new()
    for x in (-0.33, -0.16, 0.16, 0.33):
        for zz in (0.036, -0.036):
            y = yc(x) - DEPTH / 2
            M = Matrix.Translation((x, y, zz)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Diagonal((1.0, 0.5, 1.0, 1.0))
            C.cyl_bm(cb, 0.0085, -0.012, 0.012, seg=24, matrix=M)
    cutters.append(C.mesh_obj("Slots", cb, [alu]))
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.solver = "MANIFOLD"
    C.add_bevel(ob, 0.0012, segments=2, angle=40)
    return C.finalize(ob, angle=40, remove=cutters)


def crash_box(sx, alu):
    """Rectangular aluminium tube behind the beam with three crush beads."""
    x = sx * BX
    y0 = yc(x) + DEPTH / 2 - 0.004
    L = 0.165
    hw, hh = 0.040, 0.050
    base = P.rrect(-hw, hw, -hh, hh, 0.008, seg=5)
    bm = bmesh.new()
    n = 90
    rings = []
    beads = (0.045, 0.085, 0.125)
    for k in range(n + 1):
        t = L * k / n
        s = 1.0
        for b in beads:
            s -= 0.06 * P.bump(((t - b) / 0.012) ** 2)
        rings.append([bm.verts.new((x + a * s, y0 + t, c * s)) for (a, c) in base])
    m = len(base)
    for i in range(n):
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    C.fix_normals(bm)
    ob = C.mesh_obj("CrashBox", bm, [alu])
    return C.finalize(ob, angle=50), y0 + L


def flange(sx, y, zinc, dark):
    x = sx * BX + sx * 0.012
    bm = bmesh.new()
    C.box_bm(bm, 0.130, 0.008, 0.150, center=(x, y + 0.004, 0.0))
    ob = C.mesh_obj("Flange", bm, [zinc])
    cb = bmesh.new()
    for dx in (-0.048, 0.048):
        for dz in (-0.058, 0.058):
            C.cyl_bm(cb, 0.0058, -0.02, 0.02, seg=28,
                     matrix=Matrix.Translation((x + dx, y + 0.004, dz)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    cut = C.mesh_obj("FlangeHoles", cb, [zinc])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    C.add_bevel(ob, 0.0016, segments=2, angle=30)
    out = [C.finalize(ob, angle=35, remove=[cut])]
    # weld bead where the box meets the flange
    hw, hh = 0.040, 0.050
    loop = P.rounded([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)], [0.008] * 4, closed=True, seg=6)
    loop = P.resample(loop, 120, closed=True)
    pts = [Vector((sx * BX + p.x * 1.03, y - 0.002, p.y * 1.03)) for p in loop]
    fr = P.path_frames(pts, (0, 1, 0), closed=True)
    out.append(P.tube_obj("Weld", fr, P.circle(0.0028, 8), [dark], closed=True, smooth_angle=70))
    return out


def tow_boss(alu, dark):
    x = BX
    y = yc(x) - DEPTH / 2
    prof = [(0.0085, 0.0, 1), (0.0155, 0.0, 0), (0.0155, 0.012, 0), (0.0135, 0.0155, 0), (0.0085, 0.0155, 1),
            (0.0085, 0.004, 1)]
    ob = C.lathe("TowBoss", prof, [alu, dark], steps=48)
    ob.matrix_world = Matrix.Translation((x, y + 0.004, 0.0)) @ Matrix.Rotation(math.radians(90), 4, "X")
    C.add_bevel(ob, 0.0008, segments=2, angle=30)
    out = [C.finalize(ob, angle=40)]
    # thread inside
    bm = bmesh.new()
    n = 400
    turns = 7
    pts = []
    for k in range(n + 1):
        a = math.tau * turns * k / n
        pts.append(Vector((x + 0.0083 * math.cos(a), y + 0.004 - 0.0005 - 0.014 * k / n, 0.0083 * math.sin(a))))
    fr = P.path_frames(pts, lambda p: Vector((p.x - x, 0, p.z)))
    P.tube_bm(bm, fr, [(-0.0008, 0.0), (0.0008, 0.0), (0.0, -0.0009)])
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("Thread", bm, [alu]), angle=60))
    return out


def glossy_dome(center, radius, K, stops, name="Dome"):
    """Big sphere seen only by glossy rays (replaces the plain studio world in the
    reflections): emission brightness ramps with the direction from the centre against
    K, so differently oriented flats of a polished part reflect different greys."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=radius)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(nrm.outputs[0], dot.inputs[0])
    dot.inputs[1].default_value = tuple(Vector(K).normalized())
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (stops[0][1],) * 3 + (1,)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (stops[-1][1],) * 3 + (1,)
    for pos, val in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (val, val, val, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob = C.mesh_obj(name, bm, [m])
    ob.location = center
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    return ob


def hide_floor_from_glossy():
    """The white shadow catcher reflected in the satin metal washed it out to white:
    hide it from glossy rays only (the contact shadow stays)."""
    orig = C._area

    def _area(name, *a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        ob = orig(name, *a, **k)
        if name == "Rim":       # mirrored flat across the whole top face
            ob.visible_glossy = False
        return ob
    C._area = _area


def build():
    alu = mat_alu("Extrusion", v=ALU_V, rough=0.36)
    alu2 = mat_alu("CrashBoxAlu", v=ALU_V * 0.94, rough=0.40, streak=300.0)
    dark = C.principled("Bore", (0.08, 0.08, 0.085), metallic=1.0, rough=0.5)
    zinc = C.principled("ZincFlange", (0.50, 0.51, 0.52), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=60, strength=0.05, distance=0.0005, rough_var=0.1)
    weld = C.principled("WeldBead", (0.42, 0.40, 0.38), metallic=1.0, rough=0.55)
    C.add_noise_bump(weld, scale=900, strength=0.6, distance=0.0006)
    objs = [beam(alu, dark)]
    for sx in (-1, 1):
        box, yend = crash_box(sx, alu2)
        objs.append(box)
        objs += flange(sx, yend, zinc, weld)
    objs += tow_boss(alu, dark)
    C.transform_all(objs, Matrix.Rotation(math.radians(12), 4, "Z"))
    return objs


if __name__ == "__main__":
    hide_floor_from_glossy()
    C.clear()
    objs = build()
    # faces turned down/forward reflect the black lower studio world: a glossy-only dome
    # gives them a soft grey instead, brightening towards the top
    glossy_dome(Vector((0, 0, 0)), 8.0, (-0.25, -0.35, 0.90), [(0.0, 0.10), (0.4, 0.22), (0.7, 0.50), (1.0, 0.80)])
    r = int(os.environ.get("RES", "1024"))
    C.shoot("traversa-paraurti", objs, "traversa-paraurti.py",
            "front bumper reinforcement beam (generic small hatchback): curved double-cell aluminium extrusion with "
            "mounting slots and tow-eye boss, two aluminium crash boxes with crush beads and steel bolting flanges",
            az=-30, el=30, lens=70, fill=0.92, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
