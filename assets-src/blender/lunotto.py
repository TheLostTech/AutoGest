"""Rear window glass (tailgate glass) of a generic modern small hatchback, removed from the
car and shown as fitted from the outside. Curved toughened glass with a dark privacy tint,
black ceramic frit border with dot fade, printed heater grid (thin horizontal lines and a
bus bar down each side) with soldered spade terminals, and a rubber grommet in the hole
for the rear wiper spindle. Car rear (outside) is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

RAKE = math.radians(57)           # from horizontal
VH = 0.46                         # height along the glass
T = 0.0045
N0 = Vector((0, -math.sin(RAKE), math.cos(RAKE)))
FRIT_OFF = -0.00025              # printed on the inner face; drawn at the outer face so the tint does not hide it
WB, WT = 0.47, 0.42               # half widths bottom / top
WIPER = Vector((0.0, 0.052))


def gpt(q, off=0.0):
    u, v = q.x, q.y
    t = v / VH
    base = Vector((u, v * math.cos(RAKE), v * math.sin(RAKE)))
    wrap = (0.075 + 0.02 * t) * (u / WB) ** 2 + 0.01 * (u / WB) ** 4
    bulge = 0.012 * 4 * t * (1 - t)
    p = base + N0 * (bulge - wrap)
    return p - nrm(q) * off if off else p


def nrm(q):
    return P.surf_normal(lambda p: gpt(p), q, sign_ref=N0)


def outline(ib=0.0, isd=0.0, it=0.0, ne=60, seg=14):
    def side_u(v):
        return WB + (WT - WB) * v / VH
    v0, v1 = ib, VH - it
    corners = [Vector((-(side_u(v0) - isd), v0)), Vector((side_u(v0) - isd, v0)),
               Vector((side_u(v1) - isd, v1)), Vector((-(side_u(v1) - isd), v1))]
    radii = [max(0.012, r - min(ib, isd, it) * 0.6) for r in (0.07, 0.07, 0.10, 0.10)]
    pts = []
    for i in range(4):
        a, c, b = corners[i - 1], corners[i], corners[(i + 1) % 4]
        r = radii[i]
        p0 = c + (a - c).normalized() * r
        p2 = c + (b - c).normalized() * r
        for j in range(seg):
            t = j / seg
            pts.append(p0 * (1 - t) ** 2 + c * 2 * t * (1 - t) + p2 * t * t)
        q1 = b + (c - b).normalized() * radii[(i + 1) % 4]
        for j in range(ne):
            pts.append(p2.lerp(q1, j / ne))
    out = []
    for p in pts:
        uu = p.x / WB
        w = min(1.0, max(0.0, p.y / VH))
        out.append(Vector((p.x, p.y + 0.012 * (1 - uu * uu) * w - 0.006 * uu * uu * (1 - w))))
    return out


def mat_glass():
    m = C.mat_clear("RearGlassTint", ior=1.52)
    nt = m.node_tree
    a = P.bsdf(m)
    C._set(a, "Base Color", (0.34, 0.40, 0.38, 1))
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.012, 0.016, 0.016, 1)
    b.inputs["Roughness"].default_value = 0.03
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.36
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def mat_edge():
    m = C.principled("GroundEdge", (0.45, 0.58, 0.54), rough=0.25, IOR=1.52)
    C._set(P.bsdf(m), "Transmission Weight", 0.15)
    return m


def glass(gm, em):
    poly = outline()
    ob = P.fan_obj("Glass", poly, Vector((0.0, VH / 2)), 40, gpt, [gm, em], N0, power=1.15)
    P.solidify(ob, T, offset=-1, rim=1)
    cb = bmesh.new()
    c = WIPER
    P.prism_bm(cb, [c + Vector((math.cos(a), math.sin(a))) * 0.0105 for a in [math.tau * k / 48 for k in range(48)]],
               lambda q, d: gpt(q) - nrm(q) * d, -0.02, 0.03)
    C.fix_normals(cb)
    cut = C.mesh_obj("WiperHole", cb, [gm])
    m = C.add_boolean(ob, cut)
    m.solver = "MANIFOLD"
    C.add_bevel(ob, 0.0016, segments=3, angle=50)
    return C.finalize(ob, angle=55, remove=[cut])


FRIT_IN = (0.062, 0.042, 0.046)


def frit_band(frit):
    outer = outline(0.002, 0.002, 0.002)
    inner = outline(*FRIT_IN)
    rows = [[gpt(a.lerp(b, k / 6), FRIT_OFF) for a, b in zip(outer, inner)] for k in range(7)]
    ob = P.grid_obj("FritBand", rows, [frit], N0, closed_u=True)
    return C.finalize(ob, angle=60)


def dots(frit):
    bm = bmesh.new()
    inner = outline(*FRIT_IN)
    sg = 1 if P.signed_area(inner) > 0 else -1
    L = sum((inner[i] - inner[i - 1]).length for i in range(len(inner)))
    pitch = 0.006
    P2 = P.resample(inner, int(L / pitch), closed=True)
    for k in range(1, 4):
        off = P.offset2d(P2, sg * pitch * k * 0.95, closed=True)
        r = 0.0025 * (1 - 0.24 * k)
        for i, q in enumerate(off):
            if k % 2 == 0:
                q = q.lerp(off[(i + 1) % len(off)], 0.5)
            ct = gpt(q, FRIT_OFF)
            nn = nrm(q)
            X = (gpt(q + Vector((0.001, 0))) - gpt(q)).normalized()
            Y = nn.cross(X)
            bm.faces.new([bm.verts.new(ct + (X * math.cos(a) + Y * math.sin(a)) * r) for a in [math.tau * j / 8 for j in range(8)]])
    C.fix_normals(bm)
    return C.mesh_obj("FritDots", bm, [frit])


def heater(mat, term_m):
    out = []
    ib, isd, it = FRIT_IN
    z0, z1 = ib + 0.03, VH - it - 0.03
    n = 14
    vs = [z0 + (z1 - z0) * k / (n - 1) for k in range(n)]
    lift = lambda q: gpt(q, T + 0.00035)
    bm = bmesh.new()

    def xb(v):
        return WB + (WT - WB) * v / VH - isd - 0.018

    for v in vs:
        h = xb(v)
        pts = [Vector((-h + 2 * h * k / 120, v)) for k in range(121)]
        fr = P.frames_on_surface(pts, lift, -N0)
        P.tube_bm(bm, fr, P.rrect(-0.0006, 0.0006, -0.00012, 0.00012, 0.0001, seg=1))
    for sx in (-1, 1):
        pts = []
        for k in range(61):
            v = vs[0] - 0.008 + (vs[-1] - vs[0] + 0.016) * k / 60
            pts.append(Vector((sx * xb(v), v)))
        fr = P.frames_on_surface(pts, lift, -N0)
        P.tube_bm(bm, fr, P.rrect(-0.0085, 0.0085, -0.00015, 0.00015, 0.001, seg=1))
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("HeaterGrid", bm, [mat]), angle=60))
    # soldered spade terminals in the middle of each bus bar
    for sx in (-1, 1):
        v = (vs[0] + vs[-1]) / 2
        q = Vector((sx * xb(v), v))
        o = gpt(q, T + 0.0005)
        nn = nrm(q)
        Xl = Vector((0, 0, 1))
        Xl = (Xl - nn * Xl.dot(nn)).normalized()
        Yl = nn.cross(Xl)
        M = P.basis(Xl, Yl, -nn, o)
        bm = bmesh.new()
        C.box_bm(bm, 0.022, 0.010, 0.0012, center=(0, 0, 0.0006), matrix=M)                   # solder pad
        C.box_bm(bm, 0.0012, 0.0063, 0.012, center=(0.006, 0, 0.0065), matrix=M)              # blade
        tb = C.mesh_obj("Terminal", bm, [term_m])
        C.add_bevel(tb, 0.0003, segments=1, angle=30)
        out.append(C.finalize(tb, angle=35))
    return out


def grommet(rubber):
    q = WIPER
    o = gpt(q)
    nn = nrm(q)
    X = Vector((1, 0, 0))
    M = P.basis(X, nn.cross(X).normalized(), nn, o)
    ob = C.lathe("WiperGrommet", [(0.0068, -T - 0.004, 0), (0.0104, -T - 0.004, 0), (0.0104, -T - 0.0005, 0),
                                  (0.0135, -T - 0.0005, 0), (0.0135, -T - 0.003, 0), (0.0145, -T - 0.003, 0),
                                  (0.0145, 0.0005, 0), (0.0125, 0.0026, 0), (0.0068, 0.0026, 0)], [rubber], steps=48)
    ob.matrix_world = M
    return [C.finalize(ob, angle=40)]


def build():
    gm = mat_glass()
    em = mat_edge()
    frit = C.principled("CeramicFrit", (0.008, 0.008, 0.009), rough=0.05)
    heat = C.principled("HeaterPrint", (0.20, 0.085, 0.04), metallic=0.6, rough=0.45)
    term = C.principled("TinnedCopper", (0.75, 0.74, 0.70), metallic=1.0, rough=0.3)
    rubber = C.mat_rubber()
    objs = [glass(gm, em), frit_band(frit), dots(frit)]
    objs += heater(heat, term)
    objs += grommet(rubber)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("lunotto", objs, "lunotto.py",
            "rear window glass (generic small hatchback): curved privacy-tinted glass with black ceramic frit border, "
            "printed heater grid with bus bars and spade terminals, rear wiper grommet",
            az=-30, el=18, lens=70, fill=0.88, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
