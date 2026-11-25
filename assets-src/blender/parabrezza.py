"""Windscreen of a generic modern small hatchback, removed from the car, shown as fitted
(raked back) from the outside. Large laminated glass curved both ways, light green tint
with a blue-green shade band along the top; black ceramic frit border (wide along the
bottom), with the dot-matrix fade along its inner edge and a dotted patch behind the
rear-view mirror at the top centre; metal mirror mounting button bonded just below the
patch; ground, faintly green edges. Car front is -Y.
Like cristallo.py, the glass carries a faint opaque tint so it reads on light and dark
pages, and the white floor is kept out of its reflections."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

RAKE = math.radians(33)
VH = 0.80                         # height along the glass
T = 0.0052                        # laminated thickness
N0 = Vector((0, -math.sin(RAKE), math.cos(RAKE)))   # outward normal of the flat reference
FRIT_OFF = -0.00025               # frit sits under the outer ply; drawn just at the outer face so the
                                  # glass's faint opaque tint does not wash it out


def gpt(q, off=0.0):
    """2D (u across, v up the glass) -> 3D on the outer face, off behind it."""
    u, v = q.x, q.y
    t = v / VH
    base = Vector((u, v * math.cos(RAKE), v * math.sin(RAKE)))
    wrap = (0.085 + 0.03 * (1 - t)) * (u / 0.70) ** 2 + 0.012 * (u / 0.70) ** 4
    bulge = 0.022 * 4 * t * (1 - t)
    p = base + N0 * (bulge - wrap)
    return p - nrm(q) * off if off else p


def nrm(q):
    return P.surf_normal(lambda p: gpt(p), q, sign_ref=Vector((0, -1, 1)))


def outline(ib=0.0, isd=0.0, it=0.0, ne=60, seg=14):
    """Rounded trapezoid, optionally inset (bottom, sides, top); fixed point count so
    outlines with different insets correspond point for point."""
    wb, wt = 0.705, 0.585
    def side_u(v):
        return wb + (wt - wb) * v / VH
    v0, v1 = ib, VH - it
    def su(v, s):
        # side line inset perpendicular-ish by isd
        return s * (side_u(v) - isd)
    corners = [Vector((su(v0, -1), v0)), Vector((su(v0, 1), v0)), Vector((su(v1, 1), v1)), Vector((su(v1, -1), v1))]
    radii = [0.06, 0.06, 0.11, 0.11]
    radii = [max(0.012, r - min(ib, isd, it) * 0.6) for r in radii]
    pts = []
    n = 4
    for i in range(n):
        a, c, b = corners[i - 1], corners[i], corners[(i + 1) % n]
        r = radii[i]
        p0 = c + (a - c).normalized() * r
        p2 = c + (b - c).normalized() * r
        for j in range(seg):
            t = j / seg
            pts.append(p0 * (1 - t) ** 2 + c * 2 * t * (1 - t) + p2 * t * t)
        # straight run to the next corner's fillet start
        rn = radii[(i + 1) % n]
        cn = b
        q0 = p2
        q1 = cn + (c - cn).normalized() * rn
        for j in range(ne):
            pts.append(q0.lerp(q1, j / ne))
    # slight sag of top and bottom edges
    out = []
    for p in pts:
        uu = p.x / 0.7
        w = min(1.0, max(0.0, p.y / VH))
        out.append(Vector((p.x, p.y - 0.010 * uu * uu * (1 - w) + 0.012 * (1 - uu * uu) * w)))
    return out


def mat_glass():
    """Clear glass + faint opaque green component (reads on any page); shade band at the top."""
    m = C.principled("Windscreen", (0.82, 0.94, 0.88), rough=0.0, IOR=1.52)
    nt = m.node_tree
    a = P.bsdf(m)
    C._set(a, "Transmission Weight", 1.0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.08
    C._set(b, "Coat Weight", 0.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    zt = VH * math.sin(RAKE)
    band = nt.nodes.new("ShaderNodeMapRange")
    band.inputs["From Min"].default_value = zt * 0.80
    band.inputs["From Max"].default_value = zt * 0.90
    nt.links.new(sep.outputs["Z"], band.inputs["Value"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (0.21, 0.37, 0.30, 1)
    col.inputs["B"].default_value = (0.05, 0.16, 0.20, 1)
    nt.links.new(band.outputs["Result"], col.inputs["Factor"])
    nt.links.new(col.outputs["Result"], b.inputs["Base Color"])
    fac = nt.nodes.new("ShaderNodeMapRange")
    fac.inputs["To Min"].default_value = 0.15
    fac.inputs["To Max"].default_value = 0.42
    nt.links.new(band.outputs["Result"], fac.inputs["Value"])
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def mat_edge():
    m = C.principled("GroundEdge", (0.55, 0.84, 0.70), rough=0.25, IOR=1.52)
    C._set(P.bsdf(m), "Transmission Weight", 0.15)
    return m


def glass(gm, em):
    poly = outline()
    c = Vector((0.0, VH / 2))
    ob = P.fan_obj("Glass", poly, c, 60, gpt, [gm, em], N0, power=1.15)
    P.solidify(ob, T, offset=-1, rim=1)
    C.add_bevel(ob, 0.0018, segments=3, angle=50)
    return C.finalize(ob, angle=55)


def frit_band(frit):
    outer = outline(0.002, 0.002, 0.002)
    inner = outline(0.088, 0.030, 0.046)
    rows = [[gpt(a.lerp(b, k / 6), FRIT_OFF) for a, b in zip(outer, inner)] for k in range(7)]
    ob = P.grid_obj("FritBand", rows, [frit], N0, closed_u=True)
    return C.finalize(ob, angle=60)


def patch_poly():
    return P.resample(P.rounded([(-0.075, 0.615), (0.075, 0.615), (0.098, VH - 0.03), (-0.098, VH - 0.03)],
                                [0.02, 0.02, 0.0, 0.0], closed=True, seg=8), 120, closed=True)


def mirror_patch(frit):
    poly = patch_poly()
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.fan_obj("MirrorPatch", poly, c, 8, lambda q: gpt(q, FRIT_OFF + 0.00005), [frit], N0, power=1.0)
    return C.finalize(ob, angle=60)


def dots(frit):
    """Dot-matrix fade along the inner edge of the band and round the mirror patch."""
    bm = bmesh.new()
    inner = outline(0.088, 0.030, 0.046)
    sg = 1 if P.signed_area(inner) > 0 else -1

    def ring_dots(poly, sgn, rows_, pitch, r0, closed=True):
        P2 = P.resample(poly, max(8, int(sum((poly[i] - poly[i - 1]).length for i in range(1, len(poly))) / pitch)), closed=closed)
        for k in range(1, rows_ + 1):
            off = P.offset2d(P2, sgn * pitch * k * 0.95, closed=closed)
            r = r0 * (1 - 0.24 * k)
            for i, q in enumerate(off):
                if k % 2 == 0 and i % 1 == 0:
                    q = q.lerp(off[(i + 1) % len(off)], 0.5)
                ct = gpt(q, FRIT_OFF)
                nn = nrm(q)
                X = (gpt(q + Vector((0.001, 0))) - gpt(q)).normalized()
                Y = nn.cross(X)
                vs = [bm.verts.new(ct + (X * math.cos(a) + Y * math.sin(a)) * r) for a in [math.tau * j / 8 for j in range(8)]]
                bm.faces.new(vs)

    ring_dots(inner, sg, 4, 0.0062, 0.0026)
    patch = patch_poly()
    sp = 1 if P.signed_area(patch) > 0 else -1
    # only the lower part of the patch outline gets dots (the top merges into the band)
    lower = [q for q in patch if q.y < 0.70]
    lower.sort(key=lambda q: math.atan2(q.y - 0.70, q.x))
    ring_dots(lower, -sp, 3, 0.0062, 0.0026, closed=False)
    C.fix_normals(bm)
    ob = C.mesh_obj("FritDots", bm, [frit])
    return ob


def mirror_button(metal, adhesive):
    q = Vector((0.0, 0.598))
    o = gpt(q, T)
    nn = nrm(q)
    X = Vector((1, 0, 0))
    Yv = nn.cross(X).normalized()
    M = P.basis(X, Yv, -nn, o)          # local +Z points into the car
    bm = bmesh.new()
    P.superellipsoid(bm, 0.0135, 0.011, 0.0032, e1=0.25, e2=0.35, matrix=M @ Matrix.Translation((0, 0, 0.0036)))
    ob = C.mesh_obj("MirrorButton", bm, [metal])
    out = [C.finalize(ob, angle=40)]
    bm = bmesh.new()
    P.superellipsoid(bm, 0.0145, 0.012, 0.0006, e1=0.2, e2=0.3, matrix=M @ Matrix.Translation((0, 0, 0.0005)))
    out.append(C.finalize(C.mesh_obj("Adhesive", bm, [adhesive]), angle=40))
    return out


def matte_floor_in_reflections():
    orig = C._area

    def _area(*a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        return orig(*a, **k)
    C._area = _area


def build():
    gm = mat_glass()
    em = mat_edge()
    frit = C.principled("CeramicFrit", (0.008, 0.008, 0.009), rough=0.05)
    metal = C.principled("ButtonSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.35)
    adhesive = C.principled("Adhesive", (0.05, 0.05, 0.05), rough=0.6)
    objs = [glass(gm, em), frit_band(frit), mirror_patch(frit), dots(frit)]
    objs += mirror_button(metal, adhesive)
    return objs


if __name__ == "__main__":
    matte_floor_in_reflections()
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("parabrezza", objs, "parabrezza.py",
            "windscreen (generic small hatchback): large curved laminated glass, light green tint with shade band, "
            "black ceramic frit border with dot fade, dotted mirror patch, rear-view mirror mounting button",
            az=-28, el=22, lens=70, fill=0.88, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
