"""Clutch kit (kit frizione), the three pieces arranged together like a parts-dealer
photo: the pressure plate (zinc-plated stamped cover with three-lobed bolt flange,
windows, fulcrum rivets, dark diaphragm spring with eighteen slotted fingers and worn
shiny tips, cast-iron pressure ring inside) standing upright at the back; the friction
disc (riveted grooved linings, steel carrier plates, six torsion-damper coil springs,
splined hub) standing in front of it; and the release bearing (steel race, black
plastic carrier with fork pads) lying on the floor.

Each piece is built around +Z and then placed; units ~ decimetres (cover ~24 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
TAU = math.tau


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M=None, steps=128, bevel=None, angle=40, mod=None, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    if M is not None:
        ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def frames_along(pts, sec):
    out = []
    n = len(pts)
    prevU = None
    for i, P in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prevU is None:
            U = T.cross(Vector((0, 0, 1)))
            if U.length < 1e-4:
                U = T.cross(Vector((1, 0, 0)))
        else:
            U = prevU - T * prevU.dot(T)
        U.normalize()
        V = T.cross(U).normalized()
        prevU = U
        out.append((P, U, V, sec))
    return out


def place(objs, M, x, y):
    """apply M, then drop the group onto the floor at (x, y)."""
    C.transform_all(objs, M)
    bpy.context.view_layer.update()
    zmin = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((x, y, -zmin)))


def cutter(name, build_fn):
    bm = bmesh.new()
    build_fn(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [])


# ----------------------------------------------------------------- materials
def mat_zinc_cover(name):
    m = C.principled(name, (0.58, 0.58, 0.55), metallic=1.0, rough=0.34)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.40, 0.40, 0.38, 1)
    mix.inputs["B"].default_value = (0.56, 0.55, 0.51, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    C.add_noise_bump(m, scale=700, strength=0.05, distance=0.0005)
    return m


def mat_diaphragm(name):
    """black-oxide spring steel, finger tips rubbed shiny by the release bearing."""
    m = C.principled(name, (0.05, 0.05, 0.055), metallic=1.0, rough=0.36)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Object"], sep.inputs[0])
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], ln.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.34
    mr.inputs["From Max"].default_value = 0.27
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.05, 0.05, 0.055, 1)
    mix.inputs["B"].default_value = (0.62, 0.62, 0.63, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.38
    rr.inputs["To Max"].default_value = 0.18
    nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    C.add_noise_bump(m, scale=600, strength=0.05, distance=0.0005)
    return m


def mat_lining(name):
    m = C.principled(name, (0.055, 0.048, 0.042), rough=0.78)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    vo.inputs["Scale"].default_value = 160.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.12
    mr.inputs["From Max"].default_value = 0.0
    nt.links.new(vo.outputs["Distance"], mr.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 18.0
    c1 = nt.nodes.new("ShaderNodeMix"); c1.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], c1.inputs["Factor"])
    c1.inputs["A"].default_value = (0.040, 0.036, 0.032, 1)
    c1.inputs["B"].default_value = (0.085, 0.072, 0.060, 1)
    c2 = nt.nodes.new("ShaderNodeMix"); c2.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], c2.inputs["Factor"])
    nt.links.new(c1.outputs["Result"], c2.inputs["A"])
    c2.inputs["B"].default_value = (0.42, 0.33, 0.18, 1)
    nt.links.new(c2.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(mr.outputs["Result"], b.inputs["Metallic"])
    C.add_noise_bump(m, scale=500, strength=0.15, distance=0.001)
    return m


# ----------------------------------------------------------------- pressure plate
def pressure_plate(cover_m, dia_m, iron_face, rivet_m):
    out = []
    # cover: flange z 0.30-0.34, wall up to 0.62, top face inward to r 0.66
    P = [(1.24, 0.30, 0), (1.24, 0.34, 0), (1.02, 0.34, 0), (0.99, 0.37, 0), (0.98, 0.60, 0), (0.95, 0.65, 0),
         (0.66, 0.67, 0), (0.66, 0.70, 0), (0.97, 0.68, 0), (1.01, 0.63, 0), (1.02, 0.38, 0), (1.04, 0.30, 0)]
    cuts = []
    # lobes: scallop the flange between the bolt groups
    for k in range(3):
        a = TAU * k / 3 + math.pi / 3
        cuts.append(cutter("Scallop", lambda bm, a=a: C.cyl_bm(bm, 0.42, 0.0, 1.0, seg=64,
                           matrix=Matrix.Translation((1.48 * math.cos(a), 1.48 * math.sin(a), 0)))))
    def holes(bm):
        for k in range(3):
            for d in (-0.32, 0.32):
                a = TAU * k / 3 + d
                C.cyl_bm(bm, 0.045, 0.0, 1.0, seg=24, matrix=Matrix.Translation((1.13 * math.cos(a), 1.13 * math.sin(a), 0)))
            a = TAU * k / 3
            C.cyl_bm(bm, 0.035, 0.0, 1.0, seg=24, matrix=Matrix.Translation((1.15 * math.cos(a), 1.15 * math.sin(a), 0)))
    cuts.append(cutter("BoltHoles", holes))
    for k in range(3):
        a = TAU * k / 3 + math.pi / 3
        M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((1.0, 0, 0.50))
        cuts.append(cutter("Window", lambda bm, M=M: C.box_bm(bm, 0.3, 0.46, 0.17, matrix=M)))
    out.append(lathe_at("Cover", P, [cover_m], steps=256, bevel=0.008, cutters=cuts))
    # cast-iron pressure ring inside (visible through windows / from below)
    P = [(0.66, 0.0, 0), (0.98, 0.0, 0), (0.98, 0.16, 0), (0.94, 0.20, 0), (0.70, 0.20, 0), (0.66, 0.16, 0)]
    out.append(lathe_at("PressureRing", P, [iron_face], steps=160, bevel=0.006))
    # lugs of the ring that show in the windows
    bm = bmesh.new()
    for k in range(3):
        a = TAU * k / 3 + math.pi / 3
        C.box_bm(bm, 0.12, 0.24, 0.14, matrix=Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.96, 0, 0.27)))
    out.append(fin(C.mesh_obj("RingLugs", bm, [iron_face]), bevel=0.012))
    # diaphragm spring: cone from the outer rim (under the cover top) to the finger tips
    th = 0.028
    P = [(0.27, 0.86, 0), (0.93, 0.62, 0), (0.93, 0.62 + th, 0), (0.27, 0.86 + th, 0)]
    cuts = []
    NF = 18
    for k in range(NF):
        a = TAU * (k + 0.5) / NF
        R = Matrix.Rotation(a, 4, "Z")
        cuts.append(cutter("Slot", lambda bm, R=R: C.box_bm(bm, 0.40, 0.035, 0.6, matrix=R @ Matrix.Translation((0.44, 0, 0.75)))))
    def round_holes(bm):
        for k in range(NF):
            a = TAU * (k + 0.5) / NF
            C.cyl_bm(bm, 0.035, 0.4, 1.1, seg=20, matrix=Matrix.Translation((0.64 * math.cos(a), 0.64 * math.sin(a), 0)))
    cuts.append(cutter("SlotEnds", round_holes))
    out.append(lathe_at("Diaphragm", P, [dia_m], steps=NF * 16, bevel=0.004, cutters=cuts))
    # fulcrum rivets round the cover top
    for k in range(9):
        a = TAU * k / 9
        P = [(0.0, 0.69, 0), (0.042, 0.69, 0), (0.04, 0.715, 0), (0.025, 0.73, 0), (0.0, 0.732, 0)]
        out.append(lathe_at("Rivet", P, [rivet_m], Matrix.Translation((0.80 * math.cos(a), 0.80 * math.sin(a), -0.02)),
                            steps=24))
    # tangential drive straps riveted under the flange lobes (visible on the outside)
    bm = bmesh.new()
    for k in range(3):
        a = TAU * k / 3
        R = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((1.06, 0, 0.27)) @ Matrix.Rotation(math.radians(8), 4, "X")
        C.box_bm(bm, 0.10, 0.52, 0.03, matrix=R)
    out.append(fin(C.mesh_obj("Straps", bm, [rivet_m]), bevel=0.008))
    return out


# ----------------------------------------------------------------- friction disc
def helix_spring(R, wire, L, turns, mat, M):
    n = int(turns * 24)
    pts = [Vector((R * math.cos(TAU * turns * i / n), R * math.sin(TAU * turns * i / n), -L / 2 + L * i / n)) for i in range(n + 1)]
    sec = [(wire * math.cos(TAU * j / 10), wire * math.sin(TAU * j / 10)) for j in range(10)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec))
    ob = C.mesh_obj("Spring", bm, [mat])
    ob.matrix_world = M
    return C.finalize(ob, angle=60)


def friction_disc(lining, plate_m, spring_m, hub_m, rivet_m):
    out = []
    # two linings on wavy cushion segments (gap between them shows the steel)
    for (z0, z1) in ((0.015, 0.05), (-0.05, -0.015)):
        P = [(0.66, z0, 0), (1.0, z0, 0), (1.0, z1, 0), (0.66, z1, 0)]
        top = z1 if z1 > 0 else z0
        def holes(bm, top=top):
            for k in range(14):
                for (r, off) in ((0.73, 0.0), (0.90, 0.5)):
                    a = TAU * (k + off) / 14
                    C.cyl_bm(bm, 0.028, top - 0.022 * (1 if top > 0 else -1), top + 0.1 * (1 if top > 0 else -1), seg=20,
                             matrix=Matrix.Translation((r * math.cos(a), r * math.sin(a), 0)))
        def grooves(bm, top=top):
            for k in range(10):
                a = TAU * (k + 0.25) / 10
                C.box_bm(bm, 0.40, 0.022, 0.03, matrix=Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.83, 0, top)))
        cuts = [cutter("RivetHoles", holes), cutter("Grooves", grooves)]
        out.append(lathe_at("Lining", P, [lining], steps=256, bevel=0.004, cutters=cuts))
    # cushion segments (steel visible between the linings)
    P = [(0.64, -0.015, 0), (0.99, -0.015, 0), (0.99, 0.015, 0), (0.64, 0.015, 0)]
    out.append(lathe_at("Cushion", P, [plate_m], steps=128))
    # rivets in the holes
    for k in range(14):
        for (r, off) in ((0.73, 0.0), (0.90, 0.5)):
            a = TAU * (k + off) / 14
            P = [(0.0, -0.035, 0), (0.016, -0.035, 0), (0.016, 0.035, 0), (0.0, 0.035, 0)]
            out.append(lathe_at("LRivet", P, [rivet_m], Matrix.Translation((r * math.cos(a), r * math.sin(a), 0)), steps=12))
    # two carrier/retainer plates with spring windows
    for (z0, z1) in ((0.02, 0.045), (-0.045, -0.02)):
        P = [(0.20, z0, 0), (0.68, z0, 0), (0.68, z1, 0), (0.20, z1, 0)]
        def windows(bm):
            for k in range(6):
                a = TAU * k / 6
                C.box_bm(bm, 0.10, 0.25, 0.3, matrix=Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.47, 0, 0)))
        out.append(lathe_at("CarrierPlate", P, [plate_m], steps=192, bevel=0.004, cutters=[cutter("Win", windows)]))
    # damper coil springs in the windows (axis tangential)
    for k in range(6):
        a = TAU * k / 6
        M = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.47, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        out.append(helix_spring(0.048, 0.011, 0.23, 6.5, spring_m, M))
    # stop pins between the plates
    for k in range(6):
        a = TAU * (k + 0.5) / 6
        P = [(0.0, -0.06, 0), (0.03, -0.06, 0), (0.03, 0.06, 0), (0.0, 0.06, 0)]
        out.append(lathe_at("StopPin", P, [rivet_m], Matrix.Translation((0.60 * math.cos(a), 0.60 * math.sin(a), 0)), steps=16,
                            bevel=0.008))
    # splined hub with flange
    def splines(r, z, t):
        if r > 0.125:
            return r
        return r - 0.018 * (1 if math.cos(20 * t) > 0 else 0)
    P = [(0.12, -0.17, 0), (0.20, -0.17, 0), (0.20, -0.03, 0), (0.30, -0.03, 0), (0.30, 0.03, 0), (0.20, 0.03, 0),
         (0.20, 0.15, 0), (0.12, 0.15, 0)]
    out.append(lathe_at("Hub", P, [hub_m], steps=20 * 8, bevel=0.005, mod=splines))
    return out


# ----------------------------------------------------------------- release bearing
def release_bearing(race_m, black, seal):
    out = []
    P = [(0.16, 0.0, 0), (0.33, 0.0, 0), (0.33, 0.14, 0), (0.30, 0.18, 0), (0.22, 0.20, 0), (0.16, 0.20, 0)]
    out.append(lathe_at("Race", P, [race_m], steps=128, bevel=0.005))
    P = [(0.17, 0.20, 0), (0.22, 0.20, 0), (0.22, 0.26, 0), (0.17, 0.26, 0)]
    out.append(lathe_at("ContactRing", P, [race_m], steps=96, bevel=0.004))
    P = [(0.23, 0.185, 0), (0.29, 0.17, 0), (0.29, 0.18, 0), (0.23, 0.196, 0)]
    out.append(lathe_at("Seal", P, [seal], steps=96))
    # plastic carrier: sleeve + flange with two fork pads
    P = [(0.15, -0.38, 0), (0.21, -0.38, 0), (0.22, -0.10, 0), (0.40, -0.08, 0), (0.40, 0.0, 0), (0.15, 0.0, 0)]
    out.append(lathe_at("Carrier", P, [black], steps=96, bevel=0.006))
    bm = bmesh.new()
    for s in (-1, 1):
        C.box_bm(bm, 0.14, 0.12, 0.10, center=(s * 0.44, 0, -0.06))
    out.append(fin(C.mesh_obj("ForkPads", bm, [black]), bevel=0.01))
    return out


def build():
    cover_m = mat_zinc_cover("CoverZinc")
    dia_m = mat_diaphragm("Diaphragm")
    iron = C.mat_cast_iron("PressureIron", rust=0.25, base=0.16)
    rivet_m = C.principled("RivetSteel", (0.55, 0.55, 0.54), metallic=1.0, rough=0.3)
    lining = mat_lining("Lining")
    plate_m = C.principled("CarrierSteel", (0.20, 0.20, 0.21), metallic=1.0, rough=0.38)
    C.add_noise_bump(plate_m, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    spring_m = C.principled("SpringSteel", (0.12, 0.12, 0.13), metallic=1.0, rough=0.30)
    hub_m = C.mat_machined("Hub", color=0.48, rough=0.26, rings=400)
    race_m = C.mat_machined("Race", color=0.60, rough=0.18, rings=900)
    black = C.mat_black_plastic("CarrierPA", rough=0.48, color=0.03)
    seal = C.mat_rubber("Seal")

    pp = pressure_plate(cover_m, dia_m, iron, rivet_m)
    fd = friction_disc(lining, plate_m, spring_m, hub_m, rivet_m)
    rb = release_bearing(race_m, black, seal)
    # pressure plate upright at the back, diaphragm toward the camera, leaning back a little
    place(pp, Matrix.Rotation(math.radians(-8), 4, "Z") @ Matrix.Rotation(math.radians(78), 4, "X"), -0.55, 0.0)
    # disc upright in front-right, turned toward the viewer
    place(fd, Matrix.Rotation(math.radians(-28), 4, "Z") @ Matrix.Rotation(math.radians(76), 4, "X"), 1.05, -1.25)
    # release bearing lying on the floor in front-left
    place(rb, Matrix(), -0.85, -1.85)
    return pp + fd + rb


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("kit-frizione", objs, "kit-frizione.py",
            "clutch kit: pressure plate with diaphragm spring fingers, friction disc with damper springs "
            "and splined hub, release bearing, arranged together",
            az=18, el=18, lens=70, fill=0.86, **kw)
