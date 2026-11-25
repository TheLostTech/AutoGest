"""Inner tie rod (tirante sterzo / asta sterzo assiale): axial ball joint with a round
forged housing (two spanner flats, crimped dome where the rod leaves the ball), male
thread stud and tab lock washer on the rack side; long dark steel rod with spanner flats
near the joint, rolled thread at the outer end and the hex lock nut screwed on it.

Rod axis along +X (rack side at x<0); units ~ decimetres (~38 cm long)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # lathe Z -> world +X


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def xlathe(name, prof, mats, x=0.0, steps=96, bevel=None, angle=40, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = Matrix.Translation((x, 0, 0)) @ RY
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def thread_mat(name, color, rough=0.3, scale=40.0):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = scale
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.008
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def flats_cutters(x0, x1, r, mat):
    """two boxes that shave opposite flats off a round part between x0 and x1"""
    out = []
    for sy in (-1, 1):
        bm = bmesh.new()
        C.box_bm(bm, x1 - x0, 0.3, 0.6, center=((x0 + x1) / 2, sy * (r + 0.15), 0))
        out.append(C.mesh_obj("Flat", bm, [mat]))
    return out


def joint(housing_m, thread, zinc):
    out = []
    # housing: rack-side face at x=0, dome toward +X
    P = [(0.0, 0.0, 0), (0.15, 0.0, 0), (0.17, 0.02, 0), (0.17, 0.30, 0), (0.165, 0.34, 0),
         (0.15, 0.39, 0), (0.12, 0.43, 0), (0.095, 0.452, 0), (0.0, 0.455, 0)]
    out.append(xlathe("Housing", P, [housing_m], steps=128, bevel=0.006,
                      cutters=flats_cutters(0.05, 0.26, 0.135, housing_m)))
    # crimp groove line where the housing is rolled over the ball seat
    P = [(0.160, 0.305, 0), (0.172, 0.305, 0), (0.172, 0.318, 0), (0.160, 0.318, 0)]
    out.append(xlathe("CrimpRing", P, [housing_m], steps=128))
    # tab lock washer against the rack face
    P = [(0.07, -0.022, 0), (0.175, -0.022, 0), (0.175, 0.0, 0), (0.07, 0.0, 0)]
    out.append(xlathe("LockWasher", P, [zinc], steps=96))
    bm = bmesh.new()
    C.box_bm(bm, 0.022, 0.07, 0.10, center=(-0.011, 0, 0.21))
    C.box_bm(bm, 0.09, 0.07, 0.016, center=(0.035, 0, 0.255))
    out.append(fin(C.mesh_obj("WasherTab", bm, [zinc]), bevel=0.005))
    # male thread stud into the rack
    P = [(0.0, -0.022, 0), (0.07, -0.022, 0), (0.07, -0.25, 0), (0.06, -0.262, 0), (0.0, -0.262, 0)]
    out.append(xlathe("RackThread", P, [thread], steps=64))
    # rod leaving the dome through a flared neck
    P = [(0.0, 0.40, 0), (0.092, 0.44, 0), (0.09, 0.47, 0), (0.084, 0.50, 0), (0.0, 0.50, 0)]
    out.append(xlathe("BallNeck", P, [thread.copy()], steps=64))
    out[-1].data.materials[0] = housing_m
    return out


def rod(rod_m, thread, zinc):
    out = []
    L0, L1, LT = 0.45, 2.55, 3.30
    P = [(0.0, L0, 0), (0.085, L0, 0), (0.08, L0 + 0.06, 0), (0.077, L0 + 0.10, 0), (0.077, L1, 0),
         (0.072, L1 + 0.02, 0), (0.0, L1 + 0.02, 0)]
    out.append(xlathe("Rod", P, [rod_m], steps=64))
    # spanner flats section near the joint
    P = [(0.0, 0.62, 0), (0.105, 0.62, 0), (0.11, 0.64, 0), (0.11, 0.80, 0), (0.105, 0.82, 0), (0.0, 0.82, 0)]
    out.append(xlathe("FlatCollar", P, [rod_m], steps=64, bevel=0.004,
                      cutters=flats_cutters(0.60, 0.84, 0.088, rod_m)))
    P = [(0.0, L1, 0), (0.07, L1, 0), (0.07, LT - 0.012, 0), (0.06, LT, 0), (0.0, LT, 0)]
    out.append(xlathe("OuterThread", P, [thread], steps=64))
    # lock nut on the thread
    xn = L1 + 0.22
    bm = bmesh.new()
    C.cyl_bm(bm, 0.125, -0.055, 0.055, seg=6, matrix=Matrix.Translation((xn, 0, 0)) @ RY @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    nut = C.mesh_obj("LockNut", bm, [zinc])
    # chamfered corners: intersect with a double cone (bevel modifier on hex is enough here)
    out.append(fin(nut, bevel=0.014, angle=35))
    P = [(0.07, -0.058, 0), (0.105, -0.058, 0), (0.105, 0.058, 0), (0.07, 0.058, 0)]
    out.append(xlathe("NutBore", P, [zinc], x=xn, steps=64))
    return out


def build():
    housing_m = C.principled("JointSteel", (0.40, 0.40, 0.41), metallic=1.0, rough=0.34)
    C.add_noise_bump(housing_m, scale=600, strength=0.05, distance=0.0006, rough_var=0.08)
    rod_m = C.principled("RodSteel", (0.16, 0.16, 0.165), metallic=1.0, rough=0.36)
    C.add_noise_bump(rod_m, scale=600, strength=0.05, distance=0.0005, rough_var=0.08)
    thread = thread_mat("Thread", (0.52, 0.52, 0.53), rough=0.3, scale=40.0)
    zinc = C.principled("Zinc", (0.66, 0.66, 0.63), metallic=1.0, rough=0.26)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005)
    objs = joint(housing_m, thread, zinc) + rod(rod_m, thread, zinc)
    C.transform_all(objs, Matrix.Rotation(math.radians(32), 4, "Z") @ Matrix.Rotation(math.radians(40), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("tirante-sterzo", objs, "tirante-sterzo.py",
            "inner tie rod: axial ball joint housing with spanner flats and rack-side thread, "
            "long steel rod with threaded outer end and lock nut",
            az=0, el=50, lens=70, fill=0.92, **kw)
