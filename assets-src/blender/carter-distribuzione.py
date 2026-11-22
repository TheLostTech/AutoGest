"""Timing belt cover set: two black moulded polypropylene covers (upper over the twin cam
pulleys, lower over tensioner, water pump and crank sprocket) assembled with an
overlapping joint, stiffening rings and ribs on the faces, perimeter bolt lugs with
pressed steel sleeves, a hex flange bolt left in one lug, and spring-steel clips
holding the two halves together at the joint.

Cover face in the X-Z plane (front toward -Y), stood up and turned to the camera.
1 unit = 100 mm (about 460 mm tall)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RX = Matrix.Rotation(math.pi / 2, 4, "X")     # local Z -> -Y
RXn = Matrix.Rotation(-math.pi / 2, 4, "X")   # local Z -> +Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")     # local Z -> +X


# ----------------------------------------------------------------- helpers
def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circ(r, n=40, cx=0.0, cy=0.0, ph=0.0):
    return [(cx + r * math.cos(math.tau * k / n + ph), cy + r * math.sin(math.tau * k / n + ph)) for k in range(n)]


def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def resample(poly, n):
    L = [0.0]
    P = list(poly) + [poly[0]]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + math.dist(a, b))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


def frame_to(P, Z):
    """Matrix placing local origin at P with local +Z along Z."""
    d = Vector(Z).normalized()
    return Matrix.Translation(Vector(P)) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def boolean(ob, cutter, op="DIFFERENCE"):
    m = C.add_boolean(ob, cutter, op)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), bev_angle=30):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        boolean(ob, c)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=bev_angle)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter(name, fill, mat=None):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat] if mat else [])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None, mod=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps, mod=mod)
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


def smooth_path(ctrl, n=12):
    """Catmull-Rom through control points (open)."""
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def resample_path(path, step):
    P = [Vector(p) for p in path]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(L[-1] / step) + 1)
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(P) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append(P[j].lerp(P[j + 1], min(1.0, max(0.0, t))))
    return out, L[-1]


def path_frames(path, up=(0, 0, 1)):
    """Parallel-transport frames [(P, U, V, T)] along a polyline."""
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    upv = Vector(up)
    if abs(T[0].dot(upv)) > 0.95:
        upv = Vector((1, 0, 0))
    U = (upv - T[0] * upv.dot(T[0])).normalized()
    out = []
    for i, t in enumerate(T):
        U = (U - t * U.dot(t)).normalized()
        out.append((P[i], U, t.cross(U), t))
    return out


def hose_bm(bm, path, r_out, r_in=None, n=40, mat=0, mat_in=None, sx=1.0, sy=1.0, up=(0, 0, 1)):
    """Tube along path; r_out(s) / r_in(s) take arc fraction s in 0..1.
    With r_in the tube is hollow with annular end faces; otherwise capped."""
    fr = path_frames(path, up)
    m = len(fr)
    def ring(k, rf, inner=False):
        s = k / (m - 1)
        r = rf(s)
        P, U, V, _ = fr[k]
        return [bm.verts.new(P + U * (r * sx * math.cos(math.tau * j / n)) + V * (r * sy * math.sin(math.tau * j / n)))
                for j in range(n)]
    O = [ring(k, r_out) for k in range(m)]
    faces = []
    def skin(R, flip=False):
        for i in range(len(R) - 1):
            a, b = R[i], R[i + 1]
            for j in range(n):
                j2 = (j + 1) % n
                q = (a[j], a[j2], b[j2], b[j])
                f = bm.faces.new(q[::-1] if flip else q)
                faces.append(f)
    skin(O)
    if r_in is None:
        faces.append(bm.faces.new(O[0][::-1]))
        faces.append(bm.faces.new(O[-1]))
        for f in faces:
            f.material_index = mat
        return faces
    I = [ring(k, r_in) for k in range(m)]
    skin(I, flip=True)
    for f in faces:
        f.material_index = mat
    endf = []
    for A, B, fl in ((O[0], I[0], True), (O[-1], I[-1], False)):
        for j in range(n):
            j2 = (j + 1) % n
            q = (A[j], A[j2], B[j2], B[j])
            f = bm.faces.new(q[::-1] if fl else q)
            f.material_index = mat if mat_in is None else mat_in
            endf.append(f)
    return faces + endf


def tube(name, pts, r, mat, res=4, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


# ----------------------------------------------------------------- materials
def _b(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def nylon(name, color=0.05, rough=0.55, grain=260.0, dust=1.45):
    """Glass-filled nylon / PP: fine speckled texture, slightly satin, dust in creases."""
    m = C.principled(name, (color, color, color * 1.04), rough=rough)
    nt = m.node_tree
    b = _b(m)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = grain
    nz.inputs["Detail"].default_value = 3.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.08
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.06
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color * dust, color * dust * 0.97, color * dust * 0.9, 1)
    mix.inputs["B"].default_value = (color, color, color * 1.04, 1)
    nt.links.new(ao.outputs["AO"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = _b(m)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.15
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
    em = C.edge_mask(nt, 0.012, 4.0)
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
    bp.inputs["Strength"].default_value = 0.30
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def zinc(name="Zinc", c=0.60, rough=0.28):
    m = C.principled(name, (c, c, c * 1.03), metallic=1.0, rough=rough)
    C.add_noise_bump(m, scale=600, strength=0.03, distance=0.0005, rough_var=0.06)
    return m


def rubber(name="Rubber", c=0.026, rough=0.72, scale=400.0):
    m = C.principled(name, (c, c, c), rough=rough)
    C.add_noise_bump(m, scale=scale, strength=0.08, distance=0.001, rough_var=0.06)
    return m


def dark_cavity(name="Cavity"):
    return C.principled(name, (0.008, 0.008, 0.008), rough=0.85)


def shoot(name, objs, desc, **kw):
    if FAST:
        kw.update(res=(512, 512), samples=32)
    C.shoot(name, objs, name + ".py", desc, **kw)

YD = 0.42     # cover depth (front face at y=0, back at y=YD)
CAMS = [(-0.55, 3.30, 0.66), (0.80, 3.30, 0.66)]
SPLIT = 2.30


def xz_prism(bm, sec, y0, y1):
    """Prism from an outline in (x, z), extruded along +Y from y0 to y1."""
    M = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    return prism_bm(bm, sec, y0, y1, M)


def ycyl(bm, r, x, z, y0, y1, seg=40):
    C.cyl_bm(bm, r, y0, y1, seg=seg, matrix=Matrix.Translation((x, 0, z)) @ RXn)


def upper_outline():
    pts = []
    for x, z, r in CAMS:
        pts += circ(r + 0.12, 64, x, z)
    pts += [(-1.05, SPLIT - 0.12), (1.35, SPLIT - 0.12)]
    return resample(hull2d(pts), 220)


def lower_outline():
    pts = circ(0.78, 64, 0.15, 0.25) + circ(0.52, 48, 0.75, 1.30) + circ(0.45, 48, -0.55, 1.75)
    pts += [(-1.0, SPLIT + 0.10), (1.30, SPLIT + 0.10)]
    return resample(hull2d(pts), 220)


def cover(name, sec, pp, dark, yoff, rings, lugs, ribs):
    out = []
    def cuts(bm):
        for x, z in lugs:
            ycyl(bm, 0.055, x, z, -1.0, 1.0, seg=28)
    hc = cutter(name + "Holes", cuts, dark)
    def lugs_f(bm):
        xz_prism(bm, sec, yoff, YD)
        for x, z in lugs:
            ycyl(bm, 0.14, x, z, yoff - 0.04, YD - 0.10, seg=40)
    out.append(solid(name, lugs_f, [pp], bevel=0.05, seg=4, cutters=[hc], bev_angle=25))
    # raised rings + radial ribs on the face
    def deco(bm):
        for x, z, r in rings:
            ycyl(bm, r, x, z, yoff - 0.05, yoff + 0.02, seg=96)
        for (x0, z0, x1, z1) in ribs:
            L = math.hypot(x1 - x0, z1 - z0)
            a = math.atan2(z1 - z0, x1 - x0)
            M = Matrix.Translation(((x0 + x1) / 2, yoff - 0.015, (z0 + z1) / 2)) @ Matrix.Rotation(-a, 4, "Y")
            C.box_bm(bm, L, 0.05, 0.045, matrix=M)
    def deco_cut(bm):
        for x, z, r in rings:
            ycyl(bm, r - 0.07, x, z, yoff - 0.2, yoff - 0.025, seg=96)
    dc = cutter(name + "RingCut", deco_cut, dark)
    out.append(solid(name + "Ribs", deco, [pp], bevel=0.012, seg=2, cutters=[dc]))
    return out


def sleeves(steel, lugs, yoff):
    out = []
    for x, z in lugs:
        M = Matrix.Translation((x, 0, z)) @ RXn
        out.append(lathe_at("Sleeve", [(0.04, yoff - 0.065, 0), (0.08, yoff - 0.065, 0), (0.08, yoff - 0.045, 0),
                                       (0.056, yoff - 0.045, 0), (0.056, YD - 0.1, 0), (0.04, YD - 0.1, 0)], steel, M, steps=32))
    return out


def build():
    pp = nylon("CoverPP", color=0.03, rough=0.58, grain=650.0, dust=1.7)
    dark = dark_cavity()
    steel = zinc("SleeveZinc", c=0.6, rough=0.28)
    clip_m = C.principled("ClipSteel", (0.12, 0.12, 0.13), metallic=1.0, rough=0.35)
    C.add_noise_bump(clip_m, scale=400, strength=0.04, distance=0.0005)
    objs = []
    up_lugs = [(-1.33, 3.10), (1.62, 3.15), (0.12, 4.05), (-1.08, 2.42), (1.40, 2.42)]
    lo_lugs = [(-1.10, 1.55), (1.18, 1.00), (-0.62, 0.0), (0.90, -0.10), (-1.0, 2.15)]
    rings_u = [(x, z, r - 0.06) for x, z, r in CAMS]
    ribs_u = []
    for x, z, r in CAMS:
        for k in range(6):
            a = math.tau * k / 6 + 0.3
            ribs_u.append((x + 0.12 * math.cos(a), z + 0.12 * math.sin(a), x + (r - 0.12) * math.cos(a), z + (r - 0.12) * math.sin(a)))
    ribs_u += [(-1.0, 2.55, 1.3, 2.55), (0.12, 2.6, 0.12, 3.9)]
    rings_l = [(0.15, 0.25, 0.62), (0.75, 1.30, 0.38)]
    ribs_l = [(-0.70, 0.75, -0.62, 2.10), (0.15, 0.95, 0.15, 2.15), (-0.9, 2.05, 1.2, 2.05), (0.70, 0.65, 1.15, 0.45),
              (-0.5, 0.9, 0.5, 1.6)]
    objs += cover("Upper", upper_outline(), pp, dark, -0.05, rings_u, up_lugs, ribs_u)
    objs += cover("Lower", lower_outline(), pp, dark, 0.0, rings_l, lo_lugs, ribs_l)
    objs += sleeves(steel, up_lugs, -0.05) + sleeves(steel, lo_lugs, 0.0)
    # flange bolt left in one lug
    Mb = Matrix.Translation((1.18, -0.065, 1.00)) @ RX
    objs.append(lathe_at("BoltFlange", [(0.0, 0.0, 0), (0.11, 0.0, 0), (0.11, 0.02, 0), (0.0, 0.02, 0)], steel, Mb, steps=40))
    objs.append(hex_at("BoltHex", 0.075, 0.02, 0.10, steel, Mb))
    # spring clips across the joint on both sides
    for x, side in ((-1.03, -1), (1.36, 1)):
        def clip(bm, x=x, side=side):
            C.box_bm(bm, 0.12, 0.025, 0.36, center=(x - side * 0.02, -0.075, SPLIT))
            C.box_bm(bm, 0.03, YD * 0.7, 0.36, center=(x + side * 0.05, YD * 0.30, SPLIT))
            C.box_bm(bm, 0.10, 0.03, 0.05, center=(x - side * 0.03, -0.10, SPLIT + 0.12))
        objs.append(solid("Clip", clip, [clip_m], bevel=0.008))
    R = Matrix.Rotation(math.radians(24), 4, "Z") @ Matrix.Rotation(math.radians(-8), 4, "X")
    C.transform_all(objs, R)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("carter-distribuzione", objs, "carter-distribuzione.py",
            "timing belt cover: black moulded plastic upper and lower covers with ribs, bolt lugs with steel sleeves and joint clips",
            az=30, el=16, lens=70, fill=0.84, **kw)
