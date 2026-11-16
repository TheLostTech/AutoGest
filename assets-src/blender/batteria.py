"""Car battery: black polypropylene case with lid, lead terminals (red cap on +),
carry handle, vent strip, +/- markings and a small blank label."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

L, W, H = 1.60, 1.00, 0.90   # case
LH = 0.10                    # lid height
TX, TY = 0.60, -0.28         # terminal pockets (x = +/-TX)


def case(black):
    bm = bmesh.new()
    C.box_bm(bm, L, W, H, center=(0, 0, H / 2))
    C.box_bm(bm, L - 0.04, W + 0.07, 0.06, center=(0, 0, 0.03))   # hold-down ledge
    # vertical ribs on the short ends
    for sx in (-1, 1):
        for y in (-0.25, 0.0, 0.25):
            C.box_bm(bm, 0.03, 0.05, H - 0.12, center=(sx * (L / 2 + 0.01), y, (H - 0.12) / 2 + 0.06))
    ob = C.mesh_obj("Case", bm, [black])
    C.add_bevel(ob, 0.018, segments=3, angle=30)
    return C.finalize(ob, angle=35)


def lid(black):
    bm = bmesh.new()
    C.box_bm(bm, L + 0.025, W + 0.025, LH, center=(0, 0, H + LH / 2))
    ob = C.mesh_obj("Lid", bm, [black])
    cb = bmesh.new()
    for sx in (-1, 1):
        C.box_bm(cb, 0.30, 0.34, 0.2, center=(sx * TX, TY - 0.03, H + LH + 0.1 - 0.05))
    # long vent strip recess
    C.box_bm(cb, 0.95, 0.10, 0.2, center=(0, 0.20, H + LH + 0.1 - 0.012))
    cut = C.mesh_obj("LidCut", cb, [black])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.012, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[cut])


def terminal(lead, x):
    z0 = H + LH - 0.05
    P = [(0.0, z0, 0), (0.11, z0, 0), (0.11, z0 + 0.025, 0), (0.075, z0 + 0.035, 0), (0.068, z0 + 0.17, 0),
         (0.06, z0 + 0.18, 0), (0.0, z0 + 0.18, 0)]
    ob = C.lathe("Terminal", P, [lead], steps=64)
    ob.matrix_world = Matrix.Translation((x, TY - 0.03, 0))
    return C.finalize(ob, angle=40)


def red_cap(red, x):
    z0 = H + LH - 0.05
    P = [(0.0, z0 + 0.235, 0), (0.06, z0 + 0.228, 0), (0.10, z0 + 0.20, 0), (0.125, z0 + 0.12, 0),
         (0.135, z0 + 0.02, 0), (0.135, z0, 0), (0.0, z0, 0)]
    ob = C.lathe("RedCap", P, [red], steps=64)
    ob.matrix_world = Matrix.Translation((x, TY - 0.03, 0))
    out = [C.finalize(ob, angle=40)]
    # hinge tab toward the case centre
    bm = bmesh.new()
    C.box_bm(bm, 0.12, 0.16, 0.03, center=(x - 0.13, TY - 0.03, z0 + 0.03))
    t = C.mesh_obj("CapTab", bm, [red])
    C.add_bevel(t, 0.01, segments=2, angle=30)
    out.append(C.finalize(t, angle=35))
    return out


def vents(black):
    bm = bmesh.new()
    for i in range(6):
        x = -0.40 + 0.16 * i
        C.cyl_bm(bm, 0.045, H + LH - 0.02, H + LH + 0.004, seg=32, matrix=Matrix.Translation((x, 0.20, 0)))
    ob = C.mesh_obj("Vents", bm, [black])
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def handle(black):
    cu = bpy.data.curves.new("Handle", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.022
    cu.bevel_resolution = 4
    sp = cu.splines.new("POLY")
    pts = []
    z = H + LH + 0.022
    y0, y1 = 0.36, 0.44
    for i in range(9):
        a = math.pi / 2 * i / 8
        pts.append((-0.62 + 0.06 * (1 - math.cos(a)), y0 + (y1 - y0) * math.sin(a), z))
    for i in range(9):
        a = math.pi / 2 * i / 8
        pts.append((0.56 + 0.06 * math.sin(a), y1 - (y1 - y0) * (1 - math.cos(a)), z))
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = c + (1,)
    ob = C.link(bpy.data.objects.new("Handle", cu))
    cu.materials.append(black)
    out = [C.finalize(ob, angle=45)]
    for x in (-0.62, 0.62):
        bm = bmesh.new()
        C.cyl_bm(bm, 0.04, H + LH - 0.01, H + LH + 0.05, seg=24, matrix=Matrix.Translation((x, y0, 0)))
        piv = C.mesh_obj("Pivot", bm, [black])
        C.add_bevel(piv, 0.008, segments=2, angle=30)
        out.append(C.finalize(piv, angle=35))
    return out


def marks(black):
    bm = bmesh.new()
    z = H + LH + 0.006
    # plus near + terminal, minus near - terminal (raised moulding)
    C.box_bm(bm, 0.10, 0.025, 0.012, center=(TX, 0.0, z))
    C.box_bm(bm, 0.025, 0.10, 0.012, center=(TX, 0.0, z))
    C.box_bm(bm, 0.10, 0.025, 0.012, center=(-TX, 0.0, z))
    ob = C.mesh_obj("Marks", bm, [black])
    C.add_bevel(ob, 0.004, segments=1, angle=30)
    return C.finalize(ob, angle=35)


def build():
    case_m = C.mat_black_plastic("CasePP", rough=0.32, color=0.018)
    lid_m = C.mat_black_plastic("LidPP", rough=0.40, color=0.022)
    lead = C.principled("Lead", (0.42, 0.42, 0.44), metallic=0.85, rough=0.48)
    C.add_noise_bump(lead, scale=300, strength=0.15, distance=0.001, rough_var=0.08)
    red = C.mat_paint("RedCapPP", C.srgb("#C8161E"), rough=0.32, coat=0.3)
    objs = [case(case_m), lid(lid_m), vents(lid_m), marks(lid_m)]
    objs += [terminal(lead, -TX)]
    objs += [terminal(lead, TX)] + red_cap(red, TX)
    objs += handle(lid_m)
    im = C.label_image("BattLabel", 1024, 560, seed=11)
    lab = C.label_plane("Label", C.mat_label(im), 0.78, 0.42, Matrix.Translation((-0.22, -W / 2 - 0.0015, 0.50)))
    objs.append(lab)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("batteria", objs, "batteria.py",
            "12V car battery: black case and lid, lead terminals with red + cap, carry handle, blank label",
            az=32, el=26, lens=70, fill=0.82)
