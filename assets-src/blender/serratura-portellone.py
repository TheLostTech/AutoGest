"""Tailgate lock / latch, generic small hatchback: wide black phosphated steel latch plate
with two bolting ears and the striker slot opening downwards, the rotary claw in the
slot; behind it the black plastic latch body and the central-locking actuator housing
with its motor bulge, moulded ribs and lid seam, the electrical connector shroud with
pins on top, and the zinc release lever with a white nylon rod clip on the side.
The plate faces -Y, the striker comes from below (-Z)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
RX = Matrix.Rotation(math.radians(90), 4, "X")      # cylinder Z -> -Y
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # cylinder Z -> X


def bool_cut(ob, cut):
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def mat_black_steel(name="BlackPhosphate"):
    base = 0.035
    m = C.principled(name, (base, base, base * 1.05), metallic=0.75, rough=0.48)
    nt = m.node_tree
    b = P.bsdf(m)
    C.add_noise_bump(m, scale=420, strength=0.10, distance=0.0004, rough_var=0.06)
    em = C.edge_mask(nt, 0.0012, 2.5)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 140.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "MULTIPLY"
    f.use_clamp = True
    nt.links.new(em, f.inputs[0])
    nt.links.new(mr.outputs["Result"], f.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(f.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.05, 1)
    mix.inputs["B"].default_value = (0.36, 0.36, 0.37, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def rnd(pts, r, seg=8):
    q = P.rounded([Vector(p) for p in pts], r if isinstance(r, list) else [r] * len(pts), closed=True, seg=seg)
    return [(p.x, p.y) for p in q]


def extrude(name, poly, y0, y1, mat, cutters=(), bevel=0.0005):
    bm = bmesh.new()
    a = [bm.verts.new((p[0] * MM, y0 * MM, p[1] * MM)) for p in poly]
    b = [bm.verts.new((p[0] * MM, y1 * MM, p[1] * MM)) for p in poly]
    n = len(poly)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    cut = None
    if cutters:
        cb = bmesh.new()
        for f in cutters:
            f(cb)
        cut = C.mesh_obj(name + "Cut", cb, [mat])
        bool_cut(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=3, angle=30)
    return C.finalize(ob, angle=35, remove=[cut] if cut else [])


def hole(x, z, r):
    return lambda cb: C.cyl_bm(cb, r * MM, -0.08, 0.08, seg=36, matrix=Matrix.Translation((x * MM, 0, z * MM)) @ RX)


SLOT_W, SLOT_TOP = 16.0, 4.0


def slot(cb):
    C.box_bm(cb, SLOT_W * MM, 0.1, 40 * MM, center=(0, 0, (SLOT_TOP - 20) * MM))
    C.cyl_bm(cb, SLOT_W / 2 * MM, -0.05, 0.05, seg=40, matrix=Matrix.Translation((0, 0, SLOT_TOP * MM)) @ RX)
    for s in (-1, 1):
        C.box_bm(cb, 9 * MM, 0.1, 9 * MM, center=(0, 0, 0),
                 matrix=Matrix.Translation((s * SLOT_W / 2 * MM, 0, -23 * MM)) @ Matrix.Rotation(math.radians(45), 4, "Y"))


def plate(steel, dark):
    out = []
    poly = rnd([(-52, -23), (52, -23), (52, 9), (30, 20), (-30, 20), (-52, 9)], [7, 7, 8, 10, 10, 8])
    out.append(extrude("Plate", poly, 0, 3.0, steel, cutters=[slot, hole(-42, -8, 4.3), hole(42, -8, 4.3)], bevel=0.0009))
    for x in (-42, 42):   # pressed collars round the threaded holes
        col = C.lathe("Collar", [(4.3 * MM, 0.0, 0), (7.4 * MM, 0.0, 0), (6.6 * MM, 1.2 * MM, 0), (4.6 * MM, 1.4 * MM, 0),
                                 (4.3 * MM, 0.7 * MM, 0)], [steel], steps=40)
        col.matrix_world = Matrix.Translation((x * MM, 0, -8 * MM)) @ RX
        out.append(C.finalize(col, angle=40))
        thr = C.lathe("Thread", [(3.6 * MM, 0.0, 0), (4.35 * MM, 0.0, 0), (4.35 * MM, 3.0 * MM, 0), (3.6 * MM, 3.0 * MM, 0)], [dark],
                      steps=24, mod=lambda r, zz, t: r - 0.0004 * (0.5 + 0.5 * math.sin(zz * 2 * math.pi / 0.0009 + t)))
        thr.matrix_world = Matrix.Translation((x * MM, 0, -8 * MM)) @ Matrix.Rotation(math.radians(-90), 4, "X")
        out.append(C.finalize(thr, angle=60))
    return out


def claw(plastic, steel):
    out = []
    pc = Vector((16, -3))
    poly = [(pc.x + 15 * math.cos(math.tau * k / 64), pc.y + 15 * math.sin(math.tau * k / 64)) for k in range(64)]

    def fork(cb):
        C.box_bm(cb, 13.5 * MM, 0.1, 30 * MM, center=(0, 0, 0),
                 matrix=Matrix.Translation((-1 * MM, 0, -14 * MM)) @ Matrix.Rotation(math.radians(20), 4, "Y"))
    out.append(extrude("Claw", poly, 4.0, 12.0, plastic, cutters=[fork, hole(pc.x, pc.y, 2.8)], bevel=0.0007))
    pin = C.lathe("ClawRivet", [(0.0, 0.0, 0), (4.6 * MM, 0.0, 0), (4.0 * MM, 1.3 * MM, 0), (0.0, 1.7 * MM, 0)], [steel], steps=32)
    pin.matrix_world = Matrix.Translation((pc.x * MM, 0.0, pc.y * MM)) @ RX
    out.append(C.finalize(pin, angle=40))
    return out


def housing(plastic, dark):
    out = []
    bm = bmesh.new()
    P.superellipsoid(bm, 0.046, 0.017, 0.022, e1=0.15, e2=0.15, matrix=Matrix.Translation((0.0, 0.020, -0.001)))  # latch body
    P.superellipsoid(bm, 0.034, 0.028, 0.021, e1=0.2, e2=0.2, matrix=Matrix.Translation((0.010, 0.045, 0.030)))  # actuator
    C.cyl_bm(bm, 0.0125, -0.032, 0.026, seg=48, matrix=Matrix.Translation((0.010, 0.060, 0.051)) @ RY)              # motor can
    C.cyl_bm(bm, 0.0135, -0.034, -0.030, seg=48, matrix=Matrix.Translation((0.010, 0.060, 0.051)) @ RY)             # can end cap
    for x in (-0.014, -0.004, 0.006, 0.016, 0.026):                                                                  # ribs
        C.box_bm(bm, 0.0024, 0.004, 0.026, center=(x, 0.0175, 0.033))
    ob = C.mesh_obj("Housing", bm, [plastic])
    cb = bmesh.new()
    slot(cb)
    C.box_bm(cb, SLOT_W * MM, 0.024, 0.040, center=(0, 0.012, -0.016))
    cut = C.mesh_obj("HousingSlot", cb, [dark])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0012, segments=2, angle=30)
    out.append(C.finalize(ob, angle=40, remove=[cut]))
    return out


def connector(plastic, pins_m, dark):
    out = []
    cx, cy, cz = 0.026, 0.032, 0.044
    bm = bmesh.new()
    C.box_bm(bm, 0.026, 0.017, 0.018, center=(cx, cy, cz + 0.008))
    ob = C.mesh_obj("Shroud", bm, [plastic])
    cb = bmesh.new()
    C.box_bm(cb, 0.021, 0.012, 0.02, center=(cx, cy, cz + 0.015))
    cut = C.mesh_obj("ShroudCut", cb, [dark])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.0008, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    bm = bmesh.new()
    C.box_bm(bm, 0.008, 0.0035, 0.003, center=(cx, cy - 0.0095, cz + 0.014))   # locking ramp
    rp = C.mesh_obj("Ramp", bm, [plastic])
    C.add_bevel(rp, 0.0006, segments=1, angle=30)
    out.append(C.finalize(rp, angle=35))
    bm = bmesh.new()
    for k in range(5):
        C.box_bm(bm, 0.0012, 0.0024, 0.010, center=(cx - 0.008 + 0.004 * k, cy, cz + 0.008))
    out.append(C.finalize(C.mesh_obj("Pins", bm, [pins_m]), angle=35))
    return out


def lever(zinc, nylon):
    out = []
    poly = rnd([(0, -4), (34, -6), (36, 4), (0, 6)], [3, 4, 4, 3])
    ob = extrude("Lever", poly, -1.2, 1.2, zinc, cutters=[hole(4, 1, 2.0), hole(30, -1, 2.4)])
    ob.matrix_world = Matrix.Translation((0.046, 0.032, 0.006)) @ Matrix.Rotation(math.radians(90), 4, "Z") \
        @ Matrix.Rotation(math.radians(-15), 4, "Y")
    out.append(ob)
    # rod clip at the lever end (white nylon), stub of the steel rod
    M = ob.matrix_world @ Matrix.Translation((30 * MM, 0, -1 * MM))
    clip = C.lathe("RodClip", [(0.0, -4.5 * MM, 0), (4.4 * MM, -4.5 * MM, 0), (4.8 * MM, -2.5 * MM, 0), (4.8 * MM, 2.5 * MM, 0),
                               (4.4 * MM, 4.5 * MM, 0), (0.0, 4.5 * MM, 0)], [nylon], steps=36)
    clip.matrix_world = M @ RX
    C.add_bevel(clip, 0.0004, segments=1, angle=30)
    out.append(C.finalize(clip, angle=40))
    p0 = M @ Vector((0, 0, 0))
    pts = [p0 + Vector((0.002, 0.0, 0.0)) * 0 + Vector((0.0, 0.0, 1.0)) * (0.040 * k / 20) + Vector((0.0, 0.006, 0)) for k in range(21)]
    fr = P.path_frames(pts, (1, 0, 0))
    out.append(P.tube_obj("Rod", fr, P.circle(2.0 * MM, 14), [zinc], smooth_angle=60))
    return out


def build():
    steel = mat_black_steel()
    plastic = C.mat_black_plastic("HousingPA", rough=0.5, color=0.028)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.7)
    zinc = C.principled("ZincSteel", (0.68, 0.68, 0.70), metallic=1.0, rough=0.28)
    C.add_noise_bump(zinc, scale=500, strength=0.05, distance=0.0003, rough_var=0.05)
    tin = C.principled("TinPins", (0.80, 0.78, 0.72), metallic=1.0, rough=0.25)
    nylon = C.principled("Nylon", (0.84, 0.82, 0.76), rough=0.5, Subsurface_Weight=0.15)
    objs = plate(steel, dark)
    objs += claw(plastic, zinc)
    objs += housing(plastic, dark)
    objs += connector(plastic, tin, dark)
    objs += lever(zinc, nylon)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("serratura-portellone", objs, "serratura-portellone.py",
            "tailgate lock latch (generic small hatchback): black steel latch plate with downward striker slot and "
            "claw, black plastic actuator housing with motor bulge and connector, zinc release lever with rod clip",
            az=30, el=26, lens=70, fill=0.84, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
