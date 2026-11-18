"""Front bonnet (hood) of a generic modern small hatchback, removed from the car and
propped up the way parts dealers photograph it. Metallic-grey clear-coated skin, wider at
the windscreen edge than at the nose, front edge curved in plan with a slight central beak
and headlamp notches at the corners, thin turned-down side flanges, two crisp longitudinal
creases converging towards the windscreen and two washer jets. Underneath, the black
e-coated inner reinforcement frame (deep perimeter beam with lightening holes) shows along
the front and the near side, with the latch striker and the rear hinge brackets.
Built flat (car front -Y, up +Z), then pitched rear-up about the front edge."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

NU, NV = 400, 260
Y0, LEN = -0.50, 1.00
UP = Vector((0, 0, 1))
SKIN_T = 0.007
FR_T = 0.06          # depth of the inner frame (perimeter beam)
C0 = 0.40            # fraction of the half-width grid used between the creases
PITCH = 36.0         # propping angle (rear edge up), degrees


def ty(y):
    return min(1.0, max(0.0, (y - Y0) / LEN))


def hw(y):
    """Half width: narrow at the nose, wide at the windscreen edge."""
    return 0.53 + 0.15 * ty(y) ** 0.7


def yf(xn):
    """Front edge: curved in plan, slight V beak at the centre, headlamp notches at the corners."""
    a = abs(xn)
    return (Y0 + 0.05 * math.sqrt(a * a + 0.0004) + 0.10 * a * a
            + 0.15 * P.sstep(0.70, 0.86, a) + 0.06 * (1 - math.sqrt(max(0.0, 1 - a ** 8))))


def yr(xn):
    a = abs(xn)
    return Y0 + LEN - 0.02 * a * a - 0.04 * (1 - math.sqrt(max(0.0, 1 - a ** 12)))


def xc(y):        # crease half-distance, converging towards the windscreen
    return 0.17 + 0.09 * (1 - ty(y))


def height(x, y, xn=None):
    t = ty(y)
    z = 0.12 * t - 0.04 * t * t
    X = x / 0.68
    z += -0.03 * X * X - 0.015 * X ** 4
    z -= 0.10 * P.softplus(abs(x) - xc(y), 0.0012) * P.sstep(0.0, 0.2, t)   # crisp creases
    if xn is None:
        xn = max(-1.0, min(1.0, x / hw(y)))
    dv = y - yf(xn)
    ds = hw(y) - abs(x)
    z -= max(0.030 * (1 - P.sstep(0.0, 0.07, dv)) ** 2.2,          # nose rolls down and under
             0.012 * (1 - P.sstep(0.0, 0.03, ds)) ** 2)            # thin side flange
    dr = yr(xn) - y
    z -= 0.005 * (1 - P.sstep(0.0, 0.03, dr)) ** 2
    return z


def xn_of(w, y):
    """Grid column -> normalised x, with a grid line exactly on each crease."""
    a = abs(w)
    c = xc(y) / hw(y)
    if a <= C0:
        r = a / C0 * c
    else:
        r = c + (a - C0) / (1 - C0) * (1 - c)
    return math.copysign(r, w)


def uv_pt(u, v, dz=0.0):
    w = 2 * u - 1
    y = P.lerp(Y0, Y0 + LEN, v)
    for _ in range(4):
        xn = xn_of(w, y)
        y = P.lerp(yf(xn), yr(xn), v)
    x = xn * hw(y)
    return Vector((x, y, height(x, y, xn) + dz))


def skin(paint, under):
    rows = [[uv_pt(i / NU, j / NV) for i in range(NU + 1)] for j in range(NV + 1)]
    ob = P.grid_obj("HoodSkin", rows, [paint, under], UP)
    P.solidify(ob, SKIN_T, offset=-1, inner=1, rim=0)
    C.add_bevel(ob, 0.003, segments=3, angle=40)
    return C.finalize(ob, angle=40)


U0, U1, V0, V1 = 0.012, 0.988, 0.03, 0.975
TOP_DZ = -SKIN_T - 0.004


def frame(ecoat):
    """Inner reinforcement panel: a sheet following the skin, dropped by FR_T, with
    big lightening holes in the floor and oval holes in the perimeter walls."""
    nu, nv = 220, 170
    top = []
    for j in range(nv + 1):
        v = V0 + (V1 - V0) * j / nv
        top.append([uv_pt(U0 + (U1 - U0) * i / nu, v, TOP_DZ) for i in range(nu + 1)])
    bm = bmesh.new()
    T = [[bm.verts.new(p) for p in row] for row in top]
    B = [[bm.verts.new(p - Vector((0, 0, FR_T))) for p in row] for row in top]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((T[j][i], T[j][i + 1], T[j + 1][i + 1], T[j + 1][i]))
            bm.faces.new((B[j][i], B[j + 1][i], B[j + 1][i + 1], B[j][i + 1]))
    loop = [(0, i) for i in range(nu)] + [(j, nu) for j in range(nv)] + \
           [(nv, i) for i in range(nu, 0, -1)] + [(j, 0) for j in range(nv, 0, -1)]
    for k in range(len(loop)):
        (ja, ia), (jb, ib) = loop[k], loop[(k + 1) % len(loop)]
        bm.faces.new((T[ja][ia], B[ja][ia], B[jb][ib], T[jb][ib]))
    C.fix_normals(bm)
    ob = C.mesh_obj("InnerFrame", bm, [ecoat])
    cb = bmesh.new()
    # big lightening holes through the floor of the frame
    holes = [(-0.30, -0.13, 0.12, 0.08), (0.0, -0.16, 0.13, 0.075), (0.30, -0.13, 0.12, 0.08),
             (-0.32, 0.15, 0.14, 0.10), (0.0, 0.14, 0.15, 0.10), (0.32, 0.15, 0.14, 0.10),
             (-0.46, 0.40, 0.07, 0.045), (0.46, 0.40, 0.07, 0.045)]
    for (x, y, a, b) in holes:
        C.cyl_bm(cb, 1.0, -1.0, 1.0, seg=48, matrix=Matrix.Translation((x, y, 0)) @ Matrix.Diagonal((a, b, 1, 1)))
    mid = TOP_DZ - FR_T * 0.5
    # oval holes in the side walls
    for sx, u in ((-1, U0), (1, U1)):
        for k in range(6):
            c = uv_pt(u, 0.16 + 0.135 * k, mid)
            C.cyl_bm(cb, 1.0, -1.0, 1.0, seg=32,
                     matrix=Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Diagonal((0.017, 0.032, 0.07, 1)))
    # round holes in the front wall
    for k in range(-4, 5):
        c = uv_pt(0.5 + k * 0.075, V0, mid)
        C.cyl_bm(cb, 0.014, -0.07, 0.07, seg=32, matrix=Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, "X"))
    cut = C.mesh_obj("FrameCut", cb, [ecoat])
    bo = C.add_boolean(ob, cut)
    bo.solver = "MANIFOLD"   # exact solver chokes on this dense sheet
    C.add_bevel(ob, 0.003, segments=2, angle=40)
    return C.finalize(ob, angle=40, remove=[cut])


def zbottom(x, y):
    return height(x, y) + TOP_DZ - FR_T


def hinge_arms(metal):
    out = []
    for sx in (-1, 1):
        x = sx * 0.54
        xn = x / hw(0.5)
        y0 = yr(xn) - 0.13
        zb = zbottom(x, y0)
        bm = bmesh.new()
        C.box_bm(bm, 0.06, 0.13, 0.006, center=(x, y0 + 0.035, zb - 0.003))
        for dy in (-0.01, 0.07):
            C.cyl_bm(bm, 0.012, zb - 0.014, zb - 0.006, seg=6, matrix=Matrix.Translation((x, y0 + dy, 0)))
        pl = C.mesh_obj("HingePlate", bm, [metal])
        C.add_bevel(pl, 0.0015, segments=2, angle=30)
        out.append(C.finalize(pl, angle=35))
        pts = []
        for k in range(41):
            a = k / 40 * math.radians(150)
            r = 0.09
            pts.append(Vector((x, y0 + 0.10 + r * math.sin(a), zb - 0.006 - r * (1 - math.cos(a)))))
        fr = P.path_frames(pts, (1, 0, 0))
        out.append(P.tube_obj("HingeArm", fr, P.rrect(-0.018, 0.018, -0.004, 0.004, 0.002), [metal], smooth_angle=50))
        bm = bmesh.new()
        C.cyl_bm(bm, 0.017, -0.024, 0.024, seg=32, matrix=Matrix.Translation(pts[-1]) @ Matrix.Rotation(math.radians(90), 4, "Y"))
        bu = C.mesh_obj("HingeBush", bm, [metal])
        C.add_bevel(bu, 0.002, segments=2, angle=30)
        out.append(C.finalize(bu, angle=35))
    return out


def latch(metal):
    out = []
    y = yf(0.0) + 0.09
    zb = zbottom(0.0, y)
    pts = [Vector((-0.026, y, zb + 0.004))]
    for k in range(33):
        a = math.pi * k / 32
        pts.append(Vector((-0.026 * math.cos(a), y, zb - 0.036 - 0.02 * math.sin(a))))
    pts.append(Vector((0.026, y, zb + 0.004)))
    fr = P.path_frames(P.resample(pts, 60), (0, 1, 0))
    out.append(P.tube_obj("Striker", fr, P.circle(0.006, 16), [metal], smooth_angle=60))
    bm = bmesh.new()
    C.box_bm(bm, 0.10, 0.055, 0.006, center=(0, y, zb))
    st = C.mesh_obj("StrikerPlate", bm, [metal])
    C.add_bevel(st, 0.0015, segments=2, angle=30)
    out.append(C.finalize(st, angle=35))
    return out


def washer_jets(black):
    out = []
    for sx in (-1, 1):
        x, y = sx * 0.24, 0.40
        bm = bmesh.new()
        P.superellipsoid(bm, 0.014, 0.024, 0.010, e1=0.6, e2=0.8, matrix=Matrix.Translation((x, y, height(x, y))))
        out.append(C.finalize(C.mesh_obj("WasherJet", bm, [black]), angle=60))
    return out


def build():
    paint = P.body_paint()
    ec = P.ecoat("FrameEcoat", v=0.05, rough=0.5)
    metal = C.principled("HingeEcoat", (0.05, 0.052, 0.056), metallic=0.4, rough=0.42)
    black = C.mat_black_plastic("JetABS", rough=0.4)
    objs = [skin(paint, ec), frame(ec)]
    objs += hinge_arms(metal)
    objs += latch(metal)
    objs += washer_jets(black)
    # prop it up: rear edge lifted, pivoting on the nose
    C.transform_all(objs, Matrix.Rotation(math.radians(PITCH), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("cofano", objs, "cofano.py",
            "front bonnet/hood (generic small hatchback), metallic grey paint, propped up: tapered plan with headlamp notches, "
            "two crisp creases, washer jets; black e-coat inner frame with lightening holes, hinge brackets, latch striker",
            az=-42, el=14, lens=70, fill=0.86)
