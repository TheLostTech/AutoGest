"""Cabin blower motor (ventola / motorino ventilazione abitacolo) as removed from the heater
box of a small car: black polypropylene squirrel-cage fan wheel (many thin forward-curved
blades between the back plate and a stiffening ring, conical hub with retaining clip on
the shaft), mounted on the motor whose black plastic flange carries three bayonet ears,
a cooling-air tube and the integrated connector; zinc-plated motor can with vent slots
and rear bearing boss underneath."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm. Motor axis = Z, wheel on top.
RW, RIN, HW = 7.2, 6.0, 6.2     # wheel outer radius, blade inner radius, blade height
ZW = 0.6                        # wheel back-plate top
NB = 42
RF = 8.6                        # flange radius


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin=(0, 0, 0), axis=(0, 0, 1), steps=64, bevel=None, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), matrix=None, bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center, matrix=matrix)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=35)


def tube(name, pts, r, mat, res=4):
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


# ----------------------------------------------------------------- wheel
def wheel(pp, steel):
    out = []
    bm = bmesh.new()
    th = 0.13
    for k in range(NB):
        a0 = math.tau * k / NB
        sec = []
        n = 7
        for i in range(n + 1):
            u = i / n
            r = RIN + (RW - 0.05 - RIN) * u
            a = a0 + 0.20 * u - 0.10 * u * u          # forward curve
            sec.append((r, a))
        outer, inner = [], []
        for i, (r, a) in enumerate(sec):
            # normal in plan ~ tangential direction
            p = Vector((r * math.cos(a), r * math.sin(a)))
            if i < n:
                q = Vector((sec[i + 1][0] * math.cos(sec[i + 1][1]), sec[i + 1][0] * math.sin(sec[i + 1][1])))
            else:
                q = p + (p - Vector((sec[i - 1][0] * math.cos(sec[i - 1][1]), sec[i - 1][0] * math.sin(sec[i - 1][1]))))
            t = (q - p).normalized()
            nrm = Vector((-t.y, t.x)) * (th / 2)
            outer.append(p + nrm)
            inner.append(p - nrm)
        ring = outer + inner[::-1]
        vb = [bm.verts.new((p.x, p.y, ZW - 0.05)) for p in ring]
        vt = [bm.verts.new((p.x, p.y, ZW + HW + 0.05)) for p in ring]
        m = len(ring)
        bm.faces.new(vb[::-1])
        bm.faces.new(vt)
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    C.fix_normals(bm)
    bl = C.mesh_obj("Blades", bm, [pp])
    C.add_bevel(bl, 0.03, segments=1, angle=30)
    out.append(C.finalize(bl, angle=35))
    # top stiffening ring and a mid-height ring
    P = [(RIN - 0.25, ZW + HW, 0), (RW + 0.12, ZW + HW, 0), (RW + 0.12, ZW + HW + 0.35, 0), (RW - 0.1, ZW + HW + 0.45, 0),
         (RIN - 0.25, ZW + HW + 0.45, 0)]
    out.append(lathe_at("TopRing", P, [pp], steps=192, bevel=0.04))
    # back plate with conical hub rising inside the blade ring
    P = [(0.0, 0.0, 0), (RW + 0.15, 0.0, 0), (RW + 0.15, ZW, 0), (RIN - 0.4, ZW, 0), (5.2, ZW + 0.4, 0), (3.6, ZW + 2.0, 0),
         (2.0, ZW + 3.6, 0), (1.3, ZW + 4.0, 0), (1.3, ZW + 4.4, 0), (0.0, ZW + 4.4, 0)]
    out.append(lathe_at("HubPlate", P, [pp], steps=160, bevel=0.05))
    # radial ribs on the hub cone
    bm = bmesh.new()
    for k in range(6):
        a = math.tau * k / 6
        M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((3.0, 0, ZW + 2.2)) @ Matrix.Rotation(math.radians(-45), 4, "Y")
        C.box_bm(bm, 2.8, 0.22, 0.4, matrix=M)
    rb = C.mesh_obj("HubRibs", bm, [pp])
    C.add_bevel(rb, 0.06, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # shaft end with push-on retaining clip
    out.append(lathe_at("Shaft", [(0.0, ZW + 4.3, 0), (0.4, ZW + 4.3, 0), (0.4, ZW + 5.0, 0), (0.33, ZW + 5.08, 0), (0.0, ZW + 5.08, 0)],
                        [steel], steps=32))
    out.append(lathe_at("Clip", [(0.4, ZW + 4.4, 0), (0.95, ZW + 4.4, 0), (1.0, ZW + 4.48, 0), (0.95, ZW + 4.56, 0), (0.4, ZW + 4.56, 0)],
                        [steel], steps=6))
    return out


# ----------------------------------------------------------------- motor / flange
def flange(pp, zinc, pin):
    out = []
    z0 = -0.5
    P = [(3.4, z0 - 1.6, 0), (RF - 1.4, z0 - 1.0, 0), (RF, z0 - 0.5, 0), (RF, z0 + 0.15, 0), (RF - 0.3, z0 + 0.3, 0),
         (RW + 0.6, z0 + 0.3, 0), (RW + 0.6, z0 + 0.6, 0), (RW + 0.3, z0 + 0.6, 0), (RW + 0.3, z0 + 0.35, 0), (3.4, z0 + 0.35, 0)]
    out.append(lathe_at("Flange", P, [pp], steps=192, bevel=0.06))
    # three bayonet ears with screw holes
    for k in range(3):
        a = math.tau * k / 3 + math.radians(20)
        bm = bmesh.new()
        M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((RF + 0.7, 0, z0 - 0.15))
        C.box_bm(bm, 2.2, 2.2, 0.4, matrix=M)
        ob = C.mesh_obj("Ear", bm, [pp])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.35, -3, 3, seg=32, matrix=Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((RF + 1.1, 0, 0)))
        cut = C.mesh_obj("EarHole", cb, [pp])
        bo = C.add_boolean(ob, cut)
        bo.use_self = True
        C.add_bevel(ob, 0.15, segments=3, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
    # radial ribs under the flange
    bm = bmesh.new()
    for k in range(12):
        a = math.tau * k / 12
        M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((5.4, 0, z0 - 0.9)) @ Matrix.Rotation(math.radians(-14), 4, "Y")
        C.box_bm(bm, 3.6, 0.22, 0.9, matrix=M)
    rb = C.mesh_obj("FlangeRibs", bm, [pp])
    C.add_bevel(rb, 0.06, segments=1, angle=30)
    out.append(C.finalize(rb, angle=35))
    # cooling-air tube: scoop on the rim curling down into the motor
    a = math.radians(-70)
    d = Vector((math.cos(a), math.sin(a), 0))
    ctrl = [d * (RF - 0.3) + Vector((0, 0, z0 + 0.6)), d * (RF + 0.6) + Vector((0, 0, z0 - 0.4)), d * (RF - 0.6) + Vector((0, 0, z0 - 2.2)),
            d * 4.6 + Vector((0, 0, z0 - 3.0))]
    out.append(tube("AirTube", smooth_path(ctrl, 10), 0.55, pp, res=5))
    # connector shroud on the flange underside, mouth facing outward
    a = math.radians(-115)
    M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((RF - 0.6, 0, z0 - 1.7))
    bm = bmesh.new()
    C.box_bm(bm, 2.0, 2.4, 1.6, matrix=M)
    sh = C.mesh_obj("Shroud", bm, [pp])
    cb = bmesh.new()
    C.box_bm(cb, 2.0, 2.0, 1.2, matrix=M @ Matrix.Translation((0.45, 0, 0)))
    cut = C.mesh_obj("ShroudCut", cb, [pp])
    bo = C.add_boolean(sh, cut)
    bo.use_self = True
    C.add_bevel(sh, 0.08, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    bm = bmesh.new()
    for sy in (-0.45, 0.45):
        C.box_bm(bm, 1.4, 0.5, 0.08, matrix=M @ Matrix.Translation((0.3, sy, 0)))
    C.box_bm(bm, 0.7, 0.9, 0.25, matrix=M @ Matrix.Translation((0.9, 0, 0.9)))
    pn = C.mesh_obj("Pins", bm, [pin])
    out.append(C.finalize(pn, angle=35))
    # motor can below
    zc = z0 - 1.4
    def vents(r, z, t):
        if abs(r - 3.6) < 1e-6 and zc - 3.2 < z < zc - 2.0 and math.cos(8 * t) > 0.75:
            return r - 0.12
        return r
    P = [(0.0, zc - 5.0, 0), (1.0, zc - 5.0, 0), (1.1, zc - 4.6, 0), (2.8, zc - 4.55, 0), (3.4, zc - 4.3, 0), (3.6, zc - 3.9, 0)]
    P += [(3.6, zc - 3.9 + 3.6 * i / 40, 0) for i in range(41)]
    P += [(3.75, zc - 0.25, 0), (3.75, zc + 0.1, 0), (0.0, zc + 0.1, 0)]
    out.append(lathe_at("MotorCan", P, [zinc], steps=192, mod=vents))
    return out


def build():
    pp = C.mat_black_plastic("WheelPP", rough=0.48, color=0.03)
    fl = C.mat_black_plastic("FlangePP", rough=0.55, color=0.032)
    steel = C.principled("Steel", (0.60, 0.60, 0.60), metallic=1.0, rough=0.28)
    zinc = C.principled("MotorZinc", (0.60, 0.60, 0.58), metallic=1.0, rough=0.36)
    C.add_noise_bump(zinc, scale=60, strength=0.05, distance=0.003, rough_var=0.06)
    pin = C.principled("TinPin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.22)
    objs = wheel(pp, steel) + flange(fl, zinc, pin)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("ventola-abitacolo", objs, "ventola-abitacolo.py",
            "cabin blower motor: black squirrel-cage fan wheel on an electric motor with plastic mounting flange, cooling tube and connector",
            az=28, el=26, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
