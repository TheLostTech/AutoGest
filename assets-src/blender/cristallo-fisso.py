"""Fixed rear side (quarter) window of a generic modern small hatchback, removed from the car.
Small curved green-tinted toughened glass, roughly trapezoidal (vertical front edge, roof
line sloping down to the rear, raked C-pillar edge), fully encapsulated in a glossy black
moulded PVC frame with a lip over the glass; black ceramic frit just inside the frame;
threaded mounting studs and a locating pin on the back of the frame.
Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
T = 0.004
RAD = 1.25


def glass_pt(q, off=0.0):
    x, z = q.x, q.y
    y = z * z / (2 * RAD) + 0.004 * ((x - 0.17) / 0.2) ** 2
    p = Vector((x, y, z))
    if off:
        p -= P.surf_normal(lambda r: glass_pt(r), q, sign_ref=OUT) * off
    return p


def outline(inset=0.0, n=420):
    corners = [(0.0, 0.0), (0.37, 0.045), (0.165, 0.238), (0.0, 0.262)]
    radii = [0.022, 0.03, 0.035, 0.025]
    pts = P.rounded(corners, radii, closed=True, seg=18)
    pts = P.resample(pts, n, closed=True)
    if inset:
        pts = P.offset2d(pts, inset if P.signed_area(pts) > 0 else -inset, closed=True)
    return pts


def mat_glass():
    m = C.principled("QuarterGlass", (0.80, 0.93, 0.86), rough=0.0, IOR=1.52)
    nt = m.node_tree
    a = P.bsdf(m)
    C._set(a, "Transmission Weight", 1.0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.20, 0.36, 0.29, 1)
    b.inputs["Roughness"].default_value = 0.08
    C._set(b, "Coat Weight", 0.0)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.16
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def glass(gm):
    poly = outline(0.004)
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.fan_obj("Glass", poly, c, 30, glass_pt, [gm], OUT, power=1.25)
    P.solidify(ob, T, offset=-1)
    return C.finalize(ob, angle=55)


def frit(fm):
    outer = outline(0.006)
    inner = outline(0.024)
    rows = [[glass_pt(a.lerp(b, k / 4), -0.00025) for a, b in zip(outer, inner)] for k in range(5)]
    ob = P.grid_obj("Frit", rows, [fm], OUT, closed_u=True)
    out = [C.finalize(ob, angle=60)]
    # dot fade
    bm = bmesh.new()
    base = outline(0.024, n=int(1.05 / 0.0045))
    sg = 1 if P.signed_area(base) > 0 else -1
    for k in range(1, 4):
        off = P.offset2d(base, sg * 0.0044 * k, closed=True)
        r = 0.0017 * (1 - 0.24 * k)
        for i, q in enumerate(off):
            if k % 2 == 0:
                q = q.lerp(off[(i + 1) % len(off)], 0.5)
            ct = glass_pt(q, -0.00025)
            bm.faces.new([bm.verts.new(ct + Vector((math.cos(a) * r, 0, math.sin(a) * r))) for a in [math.tau * j / 8 for j in range(8)]])
    C.fix_normals(bm)
    out.append(C.mesh_obj("FritDots", bm, [fm]))
    return out


def encapsulation(pvc):
    poly = outline(0.0, n=480)
    fr = P.frames_on_surface(poly, glass_pt, OUT, closed=True)
    sg = 1 if P.signed_area(poly) > 0 else -1
    # A = in-surface left normal; for a CCW outline left is inward -> flip so +a is outward
    fr = [(Pp, A * -sg, B) for (Pp, A, B) in fr]
    sec = P.bspline([(-0.0105, 0.0005), (-0.005, 0.0026), (0.004, 0.0036), (0.011, 0.0026), (0.0145, -0.001),
                     (0.015, -0.008), (0.012, -0.013), (0.004, -0.012), (-0.004, -0.0085), (-0.009, -T - 0.0014),
                     (-0.0105, -T + 0.0006), (-0.011, -0.001)], 64, closed=True)
    sec = [(p.x, p.y) for p in sec]
    bm = bmesh.new()
    P.tube_bm(bm, fr, sec, closed=True)
    C.fix_normals(bm)
    ob = C.mesh_obj("Encapsulation", bm, [pvc])
    return [C.finalize(ob, angle=50)]


def studs(zinc, nylon):
    out = []
    poly = outline(0.0)
    for (x, z, kind) in ((0.05, 0.03, "stud"), (0.27, 0.07, "stud"), (0.10, 0.25, "stud"), (0.20, 0.032, "pin")):
        q = Vector((x, z))
        # push to the frame centre-line just outside the glass edge
        best = min(poly, key=lambda p: (p - q).length)
        dirv = (best - q).normalized() if (best - q).length > 1e-6 else Vector((0, 1))
        qq = best + dirv * 0.010
        o = glass_pt(qq) + Vector((0, 0.015, 0))
        n = Vector((0, 1, 0))
        M = Matrix.Translation(o) @ Matrix.Rotation(math.radians(-90), 4, "X")       # lathe Z -> +Y
        if kind == "stud":
            ob = C.lathe("StudBase", [(0.0, -0.002, 0), (0.0085, -0.002, 0), (0.0085, 0.0015, 0), (0.0, 0.0015, 0)], [zinc], steps=32)
            ob.matrix_world = M
            out.append(C.finalize(ob, angle=40))
            sh = C.lathe("Stud", [(0.0, 0.0, 0), (0.0029, 0.0, 0), (0.0029, 0.018, 0), (0.0022, 0.0195, 0), (0.0, 0.0195, 0)], [zinc], steps=24)
            sh.matrix_world = M
            out.append(C.finalize(sh, angle=50))
        else:
            ob = C.lathe("LocPin", [(0.0, -0.002, 0), (0.006, -0.002, 0), (0.006, 0.004, 0), (0.0035, 0.006, 0), (0.0035, 0.015, 0),
                                    (0.0025, 0.017, 0), (0.0, 0.017, 0)], [nylon], steps=32)
            ob.matrix_world = M
            out.append(C.finalize(ob, angle=40))
    return out


def build():
    gm = mat_glass()
    fm = C.principled("CeramicFrit", (0.008, 0.008, 0.009), rough=0.05)
    pvc = C.principled("EncapPVC", (0.016, 0.016, 0.017), rough=0.22, Coat_Weight=0.4)
    C.add_noise_bump(pvc, scale=700, strength=0.08, distance=0.0003, rough_var=0.04)
    zinc = C.principled("Zinc", (0.66, 0.66, 0.68), metallic=1.0, rough=0.3)
    nylon = C.principled("Nylon", (0.62, 0.60, 0.55), rough=0.5)
    objs = [glass(gm)]
    objs += frit(fm)
    objs += encapsulation(pvc)
    objs += studs(zinc, nylon)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("cristallo-fisso", objs, "cristallo-fisso.py",
            "fixed rear quarter window glass (generic small hatchback): small curved green-tinted glass encapsulated in a "
            "glossy black moulded frame, black frit edge, mounting studs on the back",
            az=-34, el=14, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
