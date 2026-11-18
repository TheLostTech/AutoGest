"""Ignition lock with key (steering-column lock housing): die-cast barrel housing with the
bolt block and column saddle, steel clamp strap with snapped-head shear bolts, black
transponder ring around the polished lock face, a plain key with black head inserted,
black ignition switch with its connector socket screwed to the back."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
N = 64
CY = -0.56         # column axis height (local Y) under the lock
RC = 0.25          # column radius


# ----------------------------------------------------------------- helpers
def oval(w, h, n=2.0, N=N):
    pts = []
    for k in range(N):
        a = TAU * k / N
        c, s = math.cos(a), math.sin(a)
        pts.append((w / 2 * math.copysign(abs(c) ** (2 / n), c), h / 2 * math.copysign(abs(s) ** (2 / n), s)))
    return pts


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


def path_pts(start, d, n, segs, step=0.02):
    """Planar pipe centre-line: segs = [('L', len) | ('A', radius, deg)] bending toward n."""
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
            Cc = P + n * R
            k = max(2, int(R * abs(ang) / step))
            for i in range(1, k + 1):
                rot = Matrix.Rotation(ang * i / k, 3, b)
                pts.append((Cc + rot @ (P - Cc), rot @ d))
            rot = Matrix.Rotation(ang, 3, b)
            P, d, n = Cc + rot @ (P - Cc), rot @ d, rot @ n
    return pts, b


def pipe(name, pts, b, r, mat, wall=0.009):
    sec = circle_pts(0, 0, r, 48)
    fr = [(P, b, t.cross(b), sec) for (P, t) in pts]
    ob = loft(name, fr, mat, cap=False)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = wall
    so.offset = -1
    so.use_even_offset = True
    return C.finalize(ob, angle=50)


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def tube(name, pts, r, mat, res=3, caps=True):
    """Smooth bezier tube through pts (auto handles)."""
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


def boxes(name, specs, mat, bevel=0.01, holes=(), seg=2, M=None):
    """specs: [(sx, sy, sz, center[, matrix])]; holes: [(r, z0, z1, matrix)] boolean cylinders."""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, z0, z1, HM) in holes:
            C.cyl_bm(cb, r, z0, z1, seg=32, matrix=HM)
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2):
    """Extrude a 2D polygon along local Z, optional boolean holes [(r, cx, cy)] through it."""
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), poly) for z in (z0, z1)]
    ob = loft(name, fr, mat)
    if M is not None:
        ob.matrix_world = M
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, cx, cy) in holes:
            C.cyl_bm(cb, r, z0 - 0.5, z1 + 0.5, seg=32, matrix=T((cx, cy, 0)))
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        if M is not None:
            cut.matrix_world = M
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def hex_at(name, r, z0, z1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


# ----------------------------------------------------------------- materials
def mat_diecast(name, base=0.50, rough=0.40):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base * 0.80, base * 0.80, base * 0.77, 1)
    mix.inputs["B"].default_value = (base * 1.08, base * 1.08, base * 1.06, 1)
    em = C.edge_mask(nt, 0.01, 4.0)
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(em, mix2.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.62, 0.62, 0.61, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 500.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.12
    bp.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def housing(cast):
    out = []
    P = [(0.0, -0.05, 0), (0.215, -0.05, 0), (0.235, -0.03, 0), (0.235, 0.50, 0), (0.22, 0.525, 0), (0.198, 0.535, 0),
         (0.198, 0.685, 0), (0.19, 0.70, 0), (0.0, 0.70, 0)]
    out.append(lathe_at("Barrel", P, [cast], Matrix(), steps=128, bevel=0.004))
    # bolt block + column saddle with the column bore
    bm = bmesh.new()
    C.box_bm(bm, 0.36, 0.30, 0.50, center=(0, -0.17, 0.22))
    C.box_bm(bm, 0.70, 0.16, 0.42, center=(0, CY + RC + 0.02, 0.22))
    for sx in (-1, 1):
        C.box_bm(bm, 0.15, 0.26, 0.24, center=(sx * 0.40, -0.43, 0.22))
    ob = C.mesh_obj("Saddle", bm, [cast])
    cb = bmesh.new()
    C.cyl_bm(cb, RC, -0.5, 1.0, seg=96, matrix=T((0, CY, 0)))
    for sx in (-1, 1):
        C.cyl_bm(cb, 0.032, -0.5, 0.5, seg=32, matrix=T((sx * 0.42, CY, 0.22)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    cut = C.mesh_obj("SaddleCut", cb, [cast])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.02, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # cast ribs along the top of the barrel and a screw boss on the side
    out.append(boxes("TopRibs", [(0.035, 0.06, 0.46, (sx * 0.085, 0.215, 0.26)) for sx in (-1, 1)], cast, bevel=0.012))
    out.append(lathe_at("SideBoss", [(0.0, 0.0, 0), (0.06, 0.0, 0), (0.055, 0.30, 0), (0.0, 0.30, 0)], [cast],
                        T((0.0, 0.0, 0.30)) @ Matrix.Rotation(math.radians(90), 4, "Y"), steps=40, bevel=0.008))
    # side web ribs
    out.append(boxes("Webs", [(0.03, 0.22, 0.40, (sx * 0.17, -0.27, 0.22)) for sx in (-1, 1)], cast, bevel=0.008))
    return out


def clamp(steel, bolt_m):
    out = []
    # lower strap: half ring under the column with flat ears
    P = [(RC + 0.002, 0.10, 0), (RC + 0.045, 0.10, 0), (RC + 0.045, 0.34, 0), (RC + 0.002, 0.34, 0)]
    ob = C.lathe("Strap", P, [steel], steps=128)
    ob.matrix_world = T((0, CY, 0))
    cb = bmesh.new()
    C.box_bm(cb, 1.0, 0.6, 1.0, center=(0, CY + 0.30, 0.22))
    cut = C.mesh_obj("StrapCut", cb, [steel])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    ears = []
    for sx in (-1, 1):
        ears.append((0.17, 0.04, 0.24, (sx * 0.39, CY - 0.02, 0.22)))
    out.append(boxes("StrapEars", ears, steel, bevel=0.008,
                     holes=[(0.032, -0.5, 0.5, T((sx * 0.42, CY, 0.22)) @ Matrix.Rotation(math.radians(-90), 4, "X")) for sx in (-1, 1)]))
    # shear bolts from below: cone head (snapped) + thread end on top
    for sx in (-1, 1):
        M = T((sx * 0.42, CY - 0.04, 0.22)) @ Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> world -Y
        out.append(lathe_at("ShearHead", [(0.0, 0.0, 0), (0.06, 0.0, 0), (0.06, 0.02, 0), (0.035, 0.07, 0), (0.0, 0.075, 0)],
                            [bolt_m], M, steps=48, bevel=0.003))
        out.append(lathe_at("ShearStem", [(0.0, -0.21, 0), (0.028, -0.21, 0), (0.028, 0.0, 0), (0.0, 0.0, 0)], [bolt_m], M, steps=32))
    return out


def front(black, chrome, brass):
    out = []
    ring = [(0.135, 0.665, 0), (0.25, 0.665, 0), (0.262, 0.68, 0), (0.262, 0.725, 0), (0.245, 0.745, 0), (0.15, 0.745, 0),
            (0.135, 0.73, 0)]
    out.append(lathe_at("TransponderRing", ring, [black], Matrix(), steps=128, bevel=0.003))
    face = [(0.0, 0.69, 0), (0.138, 0.69, 0), (0.138, 0.735, 0), (0.125, 0.75, 0), (0.0, 0.75, 0)]
    out.append(lathe_at("LockFace", face, [chrome], Matrix(), steps=96))
    # keyway insert (brass) slightly recessed
    out.append(boxes("Keyway", [(0.05, 0.13, 0.01, (0, 0.0, 0.748))], brass, bevel=0.004))
    # immobiliser lead + small connector
    pts = [(0.20, -0.17, 0.70), (0.26, -0.24, 0.66), (0.30, -0.30, 0.50), (0.32, -0.28, 0.32)]
    out.append(tube("ImmoLead", pts, 0.014, black, res=3))
    out.append(boxes("ImmoPlug", [(0.07, 0.06, 0.11, (0.32, -0.28, 0.27))], black, bevel=0.008))
    return out


def key(black, steel):
    out = []
    Mk = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # local x->Y, y->Z, z->X
    out.append(boxes("Blade", [(0.022, 0.10, 0.09, (0, 0.0, 0.79))], steel, bevel=0.004))
    out.append(boxes("Shoulder", [(0.05, 0.16, 0.035, (0, 0.0, 0.84))], steel, bevel=0.008))
    poly = resample(hull2d(circle_pts(0, 0.88, 0.075, 48) + circle_pts(0, 1.06, 0.165, 64)), 128)
    out.append(prism("KeyHead", poly, -0.048, 0.048, black, M=Mk, bevel=0.022, seg=4, holes=[(0.038, 0.0, 1.15)]))
    # moulded grip lines on the head
    out.append(prism("KeyGrip", resample(hull2d(circle_pts(0, 1.04, 0.10, 48)), 96), 0.048, 0.056, black, M=Mk,
                     bevel=0.004))
    return out


def switch(black, steel, pin_m):
    out = []
    P = [(0.0, -0.32, 0), (0.19, -0.32, 0), (0.205, -0.30, 0), (0.205, -0.07, 0), (0.24, -0.06, 0), (0.24, -0.04, 0),
         (0.0, -0.04, 0)]
    out.append(lathe_at("Switch", P, [black], Matrix(), steps=96, bevel=0.004))
    for k in range(2):
        th = math.pi * k + 0.6
        out.append(lathe_at("SwScrew", [(0.0, -0.04, 0), (0.026, -0.04, 0), (0.026, -0.065, 0), (0.0, -0.068, 0)],
                            [steel], T((0.215 * math.cos(th), 0.215 * math.sin(th), -0.005)), steps=24))
    # connector socket on the back face (opening toward -Z)
    cz = -0.38
    bm = bmesh.new()
    C.box_bm(bm, 0.24, 0.13, 0.13, center=(0.0, 0.0, cz))
    sh = C.mesh_obj("SwConn", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 0.20, 0.09, 0.13, center=(0.0, 0.0, cz - 0.03))
    cut = C.mesh_obj("SwConnCut", cb, [black])
    C.add_boolean(sh, cut)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    out.append(boxes("SwPins", [(0.012, 0.012, 0.08, ((i - 2) * 0.036, 0.0, cz + 0.01)) for i in range(5)], pin_m, bevel=0.0))
    out.append(boxes("SwLatch", [(0.06, 0.03, 0.05, (0.0, 0.075, cz - 0.02))], black, bevel=0.005))
    return out


def build():
    cast = mat_diecast("ZincDiecast", base=0.40, rough=0.50)
    steel = C.principled("ZincSteel", (0.48, 0.49, 0.50), metallic=1.0, rough=0.38)
    C.add_noise_bump(steel, scale=700, strength=0.04, distance=0.0005, rough_var=0.05)
    bolt_m = C.principled("BoltSteel", (0.50, 0.50, 0.51), metallic=1.0, rough=0.32)
    black = C.mat_black_plastic("PA66", rough=0.45, color=0.03)
    soft = C.mat_black_plastic("KeyRubber", rough=0.62, color=0.025)
    chrome = C.principled("SatinChrome", (0.80, 0.80, 0.81), metallic=1.0, rough=0.12)
    brass = C.principled("Brass", (0.78, 0.60, 0.32), metallic=1.0, rough=0.25)
    key_steel = C.principled("KeySteel", (0.70, 0.70, 0.71), metallic=1.0, rough=0.18)
    pin_m = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    objs = housing(cast) + clamp(steel, bolt_m) + front(black, chrome, brass) + key(soft, key_steel)
    objs += switch(black, steel, pin_m)
    # orient: lock axis (local Z) toward the camera-left and slightly up, local Y up
    k = Vector((-0.70, -0.64, 0.22)).normalized()
    X = Vector((0, 0, 1)).cross(k).normalized()
    C.transform_all(objs, frame_matrix(Vector((0, 0, 0)), X, k))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("blocchetto", objs, "blocchetto.py",
            "car ignition lock with key: die-cast steering-column lock housing with clamp and shear bolts, black "
            "transponder ring, inserted key with black head, ignition switch with connector",
            az=30, el=30, lens=70, fill=0.84,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
