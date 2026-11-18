"""Instrument cluster as removed from the dashboard: black textured housing with a short
anti-glare hood, curved clear front lens, black front mask with cowled dials, two large
gauges (speedometer 0-240, tachometer 0-7 x1000 with red zone) and two small ones
(fuel E/F, coolant C/H) with procedurally drawn ticks and numerals, orange needles on
black hubs, an unlit central display, side mounting tabs and a connector on the back.
No brand names or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

NU = 192
XH = 0.86            # half width of the front outline
Y_FACE = 0.13        # dial face plate depth
Y_MASK = 0.035       # front mask depth
BIG = [(-0.38, 0.03, 0.205), (0.38, 0.03, 0.205)]     # x, z, radius (speedo, tacho)
SMALL = [(-0.735, -0.01, 0.072), (0.735, -0.01, 0.072)]  # coolant, fuel
FLARE = 0.028
SFLARE = 0.034      # small gauges: wider cone so the scale is not hidden at 3/4 view
DISP = (0.0, 0.02, 0.105, 0.135)  # cx, cz, half w, half h


# ------------------------------------------------------------------ outline helpers
def outline(u, s=1.0):
    a = math.tau * u
    c, si = math.cos(a), math.sin(a)
    n = 4.6
    x0 = math.copysign(abs(c) ** (2 / n), c)
    z0 = math.copysign(abs(si) ** (2 / n), si)
    X = XH * x0
    Z = z0 * (0.285 + (0.075 * (1 - x0 * x0) if z0 > 0 else 0.0))
    return s * X, s * Z


def orient(bm, axis, sign):
    bm.normal_update()
    tot = sum(getattr(f.normal, axis) * f.calc_area() for f in bm.faces)
    if tot * sign < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)


def disc_grid(fn, nv, uv_fn=None):
    """Grid from centre (v=0) to outline (v=1); fn(u, v) -> Vector."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap") if uv_fn else None
    rows = [[bm.verts.new(fn(i / NU, j / nv)) for i in range(NU)] for j in range(nv + 1)]
    for j in range(nv):
        a, b = rows[j], rows[j + 1]
        for i in range(NU):
            i2 = (i + 1) % NU
            try:
                bm.faces.new((a[i], a[i2], b[i2], b[i]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    if uvl:
        for f in bm.faces:
            for l in f.loops:
                l[uvl].uv = uv_fn(l.vert.co)
    return bm


def place(ob, x, y, z):
    """local +Z -> world -Y (towards the viewer)."""
    ob.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
    return ob


# ------------------------------------------------------------------ dial artwork
FX0, FX1, FZ0, FZ1 = -0.93, 0.93, -0.33, 0.41
TW = 3200
TH = int(TW * (FZ1 - FZ0) / (FX1 - FX0))
S = TW / (FX1 - FX0)

GLYPHS = {
    "0": [[(0, .15), (0, .85), (.12, 1), (.48, 1), (.6, .85), (.6, .15), (.48, 0), (.12, 0), (0, .15)]],
    "1": [[(.12, .78), (.36, 1), (.36, 0)]],
    "2": [[(0, .8), (.12, 1), (.48, 1), (.6, .86), (.6, .64), (0, 0), (.62, 0)]],
    "3": [[(0, .88), (.12, 1), (.48, 1), (.6, .88), (.6, .64), (.48, .53), (.2, .53)],
          [(.48, .53), (.6, .42), (.6, .12), (.48, 0), (.12, 0), (0, .12)]],
    "4": [[(.46, 0), (.46, 1), (0, .3), (.64, .3)]],
    "5": [[(.58, 1), (.06, 1), (0, .56), (.44, .58), (.6, .45), (.6, .13), (.48, 0), (.12, 0), (0, .12)]],
    "6": [[(.56, .94), (.44, 1), (.16, 1), (0, .8), (0, .15), (.12, 0), (.48, 0), (.6, .15), (.6, .42),
           (.48, .56), (.12, .56), (0, .42)]],
    "7": [[(0, 1), (.62, 1), (.2, 0)]],
    "8": [[(.12, .53), (0, .64), (0, .88), (.12, 1), (.48, 1), (.6, .88), (.6, .64), (.48, .53), (.12, .53),
           (0, .41), (0, .12), (.12, 0), (.48, 0), (.6, .12), (.6, .41), (.48, .53)]],
    "9": [[(.04, .06), (.16, 0), (.44, 0), (.6, .2), (.6, .85), (.48, 1), (.12, 1), (0, .85), (0, .58),
           (.12, .44), (.48, .44), (.6, .58)]],
    "E": [[(.58, 1), (0, 1), (0, 0), (.58, 0)], [(0, .5), (.44, .5)]],
    "F": [[(.58, 1), (0, 1), (0, 0)], [(0, .5), (.44, .5)]],
    "C": [[(.6, .84), (.48, 1), (.12, 1), (0, .84), (0, .16), (.12, 0), (.48, 0), (.6, .16)]],
    "H": [[(0, 0), (0, 1)], [(.6, 0), (.6, 1)], [(0, .5), (.6, .5)]],
    "k": [[(0, 1), (0, 0)], [(.52, .66), (0, .24)], [(.17, .38), (.56, 0)]],
    "m": [[(0, 0), (0, .66)], [(0, .5), (.12, .66), (.24, .66), (.3, .52), (.3, 0)],
          [(.3, .52), (.42, .66), (.54, .66), (.6, .5), (.6, 0)]],
    "h": [[(0, 1), (0, 0)], [(0, .5), (.16, .66), (.46, .66), (.6, .5), (.6, 0)]],
    "/": [[(0, -.05), (.5, 1.05)]],
    "x": [[(0, 0), (.5, .66)], [(0, .66), (.5, 0)]],
    " ": [],
}


class Art:
    def __init__(self):
        self.img = np.zeros((TH, TW, 3), dtype=np.float32)
        self.img[:] = 0.014

    def px(self, x, z):
        return (x - FX0) * S, (z - FZ0) * S

    def seg(self, a, b, w, col):
        ax, ay = self.px(*a)
        bx, by = self.px(*b)
        r = w * S / 2
        x0 = max(0, int(min(ax, bx) - r - 2)); x1 = min(TW, int(max(ax, bx) + r + 3))
        y0 = max(0, int(min(ay, by) - r - 2)); y1 = min(TH, int(max(ay, by) + r + 3))
        if x1 <= x0 or y1 <= y0:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        pax, pay = xs - ax, ys - ay
        bax, bay = bx - ax, by - ay
        h = np.clip((pax * bax + pay * bay) / max(bax * bax + bay * bay, 1e-9), 0, 1)
        d = np.hypot(pax - bax * h, pay - bay * h)
        cov = np.clip(r - d + 0.5, 0, 1)[..., None]
        sub = self.img[y0:y1, x0:x1]
        sub[:] = sub * (1 - cov) + np.array(col, dtype=np.float32) * cov

    def disc(self, cx, cz, r0, r1, col):
        """Filled annulus (soft edged)."""
        ax, ay = self.px(cx, cz)
        R1 = r1 * S
        x0 = max(0, int(ax - R1 - 2)); x1 = min(TW, int(ax + R1 + 3))
        y0 = max(0, int(ay - R1 - 2)); y1 = min(TH, int(ay + R1 + 3))
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        d = np.hypot(xs - ax, ys - ay)
        cov = (np.clip(R1 - d + 0.5, 0, 1) * np.clip(d - r0 * S + 0.5, 0, 1))[..., None]
        sub = self.img[y0:y1, x0:x1]
        sub[:] = sub * (1 - cov) + np.array(col, dtype=np.float32) * cov

    def arc(self, cx, cz, r, t0, t1, w, col, n=None):
        n = n or max(8, int(abs(t1 - t0) / 2))
        pts = [(cx + r * math.cos(math.radians(t0 + (t1 - t0) * i / n)),
                cz + r * math.sin(math.radians(t0 + (t1 - t0) * i / n))) for i in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            self.seg(a, b, w, col)

    def text(self, s, cx, cz, hgt, col, wscale=1.0):
        adv = (0.6 * wscale + 0.2) * hgt
        width = adv * len(s) - 0.2 * hgt
        x = cx - width / 2
        for ch in s:
            for poly in GLYPHS[ch]:
                pts = [(x + px_ * hgt * wscale, cz - hgt / 2 + py * hgt) for px_, py in poly]
                for a, b in zip(pts, pts[1:]):
                    self.seg(a, b, 0.155 * hgt, col)
            x += adv
        return width

    def image(self, name):
        rgba = np.ones((TH, TW, 4), dtype=np.float32)
        rgba[..., :3] = self.img
        im = bpy.data.images.new(name, TW, TH, alpha=True)
        im.pixels.foreach_set(rgba.ravel())
        im.pack()
        return im


WHITE = (0.82, 0.82, 0.80)
GREY = (0.45, 0.45, 0.45)
RED = (0.75, 0.03, 0.02)
T0, T1 = 220.0, -40.0


def ang(v, vmax, t0=T0, t1=T1):
    return t0 + (t1 - t0) * v / vmax


def ray(art, cx, cz, t, r0, r1, w, col):
    c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
    art.seg((cx + r0 * c, cz + r0 * s), (cx + r1 * c, cz + r1 * s), w, col)


def artwork():
    art = Art()
    # slightly lighter dial faces with a fine outer ring
    for (cx, cz, R) in BIG:
        art.disc(cx, cz, 0, R + 0.01, (0.004, 0.004, 0.005))
        art.disc(cx, cz, R * 0.975, R * 0.99, (0.30, 0.30, 0.30))
    for (cx, cz, R) in SMALL:
        art.disc(cx, cz, 0, R + 0.008, (0.004, 0.004, 0.005))
    # speedometer
    cx, cz, R = BIG[0]
    for v in range(0, 241, 5):
        t = ang(v, 240)
        if v % 40 == 0:
            ray(art, cx, cz, t, 0.80 * R, 0.965 * R, 0.0072, WHITE)
            c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
            art.text(str(v), cx + 0.61 * R * c, cz + 0.61 * R * s, 0.036, WHITE, 0.9)
        elif v % 20 == 0:
            ray(art, cx, cz, t, 0.83 * R, 0.965 * R, 0.0058, WHITE)
        elif v % 10 == 0:
            ray(art, cx, cz, t, 0.87 * R, 0.965 * R, 0.0042, WHITE)
        else:
            ray(art, cx, cz, t, 0.91 * R, 0.965 * R, 0.0026, GREY)
    art.text("km/h", cx, cz - 0.38 * R, 0.022, GREY)
    # tachometer
    cx, cz, R = BIG[1]
    art.arc(cx, cz, 0.94 * R, ang(6, 7), ang(7, 7), 0.016, RED)
    for i in range(0, 29):
        v = i / 4
        t = ang(v, 7)
        col = RED if v >= 6 else WHITE
        if i % 4 == 0:
            ray(art, cx, cz, t, 0.79 * R, 0.965 * R, 0.0075, col)
            c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
            art.text(str(i // 4), cx + 0.62 * R * c, cz + 0.62 * R * s, 0.045, col)
        elif i % 2 == 0:
            ray(art, cx, cz, t, 0.87 * R, 0.965 * R, 0.0045, col)
        else:
            ray(art, cx, cz, t, 0.91 * R, 0.965 * R, 0.0028, GREY if v < 6 else RED)
    art.text("x1000", cx, cz - 0.38 * R, 0.022, GREY)
    # small gauges: coolant (left) and fuel (right)
    for (cx, cz, R), lo, hi, hot in ((SMALL[0], "C", "H", True), (SMALL[1], "E", "F", False)):
        a0, a1 = 215.0, 325.0  # lower arc ... drawn as upper arc instead
        t0, t1 = 150.0, 30.0
        art.arc(cx, cz, 0.86 * R, t0, t1, 0.0035, WHITE)
        for k in range(5):
            t = t0 + (t1 - t0) * k / 4
            col = RED if (k == 4 and hot) or (k == 0 and not hot) else WHITE
            ray(art, cx, cz, t, 0.68 * R if k % 2 == 0 else 0.75 * R, 0.86 * R, 0.0055, col)
        art.text(lo, cx - 0.62 * R, cz - 0.05 * R, 0.026, WHITE)
        art.text(hi, cx + 0.62 * R, cz - 0.05 * R, 0.026, RED if hot else WHITE)
    return art.image("DialArt")


def mat_dial(im):
    m = C.principled("DialFace", (1, 1, 1), rough=0.85, Specular_IOR_Level=0.3)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    tx.interpolation = "Cubic"
    nt.links.new(C._coord(nt, "UV"), tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    # printed markings read slightly backlit (translucent ink over the light guide)
    nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
    C._set(b, "Emission Strength", 0.35)
    return m


# ------------------------------------------------------------------ geometry
def housing(mat):
    rings = [(1.000, -0.006), (1.030, -0.010), (1.058, 0.004), (1.062, 0.07),
             (1.010, 0.27), (0.880, 0.345)]
    bm = bmesh.new()
    R = []
    for s, y in rings:
        R.append([bm.verts.new((outline(i / NU, s)[0], y, outline(i / NU, s)[1])) for i in range(NU)])
    for j in range(len(R) - 1):
        a, b = R[j], R[j + 1]
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((a[i], a[i2], b[i2], b[i]))
    c = bm.verts.new((0, 0.365, 0.02))
    for i in range(NU):
        bm.faces.new((R[-1][i], R[-1][(i + 1) % NU], c))
    C.fix_normals(bm)
    ob = C.mesh_obj("Housing", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.016
    so.offset = -1
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def hood(mat):
    """Anti-glare visor over the top edge, deepest in the middle."""
    ua, ub = 0.035, 0.465
    nu, nv = 120, 10
    bm = bmesh.new()
    rows = []
    for j in range(nv + 1):
        t = j / nv
        row = []
        for i in range(nu + 1):
            u = ua + (ub - ua) * i / nu
            q = math.sin(math.pi * (u - ua) / (ub - ua))
            depth = 0.16 * q ** 0.6
            s = 1.058 + 0.025 * t * q
            x, z = outline(u, s)
            row.append(bm.verts.new((x, 0.004 - depth * t, z + 0.012 * t * q)))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    orient(bm, "z", 1)
    ob = C.mesh_obj("Hood", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.016
    so.offset = -1
    C.add_bevel(ob, 0.005, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def lens(mat):
    def fn(u, v):
        x, z = outline(u, 1.012 * v)
        return Vector((x, -0.004 - 0.028 * (1 - (x / XH) ** 2) * (1 - 0.3 * v * v), z))
    bm = disc_grid(fn, 22)
    orient(bm, "y", -1)
    ob = C.mesh_obj("Lens", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.008
    so.offset = 1
    return C.finalize(ob, angle=60)


def face_plate(mat):
    def fn(u, v):
        x, z = outline(u, 1.0 * v)
        return Vector((x, Y_FACE, z))
    uvf = lambda co: ((co.x - FX0) / (FX1 - FX0), (co.z - FZ0) / (FZ1 - FZ0))
    bm = disc_grid(fn, 20, uvf)
    orient(bm, "y", -1)
    ob = C.mesh_obj("Face", bm, [mat])
    return C.finalize(ob, angle=60)


def rrect_bm(bm, cx, cz, hw, hh, r, y0, y1, n=6):
    pts = []
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccz = cx + sx * (hw - r), cz + sz * (hh - r)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    v0 = [bm.verts.new((x, y0, z)) for x, z in pts]
    v1 = [bm.verts.new((x, y1, z)) for x, z in pts]
    m = len(pts)
    for k in range(m):
        bm.faces.new((v0[k], v0[(k + 1) % m], v1[(k + 1) % m], v1[k]))
    caps = [bm.faces.new(v0[::-1]), bm.faces.new(v1)]
    side = [f for v in v0 for f in v.link_faces] + caps
    bmesh.ops.recalc_face_normals(bm, faces=list(set(side)))


def mask(mat):
    def fn(u, v):
        x, z = outline(u, 1.002 * v)
        return Vector((x, Y_MASK, z))
    bm = disc_grid(fn, 18)
    orient(bm, "y", -1)
    ob = C.mesh_obj("Mask", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.014
    so.offset = -1
    cb = bmesh.new()
    Rx = Matrix.Rotation(math.radians(90), 4, "X")
    for (x, z, r) in BIG:
        C.cyl_bm(cb, r + FLARE, -1, 1, seg=96, matrix=Matrix.Translation((x, 0, z)) @ Rx)
    for (x, z, r) in SMALL:
        C.cyl_bm(cb, r + SFLARE, -1, 1, seg=64, matrix=Matrix.Translation((x, 0, z)) @ Rx)
    cx, cz, hw, hh = DISP
    rrect_bm(cb, cx, cz, hw + 0.012, hh + 0.012, 0.03, -1, 1)
    cut = C.mesh_obj("MaskCut", cb, [mat])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.004, segments=2, angle=30)
    return C.finalize(ob, angle=40, remove=[cut])


def cowl(x, z, r, flare, black, chrome):
    """Conical black wall from dial face to the mask, chrome lip at the front."""
    d = Y_FACE - Y_MASK
    wall = C.lathe("Cowl", [(r + 0.004, 0.0, 0), (r + flare, d, 0), (r + flare + 0.006, d, 0),
                            (r + 0.010, 0.0, 0)], [black], steps=128)
    place(wall, x, Y_FACE, z)
    out = [C.finalize(wall, angle=50)]
    lip = C.lathe("Lip", [(r + flare - 0.004, 0.0, 0), (r + flare + 0.004, 0.0, 0), (r + flare + 0.007, 0.004, 0),
                          (r + flare + 0.003, 0.008, 0), (r + flare - 0.004, 0.006, 0)], [chrome], steps=128)
    place(lip, x, Y_MASK - 0.002, z)
    out.append(C.finalize(lip, angle=50))
    return out


def needle(x, z, length, t, mat, hubm, y=Y_FACE - 0.014, w=0.0075, tail=0.05):
    bm = bmesh.new()
    th = 0.004
    prof = [(-tail, w * 1.1), (0, w), (length, w * 0.32), (length + 0.004, 0.0),
            (length, -w * 0.32), (0, -w), (-tail, -w * 1.1)]
    bot = [bm.verts.new((px_, py, -th)) for px_, py in prof]
    top = [bm.verts.new((px_, py, th)) for px_, py in prof]
    m = len(prof)
    for k in range(m):
        bm.faces.new((bot[k], bot[(k + 1) % m], top[(k + 1) % m], top[k]))
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    C.fix_normals(bm)
    ob = C.mesh_obj("Needle", bm, [mat])
    C.add_bevel(ob, 0.0015, segments=1, angle=30)
    # local X along needle, local Z -> world -Y
    ob.matrix_world = (Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(90), 4, "X")
                       @ Matrix.Rotation(math.radians(t), 4, "Z"))
    # rotation: after Rx(90) local Y maps to world Z, so rotate in local XY plane
    out = [C.finalize(ob, angle=40)]
    hr = 0.024 if length > 0.1 else 0.014
    hub = C.lathe("Hub", [(0.0, 0.020, 0), (hr * 0.6, 0.018, 0), (hr, 0.010, 0), (hr, 0.0, 0), (0.0, 0.0, 0)],
                  [hubm], steps=48)
    place(hub, x, y - 0.002, z)
    out.append(C.finalize(hub, angle=40))
    return out


def display(glassm, framem, chrome):
    cx, cz, hw, hh = DISP
    bm = bmesh.new()
    rrect_bm(bm, cx, cz, hw, hh, 0.022, Y_FACE - 0.03, Y_FACE - 0.026)
    g = C.mesh_obj("Display", bm, [glassm])
    C.add_bevel(g, 0.002, segments=1, angle=30)
    out = [C.finalize(g, angle=40)]
    # tunnel walls from the display to the mask opening
    bm = bmesh.new()
    rrect_bm(bm, cx, cz, hw + 0.016, hh + 0.016, 0.034, Y_MASK + 0.006, Y_FACE - 0.02)
    t = C.mesh_obj("DispTunnel", bm, [framem])
    cb = bmesh.new()
    rrect_bm(cb, cx, cz, hw + 0.004, hh + 0.004, 0.026, Y_MASK - 0.1, Y_FACE + 0.1)
    cut = C.mesh_obj("DispCut", cb, [framem])
    C.add_boolean(t, cut)
    out.append(C.finalize(t, angle=40, remove=[cut]))
    # thin satin chrome frame at the mask opening
    bm = bmesh.new()
    rrect_bm(bm, cx, cz, hw + 0.020, hh + 0.020, 0.038, Y_MASK - 0.006, Y_MASK + 0.002)
    fr = C.mesh_obj("DispFrame", bm, [chrome])
    cb = bmesh.new()
    rrect_bm(cb, cx, cz, hw + 0.010, hh + 0.010, 0.030, Y_MASK - 0.1, Y_MASK + 0.1)
    cut = C.mesh_obj("FrameCut", cb, [chrome])
    C.add_boolean(fr, cut)
    C.add_bevel(fr, 0.002, segments=2, angle=30)
    out.append(C.finalize(fr, angle=40, remove=[cut]))
    return out


def tabs(mat):
    out = []
    Rx = Matrix.Rotation(math.radians(90), 4, "Z")
    for sx in (-1, 1):
        for (z, y) in ((0.12, 0.17), (-0.13, 0.17)):
            bm = bmesh.new()
            C.box_bm(bm, 0.16, 0.022, 0.10, center=(sx * (XH + 0.05), y, z))
            tb = C.mesh_obj("Tab", bm, [mat])
            cb = bmesh.new()
            C.cyl_bm(cb, 0.019, -1, 1, seg=32,
                     matrix=Matrix.Translation((sx * (XH + 0.085), y, z)) @ Matrix.Rotation(math.radians(90), 4, "X"))
            cut = C.mesh_obj("TabCut", cb, [mat])
            C.add_boolean(tb, cut)
            C.add_bevel(tb, 0.006, segments=2, angle=30)
            out.append(C.finalize(tb, angle=35, remove=[cut]))
    return out


def connector(shell, pins):
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.10, 0.10, center=(0.18, 0.37, -0.02))
    ob = C.mesh_obj("Connector", bm, [shell])
    cb = bmesh.new()
    C.box_bm(cb, 0.27, 0.10, 0.072, center=(0.18, 0.43, -0.02))
    cut = C.mesh_obj("ConnCut", cb, [shell])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.005, segments=2, angle=30)
    out = [C.finalize(ob, angle=35, remove=[cut])]
    bm = bmesh.new()
    for k in range(12):
        for r in (0, 1):
            C.box_bm(bm, 0.008, 0.06, 0.008, center=(0.07 + 0.02 * k, 0.37, -0.035 + 0.03 * r))
    out.append(C.mesh_obj("Pins", bm, [pins]))
    # back screw bosses
    bm = bmesh.new()
    for (x, z) in ((-0.55, 0.10), (-0.25, -0.12), (0.55, 0.10)):
        C.cyl_bm(bm, 0.03, 0.30, 0.36, seg=32,
                 matrix=Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    bo = C.mesh_obj("Bosses", bm, [shell])
    C.add_bevel(bo, 0.004, segments=1, angle=30)
    out.append(C.finalize(bo, angle=35))
    return out


def build():
    housing_m = C.mat_black_plastic("HousingPP", rough=0.55, color=0.026)
    mask_m = C.mat_black_plastic("MaskABS", rough=0.6, color=0.016)
    cowl_m = C.mat_black_plastic("CowlABS", rough=0.5, color=0.012, tex=False)
    lens_m = C.mat_clear("LensPC")
    chrome = C.principled("SatinChrome", (0.80, 0.80, 0.82), metallic=1.0, rough=0.16)
    needle_m = C.principled("NeedleOrange", C.srgb("#FF4A12"), rough=0.35,
                            Emission_Color=C.srgb("#FF4A12"), Emission_Strength=0.6)
    hub_m = C.principled("HubBlack", (0.015, 0.015, 0.016), rough=0.25)
    disp_m = C.principled("DisplayGlass", (0.004, 0.007, 0.012), rough=0.03, Coat_Weight=1.0)
    conn_m = C.mat_black_plastic("ConnPA", rough=0.6, color=0.03)
    pins_m = C.principled("PinTin", (0.75, 0.72, 0.62), metallic=1.0, rough=0.3)
    objs = [housing(housing_m), hood(housing_m), lens(lens_m), face_plate(mat_dial(artwork())), mask(mask_m)]
    for (x, z, r) in BIG:
        objs += cowl(x, z, r, FLARE, cowl_m, chrome)
    for (x, z, r) in SMALL:
        objs += cowl(x, z, r, SFLARE, cowl_m, chrome)
    objs += needle(BIG[0][0], BIG[0][1], 0.92 * BIG[0][2], ang(0, 240) - 3, needle_m, hub_m)
    objs += needle(BIG[1][0], BIG[1][1], 0.92 * BIG[1][2], ang(0, 7) - 3, needle_m, hub_m)
    objs += needle(SMALL[0][0], SMALL[0][1], 0.80 * SMALL[0][2], 150, needle_m, hub_m, w=0.005, tail=0.015)
    objs += needle(SMALL[1][0], SMALL[1][1], 0.80 * SMALL[1][2], 150, needle_m, hub_m, w=0.005, tail=0.015)
    objs += display(disp_m, cowl_m, chrome)
    objs += tabs(housing_m)
    objs += connector(conn_m, pins_m)
    return objs


def matte_floor_in_reflections():
    """The shadow-catcher floor is lit white; seen in the flat lens and display it washes
    the dials out in grey. Hide it from glossy rays only (the contact shadow is kept):
    C.shoot creates the floor right before the studio lights, so hook the light helper."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


if __name__ == "__main__":
    matte_floor_in_reflections()
    C.clear()
    objs = build()
    C.shoot("quadro", objs, "quadro.py",
            "car instrument cluster: black housing with hood and clear lens, speedometer and tachometer with "
            "needles, fuel and temperature gauges, central display, mounting tabs, rear connector",
            az=30, el=16, lens=70, fill=0.86, samples=int(os.environ.get("SAMPLES", 128)))
