"""Air-to-air intercooler (intercooler) of a small turbo-diesel, as removed from the car:
brazed aluminium bar-and-fin core (flat charge-air tubes proud of a fine louvred fin
grid, side plates top and bottom), cast-aluminium end tanks funnelling from the core
header into round hose spigots with retention beads (inlet high on one side, outlet low
on the other), and mounting lugs with rubber bushes.

Core face in the XZ plane (front -Y). 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RX = Matrix.Rotation(math.pi / 2, 4, "X")       # local Z -> -Y
RXm = Matrix.Rotation(-math.pi / 2, 4, "X")     # local Z -> +Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # local Z -> +X
RYm = Matrix.Rotation(-math.pi / 2, 4, "Y")     # local Z -> -X


# ----------------------------------------------------------------- helpers
def box(bm, x0, x1, y0, y1, z0, z1, mat=0, M=None):
    C.box_bm(bm, x1 - x0, y1 - y0, z1 - z0, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat, matrix=M)


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None, mat=0):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=frame_to(origin, axis), r1=r1, mat=mat)


def shot(name, objs, desc, **kw):
    if FAST:
        kw.update(res=(512, 512), samples=32)
    C.shoot(name, objs, name + ".py", desc, **kw)


def circ(r, n=40, ph=0.0):
    return [(r * math.cos(math.tau * k / n + ph), r * math.sin(math.tau * k / n + ph)) for k in range(n)]


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def frame_to(P, Z):
    """Matrix placing local Z along direction Z at point P."""
    q = Vector(Z).normalized().to_track_quat("Z", "Y")
    return Matrix.Translation(P) @ q.to_matrix().to_4x4()


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), raw=False):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    if raw:
        return ob
    for c in cutters:
        C.add_boolean(ob, c).use_self = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=4, caps=True):
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


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.25
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = grime
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.78, base * 0.72, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.093, 0.08, 1)
    em = C.edge_mask(nt, 0.015, 4.0)
    wm = nt.nodes.new("ShaderNodeMath"); wm.operation = "MULTIPLY"; wm.use_clamp = True
    wm.inputs[1].default_value = wear
    nt.links.new(em, wm.inputs[0])
    mix3 = nt.nodes.new("ShaderNodeMix"); mix3.data_type = "RGBA"
    nt.links.new(wm.outputs[0], mix3.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    mix3.inputs["B"].default_value = (0.72, 0.72, 0.71, 1)
    nt.links.new(mix3.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.25
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.18
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def hot_iron(name="TurbineIron"):
    """Cast iron after heat cycles: dark grey-brown, rusty bloom, coarse sand-cast grain."""
    m = C.mat_cast_iron(name, rust=0.75, base=0.11)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # overall heat oxidation: patches of brown-red scale over the grey iron
    link = next(l for l in nt.links if l.to_node == b and l.to_socket.name == "Base Color")
    src = link.from_socket
    nt.links.remove(link)
    m2 = nt.nodes.new("ShaderNodeMapRange")
    m2.inputs["From Min"].default_value = 0.42
    m2.inputs["From Max"].default_value = 0.68
    m2.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], m2.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(m2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(src, mix.inputs["A"])
    mix.inputs["B"].default_value = (0.16, 0.075, 0.04, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["To Min"].default_value = 0.8
    mm.inputs["To Max"].default_value = 0.3
    nt.links.new(m2.outputs["Result"], mm.inputs["Value"])
    for l in [l for l in nt.links if l.to_node == b and l.to_socket.name == "Metallic"]:
        nt.links.remove(l)
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    return m


def cast(name, bm, mat, voxel=0.010, iters=4, fac=0.5):
    ob = C.mesh_obj(name, bm, [mat])
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = fac
    sm.iterations = iters
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_rusty_iron(name, base=0.10, rust=0.55, scale=5.0, seed=0.0):
    """dark cast iron with blotchy surface rust (more on edges), grainy cast bump"""
    m = C.principled(name, (base, base, base * 1.03), metallic=0.7, rough=0.6)
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
    patch.inputs["From Min"].default_value = 0.42
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
    # rust colour varies between orange-brown and dark brown
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
    met.inputs["To Min"].default_value = 0.7
    met.inputs["To Max"].default_value = 0.0
    nt.links.new(fac.outputs[0], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.55
    ro.inputs["To Max"].default_value = 0.9
    nt.links.new(fac.outputs[0], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # grainy sand-cast bump + rust scale
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 260.0
    g.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    hm = nt.nodes.new("ShaderNodeMath")
    hm.operation = "MULTIPLY_ADD"
    nt.links.new(g.outputs["Fac"], hm.inputs[0])
    hm.inputs[1].default_value = 1.0
    nt.links.new(nz2.outputs["Fac"], hm.inputs[2])
    nt.links.new(hm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def thread_prof(r_root, r_crest, z0, z1, pitch):
    P = []
    z = z0
    while z + pitch <= z1 + 1e-6:
        P += [(r_root, z, 0), (r_crest, z + pitch * 0.5, 0)]
        z += pitch
    P.append((r_root, z, 0))
    return P


def steel_body(name, color=0.50, rough=0.24):
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.6, "Z", rings_scale=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.14
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # faint grime/oxidation
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color, color, color * 1.01, 1)
    mix.inputs["B"].default_value = (color * 0.62, color * 0.58, color * 0.50, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def flat_machined(name, color=0.60, rough=0.26, axis="Z", scale=6.0):
    """Fly-cut face: anisotropic metal with faint arc marks."""
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.5, axis, rings_scale=scale, ring_strength=0.03)
    C.add_noise_bump(m, scale=300, strength=0.03, distance=0.001)
    return m
CW, CD, CH = 4.20, 0.62, 1.50
PITCH = 0.12
XT = CW / 2 + 0.02

def mat_fins(name="FinGrid", pitch=0.0075):
    """Fine fin grid seen face-on: thin bright fin edges with dark gaps in between,
    a little dust and corrosion, plus bump so the grid catches the light."""
    m = C.principled(name, (0.40, 0.40, 0.40), metallic=1.0, rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    # serpentine fins: shift x by a triangle wave of z (period = tube pitch) so the
    # folds zig-zag from tube to tube instead of forming a square grid
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    pp = nt.nodes.new("ShaderNodeMath")
    pp.operation = "PINGPONG"
    pp.inputs[1].default_value = PITCH / 2
    nt.links.new(sep.outputs["Z"], pp.inputs[0])
    amp = nt.nodes.new("ShaderNodeMath")
    amp.operation = "MULTIPLY_ADD"
    amp.inputs[1].default_value = 0.9 * pitch / (PITCH / 2)
    nt.links.new(pp.outputs[0], amp.inputs[0])
    nt.links.new(sep.outputs["X"], amp.inputs[2])
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(amp.outputs[0], cmb.inputs["X"])
    nt.links.new(sep.outputs["Y"], cmb.inputs["Y"])
    nt.links.new(sep.outputs["Z"], cmb.inputs["Z"])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.wave_profile = "SIN"
    wv.inputs["Scale"].default_value = 0.314 / pitch
    wv.inputs["Distortion"].default_value = 0.0
    nt.links.new(cmb.outputs[0], wv.inputs["Vector"])
    # louvre wobble so the fins are not perfectly straight lines
    wz = nt.nodes.new("ShaderNodeTexWave")
    wz.wave_type = "BANDS"
    wz.bands_direction = "Z"
    wz.inputs["Scale"].default_value = 0.314 / 0.0045
    nt.links.new(co, wz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.inputs["Factor"].default_value = 0.18
    nt.links.new(wv.outputs["Fac"], mx.inputs["A"])
    nt.links.new(wz.outputs["Fac"], mx.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.38
    cr.elements[0].color = (0.006, 0.006, 0.006, 1)
    cr.elements[1].position = 0.72
    cr.elements[1].color = (0.42, 0.42, 0.41, 1)
    nt.links.new(mx.outputs["Result"], ramp.inputs["Fac"])
    # dust / road grime mottling
    dn = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, dn.inputs["Vector"])
    dn.inputs["Scale"].default_value = 3.5
    dn.inputs["Detail"].default_value = 8.0
    dm = nt.nodes.new("ShaderNodeMapRange")
    dm.inputs["From Min"].default_value = 0.45
    dm.inputs["From Max"].default_value = 0.75
    dm.inputs["To Max"].default_value = 0.35
    nt.links.new(dn.outputs["Fac"], dm.inputs["Value"])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.blend_type = "MULTIPLY"
    nt.links.new(dm.outputs["Result"], dirt.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], dirt.inputs["A"])
    dirt.inputs["B"].default_value = (0.35, 0.30, 0.24, 1)
    nt.links.new(dirt.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.75
    rr.inputs["To Max"].default_value = 0.35
    nt.links.new(mx.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(mx.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_alu(name, base=0.55, rough=0.32):
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=500, strength=0.06, distance=0.0006, rough_var=0.08)
    return m


def core(fins_m, tube_m, plate_m):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, CW, CD - 0.01, CH, center=(0, 0, 0))
    out.append(C.mesh_obj("FinBlock", bm, [fins_m]))
    bm = bmesh.new()
    n = int(CH / PITCH)
    z0 = -(n - 1) * PITCH / 2
    for i in range(n):
        C.box_bm(bm, CW, CD + 0.006, 0.05, center=(0, 0, z0 + i * PITCH))
    tb = C.mesh_obj("Tubes", bm, [tube_m])
    C.add_bevel(tb, 0.008, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    for sz in (-1, 1):
        def sp(bm, sz=sz):
            box(bm, -CW / 2, CW / 2, -CD / 2 - 0.01, CD / 2 + 0.01, sz * CH / 2 - 0.03 if sz > 0 else -CH / 2 - 0.05,
                CH / 2 + 0.05 if sz > 0 else -CH / 2 + 0.03)
        out.append(solid("SidePlate", sp, [plate_m], bevel=0.01))
    return out


def loft_bm(bm, frames):
    C.sweep(bm, frames)


def tank(sx, alu, rubber, steel):
    """sx=+1 right (inlet high), -1 left (outlet low)"""
    out = []
    zs = 0.38 if sx > 0 else -0.38
    N = 16

    def circle(r, n=4 * (N + 1)):
        return [(r * math.cos(math.tau * k / n), r * math.sin(math.tau * k / n)) for k in range(n)]
    secs = [(XT - 0.02, 0.0, rrect(CD + 0.06, CH + 0.10, 0.08, N)),
            (XT + 0.10, 0.0, rrect(CD + 0.02, CH + 0.02, 0.15, N)),
            (XT + 0.30, zs * 0.45, rrect(CD - 0.04, CH * 0.62, 0.24, N)),
            (XT + 0.48, zs * 0.9, rrect(0.56, 0.62, 0.27, N)),
            (XT + 0.60, zs, circle(0.27))]
    frames = []
    for (x, zc, sec) in secs:
        xx = sx * x
        frames.append((Vector((xx, 0, zc)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    loft_bm(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj("Tank", bm, [alu])
    rm = ob.modifiers.new("Sub", "SUBSURF")
    rm.levels = 1
    rm.render_levels = 1
    out.append(C.finalize(ob, angle=40))
    # weld bead / header flange along the core
    def hdr(bm):
        prism_bm(bm, rrect(CH + 0.14, CD + 0.10, 0.08, 6), sx * XT - 0.04, sx * XT + 0.04, RY)
    out.append(solid("Header", hdr, [alu], bevel=0.015))
    # spigot with retention bead
    d = Vector((sx, 0, 0))
    M = frame_to(Vector((sx * (XT + 0.58), 0, zs)), d)
    P = [(0.22, -0.02, 0), (0.27, -0.02, 0), (0.27, 0.20, 0), (0.29, 0.23, 0), (0.29, 0.26, 0), (0.27, 0.29, 0), (0.27, 0.40, 0),
         (0.255, 0.42, 0), (0.22, 0.42, 1), (0.22, 0.0, 1)]
    out.append(lathe_at("Spigot", P, alu, M, steps=96, mats=[alu, C.principled("Inside", (0.03, 0.03, 0.03), rough=0.7)]))
    # mounting lug with rubber bush (top on the right, bottom on the left)
    zl = (CH / 2 + 0.05) * (1 if sx > 0 else -1)
    def lug(bm):
        box(bm, sx * (XT + 0.06) - 0.10, sx * (XT + 0.06) + 0.10, -0.06, 0.06, min(zl, zl * 0.7), max(zl, zl * 0.7))
        cyl_axis(bm, 0.12, (sx * (XT + 0.06), -0.06, zl), (0, 1, 0), 0.0, 0.12, seg=32)
    out.append(solid("Lug", lug, [alu], bevel=0.012))
    out.append(lathe_at("Bush", [(0.04, -0.09, 0), (0.10, -0.09, 0), (0.105, -0.07, 0), (0.10, 0.09, 0), (0.04, 0.09, 0)], rubber,
                        Matrix.Translation((sx * (XT + 0.06), 0, zl)) @ RXm, steps=40))
    out.append(lathe_at("Sleeve", [(0.0, -0.10, 0), (0.045, -0.10, 0), (0.045, 0.10, 0), (0.0, 0.10, 0)], steel,
                        Matrix.Translation((sx * (XT + 0.06), 0, zl)) @ RXm, steps=24))
    return out


def build():
    fins = mat_fins("FinGrid", pitch=0.010)
    tube = mat_alu("TubeAlu", 0.52, 0.32)
    plate = mat_alu("PlateAlu", 0.42, 0.38)
    alu = cast_alu("TankAlu", base=0.46, rough=0.46, grime=0.6, grain=180.0, wear=0.25)
    rubber = C.mat_rubber("Bush")
    steel = steel_body("Sleeve", 0.5, 0.3)
    objs = core(fins, tube, plate) + tank(1, alu, rubber, steel) + tank(-1, alu, rubber, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    shot("intercooler", objs,
         "air-to-air intercooler: aluminium bar-and-fin core, cast-aluminium end tanks with round hose spigots, rubber-bushed mounting lugs",
         az=26, el=18, lens=70, fill=0.88)
