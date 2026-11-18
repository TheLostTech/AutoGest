"""Electronic throttle body (drive-by-wire): cast-aluminium housing with a round
machined bore and the butterfly plate on its shaft (slightly open), square mounting
flange with 4 bolt holes facing the camera, hose spigot with seal bead on the
other side, DC motor housing cast under the bore, black plastic gear/sensor cover
with screws on the side and its connector shroud.

Bore axis along Y (flange at -Y), throttle shaft along X. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RXn = Matrix.Rotation(-math.pi / 2, 4, "X")   # local Z -> +Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")     # local Z -> +X
RB = 0.27                                     # bore radius


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


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.5
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.15
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = grime
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.06, base * 1.06, base * 1.04, 1)
    mix1.inputs["B"].default_value = (base * 0.80, base * 0.78, base * 0.72, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.10, 0.093, 0.08, 1)
    em = C.edge_mask(nt, 0.012, 4.0)
    wm = nt.nodes.new("ShaderNodeMath"); wm.operation = "MULTIPLY"; wm.use_clamp = True
    wm.inputs[1].default_value = wear
    nt.links.new(em, wm.inputs[0])
    mix3 = nt.nodes.new("ShaderNodeMix"); mix3.data_type = "RGBA"
    nt.links.new(wm.outputs[0], mix3.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], mix3.inputs["A"])
    mix3.inputs["B"].default_value = (0.72, 0.72, 0.71, 1)
    nt.links.new(mix3.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.25
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.16
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def bore_mat(name="Bore"):
    """Machined bore with a light film of oily carbon deposit."""
    m = C.principled(name, (0.34, 0.34, 0.35), metallic=1.0, rough=0.30)
    C.add_radial_aniso(m, 0.6, "Z", rings_scale=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 4.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.58
    mr.inputs["From Max"].default_value = 0.80
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.34, 0.34, 0.35, 1)
    mix.inputs["B"].default_value = (0.10, 0.10, 0.10, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    r2 = nt.nodes.new("ShaderNodeMapRange")
    r2.inputs["To Min"].default_value = 0.22
    r2.inputs["To Max"].default_value = 0.6
    nt.links.new(mr.outputs["Result"], r2.inputs["Value"])
    nt.links.new(r2.outputs["Result"], b.inputs["Roughness"])
    return m


# ----------------------------------------------------------------- parts
def housing(alu, bore):
    out = []
    # barrel + hose spigot (lathe along Y); inner surface = bore material
    P = [(RB, -0.32, 1), (RB, 0.62, 0), (0.30, 0.62, 0), (0.325, 0.60, 0), (0.325, 0.52, 0), (0.305, 0.50, 0),
         (0.305, 0.46, 0), (0.325, 0.44, 0), (0.325, 0.36, 0), (0.37, 0.32, 0), (0.37, -0.32, 0)]
    out.append(lathe_at("Barrel", P, alu, RXn, steps=128, bevel=0.006, mats=[alu, bore]))
    # mounting flange, 4 holes
    def fl(bm):
        prism_bm(bm, rrect(0.96, 0.96, 0.17), -0.42, -0.30, RXn)
    def holes(bm):
        C.cyl_bm(bm, RB, -0.6, -0.1, seg=96, matrix=RXn)
        for sx in (-1, 1):
            for sz in (-1, 1):
                C.cyl_bm(bm, 0.048, -0.6, -0.1, seg=24, matrix=Matrix.Translation((sx * 0.35, 0, sz * 0.35)) @ RXn)
    hc = cutter("FlCut", holes, bore)
    out.append(solid("Flange", fl, [alu], bevel=0.014, cutters=[hc]))
    # bolt-hole spot faces (raised rings) on the back of the flange
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.append(lathe_at("Boss", [(0.05, -0.30, 0), (0.085, -0.30, 0), (0.085, -0.20, 0), (0.05, -0.20, 0)], alu,
                                Matrix.Translation((sx * 0.35, 0, sz * 0.35)) @ RXn, steps=32, bevel=0.006))
    # motor housing under the bore (axis along X) + web
    out.append(lathe_at("Motor", [(0.0, -0.36, 0), (0.17, -0.36, 0), (0.20, -0.33, 0), (0.20, 0.44, 0), (0.0, 0.44, 0)], alu,
                        Matrix.Translation((0, 0.02, -0.55)) @ RY, steps=64, bevel=0.008))
    def web(bm):
        C.box_bm(bm, 0.70, 0.30, 0.34, center=(0.04, 0.02, -0.38))
        C.box_bm(bm, 0.05, 0.56, 0.30, center=(-0.20, 0.0, -0.36))
        C.box_bm(bm, 0.05, 0.56, 0.30, center=(0.22, 0.0, -0.36))
    out.append(solid("Web", web, [alu], bevel=0.02))
    # shaft bearing boss on -X
    out.append(lathe_at("ShaftBoss", [(0.0, 0.30, 0), (0.10, 0.30, 0), (0.10, 0.44, 0), (0.08, 0.46, 0), (0.0, 0.46, 0)], alu,
                        Matrix.Rotation(-math.pi / 2, 4, "Y"), steps=40, bevel=0.006))
    # side pad that carries the cover
    def pad(bm):
        prism_bm(bm, [(y, z) for (y, z) in rrect(0.66, 1.16, 0.22)], 0.30, 0.43,
                 Matrix.Translation((0, 0, -0.17)) @ RY @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    out.append(solid("Pad", pad, [alu], bevel=0.02))
    return out


def butterfly(plate_m, steel, screw):
    out = []
    M = Matrix.Rotation(math.radians(24), 4, "X") @ RXn
    out.append(lathe_at("Plate", [(0.0, -0.009, 0), (RB - 0.004, -0.009, 0), (RB - 0.002, -0.004, 0), (RB - 0.002, 0.004, 0),
                                  (RB - 0.004, 0.009, 0), (0.0, 0.009, 0)], plate_m, M, steps=128))
    out.append(lathe_at("Shaft", [(0.0, -0.30, 0), (0.032, -0.30, 0), (0.032, 0.30, 0), (0.0, 0.30, 0)], steel, RY, steps=32))
    for dx in (-0.09, 0.09):
        Ms = Matrix.Rotation(math.radians(24), 4, "X") @ Matrix.Translation((dx, -0.012, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        out.append(lathe_at("PlateScrew", [(0.0, 0.0, 0), (0.028, 0.0, 0), (0.026, 0.012, 0), (0.014, 0.018, 0), (0.0, 0.018, 0)],
                            screw, Ms, steps=24))
    return out


def cover(black, dark, screw):
    out = []
    Mc = Matrix.Translation((0, 0, -0.17)) @ RY @ Matrix.Rotation(math.pi / 2, 4, "Z")
    def body(bm):
        prism_bm(bm, rrect(0.64, 1.14, 0.21), 0.43, 0.56, Mc)
        prism_bm(bm, rrect(0.46, 0.86, 0.14), 0.55, 0.62, Mc @ Matrix.Translation((0.02, -0.06, 0)))
        # stiffening ribs
        for dz in (-0.25, 0.0, 0.25):
            C.box_bm(bm, 0.03, 0.40, 0.025, center=(0.635, 0.0, -0.20 + dz))
        # connector shroud on top, pointing up
        C.box_bm(bm, 0.20, 0.34, 0.24, center=(0.50, -0.02, 0.50))
        C.box_bm(bm, 0.08, 0.12, 0.04, center=(0.50, -0.02, 0.64))
    def cav(bm):
        C.box_bm(bm, 0.15, 0.29, 0.25, center=(0.50, -0.02, 0.58))
    hc = cutter("ConnCut", cav, dark)
    out.append(solid("Cover", body, [black], bevel=0.016, cutters=[hc]))
    # screws around the cover rim
    for (y, z) in ((-0.24, 0.30), (0.24, 0.30), (-0.24, -0.66), (0.24, -0.66), (0.27, -0.17)):
        M = Matrix.Translation((0.56, y, z)) @ RY
        out.append(lathe_at("CoverScrew", [(0.0, 0.0, 0), (0.035, 0.0, 0), (0.035, 0.012, 0), (0.025, 0.026, 0), (0.0, 0.026, 0)],
                            screw, M, steps=24))
    return out


def build():
    alu = cast_alu("ThrottleAlu", base=0.40, rough=0.44, grime=0.6, grain=260.0)
    bore = bore_mat()
    plate = C.principled("PlateBrass", (0.80, 0.70, 0.48), metallic=1.0, rough=0.22)
    C.add_noise_bump(plate, scale=300, strength=0.04, distance=0.0008)
    steel = C.mat_machined("ShaftSteel", color=0.55, rough=0.2, rings=600)
    screw = C.principled("ScrewZinc", (0.60, 0.60, 0.62), metallic=1.0, rough=0.28)
    black = C.mat_black_plastic("CoverPA", rough=0.48, color=0.025)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    objs = housing(alu, bore) + butterfly(plate, steel, screw) + cover(black, dark, screw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("corpo-farfallato", objs, "corpo-farfallato.py",
            "electronic throttle body: cast aluminium housing, round bore with butterfly plate, 4-hole flange, black motor/sensor cover with connector",
            az=28, el=22, lens=70, fill=0.84, **kw)
