"""Evaporative-emission charcoal canister: black moulded polypropylene cylinder standing
upright, hot-plate welded top cap with a squeezed weld flange, three barbed hose
spigots on the cap (tank vapour, purge, fresh air; one of them an elbow) with a cut-off
rubber hose and spring clip on one, moulded mounting bracket with slotted tabs and
stiffening ribs on the side, bottom foot ring.

1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
R0 = 0.56           # body radius
ZT = 1.90           # top of the body (weld line)


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
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=angle)


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


def barb(r, z0, length, hole=True):
    """Barbed spigot profile along +Z starting at z0, with a bore."""
    ri = r * 0.55
    P = [(ri, z0, 1), (r * 1.25, z0, 0), (r * 1.25, z0 + 0.05, 0), (r, z0 + 0.07, 0)]
    z = z0 + 0.10
    while z < z0 + length - 0.12:
        P += [(r, z, 0), (r * 1.22, z + 0.06, 0), (r, z + 0.065, 0)]
        z += 0.10
    P += [(r, z0 + length - 0.02, 0), (r * 0.9, z0 + length, 0), (ri, z0 + length, 1)]
    return P


# ----------------------------------------------------------------- materials
def mat_pp(name="CanisterPP", v=0.024, rough=0.50):
    """Moulded black PP: fine grain, faint flow marks, a little dust on top surfaces."""
    m = C.principled(name, (v, v, v * 1.05), rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 700.0
    nz.inputs["Detail"].default_value = 4.0
    flow = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), flow.inputs["Vector"])
    flow.inputs["Scale"].default_value = 4.0
    flow.inputs["Detail"].default_value = 3.0
    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = 0.18
    b1.inputs["Distance"].default_value = 0.0006
    nt.links.new(nz.outputs["Fac"], b1.inputs["Height"])
    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.05
    b2.inputs["Distance"].default_value = 0.004
    nt.links.new(flow.outputs["Fac"], b2.inputs["Height"])
    nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.10
    nt.links.new(flow.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    # dust on upward faces
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    du = nt.nodes.new("ShaderNodeMapRange")
    du.inputs["From Min"].default_value = 0.6
    du.inputs["From Max"].default_value = 1.0
    du.inputs["To Max"].default_value = 0.18
    nt.links.new(sep.outputs["Z"], du.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(du.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (v, v, v * 1.05, 1)
    mix.inputs["B"].default_value = (0.11, 0.10, 0.09, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def body(pp):
    out = []
    # body: foot ring, slight draft, rounded shoulders up to the weld line
    P = [(0.0, 0.0, 0), (R0 - 0.06, 0.0, 0), (R0 - 0.02, 0.02, 0), (R0 + 0.01, 0.06, 0), (R0 + 0.01, 0.13, 0), (R0 - 0.01, 0.15, 0),
         (R0, 0.20, 0), (R0 + 0.012, ZT - 0.10, 0), (R0 + 0.012, ZT - 0.02, 0), (R0 + 0.05, ZT - 0.01, 0), (R0 + 0.05, ZT, 0), (0.0, ZT, 0)]
    out.append(lathe_at("Body", P, pp, steps=128, bevel=0.006))
    # weld flash bead between body and cap
    ring = [(R0 + 0.05 + 0.012 + 0.012 * math.cos(TAU * k / 12), ZT + 0.012 * math.sin(TAU * k / 12), 0) for k in range(12)]
    out.append(lathe_at("WeldFlash", ring, pp, steps=128))
    # cap: flange, domed top with a raised plateau for the spigots
    P = [(0.0, ZT, 0), (R0 + 0.05, ZT, 0), (R0 + 0.05, ZT + 0.03, 0), (R0 + 0.01, ZT + 0.045, 0), (R0 + 0.01, ZT + 0.12, 0),
         (R0 - 0.04, ZT + 0.19, 0), (R0 - 0.16, ZT + 0.23, 0), (0.0, ZT + 0.25, 0)]
    out.append(lathe_at("Cap", P, pp, steps=128, bevel=0.006))
    return out


def bracket(pp, dark):
    """Moulded mounting bracket on the -X side: rail plate with two slotted tabs."""
    def b(bm):
        C.box_bm(bm, 0.12, 0.42, 1.30, center=(-R0 - 0.02, 0.0, 0.95))
        for z in (0.36, 1.54):
            C.box_bm(bm, 0.36, 0.56, 0.07, center=(-R0 - 0.16, 0.0, z))
            # gusset
            C.box_bm(bm, 0.22, 0.05, 0.22, center=(-R0 - 0.10, 0.0, z + (0.12 if z < 1 else -0.12)))
        for y in (-0.16, 0.16):
            C.box_bm(bm, 0.05, 0.04, 1.20, center=(-R0 - 0.09, y, 0.95))

    def slots(bm):
        for z in (0.36, 1.54):
            prism_bm(bm, rrect(0.18, 0.09, 0.044), z - 0.2, z + 0.2, M=T((-R0 - 0.22, 0.0, 0)))
    sc = cutter("Slots", slots, dark)
    return [solid("Bracket", b, [pp], bevel=0.014, cutters=[sc])]


def spigots(pp, rubber, clip_m, dark):
    out = []
    z0 = ZT + 0.20
    # tank vapour (straight, centre-front), purge (straight, smaller), fresh air (elbow, larger)
    for (x, y, r, L, name) in ((0.10, -0.24, 0.072, 0.50, "Tank"), (-0.22, 0.02, 0.060, 0.44, "Purge")):
        M = T((x, y, 0))
        out.append(lathe_at(name, barb(r, z0, L), pp, M, steps=48, mats=[pp, dark]))
        out.append(lathe_at(name + "Boss", [(0.0, z0 - 0.02, 0), (r * 1.9, z0 - 0.02, 0), (r * 1.7, z0 + 0.05, 0), (0.0, z0 + 0.05, 0)],
                            pp, M, steps=48, bevel=0.01))
    # fresh-air elbow: up then horizontal toward +X
    x, y, r = 0.22, 0.26, 0.07
    out.append(lathe_at("AirBoss", [(0.0, z0 - 0.02, 0), (r * 1.8, z0 - 0.02, 0), (r * 1.6, z0 + 0.05, 0), (0.0, z0 + 0.05, 0)],
                        pp, T((x, y, 0)), steps=48, bevel=0.01))
    out.append(tube("AirElbow", [(x, y, z0), (x, y, z0 + 0.14), (x + 0.04, y, z0 + 0.20), (x + 0.16, y, z0 + 0.22)], r, pp, res=4))
    Me = T((x + 0.15, y, z0 + 0.22)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(lathe_at("AirBarb", barb(r, 0.0, 0.36), pp, Me, steps=48, mats=[pp, dark]))
    # short cut-off rubber hose on the tank spigot with a spring clip
    M = T((0.10, -0.24, 0))
    out.append(lathe_at("Hose", [(0.062, z0 + 0.16, 0), (0.105, z0 + 0.16, 0), (0.105, z0 + 0.62, 0), (0.08, z0 + 0.64, 0), (0.062, z0 + 0.64, 0)],
                        rubber, M, steps=48, bevel=0.008))
    out.append(lathe_at("HoseBore", [(0.0, z0 + 0.60, 0), (0.063, z0 + 0.60, 0), (0.063, z0 + 0.637, 0), (0.0, z0 + 0.637, 0)], dark, M, steps=32))
    ring = [(0.112 + 0.014 * math.cos(TAU * k / 10), z0 + 0.27 + 0.014 * math.sin(TAU * k / 10), 0) for k in range(10)]
    out.append(lathe_at("Clip", ring, clip_m, M, steps=48))
    # purge line: rubber hose pushed on the purge spigot, curving away and cut off
    pz = z0 + 0.12
    out.append(tube("PurgeHose", [(-0.22, 0.02, pz), (-0.22, 0.02, pz + 0.30), (-0.30, 0.10, pz + 0.52), (-0.55, 0.30, pz + 0.60),
                                  (-0.85, 0.45, pz + 0.55)], 0.085, rubber, res=4))
    return out


def ribs(pp):
    """Vertical stiffening ribs on the visible front face plus a moulded label recess frame."""
    out = []
    bm = bmesh.new()
    for a in (-1.15, -0.95, -0.75):
        M = Matrix.Rotation(a, 4, "Z") @ T((R0 + 0.01, 0, 0))
        C.box_bm(bm, 0.06, 0.035, 1.40, center=(0, 0, 0.98), matrix=M)
    ob = C.mesh_obj("Ribs", bm, [pp])
    C.add_bevel(ob, 0.012, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    # raised arrow-free code pad (blank moulded panel)
    bm = bmesh.new()
    M = Matrix.Rotation(-0.40, 4, "Z") @ T((R0 + 0.006, 0, 0))
    C.box_bm(bm, 0.03, 0.34, 0.50, center=(0, 0, 1.20), matrix=M)
    ob = C.mesh_obj("Pad", bm, [pp])
    C.add_bevel(ob, 0.012, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    return out


def build():
    pp = mat_pp()
    rubber = C.mat_rubber("Hose")
    clip_m = C.principled("SpringSteel", (0.50, 0.50, 0.52), metallic=1.0, rough=0.3)
    dark = C.principled("Bore", (0.008, 0.008, 0.008), rough=0.8)
    objs = body(pp) + bracket(pp, dark) + spigots(pp, rubber, clip_m, dark) + ribs(pp)[:1]
    # bracket on the back-left, spigots toward the camera
    C.transform_all(objs, Matrix.Rotation(math.radians(-45), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("canister", objs, "canister.py",
            "car evaporative emission charcoal canister: black plastic cylinder with welded cap, three barbed hose spigots, "
            "mounting bracket",
            az=30, el=30, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
