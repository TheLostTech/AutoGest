"""Manual gear shifter assembly (leva del cambio) as removed from the car: black leather
gear knob with satin-silver collar and top ring and a gloss-black top insert printed with
the 5-speed + reverse shift pattern, a stitched black leather gaiter with soft folds
clipped into a grained plastic frame, the black moulded shifter tower on a bolt-down
flange with steel-sleeved holes, and the select / shift bowden cables (sheaths, steel
abutment bracket, inner rods with ball sockets). No text or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))

# units: 1 = 10 cm, Z up, driver side towards -Y.
TW, TD, TH = 0.62, 0.80, 0.80     # tower half width (x), half depth (y), height
FZ0, FZ1 = 0.80, 0.90             # frame bottom / top
GZ0, GZ1 = 0.82, 2.22             # gaiter bottom / top
KZ0 = 2.20                        # knob collar bottom

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


GL = {
    "1": [[(.12, .78), (.36, 1), (.36, 0)]],
    "2": [[(0, .8), (.12, 1), (.48, 1), (.6, .86), (.6, .64), (0, 0), (.62, 0)]],
    "3": [[(0, .88), (.12, 1), (.48, 1), (.6, .88), (.6, .64), (.48, .53), (.2, .53)],
          [(.48, .53), (.6, .42), (.6, .12), (.48, 0), (.12, 0), (0, .12)]],
    "4": [[(.46, 0), (.46, 1), (0, .3), (.64, .3)]],
    "5": [[(.58, 1), (.06, 1), (0, .56), (.44, .58), (.6, .45), (.6, .13), (.48, 0), (.12, 0), (0, .12)]],
    "R": [[(0, 0), (0, 1), (.42, 1), (.58, .86), (.58, .64), (.42, .5), (0, .5)], [(.3, .5), (.6, 0)]],
}


def glyph(cv, ch, cx, cy, h, wd, col):
    for poly in GL[ch]:
        cv.line([(cx + (u - 0.3) * h, cy + (v - 0.5) * h) for u, v in poly], wd, col)


def rrect_z(bm, cx, cy, hw, hh, r, z0, z1, n=8, mat=0):
    """Rounded-rectangle prism in the XY plane from z0 to z1."""
    fs = rrect_y(bm, cx, cy, hw, hh, r, z0, z1, n=n, mat=mat)
    vs = list({v for f in fs for v in f.verts})
    for v in vs:
        x, y, z = v.co
        v.co = (x, z, y)
    bmesh.ops.reverse_faces(bm, faces=fs)
    return fs


# ----------------------------------------------------------------- materials
def mat_leather(name, base=0.024, rough=0.46, stitch=True):
    """Fine pebbled leather; optional double-row grey stitching along the 4 UV seams."""
    m = C.principled(name, (base, base, base * 1.02), rough=rough, Sheen_Weight=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = 140.0
    vo.feature = "F1"
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 9.0
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.10
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(vo.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if not stitch:
        return m

    def math_node(op, a=None, bval=None, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, bval)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt, "UV"), sep.inputs[0])
    u, v = sep.outputs["X"], sep.outputs["Y"]
    su = math_node("MULTIPLY", u, 4.0)
    su = math_node("ADD", su, 0.5)
    fr = math_node("FRACT", su)
    d = math_node("ABSOLUTE", math_node("SUBTRACT", fr, 0.5))          # 0 on the seam
    row = math_node("ABSOLUTE", math_node("SUBTRACT", d, 0.022))       # distance to stitch rows
    rowm = math_node("LESS_THAN", row, 0.0045)
    dash = math_node("SINE", math_node("MULTIPLY", v, 2 * math.pi * 38.0))
    dashm = math_node("GREATER_THAN", dash, -0.1)
    mask = math_node("MULTIPLY", rowm, dashm)
    groove = math_node("LESS_THAN", d, 0.004)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mask, mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.02, 1)
    mix.inputs["B"].default_value = (0.20, 0.20, 0.20, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    h = math_node("SUBTRACT", math_node("ADD", math_node("MULTIPLY", mask, 1.0),
                                        math_node("MULTIPLY", vo.outputs["Distance"], 0.25)),
                  math_node("MULTIPLY", groove, 0.8))
    nt.links.new(h, bump.inputs["Height"])
    bump.inputs["Distance"].default_value = 0.0015
    return m


# ----------------------------------------------------------------- gaiter
def gaiter(leather):
    NU, NV = 192, 90
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for j in range(NV + 1):
        v = j / NV
        s = 1 - (1 - v) ** 2.2                        # concave flanks
        a = TW - 0.025 + (0.165 - (TW - 0.025)) * s
        bb = TD - 0.07 + (0.165 - (TD - 0.07)) * s
        n = 7.0 + (2.0 - 7.0) * min(1.0, v * 1.4)
        z = GZ0 + (GZ1 - GZ0) * v
        lean = 0.03 * math.sin(math.pi * v)
        row = []
        for i in range(NU):
            u = i / NU
            t = math.tau * u + math.pi / 4
            c, si = math.cos(t), math.sin(t)
            x = a * math.copysign(abs(c) ** (2 / n), c)
            y = bb * math.copysign(abs(si) ** (2 / n), si)
            # folds: compression rings (stronger low down) wandering around the boot + slack
            env = (1 - v) ** 0.7 * min(1.0, v * 12)
            ph = 0.35 * math.sin(2 * t + 1.1) + 0.2 * math.sin(3 * t + 0.4)
            f = 0.085 * env * math.sin(math.tau * (v * 4.6 + ph)) ** 3
            f += 0.035 * env * math.sin(math.tau * (v * 7.3 + 0.6 * math.sin(3 * t + 2.0)))
            f += 0.03 * math.sin(5 * t + 7 * v) * env + 0.02 * math.sin(9 * t - 11 * v) * env
            # seam pinch at u = k/4 (the boot is sewn from four panels)
            dseam = abs(((u * 4 + 0.5) % 1.0) - 0.5)
            f -= 0.010 * math.exp(-(dseam / 0.012) ** 2) * min(1.0, v * 6)
            k = 1 + f
            row.append(bm.verts.new((x * k, y * k + lean, z)))
        rows.append(row)
    for j in range(NV):
        for i in range(NU):
            i2 = (i + 1) % NU
            f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            for l, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (uu / NU, vv / NV * 1.6)
    bm.normal_update()
    # outward normals
    cen = Vector((0, 0, (GZ0 + GZ1) / 2))
    tot = sum((f.calc_center_median() - Vector((0, 0, f.calc_center_median().z))).dot(f.normal) for f in bm.faces)
    if tot < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = C.mesh_obj("Gaiter", bm, [leather])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.014
    so.offset = -1
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    return C.finalize(ob, angle=80)


# ----------------------------------------------------------------- knob
def knob(leather, satin, gloss):
    out = []
    z0 = KZ0
    P = [(0.0, z0, 0), (0.168, z0, 0), (0.168, z0 + 0.09, 0), (0.160, z0 + 0.10, 0), (0.0, z0 + 0.10, 0)]
    col = C.lathe("Collar", P, [satin], steps=128)
    C.add_bevel(col, 0.006, segments=2, angle=30)
    out.append(C.finalize(col, angle=40))
    # leather body: waisted neck flaring into a rounded head
    prof = [(0.0, z0 + 0.09), (0.150, z0 + 0.09), (0.150, z0 + 0.11), (0.165, z0 + 0.15), (0.205, z0 + 0.21),
            (0.252, z0 + 0.28), (0.278, z0 + 0.34), (0.282, z0 + 0.39), (0.274, z0 + 0.435), (0.258, z0 + 0.465),
            (0.240, z0 + 0.478)]
    P = [(r, z, 0) for r, z in prof] + [(0.0, z0 + 0.478, 0)]
    kb = C.lathe("Knob", P, [leather], steps=160)
    sub = kb.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    out.append(C.finalize(kb, angle=50))
    ZT = z0 + 0.485
    # satin ring around the top insert
    P = [(0.200, z0 + 0.470, 0), (0.244, z0 + 0.472, 0), (0.248, ZT, 0), (0.240, ZT + 0.012, 0),
         (0.200, ZT + 0.012, 0)]
    rg = C.lathe("TopRing", P, [satin], steps=160)
    C.add_bevel(rg, 0.003, segments=2, angle=30)
    out.append(C.finalize(rg, angle=40))
    P = [(0.0, z0 + 0.47, 0), (0.202, z0 + 0.47, 0), (0.202, ZT + 0.004, 0), (0.0, ZT + 0.008, 0)]
    ins = C.lathe("Insert", P, [gloss], steps=128)
    out.append(C.finalize(ins, angle=40))
    # printed shift pattern (gear 1 top-left ... R bottom-right)
    S = 0.40
    cv = Canvas(S, S, 3000)
    W = (0.92, 0.92, 0.90, 1)
    c = S / 2
    dx, dy, lw = 0.075, 0.062, 0.0085
    cv.seg((c - dx, c), (c + dx, c), lw, W)
    for k in (-1, 0, 1):
        cv.seg((c + k * dx, c - dy), (c + k * dx, c + dy), lw, W)
    gh = 0.045
    for ch, k, sgn in (("1", -1, 1), ("2", -1, -1), ("3", 0, 1), ("4", 0, -1), ("5", 1, 1), ("R", 1, -1)):
        glyph(cv, ch, c + k * dx, c + sgn * (dy + 0.012 + gh / 2), gh, 0.0085, W)
    m = mat_print("PatternPrint", cv.image("Pattern"), rough=0.3)
    M = Matrix.Translation((0, 0, ZT + 0.0085)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.label_plane("Pattern", m, S, S, M))
    return out


# ----------------------------------------------------------------- frame + tower
def frame(black, satin):
    out = []
    bm = bmesh.new()
    rrect_z(bm, 0, 0, TW + 0.17, TD + 0.17, 0.16, FZ0, FZ1)
    cb = bmesh.new()
    rrect_z(cb, 0, 0, TW - 0.005, TD - 0.005, 0.12, FZ0 - 0.1, FZ1 + 0.1)
    cut = C.mesh_obj("FrameCut", cb, [])
    out.append(solid("Frame", bm, [black], bevel=0.02, seg=3, cutters=[cut]))
    bm = bmesh.new()
    rrect_z(bm, 0, 0, TW + 0.02, TD + 0.02, 0.13, FZ1 - 0.01, FZ1 + 0.012)
    cb = bmesh.new()
    rrect_z(cb, 0, 0, TW - 0.004, TD - 0.004, 0.12, FZ0 - 0.1, FZ1 + 0.1)
    cut = C.mesh_obj("LipCut", cb, [])
    out.append(solid("FrameLip", bm, [satin], bevel=0.004, seg=2, cutters=[cut]))
    return out


def tower(black, zinc):
    out = []
    bm = bmesh.new()
    rrect_z(bm, 0, 0, TW - 0.04, TD - 0.06, 0.08, 0.06, FZ0 + 0.01)
    out.append(solid("Tower", bm, [black], bevel=0.012))
    # vertical moulding ribs on the visible faces
    bm = bmesh.new()
    for x in (-0.36, -0.12, 0.12, 0.36):
        C.box_bm(bm, 0.035, 0.05, FZ0 - 0.14, center=(x, -(TD - 0.06) - 0.012, (FZ0 + 0.06) / 2 + 0.02))
    for y in (-0.45, -0.15, 0.15, 0.45):
        C.box_bm(bm, 0.05, 0.035, FZ0 - 0.14, center=((TW - 0.04) + 0.012, y, (FZ0 + 0.06) / 2 + 0.02))
    out.append(solid("TowerRibs", bm, [black], bevel=0.008))
    # base flange with four bolt tabs
    bm = bmesh.new()
    rrect_z(bm, 0, 0, TW + 0.12, TD + 0.08, 0.10, 0.0, 0.065)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rrect_z(bm, sx * (TW + 0.17), sy * (TD - 0.15), 0.13, 0.11, 0.08, 0.0, 0.065)
    cb = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            C.cyl_bm(cb, 0.045, -0.1, 0.2, seg=32, matrix=Matrix.Translation((sx * (TW + 0.22), sy * (TD - 0.15), 0)))
    cut = C.mesh_obj("FlangeCut", cb, [])
    fl = C.mesh_obj("Flange", bm, [black])
    C.add_boolean(fl, cut).use_self = True
    C.add_bevel(fl, 0.01, segments=2, angle=30)
    out.append(C.finalize(fl, angle=38, remove=[cut]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            sl = C.lathe("Sleeve", [(0.030, -0.004, 0), (0.048, -0.004, 0), (0.048, 0.075, 0), (0.030, 0.075, 0)],
                         [zinc], steps=40)
            sl.matrix_world = Matrix.Translation((sx * (TW + 0.22), sy * (TD - 0.15), 0))
            C.add_bevel(sl, 0.004, segments=1, angle=40)
            out.append(C.finalize(sl, angle=40))
    return out


def frames_along(pts, sec):
    out = []
    n = len(pts)
    prevU = None
    for i, P in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prevU is None:
            U = T.cross(Vector((0, 0, 1)))
            if U.length < 1e-4:
                U = T.cross(Vector((1, 0, 0)))
        else:
            U = prevU - T * prevU.dot(T)
        U.normalize()
        V = T.cross(U).normalized()
        prevU = U
        out.append((P, U, V, sec))
    return out


def bezier(p0, p1, p2, p3, n):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        pts.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return pts


def cables(sheath, zinc, chrome, black):
    out = []
    xb = TW + 0.45                    # abutment bracket plane
    # stamped steel abutment bracket bolted to the flange
    bm = bmesh.new()
    C.box_bm(bm, 0.04, 0.80, 0.42, center=(xb, 0.0, 0.27))
    C.box_bm(bm, 0.30, 0.80, 0.04, center=(xb - 0.13, 0.0, 0.08))
    cb = bmesh.new()
    for y in (-0.2, 0.2):
        C.box_bm(cb, 0.2, 0.075, 0.2, center=(xb, y, 0.40))
    cut = C.mesh_obj("BrCut", cb, [])
    out.append(solid("Bracket", bm, [zinc], bevel=0.008, cutters=[cut]))
    Rz = Matrix.Rotation(math.pi / 2, 4, "Y")    # local +Z -> world +X
    for k, y in enumerate((-0.2, 0.2)):
        zc = 0.36
        # inner rod from the tower selector arm to the bracket, ending in a ball socket
        bm = bmesh.new()
        C.cyl_bm(bm, 0.012, TW - 0.05, xb, seg=16, matrix=Matrix.Translation((0, y, zc)) @ Rz @ Matrix.Translation((0, 0, 0)))
        rod = C.mesh_obj("Rod", bm, [chrome])
        out.append(rod)
        P = [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.06, 0.03, 0), (0.06, 0.10, 0), (0.035, 0.13, 0), (0.0, 0.13, 0)]
        so = C.lathe("Socket", P, [black], steps=40)
        so.matrix_world = Matrix.Translation((TW + 0.03, y, zc)) @ Rz
        out.append(C.finalize(so, angle=40))
        # metal ferrule + plastic clip held in the bracket
        P = [(0.0, -0.05, 0), (0.05, -0.05, 0), (0.05, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.05, 0), (0.045, 0.07, 0),
             (0.045, 0.16, 0), (0.0, 0.16, 0)]
        cl = C.lathe("Clip", P, [black], steps=40)
        cl.matrix_world = Matrix.Translation((xb, y, zc)) @ Rz
        out.append(C.finalize(cl, angle=40))
        P = [(0.0, 0.16, 0), (0.042, 0.16, 0), (0.042, 0.30, 0), (0.036, 0.31, 0), (0.0, 0.31, 0)]
        fe = C.lathe("Ferrule", P, [zinc], steps=40)
        fe.matrix_world = Matrix.Translation((xb, y, zc)) @ Rz
        out.append(C.finalize(fe, angle=40))
        # sheath: out along +X, down to the floor and towards the viewer
        p0 = Vector((xb + 0.30, y, zc))
        p3 = Vector((xb + 0.95 + 0.22 * k, -0.9 - 0.25 * k, 0.045))
        pts = bezier(p0, p0 + Vector((0.55, 0, 0)), p3 + Vector((0.05, 0.75, 0.0)), p3, 48)
        sec = [(0.036 * math.cos(math.tau * i / 16), 0.036 * math.sin(math.tau * i / 16)) for i in range(16)]
        bm = bmesh.new()
        C.sweep(bm, frames_along(pts, sec), cap=True)
        sh = C.mesh_obj("Sheath", bm, [sheath])
        out.append(C.finalize(sh, angle=60))
        # far end: ferrule + inner cable end with a black ball socket
        T = (pts[-1] - pts[-2]).normalized()
        M = Matrix.Translation(pts[-1]) @ T.to_track_quat("Z", "X").to_matrix().to_4x4()
        P = [(0.0, -0.02, 0), (0.044, -0.02, 0), (0.044, 0.10, 0), (0.03, 0.11, 0), (0.012, 0.11, 0),
             (0.012, 0.30, 0), (0.0, 0.30, 0)]
        en = C.lathe("End", P, [zinc], steps=32)
        en.matrix_world = M
        out.append(C.finalize(en, angle=40))
        P = [(0.0, 0.28, 0), (0.045, 0.28, 0), (0.055, 0.31, 0), (0.055, 0.40, 0), (0.035, 0.43, 0), (0.0, 0.43, 0)]
        eb = C.lathe("EndSocket", P, [black], steps=32)
        eb.matrix_world = M
        out.append(C.finalize(eb, angle=40))
    return out


def build():
    leather = mat_leather("GaiterLeather", base=0.026)
    knob_l = mat_leather("KnobLeather", base=0.022, rough=0.42, stitch=False)
    satin = mat_satin()
    gloss = C.principled("InsertBlack", (0.01, 0.01, 0.011), rough=0.14, Coat_Weight=0.8)
    black = C.principled("FramePP", (0.020, 0.020, 0.021), rough=0.6)
    C.add_noise_bump(black, scale=650, strength=0.32, distance=0.0006, detail=4.0, rough_var=0.07)
    tower_m = C.mat_black_plastic("TowerPA", rough=0.55, color=0.03)
    zinc = C.principled("ZincSteel", (0.60, 0.61, 0.62), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005, rough_var=0.05)
    chrome = C.principled("RodSteel", (0.75, 0.75, 0.76), metallic=1.0, rough=0.15)
    sheath = C.principled("SheathPE", (0.018, 0.018, 0.019), rough=0.4)
    C.add_noise_bump(sheath, scale=500, strength=0.05, distance=0.0004)
    objs = [gaiter(leather)] + knob(knob_l, satin, gloss) + frame(black, satin) + tower(tower_m, zinc)
    objs += cables(sheath, zinc, chrome, tower_m)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("leva-cambio", objs, "leva-cambio.py",
            "manual gear shifter: leather gear knob with 5-speed pattern on top, stitched leather gaiter in a "
            "plastic frame, shifter tower on a bolt-down flange, select and shift cables",
            az=30, el=24, lens=70, fill=0.86, **kw)
