"""A/C compressor (compressore aria condizionata): ribbed cast-aluminium cylindrical body
with rear head and joint flange, four mounting ears with bolt holes parallel to the shaft,
electromagnetic clutch with poly-V pulley and riveted armature plate on the front,
suction/discharge port block on top with two fittings and studs, pressure-relief valve,
and the clutch-coil lead running back to a small black connector."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RB = 0.46          # body radius
ZP0 = 1.10         # pulley back face


def mat_cast_alu(name, base=0.45, rough=0.45, grain=480.0, wear=0.35):
    """Die-cast aluminium: mottled tone, sand-cast grain, brighter worn edges."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 5.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.84, base * 0.84, base * 0.82, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.05, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.78, 0.78, 0.78, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.07
    rr.inputs["To Max"].default_value = rough - 0.07
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    rmix = nt.nodes.new("ShaderNodeMix")
    nt.links.new(wmul.outputs[0], rmix.inputs["Factor"])
    nt.links.new(rr.outputs["Result"], rmix.inputs["A"])
    rmix.inputs["B"].default_value = 0.22
    nt.links.new(rmix.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def rib(r, z, t):
    """shallow longitudinal ribs on the cylindrical body only"""
    if r < RB - 0.005 or not (0.24 < z < 0.90):
        return r
    env = C.smoothstep(0.24, 0.30, z) * (1 - C.smoothstep(0.84, 0.90, z))
    v = math.cos(18 * t)
    sq = max(-1.0, min(1.0, (v - 0.55) * 6.0)) * 0.5 + 0.5
    return r + 0.026 * sq * env


def at_angle(th, r, z=0.0):
    """matrix placing a local +Y-pointing feature at polar angle th, radius r."""
    return Matrix.Rotation(th - math.pi / 2, 4, "Z") @ Matrix.Translation((0, r, z))


# ----------------------------------------------------------------- body
def body(alu):
    P = [(0.0, -0.02, 0), (0.30, -0.02, 0), (0.40, 0.0, 0), (0.455, 0.04, 0), (0.47, 0.09, 0), (0.47, 0.17, 0),
         (0.495, 0.175, 0), (0.495, 0.215, 0), (RB, 0.22, 0), (RB, 0.25, 0), (RB, 0.30, 0), (RB, 0.84, 0), (RB, 0.89, 0), (RB, 0.92, 0),
         (0.49, 0.925, 0), (0.49, 0.965, 0), (0.45, 0.975, 0), (0.40, 1.03, 0), (0.34, 1.07, 0),
         (0.30, 1.10, 0), (0.20, 1.10, 0), (0.0, 1.10, 0)]
    ob = C.lathe("Body", P, [alu], steps=264, mod=rib)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out = [C.finalize(ob, angle=35)]
    # rear cover through-bolts heads on the joint flange
    bm = bmesh.new()
    for k in range(6):
        th = math.tau * k / 6 + 0.3
        M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.47, 0, 0))
        C.cyl_bm(bm, 0.036, 0.215, 0.245, seg=6, matrix=M)
        C.cyl_bm(bm, 0.036, 0.895, 0.925, seg=6, matrix=M)
    bo = C.mesh_obj("FlangeBolts", bm, [alu])
    C.add_bevel(bo, 0.006, segments=1, angle=30)
    out.append(C.finalize(bo, angle=35))
    return out


def ears(alu, steel):
    out = []
    # (polar angle, z0, z1)
    specs = [(math.radians(-36), 0.76, 1.00), (math.radians(-36), 0.10, 0.34),
             (math.radians(144), 0.76, 1.00), (math.radians(144), 0.10, 0.34)]
    for th, z0, z1 in specs:
        Rz = Matrix.Rotation(th - math.pi / 2, 4, "Z")
        bm = bmesh.new()
        C.box_bm(bm, 0.12, 0.24, z1 - z0 - 0.03, center=(0, 0.47, (z0 + z1) / 2), matrix=Rz)
        a = C.mesh_obj("EarArm", bm, [alu])
        C.add_bevel(a, 0.012, segments=2, angle=30)
        out.append(C.finalize(a, angle=35))
        boss = C.lathe("EarBoss", [(0.040, z0, 0), (0.064, z0, 0), (0.072, z0 + 0.01, 0), (0.072, z1 - 0.01, 0),
                                    (0.064, z1, 0), (0.040, z1, 0)], [alu], steps=56)
        boss.matrix_world = Rz @ Matrix.Translation((0, 0.60, 0))
        C.add_bevel(boss, 0.006, segments=2, angle=30)
        out.append(C.finalize(boss, angle=35))
        sl = C.lathe("EarSleeve", [(0.034, z0 - 0.006, 0), (0.042, z0 - 0.006, 0), (0.042, z1 + 0.006, 0), (0.034, z1 + 0.006, 0)], [steel], steps=40)
        sl.matrix_world = Rz @ Matrix.Translation((0, 0.60, 0))
        out.append(C.finalize(sl, angle=40))
    return out


def ports(alu, port_m, steel, black):
    out = []
    # block on top (local +Y) toward the rear
    bm = bmesh.new()
    C.box_bm(bm, 0.46, 0.20, 0.34, center=(0, 0.47, 0.30))
    blk = C.mesh_obj("PortBlock", bm, [alu])
    C.add_bevel(blk, 0.03, segments=3, angle=30)
    out.append(C.finalize(blk, angle=35))
    top = 0.57
    up = Matrix.Rotation(math.radians(-90), 4, "X")     # local Z -> +Y
    for (x, z, r) in ((-0.11, 0.30, 0.062), (0.12, 0.30, 0.050)):
        T = Matrix.Translation((x, 0, z)) @ up
        # round pad, port spigot with o-ring groove, plastic dust cap
        P = [(0.0, top - 0.01, 0), (r + 0.045, top - 0.01, 0), (r + 0.045, top + 0.03, 0), (r + 0.035, top + 0.04, 0),
             (r + 0.004, top + 0.04, 0), (r + 0.004, top + 0.065, 0), (r - 0.006, top + 0.07, 0), (r - 0.006, top + 0.08, 0),
             (r + 0.004, top + 0.085, 0), (r + 0.004, top + 0.11, 0), (r - 0.014, top + 0.11, 0), (r - 0.014, top + 0.09, 0), (0.0, top + 0.09, 0)]
        sp = C.lathe("Port", P, [port_m], steps=64)
        sp.matrix_world = T
        C.add_bevel(sp, 0.003, segments=1, angle=40)
        out.append(C.finalize(sp, angle=40))
        cap = C.lathe("Cap", [(0.0, top + 0.17, 0), (r + 0.012, top + 0.17, 0), (r + 0.018, top + 0.16, 0),
                              (r + 0.018, top + 0.085, 0), (r + 0.006, top + 0.08, 0), (0.0, top + 0.08, 0)], [black], steps=48)
        cap.matrix_world = T
        C.add_bevel(cap, 0.004, segments=2, angle=30)
        out.append(C.finalize(cap, angle=40))
    # studs with nuts between the ports
    for (x, z) in ((0.0, 0.18), (0.0, 0.42)):
        T = Matrix.Translation((x, 0, z)) @ up
        st = C.lathe("Stud", [(0.0, top - 0.01, 0), (0.016, top - 0.01, 0), (0.016, top + 0.09, 0), (0.012, top + 0.095, 0), (0.0, top + 0.095, 0)], [steel], steps=24)
        st.matrix_world = T
        out.append(C.finalize(st, angle=40))
        bm = bmesh.new()
        C.cyl_bm(bm, 0.034, top, top + 0.03, seg=6)
        nt = C.mesh_obj("StudNut", bm, [steel])
        nt.matrix_world = T
        C.add_bevel(nt, 0.004, segments=1, angle=30)
        out.append(C.finalize(nt, angle=35))
    return out


def relief_valve(steel, alu):
    out = []
    th = math.radians(150)
    T = at_angle(th, 0.0, 0.0)
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.10, 0.16, center=(0, RB + 0.03, 0.10), matrix=T)
    bs = C.mesh_obj("ValveBoss", bm, [alu])
    C.add_bevel(bs, 0.02, segments=2, angle=30)
    out.append(C.finalize(bs, angle=35))
    bm = bmesh.new()
    M = T @ Matrix.Translation((0, RB + 0.08, 0.10)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    C.cyl_bm(bm, 0.045, 0.0, 0.05, seg=6, matrix=M)
    C.cyl_bm(bm, 0.030, 0.05, 0.075, seg=24, matrix=M)
    vv = C.mesh_obj("Valve", bm, [steel])
    C.add_bevel(vv, 0.004, segments=1, angle=30)
    out.append(C.finalize(vv, angle=35))
    return out


# ----------------------------------------------------------------- clutch + pulley
def pulley(steel):
    z = ZP0
    P = [(0.29, z, 0), (0.40, z, 0), (0.41, z + 0.01, 0)]
    z += 0.025
    for i in range(6):
        P += [(0.385, z, 0), (0.408, z + 0.012, 0)]
        z += 0.024
    P += [(0.385, z, 0), (0.41, z + 0.012, 0), (0.41, z + 0.03, 0), (0.40, z + 0.04, 0),
          (0.24, z + 0.04, 0), (0.23, z + 0.03, 0), (0.23, z - 0.01, 0), (0.29, ZP0 + 0.02, 0)]
    ob = C.lathe("Pulley", P, [steel], steps=200)
    # banana slots (magnetic pole windows) in the pulley face
    bm = bmesh.new()
    zf = z + 0.04
    for ring, (rr, n, ph) in enumerate(((0.355, 6, 0.0), (0.275, 6, 0.5))):
        for k in range(n):
            th0 = math.tau * (k + ph) / n
            for j in range(5):
                th = th0 + j * 0.11
                M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((rr, 0, zf))
                C.box_bm(bm, 0.022, 0.06, 0.03, matrix=M)
    cut = C.mesh_obj("Slots", bm, [steel])
    bo = C.add_boolean(ob, cut)
    bo.use_self = True
    C.add_bevel(ob, 0.0025, segments=1, angle=40)
    return [C.finalize(ob, angle=40, remove=[cut])], zf


def clutch(steel, spider_m, dark, zf):
    out = []
    # armature plate with riveted leaf-spring hub
    P = [(0.07, zf + 0.008, 0), (0.30, zf + 0.008, 0), (0.31, zf + 0.018, 0), (0.31, zf + 0.032, 0),
         (0.30, zf + 0.04, 0), (0.07, zf + 0.04, 0)]
    ap = C.lathe("Armature", P, [steel], steps=160)
    C.add_bevel(ap, 0.002, segments=1, angle=40)
    out.append(C.finalize(ap, angle=40))
    # 3-arm spider hub
    bm = bmesh.new()
    C.cyl_bm(bm, 0.12, zf + 0.04, zf + 0.06, seg=48)
    for k in range(3):
        th = math.tau * k / 3
        M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((0.16, 0, zf + 0.05))
        C.box_bm(bm, 0.22, 0.09, 0.02, matrix=M)
    sp = C.mesh_obj("Spider", bm, [spider_m])
    C.add_bevel(sp, 0.012, segments=2, angle=30)
    out.append(C.finalize(sp, angle=35))
    # rivets
    bm = bmesh.new()
    for k in range(3):
        th = math.tau * k / 3
        for rr in (0.20, 0.25):
            M = Matrix.Rotation(th, 4, "Z") @ Matrix.Translation((rr, 0, 0))
            C.cyl_bm(bm, 0.018, zf + 0.06, zf + 0.072, seg=16, matrix=M, r1=0.012)
    rv = C.mesh_obj("Rivets", bm, [steel])
    out.append(C.finalize(rv, angle=40))
    # centre hub, nut, shaft end
    hub = C.lathe("Hub", [(0.0, zf + 0.06, 0), (0.075, zf + 0.06, 0), (0.075, zf + 0.10, 0), (0.065, zf + 0.11, 0), (0.0, zf + 0.11, 0)], [steel], steps=64)
    out.append(C.finalize(hub, angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.052, zf + 0.11, zf + 0.15, seg=6)
    nut = C.mesh_obj("Nut", bm, [steel])
    C.add_bevel(nut, 0.006, segments=2, angle=30)
    out.append(C.finalize(nut, angle=35))
    sh = C.lathe("Shaft", [(0.0, zf + 0.15, 0), (0.026, zf + 0.15, 0), (0.026, zf + 0.175, 0), (0.02, zf + 0.18, 0), (0.0, zf + 0.18, 0)], [steel], steps=32)
    out.append(C.finalize(sh, angle=40))
    # coil housing visible behind pulley
    ch = C.lathe("Coil", [(0.26, ZP0 - 0.05, 0), (0.37, ZP0 - 0.05, 0), (0.37, ZP0 + 0.002, 0), (0.26, ZP0 + 0.002, 0)], [dark], steps=96)
    out.append(C.finalize(ch, angle=40))
    return out


# ----------------------------------------------------------------- wiring
def curve_tube(name, pts, radius, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.resolution_u = 16
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    sp.order_u = 4
    sp.use_endpoint_u = True
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def connector(black, wire_m, alu):
    out = []
    th = math.radians(52)
    T = at_angle(th, 0.0)
    # small bracket cast on the body
    bm = bmesh.new()
    C.box_bm(bm, 0.12, 0.08, 0.16, center=(0, RB + 0.02, 0.58), matrix=T)
    br = C.mesh_obj("ConnBracket", bm, [alu])
    C.add_bevel(br, 0.015, segments=2, angle=30)
    out.append(C.finalize(br, angle=35))
    # connector housing + latch
    bm = bmesh.new()
    C.box_bm(bm, 0.11, 0.09, 0.15, center=(0, RB + 0.105, 0.58), matrix=T)
    C.box_bm(bm, 0.05, 0.03, 0.08, center=(0, RB + 0.16, 0.56), matrix=T)
    C.box_bm(bm, 0.075, 0.07, 0.03, center=(0, RB + 0.105, 0.665), matrix=T)
    cn = C.mesh_obj("Connector", bm, [black])
    C.add_bevel(cn, 0.008, segments=2, angle=30)
    out.append(C.finalize(cn, angle=35))
    # lead from the coil (behind the pulley) to the connector
    def P(thd, r, z):
        t = math.radians(thd)
        return Vector((r * math.cos(t), r * math.sin(t), z))
    pts = [P(52, RB + 0.105, 0.68), P(52, RB + 0.105, 0.74), P(50, RB + 0.07, 0.84), P(48, RB + 0.05, 0.95),
           P(46, 0.42, 1.04), P(44, 0.34, 1.07), P(44, 0.32, ZP0 - 0.03)]
    out.append(curve_tube("Lead", pts, 0.016, wire_m))
    # rubber grommet where the lead leaves the coil
    g = C.lathe("Grommet", [(0.0, ZP0 - 0.09, 0), (0.03, ZP0 - 0.09, 0), (0.03, ZP0 - 0.04, 0), (0.0, ZP0 - 0.04, 0)], [wire_m], steps=24)
    g.matrix_world = Matrix.Translation(P(44, 0.32, 0))
    out.append(C.finalize(g, angle=40))
    return out


def build():
    alu = mat_cast_alu("CastAlu", base=0.34, rough=0.40)
    port_m = C.mat_machined("PortAlu", color=0.62, rough=0.22, rings=900)
    steel = C.mat_machined("PulleySteel", color=0.60, rough=0.18, rings=700)
    plate = C.mat_machined("ArmaturePlate", color=0.50, rough=0.24, rings=1400)
    bolt = C.principled("ZincSteel", (0.58, 0.59, 0.61), metallic=1.0, rough=0.26)
    C.add_noise_bump(bolt, scale=900, strength=0.03, distance=0.0005)
    dark = C.principled("DarkSteel", (0.06, 0.06, 0.065), metallic=0.9, rough=0.42)
    C.add_noise_bump(dark, scale=600, strength=0.05, distance=0.0005)
    black = C.mat_black_plastic("PA66", rough=0.5, color=0.03)
    wire = C.mat_rubber("WireSheath")
    objs = body(alu) + ears(alu, bolt) + ports(alu, port_m, bolt, black) + relief_valve(bolt, alu)
    pl, zf = pulley(steel)
    objs += pl + clutch(plate, bolt, dark, zf) + connector(black, wire, alu)
    # axis Z -> horizontal, pulley toward the front-left; port block on top
    C.transform_all(objs, Matrix.Rotation(math.radians(-24), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("compressore", objs, "compressore.py",
            "car A/C compressor: ribbed cast-aluminium body, mounting ears, electromagnetic clutch with poly-V pulley, port block with two fittings, connector",
            az=35, el=22, lens=70, fill=0.82)
