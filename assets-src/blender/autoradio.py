"""Car radio head unit (autoradio 1-DIN) as removed from the dashboard: black grained
faceplate with a recessed dark-glass display showing a simple segment readout, a CD slot,
a knurled volume knob with satin-silver cap and bezel, six preset buttons, a four-way
rocker and small function buttons with pictograms; behind it the zinc-plated steel DIN
chassis with vent slots, side clip holes, a blank label on top and the ISO connector
blocks, antenna socket and heat sink on the back. No brand names or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))

# units: 1 = 10 cm.  Faceplate front at -Y (towards the camera).
FHW, FHH = 0.94, 0.30          # faceplate half width / height
FY0, FY1 = -0.24, 0.0          # faceplate front / back
CHW, CHH = 0.89, 0.25          # chassis half width / height
CY1 = 1.60                     # chassis back
DISP = (0.0, 0.10, 0.40, 0.10)  # display window cx, cz, half w, half h
KNOB = (-0.71, 0.03, 0.15)
ROCK = (0.69, 0.03, 0.15)
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
def mat_zinc(name="ZincSteel"):
    """Bright zinc-plated sheet steel with a faint mottled passivation."""
    m = C.principled(name, (0.62, 0.63, 0.64), metallic=0.8, rough=0.30)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 5.0
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (0.20, 0.21, 0.22, 1)
    col.inputs["B"].default_value = (0.27, 0.27, 0.265, 1)
    nt.links.new(col.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.48
    rr.inputs["To Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 900.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.04
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


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


# ----------------------------------------------------------------- faceplate
def faceplate(black, gloss):
    out = []
    bm = bmesh.new()
    rrect_y(bm, 0, 0, FHW, FHH, 0.06, FY0, FY1, n=8)
    cx, cz, hw, hh = DISP

    def cuts(cb):
        rrect_y(cb, cx, cz, hw + 0.02, hh + 0.02, 0.03, FY0 - 0.1, FY0 + 0.05)
        rrect_y(cb, 0.0, 0.248, 0.30, 0.008, 0.007, FY0 - 0.1, FY0 + 0.12)   # CD slot
        for (x, z, r) in (KNOB, ROCK):                                         # shallow cups
            C.cyl_bm(cb, r + 0.035, -0.012, 0.1, seg=96,
                     matrix=Matrix.Translation((x, FY0, z)) @ RX)
    cut = cutter("FaceCut", cuts)
    out.append(solid("Faceplate", bm, [black], bevel=0.014, seg=3, cutters=[cut]))
    # thin gloss-black inlay strip under the button row and around the display
    bm = bmesh.new()
    rrect_y(bm, 0, -0.17, 0.43, 0.075, 0.02, FY0 - 0.004, FY0 + 0.01)
    out.append(solid("ButtonBed", bm, [gloss], bevel=0.004))
    return out


def display(glass_m, satin):
    cx, cz, hw, hh = DISP
    out = []
    # display artwork (dark glass, segment readout)
    cv = Canvas(2 * hw, 2 * hh, 2400, bg=(0.012, 0.016, 0.022, 1))
    LIT = (0.62, 0.86, 1.0, 1)
    GH = (0.07, 0.09, 0.11, 1)
    # band / preset readout on the left
    seven(cv, "8", 0.05, 0.10, 0.028, 0.05, 0.007, GH, GH)
    seven(cv, "1", 0.05, 0.10, 0.028, 0.05, 0.007, LIT, GH)
    # frequency 87.50
    x = 0.20
    for ch in "8750":
        seven(cv, ch, x, 0.035, 0.07, 0.125, 0.017, LIT, GH)
        x += 0.10
        if ch == "7":
            cv.rrect(x - 0.008, 0.044, 0.010, 0.010, 0.004, LIT)
            x += 0.024
    # signal bars on the right
    for i in range(5):
        cv.rrect(0.69 + i * 0.019, 0.05 + i * 0.012, 0.006, 0.012 + i * 0.012, 0.002, LIT if i < 4 else GH)
    # stereo pictogram (two linked rings) and a thin rule
    cv.ring(0.075, 0.165, 0.008, 0.013, LIT)
    cv.ring(0.093, 0.165, 0.008, 0.013, LIT)
    cv.seg((0.14, 0.165), (0.66, 0.165), 0.004, (0.22, 0.30, 0.36, 1))
    for i in range(10):
        cv.rrect(0.70 + i * 0.008, 0.165, 0.0025, 0.010, 0.001, LIT if i < 6 else GH)
    m = mat_print("DisplayArt", cv.image("DisplayArt"), rough=0.35, emit=1.6, coat=1.0, spec=0.2)
    M = Matrix.Translation((cx, FY0 + 0.045, cz))
    out.append(C.label_plane("Display", m, 2 * hw, 2 * hh, M))
    # dark tunnel walls between glass and the faceplate opening
    bm = bmesh.new()
    rrect_y(bm, cx, cz, hw + 0.026, hh + 0.026, 0.035, FY0 + 0.005, FY0 + 0.05)
    t = C.mesh_obj("Tunnel", bm, [glass_m])
    cb = bmesh.new()
    rrect_y(cb, cx, cz, hw, hh, 0.012, FY0 - 0.1, FY0 + 0.1)
    cut = C.mesh_obj("TunnelCut", cb, [])
    C.add_boolean(t, cut)
    out.append(C.finalize(t, angle=40, remove=[cut]))
    # satin-silver frame around the display opening
    bm = bmesh.new()
    rrect_y(bm, cx, cz, hw + 0.032, hh + 0.032, 0.04, FY0 - 0.006, FY0 + 0.01)
    fr = C.mesh_obj("DispFrame", bm, [satin])
    cb = bmesh.new()
    rrect_y(cb, cx, cz, hw + 0.016, hh + 0.016, 0.03, FY0 - 0.1, FY0 + 0.1)
    cut = C.mesh_obj("FrameCut", cb, [])
    C.add_boolean(fr, cut)
    C.add_bevel(fr, 0.004, segments=2, angle=30)
    out.append(C.finalize(fr, angle=40, remove=[cut]))
    return out


def knob(black, satin):
    x, z, R = KNOB
    out = []
    # bezel ring in the cup
    bz = C.lathe("Bezel", [(R + 0.005, -0.012, 0), (R + 0.032, -0.012, 0), (R + 0.032, 0.004, 0),
                           (R + 0.026, 0.012, 0), (R + 0.005, 0.012, 0)], [satin], steps=128)
    bz.matrix_world = Matrix.Translation((x, FY0, z)) @ RX
    out.append(C.finalize(bz, angle=40))

    def knurl(r, zz, t):
        if 0.02 < zz < 0.10 and r > R - 0.01:
            return r - 0.0045 * (0.5 + 0.5 * math.cos(48 * t)) ** 2
        return r
    P = [(0.0, 0.135, 1), (R - 0.03, 0.135, 0), (R - 0.022, 0.134, 1), (R - 0.004, 0.126, 1),
         (R, 0.112, 0), (R, 0.02, 0), (R - 0.006, 0.0, 0), (0.0, 0.0, 0)]
    kb = C.lathe("Knob", P, [black, satin], steps=192, mod=knurl)
    kb.matrix_world = Matrix.Translation((x, FY0, z)) @ RX
    out.append(C.finalize(kb, angle=40))
    # pointer dimple on the cap
    bm = bmesh.new()
    C.cyl_bm(bm, 0.009, 0.0, 0.004, seg=24,
             matrix=Matrix.Translation((x - 0.06 * math.sin(0.6), FY0 - 0.136, z + 0.06 * math.cos(0.6))) @ RX)
    out.append(C.mesh_obj("Pointer", bm, [black]))
    return out


def icon_canvas(w, h):
    return Canvas(w, h, 2400)


WHITE = (0.86, 0.86, 0.84, 1)


def buttons(btn, satin):
    out = []
    yb0, yb1 = FY0 - 0.026, FY0 + 0.01
    specs = []   # (cx, cz, hw, hh, r, kind)
    for i in range(6):
        specs.append((-0.3375 + i * 0.135, -0.17, 0.0625, 0.06, 0.018, "num%d" % (i + 1)))
    specs += [(-0.80, -0.17, 0.075, 0.06, 0.02, "src"), (-0.64, -0.17, 0.065, 0.06, 0.02, "mute"),
              (0.60, -0.17, 0.07, 0.06, 0.02, "phone"), (0.78, -0.17, 0.07, 0.06, 0.02, "menu"),
              (0.69, 0.245, 0.17, 0.032, 0.02, "eject"), (-0.71, 0.245, 0.17, 0.032, 0.02, "power")]
    bm = bmesh.new()
    for (cx, cz, hw, hh, r, kind) in specs:
        rrect_y(bm, cx, cz, hw, hh, r, yb0, yb1)
    out.append(solid("Buttons", bm, [btn], bevel=0.008, seg=3))
    # pictograms printed on the button faces (one alpha sheet)
    x0, x1, z0, z1 = -0.90, 0.90, -0.24, 0.29
    cv = Canvas(x1 - x0, z1 - z0, 1800)
    W = WHITE
    for (cx, cz, hw, hh, r, kind) in specs:
        u, v = cx - x0, cz - z0
        if kind.startswith("num"):
            seven(cv, kind[3], u - 0.012, v - 0.022, 0.022, 0.044, 0.0065, W, slant=0.08)
        elif kind == "src":
            cv.arc(u, v, 0.024, 120, 400, 0.006, W)
            cv.poly([(u - 0.020, v + 0.030), (u - 0.004, v + 0.020), (u - 0.020, v + 0.008)], W)
        elif kind == "mute":
            cv.poly([(u - 0.03, v - 0.01), (u - 0.015, v - 0.01), (u + 0.002, v - 0.026),
                     (u + 0.002, v + 0.026), (u - 0.015, v + 0.01), (u - 0.03, v + 0.01)], W)
            cv.seg((u + 0.012, v - 0.012), (u + 0.034, v + 0.012), 0.006, W)
            cv.seg((u + 0.012, v + 0.012), (u + 0.034, v - 0.012), 0.006, W)
        elif kind == "phone":
            cv.arc(u + 0.006, v - 0.006, 0.026, 100, 215, 0.011, W)
            cv.rrect(u - 0.004, v + 0.020, 0.012, 0.007, 0.004, W)
            cv.rrect(u - 0.021, v - 0.011, 0.007, 0.012, 0.004, W)
        elif kind == "menu":
            for k in (-1, 0, 1):
                cv.seg((u - 0.024, v + k * 0.016), (u + 0.024, v + k * 0.016), 0.006, W)
        elif kind == "eject":
            cv.poly([(u - 0.03, v - 0.002), (u + 0.03, v - 0.002), (u, v + 0.022)], W)
            cv.seg((u - 0.03, v - 0.016), (u + 0.03, v - 0.016), 0.007, W)
        elif kind == "power":
            cv.arc(u, v - 0.002, 0.018, 120, 420, 0.006, W)
            cv.seg((u, v + 0.004), (u, v + 0.024), 0.006, W)
    # rocker arrows (printed on the rocker ring, same plane depth)
    rx, rz, R = ROCK
    u, v = rx - x0, rz - z0
    for k in range(4):
        a = math.radians(90 * k)
        c, s = math.cos(a), math.sin(a)
        px, py = u + 0.105 * c, v + 0.105 * s
        cv.poly([(px + 0.018 * c, py + 0.018 * s), (px - 0.012 * c - 0.016 * s, py - 0.012 * s + 0.016 * c),
                 (px - 0.012 * c + 0.016 * s, py - 0.012 * s - 0.016 * c)], W)
    m = mat_print("ButtonPrint", cv.image("ButtonPrint"), rough=0.45)
    out.append(C.label_plane("Print", m, x1 - x0, z1 - z0,
                             Matrix.Translation(((x0 + x1) / 2, yb0 - 0.0012, (z0 + z1) / 2))))
    # four-way rocker: ring + centre button
    P = [(0.074, -0.004, 0), (0.074, 0.022, 0), (R - 0.02, 0.024, 0), (R - 0.004, 0.020, 0), (R, 0.010, 0),
         (R, -0.004, 0)]
    ring = C.lathe("Rocker", P, [btn], steps=160)
    ring.matrix_world = Matrix.Translation((rx, FY0, rz)) @ RX
    C.add_bevel(ring, 0.003, segments=1, angle=40)
    out.append(C.finalize(ring, angle=40))
    P = [(0.0, 0.034, 0), (0.05, 0.034, 0), (0.062, 0.03, 0), (0.066, 0.02, 0), (0.066, -0.004, 0), (0.0, -0.004, 0)]
    ok = C.lathe("RockOK", P, [satin], steps=96)
    ok.matrix_world = Matrix.Translation((rx, FY0, rz)) @ RX
    out.append(C.finalize(ok, angle=40))
    bz = C.lathe("RockBezel", [(R + 0.005, -0.012, 0), (R + 0.03, -0.012, 0), (R + 0.03, 0.004, 0),
                               (R + 0.024, 0.010, 0), (R + 0.005, 0.010, 0)], [satin], steps=128)
    bz.matrix_world = Matrix.Translation((rx, FY0, rz)) @ RX
    out.append(C.finalize(bz, angle=40))
    return out


# ----------------------------------------------------------------- chassis
def chassis(zinc, pcb, black, pins, brass):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 2 * CHW, CY1 - 0.02, 2 * CHH, center=(0, (CY1 + 0.02) / 2, 0))
    ob = C.mesh_obj("Chassis", bm, [zinc])
    so = ob.modifiers.new("Shell", "SOLIDIFY")
    so.thickness = 0.012
    so.offset = -1

    def cuts(cb):
        # top vent slots (two fields)
        for row in range(2):
            for i in range(12):
                x = -0.66 + i * 0.12
                y = 0.55 + row * 0.42
                C.box_bm(cb, 0.026, 0.30, 0.2, center=(x, y, CHH))
        # side clip holes and windows
        for sx in (-1, 1):
            for y in (0.16, 0.42, 0.68):
                C.cyl_bm(cb, 0.026, -0.1, 0.1, seg=24,
                         matrix=Matrix.Translation((sx * CHW, y, 0.10)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
            C.box_bm(cb, 0.1, 0.36, 0.10, center=(sx * CHW, 1.15, -0.06))
        # rear openings for the connectors
        C.box_bm(cb, 0.88, 0.2, 0.20, center=(0.05, CY1, -0.06))
    cut = cutter("ChassisCut", cuts)
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    out.append(C.finalize(ob, angle=38, remove=[cut]))
    # embossed stiffening ribs on the top (between vent fields)
    bm = bmesh.new()
    for x in (-0.78, 0.78):
        C.box_bm(bm, 0.05, 1.10, 0.012, center=(x, 0.95, CHH + 0.004))
    out.append(solid("Ribs", bm, [zinc], bevel=0.005))
    # green PCB inside, seen through the slots
    bm = bmesh.new()
    C.box_bm(bm, 2 * CHW - 0.06, CY1 - 0.1, 0.016, center=(0, CY1 / 2 + 0.03, 0.06))
    for i in range(14):
        C.box_bm(bm, 0.08, 0.05, 0.05, center=(-0.7 + 0.11 * i, 0.5 + 0.07 * (i % 5), 0.09))
    out.append(C.mesh_obj("PCB", bm, [pcb]))
    # ISO connector blocks on the back
    for (cx, w) in ((-0.17, 0.40), (0.27, 0.40)):
        bm = bmesh.new()
        C.box_bm(bm, w, 0.16, 0.17, center=(cx, CY1 + 0.04, -0.06))
        sh = C.mesh_obj("ISO", bm, [black])
        cb = bmesh.new()
        C.box_bm(cb, w - 0.04, 0.2, 0.13, center=(cx, CY1 + 0.17, -0.06))
        c2 = C.mesh_obj("ISOCut", cb, [])
        C.add_boolean(sh, c2)
        C.add_bevel(sh, 0.005, segments=2, angle=30)
        out.append(C.finalize(sh, angle=38, remove=[c2]))
        bm = bmesh.new()
        for r in range(2):
            for k in range(4):
                C.box_bm(bm, 0.022, 0.08, 0.008, center=(cx - 0.13 + k * 0.087, CY1 + 0.05, -0.095 + 0.07 * r))
        out.append(C.mesh_obj("ISOPins", bm, [pins]))
    # antenna socket
    P = [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.05, 0.03, 0), (0.035, 0.035, 0), (0.035, 0.13, 0), (0.012, 0.13, 0),
         (0.012, 0.10, 0), (0.0, 0.10, 0)]
    an = C.lathe("Antenna", P, [brass], steps=48)
    an.matrix_world = Matrix.Translation((0.68, CY1, 0.06)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    out.append(C.finalize(an, angle=40))
    # heat sink on the back, left
    bm = bmesh.new()
    C.box_bm(bm, 0.40, 0.03, 0.40, center=(-0.6, CY1 + 0.015, 0.0))
    for i in range(9):
        C.box_bm(bm, 0.016, 0.10, 0.38, center=(-0.78 + 0.045 * i, CY1 + 0.06, 0.0))
    out.append(solid("HeatSink", bm, [black], bevel=0.004))
    # rear support stud
    P = [(0.0, 0.0, 0), (0.06, 0.0, 0), (0.06, 0.04, 0), (0.025, 0.045, 0), (0.025, 0.20, 0), (0.0, 0.205, 0)]
    st = C.lathe("Stud", P, [zinc], steps=32)
    st.matrix_world = Matrix.Translation((0.68, CY1, -0.14)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    out.append(C.finalize(st, angle=40))
    return out


def build():
    black = C.principled("FaceSoftTouch", (0.018, 0.018, 0.019), rough=0.55)
    C.add_noise_bump(black, scale=800, strength=0.18, distance=0.0005, detail=4.0, rough_var=0.06)
    gloss = C.principled("PianoBlack", (0.008, 0.008, 0.009), rough=0.12, Coat_Weight=0.6)
    btn = C.principled("ButtonPC", (0.022, 0.022, 0.024), rough=0.38)
    C.add_noise_bump(btn, scale=1200, strength=0.05, distance=0.0003)
    satin = mat_satin()
    glass_m = C.principled("Tunnel", (0.01, 0.01, 0.012), rough=0.5)
    zinc = mat_zinc()
    pcb = C.principled("PCB", C.srgb("#1F4A2C"), rough=0.4)
    conn = C.mat_black_plastic("ConnPA", rough=0.6, color=0.03)
    pins = C.principled("PinTin", (0.75, 0.72, 0.62), metallic=1.0, rough=0.3)
    brass = C.principled("NickelBrass", (0.70, 0.68, 0.62), metallic=1.0, rough=0.22)
    objs = faceplate(black, gloss) + display(glass_m, satin) + knob(btn, satin) + buttons(btn, satin)
    objs += chassis(zinc, pcb, conn, pins, brass)
    im = C.label_image("RadioLabel", 1024, 640, seed=11)
    M = Matrix.Translation((0.28, 1.30, CHH + 0.0015)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    objs.append(C.label_plane("Label", C.mat_label(im), 0.46, 0.30, M))
    return objs


def matte_floor_in_reflections():
    """Keep the white shadow-catcher out of glossy reflections (it greys out the display)."""
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
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("autoradio", objs, "autoradio.py",
            "1-DIN car radio head unit: black faceplate with segment display, CD slot, volume knob, preset and "
            "function buttons, zinc-plated steel chassis with vents, ISO connectors and antenna socket on the back",
            az=-30, el=24, lens=70, fill=0.86, **kw)
