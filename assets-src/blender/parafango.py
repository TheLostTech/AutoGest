"""Front left wing (fender) of a generic modern small hatchback, removed from the car.
Metallic-grey clear-coated skin (same paint as the other body panels) with crowned
section, shoulder rolling over into the bonnet gutter, a feature line that continues the
door's, front end wrapping round towards the bumper and a notch under the headlamp;
wheel-arch cut-out with a slightly flared surround and a rolled return lip; side indicator
hole; bolting flanges with holes along the top edge and down the rear (A-pillar) edge.
Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

L = 0.90
ZB = 0.10
NU, NV = 300, 220
OUT = Vector((0, -1, 0))
SKIN_T = 0.0035
AC = Vector((0.39, 0.03))      # wheel-arch centre (x, z)
AR = 0.355                     # wheel-arch radius


def ztop(x):
    hi = 0.645 + 0.04 * x / L
    return 0.47 + (hi - 0.47) * P.sstep(0.09, 0.25, x)


def zc(x):          # feature line (continues the door's character line)
    return 0.49 + 0.01 * x / L


def w_skin(x, z):
    """Outward bulge (towards -Y) of the outer skin."""
    zm = 0.33
    zt = ztop(x)
    if z < zm:
        sec = -0.028 * ((zm - z) / zm) ** 2.2
    else:
        sec = -0.03 * ((z - zm) / 0.33) ** 1.6
    fade = P.sstep(0.18, 0.5, x)
    sec -= 0.26 * P.softplus(z - zc(x), 0.0028) * fade
    sec -= 0.045 * (1 - fade) * max(0.0, (z - 0.40) / 0.25) ** 2
    sec -= 0.035 * (1 - P.sstep(0.0, 0.05, zt - z)) ** 2          # roll into the gutter
    w = sec + 0.028 * (1 - ((x - 0.52) / 0.62) ** 2)
    w -= 0.115 * (1 - P.sstep(0.0, 0.24, x)) ** 2                  # wrap towards the bumper
    r = (Vector((x, z)) - AC).length
    w += 0.010 * P.bump(((r - AR - 0.035) / 0.05) ** 2)            # flared arch surround
    return w


def skin_pt(x, z):
    return Vector((x, -w_skin(x, z), z))


def lift_xz(q):
    return skin_pt(q.x, q.y)


def skin_n(q):
    return P.surf_normal(lift_xz, q, sign_ref=OUT)


def lift3(q, dd=0.0):
    return skin_pt(q.x, q.y) - skin_n(q) * dd


def xr(z):
    return L + 0.012 * math.sin(math.pi * min(max(z, 0.0), 0.7) / 0.7)


ZBF = 0.30          # bottom of the front leg (meets the bumper)


def zbot(x):
    return ZB + (ZBF - ZB) * (1 - P.sstep(0.10, 0.20, x))


def grid_pt(u, v):
    x = L * u ** 1.2
    zb = zbot(x)
    z = zb + (ztop(x) - zb) * v
    x += (xr(z) - L) * u ** 4
    # rounded bottom-rear corner and front-bottom corner
    return skin_pt(x, z)


def rrect_poly(cx, cz, hx, hz, r, n_edge=12, n_arc=10):
    pts = []

    def arc(x0, z0, a0):
        for k in range(n_arc):
            a = a0 + (math.pi / 2) * k / n_arc
            pts.append(Vector((x0 + r * math.cos(a), z0 + r * math.sin(a))))

    def edge(p, q):
        for k in range(n_edge):
            pts.append(p.lerp(q, k / n_edge))

    edge(Vector((cx - hx + r, cz - hz)), Vector((cx + hx - r, cz - hz)))
    arc(cx + hx - r, cz - hz + r, -math.pi / 2)
    edge(Vector((cx + hx, cz - hz + r)), Vector((cx + hx, cz + hz - r)))
    arc(cx + hx - r, cz + hz - r, 0)
    edge(Vector((cx + hx - r, cz + hz)), Vector((cx - hx + r, cz + hz)))
    arc(cx - hx + r, cz + hz - r, math.pi / 2)
    edge(Vector((cx - hx, cz + hz - r)), Vector((cx - hx, cz - hz + r)))
    arc(cx - hx + r, cz - hz + r, math.pi)
    return pts


IND = rrect_poly(0.655, 0.425, 0.032, 0.0115, 0.0105)


def shell(paint, ecoat):
    rows = [[grid_pt(i / NU, j / NV) for i in range(NU + 1)] for j in range(NV + 1)]
    ob = P.grid_obj("WingSkin", rows, [paint, ecoat], OUT)
    P.solidify(ob, SKIN_T, offset=-1, inner=1, rim=0)
    cb = bmesh.new()
    arch = [AC + Vector((math.cos(a), math.sin(a))) * AR for a in [math.tau * k / 256 for k in range(256)]]
    P.prism_bm(cb, arch, lift3, -0.08, 0.12)
    P.prism_bm(cb, IND, lift3, -0.03, 0.04)
    C.fix_normals(cb)
    cut = C.mesh_obj("Cutters", cb, [ecoat])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.0015, segments=2, angle=45)
    return C.finalize(ob, angle=40, remove=[cut])


def sheet_section(poly, t, r=0.003):
    """Closed section of a bent sheet strip following the open polyline poly (a, b)."""
    pts = P.rounded(poly, [r] * len(poly), closed=False, seg=6)
    pts = P.resample(pts, 40)
    inner = P.offset2d(pts, -t)
    sec = pts + inner[::-1]
    return [(p.x, p.y) for p in sec]


def arch_lip(paint):
    a0 = math.asin((ZB - AC.y) / AR) + 0.004
    a1 = math.pi - math.asin((ZBF - AC.y) / AR) - 0.004
    path = [AC + Vector((math.cos(a), math.sin(a))) * (AR + 0.0005) for a in
            [a0 + (a1 - a0) * k / 260 for k in range(261)]]
    fr = P.frames_on_surface(path, lift_xz, OUT)
    # rolled bead at the edge + return flange folding in towards the wheel-house
    sec = P.rounded([(-0.0075, 0.0018), (0.0015, 0.0022), (0.0030, -0.005), (0.0018, -0.036),
                     (-0.0010, -0.036), (-0.0016, -0.008), (-0.0075, -0.004)], [0.0035, 0.0035, 0.003, 0.001, 0.001, 0.002, 0.003],
                    closed=True, seg=5)
    return [P.tube_obj("ArchLip", fr, [(p.x, p.y) for p in sec], [paint], smooth_angle=60)]


def top_flange(paint, ecoat):
    xs = [0.235 + (L - 0.012 - 0.235) * k / 200 for k in range(201)]
    pts = []
    for x in xs:
        z = ztop(x)
        pts.append(skin_pt(x, z))
    fr = []
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        B = Vector((0, 0, 1))
        A = T.cross(B)
        if A.y < 0:
            A = -A
        B = A.cross(T)
        if B.z < 0:
            B = -B
        fr.append((p, A, B))
    sec = sheet_section([(-0.002, 0.0), (0.006, -0.0015), (0.010, -0.007), (0.011, -0.018),
                         (0.016, -0.021), (0.056, -0.021), (0.060, -0.017)], 0.0022)
    bm = bmesh.new()
    P.tube_bm(bm, fr, sec)
    C.fix_normals(bm)
    ob = C.mesh_obj("TopFlange", bm, [paint])
    cb = bmesh.new()
    for x in (0.33, 0.50, 0.66, 0.80):
        k = min(range(len(xs)), key=lambda i: abs(xs[i] - x))
        Pp, A, B = fr[k]
        c = Pp + A * 0.037 + B * -0.022
        M = P.basis(A.cross(B), A, B, c) @ Matrix.Diagonal((1.0, 1.6, 1.0, 1.0))
        C.cyl_bm(cb, 0.0042, -0.02, 0.02, seg=24, matrix=M)
    cut = C.mesh_obj("FlangeHoles", cb, [ecoat])
    C.add_boolean(ob, cut)
    return [C.finalize(ob, angle=50, remove=[cut])]


def rear_flange(paint, ecoat):
    zs = [ZB + 0.01 + (ztop(L) - 0.03 - ZB) * k / 120 for k in range(121)]
    pts = [skin_pt(xr(z) - 0.0008, z) for z in zs]
    fr = P.path_frames(pts, (1, 0, 0))
    fr = [(p, A if A.y > 0 else -A, B) for (p, A, B) in fr]
    sec = sheet_section([(-0.001, 0.0), (0.004, -0.001), (0.007, -0.006), (0.030, -0.006)], 0.0022)
    sec = [(a, -b) for (a, b) in sec][::-1]      # bend forward (towards -X) instead of rearward
    bm = bmesh.new()
    P.tube_bm(bm, fr, sec)
    C.fix_normals(bm)
    ob = C.mesh_obj("RearFlange", bm, [paint])
    cb = bmesh.new()
    for z in (0.24, 0.52):
        k = min(range(len(zs)), key=lambda i: abs(zs[i] - z))
        Pp, A, B = fr[k]
        c = Pp + A * 0.021
        C.cyl_bm(cb, 0.0045, -0.03, 0.03, seg=24, matrix=Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    cut = C.mesh_obj("RearHoles", cb, [ecoat])
    C.add_boolean(ob, cut)
    return [C.finalize(ob, angle=50, remove=[cut])]


def front_tab(ecoat_paint):
    """Small bumper-mount tab folded in at the front lower end."""
    q = Vector((0.012, 0.36))
    p = lift3(q, 0.0)
    bm = bmesh.new()
    C.box_bm(bm, 0.003, 0.045, 0.05, center=(p.x + 0.004, p.y + 0.022, p.z))
    ob = C.mesh_obj("FrontTab", bm, [ecoat_paint])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.0045, -0.03, 0.03, seg=24, matrix=Matrix.Translation((p.x, p.y + 0.028, p.z)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    cut = C.mesh_obj("TabHole", cb, [ecoat_paint])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.001, segments=2, angle=30)
    return [C.finalize(ob, angle=35, remove=[cut])]


def indicator_wall(black):
    """Dark return wall inside the indicator hole so it reads as an opening."""
    c = sum(IND, Vector((0, 0))) / len(IND)
    rows = [[lift3(c + (q - c) * 0.97, dd) for q in IND] for dd in (0.001, 0.01, 0.02)]
    ob = P.grid_obj("IndicatorWall", rows, [black], lambda v: lift3(c, 0.0) - v, closed_u=True)
    P.solidify(ob, 0.0015, offset=1)
    return [C.finalize(ob, angle=50)]


def build():
    paint = P.body_paint()
    ec = P.ecoat()
    objs = [shell(paint, ec)]
    objs += arch_lip(paint)
    objs += top_flange(paint, ec)
    objs += rear_flange(paint, ec)
    objs += front_tab(ec)
    objs += indicator_wall(C.mat_black_plastic("HoleBlack", rough=0.6))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("parafango", objs, "parafango.py",
            "front left wing/fender (generic small hatchback), metallic grey paint: crowned skin with feature line, "
            "wheel-arch cut-out with rolled lip, side indicator hole, bolting flanges along the top and rear edges",
            az=28, el=32, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
