"""Ignition coil rail for an inline-4 (coil-on-plug pack): black PBT rail with four
coil towers, ribbed top with a blank adhesive label, mounting tabs with steel
compression sleeves at the ends and on the back, central connector shroud with
latch on the front, and four dark-grey silicone spark-plug boots hanging down,
each ending in a plug cap with a contact spring.

Rail along X, boots toward -Z, connector toward -Y (camera). 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
CX = (-1.32, -0.44, 0.44, 1.32)
RAIL_M = Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "Z")   # sec (u,v)->(y,z), extrude ->x


# ----------------------------------------------------------------- helpers
def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=()):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        C.add_boolean(ob, c).use_self = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None, mod=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps, mod=mod)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def hex_at(name, r, z0, z1, mat, M=I4, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def silicone(name, color=0.075):
    m = C.principled(name, (color, color * 1.0, color * 1.05), rough=0.62)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 300.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    # dusty, lighter toward the plug end (heat/handling)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.2
    mr.inputs["From Max"].default_value = -0.4
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (color, color, color * 1.05, 1)
    mix.inputs["B"].default_value = (color * 1.9, color * 1.75, color * 1.55, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def rail(black, sleeve_m, dark):
    out = []
    def body(bm):
        prism_bm(bm, rrect(0.56, 0.36, 0.10), -1.78, 1.78, Matrix.Translation((0, 0, 0.20)) @ RAIL_M)
        # end tabs (horizontal) and back tabs
        for s in (-1, 1):
            C.box_bm(bm, 0.36, 0.30, 0.10, center=(s * 1.92, 0.0, 0.09))
            C.cyl_bm(bm, 0.15, 0.04, 0.14, seg=32, matrix=Matrix.Translation((s * 2.08, 0.0, 0)))
        for x in (-0.88, 0.88):
            C.box_bm(bm, 0.28, 0.30, 0.10, center=(x, 0.38, 0.09))
            C.cyl_bm(bm, 0.14, 0.04, 0.14, seg=32, matrix=Matrix.Translation((x, 0.52, 0)))
        # longitudinal top ribs
        for y in (-0.16, 0.16):
            C.box_bm(bm, 3.30, 0.035, 0.05, center=(0, y, 0.395))
    def holes(bm):
        for s in (-1, 1):
            C.cyl_bm(bm, 0.075, -0.2, 0.4, seg=24, matrix=Matrix.Translation((s * 2.08, 0.0, 0)))
        for x in (-0.88, 0.88):
            C.cyl_bm(bm, 0.07, -0.2, 0.4, seg=24, matrix=Matrix.Translation((x, 0.52, 0)))
    hc = cutter("TabHoles", holes, dark)
    out.append(solid("Rail", body, [black], bevel=0.02, cutters=[hc]))
    # coil towers
    for x in CX:
        P = [(0.0, -0.16, 0), (0.25, -0.16, 0), (0.27, -0.12, 0), (0.27, 0.36, 0), (0.25, 0.41, 0), (0.18, 0.43, 0), (0.0, 0.43, 0)]
        out.append(lathe_at("Tower", P, black, Matrix.Translation((x, 0, 0)), steps=64))
    # steel compression sleeves + bolts in the tabs
    for (x, y) in ((-2.08, 0.0), (2.08, 0.0), (-0.88, 0.52), (0.88, 0.52)):
        M = Matrix.Translation((x, y, 0))
        out.append(lathe_at("Sleeve", [(0.05, 0.03, 0), (0.075, 0.03, 0), (0.075, 0.15, 0), (0.05, 0.15, 0)], sleeve_m, M, steps=32))
    return out


def connector(black, dark, tin):
    out = []
    def con(bm):
        C.box_bm(bm, 0.46, 0.30, 0.30, center=(0.0, -0.40, 0.20))
        C.box_bm(bm, 0.14, 0.08, 0.05, center=(0.0, -0.44, 0.375))     # latch
        C.box_bm(bm, 0.05, 0.10, 0.22, center=(-0.25, -0.40, 0.20))
        C.box_bm(bm, 0.05, 0.10, 0.22, center=(0.25, -0.40, 0.20))
    def cav(bm):
        C.box_bm(bm, 0.38, 0.30, 0.22, center=(0.0, -0.52, 0.20))
    hc = cutter("ConnCav", cav, dark)
    out.append(solid("Connector", con, [black], bevel=0.014, cutters=[hc]))
    def pins(bm):
        for k in range(4):
            C.box_bm(bm, 0.022, 0.16, 0.022, center=(-0.105 + 0.07 * k, -0.42, 0.20))
    out.append(solid("Pins", pins, [tin]))
    return out


def boots(sil, black, tin):
    out = []
    for x in CX:
        M = Matrix.Translation((x, 0, 0))
        P = [(0.0, -0.10, 0), (0.20, -0.10, 0), (0.20, -0.24, 0), (0.15, -0.28, 0), (0.135, -0.32, 0)]
        z = -0.36
        for i in range(3):  # gripping ribs
            P += [(0.150, z, 0), (0.150, z - 0.03, 0), (0.135, z - 0.05, 0)]
            z -= 0.08
        P += [(0.125, -0.95, 0), (0.118, -1.12, 0), (0.108, -1.17, 0), (0.06, -1.19, 0), (0.0, -1.19, 0)]
        out.append(lathe_at("Boot", P, sil, M, steps=64, bevel=0.004))
        # contact spring tip
        out.append(lathe_at("Spring", [(0.0, -1.23, 0), (0.025, -1.23, 0), (0.03, -1.21, 0), (0.03, -1.185, 0), (0.0, -1.185, 0)], tin, M, steps=24))
        # black collar where the boot meets the tower
        out.append(lathe_at("Collar", [(0.0, -0.17, 0), (0.24, -0.17, 0), (0.24, -0.09, 0), (0.0, -0.09, 0)], black, M, steps=64, bevel=0.01))
    return out


def label():
    im = C.label_image("CoilLabel", 1024, 360, seed=21, lines=3)
    m = C.mat_label(im, rough=0.45)
    # label on the front face between the first two towers (normal -Y)
    M = Matrix.Translation((-0.88, -0.2815, 0.20))
    return [C.label_plane("Label", m, 0.46, 0.15, M)]


def build():
    black = C.mat_black_plastic("RailPBT", rough=0.34, color=0.02)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    sleeve = C.principled("SleeveZinc", (0.62, 0.60, 0.52), metallic=1.0, rough=0.28)
    C.add_noise_bump(sleeve, scale=500, strength=0.04, distance=0.0005)
    tin = C.principled("Tin", (0.75, 0.74, 0.70), metallic=1.0, rough=0.2)
    sil = silicone("BootSilicone", 0.07)
    objs = rail(black, sleeve, dark) + connector(black, dark, tin) + boots(sil, black, tin) + label()
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("bobina", objs, "bobina.py",
            "ignition coil pack for 4 cylinders: black plastic rail with four silicone plug boots hanging down, mounting tabs and connector",
            az=26, el=20, lens=70, fill=0.86, **kw)
