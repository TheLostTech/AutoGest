"""Climate control panel (comandi clima) as removed from the centre console: black grained
fascia with three rotary knobs (temperature with a blue-to-red gradient scale, fan speed
with a growing dot scale and fan pictogram, air distribution with seated-person / windscreen
pictograms), satin-silver knob bezels, a row of four push buttons with printed pictograms
(A/C snowflake, recirculation, rear and front demist) and amber indicator LEDs, and the
black moulded housing behind with snap clips and two connector headers. No text or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))

# units: 1 = 10 cm.  Fascia front at -Y (towards the camera).
PHW, PHH = 0.98, 0.44
FY0, FY1 = -0.12, 0.0
HY1 = 0.62                      # housing back
KZ, KR = 0.12, 0.175            # knob row height, knob radius
KX = (-0.63, 0.0, 0.63)
BZ, BHW, BHH = -0.31, 0.175, 0.062
BX = (-0.585, -0.195, 0.195, 0.585)
RX = Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> world -Y

# ----------------------------------------------------------------- 2D artwork
class Canvas:
    """Antialiased artwork in physical units (x right, y up); premultiplied RGBA."""

    def __init__(self, pw, ph, ppu, bg=(0, 0, 0, 0)):
        self.S = ppu
        self.W, self.H = int(round(pw * ppu)), int(round(ph * ppu))
        self.img = np.zeros((self.H, self.W, 4), np.float32)
        bg = np.array(bg, np.float32)
        self.img[..., :3] = bg[:3] * bg[3]
        self.img[..., 3] = bg[3]

    def sdf(self, bbox, fn, col):
        S = self.S
        xmin, xmax, ymin, ymax = bbox
        x0 = max(0, int(xmin * S) - 2); x1 = min(self.W, int(xmax * S) + 3)
        y0 = max(0, int(ymin * S) - 2); y1 = min(self.H, int(ymax * S) + 3)
        if x1 <= x0 or y1 <= y0:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        d = fn(xs / S, ys / S)
        cov = np.clip(0.5 - d * S, 0, 1)
        c = np.array(tuple(col) + (1.0,) * (4 - len(col)), np.float32)
        a = (cov * c[3])[..., None]
        sub = self.img[y0:y1, x0:x1]
        sub[..., :3] = sub[..., :3] * (1 - a) + c[:3] * a
        sub[..., 3:] = sub[..., 3:] * (1 - a) + a

    def seg(self, a, b, wd, col):
        r = wd / 2
        (ax, ay), (bx, by) = a, b

        def fn(X, Y):
            px, py, vx, vy = X - ax, Y - ay, bx - ax, by - ay
            h = np.clip((px * vx + py * vy) / max(vx * vx + vy * vy, 1e-12), 0, 1)
            return np.hypot(px - vx * h, py - vy * h) - r
        self.sdf((min(ax, bx) - r, max(ax, bx) + r, min(ay, by) - r, max(ay, by) + r), fn, col)

    def line(self, pts, wd, col, closed=False):
        P = list(pts) + ([pts[0]] if closed else [])
        for a, b in zip(P, P[1:]):
            self.seg(a, b, wd, col)

    def arc(self, cx, cy, r, t0, t1, wd, col, n=None):
        n = n or max(6, int(abs(t1 - t0) / 4))
        self.line([(cx + r * math.cos(math.radians(t0 + (t1 - t0) * i / n)),
                    cy + r * math.sin(math.radians(t0 + (t1 - t0) * i / n))) for i in range(n + 1)], wd, col)

    def ring(self, cx, cy, r0, r1, col):
        def fn(X, Y):
            d = np.hypot(X - cx, Y - cy)
            return np.maximum(d - r1, r0 - d)
        self.sdf((cx - r1, cx + r1, cy - r1, cy + r1), fn, col)

    def rrect(self, cx, cy, hw, hh, r, col):
        def fn(X, Y):
            qx, qy = np.abs(X - cx) - (hw - r), np.abs(Y - cy) - (hh - r)
            return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
        self.sdf((cx - hw, cx + hw, cy - hh, cy + hh), fn, col)

    def poly(self, pts, col):
        V = [(float(x), float(y)) for x, y in pts]

        def fn(X, Y):
            d = (X - V[0][0]) ** 2 + (Y - V[0][1]) ** 2
            s = np.ones_like(X)
            n = len(V)
            for i in range(n):
                vi, vj = V[i], V[i - 1]
                ex, ey = vj[0] - vi[0], vj[1] - vi[1]
                wx, wy = X - vi[0], Y - vi[1]
                h = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-12), 0, 1)
                bx, by = wx - ex * h, wy - ey * h
                d = np.minimum(d, bx * bx + by * by)
                c1, c2, c3 = Y >= vi[1], Y < vj[1], ex * wy > ey * wx
                flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
                s = np.where(flip, -s, s)
            return s * np.sqrt(d)
        xs, ys = [p[0] for p in V], [p[1] for p in V]
        self.sdf((min(xs), max(xs), min(ys), max(ys)), fn, col)

    def image(self, name):
        out = self.img.copy()
        a = np.maximum(out[..., 3:], 1e-6)
        out[..., :3] = np.clip(out[..., :3] / a, 0, 1)
        im = bpy.data.images.new(name, self.W, self.H, alpha=True)
        im.pixels.foreach_set(out.ravel())
        im.pack()
        return im


SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


def seven(cv, ch, x, y, w, h, t, col, ghost=None, slant=0.12):
    """7-segment digit, lower-left corner (x, y)."""
    g = t * 0.55
    P = {"a": ((0, 1), (1, 1)), "b": ((1, 1), (1, .5)), "c": ((1, .5), (1, 0)), "d": ((0, 0), (1, 0)),
         "e": ((0, 0), (0, .5)), "f": ((0, .5), (0, 1)), "g": ((0, .5), (1, .5))}
    for s, ((u0, v0), (u1, v1)) in P.items():
        lit = s in SEGS[ch]
        if not lit and ghost is None:
            continue
        ax, ay = x + u0 * w + slant * v0 * h, y + v0 * h
        bx, by = x + u1 * w + slant * v1 * h, y + v1 * h
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        cv.seg((ax + ux * g, ay + uy * g), (bx - ux * g, by - uy * g), t, col if lit else ghost)


def mat_print(name, im, rough=0.4, emit=0.0, coat=0.0, spec=0.5):
    m = C.principled(name, (1, 1, 1), rough=rough, Coat_Weight=coat, Specular_IOR_Level=spec)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Coat Roughness", 0.03)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    tx.interpolation = "Cubic"
    nt.links.new(C._coord(nt, "UV"), tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
    if emit:
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        C._set(b, "Emission Strength", emit)
    return m


# ----------------------------------------------------------------- materials
def mat_satin(name="SatinSilver"):
    m = C.principled(name, (0.66, 0.66, 0.67), metallic=1.0, rough=0.24)
    C.add_noise_bump(m, scale=1400, strength=0.03, distance=0.0003, rough_var=0.04)
    return m


# ----------------------------------------------------------------- geometry helpers
def rrect_y(bm, cx, cz, hw, hh, r, y0, y1, n=6, mat=0):
    """Rounded-rectangle prism in the XZ plane, extruded from y0 to y1."""
    pts = []
    r = min(r, hw - 1e-4, hh - 1e-4)
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccz = cx + sx * (hw - r), cz + sz * (hh - r)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    v0 = [bm.verts.new((x, y0, z)) for x, z in pts]
    v1 = [bm.verts.new((x, y1, z)) for x, z in pts]
    m = len(pts)
    fs = [bm.faces.new((v0[k], v0[(k + 1) % m], v1[(k + 1) % m], v1[k])) for k in range(m)]
    fs += [bm.faces.new(v0[::-1]), bm.faces.new(v1)]
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    for f in fs:
        f.material_index = mat
    return fs


def solid(name, bm, mats, bevel=0.0, seg=2, angle=30, cutters=()):
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        C.add_boolean(ob, c)
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=angle)
    return C.finalize(ob, angle=38, remove=list(cutters))


def cutter(name, fill):
    bm = bmesh.new()
    fill(bm)
    return C.mesh_obj(name, bm, [])


WHITE = (0.88, 0.88, 0.86, 1)
GREYP = (0.55, 0.55, 0.55, 1)
T0, T1 = 225.0, -45.0           # scale sweep (degrees, ccw from +x)


def polar(cx, cy, r, t):
    return cx + r * math.cos(math.radians(t)), cy + r * math.sin(math.radians(t))


def arrow(cv, pts, wd, col, head=0.018):
    cv.line(pts, wd, col)
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1
    ux, uy = (bx - ax) / L, (by - ay) / L
    cv.poly([(bx + ux * head * 0.9, by + uy * head * 0.9),
             (bx - uy * head * 0.7, by + ux * head * 0.7),
             (bx + uy * head * 0.7, by - ux * head * 0.7)], col)


def wavy(cv, x, y0, y1, amp, wd, col, head=0.014):
    n = 16
    pts = [(x + amp * math.sin(math.tau * 1.25 * i / n), y0 + (y1 - y0) * i / n) for i in range(n + 1)]
    arrow(cv, pts, wd, col, head)


def snowflake(cv, x, y, r, wd, col):
    for k in range(3):
        a = math.radians(90 + 60 * k)
        c, s = math.cos(a), math.sin(a)
        cv.seg((x - r * c, y - r * s), (x + r * c, y + r * s), wd, col)
        for sg in (-1, 1):
            px, py = x + sg * 0.62 * r * c, y + sg * 0.62 * r * s
            for b in (-1, 1):
                ab = a + (0 if sg > 0 else math.pi) + b * math.radians(40)
                cv.seg((px, py), (px + 0.35 * r * math.cos(ab), py + 0.35 * r * math.sin(ab)), wd * 0.85, col)


def car_side(cv, x, y, s, wd, col):
    P = [(-1.0, -0.25), (-1.0, 0.12), (-0.62, 0.2), (-0.30, 0.55), (0.42, 0.58), (0.86, 0.28),
         (1.0, 0.18), (1.0, -0.25)]
    cv.line([(x + s * u, y + s * v) for u, v in P], wd, col)
    cv.seg((x - 0.62 * s, y - 0.25 * s), (x + 0.6 * s, y - 0.25 * s), wd, col)
    for u in (-0.62, 0.6):
        cv.ring(x + u * s, y - 0.3 * s, 0.10 * s, 0.10 * s + wd, col)


def person(cv, x, y, s, wd, col):
    """Seated figure facing right."""
    cv.ring(x + 0.05 * s, y + 0.62 * s, 0.0, 0.13 * s, col)
    cv.line([(x - 0.05 * s, y + 0.42 * s), (x - 0.18 * s, y - 0.05 * s), (x + 0.28 * s, y - 0.05 * s),
             (x + 0.36 * s, y - 0.50 * s), (x + 0.52 * s, y - 0.50 * s)], wd * 1.4, col)
    cv.line([(x - 0.12 * s, y + 0.32 * s), (x + 0.22 * s, y + 0.18 * s)], wd, col)


def windscreen(cv, x, y, s, wd, col):
    cv.line([(x - 0.7 * s, y - 0.3 * s), (x - 0.55 * s, y + 0.25 * s), (x, y + 0.36 * s),
             (x + 0.55 * s, y + 0.25 * s), (x + 0.7 * s, y - 0.3 * s), (x - 0.7 * s, y - 0.3 * s)], wd, col)


# ----------------------------------------------------------------- fascia + artwork
def fascia(black, satin):
    out = []
    bm = bmesh.new()
    rrect_y(bm, 0, 0, PHW, PHH, 0.08, FY0, FY1, n=8)

    def cuts(cb):
        for x in KX:      # shallow cups around the knobs
            C.cyl_bm(cb, KR + 0.03, -0.014, 0.1, seg=128, matrix=Matrix.Translation((x, FY0, KZ)) @ RX)
        for x in BX:      # button wells
            rrect_y(cb, x, BZ, BHW + 0.012, BHH + 0.012, 0.03, FY0 - 0.1, FY0 + 0.04)
    cut = cutter("FasciaCut", cuts)
    out.append(solid("Fascia", bm, [black], bevel=0.016, seg=3, cutters=[cut]))
    # satin bezel rings in the cups
    for x in KX:
        bz = C.lathe("Bezel", [(KR + 0.006, -0.014, 0), (KR + 0.028, -0.014, 0), (KR + 0.028, 0.004, 0),
                               (KR + 0.022, 0.011, 0), (KR + 0.006, 0.011, 0)], [satin], steps=160)
        bz.matrix_world = Matrix.Translation((x, FY0, KZ)) @ RX
        out.append(C.finalize(bz, angle=40))
    # printed scales on the fascia
    x0, x1, z0, z1 = -PHW + 0.05, PHW - 0.05, -0.20, PHH - 0.03
    cv = Canvas(x1 - x0, z1 - z0, 1600)
    R0 = KR + 0.062
    # temperature: gradient band blue -> red
    cx, cy = KX[0] - x0, KZ - z0
    n = 90
    for i in range(n):
        t = i / (n - 1)
        a0 = T0 + (T1 - T0) * i / n
        a1 = T0 + (T1 - T0) * (i + 1.2) / n
        blue, red = np.array((0.10, 0.36, 0.95)), np.array((0.95, 0.12, 0.06))
        mid = np.array((0.80, 0.80, 0.80))
        c = blue + (mid - blue) * (t / 0.5) if t < 0.5 else mid + (red - mid) * ((t - 0.5) / 0.5)
        wd = 0.014 + 0.016 * abs(t - 0.5) * 2
        cv.arc(cx, cy, R0 + wd / 2, a0, a1, wd, tuple(c) + (1,), n=2)
    for k in range(7):
        t = T0 + (T1 - T0) * k / 6
        cv.seg(polar(cx, cy, R0 + 0.032, t), polar(cx, cy, R0 + 0.044, t), 0.005, WHITE)
    # fan speed: off ring + growing dots, fan pictogram at the bottom
    cx, cy = KX[1] - x0, KZ - z0
    p = polar(cx, cy, R0 + 0.012, T0)
    cv.ring(p[0], p[1], 0.010, 0.016, WHITE)
    cv.seg((p[0] - 0.012, p[1] - 0.012), (p[0] + 0.012, p[1] + 0.012), 0.005, WHITE)
    for k in range(1, 5):
        t = T0 + (T1 - T0) * k / 4
        q = polar(cx, cy, R0 + 0.014, t)
        cv.ring(q[0], q[1], 0, 0.006 + 0.0035 * k, WHITE)
    fx, fy = cx, cy - R0 - 0.01
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c, s = math.cos(a), math.sin(a)
        cv.poly([(fx, fy), (fx + 0.030 * math.cos(a - 0.45), fy + 0.030 * math.sin(a - 0.45)),
                 (fx + 0.034 * c, fy + 0.034 * s), (fx + 0.022 * math.cos(a + 0.5), fy + 0.022 * math.sin(a + 0.5))],
                WHITE)
    cv.ring(fx, fy, 0, 0.007, (0.02, 0.02, 0.02, 1))
    # air distribution: five pictograms around the knob
    cx, cy = KX[2] - x0, KZ - z0
    icons = ["face", "facefeet", "feet", "feetscreen", "screen"]
    for k, kind in enumerate(icons):
        t = T0 + (T1 - T0) * k / 4
        ix, iy = polar(cx, cy, R0 + 0.040, t)
        s = 0.05
        if kind == "screen":
            windscreen(cv, ix, iy - 0.005, s, 0.0055, WHITE)
            for u in (-0.3, 0, 0.3):
                wavy(cv, ix + u * s, iy - 0.009, iy + 0.008, 0.004, 0.0045, WHITE, 0.008)
            continue
        person(cv, ix - 0.01, iy - 0.002, s, 0.0055, WHITE)
        if kind in ("face", "facefeet"):
            arrow(cv, [(ix + 0.058, iy + 0.028), (ix + 0.022, iy + 0.028)], 0.005, WHITE, 0.011)
        if kind in ("feet", "facefeet", "feetscreen"):
            arrow(cv, [(ix + 0.060, iy - 0.006), (ix + 0.034, iy - 0.026)], 0.005, WHITE, 0.011)
        if kind == "feetscreen":
            windscreen(cv, ix - 0.005, iy + 0.05, 0.03, 0.0045, WHITE)
    # thin divider rule between knobs and buttons
    cv.seg((0.12, -0.215 - z0 + 0.0), (x1 - x0 - 0.12, -0.215 - z0), 0.003, (0.30, 0.30, 0.30, 1))
    m = mat_print("FasciaPrint", cv.image("FasciaPrint"), rough=0.5)
    out.append(C.label_plane("FasciaArt", m, x1 - x0, z1 - z0,
                             Matrix.Translation(((x0 + x1) / 2, FY0 - 0.0011, (z0 + z1) / 2))))
    return out


def knob(x, phi, black, satin, white):
    out = []

    def knurl(r, zz, t):
        if 0.02 < zz < 0.075 and r > KR - 0.012:
            return r - 0.004 * (0.5 + 0.5 * math.cos(60 * t)) ** 2
        return r
    P = [(0.0, 0.092, 0), (KR - 0.03, 0.092, 0), (KR - 0.018, 0.098, 0), (KR - 0.004, 0.102, 1),
         (KR, 0.092, 1), (KR, 0.080, 1), (KR - 0.002, 0.076, 0), (KR - 0.002, 0.012, 0), (KR - 0.01, 0.0, 0),
         (0.0, 0.0, 0)]
    M = Matrix.Translation((x, FY0, KZ)) @ RX @ Matrix.Rotation(math.radians(phi), 4, "Z")
    kb = C.lathe("Knob", P, [black, satin], steps=192, mod=knurl)
    kb.matrix_world = M
    out.append(C.finalize(kb, angle=40))
    # grip bar across the face
    bm = bmesh.new()
    C.box_bm(bm, 2 * KR - 0.05, 0.06, 0.06, center=(0, 0, 0.092 + 0.025))
    gb = C.mesh_obj("Grip", bm, [black])
    gb.matrix_world = M
    C.add_bevel(gb, 0.018, segments=4, angle=30)
    out.append(C.finalize(gb, angle=40))
    # white pointer inlay at the +X end of the bar
    bm = bmesh.new()
    C.box_bm(bm, 0.06, 0.013, 0.004, center=(KR - 0.075, 0, 0.092 + 0.0555))
    pt = C.mesh_obj("Pointer", bm, [white])
    pt.matrix_world = M
    C.add_bevel(pt, 0.002, segments=1, angle=30)
    out.append(C.finalize(pt, angle=40))
    return out


def buttons(btn, led_on, led_off):
    out = []
    yb0 = FY0 - 0.03
    bm = bmesh.new()
    for x in BX:
        rrect_y(bm, x, BZ, BHW, BHH, 0.03, yb0, FY0 + 0.03)
    out.append(solid("Buttons", bm, [btn], bevel=0.01, seg=3))
    x0, x1 = -0.80, 0.80
    z0, z1 = BZ - 0.07, BZ + 0.07
    cv = Canvas(x1 - x0, z1 - z0, 2200)
    W = WHITE
    for i, x in enumerate(BX):
        u, v = x - x0 - 0.03, BZ - z0
        if i == 0:
            snowflake(cv, u, v, 0.046, 0.0068, W)
        elif i == 1:
            car_side(cv, u, v - 0.006, 0.066, 0.006, W)
            cv.arc(u, v + 0.004, 0.021, 200, 480, 0.0055, W)
            q = polar(u, v + 0.004, 0.021, 200)
            cv.poly([(q[0] - 0.009, q[1] + 0.004), (q[0] + 0.007, q[1] + 0.006), (q[0] - 0.001, q[1] - 0.009)], W)
        elif i == 2:
            cv.line([(u - 0.056, v - 0.038), (u + 0.056, v - 0.038), (u + 0.056, v + 0.038), (u - 0.056, v + 0.038)],
                    0.006, W, closed=True)
            for k in (-1, 0, 1):
                wavy(cv, u + k * 0.03, v - 0.026, v + 0.018, 0.006, 0.0052, W, 0.011)
        else:
            windscreen(cv, u, v - 0.004, 0.078, 0.006, W)
            for k in (-1, 0, 1):
                wavy(cv, u + k * 0.028, v - 0.024, v + 0.016, 0.006, 0.0052, W, 0.011)
    m = mat_print("ButtonPrint", cv.image("ButtonPrint"), rough=0.4)
    out.append(C.label_plane("BtnArt", m, x1 - x0, z1 - z0,
                             Matrix.Translation(((x0 + x1) / 2, yb0 - 0.0011, (z0 + z1) / 2))))
    # indicator LEDs (A/C lit)
    bm_on, bm_off = bmesh.new(), bmesh.new()
    for i, x in enumerate(BX):
        rrect_y(bm_on if i == 0 else bm_off, x + BHW - 0.045, BZ, 0.018, 0.009, 0.008, yb0 - 0.004, yb0 + 0.01)
    out.append(solid("LedOn", bm_on, [led_on], bevel=0.002, seg=1))
    out.append(solid("LedOff", bm_off, [led_off], bevel=0.002, seg=1))
    return out


# ----------------------------------------------------------------- housing
def housing(black, conn, pins):
    out = []
    bm = bmesh.new()
    rrect_y(bm, 0, -0.02, PHW - 0.12, PHH - 0.1, 0.05, FY1 - 0.01, HY1, n=6)
    out.append(solid("Housing", bm, [black], bevel=0.012, seg=2))
    # moulded stiffening ribs on the top and the snap clips on the sides
    bm = bmesh.new()
    for x in (-0.55, -0.18, 0.18, 0.55):
        C.box_bm(bm, 0.03, HY1 - 0.08, 0.02, center=(x, (HY1 + 0.06) / 2, PHH - 0.12 + 0.004))
    for sx in (-1, 1):
        for z in (0.14, -0.18):
            C.box_bm(bm, 0.05, 0.16, 0.10, center=(sx * (PHW - 0.12 + 0.02), 0.16, z))
    out.append(solid("Ribs", bm, [black], bevel=0.008))
    # screw bosses on the back corners
    bm = bmesh.new()
    for sx in (-1, 1):
        C.cyl_bm(bm, 0.05, 0.0, 0.1, seg=32,
                 matrix=Matrix.Translation((sx * (PHW - 0.18), HY1 - 0.05, PHH - 0.17)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    out.append(solid("Bosses", bm, [black], bevel=0.006))
    # two connector headers on the back face
    for (cx, w, h, rows) in ((-0.30, 0.36, 0.18, 2), (0.25, 0.24, 0.14, 1)):
        bm = bmesh.new()
        C.box_bm(bm, w, 0.16, h, center=(cx, HY1 + 0.06, -0.06))
        sh = C.mesh_obj("Conn", bm, [conn])
        cb = bmesh.new()
        C.box_bm(cb, w - 0.04, 0.2, h - 0.04, center=(cx, HY1 + 0.19, -0.06))
        c2 = C.mesh_obj("ConnCut", cb, [])
        C.add_boolean(sh, c2)
        C.add_bevel(sh, 0.005, segments=2, angle=30)
        out.append(C.finalize(sh, angle=38, remove=[c2]))
        bm = bmesh.new()
        for r in range(rows):
            nx = int((w - 0.06) / 0.04)
            for k in range(nx):
                C.box_bm(bm, 0.01, 0.10, 0.01,
                         center=(cx - (nx - 1) * 0.02 + k * 0.04, HY1 + 0.08, -0.06 + (r - (rows - 1) / 2) * 0.05))
        out.append(C.mesh_obj("Pins", bm, [pins]))
        bm = bmesh.new()
        C.box_bm(bm, 0.08, 0.06, 0.03, center=(cx, HY1 + 0.10, -0.06 + h / 2 + 0.012))
        out.append(solid("Latch", bm, [conn], bevel=0.004))
    return out


def build():
    black = C.principled("FasciaPP", (0.020, 0.020, 0.021), rough=0.58)
    C.add_noise_bump(black, scale=700, strength=0.30, distance=0.0006, detail=4.0, rough_var=0.07)
    housing_m = C.mat_black_plastic("HousingPP", rough=0.6, color=0.03)
    knob_m = C.principled("KnobRubber", (0.022, 0.022, 0.023), rough=0.5)
    C.add_noise_bump(knob_m, scale=1100, strength=0.10, distance=0.0004)
    btn = C.principled("ButtonPC", (0.024, 0.024, 0.026), rough=0.36)
    C.add_noise_bump(btn, scale=1200, strength=0.05, distance=0.0003)
    satin = mat_satin()
    white = C.principled("PointerWhite", (0.85, 0.85, 0.83), rough=0.4)
    led_on = C.principled("LedOn", C.srgb("#FFA21A"), rough=0.2, Emission_Color=C.srgb("#FFA21A"),
                          Emission_Strength=6.0)
    led_off = C.principled("LedOff", (0.05, 0.035, 0.02), rough=0.2)
    conn = C.mat_black_plastic("ConnPA", rough=0.6, color=0.032)
    pins = C.principled("PinTin", (0.75, 0.72, 0.62), metallic=1.0, rough=0.3)
    objs = fascia(black, satin)
    for x, phi in zip(KX, (110.0, 130.0, 180.0)):
        objs += knob(x, phi, knob_m, satin, white)
    objs += buttons(btn, led_on, led_off)
    objs += housing(housing_m, conn, pins)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("comandi-clima", objs, "comandi-clima.py",
            "car climate control panel: black fascia with temperature, fan-speed and air-distribution knobs, "
            "printed scales and pictograms, A/C, recirculation and demist buttons, housing with connectors behind",
            az=24, el=20, lens=70, fill=0.86, **kw)
