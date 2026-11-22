"""Steel wheel rim (cerchio in ferro), 14 x 5.5J, 4 x 100: rolled sheet-steel rim with
J flanges, humps and drop centre, pressed centre disc welded into the well, with
recessed mounting face, embossed conical stud seats, centre bore, a ring of oval
ventilation holes and the valve hole. Silver painted, a little brake dust. No tyre.
Sheet parts are lathed from a smoothed centre line thickened to sheet thickness;
holes are boolean cutters. `wheel()` is reused by ruotino.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm. Wheel axis = Z, outboard = +Z (rotated to face -Y at the end)
PCD_R = 0.50
BORE_R = 0.285


def chaikin(pts, it=3):
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def thicken(line, t):
    """open (r, z) centre line -> closed lathe profile of a sheet of thickness t"""
    n = len(line)
    nrm = []
    for i in range(n):
        a = line[max(0, i - 1)]
        b = line[min(n - 1, i + 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1.0
        nrm.append((dz / L, -dx / L))
    A = [(p[0] + q[0] * t / 2, p[1] + q[1] * t / 2, 0) for p, q in zip(line, nrm)]
    B = [(p[0] - q[0] * t / 2, p[1] - q[1] * t / 2, 0) for p, q in zip(line, nrm)]
    return A + B[::-1]


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    try:
        m.solver = "MANIFOLD"      # fast and robust on these closed lathe sheets
    except Exception:
        m.use_self = True
    return m


def rim_line(R, s):
    Rw = R - 0.28
    raw = [(R + 0.17, -0.80), (R + 0.155, -0.775), (R + 0.10, -0.755), (R + 0.03, -0.745),
           (R + 0.002, -0.72), (R - 0.004, -0.53), (R + 0.016, -0.49), (R - 0.02, -0.45),
           (Rw + 0.06, -0.31), (Rw, -0.23), (Rw, 0.17), (Rw + 0.06, 0.25),
           (R - 0.02, 0.45), (R + 0.016, 0.49), (R - 0.004, 0.53), (R + 0.002, 0.72),
           (R + 0.03, 0.745), (R + 0.10, 0.755), (R + 0.155, 0.775), (R + 0.17, 0.80)]
    raw = [(r, z * s) for r, z in raw]
    return chaikin(raw, 3)


def disc_line(R, s):
    Rw = R - 0.28
    k = (Rw - 0.02) / 1.478           # outer disc features scale with the wheel size
    zm = 0.40 * s
    raw = [(BORE_R, zm + 0.02), (BORE_R + 0.03, zm), (0.68, zm), (0.78, zm + 0.07 * s ** 0.5),
           (0.92 * k ** 0.3, zm + 0.15 * s ** 0.5), (1.08 * k, zm + 0.17 * s ** 0.5),
           (1.24 * k, zm + 0.11 * s ** 0.5), (1.36 * k, zm - 0.02), (1.43 * k, zm - 0.16 * s),
           (Rw - 0.034, zm - 0.30 * s), (Rw - 0.032, zm - 0.62 * s)]
    return chaikin(raw, 3)


def wheel(paint, R=1.778, s=1.0, n_vents=8, vent=(0.24, 0.34), t=0.032):
    out = []
    # --- rim
    rim = C.lathe("Rim", thicken(rim_line(R, s), t), [paint], steps=200)
    vb = bmesh.new()
    Rw = R - 0.28
    Mv = Matrix.Translation((Rw, 0, 0.06 * s)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    C.cyl_bm(vb, 0.058, -0.2, 0.2, seg=24, matrix=Mv)
    vc = C.mesh_obj("ValveHole", vb, [paint])
    boolean(rim, vc)
    out.append(C.finalize(rim, angle=40, remove=[vc]))
    # --- centre disc
    disc = C.lathe("Disc", thicken(disc_line(R, s), t * 1.15), [paint], steps=200)
    k = (Rw - 0.02) / 1.478
    zm = 0.40 * s
    cuts = []
    hb = bmesh.new()
    for i in range(4):
        a = math.radians(45 + 90 * i)
        C.cyl_bm(hb, 0.072, zm - 0.5, zm + 0.5, seg=32, matrix=Matrix.Translation((PCD_R * math.cos(a), PCD_R * math.sin(a), 0)))
    cuts.append(C.mesh_obj("StudHoles", hb, [paint]))
    for i in range(n_vents):
        a = math.tau * (i + 0.5) / n_vents
        vb = bmesh.new()
        M = (Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((1.17 * k, 0, 0)) @
             Matrix.Diagonal((vent[0] * k / 0.2, vent[1] * k / 0.2, 1, 1)))
        C.cyl_bm(vb, 0.1, zm - 0.8, zm + 0.8, seg=40, matrix=M)
        cuts.append(C.mesh_obj("Vent%d" % i, vb, [paint]))
    for c in cuts:
        boolean(disc, c)
    C.add_bevel(disc, 0.006, segments=2, angle=50)
    out.append(C.finalize(disc, angle=40, remove=cuts))
    # embossed conical stud seats (pressed cones standing proud of the mounting face)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        line = chaikin([(0.074, zm + 0.075), (0.10, zm + 0.07), (0.15, zm + 0.035), (0.18, zm + 0.005)], 2)
        ob = C.lathe("Seat", thicken(line, t), [paint], steps=48)
        ob.matrix_world = Matrix.Translation((PCD_R * math.cos(a), PCD_R * math.sin(a), 0))
        out.append(C.finalize(ob, angle=45))
    return out


def mat_wheel_paint(name="WheelSilver", color=(0.30, 0.31, 0.32, 1), metallic=0.75):
    m = C.mat_paint(name, color, rough=0.40, coat=0.35, metallic=metallic)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    # brake-dust grime, mottled, darker toward the inboard (z-) side
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 10.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.50
    mr.inputs["From Max"].default_value = 0.80
    mr.inputs["To Max"].default_value = 0.30
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = color
    mix.inputs["B"].default_value = (0.11, 0.095, 0.08, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    ro = nt.nodes.new("ShaderNodeMapRange")
    ro.inputs["To Min"].default_value = 0.38
    ro.inputs["To Max"].default_value = 0.75
    nt.links.new(mr.outputs["Result"], ro.inputs["Value"])
    nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    # orange peel
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 160.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def build():
    paint = mat_wheel_paint()
    objs = wheel(paint)
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("cerchio-ferro", objs, "cerchio-ferro.py",
            "pressed steel wheel rim, silver painted, centre disc with 4 stud holes and oval ventilation holes, valve hole, no tyre",
            az=30, el=14, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
