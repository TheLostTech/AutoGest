"""Door-mirror glass (replacement lens), generic small hatchback, left side: convex
silvered glass with a ground green edge, glued on its black plastic backing plate with
a thin retaining lip; on the back the snap-on mount ring with four clip hooks, radial
ribs and the two spade contacts of the heater film on a moulded boss. Stood up and
tilted back slightly so the glass reflects the studio. Glass faces -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
S = 0.205                     # overall width of the glass (m)
HEAD_PTS = [(-0.56, 0.17), (-0.47, 0.29), (0.28, 0.31), (0.44, 0.24), (0.47, -0.10),
            (0.36, -0.23), (-0.28, -0.22), (-0.53, -0.07)]
RC = 1.4                      # radius of curvature of the convex glass
GT = 0.0022                   # glass thickness
PLATE_Y0, PLATE_Y1 = 0.0030, 0.0062


def outline(grow=0.0, n=220):
    pts = [Vector((x * S / 1.03, z * S / 1.03)) for x, z in HEAD_PTS]
    sm = P.bspline(pts, n=n, closed=True)
    if P.signed_area(sm) < 0:
        sm = sm[::-1]
    if grow:
        sm = P.offset2d(sm, -grow, closed=True)   # CCW: left normal points inwards
    return sm


CEN = sum(outline(), Vector((0, 0))) / 220
RMAX = max((p - CEN).length for p in outline())


def glass_y(p):
    r2 = (p - CEN).length_squared
    return -(RMAX ** 2 - r2) / (2 * RC)


def glass(mirror, edge):
    poly = outline()
    lift = lambda p: Vector((p.x, glass_y(p), p.y))
    ob = P.fan_obj("Glass", poly, CEN, 28, lift, [mirror, edge], OUT, power=1.2)
    P.solidify(ob, GT, offset=-1, inner=0, rim=1)
    C.add_bevel(ob, 0.0006, segments=2, angle=30)
    return C.finalize(ob, angle=45)


def plate(black):
    out = []
    poly = outline(0.0016)
    lift = lambda p: Vector((p.x, PLATE_Y0, p.y))
    ob = P.fan_obj("Plate", poly, CEN, 10, lift, [black], OUT)
    P.solidify(ob, PLATE_Y1 - PLATE_Y0, offset=1)
    C.add_bevel(ob, 0.0008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    # thin retaining lip hugging the glass edge
    path = outline(0.0012)
    fr = P.frames_on_surface(path, lambda p: Vector((p.x, PLATE_Y0, p.y)), OUT, closed=True)
    sec = P.rrect(-0.0012, 0.0010, 0.0, 0.0034, 0.0005, seg=3)
    out.append(P.tube_obj("Lip", fr, sec, [black], closed=True, smooth_angle=50))
    return out


RY = Matrix.Rotation(math.radians(-90), 4, "X")   # lathe Z -> +Y


def inside(poly, q):
    c = False
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        if (a.y > q.y) != (b.y > q.y):
            x = a.x + (q.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if q.x < x:
                c = not c
    return c


def soft_studio_reflections():
    """A perfect mirror shows every area light as a hard white slab: keep only the key
    and top lights in glossy rays, the rest of the reflection is the studio gradient."""
    orig = C._area

    def _area(name, *a, **k):
        ob = orig(name, *a, **k)
        if name in ("Fill", "Front", "Rim"):
            ob.visible_glossy = False
        return ob
    C._area = _area


def back(black, dark, brass):
    out = []
    c = Vector((CEN.x + 0.004, PLATE_Y1, CEN.y + 0.002))
    # mount ring
    ring = C.lathe("MountRing", [(0.031, -0.0005, 0), (0.037, -0.0005, 0), (0.037, 0.010, 0), (0.0355, 0.0125, 0),
                                 (0.0325, 0.0125, 0), (0.031, 0.011, 0)], [black], steps=96)
    ring.matrix_world = Matrix.Translation(c) @ RY
    C.add_bevel(ring, 0.0005, segments=1, angle=30)
    out.append(C.finalize(ring, angle=40))
    # inner disc (recessed floor) and centre boss
    hub = C.lathe("Hub", [(0.0, 0.0, 0), (0.031, 0.0, 0), (0.031, 0.0015, 0), (0.012, 0.0015, 0), (0.010, 0.006, 0),
                          (0.0065, 0.0065, 0), (0.0065, 0.003, 0), (0.0, 0.003, 0)], [black], steps=64)
    hub.matrix_world = Matrix.Translation(c) @ RY
    out.append(C.finalize(hub, angle=40))
    # four clip hooks standing out of the ring
    for k in range(4):
        a = math.radians(45 + 90 * k)
        Rz = Matrix.Rotation(a, 4, "Y")
        bm = bmesh.new()
        C.box_bm(bm, 0.012, 0.016, 0.0022, center=(0.0, 0.008, 0.0382))
        C.box_bm(bm, 0.012, 0.0028, 0.0035, center=(0.0, 0.0155, 0.0405))
        ob = C.mesh_obj("Hook", bm, [black])
        C.add_bevel(ob, 0.0005, segments=1, angle=30)
        ob.matrix_world = Matrix.Translation(c) @ Rz
        out.append(C.finalize(ob, angle=35))
    # radial ribs from the ring towards the plate edge
    bm = bmesh.new()
    inset = outline(-0.010)
    c2 = Vector((c.x, c.z))
    for k in range(8):
        a = math.radians(22.5 * (2 * k + 1))
        d = Vector((math.cos(a), math.sin(a)))
        r0 = 0.037
        r1 = r0
        while inside(inset, c2 + d * (r1 + 0.001)):
            r1 += 0.001
        L = r1 - r0
        if L < 0.004:
            continue
        mid = c2 + d * (r0 + L / 2)
        M = Matrix.Translation((mid.x, PLATE_Y1 + 0.002, mid.y)) @ Matrix.Rotation(-a, 4, "Y")
        C.box_bm(bm, L, 0.004, 0.0016, matrix=M)
    rib = C.mesh_obj("Ribs", bm, [black])
    C.add_bevel(rib, 0.0004, segments=1, angle=30)
    out.append(C.finalize(rib, angle=35))
    # heater contacts: boss with two spade tabs near the outboard (narrow) end
    bx, bz = min(p.x for p in outline()) + 0.016, CEN.y - 0.004
    bm = bmesh.new()
    C.box_bm(bm, 0.016, 0.006, 0.024, center=(bx, PLATE_Y1 + 0.003, bz))
    boss = C.mesh_obj("Boss", bm, [black])
    C.add_bevel(boss, 0.0012, segments=2, angle=30)
    out.append(C.finalize(boss, angle=35))
    for dz in (-0.0065, 0.0065):
        bm = bmesh.new()
        C.box_bm(bm, 0.0008, 0.011, 0.0063, center=(bx, PLATE_Y1 + 0.0105, bz + dz))
        t = C.mesh_obj("Spade", bm, [brass])
        C.add_bevel(t, 0.0002, segments=1, angle=30)
        out.append(C.finalize(t, angle=35))
    return out


def build():
    mirror = C.principled("MirrorGlass", (0.86, 0.88, 0.90), metallic=1.0, rough=0.02)
    edge = C.principled("GlassEdge", C.srgb("#7FA58F"), rough=0.35, Transmission_Weight=0.4, IOR=1.52)
    C.add_noise_bump(edge, scale=1800, strength=0.3, distance=0.0002)
    black = C.mat_black_plastic("PlateABS", rough=0.5, color=0.022)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.7)
    brass = C.principled("TinnedBrass", (0.82, 0.76, 0.58), metallic=1.0, rough=0.25)
    objs = [glass(mirror, edge)]
    objs += plate(black)
    objs += back(black, dark, brass)
    # stand it up, tilted back a little, rotated to a 3/4 view
    M = Matrix.Rotation(math.radians(0), 4, "Z") @ Matrix.Rotation(math.radians(-24), 4, "X")
    C.transform_all(objs, M)
    return objs


if __name__ == "__main__":
    soft_studio_reflections()
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("vetro-specchietto", objs, "vetro-specchietto.py",
            "door mirror glass (generic small hatchback): convex silvered glass on black backing plate with "
            "mount ring, clip hooks and heater spade contacts",
            az=-46, el=15, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
