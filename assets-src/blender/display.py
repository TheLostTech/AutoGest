"""Infotainment display unit (display / schermo navigatore), 8 inch: flush dark glass
touchscreen showing a simple generic home screen (map tile with route, media, phone,
vehicle and settings tiles, status bar), gloss-black bezel with two knurled rotary knobs
and a column of hard keys with pictograms on each side; behind, the black steel housing
with heat-sink fins, zinc mounting brackets and the connectors (main multi-pin block and
coloured coaxial sockets). No brand or text."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
RX = Matrix.Rotation(math.radians(90), 4, "X")   # local +Z -> world -Y
FAST = bool(os.environ.get("FAST"))


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


def arrow(cv, pts, wd, col, head=0.018):
    cv.line(pts, wd, col)
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1
    ux, uy = (bx - ax) / L, (by - ay) / L
    cv.poly([(bx + ux * head * 0.9, by + uy * head * 0.9),
             (bx - uy * head * 0.7, by + ux * head * 0.7),
             (bx + uy * head * 0.7, by - ux * head * 0.7)], col)


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


def print_plane(name, im, w, h, M, rough=0.4, emit=0.0, coat=0.0, spec=0.5):
    """Decal plane in local XZ facing -Y (C.label_plane) with alpha artwork."""
    return C.label_plane(name, mat_print(name + "M", im, rough=rough, emit=emit, coat=coat, spec=spec), w, h, M)


# ----------------------------------------------------------------- materials
def mat_satin(name="SatinSilver"):
    m = C.principled(name, (0.66, 0.66, 0.67), metallic=1.0, rough=0.24)
    C.add_noise_bump(m, scale=1400, strength=0.03, distance=0.0003, rough_var=0.04)
    return m


def mat_cast_alu(name, base=0.50, rough=0.45, grain=520.0, wear=0.35):
    """Die-cast aluminium: mottled tone, fine sand-cast grain, brighter worn edges."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 6.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.86, base * 0.86, base * 0.85, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.80, 0.80, 0.80, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.06
    rr.inputs["To Max"].default_value = rough - 0.06
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    rmix = nt.nodes.new("ShaderNodeMix")
    nt.links.new(wmul.outputs[0], rmix.inputs["Factor"])
    nt.links.new(rr.outputs["Result"], rmix.inputs["A"])
    rmix.inputs["B"].default_value = 0.22
    nt.links.new(rmix.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_brushed(name, base=0.55, rough=0.28, axis=(1.0, 60.0, 60.0), strength=0.08):
    """Extruded / brushed aluminium: fine streaks along one axis (noise stretched)."""
    m = C.principled(name, (base, base, base * 0.99), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = axis
    nt.links.new(C._coord(nt), mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40.0
    nz.inputs["Detail"].default_value = 8.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.05
    rr.inputs["To Max"].default_value = rough + 0.05
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 5.0
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.9, base * 0.9, base * 0.89, 1)
    col.inputs["B"].default_value = (base * 1.05, base * 1.05, base * 1.04, 1)
    nt.links.new(col.outputs["Result"], b.inputs["Base Color"])
    return m


def plastic(name, hexcol, rough=0.45, bump=0.06, scale=900):
    m = C.principled(name, C.srgb(hexcol), rough=rough)
    if bump:
        C.add_noise_bump(m, scale=scale, strength=bump, distance=0.0005, rough_var=0.05)
    return m


def set_input(m, key, val):
    C._set(next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), key, val)


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
        m = C.add_boolean(ob, c)
        try:
            m.use_self = True
            m.use_hole_tolerant = True
        except Exception:
            pass
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=angle)
    return C.finalize(ob, angle=38, remove=list(cutters))


def cutter(name, fill):
    bm = bmesh.new()
    fill(bm)
    return C.mesh_obj(name, bm, [])


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(TAU * k / n), cy + r * math.sin(TAU * k / n)) for k in range(n)]


def rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    for x, y, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + x + r * math.cos(a), cy + y + r * math.sin(a)))
    return pts


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


def prism(name, poly, z0, z1, mat, M=None, bevel=0.005, holes=(), seg=2, finalize=True):
    """Extrude a 2D polygon (ccw) along local Z, optional boolean holes [(r, cx, cy)] through it."""
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
    if not finalize:
        return ob
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


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


def lathe_at(name, prof, mats, M, steps=64, angle=40, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def tube(name, pts, r, mat, res=3, caps=True, M=None):
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
    if M is not None:
        ob.matrix_world = M
    return C.finalize(ob, angle=50)


def frame_matrix(P, X, Z):
    X, Z = X.normalized(), Z.normalized()
    Y = Z.cross(X)
    return Matrix(((X.x, Y.x, Z.x, P.x), (X.y, Y.y, Z.y, P.y), (X.z, Y.z, Z.z, P.z), (0, 0, 0, 1)))


def matte_floor_in_reflections():
    """Keep the white shadow-catcher out of glossy reflections (it greys out dark glass)."""
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


def fast_kw():
    return dict(res=(512, 512), samples=32) if FAST else {}


SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


def seven(cv, ch, x, y, w, h, t, col, ghost=None, slant=0.0):
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


def number(cv, s, cx, cy, h, t, col):
    w = h * 0.5
    x = cx - (len(s) * w * 1.5 - w * 0.5) / 2
    for ch in s:
        seven(cv, ch, x, cy - h / 2, w, h, t, col)
        x += w * 1.5


def drop(objs, x=None, y=None, z=0.0):
    """Translate a group so its lowest point rests on z (optionally move to x, y)."""
    bpy.context.view_layer.update()
    ps = [(o.matrix_world @ v.co) for o in objs for v in o.data.vertices]
    dx = 0.0 if x is None else x - (min(p.x for p in ps) + max(p.x for p in ps)) / 2
    dy = 0.0 if y is None else y - (min(p.y for p in ps) + max(p.y for p in ps)) / 2
    C.transform_all(objs, T((dx, dy, z - min(p.z for p in ps))))


# units: 1 = 10 cm.  Glass front at -Y.
FHW, FHH = 1.20, 0.68          # bezel half width / height
FY0, FY1 = -0.10, 0.0
SHW, SHH = 0.88, 0.52          # screen (active) half width / height
SX = 0.0
KX = 1.04                      # knob / key column x
HY1 = 0.62
WHITE = (0.86, 0.86, 0.84, 1)


def ui_image():
    w, h = 2 * SHW, 2 * SHH
    cv = Canvas(w, h, 900, bg=(0.012, 0.018, 0.03, 1))
    TILE = (0.045, 0.06, 0.085, 1)
    ACC = (0.25, 0.62, 0.95, 1)
    ICON = (0.80, 0.84, 0.88, 1)
    # status bar: clock + signal + temperature dots
    x = 0.08
    for ch in "1230":
        seven(cv, ch, x, h - 0.085, 0.022, 0.044, 0.006, ICON)
        x += 0.034 + (0.016 if ch == "2" else 0.0)
    cv.ring(0.155, h - 0.072, 0.0, 0.004, ICON)
    cv.ring(0.155, h - 0.054, 0.0, 0.004, ICON)
    for i in range(4):
        cv.rrect(w - 0.20 + i * 0.022, h - 0.07 + i * 0.006, 0.006, 0.010 + i * 0.006, 0.002, ICON)
    cv.seg((0.05, h - 0.12), (w - 0.05, h - 0.12), 0.003, (0.10, 0.13, 0.18, 1))
    # map tile
    mx0, my0, mx1, my1 = 0.06, 0.06, 0.98, h - 0.16
    cv.rrect((mx0 + mx1) / 2, (my0 + my1) / 2, (mx1 - mx0) / 2, (my1 - my0) / 2, 0.03, (0.06, 0.075, 0.09, 1))
    roads = [[(0.08, 0.20), (0.40, 0.32), (0.62, 0.30), (0.96, 0.44)], [(0.30, 0.08), (0.36, 0.40), (0.34, 0.80)],
             [(0.10, 0.62), (0.50, 0.58), (0.90, 0.72)], [(0.66, 0.08), (0.70, 0.50), (0.80, 0.82)],
             [(0.12, 0.40), (0.30, 0.46)]]
    for r in roads:
        cv.line(r, 0.016, (0.16, 0.18, 0.21, 1))
    cv.rrect(0.20, 0.72, 0.07, 0.05, 0.01, (0.07, 0.14, 0.10, 1))
    cv.rrect(0.52, 0.16, 0.08, 0.04, 0.01, (0.06, 0.10, 0.16, 1))
    route = [(0.36, 0.12), (0.37, 0.36), (0.50, 0.58), (0.70, 0.62), (0.75, 0.80)]
    cv.line(route, 0.020, ACC)
    cv.poly([(0.36, 0.17), (0.335, 0.10), (0.36, 0.115), (0.385, 0.10)], (0.95, 0.95, 0.95, 1))
    # right tiles 2x2
    tx0 = 1.04
    tw, th = (w - 0.06 - tx0 - 0.03) / 2, (my1 - my0 - 0.03) / 2
    centres = []
    for r in range(2):
        for c in range(2):
            cx = tx0 + tw / 2 + c * (tw + 0.03)
            cy = my0 + th / 2 + (1 - r) * (th + 0.03)
            cv.rrect(cx, cy, tw / 2, th / 2, 0.03, TILE)
            centres.append((cx, cy))
    # media: note
    cx, cy = centres[0]
    cv.ring(cx - 0.03, cy - 0.04, 0.0, 0.026, ICON)
    cv.seg((cx - 0.006, cy - 0.04), (cx - 0.006, cy + 0.07), 0.012, ICON)
    cv.poly([(cx - 0.012, cy + 0.075), (cx + 0.06, cy + 0.05), (cx + 0.06, cy + 0.02), (cx - 0.012, cy + 0.04)], ICON)
    # phone handset
    cx, cy = centres[1]
    cv.arc(cx + 0.01, cy - 0.01, 0.055, 100, 215, 0.024, ICON)
    cv.rrect(cx - 0.005, cy + 0.045, 0.024, 0.014, 0.008, ICON)
    cv.rrect(cx - 0.052, cy - 0.022, 0.014, 0.024, 0.008, ICON)
    # vehicle: car front
    cx, cy = centres[2]
    cv.line([(cx - 0.07, cy - 0.02), (cx - 0.05, cy + 0.04), (cx + 0.05, cy + 0.04), (cx + 0.07, cy - 0.02),
             (cx + 0.07, cy - 0.06), (cx - 0.07, cy - 0.06)], 0.012, ICON, closed=True)
    for sx in (-1, 1):
        cv.ring(cx + sx * 0.042, cy - 0.032, 0.0, 0.011, ICON)
    # settings: gear
    cx, cy = centres[3]
    cv.ring(cx, cy, 0.024, 0.05, ICON)
    for k in range(8):
        a = TAU * k / 8
        cv.seg((cx + 0.045 * math.cos(a), cy + 0.045 * math.sin(a)), (cx + 0.068 * math.cos(a), cy + 0.068 * math.sin(a)),
               0.024, ICON)
    # accent bar under the first tile
    cv.rrect(centres[0][0], centres[0][1] - th / 2 + 0.02, tw / 2 - 0.05, 0.006, 0.003, ACC)
    return cv.image("UI")


def bezel(gloss, black):
    out = []
    bm = bmesh.new()
    rrect_y(bm, 0, 0, FHW, FHH, 0.08, FY0, FY1, n=8)
    out.append(solid("Bezel", bm, [gloss], bevel=0.018, seg=3))
    # thin matte rim round the edge of the front
    bm = bmesh.new()
    rrect_y(bm, 0, 0, FHW + 0.006, FHH + 0.006, 0.084, FY0 + 0.025, FY1, n=8)
    out.append(solid("Rim", bm, [black], bevel=0.01, seg=2))
    # screen: emissive UI under the glass, then the cover glass layer
    im = ui_image()
    out.append(print_plane("Screen", im, 2 * SHW, 2 * SHH, T((SX, FY0 - 0.0012, 0.0)), rough=0.06, emit=1.1, coat=1.0,
                           spec=0.3))
    # black mask frame between the active area and the bezel edge (inside the glass)
    cv = Canvas(2 * FHW - 0.06, 2 * FHH - 0.06, 400)
    cv.rrect(FHW - 0.03, FHH - 0.03, FHW - 0.03, FHH - 0.03, 0.06, (0.004, 0.004, 0.005, 1))
    a = cv.img
    S = cv.S
    x0, x1 = int((FHW - 0.03 + SX - SHW) * S), int((FHW - 0.03 + SX + SHW) * S)
    y0, y1 = int((FHH - 0.03 - SHH) * S), int((FHH - 0.03 + SHH) * S)
    a[y0:y1, x0:x1] = 0.0
    out.append(print_plane("Mask", cv.image("Mask"), 2 * FHW - 0.06, 2 * FHH - 0.06, T((0, FY0 - 0.0018, 0)), rough=0.05,
                           coat=1.0, spec=0.4))
    return out


def knob(x, z, black, satin):
    out = []
    R = 0.085

    def knurl(r, zz, t):
        if 0.015 < zz < 0.07 and r > R - 0.01:
            return r - 0.0035 * (0.5 + 0.5 * math.cos(44 * t)) ** 2
        return r
    P = [(0.0, 0.085, 0), (R - 0.02, 0.085, 1), (R - 0.006, 0.08, 1), (R, 0.07, 0), (R, 0.012, 0), (R - 0.006, 0.0, 0),
         (0.0, 0.0, 0)]
    out.append(lathe_at("Knob", P, [black, satin], T((x, FY0, z)) @ RX, steps=160, mod=knurl))
    bz = [(R + 0.004, -0.01, 0), (R + 0.022, -0.01, 0), (R + 0.022, 0.004, 0), (R + 0.016, 0.01, 0), (R + 0.004, 0.01, 0)]
    out.append(lathe_at("KnobRing", bz, [satin], T((x, FY0, z)) @ RX, steps=128))
    return out


def keys(btn):
    out = []
    specs = []
    for sx in (-1, 1):
        for k in range(3):
            specs.append((sx * KX, 0.12 - k * 0.20))
    bm = bmesh.new()
    for x, z in specs:
        rrect_y(bm, x, z, 0.085, 0.075, 0.025, FY0 - 0.022, FY0 + 0.01)
    out.append(solid("Keys", bm, [btn], bevel=0.008, seg=3))
    cv = Canvas(2 * FHW, 2 * FHH, 1800)
    W = WHITE
    lw = 0.0075
    icons = ["home", "nav", "media", "phone", "car", "menu"]
    for (x, z), kind in zip(specs, icons):
        u, v = x + FHW, z + FHH
        if kind == "home":
            cv.line([(u - 0.03, v - 0.028), (u - 0.03, v + 0.006), (u, v + 0.032), (u + 0.03, v + 0.006), (u + 0.03, v - 0.028)],
                    lw, W, closed=True)
        elif kind == "nav":
            cv.poly([(u, v + 0.035), (u + 0.028, v - 0.032), (u, v - 0.018), (u - 0.028, v - 0.032)], W)
        elif kind == "media":
            cv.ring(u - 0.012, v - 0.02, 0.0, 0.013, W)
            cv.seg((u, v - 0.02), (u, v + 0.035), lw, W)
            cv.seg((u, v + 0.035), (u + 0.022, v + 0.022), lw, W)
        elif kind == "phone":
            cv.arc(u + 0.006, v - 0.006, 0.028, 100, 215, 0.012, W)
            cv.rrect(u - 0.004, v + 0.022, 0.012, 0.007, 0.004, W)
            cv.rrect(u - 0.023, v - 0.012, 0.007, 0.012, 0.004, W)
        elif kind == "car":
            cv.line([(u - 0.035, v - 0.01), (u - 0.025, v + 0.018), (u + 0.025, v + 0.018), (u + 0.035, v - 0.01),
                     (u + 0.035, v - 0.028), (u - 0.035, v - 0.028)], lw, W, closed=True)
        else:
            for k in (-1, 0, 1):
                cv.seg((u - 0.03, v + k * 0.018), (u + 0.03, v + k * 0.018), lw, W)
    out.append(print_plane("KeyArt", cv.image("KeyArt"), 2 * FHW, 2 * FHH, T((0, FY0 - 0.0232, 0)), rough=0.45))
    return out


def rear(steel, zinc, conn, pins, coax_cols):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 2 * FHW - 0.30, HY1, 2 * FHH - 0.24, center=(0, HY1 / 2, -0.02))
    out.append(solid("Housing", bm, [steel], bevel=0.02, seg=2))
    # heat-sink fins on the back face, left half
    out.append(boxes("Fins", [(0.03, 0.10, 0.80, (-0.80 + 0.075 * k, HY1 + 0.05, 0.0)) for k in range(9)], steel, bevel=0.008))
    # mounting brackets on both sides
    for sx in (-1, 1):
        x = sx * (FHW - 0.13)
        out.append(boxes("Bracket", [(0.02, 0.50, 0.80, (x + sx * 0.012, 0.32, -0.02)),
                                     (0.16, 0.10, 0.80, (x + sx * 0.08, 0.10, -0.02))], zinc, bevel=0.005,
                         holes=[(0.035, -0.2, 0.2, T((x + sx * 0.10, 0.10, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
                                for z in (-0.25, 0.25)]))
    # main multi-pin connector (quadlock-like) on the back
    cx, cz, w, h = 0.35, -0.20, 0.62, 0.20
    bm = bmesh.new()
    C.box_bm(bm, w, 0.16, h, center=(cx, HY1 + 0.07, cz))
    sh = C.mesh_obj("Quad", bm, [conn])
    cb = bmesh.new()
    C.box_bm(cb, w - 0.04, 0.2, h - 0.05, center=(cx, HY1 + 0.19, cz))
    c2 = C.mesh_obj("QuadCut", cb, [])
    C.add_boolean(sh, c2)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=38, remove=[c2]))
    bm = bmesh.new()
    for r in range(2):
        for k in range(14):
            C.box_bm(bm, 0.012, 0.10, 0.012, center=(cx - 0.26 + k * 0.04, HY1 + 0.09, cz - 0.03 + 0.06 * r))
    out.append(C.mesh_obj("QuadPins", bm, [pins]))
    # coloured coaxial (FAKRA-style) sockets
    for k, m in enumerate(coax_cols):
        x = 0.10 + k * 0.17
        bm = bmesh.new()
        rrect_y(bm, x, 0.18, 0.055, 0.055, 0.012, HY1 - 0.01, HY1 + 0.13)
        cb = bmesh.new()
        C.cyl_bm(cb, 0.032, -0.2, 0.2, seg=32, matrix=T((x, HY1 + 0.13, 0.18)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        out.append(solid("Coax%d" % k, bm, [m], bevel=0.006, cutters=[C.mesh_obj("CoaxCut", cb, [])]))
        out.append(lathe_at("CoaxPin", [(0.0, -0.05, 0), (0.008, -0.05, 0), (0.008, 0.06, 0), (0.0, 0.06, 0)], [pins],
                            T((x, HY1 + 0.07, 0.18)) @ Matrix.Rotation(-math.pi / 2, 4, "X"), steps=16))
    return out


def build():
    gloss = C.principled("PianoBlack", (0.008, 0.008, 0.009), rough=0.10, Coat_Weight=0.8)
    black = C.mat_black_plastic("RimPC", rough=0.5, color=0.02)
    btn = C.principled("KeyPC", (0.022, 0.022, 0.024), rough=0.36)
    C.add_noise_bump(btn, scale=1200, strength=0.05, distance=0.0003)
    satin = mat_satin()
    steel = C.principled("BlackSteel", (0.035, 0.035, 0.037), metallic=0.6, rough=0.45)
    C.add_noise_bump(steel, scale=500, strength=0.06, distance=0.0005, rough_var=0.06)
    zinc = C.principled("ZincSteel", (0.58, 0.59, 0.61), metallic=1.0, rough=0.28)
    C.add_noise_bump(zinc, scale=700, strength=0.04, distance=0.0005)
    conn = C.mat_black_plastic("ConnPA", rough=0.55, color=0.032)
    pins = C.principled("PinTin", (0.75, 0.72, 0.62), metallic=1.0, rough=0.25)
    coax = [plastic("CoaxBlue", "#2E62B0", 0.45), plastic("CoaxViolet", "#7A4A9C", 0.45), plastic("CoaxGreen", "#3C8C50", 0.45)]
    objs = bezel(gloss, black) + knob(-KX, 0.48, btn, satin) + knob(KX, 0.48, btn, satin) + keys(btn)
    objs += rear(steel, zinc, conn, pins, coax)
    # stand slightly reclined, bottom edge resting on the floor
    C.transform_all(objs, Matrix.Rotation(math.radians(-8), 4, "X"))
    drop(objs)
    return objs


if __name__ == "__main__":
    matte_floor_in_reflections()
    C.clear()
    objs = build()
    C.shoot("display", objs, "display.py",
            "car infotainment display: 8-inch dark glass touchscreen with simple home screen, gloss black bezel with "
            "two rotary knobs and side keys, black metal housing with brackets and connectors behind",
            az=-30, el=14, lens=70, fill=0.86, **fast_kw())
