"""Upper front grille of a generic modern small hatchback, removed from the car (no badge).
Trapezoidal, slightly wrapped and raked: chrome outline strip on a gloss-black frame,
recessed black textured-plastic honeycomb insert, flat mounting rim; on the back, three
bolting tabs along the top edge, push-clip pegs along the bottom and screw lugs at the
ends. Car front is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
Z0, Z1 = 0.0, 0.150
HW0, HW1 = 0.330, 0.395


def hwz(z):
    return HW0 + (HW1 - HW0) * (z - Z0) / (Z1 - Z0)


def face_y(x, z):
    return 0.075 * (x / 0.40) ** 2 + 0.22 * (z - 0.075)


def lift3(q, dd=0.0):
    """2D (x, z) on the grille face -> 3D, dd behind the front plane."""
    return Vector((q.x, face_y(q.x, q.y) + dd, q.y))


def outline(inset=0.0, n_edge=60, n_arc=14):
    """Rounded trapezoid (x, z), counter-clockwise; corners bigger at the bottom."""
    rb, rt = 0.045 - inset * 0.5, 0.030 - inset * 0.5
    rb, rt = max(rb, 0.004), max(rt, 0.004)
    z0, z1 = Z0 + inset, Z1 - inset
    corners = [Vector((-(HW0 - inset * 1.1), z0)), Vector((HW0 - inset * 1.1, z0)),
               Vector((HW1 - inset * 1.1, z1)), Vector((-(HW1 - inset * 1.1), z1))]
    radii = [rb, rb, rt, rt]
    pts = []
    n = 4
    for i in range(n):
        a, c, b = corners[i - 1], corners[i], corners[(i + 1) % n]
        r = radii[i]
        p0 = c + (a - c).normalized() * r
        p2 = c + (b - c).normalized() * r
        # straight edge from previous corner end is added implicitly by resample
        for j in range(n_arc + 1):
            t = j / n_arc
            pts.append(p0 * (1 - t) ** 2 + c * 2 * t * (1 - t) + p2 * t * t)
    return P.resample(pts, 4 * (n_edge + n_arc), closed=True)


def inside(poly, q):
    n = len(poly)
    c = False
    for i in range(n):
        a, b = poly[i - 1], poly[i]
        if (a.y > q.y) != (b.y > q.y):
            x = a.x + (q.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if q.x < x:
                c = not c
    return c


def surround(chrome, gloss):
    path = outline(0.0)
    fr = P.frames_on_surface(path, lift3, OUT, closed=True)
    out = []
    out.append(P.tube_obj("Frame", fr, P.rrect(-0.006, 0.024, -0.045, 0.002, 0.004, seg=4), [gloss],
                          closed=True, smooth_angle=50))
    out.append(P.tube_obj("ChromeStrip", fr, P.rrect(-0.008, 0.011, -0.004, 0.0085, 0.0035, seg=5), [chrome],
                          closed=True, smooth_angle=60))
    return out


D0, D1 = 0.010, 0.030


def honeycomb(mat):
    bm = bmesh.new()
    R = 0.0128
    wall = 0.0026
    dx = math.sqrt(3) * R
    dz = 1.5 * R
    zone = outline(0.020)
    rows = int((Z1 - Z0) / dz) + 3
    cols = int(2 * HW1 / dx) + 3
    for r in range(rows):
        z = Z0 + 0.004 + r * dz
        for c in range(-cols // 2, cols // 2 + 1):
            s = c * dx + (dx / 2 if r % 2 else 0)
            q = Vector((s, z))
            if not inside(zone, q):
                continue
            hexo = [Vector((s + R * math.cos(math.radians(30 + 60 * k)), z + R * math.sin(math.radians(30 + 60 * k)))) for k in range(6)]
            hexi = [q + (h - q) * ((R - wall) / R) for h in hexo]
            V = {}
            for key, ring in (("o", hexo), ("i", hexi)):
                for dd in (D0, D1):
                    V[(key, dd)] = [bm.verts.new(lift3(h, dd)) for h in ring]
            for k in range(6):
                k2 = (k + 1) % 6
                fo, fi, bo, bi = V[("o", D0)], V[("i", D0)], V[("o", D1)], V[("i", D1)]
                bm.faces.new((fo[k], fo[k2], fi[k2], fi[k]))
                bm.faces.new((fi[k], fi[k2], bi[k2], bi[k]))
                bm.faces.new((bo[k], bo[k2], fo[k2], fo[k]))
                bm.faces.new((bi[k], bi[k2], bo[k2], bo[k]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    C.fix_normals(bm)
    ob = C.mesh_obj("Honeycomb", bm, [mat])
    return C.finalize(ob, angle=30)


def rim(mat):
    """Flat textured band between the frame and the honeycomb (hides the clipped cells)."""
    a = outline(0.0)
    b = outline(0.034)
    rows = [[lift3(p.lerp(q, t), D0 - 0.0006) for p, q in zip(a, b)] for t in (0.0, 0.5, 1.0)]
    ob = P.grid_obj("Rim", rows, [mat], OUT, closed_u=True)
    P.solidify(ob, D1 - D0, offset=-1)
    return C.finalize(ob, angle=40)


def back_tabs(mat):
    out = []
    # bolting tabs rising from the back of the top edge (screwed to the slam panel)
    for x in (-0.24, 0.0, 0.24):
        z = Z1 - 0.004
        y = face_y(x, z) + 0.036
        bm = bmesh.new()
        C.box_bm(bm, 0.042, 0.004, 0.040, center=(x, y, z + 0.016))
        for dx in (-0.019, 0.019):                                              # side gussets
            C.box_bm(bm, 0.003, 0.014, 0.016, center=(x + dx, y + 0.007, z + 0.004))
        ob = C.mesh_obj("TopTab", bm, [mat])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.0055, -0.03, 0.03, seg=24, matrix=Matrix.Translation((x, y, z + 0.024)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        cut = C.mesh_obj("TabHole", cb, [mat])
        C.add_boolean(ob, cut)
        C.add_bevel(ob, 0.0012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
    # push-clip pegs along the bottom
    for x in (-0.20, -0.07, 0.07, 0.20):
        z = Z0 + 0.012
        y = face_y(x, z) + 0.045
        M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        peg = C.lathe("Clip", [(0.0, 0.0, 0), (0.0085, 0.0, 0), (0.0085, 0.004, 0), (0.004, 0.006, 0), (0.004, 0.016, 0),
                               (0.0068, 0.020, 0), (0.0068, 0.024, 0), (0.0028, 0.034, 0), (0.0, 0.035, 0)], [mat], steps=32)
        peg.matrix_world = M
        out.append(C.finalize(peg, angle=40))
    # screw lugs at the ends (pointing sideways)
    for sx in (-1, 1):
        z = 0.085
        x = sx * (hwz(z) + 0.004)
        y = face_y(x, z) + 0.03
        bm = bmesh.new()
        C.box_bm(bm, 0.040, 0.0035, 0.034, center=(x + sx * 0.016, y, z))
        ob = C.mesh_obj("Lug", bm, [mat])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.0055, -0.03, 0.03, seg=24, matrix=Matrix.Translation((x + sx * 0.024, y, z)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        cut = C.mesh_obj("LugHole", cb, [mat])
        C.add_boolean(ob, cut)
        C.add_bevel(ob, 0.0012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
    return out


def build():
    chrome = C.mat_chrome()
    gloss = C.principled("GlossBlack", (0.010, 0.010, 0.011), rough=0.10, Coat_Weight=0.8)
    tex = P.textured_black("GrilleTexPP", rough=0.62, v=0.022)
    raw = P.textured_black("RawPP", rough=0.58, v=0.03)
    objs = surround(chrome, gloss)
    objs.append(rim(tex))
    objs.append(honeycomb(tex))
    objs += back_tabs(raw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("calandra", objs, "calandra.py",
            "front grille (generic small hatchback, no badge): black textured honeycomb insert, chrome outline strip on "
            "gloss-black frame, mounting tabs and push clips on the back",
            az=-26, el=20, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
