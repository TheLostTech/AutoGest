"""Rear brake disc (disco freno posteriore) as removed from a small car: solid (non-vented)
cast-iron disc with integrated tall hat; the hat is a drum-in-hat, its machined bore being
the drum for the parking-brake shoes (open towards the back). Machined friction ring with
turning marks and light rust bloom at the rim, dark cast hat and edge with surface rust,
4 wheel-bolt holes, centre bore and a small locating-screw hole. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from pinza import mat_rusty_iron

RO = 1.25        # outer radius (250 mm disc)
RF = 0.86        # inner edge of the friction ring
T = 0.10         # disc thickness (10 mm, solid)
RH = 0.80        # hat outer radius (drum-in-hat)
RD = 0.755       # drum bore radius (151 mm drum)
H = 0.56         # hat height above the inner friction face
RB = 0.30        # centre bore
PCD = 0.50       # 4 x 100 bolt circle radius


def disc(iron, ring, drum):
    c = 0.008
    P = [
        (RB, H - 0.012, 0), (RB + 0.012, H, 0),               # centre bore chamfer
        (RH - 0.035, H, 0), (RH - 0.012, H - 0.008, 0),        # hub face (machined below)
        (RH, H - 0.035, 0),
        (RH, T + 0.05, 0), (RH + 0.012, T + 0.025, 0),         # hat wall -> fillet
        (RF - 0.03, T + 0.012, 0), (RF - 0.02, T, 0),          # undercut groove
        (RF, T, 1), (RO - 0.045, T, 0), (RO - 0.04, T + 0.004, 0),   # outer friction face + unworn lip
        (RO - c, T + 0.004, 0), (RO, T - c, 0),
        (RO, c, 0), (RO - c, -0.004, 0), (RO - 0.04, -0.004, 0),     # rim
        (RO - 0.045, 0.0, 1), (RF, 0.0, 0),                          # inner friction face
        (RD + 0.03, 0.0, 0), (RD, -0.012, 2),                  # drum mouth chamfer
        (RD, H - 0.10, 0),                                     # machined drum bore
        (RD - 0.03, H - 0.07, 0), (RB + 0.05, H - 0.07, 0),    # inside of hub face
        (RB, H - 0.09, 0),
    ]
    ob = C.lathe("Disc", P, [iron, ring, drum], steps=220)
    # machined hub face (separate material via a thin cap cut)
    cb = bmesh.new()
    for k in range(4):
        th = math.radians(45 + 90 * k)
        M = Matrix.Translation((PCD * math.cos(th), PCD * math.sin(th), 0))
        C.cyl_bm(cb, 0.068, H - 0.3, H + 0.2, seg=40, matrix=M)
    th = math.radians(0)
    M = Matrix.Translation((0.40 * math.cos(th), 0.40 * math.sin(th), 0))
    C.cyl_bm(cb, 0.032, H - 0.3, H + 0.2, seg=24, matrix=M)
    cut = C.mesh_obj("Holes", cb, [iron])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    hb = bmesh.new()
    C.cyl_bm(hb, RH - 0.05, H - 0.006, H + 0.2, seg=160)
    hub = C.mesh_obj("HubFace", hb, [drum])
    cc = bmesh.new()
    C.cyl_bm(cc, RB + 0.06, H - 0.1, H + 0.3, seg=96)
    hub_in = C.mesh_obj("HubIn", cc, [drum])
    m2 = C.add_boolean(hub, hub_in)
    m2.use_self = True
    # cut the hub face lightly so the machined material is transferred
    m3 = C.add_boolean(ob, hub)
    m3.use_self = True
    m3.use_hole_tolerant = True
    C.add_bevel(ob, 0.006, segments=2, angle=40)
    ob = C.finalize(ob, angle=38, remove=[cut, hub, hub_in])
    return [ob]


def build():
    iron = mat_rusty_iron("HatIron", base=0.075, rust=0.55, scale=4.0, seed=2.0)
    ring = C.mat_machined("FrictionRing", color=0.26, rough=0.34, rings=1100)
    drum = C.mat_machined("HubMachined", color=0.36, rough=0.28, rings=500)
    # light rust bloom on the friction ring: mix brown in by noise near the rim
    nt = ring.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 12.0
    nz.inputs["Roughness"].default_value = 0.7
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.62
    mr.inputs["From Max"].default_value = 0.82
    mr.inputs["To Max"].default_value = 0.40
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.26, 0.26, 0.265, 1)
    mix.inputs["B"].default_value = (0.11, 0.045, 0.018, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.34
    rr.inputs["To Max"].default_value = 0.75
    nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    mt = nt.nodes.new("ShaderNodeMapRange")
    mt.inputs["To Min"].default_value = 1.0
    mt.inputs["To Max"].default_value = 0.2
    nt.links.new(mr.outputs["Result"], mt.inputs["Value"])
    nt.links.new(mt.outputs["Result"], b.inputs["Metallic"])
    objs = disc(iron, ring, drum)
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("disco-posteriore", objs, "disco-posteriore.py",
            "rear brake disc: solid non-vented cast-iron disc with tall drum-in-hat, machined friction ring, 4 bolt holes",
            az=-34, el=18, lens=70, fill=0.80,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
