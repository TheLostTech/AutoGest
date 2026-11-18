"""Dual-mass flywheel (volano bimassa): pressed-steel primary mass carrying the starter
ring gear (machined teeth all round the circumference), secondary mass with the
machined friction face (turning marks), raised clutch-cover mounting ring with threaded
holes and dowel pins, ventilation windows and rivet heads in the inner zone, and the
primary hub with eight crankshaft bolt holes and pilot bearing visible in the centre.

Built around +Z (friction face up), then stood up facing the camera for the shot.
Units ~ decimetres (diameter ~29 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

NT = 132            # ring gear teeth
RR, RT = 1.40, 1.47  # ring gear root / tip radius


def gear_mod(r, z, t):
    if r <= RR + 1e-6:
        return r
    v = math.cos(NT * t)
    sq = max(-1.0, min(1.0, (v + 0.05) * 2.4)) * 0.5 + 0.5
    return RR + (r - RR) * sq


def ring_gear(steel):
    P = [(1.30, -0.31, 0), (RR, -0.31, 0), (RT - 0.018, -0.31, 0), (RT, -0.292, 0), (RT, -0.118, 0),
         (RT - 0.018, -0.10, 0), (RR, -0.10, 0), (1.30, -0.10, 0)]
    ob = C.lathe("RingGear", P, [steel], steps=NT * 8, mod=gear_mod)
    C.add_bevel(ob, 0.003, segments=1, angle=40)
    return C.finalize(ob, angle=40)


def primary(press, mach):
    # pressed cup wrapping the arc springs; lip just behind the secondary mass
    P = [(0.12, -0.37, 0), (1.25, -0.37, 0), (1.30, -0.355, 0), (1.325, -0.32, 0), (1.33, -0.10, 0),
         (1.335, 0.02, 0), (1.33, 0.07, 0), (1.31, 0.08, 0), (1.29, 0.07, 0), (1.29, -0.02, 0),
         (0.40, -0.05, 0), (0.40, 0.00, 0), (0.12, 0.00, 0)]
    ob = C.lathe("Primary", P, [press], steps=256)
    # crankshaft bolt holes in the hub
    bm = bmesh.new()
    for k in range(8):
        th = math.tau * k / 8 + math.pi / 8
        M = Matrix.Translation((0.255 * math.cos(th), 0.255 * math.sin(th), 0))
        C.cyl_bm(bm, 0.048, -0.5, 0.2, seg=28, matrix=M)
    cut = C.mesh_obj("CrankHoles", bm, [press])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out = [C.finalize(ob, angle=35, remove=[cut])]
    # pilot bearing: machined outer race + dark seal
    P = [(0.10, -0.02, 0), (0.165, -0.02, 0), (0.165, 0.065, 0), (0.155, 0.075, 0), (0.10, 0.075, 0)]
    out.append(C.finalize(C.lathe("BearingRace", P, [mach], steps=96), angle=40))
    return out


def secondary(cast, face, ring_m):
    P = [(0.40, 0.02, 0), (0.40, 0.17, 0), (0.42, 0.195, 0), (0.70, 0.205, 0), (0.725, 0.23, 0),
         (0.745, 0.262, 1), (1.175, 0.262, 0), (1.19, 0.275, 0), (1.20, 0.30, 2), (1.285, 0.30, 0),
         (1.30, 0.285, 0), (1.30, 0.04, 0), (1.27, 0.02, 0)]
    ob = C.lathe("Secondary", P, [cast, face, ring_m], steps=320)
    bm = bmesh.new()
    # ventilation windows in the inner zone
    for k in range(8):
        th = math.tau * k / 8
        M = Matrix.Translation((0.58 * math.cos(th), 0.58 * math.sin(th), 0))
        C.cyl_bm(bm, 0.075, -0.2, 0.5, seg=36, matrix=M)
    # threaded holes for the clutch cover
    for k in range(6):
        th = math.tau * k / 6 + 0.25
        M = Matrix.Translation((1.245 * math.cos(th), 1.245 * math.sin(th), 0))
        C.cyl_bm(bm, 0.028, 0.1, 0.5, seg=20, matrix=M)
        C.cyl_bm(bm, 0.028, 0.285, 0.31, seg=20, matrix=M, r1=0.04)   # countersink
    cut = C.mesh_obj("SecHoles", bm, [cast])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.005, segments=2, angle=35)
    out = [C.finalize(ob, angle=35, remove=[cut])]
    return out


def hardware(steel, dark):
    out = []
    bm = bmesh.new()
    # dowel pins on the mounting ring
    for k in range(3):
        th = math.tau * k / 3 + 0.25 + math.tau / 12
        M = Matrix.Translation((1.245 * math.cos(th), 1.245 * math.sin(th), 0))
        C.cyl_bm(bm, 0.024, 0.29, 0.36, seg=20, matrix=M)
        C.cyl_bm(bm, 0.024, 0.36, 0.368, seg=20, matrix=M, r1=0.018)
    pins = C.mesh_obj("Dowels", bm, [steel])
    out.append(C.finalize(pins, angle=40))
    # rivet heads holding the hub flange
    bm = bmesh.new()
    for k in range(8):
        th = math.tau * k / 8 + math.pi / 8
        M = Matrix.Translation((0.58 * math.cos(th), 0.58 * math.sin(th), 0.20))
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=0.034,
                                  matrix=M @ Matrix.Diagonal((1, 1, 0.45, 1)))
    rv = C.mesh_obj("Rivets", bm, [dark])
    for f in rv.data.polygons:
        f.use_smooth = True
    out.append(rv)
    # crank bolt sight: darker bores behind the hub holes are just the void; add an inner
    # hub disc deep inside so the holes do not show the background through the part
    P = [(0.0, -0.36, 0), (0.42, -0.36, 0), (0.42, -0.33, 0), (0.0, -0.33, 0)]
    out.append(C.finalize(C.lathe("HubBack", P, [dark], steps=64), angle=40))
    return out


def mat_friction():
    """Turned steel friction face: fine turning grooves (bump), irregular concentric
    sheen bands (colour + roughness), faint heat blotches from clutch use."""
    m = C.principled("FrictionFace", (0.36, 0.36, 0.365), metallic=1.0, rough=0.26)
    C.add_radial_aniso(m, 0.9, "Z", rings_scale=900.0, ring_strength=0.10)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bands = nt.nodes.new("ShaderNodeTexWave")
    bands.wave_type = "RINGS"
    bands.rings_direction = "Z"
    bands.inputs["Scale"].default_value = 22.0
    bands.inputs["Distortion"].default_value = 3.0
    bands.inputs["Detail"].default_value = 3.0
    bands.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(C._coord(nt), bands.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 5.0
    heat = nt.nodes.new("ShaderNodeMapRange")
    heat.inputs["From Min"].default_value = 0.5
    heat.inputs["From Max"].default_value = 0.75
    heat.inputs["To Max"].default_value = 0.4
    nt.links.new(nz.outputs["Fac"], heat.inputs["Value"])
    c1 = nt.nodes.new("ShaderNodeMix")
    c1.data_type = "RGBA"
    nt.links.new(bands.outputs["Fac"], c1.inputs["Factor"])
    c1.inputs["A"].default_value = (0.27, 0.27, 0.275, 1)
    c1.inputs["B"].default_value = (0.42, 0.42, 0.425, 1)
    c2 = nt.nodes.new("ShaderNodeMix")
    c2.data_type = "RGBA"
    nt.links.new(heat.outputs["Result"], c2.inputs["Factor"])
    nt.links.new(c1.outputs["Result"], c2.inputs["A"])
    c2.inputs["B"].default_value = (0.30, 0.27, 0.24, 1)
    nt.links.new(c2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.34
    rr.inputs["To Max"].default_value = 0.18
    nt.links.new(bands.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def build():
    cast = C.mat_cast_iron("SecondaryIron", rust=0.25, base=0.20)
    face = mat_friction()
    ring_m = C.mat_machined("MountRing", color=0.40, rough=0.32, rings=700)
    press = C.mat_cast_iron("PressedSteel", rust=0.45, base=0.09)
    gear = C.principled("GearSteel", (0.36, 0.36, 0.365), metallic=1.0, rough=0.34)
    C.add_noise_bump(gear, scale=500, strength=0.06, distance=0.0006, rough_var=0.08)
    mach = C.mat_machined("Bearing", color=0.60, rough=0.18, rings=1200)
    steel = C.principled("PinSteel", (0.62, 0.62, 0.63), metallic=1.0, rough=0.24)
    dark = C.principled("DarkSteel", (0.07, 0.07, 0.075), metallic=0.9, rough=0.45)
    C.add_noise_bump(dark, scale=600, strength=0.05, distance=0.0005)
    objs = [ring_gear(gear)] + primary(press, mach) + secondary(cast, face, ring_m) + hardware(steel, dark)
    # stand it up: friction face toward the camera and a little upward
    C.transform_all(objs, Matrix.Rotation(math.radians(-18), 4, "Z") @ Matrix.Rotation(math.radians(68), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("volano", objs, "volano.py",
            "dual-mass flywheel: steel starter ring gear, machined clutch friction face, "
            "mounting ring with threaded holes and dowels, crankshaft bolt holes in the hub",
            az=20, el=16, lens=70, fill=0.84, samples=S, res=(R, R))
