"""Plastic trim clips and push rivets (clip / bottoni a pressione), generic catalogue image
for the whole family: a small group of typical body/trim fasteners - a black fir-tree clip
with sealing umbrella standing on its head, a black fir-tree clip lying on its side and a
white two-piece push rivet with split expanding legs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M


def fir_tree(mat, name, rh=0.85, umbrella=True, nfins=7, fin_r=0.44, stem_r=0.15, sp=0.17):
    prof = [(0.0, -0.15, 0)]
    for i in range(1, 9):
        r = rh * 0.92 * i / 8
        prof.append((r, -0.15 + 0.09 * (r / rh) ** 2, 0))
    prof += [(rh, -0.035, 0), (rh, -0.005, 0), (rh - 0.03, 0.01, 0)]
    if umbrella:
        ru = rh * 0.86
        prof += [(0.30, 0.012, 0), (0.30, 0.03, 0), (ru, 0.24, 0), (ru - 0.02, 0.265, 0),
                 (0.26, 0.085, 0)]
    else:
        prof += [(stem_r + 0.06, 0.012, 0)]
    z = 0.20 if umbrella else 0.12
    prof += [(stem_r, z, 0)]
    for k in range(nfins):
        zk = z + 0.04 + k * sp
        fr = fin_r * (1.0 - 0.28 * (k / max(1, nfins - 1)) ** 1.5)
        prof += [(stem_r, zk, 0), (fr, zk - 0.075, 0), (fr + 0.006, zk - 0.05, 0),
                 (stem_r + 0.02, zk + 0.115, 0)]
    ze = z + 0.04 + nfins * sp
    prof += [(stem_r * 0.9, ze, 0), (stem_r * 0.5, ze + 0.06, 0), (0.0, ze + 0.07, 0)]
    ob = C.lathe(name, prof, [mat], steps=96)
    C.add_bevel(ob, 0.006, segments=2, angle=40)
    return C.finalize(ob, angle=40), ze + 0.07


def push_rivet(mat, name="Rivet"):
    rh = 0.78
    prof = [(0.0, -0.11, 0), (0.33, -0.11, 0), (0.34, -0.09, 0), (0.36, -0.08, 0), (rh - 0.04, -0.08, 0),
            (rh, -0.05, 0), (rh, -0.01, 0), (rh - 0.03, 0.0, 0), (0.30, 0.0, 0), (0.29, 0.25, 0),
            (0.33, 0.70, 0), (0.355, 0.86, 0), (0.33, 0.95, 0), (0.24, 1.0, 0), (0.0, 1.0, 0)]
    body = C.lathe(name, prof, [mat], steps=96)
    cuts = []
    for ang in (0.0, 90.0):
        bm = bmesh.new()
        C.box_bm(bm, 1.2, 0.075, 0.82, center=(0, 0, 0.62),
                 matrix=Matrix.Rotation(math.radians(ang), 4, "Z"))
        c = C.mesh_obj("SplitCut", bm, [mat])
        m = C.add_boolean(body, c)
        try:
            m.use_self = True
            m.use_hole_tolerant = True
        except Exception:
            pass
        cuts.append(c)
    # recess in the pin head
    bm = bmesh.new()
    C.cyl_bm(bm, 0.12, -0.14, -0.09, seg=48)
    c = C.mesh_obj("PinRecess", bm, [mat])
    C.add_boolean(body, c)
    cuts.append(c)
    C.add_bevel(body, 0.006, segments=2, angle=40)
    out = [C.finalize(body, angle=40, remove=cuts)]
    # the expander pin visible between the legs
    pin = C.lathe(name + "Pin", [(0.0, 0.0, 0), (0.11, 0.0, 0), (0.11, 0.93, 0), (0.08, 0.97, 0), (0.0, 0.97, 0)],
                  [mat], steps=48)
    out.append(C.finalize(pin, angle=40))
    # the seam line between pin head and rivet head
    return out


def build():
    black = C.mat_black_plastic("ClipBlack", rough=0.42, color=0.03)
    white = M.mat_plastic("ClipWhite", (0.72, 0.71, 0.67), rough=0.48, sss=0.15)
    objs = []
    # A: black fir tree with umbrella, standing on its head, stem up
    a, la = fir_tree(black, "FirA")
    M.drop_to_ground([a])
    M.place([a], Matrix.Translation((-0.85, 0.75, 0)))
    objs.append(a)
    # B: white push rivet lying on its side
    b = push_rivet(white)
    M.lie_on_x(b, 0.78, 0.355, 1.1, roll=0.4)
    M.drop_to_ground(b)
    M.place(b, Matrix.Translation((-0.35, -0.85, 0)) @ Matrix.Rotation(math.radians(-15), 4, "Z"))
    objs += b
    # C: black fir tree without umbrella lying on its side
    c, lc = fir_tree(black, "FirC", rh=0.62, umbrella=False, nfins=6, fin_r=0.36, stem_r=0.12, sp=0.15)
    M.lie_on_x([c], 0.62, 0.36, lc, roll=0.2)
    M.drop_to_ground([c])
    M.place([c], Matrix.Translation((0.95, 0.35, 0)) @ Matrix.Rotation(math.radians(-62), 4, "Z"))
    objs.append(c)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("clip", objs, "clip.py",
            "group of plastic trim clips: black fir-tree clips and a white push rivet",
            az=-28, el=34, lens=85, fill=0.86, **M.shoot_kw())
