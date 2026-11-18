"""Front left door of a generic modern small hatchback, removed from the car.
Metallic-grey clear-coated outer skin with plan crown, tucked-under sill and a crisp
horizontal character line; recessed pull handle; painted window sash with black
glass-run channel and slightly tinted side glass in place; black textured mirror-mount
sail at the front top corner; black waist seal; rubber weatherstrip around the inner
edge; hinges and check strap on the front (hinge) face. Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

L = 1.06          # door length (x = 0 hinge edge)
DEPTH = 0.105     # depth of the door shell (outer skin -> inner panel)
NU, NV = 260, 230
XS = 0.195        # rear edge of the mirror sail
HX, HZ = 0.835, 0.452   # handle centre
OUT = Vector((0, -1, 0))


def zt(x):        # beltline (rises towards the rear)
    return 0.612 + 0.042 * x / L


def zc(x):        # character line
    return 0.488 + 0.03 * x / L


def zl(x):        # lower feature line, rising towards the rear
    return 0.215 + 0.06 * x / L


def xf(z):
    return 0.014 - 0.016 * math.sin(math.pi * min(max(z, 0.0), 0.64) / 0.64)


def xr(z):
    return L - 0.014 * z


def plan(x):
    return 0.032 * (1 - ((x - 0.48) / 0.78) ** 2)


def w_skin(x, z, pocket=True):
    """Outward bulge (towards -Y) of the outer skin."""
    zm = 0.30
    if z < zm:
        sec = -0.045 * ((zm - z) / zm) ** 2.3
    else:
        sec = -0.022 * ((z - zm) / 0.33) ** 1.5
    sec -= 0.30 * P.softplus(z - zc(x), 0.0025)          # shoulder / character line
    sec -= 0.16 * P.softplus(zl(x) - z, 0.004)           # lower sculpted line
    w = plan(x) + sec
    if pocket:
        r2 = ((x - HX) / 0.098) ** 2 + ((z - HZ) / 0.04) ** 2
        w -= 0.022 * P.bump(r2) ** 0.7 if r2 < 1 else 0.0
    return w


def skin_pt(x, z):
    return Vector((x, -w_skin(x, z), z))


def w_glass(x, z):
    d = z - 0.612
    return 0.6 * plan(x) - 0.066 - 0.20 * d - 0.10 * d * d


def glass_pt(p, off=0.0):
    x, z = p.x, p.y
    return Vector((x, -w_glass(x, z) - off, z))


# ------------------------------------------------------------------ outer skin / shell
def lower_uv(u, v):
    rc = 0.06
    c = rc / L
    zb = 0.014 * u
    if u < c:
        zb += rc * (1 - math.sqrt(max(0.0, 1 - ((c - u) / c) ** 2)))
    if u > 1 - c:
        zb += rc * (1 - math.sqrt(max(0.0, 1 - ((u - (1 - c)) / c) ** 2)))
    ztp = zt(u * L)
    rt, ct = 0.014, 0.014 / L
    if u < ct:
        ztp -= rt * (1 - math.sqrt(max(0.0, 1 - ((ct - u) / ct) ** 2)))
    if u > 1 - ct:
        ztp -= rt * (1 - math.sqrt(max(0.0, 1 - ((u - (1 - ct)) / ct) ** 2)))
    z = zb + (ztp - zb) * v
    x = xf(z) + (xr(z) - xf(z)) * u
    return x, z


def shell(paint, ecoat):
    rows = []
    for j in range(NV + 1):
        v = j / NV
        rows.append([skin_pt(*lower_uv(i / NU, v)) for i in range(NU + 1)])
    ob = P.grid_obj("DoorSkin", rows, [paint, ecoat], OUT)
    P.solidify(ob, DEPTH, offset=-1, inner=1, rim=0)
    C.add_bevel(ob, 0.006, segments=4, angle=40)
    return C.finalize(ob, angle=40)


def outline_lower():
    """Closed 2D outline of the lower shell (x, z), counter-clockwise."""
    pts = []
    pts += [Vector(lower_uv(i / NU, 0.0)) for i in range(NU + 1)]
    pts += [Vector(lower_uv(1.0, j / NV)) for j in range(1, NV + 1)]
    pts += [Vector(lower_uv(i / NU, 1.0)) for i in range(NU - 1, -1, -1)]
    pts += [Vector(lower_uv(0.0, j / NV)) for j in range(NV - 1, 0, -1)]
    return pts


def weatherstrip(rubber):
    poly = P.resample(outline_lower(), 500, closed=True)
    inset = P.offset2d(poly, 0.016, closed=True)   # CCW -> left normal points inwards
    # open path: from front top, down, along the bottom, up the rear (no seal on the beltline)
    pts = []
    for p in inset:
        if p.y < zt(p.x) - 0.03:
            pts.append(p)
    # order: start near front top going down -> find start index
    k0 = max(range(len(pts)), key=lambda i: (pts[i].y if pts[i].x < 0.3 else -9))
    pts = pts[k0:] + pts[:k0]
    pts = [p for p in pts]
    fr = []
    for p in pts:
        S = skin_pt(p.x, p.y)
        n = P.surf_normal(lambda q: skin_pt(q.x, q.y), p, sign_ref=OUT)
        fr.append(S - n * (DEPTH + 0.004))
    frames = P.path_frames(fr, (0, 1, 0))
    sec = [(0.009 * math.cos(a) * 0.9, 0.009 * math.sin(a) + 0.006) for a in [math.tau * k / 14 for k in range(14)]]
    return P.tube_obj("Weatherstrip", frames, sec, [rubber], smooth_angle=70)


# ------------------------------------------------------------------ window
def dlo():
    pts = P.rounded([(0.068, zt(0.068)), (0.47, 1.048), (0.938, 1.032), (0.993, zt(0.993))],
                    [0, 0.16, 0.06, 0], closed=False, seg=24)
    return P.resample(pts, 260)


def a_pillar_z(x, D):
    for i in range(len(D) - 1):
        if D[i].x <= x <= D[i + 1].x:
            t = (x - D[i].x) / (D[i + 1].x - D[i].x)
            return D[i].y + (D[i + 1].y - D[i].y) * t
    return D[0].y


def glass(mat, D):
    off = P.offset2d(D, 0.012)          # under the channel lip
    poly = [p for p in off if p.x >= XS]
    za = a_pillar_z(XS, off)
    end = off[-1]
    poly = [Vector((XS, za))] + poly + [Vector((end.x, zt(end.x) - 0.05)), Vector((XS, zt(XS) - 0.05))]
    poly = P.rounded(poly, [0] * len(poly), closed=True)
    poly = P.resample(poly, 360, closed=True)
    ob = P.fan_obj("Glass", poly, Vector((0.6, 0.84)), 40, glass_pt, [mat], OUT, power=1.3)
    P.solidify(ob, 0.0045, offset=-1)
    return C.finalize(ob, angle=60)


def sail(mat, D):
    za = a_pillar_z(XS, D)
    poly = [p for p in P.offset2d(D, 0.004) if p.x <= XS]
    poly = poly + [Vector((XS, za)), Vector((XS, zt(XS) - 0.02)), Vector((0.066, zt(0.066) - 0.02))]
    poly = P.rounded(poly, [0] * len(poly), closed=True)
    poly = P.resample(poly, 160, closed=True)
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.fan_obj("Sail", poly, c, 16, lambda p: glass_pt(p, 0.007), [mat], OUT)
    P.solidify(ob, 0.012, offset=-1)
    C.add_bevel(ob, 0.003, segments=2, angle=35)
    return C.finalize(ob, angle=40)


def sash(paint, rubber, gloss, D):
    fr = P.frames_on_surface(D, glass_pt, OUT, side_sign=1.0)
    frame_sec = P.rrect(-0.002, 0.044, -0.034, 0.010, 0.005)
    lip_sec = [(-0.015, -0.0005), (0.003, -0.0005), (0.003, 0.0135), (-0.004, 0.0135), (-0.013, 0.006), (-0.0155, 0.002)]
    a = P.tube_obj("Sash", fr, frame_sec, [paint], smooth_angle=50)
    b = P.tube_obj("GlassRun", fr, lip_sec, [rubber], smooth_angle=50)
    # vertical divider seal between sail and glass
    za = a_pillar_z(XS, D)
    pts = [Vector((XS, zt(XS) - 0.01 + (za - zt(XS) + 0.01) * k / 30)) for k in range(31)]
    fr2 = P.frames_on_surface(pts, glass_pt, OUT)
    c = P.tube_obj("SailSeal", fr2, P.rrect(-0.006, 0.006, -0.001, 0.010, 0.003), [rubber], smooth_angle=50)
    # gloss-black applique on the B-pillar part of the frame
    k0 = next(i for i in range(len(D) - 1, 0, -1) if D[i].y > 1.0)
    frB = fr[k0 + 4:]
    d = P.tube_obj("BApplique", frB, P.rrect(-0.001, 0.047, 0.006, 0.0125, 0.003), [gloss], smooth_angle=50)
    # frame seal behind the sash
    fr3 = [(Pp + A * 0.024 + B * -0.046, A, B) for (Pp, A, B) in fr]
    e = P.tube_obj("FrameSeal", fr3, [(0.011 * math.cos(t), 0.009 * math.sin(t)) for t in [math.tau * k / 14 for k in range(14)]],
                   [rubber], smooth_angle=70)
    return [a, b, c, d, e]


def waist_seal(rubber):
    frames, secs = [], []
    n = 140
    bm = bmesh.new()
    rings = []
    for k in range(n + 1):
        x = 0.028 + (0.998 - 0.028) * k / n
        z = zt(x)
        yg = -w_glass(x, z)
        ys = -w_skin(x, z, False)
        gap = yg - ys            # >0: glass is inboard of the skin
        sec = [(0.0035, -0.012), (-gap - 0.002, -0.012), (-gap - 0.005, 0.004), (-gap + 0.002, 0.012),
               (-0.006, 0.017), (0.0035, 0.015)]
        rings.append([bm.verts.new((x, yg + a, z + b)) for (a, b) in sec])
    m = len(rings[0])
    for i in range(n):
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    C.fix_normals(bm)
    ob = C.mesh_obj("WaistSeal", bm, [rubber])
    C.add_bevel(ob, 0.002, segments=2, angle=35)
    return C.finalize(ob, angle=40)


# ------------------------------------------------------------------ hardware
def handle(paint, black):
    x, z = HX, HZ
    y0 = -w_skin(x, z, pocket=False)
    sl = (w_skin(x + 0.01, z, False) - w_skin(x - 0.01, z, False)) / 0.02
    ang = math.atan(-sl)
    M = Matrix.Translation((x, y0 - 0.002, z)) @ Matrix.Rotation(ang, 4, "Z")
    bm = bmesh.new()
    P.superellipsoid(bm, 0.086, 0.017, 0.0175, e1=0.45, e2=0.35, matrix=M)
    ob = C.mesh_obj("Handle", bm, [paint])
    out = [C.finalize(ob, angle=60)]
    # lock-barrel cover at the front end
    bm = bmesh.new()
    M2 = Matrix.Translation((x - 0.058, y0 - 0.0185, z)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")
    C.cyl_bm(bm, 0.0105, -0.0015, 0.0015, seg=48, matrix=M2)
    cap = C.mesh_obj("LockCap", bm, [black])
    C.add_bevel(cap, 0.0012, segments=2, angle=30)
    out.append(C.finalize(cap, angle=35))
    return out


def hinges(metal, black):
    out = []
    for z in (0.17, 0.505):
        x0 = xf(z)
        y0 = -w_skin(x0, z) + 0.052
        bm = bmesh.new()
        C.box_bm(bm, 0.012, 0.062, 0.10, center=(x0 - 0.005, y0, z))            # leaf on the door
        C.box_bm(bm, 0.050, 0.030, 0.034, center=(x0 - 0.034, y0 + 0.006, z))    # arm
        C.cyl_bm(bm, 0.014, z - 0.042, z + 0.042, seg=32, matrix=Matrix.Translation((x0 - 0.062, y0 + 0.006, 0)))
        for dz in (-0.03, 0.03):   # bolt heads
            C.cyl_bm(bm, 0.009, 0, 0.007, seg=6, matrix=Matrix.Translation((x0 - 0.011, y0 - 0.016, z + dz)) @ Matrix.Rotation(math.radians(-90), 4, "Y"))
        ob = C.mesh_obj("Hinge", bm, [metal])
        C.add_bevel(ob, 0.0025, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
        bm = bmesh.new()
        C.cyl_bm(bm, 0.0055, z - 0.056, z + 0.056, seg=24, matrix=Matrix.Translation((x0 - 0.062, y0 + 0.006, 0)))
        pin = C.mesh_obj("Pin", bm, [metal])
        C.add_bevel(pin, 0.0015, segments=2, angle=30)
        out.append(C.finalize(pin, angle=35))
    # door check strap
    z = 0.34
    x0 = xf(z)
    y0 = -w_skin(x0, z) + 0.052
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 0.010, 0.026, center=(x0 - 0.050, y0, z))
    C.box_bm(bm, 0.014, 0.022, 0.034, center=(x0 - 0.103, y0, z))
    C.box_bm(bm, 0.012, 0.05, 0.07, center=(x0 - 0.004, y0, z))
    ob = C.mesh_obj("CheckStrap", bm, [black])
    C.add_bevel(ob, 0.003, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    return out


def build():
    paint = P.body_paint()
    ecoat = P.ecoat()
    rubber = C.mat_rubber()
    sail_m = P.textured_black("SailPP")
    gloss_black = C.principled("GlossBlack", (0.012, 0.012, 0.013), rough=0.12)
    tint = C.mat_clear("TintedGlass", ior=1.52)
    C._set(P.bsdf(tint), "Base Color", (0.60, 0.68, 0.66, 1))
    metal = C.principled("HingeEcoat", (0.06, 0.062, 0.066), metallic=0.4, rough=0.42)
    D = dlo()
    objs = [shell(paint, ecoat), weatherstrip(rubber), glass(tint, D), sail(sail_m, D), waist_seal(rubber)]
    objs += sash(paint, rubber, gloss_black, D)
    objs += handle(paint, gloss_black)
    objs += hinges(metal, ecoat)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("porta", objs, "porta.py",
            "front left car door (generic small hatchback), metallic grey paint: curved skin with character line, "
            "pull handle, painted sash with black glass-run channel, tinted side glass, black mirror sail, seals, hinges",
            az=-36, el=12, lens=70, fill=0.86)
