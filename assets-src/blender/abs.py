"""ABS hydraulic unit with integrated ECU (centralina ABS / gruppo idraulico), as removed
from a small car: machined aluminium valve block with six brake-line ports on top (three
with zinc tube nuts and cut-off copper-nickel brake pipe stubs, three open threaded
ports), sealing plugs on the faces, return-pump motor can on one side, black plastic
ECU housing on the other with a large multi-pin connector socket and a blank label."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

BX, BY, BZ = 1.20, 0.78, 0.92        # valve block (1 unit ~ 10 cm)
EY = 0.42                            # ECU depth


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def cyl_axis(bm, r, origin, axis, l0, l1, seg=32, r1=None, mat=0):
    C.cyl_bm(bm, r, l0, l1, seg=seg, matrix=axis_mat(origin, axis), r1=r1, mat=mat)


def lathe_at(name, prof, mats, origin, axis, steps=48):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


# top ports: (x, y, radius, fitted?)
PORTS = [(-0.36, -0.16, 0.058, True), (-0.36, 0.17, 0.058, False),
         (0.02, -0.20, 0.05, True), (0.02, 0.12, 0.05, False),
         (0.33, -0.20, 0.05, True), (0.33, 0.12, 0.05, False)]


def block(alu):
    bm = bmesh.new()
    C.box_bm(bm, BX, BY, BZ, center=(0, 0, 0))
    ob = C.mesh_obj("Block", bm, [alu])
    cb = bmesh.new()
    top = BZ / 2
    for (x, y, r, _f) in PORTS:
        cyl_axis(cb, r, (x, y, top), (0, 0, 1), -0.40, 0.05, seg=40)
        cyl_axis(cb, r + 0.022, (x, y, top), (0, 0, 1), -0.022, 0.002, seg=40, r1=r + 0.001)
        # spot-face around each port
        cyl_axis(cb, r + 0.03, (x, y, top), (0, 0, 1), -0.006, 0.05, seg=48)
    # pressed sealing balls / plugs on the front face (-Y) and the side (+X)
    for (x, z) in ((-0.48, 0.30), (-0.48, -0.05), (0.47, 0.32), (0.47, -0.30), (-0.20, -0.36), (0.20, -0.36)):
        cyl_axis(cb, 0.032, (x, -BY / 2, z), (0, -1, 0), -0.02, 0.05, seg=24)
    for (y, z) in ((-0.18, 0.25), (0.15, -0.22), (-0.2, -0.25)):
        cyl_axis(cb, 0.03, (BX / 2, y, z), (1, 0, 0), -0.02, 0.05, seg=24)
    # three mounting stud holes underneath
    for (x, y) in ((-0.40, 0.0), (0.40, 0.18), (0.40, -0.18)):
        cyl_axis(cb, 0.06, (x, y, -BZ / 2), (0, 0, 1), -0.05, 0.12, seg=32)
    cut = C.mesh_obj("BlockCut", cb, [alu])
    bo = C.add_boolean(ob, cut)
    bo.use_self = True
    bo.use_hole_tolerant = True
    C.add_bevel(ob, 0.012, segments=4, angle=30)
    ob = C.finalize(ob, angle=20, remove=[cut])
    for p in ob.data.polygons:      # flat faces: avoids shading gradients across the triangulated sides
        p.use_smooth = p.area < 0.002
    return ob


def plugs(steel):
    bm = bmesh.new()
    for (x, z) in ((-0.48, 0.30), (-0.48, -0.05), (0.47, 0.32), (0.47, -0.30), (-0.20, -0.36), (0.20, -0.36)):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.027,
                                  matrix=Matrix.Translation((x, -BY / 2 + 0.012, z)))
    for (y, z) in ((-0.18, 0.25), (0.15, -0.22), (-0.2, -0.25)):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.025,
                                  matrix=Matrix.Translation((BX / 2 - 0.012, y, z)))
    for f in bm.faces:
        f.smooth = True
    ob = C.mesh_obj("Plugs", bm, [steel])
    return ob


def fittings(zinc, pipe):
    out = []
    top = BZ / 2
    bends = {0: (-1.0, -0.5), 2: (0.0, -1.0), 4: (0.6, -1.0)}
    for i, (x, y, r, fitted) in enumerate(PORTS):
        if not fitted:
            continue
        bm = bmesh.new()
        cyl_axis(bm, r + 0.02, (x, y, top), (0, 0, 1), -0.01, 0.075, seg=6)
        hx = C.mesh_obj("TubeNut", bm, [zinc])
        C.add_bevel(hx, 0.008, segments=2, angle=30)
        out.append(C.finalize(hx, angle=35))
        P = [(0.0, 0.07, 0), (0.042, 0.07, 0), (0.036, 0.11, 0), (0.0, 0.11, 0)]
        out.append(C.finalize(lathe_at("NutNeck", P, [zinc], (x, y, top), (0, 0, 1)), angle=40))
        # cut-off brake pipe: up, bend, run sideways
        dx, dy = bends[i]
        d = Vector((dx, dy, 0)).normalized()
        R = 0.13
        pts = [Vector((x, y, top + 0.06)), Vector((x, y, top + 0.12))]
        c0 = Vector((x, y, top + 0.12))
        for k in range(1, 13):
            a = math.pi / 2 * k / 12
            pts.append(c0 + d * R * (1 - math.cos(a)) + Vector((0, 0, R * math.sin(a))))
        pts.append(pts[-1] + d * (0.22 + 0.08 * i))
        cu = bpy.data.curves.new("Pipe", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.024
        cu.bevel_resolution = 5
        cu.use_fill_caps = True
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (c.x, c.y, c.z, 1)
        ob = C.link(bpy.data.objects.new("Pipe", cu))
        cu.materials.append(pipe)
        out.append(C.finalize(ob, angle=50))
    return out


def motor(zinc, black):
    out = []
    o = (0.05, -BY / 2, -0.02)
    ax = (0, -1, 0)
    P = [(0.0, 0.0, 0), (0.40, 0.0, 0), (0.40, 0.035, 0), (0.33, 0.04, 0), (0.33, 0.06, 0), (0.335, 0.075, 0),
         (0.335, 0.37, 0), (0.325, 0.385, 0), (0.335, 0.40, 0), (0.335, 0.47, 0), (0.30, 0.50, 0),
         (0.16, 0.515, 0), (0.0, 0.515, 0)]
    out.append(C.finalize(lathe_at("MotorCan", P, [zinc], o, ax, steps=96), angle=35))
    # black end bearing cap
    P = [(0.0, 0.51, 0), (0.12, 0.51, 0), (0.115, 0.56, 0), (0.09, 0.575, 0), (0.0, 0.575, 0)]
    out.append(C.finalize(lathe_at("EndCap", P, [black], o, ax), angle=40))
    # flange screws
    bm = bmesh.new()
    for a in (math.radians(30), math.radians(210)):
        p = Vector(o) + Vector((0.37 * math.cos(a), 0, 0.37 * math.sin(a)))
        cyl_axis(bm, 0.032, p, ax, 0.03, 0.06, seg=24)
    sc = C.mesh_obj("FlangeScrews", bm, [zinc])
    C.add_bevel(sc, 0.008, segments=2, angle=30)
    out.append(C.finalize(sc, angle=35))
    return out


def ecu(black, steel, pinm):
    out = []
    y0 = BY / 2
    ex, ez = BX + 0.08, BZ + 0.10
    bm = bmesh.new()
    C.box_bm(bm, ex, EY * 0.45, ez, center=(0, y0 + EY * 0.225, 0))           # base frame
    C.box_bm(bm, ex - 0.06, EY * 0.6, ez - 0.06, center=(0, y0 + EY * 0.7, 0))  # cover
    hs = C.mesh_obj("ECU", bm, [black])
    C.add_bevel(hs, 0.016, segments=3, angle=30)
    out.append(C.finalize(hs, angle=35))
    # stiffening ribs on the cover
    bm = bmesh.new()
    for k in range(5):
        z = -0.32 + k * 0.16
        C.box_bm(bm, ex - 0.20, 0.03, 0.025, center=(0, y0 + EY + 0.01, z))
    rb = C.mesh_obj("Ribs", bm, [black])
    C.add_bevel(rb, 0.006, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    # screws holding the ECU to the block (on the frame flange, visible from the top)
    bm = bmesh.new()
    for x in (-ex / 2 + 0.06, ex / 2 - 0.06):
        for z in (ez / 2 - 0.0, -ez / 2 + 0.0):
            pass
    for (x, z) in ((-0.55, 0.47), (0.55, 0.47)):
        cyl_axis(bm, 0.035, (x, y0 + 0.08, z + 0.01), (0, 0, 1), 0.0, 0.03, seg=24)
    sc = C.mesh_obj("EcuScrews", bm, [steel])
    C.add_bevel(sc, 0.008, segments=2, angle=30)
    out.append(C.finalize(sc, angle=35))
    # big connector socket on the +X end, opening facing +X
    cx = ex / 2
    cy, cz = y0 + EY * 0.48, -0.02
    sw, sh, sd = 0.30, 0.78, 0.17
    bm = bmesh.new()
    C.box_bm(bm, sd, sw, sh, center=(cx + sd / 2 - 0.02, cy, cz))
    sk = C.mesh_obj("Socket", bm, [black])
    cb = bmesh.new()
    C.box_bm(cb, sd, sw - 0.05, sh - 0.05, center=(cx + sd / 2 + 0.03, cy, cz))
    cut = C.mesh_obj("SocketCut", cb, [black])
    C.add_boolean(sk, cut)
    C.add_bevel(sk, 0.008, segments=2, angle=30)
    out.append(C.finalize(sk, angle=35, remove=[cut]))
    # latch ramp + polarisation key
    bm = bmesh.new()
    C.box_bm(bm, 0.06, 0.08, 0.12, center=(cx + 0.06, cy - sw / 2 - 0.03, cz + 0.20))
    C.box_bm(bm, 0.06, 0.08, 0.12, center=(cx + 0.06, cy - sw / 2 - 0.03, cz - 0.20))
    lt = C.mesh_obj("Latch", bm, [black])
    C.add_bevel(lt, 0.01, segments=2, angle=30)
    out.append(C.finalize(lt, angle=35))
    # pin field: two big power pins + grid of signal pins
    bm = bmesh.new()
    for col in range(3):
        for row in range(11):
            y = cy - 0.08 + col * 0.08
            z = cz - 0.25 + row * 0.042
            C.box_bm(bm, 0.11, 0.014, 0.014, center=(cx + 0.03, y, z))
    for z in (cz + 0.27, cz + 0.20):
        C.box_bm(bm, 0.11, 0.07, 0.016, center=(cx + 0.03, cy, z))
    pn = C.mesh_obj("Pins", bm, [pinm])
    out.append(pn)
    # blank label on top of the cover
    im = C.label_image("AbsLabel", 1024, 512, seed=21, lines=4)
    lab = C.label_plane("Label", C.mat_label(im), 0.62, 0.26,
                        Matrix.Translation((-0.18, y0 + EY * 0.70, ez / 2 - 0.0285)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
    out.append(lab)
    return out


def build():
    alu = C.principled("BlockAlu", (0.42, 0.42, 0.41), metallic=1.0, rough=0.50)
    C.add_noise_bump(alu, scale=600, strength=0.05, distance=0.0005, rough_var=0.08)
    nt = alu.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # fine milling marks across the faces
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "RINGS"
    wv.inputs["Scale"].default_value = 90.0
    wv.inputs["Distortion"].default_value = 1.5
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.04
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    zinc = C.principled("ZincYellow", (0.66, 0.60, 0.44), metallic=1.0, rough=0.28)
    C.add_noise_bump(zinc, scale=800, strength=0.05, distance=0.0005, rough_var=0.06)
    can = C.principled("MotorZinc", (0.50, 0.51, 0.52), metallic=1.0, rough=0.36)
    C.add_noise_bump(can, scale=700, strength=0.04, distance=0.0005, rough_var=0.06)
    pipe = C.principled("CuNiPipe", (0.72, 0.52, 0.36), metallic=1.0, rough=0.32)
    C.add_noise_bump(pipe, scale=500, strength=0.08, distance=0.0006, rough_var=0.08)
    black = C.mat_black_plastic("EcuPA", rough=0.5, color=0.03)
    pinm = C.principled("PinTin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.25)
    objs = [block(alu), plugs(can)] + fittings(zinc, pipe) + motor(can, black) + ecu(black, can, pinm)
    C.transform_all(objs, Matrix.Rotation(math.radians(-20), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("abs", objs, "abs.py",
            "ABS hydraulic unit with ECU: machined aluminium valve block with brake-line ports and fittings, pump motor, black control module with large connector",
            az=35, el=30, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
