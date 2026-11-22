"""Rear brake shoe set (ganasce freno) as removed from a small car, assembled and laid flat:
two curved pressed-steel shoes (T-section: curved table + crescent web with spring holes)
in worn black paint, bonded friction linings, upper and lower close-wound return springs
in yellow zinc, self-adjuster strut with star wheel and threaded sleeve, parking-brake
lever riveted to one shoe with its cable hook, hold-down springs and cups on both webs.
Built in the XY plane (shoes left/right of the drum centre), z up. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from pinza import mat_friction
from braccio import mat_worn_black

RL = 0.995           # lining outer radius
RT0, RT1 = 0.925, 0.950   # table inner / outer radius
ZW = 0.20            # web mid-plane
TW = 0.036           # web thickness
WID = 0.40           # table width
SPAN = math.radians(68)
SIDES = ((math.pi, "L"), (0.0, "R"))   # shoe centre angles


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def polar(r, th, z=0.0):
    return Vector((r * math.cos(th), r * math.sin(th), z))


def arc_band(bm, r0, r1, z0, z1, th0, th1, n=60, mat=0):
    frames = []
    for i in range(n + 1):
        th = th0 + (th1 - th0) * i / n
        U = Vector((math.cos(th), math.sin(th), 0))
        frames.append((Vector((0, 0, 0)), U, Vector((0, 0, 1)), [(r0, z0), (r1, z0), (r1, z1), (r0, z1)]))
    C.sweep(bm, frames, mat=mat)


def prism_xy(bm, pts, z0, z1, mat=0):
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in pts]
    fs = [bm.faces.new(top), bm.faces.new(bot[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        fs.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in fs:
        f.material_index = mat


def hole_pos(c, which):
    """spring / pin holes in the web, by shoe centre angle c"""
    s = 1 if c == 0.0 else -1
    if which == "top":
        return polar(0.865, c + s * math.radians(56))
    if which == "bot":
        return polar(0.865, c - s * math.radians(58))
    return polar(0.84, c)


# ----------------------------------------------------------------- shoes
def shoe(c, paint, lining):
    out = []
    th0, th1 = c - SPAN, c + SPAN
    bm = bmesh.new()
    arc_band(bm, RT0, RT1, ZW - WID / 2, ZW + WID / 2, th0, th1, n=80)
    tb = C.mesh_obj("Table", bm, [paint])
    C.add_bevel(tb, 0.008, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35))
    # crescent web: deeper in the middle, notched ends at the abutments
    pts = []
    n = 60
    for i in range(n + 1):
        u = i / n
        th = th0 + (th1 - th0) * u
        pts.append(polar(RT0 + 0.01, th))
    for i in range(n, -1, -1):
        u = i / n
        th = th0 + (th1 - th0) * u
        d = 0.10 + 0.09 * math.sin(math.pi * u) ** 0.8
        pts.append(polar(RT0 - d, th))
    bm = bmesh.new()
    prism_xy(bm, pts, ZW - TW / 2, ZW + TW / 2)
    web = C.mesh_obj("Web", bm, [paint])
    cb = bmesh.new()
    for w in ("top", "bot", "mid"):
        p = hole_pos(c, w)
        C.cyl_bm(cb, 0.022 if w != "mid" else 0.016, 0.0, 0.5, seg=20, matrix=Matrix.Translation(p))
    for k in (-1, 1):        # lightening holes
        p = polar(0.86, c + k * math.radians(28))
        C.cyl_bm(cb, 0.035, 0.0, 0.5, seg=24, matrix=Matrix.Translation(p))
    holes = C.mesh_obj("WebHoles", cb, [paint])
    boolean(web, holes)
    C.add_bevel(web, 0.008, segments=2, angle=30)
    out.append(C.finalize(web, angle=35, remove=[holes]))
    # bonded lining, shorter than the table, chamfered ends
    bm = bmesh.new()
    a = math.radians(5)
    arc_band(bm, RT1 - 0.002, RL, ZW - WID / 2 + 0.012, ZW + WID / 2 - 0.012, th0 + a, th1 - a, n=80)
    ln = C.mesh_obj("Lining", bm, [lining])
    C.add_bevel(ln, 0.012, segments=2, angle=30)
    out.append(C.finalize(ln, angle=35))
    return out


# ----------------------------------------------------------------- springs
def coil_spring(name, A, B, mat, coil_r=0.042, wire=0.011, z=ZW, hook_down=0.06):
    """close-wound tension spring between web holes A and B, hooks through the web"""
    A = Vector((A.x, A.y, z))
    B = Vector((B.x, B.y, z))
    D = (B - A)
    L = D.length
    T = D.normalized()
    U = Vector((0, 0, 1))
    V = T.cross(U)
    lead = 0.075
    pts = []
    # hook A: comes up through the hole, curls over into the coil axis
    for i in range(7):
        t = i / 6
        pts.append(A + Vector((0, 0, -hook_down * (1 - t))) + T * (0.02 * t) + U * (coil_r * math.sin(t * math.pi / 2)))
    coil_len = L - 2 * lead
    turns = coil_len / (2.05 * wire)
    nseg = int(turns * 24)
    P0 = A + T * lead
    for i in range(nseg + 1):
        t = i / nseg
        ph = turns * math.tau * t
        pts.append(P0 + T * (coil_len * t) + U * (coil_r * math.cos(ph)) + V * (coil_r * math.sin(ph)))
    for i in range(7):
        t = 1 - i / 6
        pts.append(B + Vector((0, 0, -hook_down * (1 - t))) - T * (0.02 * t) + U * (coil_r * math.sin(t * math.pi / 2)))
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = wire
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q.x, q.y, q.z, 1)
    cu.materials.append(mat)
    ob = C.link(bpy.data.objects.new(name, cu))
    return C.finalize(ob, angle=60)


def hold_down(c, zinc, spring_m):
    out = []
    p = hole_pos(c, "mid")
    z0 = ZW + TW / 2
    # compression spring standing on the web
    pts = []
    n = 5 * 24
    for i in range(n + 1):
        t = i / n
        ph = 5 * math.tau * t
        pts.append(Vector((p.x + 0.05 * math.cos(ph), p.y + 0.05 * math.sin(ph), z0 + 0.012 + 0.10 * t)))
    cu = bpy.data.curves.new("HoldSpring", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.009
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for q, v in zip(sp.points, pts):
        q.co = (v.x, v.y, v.z, 1)
    cu.materials.append(spring_m)
    out.append(C.finalize(C.link(bpy.data.objects.new("HoldSpring", cu)), angle=60))
    # cup washer + pin head
    P = [(0.0, z0 + 0.115, 0), (0.07, z0 + 0.115, 0), (0.075, z0 + 0.125, 0), (0.068, z0 + 0.14, 0), (0.055, z0 + 0.142, 0),
         (0.03, z0 + 0.132, 0), (0.0, z0 + 0.132, 0)]
    cup = C.lathe("Cup", P, [zinc], steps=48)
    cup.location = (p.x, p.y, 0)
    out.append(C.finalize(cup, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 0.05, 0.012, 0.012, center=(p.x, p.y, z0 + 0.146))
    C.cyl_bm(bm, 0.008, ZW - 0.1, z0 + 0.14, seg=12, matrix=Matrix.Translation((p.x, p.y, 0)))
    pin = C.mesh_obj("Pin", bm, [zinc])
    out.append(C.finalize(pin, angle=40))
    return out


# ----------------------------------------------------------------- adjuster + lever
def adjuster(paint, zinc, brass):
    out = []
    y = 0.60
    # flat strut from the left web to the star wheel, forked ends straddling the webs
    xl = -0.72
    bm = bmesh.new()
    C.box_bm(bm, 0.62, 0.06, 0.03, center=(xl + 0.31, y, ZW))
    for s in (-1, 1):
        C.box_bm(bm, 0.07, 0.05, 0.012, center=(xl + 0.015, y, ZW + s * (TW / 2 + 0.008)))
    st = C.mesh_obj("Strut", bm, [paint])
    C.add_bevel(st, 0.006, segments=2, angle=30)
    out.append(C.finalize(st, angle=35))
    # threaded sleeve + star wheel (axis X)
    X0 = -0.12
    P = [(0.0, 0.0, 0), (0.028, 0.0, 0), (0.028, 0.10, 0), (0.0, 0.10, 0)]
    sl = C.lathe("Sleeve", P, [brass], steps=32)
    sl.matrix_world = axis_mat(Vector((X0, y, ZW)), (1, 0, 0))
    out.append(C.finalize(sl, angle=40))

    def teeth(r, z, t):
        if r < 0.06:
            return r
        f = (t * 18 / math.tau) % 1.0
        return r - 0.016 * (1 - abs(2 * f - 1)) * 1.6 if r > 0.06 else r
    P = [(0.03, 0.10, 0), (0.068, 0.10, 0), (0.068, 0.135, 0), (0.03, 0.135, 0)]
    sw = C.lathe("StarWheel", P, [zinc], steps=144, mod=teeth)
    sw.matrix_world = axis_mat(Vector((X0, y, ZW)), (1, 0, 0))
    C.add_bevel(sw, 0.003, segments=1, angle=30)
    out.append(C.finalize(sw, angle=40))
    pitch = 0.016

    def thread(r, z, t):
        return r + 0.004 * math.sin(math.tau * z / pitch + t) if r > 0.01 else r
    P = [(0.0, 0.13, 0)] + [(0.020, 0.13 + i * 0.01, 0) for i in range(23)] + [(0.0, 0.35, 0)]
    rod = C.lathe("Screw", P, [zinc], steps=24, mod=thread)
    rod.matrix_world = axis_mat(Vector((X0, y, ZW)), (1, 0, 0))
    out.append(C.finalize(rod, angle=50))
    # forked end piece on the right web
    bm = bmesh.new()
    xr = X0 + 0.34
    C.box_bm(bm, 0.43 - 0.0, 0.055, 0.03, center=(xr + 0.0 + 0.16, y, ZW))
    for s in (-1, 1):
        C.box_bm(bm, 0.07, 0.05, 0.012, center=(0.705, y, ZW + s * (TW / 2 + 0.008)))
    fk = C.mesh_obj("Fork", bm, [paint])
    C.add_bevel(fk, 0.006, segments=2, angle=30)
    out.append(C.finalize(fk, angle=35))
    return out


def lever(paint, zinc):
    """parking-brake lever along the inside of the left web, pivot at the top"""
    out = []
    c = math.pi
    z0 = ZW + TW / 2 + 0.02
    pts_in, pts_out = [], []
    n = 30
    for i in range(n + 1):
        u = i / n
        th = c - math.radians(52) + math.radians(98) * u      # from upper end downwards
        r = 0.80 - 0.06 * math.sin(math.pi * u)
        w = 0.075 - 0.02 * u
        pts_out.append(polar(r + w / 2, th))
        pts_in.append(polar(r - w / 2, th))
    # cable hook at the bottom: curls inwards
    thb = c + math.radians(46)
    hook = [polar(0.70, thb + math.radians(4)), polar(0.62, thb + math.radians(1)), polar(0.60, thb - math.radians(6)),
            polar(0.66, thb - math.radians(9))]
    pts = pts_out + hook[::-1][:0] + [polar(0.74, thb + math.radians(5)), polar(0.62, thb + math.radians(3)),
                                      polar(0.58, thb - math.radians(3)), polar(0.62, thb - math.radians(8))] + pts_in[::-1]
    bm = bmesh.new()
    prism_xy(bm, pts, z0, z0 + 0.03)
    lv = C.mesh_obj("Lever", bm, [paint])
    C.add_bevel(lv, 0.007, segments=2, angle=30)
    out.append(C.finalize(lv, angle=35))
    # pivot rivet + clip
    p = polar(0.80, c - math.radians(50))
    P = [(0.0, z0 + 0.03, 0), (0.035, z0 + 0.03, 0), (0.032, z0 + 0.045, 0), (0.02, z0 + 0.052, 0), (0.0, z0 + 0.052, 0)]
    rv = C.lathe("Rivet", P, [zinc], steps=32)
    rv.location = (p.x, p.y, 0)
    out.append(C.finalize(rv, angle=50))
    return out


def build():
    paint = mat_worn_black("ShoePaint")
    lining = mat_friction("Lining")
    b = next(n for n in lining.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.095, 0.085, 0.072, 1)
    yzinc = C.principled("YellowZinc", (0.66, 0.52, 0.22), metallic=1.0, rough=0.32)
    C.add_noise_bump(yzinc, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    zinc = C.principled("Zinc", (0.62, 0.62, 0.60), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    brass = C.principled("BrassSleeve", (0.70, 0.55, 0.30), metallic=1.0, rough=0.35)
    objs = []
    for c, _ in SIDES:
        objs += shoe(c, paint, lining)
        objs += hold_down(c, zinc, zinc)
    objs.append(coil_spring("UpperSpring", hole_pos(math.pi, "top"), hole_pos(0.0, "top"), yzinc))
    objs.append(coil_spring("LowerSpring", hole_pos(math.pi, "bot"), hole_pos(0.0, "bot"), yzinc, coil_r=0.038))
    objs += adjuster(paint, zinc, brass)
    objs += lever(paint, zinc)
    C.transform_all(objs, Matrix.Rotation(math.radians(-8), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("ganasce", objs, "ganasce.py",
            "rear brake shoe set: two curved steel shoes with friction linings, return springs, adjuster strut with star wheel, handbrake lever",
            az=12, el=52, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
