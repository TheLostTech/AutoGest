"""Lower front bumper grille insert, generic small hatchback: long, narrow, wrapped and
raked black grained-polypropylene insert with a recessed honeycomb mesh inside a plain
textured frame with a slightly glossier inner lip; on the back, four snap hooks rising
from the top edge, three push-clip pegs along the bottom and a screw lug at each end.
Same construction as calandra.py, made to fit the lower bumper opening. Car front is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
Z0, Z1 = 0.0, 0.098
HW0, HW1 = 0.285, 0.255          # half width at the bottom / top edge
D0, D1 = 0.008, 0.026


def hwz(z):
    return HW0 + (HW1 - HW0) * (z - Z0) / (Z1 - Z0)


def face_y(x, z):
    return 0.095 * (x / 0.30) ** 2 - 0.16 * (z - 0.05)


def lift3(q, dd=0.0):
    return Vector((q.x, face_y(q.x, q.y) + dd, q.y))


def outline(inset=0.0, n_edge=70, n_arc=16):
    """Rounded trapezoid (x, z), counter-clockwise; big radius at the outer ends."""
    z0, z1 = Z0 + inset, Z1 - inset
    corners = [Vector((-(HW0 - inset * 1.1), z0)), Vector((HW0 - inset * 1.1, z0)),
               Vector((HW1 - inset * 1.1, z1)), Vector((-(HW1 - inset * 1.1), z1))]
    radii = [max(0.040 - inset * 0.6, 0.004), max(0.040 - inset * 0.6, 0.004),
             max(0.024 - inset * 0.5, 0.004), max(0.024 - inset * 0.5, 0.004)]
    pts = []
    for i in range(4):
        a, c, b = corners[i - 1], corners[i], corners[(i + 1) % 4]
        r = radii[i]
        p0 = c + (a - c).normalized() * r
        p2 = c + (b - c).normalized() * r
        for j in range(n_arc + 1):
            t = j / n_arc
            pts.append(p0 * (1 - t) ** 2 + c * 2 * t * (1 - t) + p2 * t * t)
    return P.resample(pts, 4 * (n_edge + n_arc), closed=True)


def inside(poly, q):
    c = False
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        if (a.y > q.y) != (b.y > q.y):
            x = a.x + (q.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if q.x < x:
                c = not c
    return c


def surround(tex, lip_m):
    fr = P.frames_on_surface(outline(0.0), lift3, OUT, closed=True)
    out = [P.tube_obj("Frame", fr, P.rrect(-0.004, 0.017, -0.040, 0.002, 0.0035, seg=4), [tex], closed=True, smooth_angle=50)]
    fr2 = P.frames_on_surface(outline(0.0135), lift3, OUT, closed=True)
    out.append(P.tube_obj("InnerLip", fr2, P.rrect(-0.0035, 0.0030, -0.012, 0.0005, 0.0018, seg=3), [lip_m],
                          closed=True, smooth_angle=55))
    return out


def honeycomb(mat):
    bm = bmesh.new()
    R = 0.0105
    wall = 0.0024
    dx = math.sqrt(3) * R
    dz = 1.5 * R
    zone = outline(0.015)
    rows = int((Z1 - Z0) / dz) + 3
    cols = int(2 * HW0 / dx) + 3
    for r in range(rows):
        z = Z0 + 0.003 + r * dz
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
    a = outline(0.0)
    b = outline(0.026)
    rows = [[lift3(p.lerp(q, t), D0 - 0.0006) for p, q in zip(a, b)] for t in (0.0, 0.5, 1.0)]
    ob = P.grid_obj("Rim", rows, [mat], OUT, closed_u=True)
    P.solidify(ob, D1 - D0, offset=-1)
    return C.finalize(ob, angle=40)


def back_fixings(mat):
    out = []
    # snap hooks rising from the back of the top edge
    for x in (-0.18, -0.06, 0.06, 0.18):
        z = Z1 - 0.003
        y = face_y(x, z) + 0.030
        bm = bmesh.new()
        C.box_bm(bm, 0.016, 0.0028, 0.026, center=(x, y, z + 0.010))                 # tongue
        C.box_bm(bm, 0.016, 0.0055, 0.004, center=(x, y - 0.0035, z + 0.019))        # barb (towards the front)
        C.box_bm(bm, 0.0026, 0.010, 0.012, center=(x - 0.0067, y + 0.004, z + 0.002))
        C.box_bm(bm, 0.0026, 0.010, 0.012, center=(x + 0.0067, y + 0.004, z + 0.002))
        ob = C.mesh_obj("SnapHook", bm, [mat])
        C.add_bevel(ob, 0.0006, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    # push-clip pegs along the bottom
    for x in (-0.15, 0.0, 0.15):
        z = Z0 + 0.010
        y = face_y(x, z) + 0.040
        M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        peg = C.lathe("Clip", [(0.0, 0.0, 0), (0.0080, 0.0, 0), (0.0080, 0.004, 0), (0.0038, 0.006, 0), (0.0038, 0.015, 0),
                               (0.0064, 0.019, 0), (0.0064, 0.023, 0), (0.0026, 0.032, 0), (0.0, 0.033, 0)], [mat], steps=32)
        peg.matrix_world = M
        out.append(C.finalize(peg, angle=40))
    # screw lugs at the ends
    for sx in (-1, 1):
        z = 0.05
        x = sx * (hwz(z) + 0.002)
        y = face_y(x, z) + 0.028
        bm = bmesh.new()
        C.box_bm(bm, 0.036, 0.0035, 0.030, center=(x + sx * 0.014, y, z))
        ob = C.mesh_obj("Lug", bm, [mat])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.0052, -0.03, 0.03, seg=24, matrix=Matrix.Translation((x + sx * 0.022, y, z)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        cut = C.mesh_obj("LugHole", cb, [mat])
        C.add_boolean(ob, cut)
        C.add_bevel(ob, 0.0012, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
    return out


def build():
    tex = P.textured_black("GrillePP", rough=0.62, v=0.022)
    lip = C.mat_black_plastic("LipPP", rough=0.32, color=0.018)
    raw = P.textured_black("RawPP", rough=0.58, v=0.03)
    objs = surround(tex, lip)
    objs.append(rim(tex))
    objs.append(honeycomb(tex))
    objs += back_fixings(raw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("griglia-paraurti", objs, "griglia-paraurti.py",
            "lower bumper grille insert (generic small hatchback): long black grained plastic honeycomb insert in a "
            "textured frame, snap hooks and push clips on the back",
            az=-28, el=24, lens=70, fill=0.9, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
