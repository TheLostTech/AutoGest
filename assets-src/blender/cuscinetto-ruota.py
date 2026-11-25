"""Wheel bearing kit (cuscinetto ruota) for a small car: sealed double-row angular
contact ball bearing (approx. 37 x 72 x 37 mm) with ground outer ring, split inner
ring (two halves, visible joint in the bore), recessed rubber lip seals with steel
inserts, plus the housing circlip that comes in the kit. Lathe profiles; circlip from
an extruded outline with boolean lug holes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

W = 0.37          # bearing width (1 unit ~ 10 cm)
RO, RI = 0.36, 0.185


def mats():
    ring = C.mat_machined("GroundSteel", color=0.42, rough=0.28, rings=900)
    face = C.mat_machined("FaceSteel", color=0.46, rough=0.30, rings=1400)
    seal = C.mat_rubber("SealRubber")
    b = next(n for n in seal.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Roughness", 0.55)
    lip = C.principled("SealInsert", (0.40, 0.40, 0.41), metallic=1.0, rough=0.35)
    clip = C.principled("SpringSteel", (0.07, 0.07, 0.075), metallic=1.0, rough=0.38)
    C.add_noise_bump(clip, scale=500, strength=0.08, distance=0.0005, rough_var=0.06)
    return ring, face, seal, lip, clip


def outer_ring(ring, face):
    c = 0.010
    P = [(0.300 + c, 0.0, 1), (RO - c, 0.0, 0), (RO, c, 0), (RO, W - c, 0), (RO - c, W, 1),
         (0.300 + c, W, 0), (0.300, W - c, 0), (0.300, c, 0)]
    ob = C.lathe("OuterRing", P, [ring, face], steps=160)
    return C.finalize(ob, angle=30)


def inner_rings(ring, face):
    out = []
    c = 0.008
    for z0, z1 in ((0.0, W / 2 - 0.001), (W / 2 + 0.001, W)):
        P = [(RI + c, z0, 1), (0.236 - c * 0.6, z0, 0), (0.236, z0 + c * 0.6, 0), (0.236, z1 - c * 0.6, 0),
             (0.236 - c * 0.6, z1, 1), (RI + c, z1, 0), (RI, z1 - c, 0), (RI, z0 + c, 0)]
        out.append(C.finalize(C.lathe("InnerRing", P, [ring, face], steps=144), angle=30))
    return out


def seal(seal_m, lip_m, top=True):
    out = []
    # rubber face with two moulded lip grooves, recessed ~1.2 mm below the ring faces
    P = [(0.301, 0.012, 0), (0.292, 0.012, 0), (0.289, 0.019, 0), (0.276, 0.019, 0), (0.272, 0.013, 0),
         (0.258, 0.013, 0), (0.254, 0.020, 0), (0.246, 0.020, 0), (0.246, 0.060, 0), (0.301, 0.060, 0)]
    if not top:
        P = [(r, W - z, m) for (r, z, m) in P][::-1]
    out.append(C.finalize(C.lathe("Seal", P, [seal_m], steps=144), angle=40))
    P = [(0.2375, 0.010, 0), (0.247, 0.010, 0), (0.247, 0.050, 0), (0.2375, 0.050, 0)]
    if not top:
        P = [(r, W - z, m) for (r, z, m) in P][::-1]
    out.append(C.finalize(C.lathe("SealLip", P, [lip_m], steps=144), angle=40))
    return out


def circlip(mat):
    """internal circlip lying flat: open ring with two drilled lugs at the gap"""
    r_in, r_out, t = 0.335, 0.375, 0.022
    gap = math.radians(26)
    n = 140
    pts_o, pts_i = [], []
    a0, a1 = gap / 2, math.tau - gap / 2
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        # ring narrows away from the lugs (tapered section like a real circlip)
        u = abs(math.cos((a - math.pi) / 2))  # 0 opposite the gap, 1 at the lugs
        ro = r_out
        ri = r_out - (0.024 + 0.016 * u)
        pts_o.append((ro * math.cos(a), ro * math.sin(a)))
        pts_i.append((ri * math.cos(a), ri * math.sin(a)))
    bm = bmesh.new()
    poly = pts_o + pts_i[::-1]
    vb = [bm.verts.new((x, y, 0)) for x, y in poly]
    vt = [bm.verts.new((x, y, t)) for x, y in poly]
    m = len(poly)
    bm.faces.new(vb[::-1])
    bm.faces.new(vt)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    # lugs: inward ears at both ends of the gap
    for s in (-1, 1):
        a = s * (gap / 2 + math.radians(5))
        cx, cy = 0.318 * math.cos(a), 0.318 * math.sin(a)
        C.cyl_bm(bm, 0.040, 0.0, t, seg=40, matrix=Matrix.Translation((cx, cy, 0)))
    C.fix_normals(bm)
    ob = C.mesh_obj("Circlip", bm, [mat])
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.004
    hb = bmesh.new()
    for s in (-1, 1):
        a = s * (gap / 2 + math.radians(5))
        C.cyl_bm(hb, 0.016, -0.1, 0.1, seg=24, matrix=Matrix.Translation((0.318 * math.cos(a), 0.318 * math.sin(a), 0)))
    holes = C.mesh_obj("LugHoles", hb, [mat])
    bo = C.add_boolean(ob, holes)
    bo.use_self = True
    bo.use_hole_tolerant = True
    C.add_bevel(ob, 0.004, segments=2, angle=30)
    return C.finalize(ob, angle=35, remove=[holes])


def build():
    ring, face, seal_m, lip, clip = mats()
    brg = [outer_ring(ring, face)] + inner_rings(ring, face) + seal(seal_m, lip, True) + seal(seal_m, lip, False)
    # bearing slightly tilted, resting on its rim, so face, seal and ground OD all show
    C.transform_all(brg, Matrix.Translation((0, 0, 0.0)) @ Matrix.Rotation(math.radians(0), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in brg for v in o.data.vertices)
    C.transform_all(brg, Matrix.Translation((0, 0, -lowest)))
    cl = circlip(clip)
    cl.matrix_world = Matrix.Translation((0.46, 0.46, 0.0)) @ Matrix.Rotation(math.radians(215), 4, "Z")
    return brg + [cl]


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("cuscinetto-ruota", objs, "cuscinetto-ruota.py",
            "wheel bearing kit: sealed double-row ball bearing with ground steel rings and black rubber seals, plus housing circlip",
            az=20, el=38, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
