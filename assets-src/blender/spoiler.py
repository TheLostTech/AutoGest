"""Rear roof spoiler of a generic modern small hatchback, removed from the car.
Painted wing-section lip (same metallic grey clear-coat as the other body panels) curving
gently in plan, with small endplates turning down at both tips; a slot in the trailing
face carries the red third brake lamp lens; black rubber seal along the leading edge where
it meets the roof, black foam gasket and threaded studs underneath.
Car rear (outside) is -Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

XE = 0.50            # half span
TE = 0.240           # chord (trailing face distance behind the leading edge)
SEC = [(0.0, -0.010), (0.006, 0.008), (0.05, 0.021), (0.12, 0.028), (0.19, 0.031), (0.228, 0.029), (0.2375, 0.025),
       (0.2405, 0.017), (0.2405, -0.006), (0.238, -0.013), (0.228, -0.017), (0.17, -0.015), (0.10, -0.021),
       (0.04, -0.029), (0.008, -0.027)]
SECB = P.bspline(SEC, 110, closed=True)
LAMP_W, LAMP_Z0, LAMP_Z1 = 0.13, -0.0035, 0.0105


def yoff(x):
    return 0.028 * (x / XE) ** 2


def sec_at(x):
    ax = abs(x)
    e = P.sstep(XE - 0.09, XE - 0.005, ax)
    out = []
    for p in SECB:
        a, b = p.x, p.y
        if b < 0.0:
            w = P.sstep(0.12, 0.21, a)
            b -= 0.055 * e * w * min(1.0, (-b / 0.015)) ** 0.5
        out.append((a, b))
    return out


def shell(paint):
    bm = bmesh.new()
    n = 260
    rings = []
    for k in range(n + 1):
        t = -1 + 2 * k / n
        x = XE * math.copysign(abs(t) ** 0.85, t)
        ex = abs(x) - (XE - 0.03)
        sc = math.sqrt(max(0.0, 1 - (ex / 0.03) ** 2)) if ex > 0 else 1.0
        sc = max(sc, 0.06)
        sec = sec_at(x)
        ca = sum(a for a, b in sec) / len(sec)
        cb = sum(b for a, b in sec) / len(sec)
        y0 = yoff(x)
        rings.append([bm.verts.new((x, y0 - (ca + (a - ca) * (0.35 + 0.65 * sc)), cb + (b - cb) * sc)) for (a, b) in sec])
    m = len(SECB)
    for i in range(n):
        for k in range(m):
            k2 = (k + 1) % m
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    C.fix_normals(bm)
    ob = C.mesh_obj("Spoiler", bm, [paint])
    cb = bmesh.new()
    C.box_bm(cb, 2 * LAMP_W, 0.05, LAMP_Z1 - LAMP_Z0, center=(0.0, -TE - 0.005 + 0.012, (LAMP_Z0 + LAMP_Z1) / 2))
    cut = C.mesh_obj("LampSlot", cb, [paint])
    mm = C.add_boolean(ob, cut)
    mm.use_self = True
    C.add_bevel(ob, 0.0012, segments=2, angle=40)
    return C.finalize(ob, angle=45, remove=[cut])


def lamp(lens_m, back_m, led_m):
    out = []
    yb = -TE + 0.012
    bm = bmesh.new()
    C.box_bm(bm, 2 * LAMP_W - 0.002, 0.004, LAMP_Z1 - LAMP_Z0 - 0.0015, center=(0.0, yb - 0.003, (LAMP_Z0 + LAMP_Z1) / 2))
    ln = C.mesh_obj("BrakeLens", bm, [lens_m])
    C.add_bevel(ln, 0.0008, segments=2, angle=30)
    out.append(C.finalize(ln, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 2 * LAMP_W, 0.003, LAMP_Z1 - LAMP_Z0, center=(0.0, yb + 0.004, (LAMP_Z0 + LAMP_Z1) / 2))
    out.append(C.finalize(C.mesh_obj("LampBack", bm, [back_m]), angle=35))
    # row of LEDs behind the lens
    bm = bmesh.new()
    for k in range(12):
        x = -LAMP_W + 0.011 + k * (2 * LAMP_W - 0.022) / 11
        C.box_bm(bm, 0.0045, 0.0016, 0.0045, center=(x, yb + 0.0018, (LAMP_Z0 + LAMP_Z1) / 2))
    out.append(C.finalize(C.mesh_obj("LEDs", bm, [led_m]), angle=35))
    return out


def seal(rubber):
    pts = []
    for k in range(161):
        t = -1 + 2 * k / 160
        x = (XE - 0.04) * t
        p = Vector((x, yoff(x) + 0.004, -0.010))
        pts.append(p)
    fr = P.path_frames(pts, (0, 0.6, 1))
    sec = [(-0.003, -0.002), (0.004, -0.002), (0.0055, 0.001), (0.003, 0.004), (-0.002, 0.004), (-0.004, 0.001)]
    return [P.tube_obj("LeadingSeal", fr, sec, [rubber], smooth_angle=60)]


def underside(foam, zinc):
    out = []
    pts = []
    for k in range(121):
        x = (XE - 0.07) * (-1 + 2 * k / 120)
        pts.append(Vector((x, yoff(x) - 0.03, -0.0275)))
    fr = P.path_frames(pts, (0, 0, 1))
    out.append(P.tube_obj("Gasket", fr, P.rrect(-0.008, 0.008, -0.003, 0.001, 0.001), [foam], smooth_angle=60))
    for x in (-0.30, 0.0, 0.30):
        st = C.lathe("Stud", [(0.0, 0.0, 0), (0.003, 0.0, 0), (0.003, -0.016, 0), (0.0022, -0.0175, 0), (0.0, -0.0175, 0)], [zinc], steps=20)
        st.matrix_world = Matrix.Translation((x, yoff(x) - 0.08, -0.020))
        out.append(C.finalize(st, angle=50))
    return out


def mat_lens():
    m = C.principled("BrakeLensRed", (0.55, 0.02, 0.025), rough=0.05, Coat_Weight=1.0, IOR=1.5)
    nt = m.node_tree
    b = P.bsdf(m)
    C._set(b, "Transmission Weight", 0.55)
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 90.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def build():
    paint = P.body_paint()
    rubber = C.mat_rubber()
    foam = C.principled("Foam", (0.03, 0.03, 0.03), rough=0.9)
    C.add_noise_bump(foam, scale=1500, strength=0.4, distance=0.0005)
    zinc = C.principled("Zinc", (0.6, 0.6, 0.62), metallic=1.0, rough=0.3)
    back = C.principled("LampHousing", (0.25, 0.012, 0.014), rough=0.4)
    led = C.principled("LED", (0.75, 0.72, 0.62), rough=0.3)
    objs = [shell(paint)]
    objs += lamp(mat_lens(), back, led)
    objs += seal(rubber)
    objs += underside(foam, zinc)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("spoiler", objs, "spoiler.py",
            "rear roof spoiler (generic small hatchback), metallic grey paint: wing-section lip with down-turned endplates, "
            "red third brake lamp in the trailing face, rubber leading-edge seal",
            az=-34, el=30, lens=70, fill=0.9, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
