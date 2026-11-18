"""Coolant expansion tank (vaschetta liquido refrigerante / vaso di espansione) as removed
from a small car: blow-moulded translucent off-white polypropylene tank with a little
pink coolant inside, moulded MIN/MAX lines and lettering on the front, black ribbed
pressure cap on the filler neck, outlet hose nipple at the bottom and vent nipple on
the side (both with retention beads), flat mounting tab with hole and a top peg."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

NX = 0.48              # filler neck x (1 unit ~ 10 cm)
TOP = 0.75             # top of the main body
LEVEL = 0.16           # coolant level (between MIN and MAX)
YF = -0.50             # front face


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def lathe_at(name, prof, mats, origin, axis, steps=64, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = axis_mat(origin, axis)
    return ob


def boolean(ob, cutter, op="DIFFERENCE"):
    m = C.add_boolean(ob, cutter, op)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def remeshed(ob, voxel=0.012, iters=12, fac=0.6):
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = fac
    sm.iterations = iters
    return ob


def rbox(bm, sx, sy, sz, center, r):
    vs = C.box_bm(bm, sx, sy, sz, center=center)
    es = list({e for v in vs for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=list(vs) + es, offset=r, offset_type="OFFSET", segments=6,
                    profile=0.5, affect="EDGES", clamp_overlap=True)


def body_bm(inset=0.0):
    i = inset
    bm = bmesh.new()
    rbox(bm, 1.90 - 2 * i, 1.00 - 2 * i, 1.05 - 2 * i, (0, 0, 0.22), 0.16 - i)          # main
    rbox(bm, 1.40 - 2 * i, 0.82 - 2 * i, 0.60, (0.10, 0, -0.42 + i), 0.12 - i)         # lower sump
    C.cyl_bm(bm, 0.27 - i, 0.5, TOP + 0.22 - i, seg=48, matrix=Matrix.Translation((NX, -0.05, 0)))
    return bm


def tank(shell):
    out = []
    bm = body_bm()
    # mounting tab on the +X end
    C.box_bm(bm, 0.56, 0.09, 0.42, center=(1.12, 0.28, -0.12))
    ob = C.mesh_obj("Tank", bm, [shell])
    remeshed(ob, iters=10)
    cb = bmesh.new()
    C.cyl_bm(cb, 0.085, -1, 1, seg=32, matrix=Matrix.Translation((1.22, 0.28, -0.14)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    cut = C.mesh_obj("TabHole", cb, [shell])
    boolean(ob, cut)
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.024
    so.offset = -1
    out.append(C.finalize(ob, angle=60, remove=[cut]))
    return out


def coolant(fluid):
    ob = C.mesh_obj("Coolant", body_bm(0.03), [fluid])
    remeshed(ob, iters=10)
    bm = bmesh.new()
    C.box_bm(bm, 3, 3, 2, center=(0, 0, LEVEL - 1.0))
    keep = C.mesh_obj("Level", bm, [fluid])
    boolean(ob, keep, "INTERSECT")
    return C.finalize(ob, angle=50, remove=[keep])


def nipple(name, mat, origin, axis, r=0.10, length=0.42):
    ri = r - 0.03
    P = [(ri, -0.06, 0), (r + 0.05, -0.06, 0), (r + 0.05, -0.02, 0), (r + 0.01, 0.03, 0), (r, 0.06, 0),
         (r, length - 0.10, 0), (r + 0.025, length - 0.06, 0), (r + 0.02, length - 0.035, 0), (r, length - 0.02, 0),
         (r - 0.01, length, 0), (ri, length, 0), (ri, -0.06, 0)]
    return C.finalize(lathe_at(name, P, [mat], origin, axis, steps=48), angle=45)


def fittings(shell, cap_m):
    out = []
    # outlet at the bottom, angled down and back; vent on the +X end near the top
    out.append(nipple("Outlet", shell, (0.30, -0.10, -0.66), (0.25, -0.55, -1.0), r=0.10, length=0.45))
    out.append(nipple("Vent", shell, (0.90, -0.10, 0.50), (1.0, -0.25, 0.15), r=0.06, length=0.34))
    # ribbed black pressure cap
    z = TOP + 0.20
    P = [(0.0, z, 0), (0.33, z, 0), (0.345, z + 0.02, 0), (0.345, z + 0.20, 0), (0.33, z + 0.23, 0),
         (0.22, z + 0.245, 0), (0.0, z + 0.25, 0)]
    rib = lambda r, zz, t: r + (0.022 if (r > 0.34 and math.cos(22 * t) > 0.2) else 0.0)
    out.append(C.finalize(lathe_at("Cap", P, [cap_m], (NX, -0.05, 0), (0, 0, 1), steps=176, mod=rib), angle=40))
    # moulded arrow-free circle on top of the cap
    P = [(0.12, z + 0.25, 0), (0.15, z + 0.25, 0), (0.15, z + 0.262, 0), (0.12, z + 0.262, 0)]
    out.append(C.finalize(lathe_at("CapRing", P, [cap_m], (NX, -0.05, 0), (0, 0, 1), steps=64), angle=40))
    return out


def marks(shell):
    """raised MIN / MAX lines with lettering on the front face"""
    out = []
    bm = bmesh.new()
    for z in (0.46, -0.10):
        C.box_bm(bm, 0.40, 0.03, 0.022, center=(-0.16, YF - 0.002, z))
    mk = C.mesh_obj("Lines", bm, [shell])
    C.add_bevel(mk, 0.006, segments=1, angle=30)
    out.append(C.finalize(mk, angle=35))
    for txt, z in (("MAX", 0.46), ("MIN", -0.10)):
        cu = bpy.data.curves.new(txt, "FONT")
        cu.body = txt
        cu.size = 0.13
        cu.extrude = 0.008
        cu.bevel_depth = 0.002
        cu.align_x = "RIGHT"
        cu.align_y = "CENTER"
        ob = C.link(bpy.data.objects.new(txt, cu))
        cu.materials.append(shell)
        ob.matrix_world = Matrix.Translation((-0.40, YF - 0.006, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        out.append(C.finalize(ob, angle=40))
    return out


def build():
    shell = C.principled("TankPP", (0.95, 0.91, 0.74), rough=0.36, IOR=1.49)
    b = next(n for n in shell.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Transmission Weight", 0.94)
    C.add_noise_bump(shell, scale=420, strength=0.06, distance=0.0006, rough_var=0.06)
    fluid = C.principled("CoolantG12", (0.95, 0.35, 0.55), rough=0.05, IOR=1.40)
    C._set(next(n for n in fluid.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Transmission Weight", 1.0)
    cap = C.mat_black_plastic("CapPA", rough=0.42, color=0.025)
    objs = tank(shell) + [coolant(fluid)] + fittings(shell, cap) + marks(shell)
    C.transform_all(objs, Matrix.Rotation(math.radians(-8), 4, "Z"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("vaschetta", objs, "vaschetta.py",
            "coolant expansion tank: translucent white plastic tank with MIN/MAX marks, black cap, two hose nipples, mounting tab",
            az=30, el=20, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
