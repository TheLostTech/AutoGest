"""Steering wheel without airbag (volante senza airbag): three-spoke wheel with a black
leather-look rim (grain, seam on the inner side with grey cross stitching), black
soft-touch spokes with satin-silver trim inserts, and an empty airbag cavity showing the
grey die-cast magnesium armature with the splined hub bore, airbag fixing holes, the
clock-spring connector and horn contact. No logos.

Built in the XY plane (face toward +Z, X right, Y up), then stood up facing the camera.
Units ~ decimetres (outer diameter ~37 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RW = 1.66            # rim centre-line radius
SR, SZ = 0.165, 0.150   # rim section half-size (radial, axial)
HUB_R = 0.70


def rim_frame(th):
    P = Vector((RW * math.cos(th), RW * math.sin(th), 0.0))
    U = Vector((math.cos(th), math.sin(th), 0.0))       # radial out
    V = Vector((0, 0, 1.0))                             # toward driver
    T = Vector((-math.sin(th), math.cos(th), 0.0))
    return P, U, V, T


def rim_section(phi):
    """D-ish section: fuller on the driver/inner side."""
    c, s = math.cos(phi), math.sin(phi)
    k = 1.0 + 0.06 * (-c)
    return (SR * c * k, SZ * s)


def rim(leather):
    bm = bmesh.new()
    n, m = 320, 40
    frames = []
    for i in range(n):
        th = math.tau * i / n
        P, U, V, T = rim_frame(th)
        sec = [rim_section(math.tau * j / m) for j in range(m)]
        frames.append((P, U, V, sec))
    rings = [[bm.verts.new(P + u * U + v * V) for (u, v) in sec] for (P, U, V, sec) in frames]
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    C.fix_normals(bm)
    ob = C.mesh_obj("Rim", bm, [leather])
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def stitches(thread, seam):
    """cross stitching along the seam on the inner side of the rim."""
    bm = bmesh.new()
    phi0 = math.pi            # inner side
    dphi = 0.17
    n = 190
    for i in range(n):
        th = math.tau * (i + 0.5) / n
        P, U, V, T = rim_frame(th)
        for side in (-1, 1):
            u, v = rim_section(phi0 + side * dphi)
            pos = P + U * u * 1.004 + V * v * 1.004
            # stitch runs diagonally from the row toward the seam
            nrm = (U * math.cos(phi0 + side * dphi) + V * math.sin(phi0 + side * dphi)).normalized()
            d = (T * 0.6 - side * V * 0.8).normalized()
            w = nrm.cross(d).normalized()
            M = Matrix((
                (d.x, w.x, nrm.x, pos.x),
                (d.y, w.y, nrm.y, pos.y),
                (d.z, w.z, nrm.z, pos.z),
                (0, 0, 0, 1)))
            C.box_bm(bm, 0.034, 0.011, 0.008, matrix=M)
    st = C.mesh_obj("Stitches", bm, [thread])
    C.add_bevel(st, 0.003, segments=1, angle=30)
    out = [C.finalize(st, angle=60)]
    # thin dark seam line between the two rows
    bm = bmesh.new()
    frames = []
    for i in range(240):
        th = math.tau * i / 240
        P, U, V, T = rim_frame(th)
        u, v = rim_section(phi0)
        c = P + U * (u + 0.002) + V * v
        sec = [(0.006 * math.cos(math.tau * j / 8), 0.006 * math.sin(math.tau * j / 8)) for j in range(8)]
        frames.append((c, U, V, sec))
    rings = [[bm.verts.new(P + a * U + b * V) for (a, b) in sec] for (P, U, V, sec) in frames]
    for i in range(240):
        a, b = rings[i], rings[(i + 1) % 240]
        for k in range(8):
            k2 = (k + 1) % 8
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    sm = C.mesh_obj("Seam", bm, [seam])
    out.append(sm)
    return out


def superellipse(w, h, n=28, e=0.38):
    pts = []
    for j in range(n):
        a = math.tau * j / n
        c, s = math.cos(a), math.sin(a)
        pts.append((w / 2 * math.copysign(abs(c) ** e, c), h / 2 * math.copysign(abs(s) ** e, s)))
    return pts


def spoke(name, th, w0, w1, h, mat, z0=-0.02, z1=0.0, r0=0.55, r1=RW, n=16, dz=0.0):
    """Spoke from the hub (r0) to the rim (r1) along polar angle th."""
    d = Vector((math.cos(th), math.sin(th), 0))
    side = Vector((-math.sin(th), math.cos(th), 0))
    frames = []
    for i in range(n + 1):
        u = i / n
        r = r0 + (r1 - r0) * u
        z = z0 + (z1 - z0) * u + dz * math.sin(math.pi * u)
        # widen into the rim
        w = w0 + (w1 - w0) * u + 0.22 * C.smoothstep(0.72, 1.0, u)
        frames.append((d * r + Vector((0, 0, z)), side, Vector((0, 0, 1)), superellipse(w, h)))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, 0.01, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def trim(name, th, w0, w1, mat, r0, r1, z):
    d = Vector((math.cos(th), math.sin(th), 0))
    side = Vector((-math.sin(th), math.cos(th), 0))
    frames = []
    n = 10
    for i in range(n + 1):
        u = i / n
        r = r0 + (r1 - r0) * u
        w = w0 + (w1 - w0) * u
        frames.append((d * r + Vector((0, 0, z + 0.012 * math.sin(math.pi * u))), side, Vector((0, 0, 1)),
                       superellipse(w, 0.035, e=0.3)))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, 0.006, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def hub(shell, mg, yellow, black, zinc):
    out = []
    # rear shroud + cavity walls (lathe, slightly oval)
    P = [(0.0, -0.62, 0), (0.30, -0.62, 0), (0.48, -0.55, 0), (0.64, -0.40, 0), (0.74, -0.20, 0),
         (0.78, 0.02, 0), (0.77, 0.10, 0), (0.73, 0.13, 0), (0.68, 0.12, 0), (0.66, 0.02, 0),
         (0.64, -0.22, 0), (0.60, -0.26, 0), (0.0, -0.26, 0)]
    ob = C.lathe("HubShell", P, [shell], steps=128)
    ob.matrix_world = Matrix.Diagonal((1.12, 1.0, 1.0, 1.0))
    out.append(C.finalize(ob, angle=40))
    # magnesium armature floor with hub boss and splined bore
    P = [(0.09, -0.25, 0), (0.62, -0.25, 0), (0.62, -0.22, 0), (0.24, -0.20, 0), (0.21, -0.12, 0),
         (0.11, -0.12, 0), (0.09, -0.14, 0)]
    def spl(r, z, t):
        if abs(r - 0.09) > 1e-6:
            return r
        return r + 0.012 * (max(-1.0, min(1.0, math.cos(36 * t) * 2.5)) * 0.5 + 0.5)
    ob = C.lathe("Armature", P, [mg], steps=288, mod=spl)
    ob.matrix_world = Matrix.Diagonal((1.1, 1.0, 1.0, 1.0))
    bm = bmesh.new()
    for x, y in ((-0.44, 0.10), (0.44, 0.10), (0.0, -0.46)):
        C.cyl_bm(bm, 0.045, -0.4, 0.0, seg=24, matrix=Matrix.Translation((x / 1.1, y, 0)))
    cut = C.mesh_obj("ArmHoles", bm, [mg])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    # bottom of the bore (dark) so the hole reads as a hole
    out.append(C.finalize(C.lathe("BoreBack", [(0.0, -0.30, 0), (0.12, -0.30, 0), (0.12, -0.28, 0), (0.0, -0.28, 0)], [black], steps=32), angle=40))
    # clock-spring connector (yellow) + horn contact block
    bm = bmesh.new()
    C.box_bm(bm, 0.18, 0.10, 0.08, center=(0.30, 0.34, -0.17))
    C.box_bm(bm, 0.06, 0.04, 0.03, center=(0.30, 0.39, -0.12))
    yc = C.mesh_obj("SquibConn", bm, [yellow])
    C.add_bevel(yc, 0.012, segments=2, angle=30)
    out.append(C.finalize(yc, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.14, 0.09, 0.07, center=(-0.30, 0.34, -0.18))
    hc = C.mesh_obj("HornConn", bm, [black])
    C.add_bevel(hc, 0.012, segments=2, angle=30)
    out.append(C.finalize(hc, angle=35))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.03, -0.24, -0.13, seg=16, matrix=Matrix.Translation((-0.12, -0.30, 0)))
    C.cyl_bm(bm, 0.045, -0.13, -0.11, seg=16, matrix=Matrix.Translation((-0.12, -0.30, 0)))
    hp = C.mesh_obj("HornPin", bm, [zinc])
    out.append(C.finalize(hp, angle=40))
    return out


def mat_leather(name):
    m = C.principled(name, (0.011, 0.011, 0.012), rough=0.45)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Sheen Weight", 0.03)
    C._set(b, "Sheen Roughness", 0.4)
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "DISTANCE_TO_EDGE"
    vo.inputs["Scale"].default_value = 220.0
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 900.0
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(vo.outputs["Distance"], add.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.3
    nt.links.new(nz.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], add.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # hand-polished areas slightly glossier
    big = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), big.inputs["Vector"])
    big.inputs["Scale"].default_value = 2.5
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.34
    mr.inputs["To Max"].default_value = 0.46
    nt.links.new(big.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def build():
    leather = mat_leather("Leather")
    thread = C.principled("Thread", (0.20, 0.20, 0.20), rough=0.7)
    seam = C.principled("Seam", (0.005, 0.005, 0.005), rough=0.8)
    soft = C.mat_black_plastic("SoftTouch", rough=0.62, color=0.028)
    shell = C.mat_black_plastic("HubShell", rough=0.5, color=0.024)
    silver = C.principled("SatinSilver", (0.55, 0.56, 0.58), metallic=1.0, rough=0.32)
    C.add_noise_bump(silver, scale=900, strength=0.03, distance=0.0004)
    mg = C.principled("Magnesium", (0.20, 0.20, 0.21), metallic=0.6, rough=0.6)
    C.add_noise_bump(mg, scale=500, strength=0.1, distance=0.0008, rough_var=0.08)
    yellow = C.principled("SquibYellow", C.srgb("#E2B21C"), rough=0.45)
    black = C.mat_black_plastic("ConnBlack", rough=0.45, color=0.02)
    zinc = C.principled("Zinc", (0.66, 0.67, 0.69), metallic=1.0, rough=0.24)

    objs = [rim(leather)] + stitches(thread, seam)
    objs += hub(shell, mg, yellow, black, zinc)
    side_a = math.radians(-12)
    for th in (side_a, math.pi - side_a):
        objs.append(spoke("SideSpoke", th, 0.62, 0.42, 0.20, soft, z0=0.0, z1=-0.02, r0=0.80))
        objs.append(trim("SideTrim", th, 0.22, 0.13, silver, 0.98, 1.38, 0.095))
    objs.append(spoke("BottomSpoke", -math.pi / 2, 0.50, 0.32, 0.18, soft, z0=0.0, z1=-0.02, r0=0.72))
    objs.append(trim("BottomTrim", -math.pi / 2, 0.14, 0.09, silver, 0.90, 1.34, 0.085))
    # stand it up facing the camera, leaning back a little
    C.transform_all(objs, Matrix.Rotation(math.radians(-16), 4, "Z") @ Matrix.Rotation(math.radians(74), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("volante", objs, "volante.py",
            "three-spoke steering wheel without airbag: black leather-look rim with stitching, "
            "silver spoke trims, empty airbag cavity with splined hub",
            az=18, el=14, lens=70, fill=0.86, samples=S, res=(R, R))
