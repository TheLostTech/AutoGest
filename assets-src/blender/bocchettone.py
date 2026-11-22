"""Fuel filler neck: zinc-plated steel filler pipe with two bends, filler head cup with a
three-hole mounting plate and a black screw cap (grip bar, knurled rim, tether strap),
a small breather line running alongside held by two clips and joined into the head,
and the lower end with a hose bead, a short black rubber hose and a band clamp.

Laid flat on the ground. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
RP = 0.17           # neck pipe radius (34 mm)
RV = 0.045          # breather line radius
RH = 0.31           # head cup radius
ZG = 0.42           # height of the pipe axis above the floor


# ----------------------------------------------------------------- helpers
def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


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
    P = poly + [poly[0]]
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


def loft(name, frames, mat, cap=True):
    bm = bmesh.new()
    C.sweep(bm, frames, cap=cap)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def frame_matrix(P, X, Z):
    X, Z = X.normalized(), Z.normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P.x), (X.y, Y.y, Z.y, P.y), (X.z, Y.z, Z.z, P.z), (0, 0, 0, 1)))


def path_pts(start, d, n, segs, step=0.03):
    """Planar centre-line: segs = [('L', len) | ('A', radius, deg)]; +deg bends toward n, -deg away."""
    P = Vector(start)
    d = Vector(d).normalized()
    n = Vector(n).normalized()
    b = d.cross(n).normalized()
    pts = [(P.copy(), d.copy())]
    for s in segs:
        if s[0] == "L":
            k = max(1, int(s[1] / step))
            for i in range(1, k + 1):
                pts.append((P + d * (s[1] * i / k), d.copy()))
            P = P + d * s[1]
        else:
            R, ang = s[1], math.radians(s[2])
            nn = n if ang >= 0 else -n
            bb = d.cross(nn).normalized()
            ang = abs(ang)
            Cc = P + nn * R
            k = max(2, int(R * ang / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, bb)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, bb)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts, b


def pipe(name, pts, b, r, mat, wall=0.012):
    sec = circle_pts(0, 0, r, 48)
    fr = [(P, b, t.cross(b), sec) for (P, t) in pts]
    ob = loft(name, fr, mat, cap=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def lathe_at(name, prof, mats, M=I4, steps=64, angle=40, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
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


# ----------------------------------------------------------------- materials
def mat_zinc(name="ZincSteel", base=0.50, rough=0.52):
    """Zinc-plated (yellow-passivated, aged) steel: matte silver with faint gold/iridescent
    mottling, a little white corrosion bloom and fine grain."""
    m = C.principled(name, (base, base, base * 0.98), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.30
    cr.elements[0].color = (base * 0.95, base * 0.93, base * 0.86, 1)
    cr.elements[1].position = 0.75
    cr.elements[1].color = (base * 1.05, base * 0.96, base * 0.74, 1)
    e = cr.elements.new(0.52)
    e.color = (base, base, base * 1.0, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    # white zinc bloom spots
    sp = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), sp.inputs["Vector"])
    sp.inputs["Scale"].default_value = 14.0
    sp.inputs["Detail"].default_value = 8.0
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.66
    th.inputs["From Max"].default_value = 0.76
    th.inputs["To Max"].default_value = 0.6
    nt.links.new(sp.outputs["Fac"], th.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = (0.70, 0.70, 0.68, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 0.45
    nt.links.new(th.outputs["Result"], mr.inputs["Value"])
    ad = nt.nodes.new("ShaderNodeMath")
    ad.operation = "ADD"
    ad.inputs[1].default_value = rough
    nt.links.new(mr.outputs["Result"], ad.inputs[0])
    nt.links.new(ad.outputs[0], b.inputs["Roughness"])
    C.add_noise_bump(m, scale=380, strength=0.06, distance=0.001)
    return m


# ----------------------------------------------------------------- parts
def head(zinc, black, rubber, dark, M):
    """Filler head along local +Z (z=0 joins the pipe)."""
    out = []
    P = [(RP - 0.012, -0.02, 0), (RP, -0.02, 0), (RP + 0.005, 0.06, 0), (RH - 0.03, 0.16, 0), (RH, 0.20, 0), (RH, 0.52, 0),
         (RH + 0.022, 0.535, 0), (RH + 0.022, 0.56, 0), (RH - 0.012, 0.56, 0), (RH - 0.012, 0.20, 0), (RP - 0.012, 0.06, 0)]
    out.append(lathe_at("HeadCup", P, [zinc], M, steps=96, bevel=0.004))
    # three-hole mounting plate around the cup
    poly = resample(hull2d(circle_pts(0, 0, RH + 0.10, 64) + sum((circle_pts(0.52 * math.cos(a), 0.52 * math.sin(a), 0.10, 24)
                                                                  for a in (math.radians(30), math.radians(150), math.radians(270))), [])), 160)
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (0.34, 0.365)]
    pl = loft("Plate", fr, zinc)
    pl.matrix_world = M
    cb = bmesh.new()
    C.cyl_bm(cb, RH - 0.004, 0.0, 0.8, seg=64)
    for a in (30, 150, 270):
        a = math.radians(a)
        C.cyl_bm(cb, 0.04, 0.0, 0.8, seg=24, matrix=T((0.52 * math.cos(a), 0.52 * math.sin(a), 0)))
    cut = C.mesh_obj("PlateCut", cb, [zinc])
    cut.matrix_world = M
    m = C.add_boolean(pl, cut)
    m.use_self = True
    C.add_bevel(pl, 0.006, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35, remove=[cut]))
    # rubber splash seal under the plate
    out.append(lathe_at("Seal", [(RH, 0.30, 0), (RH + 0.13, 0.30, 0), (RH + 0.15, 0.32, 0), (RH + 0.15, 0.34, 0), (RH, 0.34, 0)],
                        [rubber], M, steps=96, bevel=0.006))

    # black screw cap: knurled rim, flat face, grip bar
    def knurl(r, z, t):
        if r > RH + 0.02 and 0.58 < z < 0.66:
            return r + 0.010 * (0.5 + 0.5 * math.cos(36 * t))
        return r
    P = [(0.0, 0.54, 0), (RH + 0.03, 0.54, 0), (RH + 0.04, 0.575, 0), (RH + 0.04, 0.665, 0), (RH + 0.02, 0.69, 0), (0.0, 0.69, 0)]
    out.append(lathe_at("Cap", P, [black], M, steps=144, bevel=0.006, mod=knurl))
    bm = bmesh.new()
    C.box_bm(bm, 0.50, 0.09, 0.16, center=(0, 0, 0.75))
    C.box_bm(bm, 0.06, 0.06, 0.03, center=(0.19, 0.18, 0.70))     # tether lug
    gb = C.mesh_obj("Grip", bm, [black])
    gb.matrix_world = M
    C.add_bevel(gb, 0.03, segments=3, angle=30)
    out.append(C.finalize(gb, angle=35))
    # tether strap from the cap lug down to a ring around the cup neck
    pts = [M @ Vector(p) for p in ((0.19, 0.20, 0.70), (0.30, 0.30, 0.60), (0.40, 0.34, 0.40), (0.36, 0.30, 0.22), (0.28, 0.20, 0.14))]
    out.append(tube("Tether", pts, 0.016, black, res=2))
    out.append(lathe_at("TetherRing", [(RP + 0.002, 0.08, 0), (RP + 0.028, 0.08, 0), (RP + 0.028, 0.12, 0), (RP + 0.002, 0.12, 0)],
                        [black], M, steps=64, bevel=0.005))
    return out


def build():
    zinc = mat_zinc()
    zinc2 = mat_zinc("ZincLine", base=0.54, rough=0.42)
    black = C.mat_black_plastic("CapPA", rough=0.48, color=0.022)
    rubber = C.mat_rubber("HoseRubber")
    dark = C.principled("Inside", (0.01, 0.01, 0.01), rough=0.8)
    objs = []
    # neck centre-line, lying flat: starts at the head, runs back-left with two bends
    pts, b = path_pts((0.0, 0.0, ZG), (-0.90, 0.44, 0.0), (0.44, 0.90, 0.0),
                      [("L", 0.55), ("A", 1.1, 38), ("L", 1.0), ("A", 1.6, -48), ("L", 1.5)])
    objs.append(pipe("Neck", pts, b, RP, zinc))
    P0, t0 = pts[0]
    Mh = frame_matrix(P0, b, -t0)
    objs += head(zinc, black, rubber, dark, Mh)
    # lower end: hose bead, rubber hose, band clamp
    P1, t1 = pts[-1]
    M1 = frame_matrix(P1, b, t1)
    objs.append(lathe_at("Bead", [(RP - 0.01, -0.30, 0), (RP + 0.02, -0.29, 0), (RP + 0.02, -0.27, 0), (RP - 0.01, -0.26, 0)], [zinc], M1, steps=64))
    objs.append(lathe_at("Hose", [(RP + 0.005, -0.42, 0), (RP + 0.05, -0.42, 0), (RP + 0.06, -0.40, 0), (RP + 0.06, 0.38, 0),
                                  (RP + 0.05, 0.40, 0), (RP + 0.005, 0.40, 0)], [rubber], M1, steps=64, bevel=0.006))
    objs.append(lathe_at("Clamp", [(RP + 0.055, -0.30, 0), (RP + 0.078, -0.30, 0), (RP + 0.078, -0.22, 0), (RP + 0.055, -0.22, 0)],
                         [zinc2], M1, steps=64, bevel=0.004))
    bm = bmesh.new()
    C.box_bm(bm, 0.07, 0.10, 0.11, center=(0, RP + 0.11, -0.26))
    hs = C.mesh_obj("ClampScrew", bm, [zinc2])
    hs.matrix_world = M1
    C.add_bevel(hs, 0.012, segments=2, angle=30)
    objs.append(C.finalize(hs, angle=35))
    # breather line alongside the neck (offset toward +b side in the floor plane)
    side = []
    for i in range(0, len(pts) * 3 // 4, 4):
        P, t = pts[i]
        nrm = t.cross(Vector((0, 0, 1))).normalized()
        side.append(P - nrm * (RP + 0.10) + Vector((0, 0, -0.05)))
    side[0] = Mh @ Vector((0.0, (RH - 0.02), 0.18))
    sp = [side[0] + (side[0] - (Mh @ Vector((0, 0, 0.18)))).normalized() * 0.12] + side
    objs.append(tube("Breather", sp, RV, zinc2, res=3))
    # rubber stub on the breather end
    e = sp[-1]
    d = (sp[-1] - sp[-2]).normalized()
    objs.append(tube("BreatherHose", [e - d * 0.02, e + d * 0.25, e + d * 0.45 + Vector((0, 0, -0.04))], RV + 0.03, rubber, res=3))
    # two clips tying the breather to the neck
    for i in (len(pts) // 4, len(pts) // 2):
        P, t = pts[i]
        nrm = t.cross(Vector((0, 0, 1))).normalized()
        Mc = frame_matrix(P, nrm, t)
        bm = bmesh.new()
        C.box_bm(bm, RP + 0.18, 0.05, 0.06, center=((RP + 0.18) / 2 - 0.03, 0, -0.05 + 0.0))
        cl = C.mesh_obj("Clip", bm, [black])
        cl.matrix_world = Mc @ Matrix.Rotation(math.radians(90), 4, "X")
        C.add_bevel(cl, 0.015, segments=2, angle=30)
        objs.append(C.finalize(cl, angle=35))
        objs.append(lathe_at("ClipBand", [(RP + 0.002, -0.03, 0), (RP + 0.022, -0.03, 0), (RP + 0.022, 0.03, 0), (RP + 0.002, 0.03, 0)],
                             [black], frame_matrix(P, b, t), steps=64, bevel=0.006))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("bocchettone", objs, "bocchettone.py",
            "car fuel filler neck: bent zinc-plated steel filler pipe with filler head, mounting plate and black screw cap, "
            "breather line alongside, rubber hose and clamp at the lower end",
            az=30, el=38, lens=70, fill=0.82,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
