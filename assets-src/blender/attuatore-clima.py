"""HVAC flap actuator motor (attuatore / motorino flap clima) as removed from the heater box
of a small car: compact two-part black plastic housing (rounded-rectangle outline with the
gear-end bulge), snap hooks along the parting line, three screw ears, the off-white
acetal output hub with its double-D drive shaft on the gear end, an integrated
multi-pin connector shroud with locking ramp, stiffening ribs and a blank adhesive label."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm. Housing footprint in X-Y, output face toward +Z.
H0, HS, H1 = 0.0, 1.55, 2.6      # base bottom, parting line, top (output face)
GC, GR = Vector((1.65, 0.35)), 2.15   # gear-end bulge centre / radius


# ----------------------------------------------------------------- helpers
def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=64, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def hull2d(pts):
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def circle(c, r, n=48):
    return [(c[0] + r * math.cos(math.tau * k / n), c[1] + r * math.sin(math.tau * k / n)) for k in range(n)]


def prism(name, poly, z0, z1, mats, inset=0.0):
    bm = bmesh.new()
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    P = []
    for (x, y) in poly:
        d = Vector((x - cx, y - cy))
        if inset and d.length > 1e-6:
            d2 = d.normalized() * (d.length - inset)
            x, y = cx + d2.x, cy + d2.y
        P.append((x, y))
    b = [bm.verts.new((x, y, z0)) for (x, y) in P]
    t = [bm.verts.new((x, y, z1)) for (x, y) in P]
    n = len(P)
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b[i], b[j], t[j], t[i]))
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, mats)


def outline():
    pts = circle(GC, GR, 72)
    for (x, y) in ((-3.0, -2.15), (-3.0, 2.45)):
        pts += circle((x + 0.45, y + (0.45 if y < 0 else -0.45)), 0.45, 16)
    return hull2d(pts)


# ----------------------------------------------------------------- parts
def housing(black, lid_m):
    out = []
    poly = outline()
    ob = prism("Base", poly, H0, HS - 0.03, [black])
    C.add_bevel(ob, 0.12, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35))
    ob = prism("Lid", poly, HS, H1, [lid_m], inset=0.03)
    C.add_bevel(ob, 0.14, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35))
    # parting-line lip (slightly proud, gives the seam a shadow line)
    ob = prism("Lip", poly, HS - 0.12, HS - 0.02, [black], inset=-0.05)
    C.add_bevel(ob, 0.03, segments=1, angle=30)
    out.append(C.finalize(ob, angle=35))
    # snap hooks across the parting line
    bm = bmesh.new()
    for (x, y, a) in ((-1.2, -2.17, 0), (1.0, -1.98, 0.25), (-1.2, 2.47, math.pi), (-3.03, 0.2, -math.pi / 2), (3.82, 0.4, math.pi / 2)):
        M = Matrix.Translation((x, y, HS)) @ Matrix.Rotation(a, 4, "Z")
        C.box_bm(bm, 0.55, 0.16, 0.95, matrix=M)
        C.box_bm(bm, 0.55, 0.12, 0.16, center=(0, -0.08, 0.42), matrix=M)
    sn = C.mesh_obj("Snaps", bm, [black])
    C.add_bevel(sn, 0.03, segments=1, angle=30)
    out.append(C.finalize(sn, angle=35))
    # ribs on the lid (output face), radial around the hub + one cross rib
    bm = bmesh.new()
    for k in range(6):
        a = math.radians(200 + 32 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        c = Vector((GC.x, GC.y, H1 + 0.07)) + d * 1.45
        M = Matrix.Translation(c) @ Matrix.Rotation(a, 4, "Z")
        C.box_bm(bm, 0.95, 0.14, 0.16, matrix=M)
    rb = C.mesh_obj("LidRibs", bm, [lid_m])
    C.add_bevel(rb, 0.035, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    return out


def ears(black):
    out = []
    specs = [((-3.35, -1.75), math.radians(215)), ((-3.35, 2.05), math.radians(145)), ((3.85, -1.3), math.radians(-40))]
    for (x, y), a in specs:
        d = Vector((math.cos(a), math.sin(a)))
        tip = Vector((x, y)) + d * 0.75
        pts = circle(tip, 0.55, 28) + [(x - 0.55 * d.y, y + 0.55 * d.x), (x + 0.55 * d.y, y - 0.55 * d.x),
                                       (x - 0.55 * d.y - 0.6 * d.x, y + 0.55 * d.x - 0.6 * d.y),
                                       (x + 0.55 * d.y - 0.6 * d.x, y - 0.55 * d.x - 0.6 * d.y)]
        ob = prism("Ear", hull2d(pts), H0, H0 + 0.42, [black])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.24, -1, 2, seg=32, matrix=Matrix.Translation((tip.x, tip.y, 0)))
        cut = C.mesh_obj("EarHole", cb, [black])
        bo = C.add_boolean(ob, cut)
        bo.use_self = True
        C.add_bevel(ob, 0.05, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
        # gusset from ear to wall
        bm = bmesh.new()
        M = Matrix.Translation((x - 0.25 * d.x, y - 0.25 * d.y, H0 + 0.6)) @ Matrix.Rotation(a, 4, "Z")
        C.box_bm(bm, 0.6, 0.14, 0.5, matrix=M)
        gs = C.mesh_obj("Gusset", bm, [black])
        C.add_bevel(gs, 0.03, segments=1, angle=30)
        out.append(C.finalize(gs, angle=35))
    return out


def output(pom, black):
    out = []
    c = (GC.x, GC.y, 0)
    P = [(0.80, H1 - 0.02, 0), (1.12, H1 - 0.02, 0), (1.12, H1 + 0.22, 0), (1.04, H1 + 0.28, 0), (0.80, H1 + 0.28, 0)]
    out.append(lathe_at("HubCollar", P, [black], origin=c, steps=96, bevel=0.02))
    P = [(0.0, H1 + 0.05, 0), (0.78, H1 + 0.05, 0), (0.78, H1 + 0.36, 0), (0.70, H1 + 0.44, 0), (0.0, H1 + 0.44, 0)]
    out.append(lathe_at("Hub", P, [pom], origin=c, steps=96, bevel=0.015))
    # double-D drive shaft
    def dd(r, z, t):
        if r < 0.3:
            return r
        x = abs(r * math.cos(t))
        return r if x <= 0.27 else 0.27 / max(1e-6, abs(math.cos(t)))
    P = [(0.0, H1 + 0.40, 0), (0.38, H1 + 0.40, 0), (0.38, H1 + 1.20, 0), (0.33, H1 + 1.26, 0), (0.0, H1 + 1.26, 0)]
    out.append(lathe_at("Shaft", P, [pom], origin=c, steps=96, mod=dd))
    return out


def connector(black, pin):
    out = []
    # shroud on the -Y wall near the straight end, mouth toward -Y
    x0, z0 = -1.55, 0.85
    y0 = -2.15
    bm = bmesh.new()
    C.box_bm(bm, 2.0, 1.1, 1.15, center=(x0, y0 - 0.45, z0))
    sh = C.mesh_obj("Shroud", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, 1.74, 1.2, 0.88, center=(x0, y0 - 0.75, z0))
    cut = C.mesh_obj("ShroudCut", cb, [black])
    bo = C.add_boolean(sh, cut)
    bo.use_self = True
    C.add_bevel(sh, 0.05, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    bm = bmesh.new()
    C.box_bm(bm, 0.6, 0.55, 0.16, center=(x0, y0 - 0.62, z0 + 0.64))
    C.box_bm(bm, 0.6, 0.12, 0.26, center=(x0, y0 - 0.84, z0 + 0.66))
    C.box_bm(bm, 0.14, 0.9, 0.22, center=(x0 - 0.88, y0 - 0.5, z0 + 0.66))
    C.box_bm(bm, 0.14, 0.9, 0.22, center=(x0 + 0.88, y0 - 0.5, z0 + 0.66))
    rp = C.mesh_obj("Latch", bm, [black])
    C.add_bevel(rp, 0.03, segments=1, angle=30)
    out.append(C.finalize(rp, angle=35))
    bm = bmesh.new()
    for i in range(6):
        C.box_bm(bm, 0.09, 0.75, 0.09, center=(x0 - 0.65 + i * 0.26, y0 - 0.55, z0 - 0.05))
    pn = C.mesh_obj("Pins", bm, [pin])
    out.append(C.finalize(pn, angle=35))
    return out


def build():
    black = C.mat_black_plastic("PBT", rough=0.5, color=0.028)
    lid = C.mat_black_plastic("LidPBT", rough=0.42, color=0.034)
    pom = C.principled("POM", (0.80, 0.78, 0.72), rough=0.38, **{"Subsurface Weight": 0.15})
    C.add_noise_bump(pom, scale=90, strength=0.04, distance=0.002)
    pin = C.principled("TinPin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.22)
    objs = housing(black, lid) + ears(black) + output(pom, black) + connector(black, pin)
    im = C.label_image("ActLabel", 1024, 560, seed=11, lines=4)
    M = Matrix.Translation((-1.55, 0.15, H1 + 0.004)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    objs.append(C.label_plane("Label", C.mat_label(im), 2.3, 1.3, M))
    C.transform_all(objs, Matrix.Rotation(math.radians(-18), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("attuatore-clima", objs, "attuatore-clima.py",
            "HVAC flap actuator: small black plastic motor housing with screw ears, off-white output shaft, connector, blank label",
            az=28, el=34, lens=70, fill=0.82,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
