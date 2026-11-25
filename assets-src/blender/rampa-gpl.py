"""LPG/CNG injector rail for a 4-cylinder engine: anodised aluminium common rail with
four injectors standing on it (machined aluminium bodies, black coil caps with
2-pin connector sockets and latches), brass nozzles on the front face with short
black rubber hoses and spring clips fanning out toward the camera, barbed gas inlet
with a hose stub at one end, a black temperature/pressure sensor at the other end,
and a zinc-plated mounting bracket.

1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
LX = 1.84           # rail length
HR = 0.30           # rail section (square)
XS = (-0.63, -0.21, 0.21, 0.63)


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


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


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


def axis_frame(P, d):
    d = Vector(d).normalized()
    x = d.orthogonal().normalized()
    y = d.cross(x)
    return Matrix(((x.x, y.x, d.x, P[0]), (x.y, y.y, d.y, P[1]), (x.z, y.z, d.z, P[2]), (0, 0, 0, 1)))


def barb(r, length):
    P = [(0.0, 0.0, 0), (r, 0.0, 0)]
    z = 0.03
    while z < length - 0.06:
        P += [(r, z, 0), (r * 1.22, z + 0.04, 0), (r, z + 0.045, 0)]
        z += 0.065
    P += [(r, length - 0.01, 0), (r * 0.85, length, 0), (r * 0.55, length, 1), (r * 0.55, length - 0.02, 1), (0.0, length - 0.02, 1)]
    return P


# ----------------------------------------------------------------- materials
def mat_anodised(name="RailAlu", color=(0.50, 0.51, 0.53), rough=0.32):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # extrusion lines along X + faint mottling
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.02, 1.0, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 260.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mo = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(tc.outputs["Object"], mo.inputs["Vector"])
    mo.inputs["Scale"].default_value = 3.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.12
    nt.links.new(mo.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


# ----------------------------------------------------------------- parts
def rail(alu, steel, dark):
    out = []

    def body(bm):
        prism_bm(bm, rrect(HR, HR, 0.04), -LX / 2, LX / 2, M=T((0, 0, HR / 2)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
        # injector seats
        for x in XS:
            C.cyl_bm(bm, 0.15, HR - 0.01, HR + 0.05, seg=48, matrix=T((x, 0.0, 0)))

    def holes(bm):
        for x in (-0.84, 0.84):   # through mounting holes
            C.cyl_bm(bm, 0.04, -0.2, 0.6, seg=24, matrix=T((x, 0.0, 0)))
    out.append(solid("Rail", body, [alu], bevel=0.012, cutters=[cutter("RailHoles", holes, dark)]))
    # injector retaining screws on the rail top between seats
    for x in (-0.42, 0.0, 0.42):
        hd = C.lathe("Screw", [(0.0, HR - 0.01, 0), (0.05, HR - 0.01, 0), (0.05, HR + 0.03, 0), (0.044, HR + 0.036, 0), (0.0, HR + 0.036, 0)],
                     [steel], steps=32)
        hd.matrix_world = T((x, 0.06, 0))
        bm = bmesh.new()
        C.cyl_bm(bm, 0.022, HR + 0.015, HR + 0.1, seg=6, matrix=T((x, 0.06, 0)))
        cut = C.mesh_obj("ScrewCut", bm, [steel])
        C.add_boolean(hd, cut)
        C.add_bevel(hd, 0.004, segments=1, angle=40)
        out.append(C.finalize(hd, angle=40, remove=[cut]))
    return out


def injector(x, alu2, black, tin, dark, steel):
    out = []
    M = T((x, 0.0, 0.0))
    P = [(0.0, HR + 0.04, 0), (0.125, HR + 0.04, 0), (0.13, HR + 0.06, 0), (0.13, HR + 0.20, 0), (0.115, HR + 0.22, 0), (0.0, HR + 0.22, 0)]
    out.append(lathe_at("InjBody", P, alu2, M, steps=64, bevel=0.005))
    P = [(0.0, HR + 0.21, 0), (0.142, HR + 0.21, 0), (0.148, HR + 0.23, 0), (0.148, HR + 0.47, 0), (0.135, HR + 0.50, 0), (0.0, HR + 0.50, 0)]
    out.append(lathe_at("Coil", P, black, M, steps=64, bevel=0.006))
    # 2-pin connector socket on top, opening toward -Y (camera)
    z0 = HR + 0.50

    def sock(bm):
        C.box_bm(bm, 0.19, 0.22, 0.15, center=(0.0, -0.04, z0 + 0.07))
        C.box_bm(bm, 0.07, 0.04, 0.035, center=(0.0, -0.06, z0 + 0.155))   # latch nose
        C.box_bm(bm, 0.05, 0.16, 0.02, center=(0.0, 0.0, z0 + 0.15))        # latch rib

    def cav(bm):
        C.box_bm(bm, 0.14, 0.20, 0.10, center=(0.0, -0.15, z0 + 0.07))
    out.append(solid("Socket", sock, [black], bevel=0.01, cutters=[cutter("SockCav", cav, dark)], M=M))

    def pins(bm):
        for dx in (-0.035, 0.035):
            C.box_bm(bm, 0.016, 0.12, 0.016, center=(dx, -0.07, z0 + 0.07))
    out.append(solid("Pins", pins, [tin], M=M))
    return out


def nozzles_and_hoses(brass, rubber, clip_m, dark):
    out = []
    fan = (-26, -9, 9, 26)
    for i, x in enumerate(XS):
        a = math.radians(fan[i])
        d = Vector((math.sin(a) * 0.6, -1.0, 0.0)).normalized()
        p0 = Vector((x, -HR / 2 + 0.01, 0.13))
        out.append(hex_at("NozHex", 0.055, 0.0, 0.05, brass, axis_frame(p0, (0, -1, 0)), bevel=0.005))
        Mn = axis_frame(p0 + Vector((0, -0.05, 0)), (0, -1, 0))
        out.append(lathe_at("Nozzle", barb(0.034, 0.17), brass, Mn, steps=32, mats=[brass, dark]))
        # hose: over the barb, curving down to the floor and fanning out
        h0 = p0 + Vector((0, -0.09, 0))
        L = (0.95, 1.10, 1.05, 0.90)[i]
        pts = [h0, h0 + Vector((0, -0.14, -0.01)), h0 + Vector((0, -0.30, -0.06)) + d * 0.04,
               Vector((h0.x, h0.y, 0.06)) + d * 0.55, Vector((h0.x, h0.y, 0.058)) + d * L]
        out.append(tube("Hose", pts, 0.058, rubber, res=4, caps=True))
        # dark bore on the cut hose end
        e = Vector(pts[-1])
        dd = (e - Vector(pts[-2])).normalized()
        out.append(lathe_at("HoseBore", [(0.0, -0.02, 0), (0.030, -0.02, 0), (0.030, 0.003, 0), (0.0, 0.003, 0)], dark, axis_frame(e, dd), steps=24))
        # spring clip on the hose over the nozzle
        ring = [(0.066 + 0.011 * math.cos(TAU * k / 10), 0.011 * math.sin(TAU * k / 10), 0) for k in range(10)]
        out.append(lathe_at("Clip", ring, clip_m, axis_frame(h0 + Vector((0, -0.08, -0.004)), (0, -1, -0.05)), steps=40))
    return out


def ends(alu, brass, rubber, black, dark, tin):
    out = []
    # gas inlet barb at the left end with a hose stub
    p0 = Vector((-LX / 2, 0.0, HR / 2))
    out.append(hex_at("InHex", 0.085, 0.0, 0.07, brass, axis_frame(p0, (-1, 0, 0)), bevel=0.006))
    out.append(lathe_at("InBarb", barb(0.06, 0.28), brass, axis_frame(p0 + Vector((-0.07, 0, 0)), (-1, 0, 0)), steps=40, mats=[brass, dark]))
    h0 = p0 + Vector((-0.16, 0, 0))
    pts = [h0, h0 + Vector((-0.25, 0.0, -0.02)), h0 + Vector((-0.45, -0.10, -0.08)), Vector((h0.x - 0.62, -0.30, 0.09))]
    out.append(tube("InHose", pts, 0.09, rubber, res=4))
    e = Vector(pts[-1])
    dd = (e - Vector(pts[-2])).normalized()
    out.append(lathe_at("InBore", [(0.0, -0.02, 0), (0.055, -0.02, 0), (0.055, 0.003, 0), (0.0, 0.003, 0)], dark, axis_frame(e, dd), steps=24))
    # sensor at the right end (black body with connector)
    p1 = Vector((LX / 2, 0.0, HR / 2))
    M = axis_frame(p1, (1, 0, 0))
    out.append(hex_at("SenHex", 0.09, 0.0, 0.06, brass, M, bevel=0.006))
    out.append(lathe_at("SenBody", [(0.0, 0.06, 0), (0.10, 0.06, 0), (0.11, 0.08, 0), (0.11, 0.22, 0), (0.0, 0.22, 0)], black, M, steps=48, bevel=0.008))

    def sc(bm):
        C.box_bm(bm, 0.20, 0.16, 0.16, center=(0.0, 0.0, 0.29))

    def cv(bm):
        C.box_bm(bm, 0.15, 0.11, 0.10, center=(0.0, 0.0, 0.35))
    out.append(solid("SenConn", sc, [black], bevel=0.012, cutters=[cutter("SenCav", cv, dark)], M=M))
    return out


def bracket(zinc, dark):
    def b(bm):
        C.box_bm(bm, 2.06, 0.06, 0.34, center=(0.0, HR / 2 + 0.03, 0.17))
        for x in (-0.84, 0.84):
            C.box_bm(bm, 0.22, 0.30, 0.03, center=(x, 0.02, -0.015 + 0.0))

    def holes(bm):
        for x in (-0.95, 0.95):
            C.cyl_bm(bm, 0.05, -0.2, 0.2, seg=24, matrix=T((x, HR / 2 + 0.03, 0.20)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        for x in (-0.84, 0.84):
            C.cyl_bm(bm, 0.04, -0.2, 0.2, seg=24, matrix=T((x, 0.0, 0)))
    return [solid("Bracket", b, [zinc], bevel=0.008, cutters=[cutter("BrHoles", holes, dark)], M=T((0, 0, 0.0)))]


def build():
    alu = mat_anodised()
    alu2 = mat_anodised("InjAlu", color=(0.60, 0.60, 0.62), rough=0.24)
    C.add_radial_aniso(alu2, 0.5, "Z")
    steel = C.principled("ScrewSteel", (0.32, 0.32, 0.33), metallic=1.0, rough=0.35)
    brass = C.principled("Brass", (0.78, 0.58, 0.28), metallic=1.0, rough=0.30)
    C.add_noise_bump(brass, scale=500, strength=0.05, distance=0.0005, rough_var=0.08)
    black = C.mat_black_plastic("CoilPA", rough=0.42, color=0.022)
    rubber = C.mat_rubber("Hose")
    clip_m = C.principled("SpringSteel", (0.50, 0.50, 0.52), metallic=1.0, rough=0.3)
    tin = C.principled("Tin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.2)
    zinc = C.principled("Zinc", (0.62, 0.60, 0.52), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=400, strength=0.05, distance=0.0006, rough_var=0.08)
    dark = C.principled("Bore", (0.01, 0.01, 0.01), rough=0.8)
    objs = rail(alu, steel, dark)
    for x in XS:
        objs += injector(x, alu2, black, tin, dark, steel)
    objs += nozzles_and_hoses(brass, rubber, clip_m, dark)
    objs += ends(alu, brass, rubber, black, dark, tin)
    objs += bracket(zinc, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("rampa-gpl", objs, "rampa-gpl.py",
            "LPG injector rail: aluminium common rail with four injectors with black coils and 2-pin connectors, brass "
            "nozzles with short rubber hoses, gas inlet with hose, sensor, mounting bracket",
            az=28, el=36, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
