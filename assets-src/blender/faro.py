"""Car headlamp unit: black housing, clear polycarbonate lens, chrome reflector bowl,
projector lens module and a light-guide DRL strip."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

CX, CZ = -0.05, 0.03
NU = 160


def outline(u):
    a = math.tau * u
    c, s = math.cos(a), math.sin(a)
    n = 5.0
    x0 = math.copysign(abs(c) ** (2 / n), c)
    z0 = math.copysign(abs(s) ** (2 / n), s)
    X = x0
    t = (X + 1) / 2
    h = 0.40 - 0.15 * t
    zc = 0.10 * t ** 1.5
    return X, zc + h * z0


def y_edge(X):
    t = (X + 1) / 2
    return 0.32 * t * t


def scaled(u, s):
    X, Z = outline(u)
    return CX + s * (X - CX), CZ + s * (Z - CZ)


def grid_surface(name, fn, nv, mats, closed_u=True, center=None):
    """fn(u, v) -> Vector ; u in [0,1) around, v rows. center: Vector for a pole at v=0."""
    bm = bmesh.new()
    rows = []
    for j in range(nv + 1):
        v = j / nv
        rows.append([bm.verts.new(fn(i / NU, v)) for i in range(NU)])
    for j in range(nv):
        a, b = rows[j], rows[j + 1]
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((a[i], a[i2], b[i2], b[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    return bm


def lens_point(u, v):
    X, Z = outline(u)
    x = CX + v * (X - CX)
    z = CZ + v * (Z - CZ)
    y = y_edge(x) - 0.11 * (1 - v * v)
    return Vector((x, y, z))


def orient(bm, want_y_sign):
    bm.normal_update()
    ny = sum(f.normal.y * f.calc_area() for f in bm.faces)
    if ny * want_y_sign < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)


def lens(mat):
    bm = grid_surface("Lens", lens_point, 24, [mat])
    orient(bm, -1)
    ob = C.mesh_obj("Lens", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.016
    so.offset = -1
    return C.finalize(ob, angle=60)


def housing(mat):
    rings = [  # (scale, y-function)
        (1.000, lambda X: y_edge(X) + 0.004),
        (1.040, lambda X: y_edge(X) - 0.004),
        (1.068, lambda X: y_edge(X) + 0.030),
        (1.068, lambda X: y_edge(X) + 0.120),
        (1.000, lambda X: 0.56),
        (0.880, lambda X: 0.78),
    ]
    bm = bmesh.new()
    R = []
    for s, yf in rings:
        row = []
        for i in range(NU):
            X, Z = outline(i / NU)
            x, z = CX + s * (X - CX), CZ + s * (Z - CZ)
            row.append(bm.verts.new((x, yf(X), z)))
        R.append(row)
    for j in range(len(R) - 1):
        a, b = R[j], R[j + 1]
        for i in range(NU):
            i2 = (i + 1) % NU
            bm.faces.new((a[i], a[i2], b[i2], b[i]))
    c = bm.verts.new((CX, 0.80, CZ))
    last = R[-1]
    for i in range(NU):
        bm.faces.new((last[i], last[(i + 1) % NU], c))
    orient(bm, 1)  # fine for mostly-closed shell; fix_normals next
    C.fix_normals(bm)
    ob = C.mesh_obj("Housing", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.02
    so.offset = -1
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=40)


REF = (0.42, 0.205)   # reflector X, radius
PRJ = (-0.42, 0.215)  # projector X, hole radius
IND = (0.76, 0.092)   # indicator bowl


def zc_at(X):
    t = (X + 1) / 2
    return 0.10 * t ** 1.5


def plate_y(X):
    return y_edge(X) + 0.16


def bezel(mat):
    def fn(u, v):
        X, Z = outline(u)
        x = CX + 0.99 * v * (X - CX)
        z = CZ + 0.99 * v * (Z - CZ)
        return Vector((x, plate_y(x), z))
    bm = grid_surface("Bezel", fn, 18, [mat])
    orient(bm, -1)
    ob = C.mesh_obj("Bezel", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.012
    so.offset = 1
    cb = bmesh.new()
    R = Matrix.Rotation(math.radians(90), 4, "X")
    for X, r in (REF, PRJ, IND):
        C.cyl_bm(cb, r, -1, 1, seg=64, matrix=Matrix.Translation((X, 0, zc_at(X))) @ R)
    cut = C.mesh_obj("BezelCut", cb, [mat])
    C.add_boolean(ob, cut)
    return C.finalize(ob, angle=40, remove=[cut])


def place(ob, X, y):
    """local +Z (front) -> world -Y, at reflector/projector centre."""
    ob.matrix_world = Matrix.Translation((X, y, zc_at(X))) @ Matrix.Rotation(math.radians(90), 4, "X")
    return ob


def reflector(chrome, glass, REF=REF, f=0.075, bulb_scale=1.0):
    X, r = REF
    y0 = plate_y(X)
    prof = []
    N = 16
    for i in range(N + 1):
        rr = 0.03 + (r + 0.004 - 0.03) * i / N
        z = (rr * rr - (r + 0.004) ** 2) / (4 * f)
        prof.append((rr, z, 0))
    bowl = C.lathe("Bowl", prof, [chrome], steps=96, closed=False)
    so = bowl.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.006
    place(bowl, X, y0 + 0.004)
    bowl = C.finalize(bowl, angle=50)
    # chrome trim ring
    ring = C.lathe("RefRing", [(r - 0.004, 0.0, 0), (r + 0.012, 0.0, 0), (r + 0.016, -0.008, 0), (r + 0.008, -0.016, 0), (r - 0.004, -0.012, 0)], [chrome], steps=96)
    place(ring, X, y0 - 0.006)
    ring = C.finalize(ring, angle=50)
    # bulb: glass capsule with chrome tip
    zb = -(r * r) / (4 * f)  # bowl apex (local z)
    k = bulb_scale
    bulb = C.lathe("Bulb", [(0.0, zb + 0.13 * k, 0), (0.016 * k, zb + 0.125 * k, 0), (0.024 * k, zb + 0.10 * k, 0),
                            (0.024 * k, zb + 0.03 * k, 0), (0.0, zb + 0.03 * k, 0)], [glass], steps=48)
    place(bulb, X, y0)
    bulb = C.finalize(bulb, angle=60)
    tip = C.lathe("BulbTip", [(0.0, zb + 0.145 * k, 0), (0.018 * k, zb + 0.138 * k, 0), (0.026 * k, zb + 0.12 * k, 0),
                              (0.026 * k, zb + 0.112 * k, 0), (0.0, zb + 0.112 * k, 0)], [chrome], steps=48)
    place(tip, X, y0)
    tip = C.finalize(tip, angle=60)
    return [bowl, ring, bulb, tip]


def projector(chrome, glass, black):
    X, r = PRJ
    y0 = plate_y(X)
    shroud = C.lathe("Shroud", [(r + 0.004, 0.0, 0), (r - 0.012, -0.04, 0), (0.19, -0.08, 0), (0.186, -0.08, 0),
                                (r - 0.016, -0.04, 0), (r, 0.004, 0)], [chrome], steps=96)
    place(shroud, X, y0)
    shroud = C.finalize(shroud, angle=50)
    lr = 0.165
    lensP = [(0.0, 0.085, 0), (0.06, 0.078, 0), (0.105, 0.058, 0), (0.14, 0.032, 0), (0.16, 0.010, 0),
             (lr, 0.0, 0), (lr, -0.02, 0), (0.0, -0.02, 0)]
    pl = C.lathe("ProjLens", lensP, [glass], steps=96)
    place(pl, X, y0 - 0.02)
    pl = C.finalize(pl, angle=50)
    holder = C.lathe("Holder", [(lr - 0.004, 0.012, 0), (lr + 0.022, 0.012, 0), (lr + 0.026, 0.0, 0),
                                (lr + 0.026, -0.05, 0), (lr - 0.004, -0.05, 0)], [chrome], steps=96)
    place(holder, X, y0 - 0.02)
    holder = C.finalize(holder, angle=40)
    barrel = C.lathe("Barrel", [(lr - 0.005, -0.03, 0), (lr + 0.005, -0.03, 0), (lr + 0.005, -0.30, 0),
                                (0.0, -0.30, 0)], [black], steps=64, closed=False)
    place(barrel, X, y0 - 0.02)
    barrel = C.finalize(barrel, angle=40)
    return [shroud, pl, holder, barrel]


def light_guide(mat):
    cu = bpy.data.curves.new("DRL", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.027
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    us = [-0.075 + 0.525 * i / 80 for i in range(81)]
    sp.points.add(len(us) - 1)
    for p, u in zip(sp.points, us):
        x, z = scaled(u % 1.0, 0.86)
        p.co = (x, y_edge(x) + 0.085, z, 1)
    ob = C.link(bpy.data.objects.new("DRL", cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=60)


def tabs(mat):
    out = []
    specs = [  # x, y, z0, z1, width, plane
        (-0.55, 0.42, 0.30, 0.52, 0.17, "XZ"),
        (0.40, 0.47, 0.28, 0.48, 0.16, "XZ"),
    ]
    for X, y, z0, z1, wdt, _ in specs:
        bm = bmesh.new()
        C.box_bm(bm, wdt, 0.035, z1 - z0, center=(X, y, (z0 + z1) / 2))
        tb = C.mesh_obj("Tab", bm, [mat])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.034, -1, 1, seg=32, matrix=Matrix.Translation((X, y, z1 - 0.065)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        cut = C.mesh_obj("TabCut", cb, [mat])
        C.add_boolean(tb, cut)
        C.add_bevel(tb, 0.008, segments=2, angle=30)
        out.append(C.finalize(tb, angle=35, remove=[cut]))
    # side tab at the outer end
    bm = bmesh.new()
    C.box_bm(bm, 0.20, 0.035, 0.16, center=(1.04, 0.56, 0.10))
    tb = C.mesh_obj("TabS", bm, [mat])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.032, -1, 1, seg=32, matrix=Matrix.Translation((1.08, 0.56, 0.10)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    cut = C.mesh_obj("TabCut", cb, [mat])
    C.add_boolean(tb, cut)
    C.add_bevel(tb, 0.008, segments=2, angle=30)
    out.append(C.finalize(tb, angle=35, remove=[cut]))
    return out


def build():
    black = C.mat_black_plastic("HousingABS", rough=0.38)
    clear = C.mat_clear("LensPC")
    glass = C.mat_clear("Glass", ior=1.52)
    chrome = C.mat_chrome()
    bez = C.principled("BezelSatin", (0.20, 0.205, 0.215), metallic=1.0, rough=0.30)
    drl = C.principled("LightGuide", (0.92, 0.92, 0.92), rough=0.35)
    db = next(n for n in drl.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(db, "Transmission Weight", 0.15)
    C._set(db, "Emission Color", (1.0, 1.0, 1.0, 1))
    C._set(db, "Emission Strength", 0.6)
    amber = C.mat_clear("Amber", ior=1.5)
    C._set(next(n for n in amber.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Base Color", (1.0, 0.36, 0.02, 1))
    objs = [lens(clear), housing(black), bezel(bez), light_guide(drl)]
    objs += reflector(chrome, glass)
    objs += reflector(chrome, amber, REF=IND, f=0.04, bulb_scale=0.6)
    objs += projector(chrome, glass, black)
    objs += tabs(black)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("faro", objs, "faro.py",
            "car headlamp unit: black housing, clear lens, chrome reflector bowl, projector lens, DRL light guide",
            az=34, el=17, lens=70, fill=0.84)
