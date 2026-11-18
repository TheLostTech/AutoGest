"""Handbrake lever (freno a mano) as removed from the car: black e-coated stamped steel
lever arm with a pressed stiffening rib, a black leather grip with plastic collar and end
cap, a satin-silver release button at the tip, the zinc-plated ratchet sector and pawl,
the stamped mounting base with two cheeks, pivot bolt and bolt holes, and at the rear the
cable attachment: threaded adjuster rod with nut, equaliser yoke and two short cable
ends with ferrules and nipples. No text or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))

# units: 1 = 10 cm, Z up, lever in the XZ plane pointing to +X, viewer on -Y.
P0 = Vector((0.0, 0.0, 0.62))     # pivot
ALPHA = math.radians(26.0)        # lever angle above horizontal
LW = 0.13                         # lever half width (y)
CY0, CY1 = 0.16, 0.19             # cheek plates |y|
G0, G1 = 1.55, 3.20               # grip start / tip along the lever
L = Matrix.Translation(P0) @ Matrix.Rotation(-ALPHA, 4, "Y")   # lever frame: x = along, z = up
RY = Matrix.Rotation(math.pi / 2, 4, "Y")                       # local +Z -> +X
RXN = Matrix.Rotation(-math.pi / 2, 4, "X")                     # local +Z -> +Y

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



def prism_xz(bm, pts, y0, y1, mat=0):
    """Polygon in the XZ plane extruded from y0 to y1 (closed solid)."""
    a = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    n = len(pts)
    fs = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for k in range(n)]
    fs += [bm.faces.new(a[::-1]), bm.faces.new(b)]
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    for f in fs:
        f.material_index = mat
    return fs


def mat_ecoat(name="EcoatSteel"):
    """Black e-coated pressed steel: satin, faint orange peel, slightly worn edges."""
    m = C.principled(name, (0.028, 0.028, 0.030), rough=0.42, metallic=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    C.add_noise_bump(m, scale=300, strength=0.10, distance=0.0008, rough_var=0.05)
    em = C.edge_mask(nt, 0.01, 3.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 30.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    nt.links.new(em, mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.7
    nt.links.new(mul.outputs[0], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.028, 0.028, 0.030, 1)
    mix.inputs["B"].default_value = (0.09, 0.09, 0.095, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_leather(name, base=0.024, rough=0.46):
    m = C.principled(name, (base, base, base * 1.02), rough=rough, Sheen_Weight=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = 140.0
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
    return m


# ----------------------------------------------------------------- base
def base(ecoat, zinc):
    out = []
    bm = bmesh.new()
    rrect_y(bm, 0.05, 0.0, 0.85, 0.34, 0.12, 0.0, 0.045)       # (x, y) plate, built in XZ then swapped
    for v in bm.verts:
        x, y, z = v.co
        v.co = (x, z, y)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    # raised flanges along the long edges
    for sy in (-1, 1):
        C.box_bm(bm, 1.5, 0.035, 0.10, center=(0.05, sy * 0.325, 0.05))
    cb = bmesh.new()
    for (x, y) in ((-0.62, 0.0), (0.70, -0.18), (0.70, 0.18)):
        C.cyl_bm(cb, 0.05, -0.1, 0.2, seg=32, matrix=Matrix.Translation((x, y, 0)))
    cut = C.mesh_obj("PlateCut", cb, [])
    pl = C.mesh_obj("Plate", bm, [ecoat])
    C.add_boolean(pl, cut).use_self = True
    C.add_bevel(pl, 0.008, segments=2, angle=30)
    out.append(C.finalize(pl, angle=38, remove=[cut]))
    # pressed cheeks carrying the pivot
    prof = [(-0.55, 0.03), (0.70, 0.03), (0.42, 0.40), (0.20, 0.70), (0.0, 0.76), (-0.20, 0.70), (-0.42, 0.44)]
    for sy in (-1, 1):
        bm = bmesh.new()
        prism_xz(bm, prof, sy * CY0, sy * CY1)
        cb = bmesh.new()
        prism_xz(cb, [(-0.30, 0.14), (0.28, 0.14), (0.12, 0.38), (-0.18, 0.38)], sy * (CY0 - 0.1), sy * (CY1 + 0.1))
        cut = C.mesh_obj("CheekCut", cb, [])
        out.append(solid("Cheek", bm, [ecoat], bevel=0.01, seg=2, cutters=[cut]))
    # pivot bolt: hex head on the viewer side, nut + thread on the far side
    for side in (-1, 1):
        bm = bmesh.new()
        C.cyl_bm(bm, 0.075, 0.0, 0.055, seg=6)
        hx = C.mesh_obj("Hex", bm, [zinc])
        hx.matrix_world = Matrix.Translation(P0 + Vector((0, side * CY1, 0))) @ (RXN if side > 0 else Matrix.Rotation(math.pi / 2, 4, "X"))
        C.add_bevel(hx, 0.01, segments=2, angle=30)
        out.append(C.finalize(hx, angle=38))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.035, -CY1 - 0.06, CY1 + 0.10, seg=24)
    sh = C.mesh_obj("Shaft", bm, [zinc])
    sh.matrix_world = Matrix.Translation(P0) @ RXN
    out.append(C.finalize(sh, angle=38))
    return out


def sector(zinc):
    """Toothed ratchet sector fixed to the viewer-side cheek."""
    r0, r1, rt = 0.30, 0.43, 0.47
    a0, a1 = -78.0, -12.0
    n = 16
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((r1 * math.cos(a), r1 * math.sin(a)))
        if i < n:
            am = math.radians(a0 + (a1 - a0) * (i + 0.5) / n)
            pts.append((rt * math.cos(am), rt * math.sin(am)))
    for i in range(12, -1, -1):
        a = math.radians(a0 + (a1 - a0) * i / 12)
        pts.append((r0 * math.cos(a), r0 * math.sin(a)))
    bm = bmesh.new()
    prism_xz(bm, [(P0.x + x, P0.z + z) for x, z in pts], -CY1 - 0.028, -CY1 - 0.002)
    out = [solid("Sector", bm, [zinc], bevel=0.004, seg=1, angle=25)]
    # rivets fixing it to the cheek
    for a in (-66, -24):
        q = P0 + Vector((0.34 * math.cos(math.radians(a)), 0, 0.34 * math.sin(math.radians(a))))
        rv = C.lathe("Rivet", [(0.0, 0.0, 0), (0.03, 0.0, 0), (0.028, 0.012, 0), (0.0, 0.018, 0)], [zinc], steps=24)
        rv.matrix_world = Matrix.Translation(q + Vector((0, -CY1 - 0.028, 0))) @ Matrix.Rotation(math.pi / 2, 4, "X")
        out.append(C.finalize(rv, angle=40))
    return out


# ----------------------------------------------------------------- lever
def lever(ecoat, zinc):
    out = []
    prof = [(-0.36, -0.36), (-0.18, -0.38), (-0.02, -0.20), (0.40, -0.17), (G0 + 0.4, -0.10),
            (G0 + 0.4, 0.10), (0.40, 0.17), (0.0, 0.19), (-0.20, 0.15), (-0.38, 0.0)]
    bm = bmesh.new()
    prism_xz(bm, prof, -LW, LW)
    lv = C.mesh_obj("Lever", bm, [ecoat])
    lv.matrix_world = L
    cb = bmesh.new()
    C.cyl_bm(cb, 0.04, -1, 1, seg=24, matrix=Matrix.Translation((-0.27, 0, -0.27)) @ RXN)
    cut = C.mesh_obj("LugHole", cb, [])
    cut.matrix_world = L
    C.add_boolean(lv, cut)
    C.add_bevel(lv, 0.03, segments=3, angle=30)
    out.append(C.finalize(lv, angle=38, remove=[cut]))
    # pressed rib along the viewer-side face
    bm = bmesh.new()
    prism_xz(bm, [(0.25, -0.05), (G0 + 0.2, -0.03), (G0 + 0.2, 0.03), (0.25, 0.05)], -LW - 0.018, -LW + 0.01)
    rb = C.mesh_obj("Rib", bm, [ecoat])
    rb.matrix_world = L
    C.add_bevel(rb, 0.012, segments=3, angle=20)
    out.append(C.finalize(rb, angle=38))
    # pawl hanging off the lever towards the sector teeth
    bm = bmesh.new()
    prism_xz(bm, [(0.22, -0.12), (0.36, -0.12), (0.37, -0.24), (0.33, -0.31), (0.27, -0.27), (0.22, -0.18)],
             -0.252, -0.228)
    pw = C.mesh_obj("Pawl", bm, [zinc])
    pw.matrix_world = L
    C.add_bevel(pw, 0.004, segments=1, angle=30)
    out.append(C.finalize(pw, angle=38))
    rv = C.lathe("PawlPin", [(0.0, 0.0, 0), (0.024, 0.0, 0), (0.024, 0.122, 0), (0.034, 0.124, 0), (0.032, 0.136, 0),
                             (0.0, 0.140, 0)], [zinc], steps=24)
    rv.matrix_world = L @ Matrix.Translation((0.29, -LW + 0.01, -0.16)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    out.append(C.finalize(rv, angle=40))
    return out


def grip(leather, plastic, satin):
    out = []
    zs = [(0.20, 0.0, 1), (0.215, 0.02, 1), (0.215, 0.07, 1), (0.192, 0.09, 0), (0.192, 0.11, 0),
          (0.198, 0.30, 0), (0.222, 0.62, 0), (0.238, 0.95, 0), (0.236, 1.22, 0), (0.222, 1.42, 0),
          (0.214, 1.47, 1), (0.218, 1.50, 1), (0.215, 1.56, 1), (0.196, 1.62, 1), (0.150, 1.645, 1),
          (0.0, 1.645, 1)]
    P = [(0.0, 0.0, 1)] + zs
    gp = C.lathe("Grip", P, [leather, plastic], steps=128)
    gp.matrix_world = L @ Matrix.Translation((G0, 0, 0.005)) @ RY @ Matrix.Diagonal((1.0, 0.80, 1.0, 1.0))
    sub = gp.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    out.append(C.finalize(gp, angle=40))
    # raised seam along the underside of the leather
    bm = bmesh.new()
    pts = []
    for (r, z, mi) in zs[4:10]:
        pts.append(Vector((r * 1.0 + 0.004, 0, z)))
    sec = [(0.008 * math.cos(math.tau * i / 8), 0.008 * math.sin(math.tau * i / 8)) for i in range(8)]
    frames = []
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        U = Vector((0, 1, 0))
        V = T.cross(U).normalized()
        frames.append((p, U, V, sec))
    C.sweep(bm, frames)
    sm = C.mesh_obj("Seam", bm, [leather])
    sm.matrix_world = (L @ Matrix.Translation((G0, 0, 0.005)) @ RY @ Matrix.Rotation(math.pi, 4, "Z")
                       @ Matrix.Diagonal((1.0, 0.80, 1.0, 1.0)))
    out.append(C.finalize(sm, angle=60))
    # release button: satin ring + domed push button
    M = L @ Matrix.Translation((G0 + 1.64, 0, 0.005)) @ RY
    rg = C.lathe("BtnRing", [(0.090, -0.01, 0), (0.135, -0.01, 0), (0.135, 0.012, 0), (0.125, 0.022, 0),
                             (0.090, 0.022, 0)], [satin], steps=96)
    rg.matrix_world = M
    C.add_bevel(rg, 0.003, segments=1, angle=30)
    out.append(C.finalize(rg, angle=40))
    bt = C.lathe("Button", [(0.0, 0.075, 0), (0.05, 0.072, 0), (0.078, 0.060, 0), (0.085, 0.04, 0),
                            (0.085, 0.0, 0), (0.0, 0.0, 0)], [satin], steps=96)
    bt.matrix_world = M
    out.append(C.finalize(bt, angle=40))
    return out


# ----------------------------------------------------------------- cable attachment
def cables(zinc, ecoat, sheath, steel):
    out = []
    lug = L @ Vector((-0.27, 0, -0.27))
    # clevis pin through the lug
    bm = bmesh.new()
    C.cyl_bm(bm, 0.035, -LW - 0.05, LW + 0.05, seg=24)
    pn = C.mesh_obj("Clevis", bm, [zinc])
    pn.matrix_world = Matrix.Translation(lug) @ RXN
    out.append(C.finalize(pn, angle=40))
    # U-clevis around the lug
    bm = bmesh.new()
    for sy in (-1, 1):
        C.box_bm(bm, 0.16, 0.025, 0.11, center=(lug.x - 0.05, sy * (LW + 0.025), lug.z))
    C.box_bm(bm, 0.05, 2 * LW + 0.075, 0.11, center=(lug.x - 0.14, 0, lug.z))
    out.append(solid("ClevisU", bm, [zinc], bevel=0.008))
    # threaded adjuster rod back to the equaliser
    xe = -0.80
    pitch = 0.025

    def thread(r, z, t):
        return r + 0.004 * math.sin(math.tau * z / pitch + t) if r > 0.02 else r
    P = [(0.0, 0.0, 0)] + [(0.028, 0.0 + i * 0.01, 0) for i in range(int((-xe + lug.x - 0.16) / 0.01) + 1)] + [(0.0, -xe + lug.x - 0.16, 0)]
    rod = C.lathe("Rod", P, [steel], steps=32, mod=thread)
    rod.matrix_world = Matrix.Translation((xe, 0, lug.z)) @ RY
    out.append(C.finalize(rod, angle=50))
    # hex adjusting nut + lock nut against the yoke
    for x in (xe + 0.07, xe + 0.15):
        bm = bmesh.new()
        C.cyl_bm(bm, 0.06, 0.0, 0.06, seg=6)
        nt_ = C.mesh_obj("Nut", bm, [zinc])
        nt_.matrix_world = Matrix.Translation((x, 0, lug.z)) @ RY @ Matrix.Rotation(math.radians(30), 4, "Z")
        C.add_bevel(nt_, 0.008, segments=2, angle=30)
        out.append(C.finalize(nt_, angle=38))
    # equaliser yoke (pressed steel bar across the two cables)
    bm = bmesh.new()
    prism_xz(bm, [(xe - 0.10, lug.z - 0.07), (xe + 0.07, lug.z - 0.07), (xe + 0.07, lug.z + 0.07),
                  (xe - 0.10, lug.z + 0.07)], -0.27, 0.27)
    yk = C.mesh_obj("Yoke", bm, [ecoat])
    cb = bmesh.new()
    for sy in (-1, 1):
        C.box_bm(cb, 0.08, 0.04, 0.2, center=(xe - 0.08, sy * 0.20, lug.z))
    cut = C.mesh_obj("YokeCut", cb, [])
    C.add_boolean(yk, cut)
    C.add_bevel(yk, 0.015, segments=3, angle=30)
    out.append(C.finalize(yk, angle=38, remove=[cut]))
    # two cable ends: barrel nipple in the yoke slot, short inner cable, ferrule, sheath stub
    for sy in (-1, 1):
        y = sy * 0.20
        bm = bmesh.new()
        C.cyl_bm(bm, 0.03, -0.035, 0.035, seg=24)
        nb = C.mesh_obj("Nipple", bm, [zinc])
        nb.matrix_world = Matrix.Translation((xe - 0.06, y, lug.z)) @ RXN
        out.append(C.finalize(nb, angle=40))
        start = Vector((xe - 0.08, y, lug.z))
        end = Vector((xe - 0.55, y * 1.5, 0.05))
        mid1 = start + Vector((-0.22, 0, 0))
        mid2 = end + Vector((0.22, 0, 0.14))
        pts = []
        for i in range(41):
            t = i / 40
            pts.append(start * (1 - t) ** 3 + mid1 * 3 * (1 - t) ** 2 * t + mid2 * 3 * (1 - t) * t * t + end * t ** 3)
        sec_in = [(0.011 * math.cos(math.tau * i / 10), 0.011 * math.sin(math.tau * i / 10)) for i in range(10)]
        sec_sh = [(0.034 * math.cos(math.tau * i / 16), 0.034 * math.sin(math.tau * i / 16)) for i in range(16)]

        def frames(p, sec):
            fr = []
            for i, q in enumerate(p):
                T = (p[min(i + 1, len(p) - 1)] - p[max(i - 1, 0)]).normalized()
                U = T.cross(Vector((0, 0, 1)))
                if U.length < 1e-4:
                    U = Vector((0, 1, 0))
                U.normalize()
                fr.append((q, U, T.cross(U).normalized(), sec))
            return fr
        k = 12
        bm = bmesh.new()
        C.sweep(bm, frames(pts[:k + 1], sec_in))
        out.append(C.finalize(C.mesh_obj("Inner", bm, [steel]), angle=60))
        # ferrule
        T = (pts[k + 1] - pts[k]).normalized()
        M = Matrix.Translation(pts[k]) @ T.to_track_quat("Z", "Y").to_matrix().to_4x4()
        fe = C.lathe("Ferrule", [(0.0, 0.0, 0), (0.026, 0.0, 0), (0.042, 0.02, 0), (0.042, 0.12, 0), (0.0, 0.12, 0)],
                     [zinc], steps=32)
        fe.matrix_world = M
        C.add_bevel(fe, 0.004, segments=1, angle=30)
        out.append(C.finalize(fe, angle=40))
        bm = bmesh.new()
        C.sweep(bm, frames(pts[k + 3:], sec_sh))
        out.append(C.finalize(C.mesh_obj("Sheath", bm, [sheath]), angle=60))
        # cut end of the sheath: crimped sleeve
        T = (pts[-1] - pts[-2]).normalized()
        M = Matrix.Translation(pts[-1]) @ T.to_track_quat("Z", "Y").to_matrix().to_4x4()
        cs = C.lathe("Crimp", [(0.0, -0.08, 0), (0.040, -0.08, 0), (0.040, 0.0, 0), (0.0, 0.0, 0)], [zinc], steps=32)
        cs.matrix_world = M
        C.add_bevel(cs, 0.004, segments=1, angle=30)
        out.append(C.finalize(cs, angle=40))
    return out


def build():
    ecoat = mat_ecoat()
    zinc = C.principled("ZincSteel", (0.60, 0.61, 0.62), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005, rough_var=0.05)
    steel = C.principled("RodSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    leather = mat_leather("GripLeather", base=0.024)
    plastic = C.principled("GripPP", (0.022, 0.022, 0.023), rough=0.5)
    C.add_noise_bump(plastic, scale=700, strength=0.25, distance=0.0006, rough_var=0.06)
    satin = mat_satin()
    sheath = C.principled("SheathPE", (0.018, 0.018, 0.019), rough=0.4)
    C.add_noise_bump(sheath, scale=500, strength=0.05, distance=0.0004)
    objs = base(ecoat, zinc) + sector(zinc) + lever(ecoat, zinc) + grip(leather, plastic, satin)
    objs += cables(zinc, ecoat, sheath, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("freno-mano", objs, "freno-mano.py",
            "handbrake lever: black steel lever with leather grip and release button, ratchet sector and pawl, "
            "stamped mounting base, adjuster rod, equaliser and cable ends",
            az=38, el=26, lens=70, fill=0.88, **kw)
