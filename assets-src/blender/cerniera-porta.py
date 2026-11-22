"""Front door hinge, generic small hatchback: two forged steel leaves in black e-coat with
worn edges, joined by a zinc-plated hinge pin with a head on top and a retaining clip
underneath. The body-side leaf carries two knuckles and a flanged mounting face with two
slotted bolt holes; the door-side leaf is a forged arm on the middle knuckle that widens
into its own mounting plate with two bolt holes. Shown opened to about 130 degrees.
Pin axis along Z at the origin; units are metres."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
RY = Matrix.Rotation(math.radians(90), 4, "Y")    # cylinder axis Z -> X
OPEN = 50.0                                      # door leaf direction (deg from +X)


def mat_ecoat_worn(name="EcoatSteel"):
    base = 0.028
    m = C.principled(name, (base, base, base * 1.06), metallic=0.1, rough=0.40)
    nt = m.node_tree
    b = P.bsdf(m)
    C.add_noise_bump(m, scale=380, strength=0.12, distance=0.0004, rough_var=0.06)
    em = C.edge_mask(nt, 0.0012, 2.2)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 160.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.65
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.06, 1)
    mix.inputs["B"].default_value = (0.42, 0.42, 0.43, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["To Min"].default_value = 0.1
    mm.inputs["To Max"].default_value = 1.0
    nt.links.new(f.outputs[0], mm.inputs["Value"])
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    return m


def box(bm, x0, x1, y0, y1, z0, z1):
    C.box_bm(bm, (x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM,
             center=((x0 + x1) / 2 * MM, (y0 + y1) / 2 * MM, (z0 + z1) / 2 * MM))


def prism_xz(bm, poly, y0, y1):
    a = [bm.verts.new((x * MM, y0 * MM, z * MM)) for x, z in poly]
    b = [bm.verts.new((x * MM, y1 * MM, z * MM)) for x, z in poly]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    bm.normal_update()


def forged(name, bm, holes, mat, M=None):
    """Pieces -> holes cut -> voxel-fused and smoothed like a forging."""
    ob = C.mesh_obj(name, bm, [mat])
    cb = bmesh.new()
    for (p, axis, r, slot) in holes:
        R = RY if axis == "X" else Matrix.Identity(4)
        for s in ((-slot / 2, slot / 2) if slot else (0.0,)):
            C.cyl_bm(cb, r * MM, -0.04, 0.04, seg=40,
                     matrix=Matrix.Translation(Vector(p) * MM + Vector((0, s * MM, 0))) @ R)
        if slot:
            C.box_bm(cb, 0.08, slot * MM, 2 * r * MM, center=Vector(p) * MM) if axis == "X" else None
    cut = C.mesh_obj(name + "Cut", cb, [mat])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    rm = ob.modifiers.new("Fuse", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.00045
    sm = ob.modifiers.new("Soft", "SMOOTH")
    sm.factor = 0.8
    sm.iterations = 6
    out = C.finalize(ob, angle=80, remove=[cut])
    if M is not None:
        out.matrix_world = M @ out.matrix_world
    return out


def body_leaf(mat):
    bm = bmesh.new()
    C.cyl_bm(bm, 11 * MM, 11.4 * MM, 30 * MM, seg=48)
    C.cyl_bm(bm, 11 * MM, -30 * MM, -11.4 * MM, seg=48)
    box(bm, -48, -12, -4, 4, -30, 30)                        # web
    box(bm, -14, 0, -4, 4, 11.4, 30)                         # web to the knuckles
    box(bm, -14, 0, -4, 4, -30, -11.4)
    box(bm, -54, -47, -4, 38, -33, 33)                       # mounting flange
    box(bm, -48, -30, 3, 9, -26, 26)                         # forging rib
    holes = [((-50, 21, 17), "X", 4.6, 4.0), ((-50, 21, -17), "X", 4.6, 4.0)]
    return forged("BodyLeaf", bm, holes, mat)


def door_leaf(mat):
    bm = bmesh.new()
    C.cyl_bm(bm, 11 * MM, -10.9 * MM, 10.9 * MM, seg=48)
    prism_xz(bm, [(4, -10.9), (24, -10.9), (46.5, -24), (46.5, 24), (24, 10.9), (4, 10.9)], -4.5, 4.5)   # tapered arm
    box(bm, 45, 52, -32, 4.5, -26, 26)                      # mounting plate
    holes = [((48, -18, 13), "X", 4.4, 0.0), ((48, -18, -13), "X", 4.4, 0.0)]
    return forged("DoorLeaf", bm, holes, mat, M=Matrix.Rotation(math.radians(OPEN), 4, "Z"))


def pin(zinc, clip_m):
    out = []
    p = C.lathe("Pin", [(0.0, -34.0 * MM, 0), (4.4 * MM, -34.0 * MM, 0), (4.8 * MM, -33.0 * MM, 0), (4.8 * MM, 31.0 * MM, 0),
                        (8.0 * MM, 31.0 * MM, 0), (8.2 * MM, 33.0 * MM, 0), (7.4 * MM, 35.0 * MM, 0), (0.0, 35.2 * MM, 0)],
                [zinc], steps=48)
    C.add_bevel(p, 0.0003, segments=2, angle=30)
    out.append(C.finalize(p, angle=40))
    # retaining clip under the bottom knuckle
    bm = bmesh.new()
    ring = C.lathe("Clip", [(4.6 * MM, -32.6 * MM, 0), (7.4 * MM, -32.6 * MM, 0), (7.4 * MM, -31.4 * MM, 0), (4.6 * MM, -31.4 * MM, 0)],
                   [clip_m], steps=48)
    out.append(C.finalize(ring, angle=40))
    # thin nylon washers in the knuckle gaps
    for z in (-11.15, 11.15):
        w = C.lathe("Washer", [(4.9 * MM, (z - 0.25) * MM, 0), (10.6 * MM, (z - 0.25) * MM, 0), (10.6 * MM, (z + 0.25) * MM, 0),
                               (4.9 * MM, (z + 0.25) * MM, 0)], [clip_m], steps=48)
        out.append(C.finalize(w, angle=40))
    return out


def build():
    ec = mat_ecoat_worn()
    zinc = C.principled("ZincPin", (0.72, 0.72, 0.74), metallic=1.0, rough=0.22)
    C.add_noise_bump(zinc, scale=600, strength=0.05, distance=0.0002, rough_var=0.05)
    clip_m = C.principled("SpringSteel", (0.06, 0.06, 0.065), metallic=0.9, rough=0.35)
    objs = [body_leaf(ec), door_leaf(ec)]
    objs += pin(zinc, clip_m)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("cerniera-porta", objs, "cerniera-porta.py",
            "door hinge (generic small hatchback): two forged steel leaves in black e-coat with bolt holes, "
            "joined by a zinc-plated hinge pin",
            az=24, el=24, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
