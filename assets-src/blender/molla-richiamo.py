"""Return / tension springs (molle di richiamo), generic catalogue image for the whole family:
three close-wound extension springs with full machine loops at both ends (two in bright
zinc, one in black oxide) lying on the floor in a loose group."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M


def chaikin(pts, it=2):
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append(a * 0.75 + b * 0.25)
            out.append(a * 0.25 + b * 0.75)
        out.append(pts[-1])
        pts = out
    return pts


def spring_path(rc, wr, turns, per_turn=56, nloop=44, end_gap=0.12):
    pitch = 2 * wr * 1.03
    pts = []
    # bottom loop (downward), traced backwards so the path is continuous
    e_r0 = Vector((1, 0, 0))
    z0 = 0.0
    lo = []
    for i in range(nloop + 1):
        ph = (math.pi - end_gap) * (1 - i / nloop)
        lo.append(Vector((0, 0, z0 - wr * 0.6)) + rc * (math.cos(ph) * e_r0 - math.sin(ph) * Vector((0, 0, 1))))
    pts += lo[:-1]
    n = int(turns * per_turn)
    th_e = math.tau * turns
    for i in range(n + 1):
        th = th_e * i / n
        pts.append(Vector((rc * math.cos(th), rc * math.sin(th), z0 + pitch * th / math.tau)))
    ze = z0 + pitch * turns
    e_r1 = Vector((math.cos(th_e), math.sin(th_e), 0))
    for i in range(1, nloop + 1):
        ph = (math.pi - end_gap) * i / nloop
        pts.append(Vector((0, 0, ze + wr * 0.6)) + rc * (math.cos(ph) * e_r1 + math.sin(ph) * Vector((0, 0, 1))))
    return chaikin(pts, 2), ze


def spring(mat, name, rc, wr, turns):
    pts, ze = spring_path(rc, wr, turns)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = wr
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        p.co = (v.x, v.y, v.z, 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    ob = C.finalize(ob, angle=70)
    return ob, ze


def lay(ob, ze, rc, wr, x, y, rz, roll):
    # axis Z -> X, centred, resting on the coil body
    ob.matrix_world = (Matrix.Translation((x, y, rc + wr)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
                       @ Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(roll, 4, "Z")
                       @ Matrix.Translation((0, 0, -ze / 2)))


def build():
    zinc = M.mat_zinc("Zinc", tint=(0.55, 0.565, 0.60), rough=0.22)
    bo = M.mat_black_oxide("BlackOxide", rough=0.32)
    objs = []
    specs = [  # mat, rc, wr, turns, x, y, rz, roll
        (zinc, 0.40, 0.065, 22, 0.0, 0.0, -28, math.radians(80)),
        (bo, 0.30, 0.05, 20, 0.55, -1.15, -20, math.radians(100)),
        (zinc, 0.24, 0.042, 26, -0.45, 1.05, -36, math.radians(70)),
    ]
    for i, (m, rc, wr, tu, x, y, rz, roll) in enumerate(specs):
        ob, ze = spring(m, "Spring%d" % i, rc, wr, tu)
        lay(ob, ze, rc, wr, x, y, rz, roll)
        objs.append(ob)
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("molla-richiamo", objs, "molla-richiamo.py",
            "three close-wound extension (return) springs with machine loops at both ends, zinc plated and black",
            az=-25, el=36, lens=85, fill=0.88, **M.shoot_kw())
