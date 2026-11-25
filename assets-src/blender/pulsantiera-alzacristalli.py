"""Driver's door window switch panel (pulsantiera alzacristalli): black grained armrest
insert with four pull-up / push-down window switches in a 2x2 block, each with a printed
window pictogram, a central child-lock button, and the round mirror-adjust joystick with
satin trim ring and selector pictograms; underneath, the moulded switch housing with snap
clips and the multi-pin connector socket at the end. No text or logos."""
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


# units: 1 = 10 cm.  Panel lies flat, top face at z = ZT, front edge toward -Y.
PL, PW = 1.40, 0.62          # panel outline (X, Y)
ZT = 0.10
MX, MY, MR = -0.46, 0.02, 0.115
SW = [(0.06, 0.13), (0.38, 0.13), (0.06, -0.13), (0.38, -0.13)]   # switch centres
SHW, SHL = 0.105, 0.085      # switch cap half width (X) / half length (Y)
WHITE = (0.86, 0.86, 0.84, 1)
UP = Matrix.Rotation(math.radians(-90), 4, "X")   # plane facing +Z


def outline():
    pts = circle_pts(-PL / 2 + 0.25, 0.0, 0.31, 64) + circle_pts(PL / 2 - 0.2, 0.06, 0.25, 64) + \
        circle_pts(PL / 2 - 0.2, -0.06, 0.25, 64)
    return resample(hull2d(pts), 180)


def panel(black, satin):
    out = []
    ob = prism("Panel", outline(), 0.0, ZT, black, bevel=0.0, finalize=False)
    cb = bmesh.new()
    for x, y in SW:
        C.box_bm(cb, 2 * SHW + 0.024, 2 * SHL + 0.05, 0.2, center=(x, y, ZT))
    C.cyl_bm(cb, MR + 0.032, ZT - 0.03, ZT + 0.1, seg=96, matrix=T((MX, MY, 0)))
    C.box_bm(cb, 0.09, 0.07, 0.2, center=(0.22, 0.0, ZT))
    cut = C.mesh_obj("PanelCut", cb, [])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(ob, 0.022, segments=3, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # recess floors (dark) under the switch openings
    out.append(boxes("Wells", [(2 * SHW + 0.03, 2 * SHL + 0.06, 0.02, (x, y, ZT - 0.05)) for x, y in SW] +
                     [(0.10, 0.08, 0.02, (0.22, 0.0, ZT - 0.05))], black, bevel=0.0))
    # satin ring round the mirror joystick
    P = [(MR + 0.008, ZT - 0.03, 0), (MR + 0.032, ZT - 0.03, 0), (MR + 0.032, ZT + 0.004, 0), (MR + 0.026, ZT + 0.012, 0),
         (MR + 0.008, ZT + 0.012, 0)]
    out.append(lathe_at("Trim", P, [satin], T((MX, MY, 0)), steps=128))
    # printed artwork on the panel top
    x0, x1, y0, y1 = -PL / 2, PL / 2, -PW / 2, PW / 2
    cv = Canvas(x1 - x0, y1 - y0, 1500)
    W = WHITE
    cx, cy = MX - x0, MY - y0
    R0 = MR + 0.07
    # selector positions: left mirror, off dot, right mirror, heater
    for t, kind in ((150, "L"), (90, "0"), (30, "R")):
        px, py = cx + R0 * math.cos(math.radians(t)), cy + R0 * math.sin(math.radians(t))
        if kind == "0":
            cv.ring(px, py, 0.0, 0.008, W)
        else:
            sx = -1 if kind == "L" else 1
            pts = [(px - 0.024, py - 0.012), (px + 0.024, py - 0.012), (px + 0.02, py + 0.014), (px - 0.02, py + 0.014)]
            cv.line(pts, 0.005, W, closed=True)
            cv.seg((px + sx * 0.024, py + 0.001), (px + sx * 0.04, py + 0.001), 0.005, W)
    px, py = cx, cy - R0
    pts = [(px - 0.024, py - 0.012), (px + 0.024, py - 0.012), (px + 0.02, py + 0.014), (px - 0.02, py + 0.014)]
    cv.line(pts, 0.005, W, closed=True)
    for k in (-1, 0, 1):
        q = [(px + k * 0.011 + 0.003 * math.sin(i / 6 * TAU), py - 0.008 + 0.016 * i / 6) for i in range(7)]
        cv.line(q, 0.0035, W)
    m = mat_print("PanelPrint", cv.image("PanelPrint"), rough=0.5)
    out.append(C.label_plane("PanelArt", m, x1 - x0, y1 - y0, T((0, 0, ZT + 0.0011)) @ UP))
    return out


def window_icon(cv, u, v, s, wd, col, front=True):
    # side window: slanted A-pillar toward -X for front windows
    if front:
        P = [(-0.9, -0.5), (0.9, -0.5), (0.9, 0.5), (-0.2, 0.5)]
    else:
        P = [(-0.9, -0.5), (0.9, -0.5), (0.5, 0.5), (-0.9, 0.5)]
    cv.line([(u + s * a, v + s * b) for a, b in P], wd, col, closed=True)
    arrow(cv, [(u, v - 0.32 * s), (u, v + 0.14 * s)], wd, col, head=0.016)


def switches(btn, black):
    out = []
    ztop = ZT + 0.065
    for i, (x, y) in enumerate(SW):
        tilt = math.radians(4 if i % 2 else -3)
        Ms = T((x, y, ztop)) @ Matrix.Rotation(tilt, 4, "X")
        # cap: rounded body with a pull lip overhanging the front (-Y) edge, top slightly crowned
        bm = bmesh.new()
        C.box_bm(bm, 2 * SHW, 2 * SHL, 0.12, center=(0, 0, -0.04))
        C.box_bm(bm, 2 * SHW - 0.01, 0.05, 0.035, center=(0, -SHL - 0.012, 0.0025))
        ob = C.mesh_obj("Switch%d" % i, bm, [btn])
        ob.matrix_world = Ms
        C.add_bevel(ob, 0.014, segments=3, angle=30)
        out.append(C.finalize(ob, angle=35))
        cv = Canvas(0.16, 0.12, 3000)
        window_icon(cv, 0.08, 0.06, 0.058, 0.0075, WHITE, front=(i < 2))
        out.append(C.label_plane("SwArt%d" % i, mat_print("SwPrint%d" % i, cv.image("SwPrint%d" % i), rough=0.45),
                                 0.16, 0.12, Ms @ T((0, 0, 0.0204)) @ UP))
    # child-lock button between the two rows
    out.append(boxes("Lock", [(0.08, 0.06, 0.10, (0.22, 0.0, ZT - 0.02))], btn, bevel=0.014, seg=3))
    cv = Canvas(0.08, 0.06, 4000)
    cv.line([(0.02, 0.015), (0.06, 0.015), (0.06, 0.045), (0.035, 0.045)], 0.004, WHITE, closed=False)
    cv.seg((0.02, 0.012), (0.062, 0.05), 0.0045, (0.9, 0.3, 0.15, 1))
    out.append(C.label_plane("LockArt", mat_print("LockPrint", cv.image("LockPrint"), rough=0.45), 0.08, 0.06,
                             T((0.22, 0.0, ZT + 0.0305)) @ UP))
    return out


def joystick(btn, satin):
    out = []
    P = [(0.0, ZT + 0.07, 0), (MR - 0.035, ZT + 0.07, 0), (MR - 0.012, ZT + 0.062, 0), (MR - 0.002, ZT + 0.045, 0),
         (MR, ZT + 0.02, 0), (MR, ZT - 0.02, 0), (0.0, ZT - 0.02, 0)]
    out.append(lathe_at("Joy", P, [btn], T((MX, MY, 0)), steps=128, bevel=0.003))
    # centre stick dome with 4 arrow ribs
    out.append(lathe_at("Stick", [(0.0, ZT + 0.115, 0), (0.03, ZT + 0.11, 0), (0.045, ZT + 0.09, 0), (0.05, ZT + 0.07, 0),
                                  (0.0, ZT + 0.07, 0)], [btn], T((MX, MY, 0)), steps=64))
    cv = Canvas(0.24, 0.24, 3000)
    c = 0.12
    for k in range(4):
        a = math.radians(90 * k)
        ca, sa = math.cos(a), math.sin(a)
        px, py = c + 0.078 * ca, c + 0.078 * sa
        cv.poly([(px + 0.016 * ca, py + 0.016 * sa), (px - 0.01 * ca - 0.014 * sa, py - 0.01 * sa + 0.014 * ca),
                 (px - 0.01 * ca + 0.014 * sa, py - 0.01 * sa - 0.014 * ca)], WHITE)
    out.append(C.label_plane("JoyArt", mat_print("JoyPrint", cv.image("JoyPrint"), rough=0.45), 0.24, 0.24,
                             T((MX, MY, ZT + 0.0705)) @ UP))
    return out


def housing(black, conn, pins):
    out = []
    poly = resample(hull2d(circle_pts(-0.30, 0, 0.22, 48) + circle_pts(0.42, 0, 0.22, 48)), 120)
    out.append(prism("Housing", poly, -0.30, 0.005, black, bevel=0.014, seg=2))
    out.append(boxes("Clips", [(0.10, 0.03, 0.12, (x, sy * 0.235, -0.07)) for x in (-0.35, 0.40) for sy in (-1, 1)],
                     black, bevel=0.006))
    # connector socket at the +X end, opening toward +X
    cz, w, h = -0.16, 0.30, 0.16
    bm = bmesh.new()
    C.box_bm(bm, 0.18, w, h, center=(0.66, 0.0, cz))
    sh = C.mesh_obj("Conn", bm, [conn])
    cb = bmesh.new()
    C.box_bm(cb, 0.2, w - 0.04, h - 0.04, center=(0.77, 0.0, cz))
    c2 = C.mesh_obj("ConnCut", cb, [])
    C.add_boolean(sh, c2)
    C.add_bevel(sh, 0.005, segments=2, angle=30)
    out.append(C.finalize(sh, angle=38, remove=[c2]))
    bm = bmesh.new()
    for r in range(2):
        for k in range(6):
            C.box_bm(bm, 0.10, 0.012, 0.012, center=(0.68, -0.10 + 0.04 * k, cz - 0.025 + 0.05 * r))
    out.append(C.mesh_obj("Pins", bm, [pins]))
    out.append(boxes("Latch", [(0.07, 0.09, 0.03, (0.70, 0.0, cz + h / 2 + 0.012))], conn, bevel=0.004))
    return out


def build():
    black = C.principled("PanelPP", (0.020, 0.020, 0.021), rough=0.58)
    C.add_noise_bump(black, scale=700, strength=0.30, distance=0.0006, detail=4.0, rough_var=0.07)
    btn = C.principled("SwitchPC", (0.024, 0.024, 0.026), rough=0.38)
    C.add_noise_bump(btn, scale=1200, strength=0.05, distance=0.0003)
    satin = mat_satin()
    housing_m = C.mat_black_plastic("HousingPP", rough=0.6, color=0.03)
    conn = C.mat_black_plastic("ConnPA", rough=0.6, color=0.032)
    pins = C.principled("PinTin", (0.75, 0.72, 0.62), metallic=1.0, rough=0.3)
    objs = panel(black, satin) + switches(btn, black) + joystick(btn, satin) + housing(housing_m, conn, pins)
    drop(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("pulsantiera-alzacristalli", objs, "pulsantiera-alzacristalli.py",
            "car driver door window switch panel: black panel with four window switches with pictograms, child-lock "
            "button and mirror adjust joystick, housing with connector underneath",
            az=22, el=42, lens=70, fill=0.86, **fast_kw())
