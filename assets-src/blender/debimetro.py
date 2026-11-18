"""Mass air flow sensor (hot-film MAF in its own housing): short dark-grey glass-filled
nylon tube with hose-clamp beads on both ends, plastic honeycomb flow straightener
at the inlet, raised pad on top carrying the black plug-in sensor head (screwed
flange, body and 5-pin connector shroud with latch), moulded flow arrow on the side.

Tube axis along Y (inlet at -Y, toward the camera). 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RXn = Matrix.Rotation(-math.pi / 2, 4, "X")   # local Z -> +Y
RO, RI = 0.40, 0.355                          # tube outer / inner radius


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


def nylon(name, color=0.055, rough=0.55):
    """Glass-filled nylon: fine speckled texture, slightly satin."""
    m = C.principled(name, (color, color, color * 1.04), rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 260.0
    nz.inputs["Detail"].default_value = 3.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.08
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # dusty in the creases
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.06
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color * 1.5, color * 1.45, color * 1.35, 1)
    mix.inputs["B"].default_value = (color, color, color * 1.04, 1)
    nt.links.new(ao.outputs["AO"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def tube(grey):
    out = []
    P = [(RI, -0.60, 0), (RI, 0.60, 0), (0.38, 0.62, 0), (0.395, 0.62, 0), (0.41, 0.60, 0), (0.41, 0.54, 0),
         (0.385, 0.52, 0), (0.385, 0.47, 0), (0.43, 0.44, 0), (0.43, 0.40, 0), (0.40, 0.37, 0), (RO, 0.20, 0),
         (RO + 0.01, 0.18, 0), (RO + 0.01, -0.18, 0), (RO, -0.20, 0), (0.40, -0.37, 0), (0.43, -0.40, 0),
         (0.43, -0.44, 0), (0.385, -0.47, 0), (0.385, -0.52, 0), (0.41, -0.54, 0), (0.41, -0.60, 0),
         (0.395, -0.62, 0), (0.38, -0.62, 0)]
    out.append(lathe_at("Tube", P, grey, RXn, steps=160, bevel=0.004))
    # raised pad for the sensor + side ribs
    def pad(bm):
        C.box_bm(bm, 0.40, 0.62, 0.20, center=(0, 0, RO - 0.02 + 0.06))
        for s in (-1, 1):
            C.box_bm(bm, 0.03, 0.30, 0.16, center=(s * 0.21, 0, RO - 0.06))
    def bore(bm):
        C.cyl_bm(bm, RI + 0.002, -0.8, 0.8, seg=96, matrix=RXn)
    bc = cutter("PadBore", bore, grey)
    out.append(solid("Pad", pad, [grey], bevel=0.02, cutters=[bc]))
    # flow arrow moulded on the side (+X)
    arrow = [(-0.20, -0.03), (0.08, -0.03), (0.08, -0.085), (0.21, 0.0), (0.08, 0.085), (0.08, 0.03), (-0.20, 0.03)]
    def ar(bm):
        # arrow lies in the Y-Z plane, extruded along X; points toward +Y (flow direction)
        # columns: local x -> world Y (flow), local y -> world Z, local z (extrusion) -> world X
        M = Matrix.Rotation(math.radians(-32), 4, "Y") @ Matrix(((0, 0, 1, RO), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        prism_bm(bm, [(-0.20, -0.03), (0.09, -0.03), (0.09, 0.03), (-0.20, 0.03)], -0.03, 0.04, M)
        prism_bm(bm, [(0.08, -0.085), (0.22, 0.0), (0.08, 0.085)], -0.03, 0.04, M)
    out.append(solid("Arrow", ar, [grey], bevel=0.006))
    return out


def honeycomb(grey):
    def disc(bm):
        C.cyl_bm(bm, RI + 0.004, -0.50, -0.44, seg=96, matrix=RXn)
    cells = []
    s = 0.052                     # cell flat-to-flat spacing
    hx = s / math.sqrt(3) * 0.86  # hex circumradius (wall thickness = rest)
    def cut(bm):
        rows = int(RI / (s * 0.866)) + 2
        for j in range(-rows, rows + 1):
            z = j * s * 0.866
            off = (s / 2) if (j % 2) else 0.0
            for i in range(-rows, rows + 1):
                x = i * s + off
                if math.hypot(x, z) > RI - 0.01:
                    continue
                M = Matrix.Translation((x, 0, z)) @ RXn
                C.cyl_bm(bm, hx, -0.55, -0.40, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    hc = cutter("Cells", cut, grey)
    return solid("Honeycomb", disc, [grey], bevel=0.0, cutters=[hc], angle=40)


def sensor(black, dark, screw):
    out = []
    z0 = RO + 0.14
    def body(bm):
        C.box_bm(bm, 0.36, 0.58, 0.05, center=(0, 0, z0 + 0.025))          # flange
        C.box_bm(bm, 0.26, 0.40, 0.14, center=(0, 0.02, z0 + 0.12))        # electronics body
        C.box_bm(bm, 0.18, 0.30, 0.06, center=(0, 0.02, z0 + 0.21))        # lid step
        # connector shroud pointing +X
        C.box_bm(bm, 0.30, 0.24, 0.18, center=(0.24, 0.02, z0 + 0.13))
        C.box_bm(bm, 0.08, 0.10, 0.04, center=(0.26, 0.02, z0 + 0.235))   # latch
    def cav(bm):
        C.box_bm(bm, 0.20, 0.19, 0.13, center=(0.36, 0.02, z0 + 0.13))
    hc = cutter("ConnCav", cav, dark)
    out.append(solid("SensorHead", body, [black], bevel=0.014, cutters=[hc]))
    # 5 pins
    def pins(bm):
        for k in range(5):
            C.box_bm(bm, 0.10, 0.012, 0.022, center=(0.31, -0.06 + 0.032 * k + 0.016, z0 + 0.13))
    out.append(solid("Pins", pins, [C.principled("Tin", (0.75, 0.74, 0.70), metallic=1.0, rough=0.2)]))
    # two torx screws on the flange ears
    for y in (-0.24, 0.24):
        M = Matrix.Translation((0, y, z0 + 0.05))
        out.append(lathe_at("Screw", [(0.0, 0.0, 0), (0.045, 0.0, 0), (0.045, 0.02, 0), (0.035, 0.035, 0), (0.0, 0.035, 0)], screw, M, steps=32))
        out.append(lathe_at("Torx", [(0.0, 0.0355, 0), (0.016, 0.0355, 0), (0.016, 0.037, 0), (0.0, 0.037, 0)], dark, M, steps=6))
    return out


def build():
    grey = nylon("PA6GF", color=0.05, rough=0.55)
    black = C.mat_black_plastic("SensorPBT", rough=0.40, color=0.02)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    screw = C.principled("ScrewZinc", (0.58, 0.58, 0.60), metallic=1.0, rough=0.28)
    C.add_noise_bump(screw, scale=600, strength=0.03, distance=0.0005)
    objs = tube(grey) + [honeycomb(grey)] + sensor(black, dark, screw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("debimetro", objs, "debimetro.py",
            "mass air flow sensor: short dark plastic tube with honeycomb at the inlet, black plug-in sensor head with connector on top",
            az=32, el=22, lens=70, fill=0.82, **kw)
