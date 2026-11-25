"""Tyre repair / inflation kit (kit gonfiaggio) from a small car without spare wheel:
compact 12 V compressor in a dark grey plastic housing with rubber base, round
pressure gauge (blank dial with tick marks, red needle, clear window), rocker
switch, air hose with screw-on valve connector, power lead with 12 V plug, and the
sealant bottle with black cap and plain label band. No brand or text."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm
GAUGE_C = Vector((-0.30, -0.12, 0.80))
GAUGE_N = Vector((0.0, -0.45, 1.0)).normalized()


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def rbox(name, size, center, mat, bevel, seg=5):
    bm = bmesh.new()
    C.box_bm(bm, *size, center=center)
    ob = C.mesh_obj(name, bm, [mat])
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width = bevel
    b.segments = seg
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(30)
    b.use_clamp_overlap = True
    return C.finalize(ob, angle=40)


def dial_image():
    import numpy as np
    n = 512
    img = np.ones((n, n, 4), dtype=np.float32)
    y, x = np.mgrid[0:n, 0:n]
    cx = cy = (n - 1) / 2
    r = np.hypot(x - cx, y - cy) / (n / 2)
    a = np.degrees(np.arctan2(y - cy, x - cx))       # image y up = +a
    img[..., :3] = 0.93
    # sweep from 225 deg (low) clockwise to -45 deg (high)
    s = (225 - a) % 360                                 # 0..270 along the scale
    on = s <= 270
    for step, r0, w in ((27.0, 0.70, 1.6), (5.4, 0.78, 0.8)):
        k = np.abs(((s + step / 2) % step) - step / 2)
        m = on & (k < w) & (r > r0) & (r < 0.90)
        img[m, :3] = 0.06
    band = on & (r > 0.905) & (r < 0.925)
    img[band, :3] = 0.06
    red = (s > 230) & on & (r > 0.86) & (r < 0.90)
    img[red] = (0.65, 0.05, 0.03, 1)
    # blank maker plate area (grey bar, no text)
    m = (np.abs(x - cx) < n * 0.13) & (y - cy < -n * 0.16) & (y - cy > -n * 0.21)
    img[m, :3] = 0.55
    im = bpy.data.images.new("Dial", n, n, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.pack()
    return im


def gauge(bezel_m, face_m, needle_m, glass_m):
    out = []
    M = axis_mat(GAUGE_C, GAUGE_N)
    P = [(0.25, -0.10, 0), (0.33, -0.10, 0), (0.345, 0.02, 0), (0.335, 0.055, 0), (0.30, 0.07, 0), (0.27, 0.065, 0), (0.25, 0.02, 0)]
    ob = C.lathe("Bezel", P, [bezel_m], steps=96)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=40))
    # dial face disc with UVs
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    n = 96
    c = bm.verts.new((0, 0, 0.005))
    ring = [bm.verts.new((0.255 * math.cos(math.tau * i / n), 0.255 * math.sin(math.tau * i / n), 0.005)) for i in range(n)]
    for i in range(n):
        f = bm.faces.new((c, ring[i], ring[(i + 1) % n]))
        for l in f.loops:
            l[uv].uv = (0.5 + l.vert.co.x / 0.51, 0.5 + l.vert.co.y / 0.51)
    face = C.mesh_obj("DialFace", bm, [face_m])
    face.matrix_world = M
    out.append(face)
    # needle pointing at ~60 % of the scale
    ang = math.radians(225 - 0.55 * 270)
    bm = bmesh.new()
    C.box_bm(bm, 0.22, 0.014, 0.008, center=(0.09, 0, 0.018), matrix=Matrix.Rotation(ang, 4, "Z"))
    C.cyl_bm(bm, 0.028, 0.01, 0.03, seg=24)
    out.append(C.mesh_obj("Needle", bm, [needle_m]))
    out[-1].matrix_world = M
    # domed window
    P = [(0.0, 0.075, 0), (0.12, 0.071, 0), (0.22, 0.062, 0), (0.275, 0.05, 0), (0.275, 0.04, 0), (0.0, 0.066, 0)]
    ob = C.lathe("Window", P, [glass_m], steps=96)
    ob.matrix_world = M
    out.append(C.finalize(ob, angle=50))
    return out


def tube(name, pts, radius, mat, res=12):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.resolution_u = res
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=60)


def compressor(housing, base_m, rubber, switch_m, brass, steel, red_m, cable_m):
    out = []
    out.append(rbox("Housing", (1.55, 1.05, 0.62), (0, 0, 0.47), housing, 0.16, 6))
    out.append(rbox("Base", (1.62, 1.12, 0.20), (0, 0, 0.10), base_m, 0.08, 4))
    # raised top deck where gauge and switch sit
    out.append(rbox("Deck", (1.25, 0.80, 0.10), (0.0, 0.0, 0.78), base_m, 0.05, 3))
    # rocker switch
    out.append(rbox("SwitchFrame", (0.30, 0.22, 0.06), (0.42, -0.08, 0.84), base_m, 0.02, 2))
    sw = rbox("Rocker", (0.22, 0.15, 0.06), (0.42, -0.08, 0.875), switch_m, 0.02, 2)
    sw.matrix_world = Matrix.Translation((0.42, -0.08, 0.875)) @ Matrix.Rotation(math.radians(10), 4, "Y") @ Matrix.Translation((-0.42, 0.08, -0.875))
    out.append(sw)
    # side vent slots (moulded grille) on the front face
    bm = bmesh.new()
    for i in range(6):
        C.box_bm(bm, 0.05, 0.03, 0.28, center=(0.25 + i * 0.09, -0.535, 0.45))
    out.append(C.mesh_obj("Vents", bm, [base_m]))
    # rubber feet strip / grip
    # air hose: from the right side, loops out in front, ends in the valve connector
    hose_pts = [(0.80, -0.20, 0.36), (1.05, -0.30, 0.30), (1.15, -0.60, 0.08), (0.80, -1.05, 0.045),
                (0.10, -1.20, 0.045), (-0.55, -1.00, 0.045), (-0.70, -0.75, 0.045)]
    out.append(tube("Hose", hose_pts, 0.045, rubber))
    out.append(C.finalize(C.lathe("Gland", [(0.0, -0.02, 0), (0.08, -0.02, 0), (0.085, 0.10, 0), (0.06, 0.13, 0), (0.0, 0.13, 0)], [base_m], steps=32), angle=40))
    out[-1].matrix_world = axis_mat(Vector((0.77, -0.19, 0.36)), Vector((1.0, -0.35, -0.1)))
    # screw-on valve connector at the end of the hose
    d = (Vector((-0.70, -0.75, 0.045)) - Vector((-0.55, -1.00, 0.045))).normalized()
    knurl = lambda r, z, t: r + (0.008 if (r > 0.07 and 0.08 < z < 0.22 and math.cos(24 * t) > 0) else 0.0)
    P = [(0.0, -0.02, 0), (0.055, -0.02, 0), (0.06, 0.05, 0), (0.085, 0.08, 0), (0.085, 0.22, 0),
         (0.07, 0.25, 0), (0.07, 0.30, 0), (0.0, 0.30, 0)]
    ob = C.lathe("Connector", P, [brass], steps=96, mod=knurl)
    ob.matrix_world = axis_mat(Vector((-0.69, -0.77, 0.045)) + Vector((0, 0, 0.042)), d)
    out.append(C.finalize(ob, angle=45))
    # power lead out of the back, coiled loop, 12 V plug
    cab_pts = [(-0.55, 0.50, 0.30), (-0.80, 0.70, 0.12), (-1.25, 0.70, 0.035), (-1.55, 0.25, 0.035),
               (-1.40, -0.25, 0.035), (-1.05, -0.40, 0.035)]
    out.append(tube("Cable", cab_pts, 0.035, cable_m))
    d = (Vector(cab_pts[-1]) - Vector(cab_pts[-2])).normalized()
    P = [(0.0, -0.05, 0), (0.06, -0.05, 0), (0.10, 0.08, 0), (0.115, 0.30, 0), (0.105, 0.36, 0),
         (0.09, 0.40, 0), (0.09, 0.62, 0), (0.07, 0.64, 0), (0.0, 0.64, 0)]
    ob = C.lathe("Plug", P, [base_m], steps=64)
    o = Vector(cab_pts[-1]) + Vector((0, 0, 0.115 - 0.035))
    ob.matrix_world = axis_mat(o, d)
    out.append(C.finalize(ob, angle=40))
    P = [(0.0, 0.64, 0), (0.035, 0.64, 0), (0.035, 0.72, 0), (0.0, 0.72, 0)]
    ob = C.lathe("PlugTip", P, [steel], steps=32)
    ob.matrix_world = axis_mat(o, d)
    out.append(C.finalize(ob, angle=40))
    bm = bmesh.new()
    for s in (-1, 1):
        C.box_bm(bm, 0.025, 0.06, 0.16, center=(s * 0.095, 0, 0.52))
    ob = C.mesh_obj("PlugSprings", bm, [steel])
    ob.matrix_world = axis_mat(o, d)
    out.append(ob)
    P = [(0.0, 0.36, 0), (0.108, 0.36, 0), (0.108, 0.40, 0), (0.0, 0.40, 0)]
    ob = C.lathe("PlugRing", P, [red_m], steps=48)
    ob.matrix_world = axis_mat(o, d)
    out.append(C.finalize(ob, angle=40))
    return out


def bottle(hdpe, cap_m, label_m):
    out = []
    x, y = 1.30, 0.42
    P = [(0.0, 0.0, 0), (0.28, 0.0, 0), (0.33, 0.04, 0), (0.335, 0.12, 0), (0.335, 1.02, 0), (0.32, 1.10, 0),
         (0.24, 1.20, 0), (0.15, 1.24, 0), (0.14, 1.30, 0), (0.0, 1.30, 0)]
    ob = C.lathe("Bottle", P, [hdpe], steps=96)
    ob.matrix_world = Matrix.Translation((x, y, 0))
    out.append(C.finalize(ob, angle=40))
    P = [(0.338, 0.30, 0), (0.341, 0.30, 0), (0.341, 0.86, 0), (0.338, 0.86, 0)]
    ob = C.lathe("Label", P, [label_m], steps=96)
    ob.matrix_world = Matrix.Translation((x, y, 0))
    out.append(C.finalize(ob, angle=40))
    knurl = lambda r, z, t: r + (0.01 if (r > 0.17 and math.cos(40 * t) > 0) else 0.0)
    P = [(0.0, 1.28, 0), (0.175, 1.28, 0), (0.18, 1.30, 0), (0.18, 1.48, 0), (0.165, 1.50, 0), (0.0, 1.50, 0)]
    ob = C.lathe("Cap", P, [cap_m], steps=160, mod=knurl)
    ob.matrix_world = Matrix.Translation((x, y, 0))
    out.append(C.finalize(ob, angle=50))
    return out


def build():
    housing = C.mat_black_plastic("HousingABS", rough=0.42, color=0.075)
    base_m = C.mat_black_plastic("BaseABS", rough=0.5, color=0.022)
    rubber = C.principled("HoseRubber", (0.03, 0.03, 0.03), rough=0.5)
    C.add_noise_bump(rubber, scale=300, strength=0.05, distance=0.0005)
    cable = C.principled("CablePVC", (0.025, 0.025, 0.026), rough=0.4)
    switch = C.principled("SwitchOrange", C.srgb("#D9570F"), rough=0.4)
    brass = C.principled("Brass", C.srgb("#B89150"), metallic=1.0, rough=0.28)
    steel = C.principled("Steel", (0.7, 0.7, 0.71), metallic=1.0, rough=0.22)
    red = C.principled("RedPP", C.srgb("#B3120F"), rough=0.4)
    bezel = C.mat_chrome("BezelChrome")
    face = C.mat_label(dial_image(), "DialMat", rough=0.4)
    needle = C.principled("Needle", C.srgb("#C8160F"), rough=0.35)
    glass = C.mat_clear("Window")
    hdpe = C.principled("HDPE", (0.86, 0.86, 0.84), rough=0.42, **{"Subsurface Weight": 0.3, "Subsurface Radius": (0.2, 0.2, 0.2)})
    cap = C.mat_black_plastic("CapPP", rough=0.45, color=0.03)
    label = C.principled("LabelOrange", C.srgb("#E0741B"), rough=0.35)
    objs = compressor(housing, base_m, rubber, switch, brass, steel, red, cable) + gauge(bezel, face, needle, glass) + bottle(hdpe, cap, label)
    C.transform_all(objs, Matrix.Rotation(math.radians(-14), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("kit-gonfiaggio", objs, "kit-gonfiaggio.py",
            "tyre repair kit: compact 12V compressor with round pressure gauge, air hose and power plug, sealant bottle",
            az=26, el=30, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
