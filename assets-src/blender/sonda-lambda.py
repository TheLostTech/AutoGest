"""Lambda (oxygen) sensor, heated 4-wire type: sooty slotted double tip guard, copper-tinted
crush washer, M18 thread with anti-seize, 22 mm hex, crimped stainless upper body with
a grommet, a short woven heat sleeve, then a black cable lying in a loose loop on the
floor and ending in a black 4-pin connector with latch and visible terminals.

Sensor built along local Z (tip at z=0) and laid on the ground along +X.
1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
RH = 0.127                  # hex circumradius (22 mm across flats)
ZTOP = 0.90                 # end of the grommet (cable exit)


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


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=()):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


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


def thread_prof(r_root, r_crest, z0, z1, pitch):
    P = []
    z = z0
    while z + pitch <= z1 + 1e-6:
        P += [(r_root, z, 0), (r_crest, z + pitch * 0.5, 0)]
        z += pitch
    P.append((r_root, z, 0))
    return P


def tube(name, pts, r, mat, res=4, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    cu.resolution_u = 24
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


# ----------------------------------------------------------------- materials
def sooty_tip(name):
    """Tip guard: dark soot and grey-brown deposits, lighter toward the hex."""
    m = C.principled(name, (0.10, 0.09, 0.08), metallic=0.6, rough=0.7)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 40.0
    nz.inputs["Detail"].default_value = 8.0
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 3.0       # z (0..0.16) * 3 -> 0..0.5
    nt.links.new(sep.outputs["Z"], add.inputs[0])
    nt.links.new(nz.outputs["Fac"], add.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.35
    cr.elements[0].color = (0.035, 0.032, 0.03, 1)
    cr.elements[1].position = 0.95
    cr.elements[1].color = (0.36, 0.32, 0.27, 1)
    e = cr.elements.new(0.65)
    e.color = (0.16, 0.12, 0.09, 1)
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    C.add_noise_bump(m, scale=500, strength=0.15, distance=0.0006)
    return m


def steel(name, color=0.55, rough=0.28, aniso=True):
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    if aniso:
        C.add_radial_aniso(m, 0.5, "Z")
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 18.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.14
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color, color, color * 1.01, 1)
    mix.inputs["B"].default_value = (color * 0.70, color * 0.62, color * 0.52, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_sleeve(name="FibreSleeve"):
    """Woven glass-fibre heat sleeve, dark grey."""
    m = C.principled(name, (0.09, 0.09, 0.095), rough=0.75)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(45))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 160.0
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(ck.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- sensor (local Z)
def sensor(tip, ceramic, washer, thr, hexm, body, grommet, dark):
    out = []
    # outer slotted guard (hollow, open centre hole at the tip)
    P = [(0.016, 0.0, 0), (0.050, 0.0, 0), (0.064, 0.012, 0), (0.068, 0.03, 0), (0.068, 0.165, 0), (0.058, 0.165, 0),
         (0.058, 0.03, 0), (0.048, 0.012, 0), (0.016, 0.012, 0)]
    g = C.lathe("Guard", P, [tip], steps=72)

    def slots(bm):
        for k in range(6):
            a = TAU * k / 6
            M = Matrix.Rotation(a, 4, "Z") @ T((0.066, 0, 0.095))
            C.box_bm(bm, 0.03, 0.026, 0.085, matrix=M)
        for k in range(6):  # row of small holes between the slots near the tip
            a = TAU * (k + 0.5) / 6
            C.cyl_bm(bm, 0.010, -0.03, 0.03, seg=16,
                     matrix=Matrix.Rotation(a, 4, "Z") @ T((0.066, 0, 0.045)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    cut = cutter("Slots", slots, dark)
    m = C.add_boolean(g, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(g, 0.003, segments=1, angle=35)
    out.append(C.finalize(g, angle=40, remove=[cut]))
    # inner guard + zirconia element visible through the slots
    out.append(lathe_at("Inner", [(0.0, 0.03, 0), (0.040, 0.03, 0), (0.046, 0.04, 0), (0.046, 0.17, 0), (0.0, 0.17, 0)], ceramic, steps=48))
    # crush washer
    out.append(lathe_at("Washer", [(0.090, 0.165, 0), (0.122, 0.165, 0), (0.126, 0.172, 0), (0.126, 0.188, 0), (0.122, 0.195, 0),
                                   (0.090, 0.195, 0)], washer, steps=64))
    # M18 thread
    th = [(0.0, 0.16, 0), (0.084, 0.16, 0)] + thread_prof(0.084, 0.091, 0.165, 0.33, 0.015) + [(0.086, 0.335, 0), (0.0, 0.335, 0)]
    out.append(lathe_at("Thread", th, thr, steps=72, angle=60))
    # shoulder + hex
    out.append(lathe_at("Shoulder", [(0.0, 0.195, 0), (0.104, 0.195, 0), (0.108, 0.20, 0), (0.108, 0.22, 0), (0.0, 0.22, 0)], hexm, steps=64))
    out.append(lathe_at("Shoulder2", [(0.0, 0.33, 0), (0.094, 0.33, 0), (0.094, 0.35, 0), (0.0, 0.35, 0)], hexm, steps=64))
    out.append(hex_at("Hex", RH, 0.35, 0.47, hexm, bevel=0.012))
    # crimped stainless upper body
    P = [(0.0, 0.46, 0), (0.084, 0.46, 0), (0.086, 0.49, 0), (0.080, 0.51, 0), (0.078, 0.56, 0), (0.072, 0.575, 0), (0.078, 0.59, 0),
         (0.078, 0.70, 0), (0.070, 0.715, 0), (0.076, 0.73, 0), (0.076, 0.80, 0), (0.066, 0.83, 0), (0.056, 0.84, 0), (0.0, 0.84, 0)]
    out.append(lathe_at("Upper", P, body, steps=72))
    # cable grommet
    out.append(lathe_at("Grommet", [(0.0, 0.83, 0), (0.052, 0.83, 0), (0.052, 0.86, 0), (0.044, 0.88, 0), (0.036, ZTOP, 0), (0.0, ZTOP, 0)],
                        grommet, steps=48))
    return out


def connector(black, grey, tin, dark, M):
    out = []

    def body(bm):
        prism_bm(bm, rrect(0.30, 0.20, 0.03), 0.0, 0.34)
        C.box_bm(bm, 0.12, 0.05, 0.20, center=(0.0, 0.115, 0.20))     # latch rail
        C.box_bm(bm, 0.08, 0.035, 0.05, center=(0.0, 0.135, 0.30))    # latch hook
        for sx in (-1, 1):                                            # side guide ribs
            C.box_bm(bm, 0.02, 0.21, 0.26, center=(sx * 0.155, 0.0, 0.17))
        # strain-relief neck toward the cable (-Z)
        C.cyl_bm(bm, 0.06, -0.10, 0.0, seg=32)

    def cav(bm):
        prism_bm(bm, rrect(0.24, 0.14, 0.02), 0.14, 0.40)
    hc = cutter("ConnCav", cav, dark)
    out.append(solid("Connector", body, [black], bevel=0.012, cutters=[hc]))
    # terminal tower inside with 4 sockets
    def tower(bm):
        prism_bm(bm, rrect(0.19, 0.09, 0.015), 0.13, 0.31)
    def socks(bm):
        for k in range(4):
            C.box_bm(bm, 0.022, 0.022, 0.12, center=(-0.066 + 0.044 * k, 0.0, 0.30))
    sc = cutter("Sockets", socks, dark)
    out.append(solid("Tower", tower, [grey], bevel=0.006, cutters=[sc]))
    def pins(bm):
        for k in range(4):
            C.box_bm(bm, 0.012, 0.012, 0.06, center=(-0.066 + 0.044 * k, 0.0, 0.25))
    out.append(solid("Pins", pins, [tin]))
    # rubber boot over the neck
    out.append(lathe_at("Boot", [(0.0, -0.26, 0), (0.028, -0.26, 0), (0.034, -0.22, 0), (0.044, -0.16, 0), (0.05, -0.12, 0),
                                 (0.058, -0.08, 0), (0.058, -0.06, 0), (0.0, -0.06, 0)], grey, steps=40))
    for o in out:
        o.matrix_world = M @ o.matrix_world
    return out


def build():
    tip = sooty_tip("TipSoot")
    ceramic = C.principled("Element", (0.05, 0.045, 0.04), rough=0.8)
    washer = C.principled("Washer", (0.62, 0.42, 0.30), metallic=1.0, rough=0.38)
    C.add_noise_bump(washer, scale=600, strength=0.05, distance=0.0004)
    thr = steel("AntiSeize", 0.40, 0.55, aniso=False)
    hexm = steel("HexSteel", 0.50, 0.30)
    body = steel("UpperSteel", 0.62, 0.22)
    grommet = C.mat_rubber("Grommet")
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    cable_m = C.principled("CableJacket", (0.018, 0.018, 0.02), rough=0.38)
    C.add_noise_bump(cable_m, scale=300, strength=0.05, distance=0.0006)
    black = C.mat_black_plastic("ConnPA", rough=0.45, color=0.025)
    grey = C.mat_black_plastic("ConnGrey", rough=0.55, color=0.07)
    tin = C.principled("Tin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.2)

    # sensor laid along +X, resting on the hex
    S = T((0.0, 0.0, RH)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Rotation(math.radians(30), 4, "Z")
    objs = sensor(tip, ceramic, washer, thr, hexm, body, grommet, dark)
    C.transform_all(objs, S)
    x0 = ZTOP
    # woven heat sleeve over the first part of the cable
    sleeve_pts = [(x0 - 0.02, 0, RH), (x0 + 0.20, 0, RH - 0.01), (x0 + 0.42, 0.03, RH - 0.05)]
    objs.append(tube("Sleeve", sleeve_pts, 0.036, mat_sleeve(), res=4))
    # black cable: down to the floor, loose loop behind the sensor, to the connector
    zc = 0.026
    cpts = [(x0 + 0.40, 0.03, RH - 0.05), (x0 + 0.66, 0.10, zc + 0.01), (x0 + 0.86, 0.36, zc), (x0 + 0.80, 0.70, zc),
            (x0 + 0.45, 0.86, zc), (x0 + 0.0, 0.84, zc), (x0 - 0.30, 0.80, zc + 0.01), (x0 - 0.50, 0.80, 0.05)]
    objs.append(tube("Cable", cpts, 0.026, cable_m, res=4))
    # connector: cable enters from +Y side of the floor loop, mouth facing the camera (-Y)
    end = Vector(cpts[-1])
    d = (end - Vector(cpts[-2])).normalized()
    zax = d
    xax = Vector((0, 0, 1)).cross(zax).normalized()
    yax = zax.cross(xax)
    R = Matrix(((xax.x, yax.x, zax.x, 0), (xax.y, yax.y, zax.y, 0), (xax.z, yax.z, zax.z, 0), (0, 0, 0, 1)))
    M = T(end + d * 0.26) @ R
    objs += connector(black, grey, tin, dark, M)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("sonda-lambda", objs, "sonda-lambda.py",
            "lambda (oxygen) sensor: sooty slotted tip guard, M18 thread with crush washer, steel hex, stainless body, "
            "black cable in a loose loop ending in a black 4-pin connector",
            az=26, el=44, lens=70, fill=0.88,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
