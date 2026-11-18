"""Cylinder head of a small inline-4 (DOHC, 16 valves) as removed from the car:
cast-aluminium head with machined head-gasket face (deck), open cam carrier on top
with two camshafts (lobes, bearing towers and bolted caps), machined cam-cover
gasket rail, four central spark-plug wells, head-bolt heads, exhaust ports with
studs on a machined flange (front side), intake ports on the back, cam seals and
hubs on the timing end, thermostat/water outlet on the opposite end.

Crank axis along X (timing end +X), exhaust side -Y, intake +Y, Z up.
1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # local Z -> world +X
RXm = Matrix.Rotation(math.pi / 2, 4, "X")      # local Z -> world -Y
CYL_X = (-1.35, -0.45, 0.45, 1.35)
JRN_X = (-1.80, -0.90, 0.0, 0.90, 1.80)
L, W = 4.30, 2.00
ZD = 1.04          # top deck
ZC = 1.42          # cam centre
CAM_Y = (-0.46, 0.46)


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


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), raw=False):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    if raw:
        return ob
    for c in cutters:
        C.add_boolean(ob, c).use_self = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40):
    ob = C.lathe(name, prof, [mat], steps=steps)
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


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    """Sand/die-cast aluminium: mottled tone, grime in cavities (AO), bright worn edges."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.35
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
    em = C.edge_mask(nt, 0.02, 4.0)
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
    bp.inputs["Strength"].default_value = 0.18
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def flat_machined(name, color=0.60, rough=0.26, axis="Z", scale=6.0):
    """Fly-cut face: anisotropic metal with faint arc marks."""
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.5, axis, rings_scale=scale, ring_strength=0.03)
    C.add_noise_bump(m, scale=300, strength=0.03, distance=0.001)
    return m


# ----------------------------------------------------------------- parts
def head_body(alu, deck_m, flange_m, port_m):
    out = []

    def fill(bm):
        C.box_bm(bm, L, W - 0.04, ZD - 0.10, center=(0, 0, 0.10 + (ZD - 0.10) / 2))
        # cast ribs/bulges on the flanks between the ports
        for s in (-1, 1):
            for x in (-2.0, -0.9, 0.0, 0.9, 2.0):
                C.box_bm(bm, 0.16, 0.08, ZD - 0.18, center=(x, s * (W / 2 - 0.02), 0.10 + (ZD - 0.10) / 2 + 0.02))
            C.box_bm(bm, L - 0.40, 0.06, 0.12, center=(0, s * (W / 2 - 0.01), 0.20))
    # port cutters (exhaust -Y, intake +Y)
    cb = bmesh.new()
    for x in CYL_X:
        prism_bm(cb, rrect(0.46, 0.34, 0.14), -0.05, 0.62, Matrix.Translation((x, -W / 2 - 0.12, 0.60)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        prism_bm(cb, rrect(0.40, 0.48, 0.17), -0.05, 0.62, Matrix.Translation((x, W / 2 + 0.12, 0.62)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    C.fix_normals(cb)
    pc = C.mesh_obj("PortCut", cb, [port_m])
    bm2 = bmesh.new()
    fill(bm2)
    # machined manifold flanges
    C.box_bm(bm2, L - 0.50, 0.08, 0.50, center=(0, -W / 2 - 0.02, 0.60), mat=1)
    C.box_bm(bm2, L - 0.30, 0.08, 0.72, center=(0, W / 2 + 0.02, 0.62), mat=1)
    C.fix_normals(bm2)
    ob = C.mesh_obj("Head", bm2, [alu, flange_m])
    C.add_boolean(ob, pc).use_self = True
    C.add_bevel(ob, 0.025, segments=2, angle=30)
    out.append(C.finalize(ob, angle=30, remove=[pc]))
    # machined deck (head gasket face) slab
    out.append(solid("Deck", lambda bm: C.box_bm(bm, L, W, 0.10, center=(0, 0, 0.05)), [deck_m], bevel=0.012))
    return out


def top_rail(alu, rail_m):
    out = []

    def fill(bm):
        h = 0.36
        zc = ZD + h / 2
        C.box_bm(bm, L, 0.16, h, center=(0, -(W / 2 - 0.08), zc))
        C.box_bm(bm, L, 0.16, h, center=(0, (W / 2 - 0.08), zc))
        C.box_bm(bm, 0.16, W - 0.30, h, center=(-(L / 2 - 0.08), 0, zc))
        C.box_bm(bm, 0.16, W - 0.30, h, center=((L / 2 - 0.08), 0, zc))
        # cover-bolt bosses on the inside of the rail
        for x in (-1.35, 1.35):
            for s in (-1, 1):
                C.box_bm(bm, 0.18, 0.10, h, center=(x, s * (W / 2 - 0.19), zc))
        # half-round cam bosses on the timing end
        for y in CAM_Y:
            C.cyl_bm(bm, 0.21, L / 2 - 0.16, L / 2 + 0.04, seg=40, matrix=Matrix.Translation((0, y, ZC)) @ RY)
    out.append(solid("Rail", fill, [alu], bevel=0.02))
    # machined gasket strip on top of the rail
    def strip(bm):
        zz = ZD + 0.36 + 0.012
        C.box_bm(bm, L, 0.16, 0.024, center=(0, -(W / 2 - 0.08), zz))
        C.box_bm(bm, L, 0.16, 0.024, center=(0, (W / 2 - 0.08), zz))
        C.box_bm(bm, 0.16, W - 0.32, 0.024, center=(-(L / 2 - 0.08), 0, zz))
        C.box_bm(bm, 0.16, W - 0.32, 0.024, center=((L / 2 - 0.08), 0, zz))
    holes = bmesh.new()
    zz = ZD + 0.36
    for x in (-2.07, -1.0, 0.0, 1.0, 2.07):
        for s in (-1, 1):
            C.cyl_bm(holes, 0.035, zz - 0.2, zz + 0.1, seg=20, matrix=Matrix.Translation((x, s * (W / 2 - 0.08), 0)))
    hc = C.mesh_obj("RailHoles", holes, [rail_m])
    bm = bmesh.new(); strip(bm); C.fix_normals(bm)
    st = C.mesh_obj("RailTop", bm, [rail_m])
    C.add_boolean(st, hc).use_self = True
    C.add_bevel(st, 0.006, segments=1, angle=30)
    out.append(C.finalize(st, angle=30, remove=[hc]))
    return out


def lobe_sec(phase, base=0.155, lift=0.085, n=48):
    pts = []
    for k in range(n):
        t = math.tau * k / n
        c = math.cos(t - phase)
        r = base + lift * (max(0.0, c) ** 2.2)
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


def camshaft(y, steel, cast, alu, bolt, idx):
    out = []
    M = Matrix.Translation((0, y, ZC)) @ RY      # local z == world x
    # shaft with journals
    P = [(0.0, -2.02, 0), (0.09, -2.02, 0), (0.095, -2.0, 0), (0.095, L / 2 + 0.10, 0), (0.0, L / 2 + 0.10, 0)]
    out.append(lathe_at("CamShaft", P, steel, M, steps=48, angle=40))
    # lobes (2 per cylinder for this cam)
    order = (0.0, math.pi, math.pi * 1.5, math.pi * 0.5)
    def lobes(bm):
        for i, x in enumerate(CYL_X):
            ph = order[i] + (0.6 if idx else 0.0)
            for dx in (-0.17, 0.17):
                prism_bm(bm, lobe_sec(ph), x + dx - 0.07, x + dx + 0.07, M)
    out.append(solid("Lobes", lobes, [cast], bevel=0.01, angle=40))
    # bearing towers + caps with bolts
    def towers(bm):
        for x in JRN_X:
            C.box_bm(bm, 0.24, 0.42, ZC - ZD, center=(x, y, ZD + (ZC - ZD) / 2))
    out.append(solid("Towers", towers, [alu], bevel=0.02))
    def caps(bm):
        for x in JRN_X:
            C.box_bm(bm, 0.22, 0.42, 0.17, center=(x, y, ZC + 0.085))
            C.cyl_bm(bm, 0.115, -0.11, 0.11, seg=32, matrix=Matrix.Translation((x, y, ZC + 0.02)) @ RY)
    out.append(solid("Caps", caps, [cast], bevel=0.02))
    for x in JRN_X:
        for dy in (-0.15, 0.15):
            out.append(hex_at("CapBolt", 0.045, ZC + 0.17, ZC + 0.23, bolt, Matrix.Translation((x, y + dy, 0))))
            out.append(lathe_at("Washer", [(0.0, ZC + 0.168, 0), (0.06, ZC + 0.168, 0), (0.06, ZC + 0.18, 0), (0.0, ZC + 0.18, 0)],
                                bolt, Matrix.Translation((x, y + dy, 0)), steps=24))
    # cam seal + hub on the timing end
    xe = L / 2 + 0.04
    out.append(lathe_at("Seal", [(0.09, 0.0, 0), (0.15, 0.0, 0), (0.15, 0.03, 0), (0.09, 0.03, 0)],
                        C.mat_rubber("SealRubber"), Matrix.Translation((xe, y, ZC)) @ RY, steps=48))
    return out


def plug_wells(alu, dark):
    out = []
    for x in CYL_X:
        P = [(0.0, ZD + 0.05, 1), (0.10, ZD + 0.05, 0), (0.10, ZD + 0.33, 0), (0.12, ZD + 0.36, 0), (0.15, ZD + 0.36, 0),
             (0.17, ZD + 0.33, 0), (0.17, ZD - 0.02, 0), (0.0, ZD - 0.02, 0)]
        ob = C.lathe("PlugWell", P, [alu, dark], steps=48)
        ob.matrix_world = Matrix.Translation((x, 0, 0))
        out.append(C.finalize(ob, angle=40))
    return out


def head_bolts(bolt):
    out = []
    for x in JRN_X:
        for s in (-1, 1):
            M = Matrix.Translation((x + (0.0 if abs(x) < 2 else 0), s * 0.76, 0))
            out.append(lathe_at("HBWasher", [(0.0, ZD - 0.01, 0), (0.085, ZD - 0.01, 0), (0.085, ZD + 0.02, 0), (0.0, ZD + 0.02, 0)], bolt, M, steps=32))
            # 12-point-ish head: two hexes rotated
            out.append(hex_at("HBHead", 0.06, ZD + 0.02, ZD + 0.11, bolt, M))
            out.append(hex_at("HBHead2", 0.06, ZD + 0.02, ZD + 0.11, bolt, M @ Matrix.Rotation(math.pi / 6, 4, "Z")))
    return out


def studs(steel):
    out = []
    y = -W / 2 - 0.06
    pos = [(-2.0, 0.60), (-0.9, 0.98), (-0.9, 0.24), (0.0, 0.98), (0.0, 0.24), (0.9, 0.98), (0.9, 0.24), (2.0, 0.60)]
    for (x, z) in pos:
        M = Matrix.Translation((x, y, z)) @ RXm
        P = [(0.0, 0.0, 0), (0.05, 0.0, 0), (0.05, 0.20, 0), (0.038, 0.22, 0), (0.0, 0.22, 0)]
        ob = C.lathe("Stud", P, [steel], steps=24)
        ob.matrix_world = M
        out.append(C.finalize(ob, angle=40))
    # intake side bolt holes are part of the flange; add threaded inserts look
    return out


def thermostat(alu, bolt):
    out = []
    M = Matrix.Translation((-L / 2, 0.35, 0.72)) @ Matrix.Rotation(-math.pi / 2, 4, "Y")   # local z -> -X
    P = [(0.0, -0.05, 0), (0.30, -0.05, 0), (0.30, 0.06, 0), (0.22, 0.10, 0), (0.17, 0.22, 0), (0.17, 0.40, 0),
         (0.19, 0.42, 0), (0.19, 0.46, 0), (0.14, 0.48, 0), (0.12, 0.48, 0), (0.12, 0.30, 0), (0.0, 0.30, 0)]
    out.append(lathe_at("Outlet", P, alu, M, steps=48, bevel=0.006))
    for k in range(3):
        th = math.tau * k / 3 + 0.4
        Mb = M @ Matrix.Translation((0.30 * math.cos(th), 0.30 * math.sin(th), 0))
        out.append(lathe_at("OBoss", [(0.0, -0.05, 0), (0.07, -0.05, 0), (0.07, 0.07, 0), (0.0, 0.07, 0)], alu, Mb, steps=24))
        out.append(hex_at("OBolt", 0.045, 0.07, 0.13, bolt, Mb))
    # lifting eye
    def eye(bm):
        C.box_bm(bm, 0.06, 0.34, 0.40, center=(-L / 2 + 0.05, -0.55, ZD + 0.16))
    out.append(solid("LiftEye", eye, [alu], bevel=0.02))
    # timing-end face: cast ribs, water passage boss, cam position sensor
    def ribs(bm):
        for y in (-0.62, 0.0, 0.62):
            C.box_bm(bm, 0.08, 0.10, ZD - 0.20, center=(L / 2 + 0.03, y, 0.10 + (ZD - 0.20) / 2 + 0.02))
        C.box_bm(bm, 0.08, W - 0.30, 0.10, center=(L / 2 + 0.03, 0, 0.28))
        C.cyl_bm(bm, 0.16, L / 2, L / 2 + 0.10, seg=32, matrix=Matrix.Translation((0, -0.32, 0.62)) @ RY)
    out.append(solid("EndRibs", ribs, [alu], bevel=0.02))
    blk = C.mat_black_plastic("SensorPA", rough=0.45, color=0.025)
    Ms = Matrix.Translation((L / 2 + 0.03, 0.42, 0.66)) @ RY
    out.append(lathe_at("SensorBody", [(0.0, 0.0, 0), (0.11, 0.0, 0), (0.11, 0.10, 0), (0.08, 0.13, 0), (0.0, 0.13, 0)], blk, Ms, steps=32))
    def conn(bm):
        C.box_bm(bm, 0.16, 0.18, 0.26, center=(L / 2 + 0.14, 0.42, 0.85))
    out.append(solid("SensorConn", conn, [blk], bevel=0.015))
    out.append(hex_at("PassPlug", 0.08, 0.10, 0.16, bolt, Matrix.Translation((L / 2, -0.32, 0.62)) @ RY))
    return out


def build():
    alu = cast_alu("HeadAlu", base=0.27, rough=0.58, grime=0.85, grain=150.0, wear=0.25)
    deck = flat_machined("DeckFace", 0.50, 0.28, "Z", 3.0)
    flange = flat_machined("PortFlange", 0.36, 0.42, "Y", 5.0)
    port = C.principled("PortSoot", (0.06, 0.055, 0.05), metallic=0.4, rough=0.75)
    C.add_noise_bump(port, scale=120, strength=0.2, distance=0.003)
    rail = flat_machined("RailFace", 0.50, 0.28, "Z", 4.0)
    steel = C.mat_machined("CamSteel", color=0.45, rough=0.22, rings=300)
    lobe = C.principled("LobeSteel", (0.42, 0.42, 0.43), metallic=1.0, rough=0.26)
    C.add_noise_bump(lobe, scale=200, strength=0.03, distance=0.001)
    cap = cast_alu("CapAlu", base=0.36, rough=0.48, grime=0.6, grain=170.0, wear=0.2)
    bolt = C.principled("BoltSteel", (0.30, 0.30, 0.31), metallic=1.0, rough=0.35)
    C.add_noise_bump(bolt, scale=300, strength=0.05, distance=0.001)
    stud = C.principled("StudZinc", (0.62, 0.60, 0.52), metallic=1.0, rough=0.3)
    dark = C.principled("WellDark", (0.02, 0.02, 0.02), rough=0.8)
    objs = head_body(alu, deck, flange, port) + top_rail(alu, rail)
    for i, y in enumerate(CAM_Y):
        objs += camshaft(y, steel, lobe, alu, bolt, i)
    objs += plug_wells(alu, dark) + head_bolts(bolt) + studs(stud) + thermostat(alu, bolt)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("testata", objs, "testata.py",
            "inline-4 DOHC cylinder head: cast aluminium, machined gasket face, open cam carrier with two camshafts, spark-plug wells, exhaust ports with studs",
            az=22, el=34, lens=70, fill=0.86, **kw)
