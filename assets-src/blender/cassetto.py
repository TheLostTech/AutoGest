"""Glovebox (cassetto portaoggetti) as removed from the dashboard, shown dropped open:
the lid is the outer dashboard face - wider and taller than the bin, curved in both
directions to follow the dash, black grained plastic with a satin-silver crease inlay and
a recessed latch handle near its top edge - hinged at the bottom on two stamped steel
hinge brackets and swung ~40 degrees open towards the viewer. Behind it the moulded bin
with tapered walls, a dark grey flocked interior and a felt floor mat, zinc
latch bolts at the top corners, and a linear damper stay on the side. No text or logos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
import numpy as np
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))

# Geometry is built CLOSED (units: 1 = 10 cm, Z up, lid facing -Y) and then swung open
# about the hinge axis (parallel to X) by OPEN degrees, top towards the viewer.
LHW = 1.95                 # lid half width
LZ0, LZ1 = -0.10, 2.16     # lid bottom / top
LY = -0.02                 # lid back reference
BULGE_X, BULGE_Z = 0.16, 0.09
BHW = 1.62                 # bin half width at the front
WALL = 0.04
HANDLE = (0.0, 1.88, 0.34, 0.075)   # cx, cz, half w, half h
HINGE = Vector((0.0, 0.24, 0.16))   # pivot axis point (y, z used)
OPEN = 40.0
RY = Matrix.Rotation(math.pi / 2, 4, "Y")     # local +Z -> +X
RXN = Matrix.Rotation(-math.pi / 2, 4, "X")   # local +Z -> +Y

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



def open_matrix():
    return (Matrix.Translation(HINGE) @ Matrix.Rotation(math.radians(OPEN), 4, "X")
            @ Matrix.Translation(-HINGE))


# ----------------------------------------------------------------- materials
def mat_grained(name, v=0.022, rough=0.6, strength=0.4, scale=160.0):
    """Dashboard-style grained black plastic (fine leather-like grain)."""
    m = C.principled(name, (v, v, v * 1.05), rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = scale
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 700.0
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(vo.outputs["Distance"], add.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.3
    nt.links.new(nz.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], add.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.06
    nt.links.new(vo.outputs["Distance"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_felt(name="Felt", v=0.13):
    m = C.principled(name, (v, v, v * 1.04), rough=0.95, Sheen_Weight=0.6, Sheen_Roughness=0.4)
    C.add_noise_bump(m, scale=900, strength=0.5, distance=0.001, detail=8.0)
    return m


# ----------------------------------------------------------------- lid
def lid_y(x, z):
    """Front surface: domed in both directions, stepped styling crease low down."""
    zc = (LZ0 + LZ1) / 2
    hh = (LZ1 - LZ0) / 2
    y = LY - 0.03 - BULGE_X * (1 - (x / LHW) ** 2) - BULGE_Z * (1 - ((z - zc) / hh) ** 2)
    return y + 0.026 * (1 - C.smoothstep(0.62, 0.68, z))


def lid_outline():
    """Rounded trapezoid with an arched top edge (x, z)."""
    n = 7.0
    zc = (LZ0 + LZ1) / 2
    hh = (LZ1 - LZ0) / 2
    pts = []
    for i in range(240):
        a = math.tau * i / 240
        c, si = math.cos(a), math.sin(a)
        x = LHW * math.copysign(abs(c) ** (2 / n), c)
        z = zc + hh * math.copysign(abs(si) ** (2 / n), si)
        zn = (z - LZ0) / (LZ1 - LZ0)
        x *= 1 - 0.08 * (1 - zn)
        z += 0.14 * (1 - (x / LHW) ** 2) * C.smoothstep(0.5, 1.0, zn)
        pts.append((x, z))
    return pts


def lid_outline_prism():
    pts = lid_outline()
    bm = bmesh.new()
    a = [bm.verts.new((x, -0.8, z)) for x, z in pts]
    b = [bm.verts.new((x, 0.3, z)) for x, z in pts]
    n = len(pts)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.mesh_obj("LidOutline", bm, [])


def lid(grain, satin, black):
    out = []
    NX, NZ = 170, 130
    bm = bmesh.new()
    rows = []
    for j in range(NZ + 1):
        z = LZ0 - 0.05 + (LZ1 + 0.25 - LZ0) * j / NZ
        rows.append([bm.verts.new((x, lid_y(x, z), z)) for x in
                     [-LHW - 0.05 + (2 * LHW + 0.1) * i / NX for i in range(NX + 1)]])
    for j in range(NZ):
        for i in range(NX):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.normal_update()
    if sum(f.normal.y * f.calc_area() for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = C.mesh_obj("Lid", bm, [grain])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.06
    so.offset = -1
    ocut = lid_outline_prism()
    C.add_boolean(ob, ocut, op="INTERSECT")
    cx, cz, hw, hh2 = HANDLE
    cb = bmesh.new()
    rrect_y(cb, cx, cz, hw, hh2, 0.07, -0.8, 0.3)
    cut = C.mesh_obj("HandleCut", cb, [])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.014, segments=3, angle=30)
    out.append(C.finalize(ob, angle=40, remove=[ocut, cut]))
    # recess tub behind the handle opening
    yf = lid_y(cx, cz)
    bm = bmesh.new()
    rrect_y(bm, cx, cz, hw + 0.05, hh2 + 0.05, 0.10, yf + 0.03, yf + 0.13)
    tub = C.mesh_obj("Tub", bm, [black])
    cb = bmesh.new()
    rrect_y(cb, cx, cz, hw - 0.002, hh2 - 0.002, 0.07, yf - 0.3, yf + 0.10)
    c2 = C.mesh_obj("TubCut", cb, [])
    C.add_boolean(tub, c2)
    out.append(C.finalize(tub, angle=40, remove=[c2]))
    # latch lever in the recess: satin pull bar with a finger lip
    bm = bmesh.new()
    rrect_y(bm, cx, cz + 0.008, hw - 0.04, hh2 - 0.03, 0.045, yf + 0.03, yf + 0.09)
    lv = C.mesh_obj("Lever", bm, [satin])
    C.add_bevel(lv, 0.01, segments=3, angle=30)
    out.append(C.finalize(lv, angle=40))
    # satin inlay following the crease
    z = 0.695
    pts = [Vector((x, lid_y(x, z) - 0.006, z)) for x in [-1.50 + 3.0 * i / 90 for i in range(91)]]
    frames = []
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, 90)] - pts[max(i - 1, 0)]).normalized()
        U = Vector((0, 0, 1)).cross(T).normalized()
        V = T.cross(U).normalized()
        frames.append((p, U, V, [(0.0, -0.012), (0.006, -0.008), (0.008, 0.0), (0.006, 0.008), (0.0, 0.012)]))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("CreaseStrip", bm, [satin]), angle=50))
    return out


# ----------------------------------------------------------------- bin
def bx(y):
    """Bin half width: the side walls taper towards the back."""
    return BHW - 0.20 * max(0.0, y) / 1.6


def profile():
    """Bin side outline (y, z) from the top of the front wall round to the back rim;
    the segment from the last point back to the first is the open top."""
    pts = [(0.06, 1.98), (0.06, 0.16), (0.09, 0.06), (0.18, 0.0), (0.6, 0.0), (1.0, 0.0)]
    back = [(1.22, 0.04), (1.40, 0.16), (1.52, 0.40), (1.58, 0.74), (1.57, 1.08), (1.48, 1.38), (1.32, 1.62)]
    return pts + back


def bin_shell(outer, inner):
    P = profile()
    bm = bmesh.new()
    a = [bm.verts.new((-bx(y), y, z)) for y, z in P]
    b = [bm.verts.new((bx(y), y, z)) for y, z in P]
    n = len(P)
    for k in range(n - 1):
        bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cen = Vector((0, 0.8, 0.9))
    bm.normal_update()
    if sum((f.calc_center_median() - cen).dot(f.normal) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = C.mesh_obj("Bin", bm, [outer, inner])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = WALL
    so.offset = -1
    so.material_offset = 1
    C.add_bevel(ob, 0.012, segments=3, angle=30)
    return [C.finalize(ob, angle=38)]


def bin_details(grain, black, zinc, felt, flock):
    out = []
    P = profile()
    y0, z0 = P[-1]
    # moulded rim lip along the open edge of the side walls and back
    bm = bmesh.new()
    C.box_bm(bm, 2 * bx(y0) + 0.05, 0.07, 0.05, center=(0, y0 + 0.01, z0 - 0.015))
    out.append(solid("BackLip", bm, [grain], bevel=0.015))
    # side wall stiffening ribs
    bm = bmesh.new()
    for sx in (-1, 1):
        for y in (0.70, 1.15):
            C.box_bm(bm, 0.03, 0.045, 1.25, center=(sx * (bx(y) + 0.012), y, 0.75))
    out.append(solid("SideRibs", bm, [grain], bevel=0.01))
    # felt mat on the floor
    bm = bmesh.new()
    C.box_bm(bm, 2 * bx(1.0) - 0.14, 0.86, 0.02, center=(0, 0.60, WALL + 0.012))
    out.append(solid("FeltMat", bm, [felt], bevel=0.008))
    # hinge bosses + pivot pins on the side walls
    for sx in (-1, 1):
        M = Matrix.Translation((sx * bx(HINGE.y), HINGE.y, HINGE.z)) @ (RY if sx > 0 else Matrix.Rotation(-math.pi / 2, 4, "Y"))
        bs = C.lathe("Boss", [(0.0, 0.0, 0), (0.13, 0.0, 0), (0.13, 0.05, 0), (0.11, 0.07, 0), (0.0, 0.07, 0)],
                     [black], steps=64)
        bs.matrix_world = M
        C.add_bevel(bs, 0.008, segments=2, angle=30)
        out.append(C.finalize(bs, angle=40))
        pn = C.lathe("Pin", [(0.0, 0.0, 0), (0.04, 0.0, 0), (0.04, 0.19, 0), (0.06, 0.19, 0), (0.06, 0.22, 0),
                             (0.0, 0.225, 0)], [zinc], steps=40)
        pn.matrix_world = M
        out.append(C.finalize(pn, angle=40))
    # latch bolts at the top corners (zinc tongue in a black guide)
    for sx in (-1, 1):
        y = 0.26
        bm = bmesh.new()
        C.box_bm(bm, 0.10, 0.22, 0.16, center=(sx * (bx(y) + 0.05), y, 1.82))
        out.append(solid("LatchGuide", bm, [black], bevel=0.012))
        bm = bmesh.new()
        C.box_bm(bm, 0.12, 0.10, 0.06, center=(sx * (bx(y) + 0.14), y, 1.82))
        out.append(solid("LatchBolt", bm, [zinc], bevel=0.008))
    return out


DAMP_Q = (1.02, 1.30)   # damper anchor on the right wall (y, z), closed frame


def damper(black, chrome, zinc):
    """Linear damper stay: anchored on the bin side, reaching up and back (world frame)."""
    out = []
    Mo = open_matrix()
    q = Mo @ Vector((bx(DAMP_Q[0]) + 0.045, DAMP_Q[0], DAMP_Q[1]))
    d = Vector((0.0, 0.62, 0.78)).normalized()
    M = Matrix.Translation(q) @ d.to_track_quat("Z", "X").to_matrix().to_4x4()
    Mx = Matrix.Translation(q) @ RY
    # pivot stud + eye on the wall
    st = C.lathe("DStud", [(0.0, -0.05, 0), (0.035, -0.05, 0), (0.035, 0.07, 0), (0.05, 0.07, 0), (0.05, 0.095, 0),
                           (0.0, 0.10, 0)], [zinc], steps=32)
    st.matrix_world = Mx
    out.append(C.finalize(st, angle=40))
    eye = C.lathe("DEye", [(0.035, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.05, 0), (0.035, 0.05, 0)], [black], steps=40)
    eye.matrix_world = Mx @ Matrix.Translation((0, 0, 0.012))
    out.append(C.finalize(eye, angle=40))
    body = C.lathe("DBody", [(0.0, 0.05, 0), (0.035, 0.05, 0), (0.05, 0.08, 0), (0.05, 0.62, 0), (0.042, 0.65, 0),
                             (0.02, 0.66, 0), (0.0, 0.66, 0)], [black], steps=48)
    body.matrix_world = Matrix.Translation((0.075, 0, 0)) @ M
    C.add_bevel(body, 0.004, segments=1, angle=30)
    out.append(C.finalize(body, angle=40))
    rod = C.lathe("DRod", [(0.0, 0.64, 0), (0.016, 0.64, 0), (0.016, 1.06, 0), (0.0, 1.06, 0)], [chrome], steps=24)
    rod.matrix_world = Matrix.Translation((0.075, 0, 0)) @ M
    out.append(C.finalize(rod, angle=40))
    end = C.lathe("DEnd", [(0.0, 1.04, 0), (0.035, 1.04, 0), (0.045, 1.07, 0), (0.045, 1.15, 0), (0.03, 1.17, 0),
                           (0.0, 1.17, 0)], [black], steps=32)
    end.matrix_world = Matrix.Translation((0.075, 0, 0)) @ M
    out.append(C.finalize(end, angle=40))
    # mounting clip at the free end (bolts to the dash cross-member)
    tip = q + Vector((0.075, 0, 0)) + d * 1.17
    bm = bmesh.new()
    C.box_bm(bm, 0.05, 0.16, 0.12, center=tip + Vector((0, 0.02, 0.04)))
    out.append(solid("DClip", bm, [black], bevel=0.012))
    return out


def hinge_brackets(steel, zg):
    """Stamped steel hinge brackets carrying the pivot pins (world frame, feet on the floor)."""
    out = []
    for sx in (-1, 1):
        xe = sx * (bx(HINGE.y) + 0.20)
        # upright ear with the pivot hole
        prof = [(HINGE.y - 0.16, zg), (HINGE.y + 0.42, zg), (HINGE.y + 0.18, HINGE.z + 0.02),
                (HINGE.y + 0.08, HINGE.z + 0.12), (HINGE.y - 0.06, HINGE.z + 0.12), (HINGE.y - 0.14, HINGE.z)]
        bm = bmesh.new()
        a = [bm.verts.new((xe - 0.015, y, z)) for y, z in prof]
        b = [bm.verts.new((xe + 0.015, y, z)) for y, z in prof]
        n = len(prof)
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
        bm.faces.new(a[::-1])
        bm.faces.new(b)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # foot flange on the floor
        C.box_bm(bm, 0.22, 0.62, 0.03, center=(xe + sx * 0.10, HINGE.y + 0.13, zg + 0.015))
        cb = bmesh.new()
        C.cyl_bm(cb, 0.04, -1, 1, seg=24, matrix=Matrix.Translation((xe + sx * 0.12, HINGE.y + 0.30, 0)))
        cut = C.mesh_obj("FootHole", cb, [])
        ob = C.mesh_obj("Bracket", bm, [steel])
        C.add_boolean(ob, cut).use_self = True
        C.add_bevel(ob, 0.008, segments=2, angle=30)
        out.append(C.finalize(ob, angle=38, remove=[cut]))
        nut = C.lathe("PivotNut", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.045, 0), (0.0, 0.05, 0)], [steel], steps=6)
        nut.matrix_world = (Matrix.Translation((xe + sx * 0.015, HINGE.y, HINGE.z))
                            @ (RY if sx > 0 else Matrix.Rotation(-math.pi / 2, 4, "Y")))
        C.add_bevel(nut, 0.008, segments=2, angle=30)
        out.append(C.finalize(nut, angle=38))
    return out


def build():
    grain = mat_grained("DashGrain", v=0.026, strength=0.45)
    bin_m = mat_grained("BinPP", v=0.03, rough=0.62, strength=0.25, scale=120.0)
    black = C.mat_black_plastic("FittingsPA", rough=0.5, color=0.025)
    satin = mat_satin()
    zinc = C.principled("ZincSteel", (0.60, 0.61, 0.62), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005, rough_var=0.05)
    steel = C.principled("BracketSteel", (0.05, 0.05, 0.055), rough=0.45)       # black e-coat
    C.add_noise_bump(steel, scale=300, strength=0.08, distance=0.0008)
    chrome = C.principled("RodChrome", (0.80, 0.80, 0.81), metallic=1.0, rough=0.12)
    felt = mat_felt("Felt", 0.12)
    flock = mat_felt("Flock", 0.085)
    swing = lid(grain, satin, black) + bin_shell(bin_m, flock) + bin_details(bin_m, black, zinc, felt, flock)
    C.transform_all(swing, open_matrix())
    bpy.context.view_layer.update()
    zg = min((o.matrix_world @ v.co).z for o in swing for v in o.data.vertices)
    return swing + damper(black, chrome, zinc) + hinge_brackets(steel, zg)


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("cassetto", objs, "cassetto.py",
            "car glovebox dropped open: curved black grained dashboard lid with latch handle, hinged at the bottom, "
            "bin with flocked interior and felt mat, hinge brackets and damper stay",
            az=30, el=17, lens=70, fill=0.86, **kw)
