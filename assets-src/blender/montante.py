"""Complete McPherson front strut (montante / gruppo molla-ammortizzatore) of a small
car, as removed: damper tube with welded two-bolt knuckle clevis bracket (one slotted
camber hole), anti-roll-bar link tab and brake-hose bracket, pressed lower spring seat,
black coil spring with closed ends, chrome rod hidden by the bellows boot, upper
spring seat, bonded rubber top mount with thrust bearing, three studs and rod nut.
Distinct from ammortizzatore.png (coilover with eye bush)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm, strut axis Z, knuckle side = +X
TR = 0.25                     # damper tube radius
Z_TUBE = 3.05
Z_LO, Z_HI = 2.05, 4.42       # spring seat surfaces
SR, WR = 0.62, 0.066          # spring mean radius, wire radius


def mat_worn_black(name="ArmPaint"):
    m = C.mat_paint(name, (0.022, 0.022, 0.024, 1), rough=0.42, coat=0.15)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 14.0
    nz.inputs["Detail"].default_value = 10.0
    em = C.edge_mask(nt, 0.02, 5.0)
    th = nt.nodes.new("ShaderNodeMapRange")
    th.inputs["From Min"].default_value = 0.55
    th.inputs["From Max"].default_value = 0.62
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    nt.links.new(em, mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 1.3
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], th.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(th.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.022, 0.022, 0.024, 1)
    mix.inputs["B"].default_value = (0.20, 0.19, 0.18, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.42
    ro.inputs["To Max"].default_value = 0.8
    nt.links.new(th.outputs["Result"], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # orange-peel
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 220.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def axis_mat(origin, axis):
    d = Vector(axis).normalized()
    return Matrix.Translation(origin) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def spring(paint):
    turns = 5.4
    n = 900
    th_end = 0.85 * math.tau
    th_tot = turns * math.tau

    def pitch(th):
        a = C.smoothstep(0, th_end, th) * C.smoothstep(0, th_end, th_tot - th)
        return 1.0 * (1 - a) + 4.0 * a
    zs = [0.0]
    ths = [th_tot * i / n for i in range(n + 1)]
    for i in range(1, n + 1):
        zs.append(zs[-1] + pitch((ths[i] + ths[i - 1]) / 2) * (ths[i] - ths[i - 1]))
    k = ((Z_HI - WR) - (Z_LO + WR)) / zs[-1]
    cu = bpy.data.curves.new("Spring", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = WR
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(n)
    for p, th, z in zip(sp.points, ths, zs):
        # slight barrel shape and pigtail-free closed ends
        rr = SR * (1.0 + 0.03 * math.sin(math.pi * th / th_tot))
        p.co = (rr * math.cos(th), rr * math.sin(th), Z_LO + WR + z * k, 1)
    ob = C.link(bpy.data.objects.new("Spring", cu))
    cu.materials.append(paint)
    return C.finalize(ob, angle=60)


def damper(paint, chrome, rubber, zinc):
    out = []
    P = [(0.0, 0.0, 0), (TR - 0.03, 0.0, 0), (TR, 0.03, 0), (TR, Z_TUBE - 0.06, 0), (TR - 0.02, Z_TUBE - 0.02, 0),
         (0.16, Z_TUBE, 0), (0.15, Z_TUBE + 0.06, 0), (0.0, Z_TUBE + 0.06, 0)]
    out.append(C.finalize(C.lathe("Tube", P, [paint], steps=96), angle=35))
    # lower spring seat (pressed dish) welded on the tube
    P = [(TR - 0.005, Z_LO - 0.22, 0), (TR + 0.05, Z_LO - 0.22, 0), (0.42, Z_LO - 0.08, 0), (0.66, Z_LO - 0.025, 0),
         (0.74, Z_LO + 0.02, 0), (0.77, Z_LO + 0.09, 0), (0.745, Z_LO + 0.10, 0), (0.715, Z_LO + 0.04, 0),
         (0.64, Z_LO + 0.008, 0), (0.42, Z_LO - 0.04, 0), (TR + 0.03, Z_LO - 0.16, 0), (TR - 0.005, Z_LO - 0.16, 0)]
    seat = C.lathe("LowerSeat", P, [paint], steps=144)
    # drain notch in the dish rim
    cb = bmesh.new()
    C.box_bm(cb, 0.20, 0.16, 0.2, center=(0.74, 0, Z_LO + 0.10), matrix=Matrix.Rotation(math.radians(-60), 4, "Z"))
    cut = C.mesh_obj("Notch", cb, [paint])
    boolean(seat, cut)
    out.append(C.finalize(seat, angle=35, remove=[cut]))
    # chrome rod (only the top shows above the boot)
    P = [(0.0, Z_TUBE, 0), (0.11, Z_TUBE, 0), (0.11, Z_HI + 0.45, 0), (0.0, Z_HI + 0.45, 0)]
    out.append(C.finalize(C.lathe("Rod", P, [chrome], steps=48), angle=40))
    # bump stop + bellows boot
    P = [(0.0, Z_TUBE + 0.06, 0), (0.24, Z_TUBE + 0.06, 0)]
    z = Z_TUBE + 0.10
    while z < Z_HI - 0.18:
        P += [(0.33, z + 0.045, 0), (0.27, z + 0.09, 0)]
        z += 0.09
    P += [(0.30, Z_HI - 0.06, 0), (0.0, Z_HI - 0.06, 0)]
    out.append(C.finalize(C.lathe("Boot", P, [rubber], steps=96), angle=55))
    # knuckle clevis bracket: wrap + two ears toward +X with bolt holes along Y
    bm = bmesh.new()
    C.cyl_bm(bm, TR + 0.035, 0.08, 1.15, seg=64)
    for s in (-1, 1):
        C.box_bm(bm, 0.62, 0.06, 1.05, center=(0.36, s * 0.235, 0.62))
    br = C.mesh_obj("Clevis", bm, [paint])
    hb = bmesh.new()
    C.cyl_bm(hb, TR - 0.002, -1, 2, seg=64)          # tube passes through (bracket wraps it)
    C.cyl_bm(hb, 0.075, -0.6, 0.6, seg=28, matrix=axis_mat((0.46, 0, 0.30), (0, 1, 0)))
    for dz in (-0.04, 0.0, 0.04):                     # slotted upper hole (camber adjust)
        C.cyl_bm(hb, 0.075, -0.6, 0.6, seg=28, matrix=axis_mat((0.46 - 0.02, 0, 0.92 + dz), (0, 1, 0)))
    holes = C.mesh_obj("ClevisHoles", hb, [paint])
    boolean(br, holes)
    C.add_bevel(br, 0.015, segments=2, angle=30)
    out.append(C.finalize(br, angle=35, remove=[holes]))
    # anti-roll-bar link tab (toward -X) and brake-hose bracket (toward -Y)
    bm = bmesh.new()
    C.box_bm(bm, 0.42, 0.05, 0.28, center=(-(TR + 0.18), 0.0, 1.55))
    C.box_bm(bm, 0.05, 0.30, 0.20, center=(0.05, -(TR + 0.12), 1.30))
    tab = C.mesh_obj("Tabs", bm, [paint])
    hb = bmesh.new()
    C.cyl_bm(hb, 0.055, -0.5, 0.5, seg=24, matrix=axis_mat((-(TR + 0.27), 0, 1.55), (0, 1, 0)))
    C.box_bm(hb, 0.4, 0.10, 0.07, center=(0.05, -(TR + 0.20), 1.30))
    th = C.mesh_obj("TabHoles", hb, [paint])
    boolean(tab, th)
    C.add_bevel(tab, 0.012, segments=2, angle=30)
    out.append(C.finalize(tab, angle=35, remove=[th]))
    # clevis bolts' washers would be on the knuckle: leave holes empty (as sold)
    return out


def top(paint, rubber, zinc, plastic, steel):
    out = []
    z = Z_HI
    # upper spring seat (pressed steel) + rubber isolator under it
    P = [(0.12, z + 0.02, 0), (0.30, z + 0.02, 0), (0.62, z - 0.005, 0), (0.74, z + 0.01, 0), (0.77, z + 0.06, 0),
         (0.745, z + 0.07, 0), (0.71, z + 0.04, 0), (0.62, z + 0.03, 0), (0.30, z + 0.06, 0), (0.12, z + 0.06, 0)]
    out.append(C.finalize(C.lathe("UpperSeat", P, [paint], steps=144), angle=35))
    P = [(0.40, z - 0.03, 0), (0.70, z - 0.03, 0), (0.71, z + 0.0, 0), (0.40, z + 0.0, 0)]
    out.append(C.finalize(C.lathe("Isolator", P, [rubber], steps=144), angle=40))
    # thrust bearing (plastic)
    P = [(0.16, z + 0.06, 0), (0.50, z + 0.06, 0), (0.52, z + 0.09, 0), (0.50, z + 0.17, 0), (0.16, z + 0.17, 0)]
    out.append(C.finalize(C.lathe("Bearing", P, [plastic], steps=128), angle=40))
    # bonded rubber mount + top plate
    P = [(0.10, z + 0.17, 0), (0.40, z + 0.17, 0), (0.45, z + 0.22, 0), (0.46, z + 0.30, 0),
         (0.43, z + 0.35, 0), (0.10, z + 0.35, 0)]
    out.append(C.finalize(C.lathe("MountRubber", P, [rubber], steps=128), angle=50))
    bm = bmesh.new()
    n = 180
    poly = []
    for i in range(n):
        t = math.tau * i / n
        c = math.cos(3 * (t - math.radians(30)))
        r = 0.44 + 0.14 * max(0.0, c) ** 2.2
        poly.append((r * math.cos(t), r * math.sin(t)))
    zb, zt = z + 0.35, z + 0.385
    vb = [bm.verts.new((x, y, zb)) for x, y in poly]
    vt = [bm.verts.new((x, y, zt)) for x, y in poly]
    bm.faces.new(vb[::-1])
    bm.faces.new(vt)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    pl = C.mesh_obj("TopPlate", bm, [zinc])
    C.add_bevel(pl, 0.008, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    P = [(0.10, zt + 0.08, 0), (0.15, zt + 0.08, 0), (0.19, zt + 0.06, 0), (0.21, zt, 0), (0.10, zt, 0)]
    out.append(C.finalize(C.lathe("Dome", P, [zinc], steps=96), angle=40))
    # studs
    for k in range(3):
        a = math.radians(30 + 120 * k)
        P = [(0.0, zt - 0.01, 0), (0.042, zt - 0.01, 0), (0.042, zt + 0.03, 0)]
        zz = zt + 0.03
        for i in range(16):
            P += [(0.043, zz + 0.0075, 0), (0.037, zz + 0.015, 0)]
            zz += 0.015
        P += [(0.03, zz + 0.016, 0), (0.0, zz + 0.016, 0)]
        ob = C.lathe("Stud", P, [steel], steps=32)
        ob.matrix_world = Matrix.Translation((0.47 * math.cos(a), 0.47 * math.sin(a), 0))
        out.append(C.finalize(ob, angle=50))
    # rod nut on top
    bm = bmesh.new()
    C.cyl_bm(bm, 0.11, zt + 0.08, zt + 0.17, seg=6)
    nut = C.mesh_obj("RodNut", bm, [steel])
    C.add_bevel(nut, 0.012, segments=1, angle=30)
    out.append(C.finalize(nut, angle=35))
    P = [(0.0, zt + 0.17, 0), (0.07, zt + 0.17, 0), (0.07, zt + 0.22, 0), (0.0, zt + 0.22, 0)]
    out.append(C.finalize(C.lathe("RodEnd", P, [steel], steps=32), angle=40))
    return out


def build():
    spring_paint = mat_worn_black("SpringPaint")
    tube_paint = mat_worn_black("TubePaint")
    for n in tube_paint.node_tree.nodes:           # tube a shade lighter than the spring
        if n.type == "MIX":
            n.inputs["A"].default_value = (0.05, 0.05, 0.053, 1)
    chrome = C.mat_chrome()
    rubber = C.mat_rubber()
    zinc = C.principled("ZincPlate", (0.58, 0.59, 0.60), metallic=1.0, rough=0.34)
    C.add_noise_bump(zinc, scale=180, strength=0.06, distance=0.0008, rough_var=0.08)
    steel = C.principled("Steel", (0.62, 0.62, 0.62), metallic=1.0, rough=0.3)
    plastic = C.mat_black_plastic("BearingPA", rough=0.5, color=0.05)
    objs = [spring(spring_paint)] + damper(tube_paint, chrome, rubber, zinc) + top(tube_paint, rubber, zinc, plastic, steel)
    C.transform_all(objs, Matrix.Rotation(math.radians(-35), 4, "Z"))
    C.transform_all(objs, Matrix.Rotation(math.radians(7), 4, "Y"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("montante", objs, "montante.py",
            "complete McPherson strut: black coil spring on damper with knuckle clevis bracket, spring seats, bellows boot, rubber top mount with three studs",
            az=30, el=14, lens=70, fill=0.88,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
