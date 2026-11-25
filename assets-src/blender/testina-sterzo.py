"""Tie rod end (testina sterzo / testina dello sterzo): dark forged-steel body with the
ball-joint socket (pressed steel cap underneath), cranked forged arm and round threaded
shank whose open end shows the female thread for the tie rod; black rubber dust boot,
tapered ball stud with threaded tip and the self-locking hex nut fitted on it.

Socket axis +Z (stud up), shank along +X; units ~ decimetres (~13 cm long)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # lathe Z -> world +X
ZS = -0.03          # shank axis height
XS0, XS1 = 0.52, 1.06   # shank start / open end


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M, steps=96, bevel=None, angle=40, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle)


def thread_mat(name, color, rough=0.3, scale=90.0):
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


def superellipse(hw, hh, n=28, p=3.0):
    pts = []
    for i in range(n):
        t = math.tau * i / n
        c, s = math.cos(t), math.sin(t)
        pts.append((hw * math.copysign(abs(c) ** (2 / p), c), hh * math.copysign(abs(s) ** (2 / p), s)))
    return pts


def body(forged, cap_m, thread):
    out = []
    # socket housing around Z
    P = [(0.0, -0.13, 0), (0.17, -0.13, 0), (0.205, -0.10, 0), (0.212, -0.04, 0), (0.21, 0.07, 0),
         (0.19, 0.115, 0), (0.15, 0.14, 0), (0.115, 0.15, 0), (0.0, 0.15, 0)]
    out.append(lathe_at("Socket", P, [forged], Matrix(), steps=128, bevel=0.008))
    # pressed closing cap on the bottom with a rolled edge
    P = [(0.0, -0.165, 0), (0.12, -0.163, 0), (0.165, -0.15, 0), (0.18, -0.128, 0), (0.17, -0.12, 0), (0.0, -0.12, 0)]
    out.append(lathe_at("BottomCap", P, [cap_m], Matrix(), steps=96))
    # cranked forged arm from the socket to the shank (rounded section)
    frames = []
    n = 18
    for i in range(n + 1):
        u = i / n
        x = 0.08 + (XS0 + 0.06 - 0.08) * u
        z = 0.01 + (ZS - 0.01) * C.smoothstep(0.2, 0.8, u) - 0.03 * math.sin(math.pi * u)
        hw = 0.11 - 0.025 * math.sin(math.pi * u)
        hh = 0.095 - 0.012 * math.sin(math.pi * u)
        frames.append((Vector((x, 0, z)), Vector((0, 1, 0)), Vector((0, 0, 1)), superellipse(hw, hh)))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    out.append(fin(C.mesh_obj("Arm", bm, [forged]), bevel=0.01, angle=40))
    # forging parting-line flash along the arm sides
    bm = bmesh.new()
    for sy in (-1, 1):
        C.box_bm(bm, 0.36, 0.012, 0.018, center=(0.36, sy * 0.098, -0.02))
    out.append(fin(C.mesh_obj("Flash", bm, [forged]), bevel=0.005, angle=40))
    # threaded shank with female thread visible at the open end
    L = XS1 - XS0
    P = [(0.0, 0.0, 0), (0.118, 0.0, 0), (0.126, 0.03, 0), (0.126, L - 0.025, 0), (0.112, L, 0),
         (0.078, L, 1), (0.066, L - 0.012, 1), (0.066, 0.12, 1), (0.0, 0.10, 0)]
    out.append(lathe_at("Shank", P, [forged, thread], Matrix.Translation((XS0, 0, ZS)) @ RY, steps=96, bevel=0.004))
    # two spanner flats near the arm (raised hex collar)
    bm = bmesh.new()
    C.cyl_bm(bm, 0.145, 0.0, 0.10, seg=6, matrix=Matrix.Translation((XS0 + 0.03, 0, ZS)) @ RY @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    out.append(fin(C.mesh_obj("Hex", bm, [forged]), bevel=0.012, angle=35))
    return out


def stud(rubber, rod_m, thread, zinc, nylon):
    out = []
    P = [(0.0, 0.13, 0), (0.17, 0.13, 0), (0.195, 0.16, 0), (0.205, 0.20, 0), (0.19, 0.245, 0),
         (0.15, 0.28, 0), (0.105, 0.30, 0), (0.088, 0.315, 0), (0.0, 0.315, 0)]
    out.append(lathe_at("Boot", P, [rubber], Matrix(), steps=128, angle=55))
    # retaining ring on the boot neck
    P = [(0.08, 0.292, 0), (0.104, 0.292, 0), (0.108, 0.30, 0), (0.104, 0.308, 0), (0.08, 0.308, 0)]
    out.append(lathe_at("BootRing", P, [zinc], Matrix(), steps=64))
    P = [(0.0, 0.30, 0), (0.088, 0.30, 0), (0.072, 0.56, 0), (0.0, 0.56, 0)]
    out.append(lathe_at("Taper", P, [rod_m], Matrix(), steps=64))
    P = [(0.0, 0.56, 0), (0.058, 0.56, 0), (0.058, 0.86, 0), (0.048, 0.872, 0), (0.0, 0.872, 0)]
    out.append(lathe_at("StudThread", P, [thread], Matrix(), steps=48))
    # self-locking nut (washer face + hex + nylon-insert crown)
    bm = bmesh.new()
    C.cyl_bm(bm, 0.118, 0.625, 0.735, seg=6)
    C.cyl_bm(bm, 0.115, 0.612, 0.630, seg=48)
    out.append(fin(C.mesh_obj("Nut", bm, [zinc]), bevel=0.01, angle=35))
    P = [(0.058, 0.73, 0), (0.10, 0.73, 0), (0.10, 0.775, 0), (0.088, 0.79, 0), (0.058, 0.79, 0)]
    out.append(lathe_at("NutCrown", P, [zinc], Matrix(), steps=64))
    P = [(0.058, 0.786, 0), (0.08, 0.786, 0), (0.08, 0.796, 0), (0.058, 0.796, 0)]
    out.append(lathe_at("NutNylon", P, [nylon], Matrix(), steps=48))
    return out


def build():
    forged = C.mat_cast_iron("ForgedEnd", rust=0.3, base=0.075)
    cap_m = C.principled("CapSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.38)
    C.add_noise_bump(cap_m, scale=600, strength=0.05, distance=0.0005, rough_var=0.08)
    rubber = C.mat_rubber("BootRubber")
    rb = next(n for n in rubber.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rb.inputs["Roughness"].default_value = 0.55
    rod_m = C.principled("StudSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.30)
    C.add_noise_bump(rod_m, scale=600, strength=0.04, distance=0.0005, rough_var=0.06)
    thread = thread_mat("Thread", (0.50, 0.50, 0.51), rough=0.3, scale=40.0)
    zinc = C.principled("ZincNut", (0.66, 0.66, 0.62), metallic=1.0, rough=0.26)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005)
    nylon = C.principled("Nylon", (0.62, 0.60, 0.52), rough=0.5)
    objs = body(forged, cap_m, thread) + stud(rubber, rod_m, thread, zinc, nylon)
    # shank open end toward the viewer (front-right)
    C.transform_all(objs, Matrix.Rotation(math.radians(-12), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("testina-sterzo", objs, "testina-sterzo.py",
            "tie rod end: forged steel body with ball-joint socket, threaded shank with female thread, "
            "rubber dust boot, tapered ball stud with self-locking nut",
            az=30, el=24, lens=70, fill=0.84, **kw)
