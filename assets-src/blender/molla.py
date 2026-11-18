"""Front suspension coil spring (molla) as removed from a small car: cylindrical helix in
satin black powder coat, closed end coils ground flat (bare steel seats where the
grinding cut through the paint), small factory colour-code paint dashes on one coil."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

SR = 0.68       # mean coil radius (1 unit ~ 10 cm)
WR = 0.068      # wire radius
H = 3.25        # free length
TURNS = 7.4
N = 1400


def z_of_theta():
    """closed (touching) end coils, open pitch in the middle; returns thetas, z"""
    th_tot = TURNS * math.tau
    th_end = 1.05 * math.tau
    closed = 2.1 * WR / math.tau          # per radian
    ths = [th_tot * i / N for i in range(N + 1)]

    def pitch(th):
        a = C.smoothstep(0.35 * th_end, th_end * 1.15, th) * C.smoothstep(0.35 * th_end, th_end * 1.15, th_tot - th)
        return closed * (1 - a) + a

    zs = [0.0]
    for i in range(1, N + 1):
        zs.append(zs[-1] + pitch((ths[i] + ths[i - 1]) / 2) * (ths[i] - ths[i - 1]))
    # scale the open part so the centre-line runs from -0.25*WR to H+0.25*WR
    z0, z1 = -0.25 * WR, H + 0.25 * WR
    k = (z1 - z0) / zs[-1]
    return ths, [z0 + z * k for z in zs]


def helix_curve(name, ths, zs, r, mat, i0=0, i1=None):
    i1 = len(ths) if i1 is None else i1
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(i1 - i0 - 1)
    for p, th, z in zip(sp.points, ths[i0:i1], zs[i0:i1]):
        p.co = (SR * math.cos(th), SR * math.sin(th), z, 1)
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return ob


def spring(paint, ground):
    ths, zs = z_of_theta()
    ob = C.finalize(helix_curve("Spring", ths, zs, WR, paint), angle=70)
    # grind both ends flat: big boxes below z=0 and above z=H
    bm = bmesh.new()
    C.box_bm(bm, 4, 4, 1.0, center=(0, 0, -0.5))
    C.box_bm(bm, 4, 4, 1.0, center=(0, 0, H + 0.5))
    cut = C.mesh_obj("Grind", bm, [ground])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.004, segments=2, angle=40)
    out = [C.finalize(ob, angle=40, remove=[cut])]
    # colour-code paint dashes on the outer face of a middle coil
    for (frac, col, ln) in ((0.398, "white", 7), (0.403, "yellow", 11)):
        out.append(dash_patch(ths, zs, int(frac * N), ln, dash[col], 0.55 if col == "white" else -0.1))
    return out


def dash_patch(ths, zs, i0, ln, mat, phi0):
    """thin painted stripe hugging the outer side of the wire"""
    bm = bmesh.new()
    rows = []
    for i in range(i0, i0 + ln):
        th = ths[i]
        rad = Vector((math.cos(th), math.sin(th), 0))
        c = rad * SR + Vector((0, 0, zs[i]))
        row = []
        for j in range(7):
            ph = phi0 + (j / 6 - 0.5) * 0.55
            row.append(bm.verts.new(c + (WR + 0.0015) * (math.cos(ph) * rad + math.sin(ph) * Vector((0, 0, 1)))))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for j in range(6):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    C.fix_normals(bm)
    ob = C.mesh_obj("Dash", bm, [mat])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.001
    return C.finalize(ob, angle=60)


dash = {}


def build():
    paint = C.mat_paint("PowderCoat", (0.03, 0.03, 0.032, 1), rough=0.38, coat=0.25)
    C.add_noise_bump(paint, scale=260, strength=0.06, distance=0.0012, rough_var=0.06)
    ground = C.principled("GroundSteel", (0.50, 0.49, 0.47), metallic=1.0, rough=0.32)
    C.add_noise_bump(ground, scale=900, strength=0.12, distance=0.0008, rough_var=0.1)
    dash["white"] = C.mat_paint("DashWhite", (0.75, 0.75, 0.72, 1), rough=0.55, coat=0.0)
    dash["yellow"] = C.mat_paint("DashYellow", (0.80, 0.55, 0.04, 1), rough=0.55, coat=0.0)
    for m in dash.values():
        C.add_noise_bump(m, scale=300, strength=0.15, distance=0.001)
    objs = spring(paint, ground)
    C.transform_all(objs, Matrix.Rotation(math.radians(-60), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("molla", objs, "molla.py",
            "front suspension coil spring: black powder-coated steel helix with closed ends ground flat",
            az=30, el=16, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
