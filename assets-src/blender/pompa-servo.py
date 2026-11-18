"""Power steering pump (pompa servosterzo, vane type): die-cast aluminium body with a
bearing nose, three mounting bosses with bolt holes parallel to the shaft, rear cover with
four hex bolts, poly-V pulley pressed onto the shaft, suction spigot with hose barb on top,
high-pressure outlet union and a pressure switch with black connector on the rear cover.

Built along +Z (rear cover -> pulley) with "up" = +Y, then laid down for the shot.
Units ~ decimetres (pulley diameter ~13 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RB = 0.50           # main body radius
ZP = 1.42           # pulley back face


def mat_cast_alu(name, base=0.42, rough=0.45, grain=480.0, wear=0.35):
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
    col.inputs["A"].default_value = (base * 0.80, base * 0.80, base * 0.78, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.05, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.75, 0.75, 0.75, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.07
    rr.inputs["To Max"].default_value = rough - 0.07
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
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


def axis_matrix(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def polar(th, r, z):
    return Vector((r * math.cos(th), r * math.sin(th), z))


# ----------------------------------------------------------------- body
def body(alu):
    out = []
    def ribs(r, z, t):
        if abs(r - RB) > 1e-6 or not (0.40 <= z <= 0.98):
            return r
        v = math.cos(16 * t)
        env = C.smoothstep(0.40, 0.46, z) * (1 - C.smoothstep(0.92, 0.98, z))
        return r + 0.03 * env * (max(-1.0, min(1.0, (v - 0.5) * 6)) * 0.5 + 0.5)
    P = [(0.0, 0.30, 0), (0.46, 0.30, 0), (0.49, 0.32, 0), (RB, 0.36, 0), (RB, 0.380, 0), (RB, 0.400, 0), (RB, 0.420, 0), (RB, 0.440, 0), (RB, 0.460, 0), (RB, 0.480, 0), (RB, 0.500, 0), (RB, 0.520, 0), (RB, 0.540, 0), (RB, 0.560, 0), (RB, 0.580, 0), (RB, 0.600, 0), (RB, 0.620, 0), (RB, 0.640, 0), (RB, 0.660, 0), (RB, 0.680, 0), (RB, 0.700, 0), (RB, 0.720, 0), (RB, 0.740, 0), (RB, 0.760, 0), (RB, 0.780, 0), (RB, 0.800, 0), (RB, 0.820, 0), (RB, 0.840, 0), (RB, 0.860, 0), (RB, 0.880, 0), (RB, 0.900, 0), (RB, 0.920, 0), (RB, 0.940, 0), (RB, 0.960, 0), (RB, 0.980, 0),
         (0.49, 1.02, 0), (0.44, 1.06, 0), (0.33, 1.10, 0), (0.29, 1.14, 0), (0.28, 1.20, 0),
         (0.28, 1.36, 0), (0.25, 1.39, 0), (0.0, 1.39, 0)]
    ob = C.lathe("Body", P, [alu], steps=224, mod=ribs)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35))
    # rear cover
    P = [(0.0, -0.02, 0), (0.40, -0.02, 0), (0.46, 0.01, 0), (0.48, 0.06, 0), (0.48, 0.27, 0),
         (0.47, 0.30, 0), (0.0, 0.30, 0)]
    jf = C.lathe("JointFlange", [(0.40, 0.27, 0), (0.525, 0.27, 0), (0.535, 0.28, 0), (0.535, 0.33, 0), (0.525, 0.34, 0), (0.40, 0.34, 0)], [alu], steps=160)
    C.add_bevel(jf, 0.004, segments=2, angle=35)
    out.append(C.finalize(jf, angle=35))
    ob = C.lathe("RearCover", P, [alu], steps=160)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35))
    return out


def bosses(alu, zinc):
    out = []
    for th in (math.radians(205), math.radians(335), math.radians(140)):
        d = Vector((math.cos(th), math.sin(th), 0))
        # web from the body to the boss
        bm = bmesh.new()
        M = Matrix.Rotation(th, 4, "Z")
        C.box_bm(bm, 0.26, 0.15, 0.62, center=(0.52, 0, 0.66), matrix=M)
        w = C.mesh_obj("Web", bm, [alu])
        C.add_bevel(w, 0.03, segments=3, angle=30)
        out.append(C.finalize(w, angle=35))
        P = [(0.045, 0.34, 0), (0.09, 0.34, 0), (0.105, 0.36, 0), (0.105, 0.96, 0), (0.09, 0.98, 0), (0.045, 0.98, 0)]
        b = C.lathe("Boss", P, [alu], steps=48)
        b.matrix_world = Matrix.Translation(d * 0.68)
        C.add_bevel(b, 0.006, segments=2, angle=35)
        out.append(C.finalize(b, angle=35))
        P = [(0.036, 0.33, 0), (0.046, 0.33, 0), (0.046, 0.99, 0), (0.036, 0.99, 0)]
        s = C.lathe("BossSleeve", P, [zinc], steps=32)
        s.matrix_world = Matrix.Translation(d * 0.68)
        out.append(C.finalize(s, angle=40))
    return out


def cover_bolts(zinc):
    bm = bmesh.new()
    for k in range(4):
        th = math.tau * k / 4 + math.pi / 4
        M = Matrix.Translation(polar(th, 0.43, 0)) @ Matrix.Rotation(math.pi, 4, "X")
        C.cyl_bm(bm, 0.055, 0.02, 0.075, seg=6, matrix=M)
        C.cyl_bm(bm, 0.068, 0.015, 0.025, seg=32, matrix=M)
    ob = C.mesh_obj("CoverBolts", bm, [zinc])
    C.add_bevel(ob, 0.006, segments=1, angle=30)
    return [C.finalize(ob, angle=35)]


# ----------------------------------------------------------------- ports
def suction(alu, mach, rubber):
    out = []
    ax = Vector((0, 1.0, -0.55)).normalized()
    base = Vector((0, RB - 0.06, 0.62))
    T = axis_matrix(base, ax)
    P = [(0.0, 0.0, 0), (0.17, 0.0, 0), (0.17, 0.14, 0), (0.15, 0.17, 0), (0.12, 0.18, 0), (0.0, 0.18, 0)]
    b = C.lathe("SuctionBoss", P, [alu], steps=64)
    b.matrix_world = T
    C.add_bevel(b, 0.01, segments=2, angle=35)
    out.append(C.finalize(b, angle=35))
    # pipe with two hose barbs
    P = [(0.0, 0.16, 0), (0.095, 0.16, 0), (0.095, 0.40, 0), (0.115, 0.43, 0), (0.095, 0.47, 0),
         (0.095, 0.53, 0), (0.115, 0.56, 0), (0.095, 0.60, 0), (0.095, 0.64, 0), (0.07, 0.65, 0),
         (0.07, 0.62, 0), (0.0, 0.62, 0)]
    p = C.lathe("SuctionPipe", P, [mach], steps=96)
    p.matrix_world = T
    out.append(C.finalize(p, angle=40))
    return out


def pressure_side(zinc, brass, black, alu):
    out = []
    # outlet union on top of the rear cover
    T = axis_matrix(Vector((0.12, 0.30, 0.15)), Vector((0, 1, 0)))
    P = [(0.0, 0.0, 0), (0.15, 0.0, 0), (0.15, 0.16, 0), (0.13, 0.18, 0), (0.0, 0.18, 0)]
    b = C.lathe("OutletBoss", P, [alu], steps=64)
    b.matrix_world = T
    C.add_bevel(b, 0.01, segments=2, angle=35)
    out.append(C.finalize(b, angle=35))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.12, 0.17, 0.27, seg=6)
    C.cyl_bm(bm, 0.075, 0.27, 0.34, seg=32)
    C.cyl_bm(bm, 0.06, 0.34, 0.37, seg=32, r1=0.045)
    u = C.mesh_obj("OutletUnion", bm, [zinc])
    u.matrix_world = T
    C.add_bevel(u, 0.008, segments=2, angle=30)
    out.append(C.finalize(u, angle=35))
    # pressure switch on the cover, leaning back, with connector
    T = axis_matrix(Vector((-0.20, 0.26, 0.10)), Vector((-0.5, 1, -0.6)))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.075, 0.0, 0.10, seg=6)
    C.cyl_bm(bm, 0.055, 0.10, 0.16, seg=32)
    sw = C.mesh_obj("SwitchBody", bm, [brass])
    sw.matrix_world = T
    C.add_bevel(sw, 0.006, segments=2, angle=30)
    out.append(C.finalize(sw, angle=35))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.065, 0.16, 0.24, seg=32)
    C.box_bm(bm, 0.09, 0.09, 0.10, center=(0, 0, 0.29))
    C.box_bm(bm, 0.04, 0.02, 0.05, center=(0, 0.052, 0.28))
    cn = C.mesh_obj("SwitchConn", bm, [black])
    cn.matrix_world = T
    C.add_bevel(cn, 0.008, segments=2, angle=30)
    out.append(C.finalize(cn, angle=35))
    return out


# ----------------------------------------------------------------- pulley
def pulley(steel, zinc):
    z = ZP
    P = [(0.18, z, 0), (0.56, z, 0), (0.62, z + 0.01, 0)]
    z += 0.03
    for i in range(6):
        P += [(0.59, z, 0), (0.618, z + 0.012, 0)]
        z += 0.024
    P += [(0.59, z, 0), (0.62, z + 0.012, 0), (0.62, z + 0.03, 0), (0.60, z + 0.04, 0),
          (0.565, z + 0.04, 0), (0.54, z - 0.05, 0), (0.30, z - 0.06, 0), (0.25, z - 0.02, 0),
          (0.22, z + 0.07, 0), (0.12, z + 0.08, 0), (0.10, z + 0.06, 0),
          (0.10, ZP - 0.02, 0), (0.18, ZP - 0.02, 0)]
    ob = C.lathe("Pulley", P, [steel], steps=200)
    # lightening holes in the web
    bm = bmesh.new()
    for k in range(6):
        th = math.tau * k / 6
        M = Matrix.Translation(polar(th, 0.43, 0))
        C.cyl_bm(bm, 0.075, z - 0.2, z + 0.3, seg=32, matrix=M)
    cut = C.mesh_obj("PulleyHoles", bm, [steel])
    C.add_boolean(ob, cut)
    C.add_bevel(ob, 0.003, segments=1, angle=40)
    out = [C.finalize(ob, angle=40, remove=[cut])]
    zt = z + 0.08
    P = [(0.0, ZP - 0.1, 0), (0.07, ZP - 0.1, 0), (0.07, zt + 0.03, 0), (0.06, zt + 0.04, 0), (0.0, zt + 0.04, 0)]
    out.append(C.finalize(C.lathe("Shaft", P, [zinc], steps=48), angle=40))
    return out


def build():
    alu = mat_cast_alu("PumpAlu", base=0.32, rough=0.46)
    steel = C.mat_machined("PulleySteel", color=0.55, rough=0.2, rings=700)
    mach = C.principled("Spigot", (0.60, 0.60, 0.61), metallic=1.0, rough=0.30)
    C.add_noise_bump(mach, scale=800, strength=0.03, distance=0.0005, rough_var=0.05)
    zinc = C.principled("Zinc", (0.66, 0.67, 0.69), metallic=1.0, rough=0.24)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005)
    brass = C.principled("YellowZinc", (0.70, 0.62, 0.42), metallic=1.0, rough=0.3)
    black = C.mat_black_plastic("PA66", rough=0.45, color=0.03)
    rubber = C.mat_rubber("Hose")
    objs = body(alu) + bosses(alu, zinc) + cover_bolts(zinc) + suction(alu, mach, rubber)
    objs += pressure_side(zinc, brass, black, alu) + pulley(steel, zinc)
    # axis Z -> toward the camera-left, local +Y -> up
    C.transform_all(objs, Matrix.Rotation(math.radians(-28), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("pompa-servo", objs, "pompa-servo.py",
            "power steering pump: die-cast aluminium body with mounting bosses, poly-V pulley, "
            "suction spigot, high-pressure outlet union and pressure switch with connector",
            az=35, el=22, lens=70, fill=0.80, samples=S, res=(R, R))
