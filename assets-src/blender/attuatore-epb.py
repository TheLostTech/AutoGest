"""Electric parking brake actuator (attuatore freno di stazionamento elettrico / motore
EPB) as removed from a rear caliper of a small car: black glass-filled nylon housing of
the motor-gear unit (round gearbox portion and parallel motor can portion, two shells
joined at a welded flange), stiffening ribs, mounting flange with two ears carrying
steel compression bushings and captive Torx bolts, round output spigot with O-ring and
the internal Torx drive that engages the caliper spindle, two-pin connector socket with
latch on the motor end. Built with the output axis along Z (spigot down), then laid on
its side so the spigot faces the camera. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

G = Vector((0.0, 0.0))        # gearbox centre (output axis)
RG = 0.43
M = Vector((0.66, 0.08))      # motor centre
RM = 0.29
ZS = 0.30                     # shell split height
HT = 0.80                     # total height


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=48, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def hull(off=0.0, n=40):
    """outline of two circles joined by their outer tangents (CCW)"""
    d = M - G
    L = d.length
    ang = math.atan2(d.y, d.x)
    a = math.acos((RG - RM) / L)
    pts = []
    for i in range(n + 1):                       # big circle, far side
        t = ang + a + (math.tau - 2 * a) * i / n
        pts.append(G + (RG + off) * Vector((math.cos(t), math.sin(t))))
    for i in range(n // 2 + 1):                  # small circle, far side
        t = ang - a + 2 * a * i / (n // 2)
        pts.append(M + (RM + off) * Vector((math.cos(t), math.sin(t))))
    return pts


def bevel(ob, width, segments=2, angle=30):
    """bevel with hardened normals: keeps the big flat moulded faces flat-shaded"""
    m = C.add_bevel(ob, width, segments=segments, angle=angle)
    try:
        m.harden_normals = True
    except Exception:
        pass
    return m


def prism(bm, pts, z0, z1, mat=0):
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    for f in bm.faces:
        f.material_index = mat


def ears():
    """mounting flange: two ears around the gearbox, away from the motor"""
    out = []
    for a in (math.radians(125), math.radians(245)):
        c = G + (RG + 0.10) * Vector((math.cos(a), math.sin(a)))
        out.append((c, a))
    return out


def housing(pa, steel, mark):
    out = []
    bm = bmesh.new()
    prism(bm, hull(0.0), 0.0, ZS - 0.02)
    lo = C.mesh_obj("LowerShell", bm, [pa])
    bevel(lo, 0.03, segments=3, angle=30)
    out.append(C.finalize(lo, angle=35))
    bm = bmesh.new()
    prism(bm, hull(0.03), ZS - 0.035, ZS + 0.025)      # welded flange
    fl = C.mesh_obj("WeldFlange", bm, [pa])
    bevel(fl, 0.012, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35))
    bm = bmesh.new()
    prism(bm, hull(-0.01), ZS + 0.01, HT)
    up = C.mesh_obj("Cover", bm, [pa])
    bevel(up, 0.07, segments=4, angle=30)
    out.append(C.finalize(up, angle=35))
    # vertical stiffening ribs on the gearbox wall and a ring rib on the cover top
    bm = bmesh.new()
    for k in range(7):
        a = math.radians(140 + 20 * k)
        c = G + (RG - 0.005) * Vector((math.cos(a), math.sin(a)))
        Mx = Matrix.Translation((c.x, c.y, (ZS + 0.04 + HT - 0.09) / 2)) @ Matrix.Rotation(a, 4, "Z")
        C.box_bm(bm, 0.06, 0.03, HT - 0.09 - ZS - 0.04, matrix=Mx)
    rb = C.mesh_obj("Ribs", bm, [pa])
    bevel(rb, 0.01, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    P = [(0.22, HT - 0.005, 0), (0.25, HT - 0.005, 0), (0.25, HT + 0.03, 0), (0.22, HT + 0.03, 0)]
    out.append(C.finalize(lathe_at("TopRing", P, [pa], Vector((G.x, G.y, 0)), (0, 0, 1), steps=96), angle=40))
    # motor end cap boss
    P = [(0.0, HT - 0.01, 0), (0.17, HT - 0.01, 0), (0.17, HT + 0.035, 0), (0.15, HT + 0.05, 0), (0.0, HT + 0.05, 0)]
    out.append(C.finalize(lathe_at("MotorCap", P, [pa], Vector((M.x, M.y, 0)), (0, 0, 1), steps=64), angle=40))
    # bottom mounting flange with ears
    bm = bmesh.new()
    pts = []
    n = 64
    for i in range(n):
        t = math.tau * i / n
        r = RG + 0.03
        for (c, a) in ears():
            da = math.atan2(math.sin(t - a), math.cos(t - a))
            r = max(r, RG + 0.03 + 0.16 * max(0.0, 1 - (da / 0.42) ** 2) ** 0.5)
        pts.append(G + r * Vector((math.cos(t), math.sin(t))))
    prism(bm, pts, 0.0, 0.09)
    fe = C.mesh_obj("Flange", bm, [pa])
    cb = bmesh.new()
    for (c, a) in ears():
        C.cyl_bm(cb, 0.055, -0.1, 0.3, seg=32, matrix=Matrix.Translation((c.x, c.y, 0)))
    cut = C.mesh_obj("EarHoles", cb, [pa])
    boolean(fe, cut)
    bevel(fe, 0.015, segments=2, angle=30)
    out.append(C.finalize(fe, angle=35, remove=[cut]))
    for (c, a) in ears():
        o = Vector((c.x, c.y, 0))
        P = [(0.038, -0.005, 0), (0.056, -0.005, 0), (0.056, 0.095, 0), (0.038, 0.095, 0)]
        out.append(C.finalize(lathe_at("Bushing", P, [steel], o, (0, 0, 1), steps=40), angle=40))
        # captive bolt: flanged Torx head on top of the ear, thread below
        P = [(0.0, 0.095, 0), (0.085, 0.095, 0), (0.085, 0.11, 0), (0.07, 0.125, 0), (0.07, 0.15, 0), (0.06, 0.16, 0), (0.0, 0.16, 0)]
        hd = lathe_at("BoltHead", P, [steel], o, (0, 0, 1), steps=48)
        cb = bmesh.new()
        C.cyl_bm(cb, 0.032, 0.12, 0.3, seg=6, matrix=Matrix.Translation(o))
        C.cyl_bm(cb, 0.032, 0.12, 0.3, seg=6, matrix=Matrix.Translation(o) @ Matrix.Rotation(math.radians(30), 4, "Z"))
        tc = C.mesh_obj("TorxCut", cb, [steel])
        boolean(hd, tc)
        out.append(C.finalize(hd, angle=40, remove=[tc]))
        pitch = 0.025

        def thread(r, z, t):
            return r + 0.004 * math.sin(math.tau * z / pitch + t) if r > 0.02 else r
        P = [(0.0, -0.20, 0), (0.026, -0.20, 0)] + [(0.034, -0.19 + i * 0.01, 0) for i in range(20)] + [(0.0, 0.0, 0)]
        out.append(C.finalize(lathe_at("BoltThread", P, [steel], o, (0, 0, 1), steps=32, mod=thread), angle=50))
    return out


def spigot(pa, oring, steel):
    out = []
    o = Vector((G.x, G.y, 0))
    P = [(0.0, -0.002, 0), (0.24, -0.002, 0), (0.24, -0.04, 0), (0.205, -0.05, 0), (0.205, -0.22, 0),
         (0.19, -0.235, 0), (0.12, -0.235, 0), (0.11, -0.22, 0), (0.0, -0.22, 0)]
    sp = lathe_at("Spigot", P, [pa], o, (0, 0, 1), steps=96)
    cb = bmesh.new()
    # internal Torx drive socket in the output gear
    for k in range(3):
        C.cyl_bm(cb, 0.022, -0.5, -0.10, seg=16, matrix=Matrix.Translation(o) @ Matrix.Rotation(math.radians(60 * k), 4, "Z") @ Matrix.Translation((0.075, 0, 0)))
        C.cyl_bm(cb, 0.022, -0.5, -0.10, seg=16, matrix=Matrix.Translation(o) @ Matrix.Rotation(math.radians(60 * k + 180), 4, "Z") @ Matrix.Translation((0.075, 0, 0)))
    C.cyl_bm(cb, 0.078, -0.5, -0.10, seg=48, matrix=Matrix.Translation(o))
    cut = C.mesh_obj("TorxSocket", cb, [steel])
    boolean(sp, cut)
    out.append(C.finalize(sp, angle=40, remove=[cut]))
    P = [(0.198, -0.10, 0), (0.212, -0.10, 0), (0.222, -0.115, 0), (0.212, -0.13, 0), (0.198, -0.13, 0)]
    out.append(C.finalize(lathe_at("ORing", P, [oring], o, (0, 0, 1), steps=96), angle=60))
    # steel output gear face visible inside the socket
    P = [(0.0, -0.13, 0), (0.11, -0.13, 0), (0.11, -0.12, 0), (0.0, -0.12, 0)]
    out.append(C.finalize(lathe_at("GearFace", P, [steel], o, (0, 0, 1), steps=48), angle=40))
    return out


def connector(pa, pin):
    """two-pin socket on the motor end, mouth facing +X"""
    out = []
    a = math.radians(-8)
    d = Vector((math.cos(a), math.sin(a), 0))
    base = Vector((M.x, M.y, 0)) + d * (RM - 0.03) + Vector((0, 0, 0.52))
    R = Matrix.Translation(base) @ Matrix.Rotation(a, 4, "Z")
    bm = bmesh.new()
    C.box_bm(bm, 0.26, 0.30, 0.20, center=(0.13, 0, 0))
    sh = C.mesh_obj("Shroud", bm, [pa])
    sh.matrix_world = R
    cb = bmesh.new()
    C.box_bm(cb, 0.22, 0.25, 0.15, center=(0.20, 0, 0))
    cut = C.mesh_obj("ShroudCut", cb, [pa])
    cut.matrix_world = R
    boolean(sh, cut)
    bevel(sh, 0.012, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    bm = bmesh.new()
    C.box_bm(bm, 0.10, 0.10, 0.03, center=(0.18, 0, 0.11))     # latch window frame
    C.box_bm(bm, 0.02, 0.09, 0.03, center=(0.235, 0, 0.115))    # latch ramp
    rb = C.mesh_obj("Latch", bm, [pa])
    rb.matrix_world = R
    bevel(rb, 0.006, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    bm = bmesh.new()
    for s in (-1, 1):
        C.box_bm(bm, 0.14, 0.025, 0.04, center=(0.15, s * 0.06, 0))
    pn = C.mesh_obj("Pins", bm, [pin])
    pn.matrix_world = R
    out.append(C.finalize(pn, angle=40))
    return out


def build():
    pa = C.principled("PA66GF", (0.024, 0.024, 0.026), rough=0.56)
    C.add_noise_bump(pa, scale=1100, strength=0.08, distance=0.0004, rough_var=0.05)
    steel = C.principled("ZincSteel", (0.60, 0.60, 0.58), metallic=1.0, rough=0.3)
    C.add_noise_bump(steel, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    oring = C.principled("ORing", (0.035, 0.035, 0.035), rough=0.5)
    pin = C.principled("TinPin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.22)
    objs = housing(pa, steel, None) + spigot(pa, oring, steel) + connector(pa, pin)
    # lie on the side: spigot towards the camera (-Y)
    C.transform_all(objs, Matrix.Rotation(math.radians(-15), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "X"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("attuatore-epb", objs, "attuatore-epb.py",
            "electric parking brake actuator: black plastic motor-gear housing, mounting ears with bolts, round output spigot with O-ring and Torx drive, connector",
            az=28, el=28, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
