"""Radiator cooling fan assembly (elettroventola) as removed from a small car, seen from
the engine side: black polypropylene shroud with perimeter lip, venturi ring around the
round opening, diagonal stiffening ribs and mounting lugs; 7-blade swept black fan
inside the ring; zinc-plated motor can held by four curved struts; wire in a corrugated
loom clipped along a strut down to a two-pin connector clipped to the shroud."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# shroud in the X-Z plane, engine side (motor) toward -Y. 1 unit ~ 10 cm
SW, SH = 3.80, 3.40
RO = 1.56                 # opening radius
RF = 1.47                 # fan tip radius
RH = 0.42                 # hub radius
YM = -0.34                # motor mount plane
NB = 7


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=64, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def tube(name, pts, r, mat, res=5):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def smooth_path(ctrl, n=12):
    """Catmull-Rom through control points (open)"""
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n):
            t = s / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


# ----------------------------------------------------------------- shroud
def shroud(pp):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, SW, 0.06, SH, center=(0, 0, 0))                     # plate
    t = 0.06
    for sz in (-1, 1):                                               # perimeter lip toward radiator
        C.box_bm(bm, SW, 0.40, t, center=(0, 0.17, sz * (SH / 2 - t / 2)))
    for sx in (-1, 1):
        C.box_bm(bm, t, 0.40, SH, center=(sx * (SW / 2 - t / 2), 0.17, 0))
    sh = C.mesh_obj("Shroud", bm, [pp])
    cb = bmesh.new()
    C.cyl_bm(cb, RO, -1, 1, seg=160, matrix=Matrix.Rotation(math.pi / 2, 4, "X"))
    # pressure-relief windows in the lower corners
    for sx in (-1, 1):
        C.box_bm(cb, 0.42, 1, 0.34, center=(sx * 1.55, 0, -1.32))
    cut = C.mesh_obj("Opening", cb, [pp])
    boolean(sh, cut)
    C.add_bevel(sh, 0.02, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    # venturi ring (protrudes to the engine side)
    P = [(RO, 0.03, 0), (RO + 0.07, 0.03, 0), (RO + 0.07, -0.20, 0), (RO + 0.03, -0.26, 0), (RO, -0.26, 0)]
    out.append(C.finalize(lathe_at("Venturi", P, [pp], (0, 0, 0), (0, 1, 0), steps=192), angle=40))
    # ribs: diagonal to the corners + one horizontal pair, on the engine face
    bm = bmesh.new()
    for a in (45, 135, 225, 315):
        d = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
        L = 2.45 - RO
        c = d * (RO + 0.05 + L / 2)
        M = Matrix.Translation(c + Vector((0, -0.09, 0))) @ Matrix.Rotation(-math.radians(a), 4, "Y")
        C.box_bm(bm, L, 0.18, 0.05, matrix=M)
    for sx in (-1, 1):
        C.box_bm(bm, SW / 2 - RO - 0.12, 0.14, 0.05, center=(sx * (RO + (SW / 2 - RO) / 2 + 0.02), -0.07, 0.0))
    rb = C.mesh_obj("Ribs", bm, [pp])
    C.add_bevel(rb, 0.012, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # relief-window flaps (rubber, slightly open)
    for sx in (-1, 1):
        bm = bmesh.new()
        C.box_bm(bm, 0.44, 0.012, 0.36, center=(0, 0, -0.18))
        fl = C.mesh_obj("Flap", bm, [rubber_m])
        fl.matrix_world = Matrix.Translation((sx * 1.55, 0.06, -1.32 + 0.18)) @ Matrix.Rotation(math.radians(-8), 4, "X")
        out.append(C.finalize(fl, angle=35))
    # mounting lugs: two hooks on top, two pegs at the bottom
    bm = bmesh.new()
    for sx in (-1, 1):
        C.box_bm(bm, 0.28, 0.12, 0.22, center=(sx * 1.25, 0.10, SH / 2 + 0.10))
        C.box_bm(bm, 0.28, 0.24, 0.06, center=(sx * 1.25, 0.20, SH / 2 + 0.18))
    lg = C.mesh_obj("Hooks", bm, [pp])
    C.add_bevel(lg, 0.02, segments=2, angle=30)
    out.append(C.finalize(lg, angle=35))
    for sx in (-1, 1):
        P = [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.09, 0.12, 0), (0.07, 0.14, 0), (0.07, 0.24, 0), (0.05, 0.26, 0), (0.0, 0.26, 0)]
        out.append(C.finalize(lathe_at("Peg", P, [pp], (sx * 1.25, 0.12, -SH / 2), (0, 0, -1), steps=32), angle=40))
    return out


# ----------------------------------------------------------------- fan
def blade(k, mat):
    bm = bmesh.new()
    nr, ns = 26, 12
    r0, r1 = RH - 0.03, RF
    base = math.tau * k / NB
    rows = []
    for i in range(nr + 1):
        u = i / nr
        r = r0 + (r1 - r0) * u
        sweep = 0.62 * u ** 1.6
        chord = 0.48 + 0.42 * u
        tip = 1.0
        if u > 0.86:
            tip = math.sqrt(max(0.0, 1 - ((u - 0.86) / 0.14) ** 2)) * 0.9 + 0.1
        beta = math.radians(38 - 16 * u)
        row = []
        for j in range(ns + 1):
            s = (j / ns - 0.5) * tip
            th = base + sweep + s * chord * math.cos(beta) / r
            y = -s * chord * math.sin(beta) + 0.045 * (1 - (2 * s) ** 2) * chord
            row.append(bm.verts.new((r * math.cos(th), y, r * math.sin(th))))
        rows.append(row)
    for i in range(nr):
        for j in range(ns):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    ob = C.mesh_obj("Blade", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.03
    so.offset = 0
    return C.finalize(ob, angle=60)


def fan(fan_m):
    out = [blade(k, fan_m) for k in range(NB)]
    # hub cup: closed toward the radiator (+Y), open toward the motor
    P = [(0.0, 0.30, 0), (RH - 0.06, 0.30, 0), (RH, 0.25, 0), (RH, -0.12, 0), (RH - 0.04, -0.12, 0),
         (RH - 0.04, 0.22, 0), (0.0, 0.22, 0)]
    out.append(C.finalize(lathe_at("Hub", [(r, -z, i) for (r, z, i) in P], [fan_m], (0, 0, 0), (0, -1, 0), steps=96), angle=40))
    return out


# ----------------------------------------------------------------- motor + struts
def motor(can, pp, steel):
    out = []
    P = [(0.0, 0.0, 0), (0.30, 0.0, 0), (0.34, 0.02, 0), (0.36, 0.06, 0), (0.36, 0.14, 0), (0.355, 0.15, 0),
         (0.37, 0.16, 0), (0.37, 0.48, 0), (0.355, 0.50, 0), (0.33, 0.55, 0), (0.20, 0.58, 0), (0.0, 0.58, 0)]
    vents = lambda r, z, t: r - (0.02 if (0.2 < z < 0.4 and math.cos(10 * t) > 0.7) else 0)
    out.append(C.finalize(lathe_at("MotorCan", P, [can], (0, YM + 0.02, 0), (0, -1, 0), steps=160, mod=vents), angle=40))
    # mount ring the struts attach to
    P = [(0.36, 0.0, 0), (0.50, 0.0, 0), (0.50, 0.08, 0), (0.36, 0.08, 0)]
    out.append(C.finalize(lathe_at("MountRing", P, [pp], (0, YM + 0.05, 0), (0, -1, 0), steps=96), angle=40))
    # shaft end / bearing boss on the back
    P = [(0.0, 0.58, 0), (0.10, 0.58, 0), (0.10, 0.64, 0), (0.0, 0.64, 0)]
    out.append(C.finalize(lathe_at("Boss", P, [steel], (0, YM + 0.02, 0), (0, -1, 0), steps=48), angle=40))
    # struts: swept arcs from the mount ring out to the shroud
    bm = bmesh.new()
    for k in range(4):
        a0 = math.radians(20 + 90 * k)
        frames = []
        n = 14
        for i in range(n + 1):
            u = i / n
            r = 0.46 + (RO + 0.30 - 0.46) * u
            a = a0 + 0.35 * u * u
            P0 = Vector((r * math.cos(a), YM - 0.02 + 0.30 * u * u, r * math.sin(a)))
            Ur = Vector((-math.sin(a), 0, math.cos(a)))
            frames.append((P0, Ur, Vector((0, 1, 0)), [(-0.045, -0.09), (0.045, -0.09), (0.045, 0.09), (-0.045, 0.09)]))
        C.sweep(bm, frames)
    C.fix_normals(bm)
    st = C.mesh_obj("Struts", bm, [pp])
    C.add_bevel(st, 0.015, segments=2, angle=30)
    out.append(C.finalize(st, angle=35))
    return out


def wiring(loom, plug, pin):
    out = []
    a = math.radians(20 + 90 * 3)     # follows the lower-right strut
    ctrl = [(0.18, YM - 0.50, -0.20), (0.30, YM - 0.40, -0.42)]
    for u in (0.25, 0.55, 0.85):
        r = 0.46 + (RO + 0.30 - 0.46) * u
        aa = a + 0.35 * u * u
        ctrl.append((r * math.cos(aa), YM - 0.16 + 0.30 * u * u, r * math.sin(aa)))
    ctrl += [(1.62, -0.13, -1.35), (1.62, -0.18, -1.65), (1.45, -0.26, -1.85)]
    pts = smooth_path(ctrl, 10)
    out.append(tube("Loom", pts, 0.055, loom, res=4))
    # two-pin connector at the end, clipped to the lower shroud edge
    end = pts[-1]
    d = (pts[-1] - pts[-3]).normalized()
    M = Matrix.Translation(end + d * 0.16) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    C.box_bm(bm, 0.30, 0.20, 0.34, matrix=M)
    C.box_bm(bm, 0.12, 0.08, 0.20, matrix=M @ Matrix.Translation((0, 0.13, 0.02)))
    pl = C.mesh_obj("Plug", bm, [plug])
    C.add_bevel(pl, 0.02, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    # loom clips on the strut
    for u in (0.35, 0.75):
        r = 0.46 + (RO + 0.30 - 0.46) * u
        aa = a + 0.35 * u * u
        p = Vector((r * math.cos(aa), YM - 0.12 + 0.30 * u * u, r * math.sin(aa)))
        M = Matrix.Translation(p) @ Matrix.Rotation(aa, 4, "Y").inverted()
        bm = bmesh.new()
        C.box_bm(bm, 0.10, 0.16, 0.16, matrix=M)
        cl = C.mesh_obj("Clip", bm, [plug])
        C.add_bevel(cl, 0.02, segments=2, angle=30)
        out.append(C.finalize(cl, angle=35))
    return out


rubber_m = None


def build():
    global rubber_m
    pp = C.mat_black_plastic("ShroudPP", rough=0.55, color=0.03)
    fan_m = C.mat_black_plastic("FanPA", rough=0.38, color=0.022)
    rubber_m = C.mat_rubber()
    can = C.principled("MotorZinc", (0.58, 0.58, 0.56), metallic=1.0, rough=0.38)
    C.add_noise_bump(can, scale=700, strength=0.05, distance=0.0005, rough_var=0.06)
    steel = C.principled("Steel", (0.5, 0.5, 0.5), metallic=1.0, rough=0.3)
    loom = C.mat_black_plastic("Loom", rough=0.5, color=0.02)
    nt = loom.node_tree
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 60.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED").inputs["Normal"])
    plug = C.mat_black_plastic("PlugPA", rough=0.4, color=0.05)
    objs = shroud(pp) + fan(fan_m) + motor(can, pp, steel) + wiring(loom, plug, steel)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("elettroventola", objs, "elettroventola.py",
            "radiator cooling fan assembly: black plastic shroud with round opening, 7-blade fan, electric motor on struts, wire with connector",
            az=28, el=18, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
