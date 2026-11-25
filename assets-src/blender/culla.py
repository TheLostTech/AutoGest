"""Front subframe / engine cradle (culla motore / telaietto anteriore) of a small car:
pressed-steel welded box-section frame in black e-coat, arched rear crossmember with
seam-welded flanges and stamped holes, two side members, light front crossmember,
four body mounts (rear rubber-bushed sleeves, front towers), control-arm pickups each
side (front clevis, rear vertical-bush bracket), steering-rack pads and the rear
engine-mount clevis. Members are rounded box sections swept along paths."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm. X across, +Y forward, Z up


def mat_worn_black(name="ArmPaint"):
    m = C.mat_paint(name, (0.022, 0.022, 0.024, 1), rough=0.42, coat=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 14.0
    nz.inputs["Detail"].default_value = 10.0
    em = C.edge_mask(nt, 0.02, 5.0)
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.55
    th.inputs["From Max"].default_value = 0.62
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    nt.links.new(em, mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 1.3
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], th.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs["B"].default_value = (0.20, 0.19, 0.18, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.42
    ro.inputs["To Max"].default_value = 0.8
    nt.links.new(th.outputs["Result"], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # orange-peel
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 220.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def catmull(pts, n=8):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[i + k]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def rrect(w, h, r, n=5):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def member(name, ctrl, paint, wfn, hfn, r=0.08, flange=None, n=10):
    """box member swept along a path; wfn/hfn(t) give width (horizontal) / height.
    flange: (extra, thickness) adds a welded seam flange at mid height."""
    path = catmull(ctrl, n)
    N = len(path)
    frames, fl = [], []
    for i, p in enumerate(path):
        T = (path[min(N - 1, i + 1)] - path[max(0, i - 1)]).normalized()
        V = Vector((0, 0, 1))
        V = (V - T * V.dot(T)).normalized()
        U = V.cross(T).normalized()
        t = i / (N - 1)
        w, h = wfn(t), hfn(t)
        frames.append((p, U, V, rrect(w, h, r)))
        if flange:
            e, th = flange
            fl.append((p, U, V, [(-w / 2 - e, -th / 2), (w / 2 + e, -th / 2), (w / 2 + e, th / 2), (-w / 2 - e, th / 2)]))
    bm = bmesh.new()
    C.sweep(bm, frames)
    if flange:
        C.sweep(bm, fl)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [paint])
    return ob


def bushing(paint, rubber, steel, c, r_out, h, axis=(0, 0, 1)):
    out = []
    P = [(r_out - 0.07, -h / 2, 0), (r_out, -h / 2, 0), (r_out, h / 2, 0), (r_out - 0.07, h / 2, 0)]
    ob = C.lathe("MountSleeve", P, [paint], steps=64)
    ob.matrix_world = axis_mat(c, axis)
    C.add_bevel(ob, 0.015, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35))
    ri = r_out * 0.42
    P = [(ri, -h / 2 - 0.04, 0), (r_out - 0.07, -h / 2 - 0.03, 0), (r_out - 0.07, h / 2 + 0.02, 0),
         (r_out - 0.10, h / 2 + 0.06, 0), (ri, h / 2 + 0.06, 0)]
    out.append(C.finalize(C.lathe("MountRubber", P, [rubber], steps=64), angle=45))
    out[-1].matrix_world = axis_mat(c, axis)
    P = [(ri - 0.05, -h / 2 - 0.08, 0), (ri, -h / 2 - 0.08, 0), (ri, h / 2 + 0.12, 0), (ri - 0.05, h / 2 + 0.12, 0)]
    out.append(C.finalize(C.lathe("MountCore", P, [steel], steps=40), angle=40))
    out[-1].matrix_world = axis_mat(c, axis)
    return out


def frame(paint):
    out = []
    # rear crossmember: arched, wide, with seam flanges and stamped holes
    rear = member("RearX", [(-4.75, -1.75, 0.05), (-3.0, -1.62, 0.22), (0.0, -1.55, 0.34), (3.0, -1.62, 0.22), (4.75, -1.75, 0.05)],
                  paint, lambda t: 0.95 - 0.15 * math.sin(math.pi * t), lambda t: 0.50, r=0.10, flange=(0.10, 0.04), n=14)
    hb = bmesh.new()
    for x in (-2.9, -0.9, 0.9, 2.9):
        z = 0.34 - 0.12 * (abs(x) / 3.0) ** 2
        C.cyl_bm(hb, 0.15 if abs(x) < 2 else 0.12, z - 0.1, z + 0.6, seg=32,
                 matrix=Matrix.Translation((x, -1.58, 0)) @ Matrix.Diagonal((1.0, 0.7, 1, 1)))
    holes = C.mesh_obj("RearHoles", hb, [paint])
    boolean(rear, holes)
    C.add_bevel(rear, 0.015, segments=2, angle=35)
    out.append(C.finalize(rear, angle=35, remove=[holes]))
    # side members (mirrored pair), rising toward the front towers
    for s in (-1, 1):
        sm = member("Side", [(s * 4.45, -1.95, 0.05), (s * 4.30, -0.8, 0.08), (s * 4.0, 0.6, 0.18), (s * 3.75, 1.9, 0.32), (s * 3.70, 2.55, 0.40)],
                    paint, lambda t: 0.62 - 0.18 * t, lambda t: 0.52 - 0.12 * t, r=0.09, flange=(0.07, 0.035), n=12)
        hb = bmesh.new()
        for y in (-0.2, 0.9):
            x = s * (4.22 - 0.25 * (y + 0.2))
            C.cyl_bm(hb, 0.10, -0.5, 0.5, seg=28, matrix=axis_mat((x, y, 0.14 + 0.08 * (y + 0.2)), (1, 0, 0)) @ Matrix.Diagonal((0.8, 1.4, 1, 1)))
        holes = C.mesh_obj("SideHoles", hb, [paint])
        boolean(sm, holes)
        C.add_bevel(sm, 0.015, segments=2, angle=35)
        out.append(C.finalize(sm, angle=35, remove=[holes]))
    # light front crossmember
    fx = member("FrontX", [(-3.72, 2.42, 0.40), (0.0, 2.50, 0.48), (3.72, 2.42, 0.40)], paint,
                lambda t: 0.36, lambda t: 0.30, r=0.08, n=10)
    C.add_bevel(fx, 0.012, segments=2, angle=35)
    out.append(C.finalize(fx, angle=35))
    return out


def mounts(paint, rubber, steel):
    out = []
    for s in (-1, 1):
        # rear body mounts: bushed sleeves welded at the rear corners
        out += bushing(paint, rubber, steel, Vector((s * 4.92, -1.95, 0.08)), 0.36, 0.62)
        # front towers
        P = [(0.0, 0.0, 0), (0.27, 0.0, 0), (0.27, 0.62, 0), (0.25, 0.66, 0), (0.12, 0.68, 0), (0.0, 0.68, 0)]
        ob = C.lathe("Tower", P, [paint], steps=64)
        ob.matrix_world = Matrix.Translation((s * 3.78, 2.62, 0.30))
        out.append(C.finalize(ob, angle=35))
        P = [(0.075, 0.30, 0), (0.12, 0.30, 0), (0.12, 0.76, 0), (0.075, 0.76, 0)]
        ob = C.lathe("TowerSleeve", P, [steel], steps=40)
        ob.matrix_world = Matrix.Translation((s * 3.78, 2.62, 0.30))
        out.append(C.finalize(ob, angle=40))
    return out


def brackets(paint):
    out = []
    bm = bmesh.new()
    hb = bmesh.new()
    for s in (-1, 1):
        # front control-arm clevis: two plates across Y, bolt along Y
        for y in (0.62, 1.12):
            C.box_bm(bm, 0.78, 0.07, 0.62, center=(s * 4.42, y, 0.10))
        C.cyl_bm(hb, 0.075, -0.6, 0.6, seg=28, matrix=axis_mat((s * 4.62, 0.87, 0.02), (0, 1, 0)))
        # rear control-arm bracket: top/bottom plates, vertical bolt
        for z in (-0.20, 0.28):
            C.box_bm(bm, 0.80, 0.72, 0.07, center=(s * 4.78, -1.05, z))
        C.box_bm(bm, 0.07, 0.72, 0.55, center=(s * 4.42, -1.05, 0.04))
        C.cyl_bm(hb, 0.08, -0.6, 0.6, seg=28, matrix=Matrix.Translation((s * 4.92, -1.05, 0.0)))
        # steering rack pads with two bolt holes each
        C.box_bm(bm, 0.75, 0.55, 0.10, center=(s * 1.85, -1.45, 0.52))
        for dx in (-0.22, 0.22):
            C.cyl_bm(hb, 0.05, 0.3, 0.8, seg=20, matrix=Matrix.Translation((s * 1.85 + dx, -1.45, 0)))
        # anti-roll bar clamp seat on the side member
        C.box_bm(bm, 0.45, 0.42, 0.08, center=(s * 4.10, 0.15, 0.48))
    # rear engine-mount clevis at the centre, pointing back
    for x in (-0.24, 0.24):
        C.box_bm(bm, 0.07, 0.80, 0.55, center=(x, -2.20, 0.25))
    C.box_bm(bm, 0.55, 0.30, 0.07, center=(0, -1.98, 0.02))
    C.cyl_bm(hb, 0.085, -0.6, 0.6, seg=28, matrix=axis_mat((0, -2.38, 0.30), (1, 0, 0)))
    ob = C.mesh_obj("Brackets", bm, [paint])
    holes = C.mesh_obj("BracketHoles", hb, [paint])
    boolean(ob, holes)
    C.add_bevel(ob, 0.018, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[holes]))
    return out


def build():
    paint = mat_worn_black("Ecoat")
    rubber = C.mat_rubber("MountRubber")
    steel = C.principled("ZincSleeve", (0.55, 0.55, 0.53), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    objs = frame(paint) + mounts(paint, rubber, steel) + brackets(paint)
    C.transform_all(objs, Matrix.Rotation(math.radians(-22), 4, "Z"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("culla", objs, "culla.py",
            "front subframe / engine cradle: black e-coated pressed-steel welded frame with crossmembers, body mount bushes, control arm brackets and steering rack pads",
            az=30, el=38, lens=70, fill=0.90,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
