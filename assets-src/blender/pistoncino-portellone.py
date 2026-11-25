"""Tailgate gas strut (gas spring), generic small hatchback: semi-gloss black steel
pressure cylinder with a rolled seal end and a faint white printed band, polished chrome
piston rod, zinc-plated end pieces and black plastic ball-socket ends, each with its
spring-steel safety clip. Laid diagonally on the floor.
Built along +Z (cylinder end at z = 0), then laid down."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
RC = 10.5 * MM       # cylinder radius
LC = 250 * MM        # cylinder length
RR = 4.0 * MM        # rod radius
LR = 205 * MM        # exposed rod


def cylinder(paint):
    prof = [(0.0, -6 * MM, 0), (6.5 * MM, -6 * MM, 0), (8.5 * MM, -4.5 * MM, 0), (RC - 0.4 * MM, -0.8 * MM, 0),
            (RC, 0.0, 0), (RC, LC - 9 * MM, 0),
            (RC - 0.9 * MM, LC - 7.5 * MM, 0), (RC - 0.9 * MM, LC - 6.0 * MM, 0), (RC, LC - 4.5 * MM, 0),  # crimp groove
            (RC, LC - 1.5 * MM, 0), (RC - 1.0 * MM, LC, 0), (RR + 1.4 * MM, LC + 0.6 * MM, 0), (RR + 1.4 * MM, LC + 1.6 * MM, 0),
            (0.0, LC + 1.6 * MM, 0)]
    ob = C.lathe("Cylinder", prof, [paint], steps=96)
    C.add_bevel(ob, 0.0003, segments=2, angle=30)
    return C.finalize(ob, angle=40)


def rod(chrome, zinc):
    out = []
    r = C.lathe("Rod", [(0.0, LC, 0), (RR, LC, 0), (RR, LC + LR, 0), (0.0, LC + LR, 0)], [chrome], steps=64)
    out.append(C.finalize(r, angle=40))
    # end piece on the rod and on the cylinder base (zinc), with threaded studs into the sockets
    for (z0, sgn) in ((LC + LR, 1), (-6 * MM, -1)):
        prof = [(0.0, 0.0, 0), (6.2 * MM, 0.0, 0), (6.2 * MM, 7 * MM, 0), (5.2 * MM, 8.2 * MM, 0), (0.0, 8.2 * MM, 0)]
        e = C.lathe("EndPiece", prof, [zinc], steps=48)
        M = Matrix.Translation((0, 0, z0))
        if sgn < 0:
            M = M @ Matrix.Rotation(math.pi, 4, "X")
        e.matrix_world = M
        C.add_bevel(e, 0.0003, segments=2, angle=30)
        out.append(C.finalize(e, angle=40))
    return out


def socket(plastic, wire_m, z0, sgn):
    """Ball socket: shank on the strut axis, head with the cup opening along X."""
    out = []
    M = Matrix.Translation((0, 0, z0))
    if sgn < 0:
        M = M @ Matrix.Rotation(math.pi, 4, "X")
    hz = 25 * MM                                   # head centre along the axis
    bm = bmesh.new()
    C.cyl_bm(bm, 7.8 * MM, 0.0, hz, seg=48)
    P.superellipsoid(bm, 10.5 * MM, 9.0 * MM, 10.0 * MM, e1=0.7, e2=0.75, nu=64, nv=32,
                     matrix=Matrix.Translation((0, 0, hz)))
    ob = C.mesh_obj("Socket", bm, [plastic])
    cb = bmesh.new()
    C.cyl_bm(cb, 6.6 * MM, -0.03, 0.03, seg=48, matrix=Matrix.Translation((0, 0, hz)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    # slot for the clip, across the top of the head
    C.box_bm(cb, 0.03, 1.8 * MM, 3.0 * MM, center=(0, 0, hz + 9.6 * MM))
    cut = C.mesh_obj("SocketCut", cb, [plastic])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(ob, 0.0005, segments=2, angle=35)
    ob.matrix_world = M
    cut.matrix_world = M
    out.append(C.finalize(ob, angle=45, remove=[cut]))
    # dark ball seat inside the cup
    seat = C.lathe("Seat", [(0.0, -4 * MM, 0), (6.7 * MM, -4 * MM, 0), (6.7 * MM, 4 * MM, 0), (0.0, 4 * MM, 0)], [plastic], steps=48)
    seat.matrix_world = M @ Matrix.Translation((0, 0, hz)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    out.append(C.finalize(seat, angle=40))
    # spring clip: wire loop over the head through the slot, legs down both sides
    pts = []
    N = 60
    for k in range(N + 1):
        a = -math.radians(115) + math.radians(230) * k / N
        pts.append(Vector((10.9 * MM * math.sin(a), 0.0, hz + 10.2 * MM * math.cos(a))))
    pts = [M @ p for p in pts]
    fr = P.path_frames(pts, lambda p: (M.to_3x3() @ Vector((0, 1, 0))))
    out.append(P.tube_obj("Clip", fr, P.circle(0.75 * MM, 12), [wire_m], smooth_angle=70))
    return out


def print_band(ink_alpha_mat):
    """Thin sleeve with UVs on the cylinder carrying the printed text bars."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    n, z0, z1 = 96, 70 * MM, 175 * MM
    r = RC + 0.03 * MM
    rows = []
    for z in (z0, z1):
        rows.append([bm.verts.new((r * math.cos(math.tau * k / n), r * math.sin(math.tau * k / n), z)) for k in range(n + 1)])
    for k in range(n):
        f = bm.faces.new((rows[0][k], rows[0][k + 1], rows[1][k + 1], rows[1][k]))
        for l, (u, v) in zip(f.loops, ((k / n, 0), ((k + 1) / n, 0), ((k + 1) / n, 1), (k / n, 1))):
            l[uv].uv = (u, v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    ob = C.mesh_obj("Print", bm, [ink_alpha_mat])
    return ob


def print_material():
    import numpy as np, random
    w, h = 256, 1024
    img = np.zeros((h, w, 4), dtype=np.float32)
    rnd = random.Random(7)
    # two printed lines running along the cylinder (v), near u = 0.30
    for (u0, lw) in ((150, 9), (166, 7)):
        y = 40
        while y < h - 40:
            L = rnd.choice((18, 24, 30, 42, 12))
            img[y:y + L, u0:u0 + lw, :] = (0.92, 0.92, 0.90, 1.0)
            y += L + rnd.choice((8, 10, 22))
    im = bpy.data.images.new("StrutPrint", w, h, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.pack()
    m = bpy.data.materials.new("PrintInk")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["UV"], tx.inputs["Vector"])
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.75, 0.75, 0.72, 1)
    b.inputs["Roughness"].default_value = 0.5
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tx.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build():
    paint = C.mat_paint("StrutBlack", (0.018, 0.018, 0.02), rough=0.32, coat=0.4)
    C.add_noise_bump(paint, scale=700, strength=0.04, distance=0.0002, rough_var=0.04)
    chrome = C.principled("RodChrome", (0.93, 0.93, 0.94), metallic=1.0, rough=0.035)
    zinc = C.principled("ZincEnd", (0.72, 0.72, 0.74), metallic=1.0, rough=0.28)
    C.add_noise_bump(zinc, scale=600, strength=0.05, distance=0.0002, rough_var=0.05)
    plastic = C.mat_black_plastic("SocketPOM", rough=0.42, color=0.02)
    wire_m = C.principled("ClipSteel", (0.62, 0.62, 0.64), metallic=1.0, rough=0.25)
    objs = [cylinder(paint)]
    objs += rod(chrome, zinc)
    objs += socket(plastic, wire_m, LC + LR + 8.2 * MM, 1)
    objs += socket(plastic, wire_m, -6 * MM - 8.2 * MM, -1)
    objs.append(print_band(print_material()))
    # lie it down along X (socket openings vertical), then turn it diagonal
    M = Matrix.Rotation(math.radians(77), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "Y")
    C.transform_all(objs, M)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("pistoncino-portellone", objs, "pistoncino-portellone.py",
            "tailgate gas strut (generic small hatchback): black pressure cylinder, chrome piston rod, "
            "black plastic ball-socket ends with metal safety clips",
            az=8, el=22, lens=70, fill=0.92, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
