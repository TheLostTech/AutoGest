"""Front left door window glass of a generic modern small hatchback, removed from the door.
Curved (tumblehome) tempered glass with a light green tint, unframed shape: vertical front
edge behind the mirror sail, raked A-pillar edge, gently rounded top-rear corner, long
lower part that drops inside the door; ground edges that catch the light; two black
regulator-rail clamps bolted through the bottom edge. Car front is -X, outside is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
T = 0.0045
RAD = 1.35        # vertical curvature radius


def glass_pt(q, off=0.0):
    x, z = q.x, q.y
    y = z * z / (2 * RAD) + 0.006 * ((x - 0.52) / 0.35) ** 2
    return Vector((x, y - off, z))


def outline():
    corners = [(0.20, 0.09), (0.20, 0.455), (0.47, 0.748), (0.80, 0.738), (0.866, 0.672), (0.856, 0.03), (0.29, 0.0)]
    radii = [0.04, 0.11, 0.16, 0.06, 0.045, 0.04, 0.07]
    pts = P.rounded(corners, radii, closed=True, seg=20)
    return P.resample(pts, 520, closed=True)


def mat_glass():
    """Clear green-tinted glass + a faint opaque green component so the tint survives
    alpha compositing on any page background."""
    m = C.principled("SideGlass", (0.80, 0.93, 0.86), rough=0.0, IOR=1.52)
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


def mat_edge():
    m = C.principled("GroundEdge", (0.55, 0.86, 0.70), rough=0.22, IOR=1.52)
    C._set(P.bsdf(m), "Transmission Weight", 0.15)
    return m


def glass(gm, em):
    poly = outline()
    c = sum(poly, Vector((0, 0))) / len(poly)
    ob = P.fan_obj("Glass", poly, c, 44, glass_pt, [gm, em], OUT, power=1.25)
    P.solidify(ob, T, offset=-1, rim=1)
    C.add_bevel(ob, 0.0016, segments=3, angle=50)
    return C.finalize(ob, angle=55)


def bottom_z(x):
    return 0.03 * (x - 0.29) / (0.856 - 0.29)


def clamps(black, zinc, rubber):
    out = []
    for x in (0.38, 0.72):
        zb = bottom_z(x)
        q = Vector((x, zb + 0.02))
        o = glass_pt(q, T / 2)
        n = P.surf_normal(glass_pt, q, sign_ref=OUT)
        Zl = Vector((0, 0, 1))
        Zl = (Zl - n * Zl.dot(n)).normalized()
        Xl = Zl.cross(n).normalized()
        if Xl.x < 0:
            Xl = -Xl
        M = P.basis(Xl, n, Zl, o)        # local Y = outward normal
        bm = bmesh.new()
        for s in (-1, 1):
            C.box_bm(bm, 0.090, 0.005, 0.048, center=(0, s * (T / 2 + 0.0035), -0.012), matrix=M)
        C.box_bm(bm, 0.090, T + 0.012, 0.008, center=(0, 0, -0.036 - 0.0), matrix=M)
        C.box_bm(bm, 0.050, 0.016, 0.030, center=(0.0, 0.003, -0.054), matrix=M)
        C.box_bm(bm, 0.004, 0.012, 0.022, center=(-0.03, 0.003, -0.047), matrix=M)
        C.box_bm(bm, 0.004, 0.012, 0.022, center=(0.03, 0.003, -0.047), matrix=M)
        ob = C.mesh_obj("Clamp", bm, [black])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.0062, -0.03, 0.03, seg=32, matrix=M @ Matrix.Translation((0, 0, -0.056)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        cut = C.mesh_obj("ClampHole", cb, [black])
        C.add_boolean(ob, cut)
        C.add_bevel(ob, 0.0014, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35, remove=[cut]))
        # rubber liner showing along the top of the jaws
        for s in (-1, 1):
            bm = bmesh.new()
            C.box_bm(bm, 0.088, 0.0022, 0.004, center=(0, s * (T / 2 + 0.0011), 0.0115), matrix=M)
            lr = C.mesh_obj("Liner", bm, [rubber])
            C.add_bevel(lr, 0.0008, segments=2, angle=30)
            out.append(C.finalize(lr, angle=35))
        # through bolts: hex heads on the outer jaw, washers
        for dx in (-0.024, 0.024):
            hd = C.lathe("BoltHead", [(0.0, 0.0, 0), (0.0068, 0.0, 0), (0.0068, 0.0045, 0), (0.0058, 0.0058, 0), (0.0, 0.006, 0)],
                         [zinc], steps=6)
            hd.matrix_world = M @ Matrix.Translation((dx, T / 2 + 0.006, -0.008)) @ Matrix.Rotation(math.radians(-90), 4, "X")
            C.add_bevel(hd, 0.0007, segments=2, angle=30)
            out.append(C.finalize(hd, angle=35))
            ws = C.lathe("Washer", [(0.0035, 0.0, 0), (0.0095, 0.0, 0), (0.0095, 0.0012, 0), (0.0035, 0.0012, 0)], [zinc], steps=40)
            ws.matrix_world = M @ Matrix.Translation((dx, T / 2 + 0.006, -0.008)) @ Matrix.Rotation(math.radians(-90), 4, "X")
            out.append(C.finalize(ws, angle=35))
        # plastic bushing in the mounting hole
        bu = C.lathe("Bush", [(0.0035, -0.010, 0), (0.0062, -0.010, 0), (0.0062, 0.010, 0), (0.0085, 0.010, 0), (0.0085, 0.012, 0), (0.0035, 0.012, 0)],
                     [rubber], steps=32)
        bu.matrix_world = M @ Matrix.Translation((0, 0.003, -0.056)) @ Matrix.Rotation(math.radians(90), 4, "X")
        out.append(C.finalize(bu, angle=40))
    return out


def build():
    gm = mat_glass()
    em = mat_edge()
    black = C.mat_black_plastic("ClampPA", rough=0.45, color=0.025)
    zinc = C.principled("Zinc", (0.66, 0.66, 0.68), metallic=1.0, rough=0.3)
    C.add_noise_bump(zinc, scale=500, strength=0.05, distance=0.0003, rough_var=0.05)
    rubber = C.mat_rubber()
    objs = [glass(gm, em)]
    objs += clamps(black, zinc, rubber)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("cristallo", objs, "cristallo.py",
            "front left door window glass (generic small hatchback): curved green-tinted tempered glass, unframed shape, "
            "two black regulator-rail clamps bolted at the bottom edge",
            az=-30, el=12, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
