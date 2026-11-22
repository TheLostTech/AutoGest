"""12 V socket / cigarette lighter (presa 12V / accendisigari): the socket standing upright
- black bezel with lip, zinc-plated steel sleeve with the centre contact at the bottom,
moulded outer sleeve with clip tabs and the spade terminals underneath - with its black
tethered cap lying open beside it, and the lighter plug lying in front showing the
spiral heating element in its cup, the ribbed black knob and chrome trim ring."""
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


# units: 1 = 10 cm.


def socket(black, zinc, brass, tin, M):
    out = []
    # zinc sleeve: open at the top, floor at z = 0.10
    P = [(0.0, 0.10, 0), (0.104, 0.10, 0), (0.104, 0.53, 0), (0.114, 0.53, 0), (0.114, 0.04, 0), (0.0, 0.04, 0)]
    out.append(lathe_at("Sleeve", P, [zinc], M, steps=128))
    # moulded outer sleeve with clip tabs
    P = [(0.115, 0.06, 0), (0.135, 0.06, 0), (0.135, 0.49, 0), (0.115, 0.49, 0)]
    out.append(lathe_at("Outer", P, [black], M, steps=96, bevel=0.004))
    specs = []
    for k in range(3):
        a = TAU * k / 3 + 0.3
        specs.append((0.03, 0.05, 0.16, (0, 0, 0), M @ Matrix.Rotation(a, 4, "Z") @ T((0.145, 0.0, 0.30))))
    out.append(boxes("Clips", specs, black, bevel=0.006))
    # bezel with rounded lip
    P = [(0.104, 0.47, 0), (0.17, 0.47, 0), (0.18, 0.49, 0), (0.178, 0.53, 0), (0.165, 0.555, 0), (0.135, 0.565, 0),
         (0.108, 0.562, 0), (0.104, 0.55, 0)]
    out.append(lathe_at("Bezel", P, [black], M, steps=128))
    # centre contact (brass) and the side spring contacts inside
    out.append(lathe_at("Centre", [(0.0, 0.10, 0), (0.035, 0.10, 0), (0.035, 0.125, 0), (0.025, 0.14, 0), (0.0, 0.14, 0)],
                        [brass], M, steps=48))
    out.append(boxes("Springs", [(0.012, 0.03, 0.12, (0, 0, 0), M @ Matrix.Rotation(a, 4, "Z") @ T((0.098, 0, 0.30)))
                                 for a in (0.5, 0.5 + math.pi)], zinc, bevel=0.003))
    # spade terminals underneath
    out.append(boxes("Spades", [(0.063, 0.008, 0.12, (0.0, 0.0, -0.02)),
                                (0.048, 0.008, 0.10, (0.0, 0.0, 0.0), T((0.0, 0.06, 0.0)) @ T((0.09, 0.0, 0.0)))],
                     tin, bevel=0.002, M=M))
    out.append(boxes("SpadeRoot", [(0.10, 0.03, 0.02, (0.0, 0.0, 0.045)), (0.06, 0.06, 0.03, (0.09, 0.06, 0.045))],
                     black, bevel=0.004, M=M))
    return out


def cap(black, M):
    out = []
    P = [(0.0, -0.05, 0), (0.098, -0.05, 0), (0.102, -0.01, 0), (0.12, 0.0, 0), (0.125, 0.02, 0), (0.118, 0.04, 0),
         (0.0, 0.042, 0)]
    out.append(lathe_at("Cap", P, [black], M, steps=96, bevel=0.003))
    out.append(boxes("CapTab", [(0.06, 0.05, 0.02, (0.0, 0.125, 0.025))], black, bevel=0.006, M=M))
    return out


def lighter(black, chrome, steel, coil_m, M):
    out = []
    # metal body / element cup (element face at z = 0)
    P = [(0.074, 0.004, 0), (0.088, 0.0, 0), (0.098, 0.006, 0), (0.098, 0.31, 0), (0.0, 0.31, 0), (0.0, 0.04, 0),
         (0.074, 0.04, 0)]
    out.append(lathe_at("Cup", P, [steel], M, steps=96))
    # bimetal spring clips on the body
    out.append(boxes("ClipsL", [(0.014, 0.05, 0.14, (0, 0, 0), Matrix.Rotation(a, 4, "Z") @ T((0.1, 0, 0.20)))
                                for a in (0.0, math.pi)], steel, bevel=0.004, M=M))
    # spiral heating ribbon in the cup
    cu = bpy.data.curves.new("Coil", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0042
    cu.bevel_resolution = 1
    sp = cu.splines.new("POLY")
    n = 360
    sp.points.add(n)
    for i in range(n + 1):
        t = i / n
        a = TAU * 6.0 * t
        r = 0.008 + 0.062 * t
        sp.points[i].co = (r * math.cos(a), r * math.sin(a), 0.03, 1)
    ob = C.link(bpy.data.objects.new("Coil", cu))
    cu.materials.append(coil_m)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=60))
    # chrome trim ring + ribbed knob
    out.append(lathe_at("Trim", [(0.09, 0.30, 0), (0.135, 0.30, 0), (0.14, 0.315, 0), (0.135, 0.33, 0), (0.09, 0.33, 0)],
                        [chrome], M, steps=96))

    def ribs(r, z, t):
        if 0.35 < z < 0.50 and r > 0.11:
            return r - 0.006 * (0.5 + 0.5 * math.cos(24 * t)) ** 3
        return r
    P = [(0.0, 0.33, 0), (0.125, 0.33, 0), (0.13, 0.36, 0), (0.135, 0.48, 0), (0.128, 0.51, 0), (0.11, 0.525, 0),
         (0.0, 0.53, 0)]
    out.append(lathe_at("Knob", P, [black], M, steps=192, mod=ribs))
    return out


def knob_print(M):
    cv = Canvas(0.16, 0.16, 3000)
    W = (0.86, 0.86, 0.84, 1)
    # cigarette pictogram: bar with a glowing tip and two smoke waves
    cv.rrect(0.07, 0.07, 0.05, 0.010, 0.003, W)
    cv.rrect(0.128, 0.07, 0.008, 0.010, 0.002, (0.85, 0.35, 0.12, 1))
    for k in range(2):
        pts = [(0.115 + k * 0.016 + 0.006 * math.sin(i / 8 * TAU), 0.088 + 0.045 * i / 8) for i in range(9)]
        cv.line(pts, 0.004, W)
    return print_plane("KnobPrint", cv.image("KnobPrint"), 0.16, 0.16,
                       M @ T((0, 0, 0.5315)) @ Matrix.Rotation(math.radians(-90), 4, "X"), rough=0.4)


def build():
    black = C.principled("PA6", (0.022, 0.022, 0.023), rough=0.45)
    C.add_noise_bump(black, scale=900, strength=0.10, distance=0.0004, rough_var=0.05)
    zinc = C.principled("ZincSleeve", (0.62, 0.62, 0.60), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=500, strength=0.05, distance=0.0005, rough_var=0.06)
    brass = C.principled("Brass", (0.78, 0.62, 0.36), metallic=1.0, rough=0.25)
    tin = C.principled("Tin", (0.62, 0.60, 0.56), metallic=1.0, rough=0.16)
    chrome = C.mat_chrome("Chrome")
    steel = C.principled("CupSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.04, distance=0.0004)
    coil_m = C.principled("Element", (0.30, 0.26, 0.24), metallic=1.0, rough=0.42)
    objs = []
    Ms = T((-0.05, 0.12, 0.08)) @ Matrix.Rotation(math.radians(8), 4, "X")
    a = socket(black, zinc, brass, tin, Ms)
    Mc = T((0.36, 0.20, 0.05))
    b = cap(black, Mc)
    # tether strap from the bezel lip to the cap tab
    drop(a)
    drop(b)
    p0 = Ms @ Vector((0.16, 0.06, 0.51))
    p1 = Mc @ Vector((0.0, 0.14, 0.025))
    mid = (p0 + p1) / 2 + Vector((0, 0, 0.10))
    b.append(tube("Tether", [p0, mid, p1], 0.012, black, res=2))
    lay = Matrix.Rotation(math.radians(90), 4, "Y")
    Ml = T((-0.05, -0.32, 0.10)) @ Matrix.Rotation(math.radians(140), 4, "Z") @ lay
    c = lighter(black, chrome, steel, coil_m, Ml) + [knob_print(Ml)]
    drop(c)
    return a + b + c


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("presa-12v", objs, "presa-12v.py",
            "car 12 V socket and cigarette lighter: socket with black bezel, metal sleeve and terminals, tethered cap, "
            "lighter plug showing the spiral heating element and ribbed knob",
            az=24, el=34, lens=70, fill=0.84, **fast_kw())
