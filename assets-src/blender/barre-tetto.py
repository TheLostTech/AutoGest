"""Roof bars (pair of crossbars), generic small hatchback without roof rails: two
brushed silver anodised aluminium aero bars with a black rubber T-slot strip on top and
black end caps, each on two black grained-plastic towers with rubber pads, an outboard
lock cylinder and the black rubber-coated steel clamp hook that grips the door frame.
Bars along X, set side by side on Y."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
LB = 1.06            # bar length
CH = 0.082           # chord (Y)
TH = 0.024           # thickness (Z)
FX = 0.425           # foot positions along the bar
GAP = 0.42           # distance between the two bars
RY = Matrix.Rotation(math.radians(90), 4, "Y")


def aero(n=56, ch=CH, th=TH):
    """Closed wing section (a = chord along Y, b = Z), leading edge at a = -ch/2, flatter underside."""
    top, bot = [], []
    for k in range(n + 1):
        b_ = k / n
        x = (1 - math.cos(math.pi * b_)) / 2          # cosine spacing 0..1
        t = 5 * (th / ch) * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
        a = -ch / 2 + ch * x
        top.append((a, t * ch * 1.15))
        bot.append((a, -t * ch * 0.62))
    pts = top + bot[::-1][1:-1]
    return pts


def mat_alu():
    m = C.principled("AnodisedAlu", (0.70, 0.71, 0.73), metallic=1.0, rough=0.34)
    nt = m.node_tree
    b = P.bsdf(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (3.0, 900.0, 900.0)       # streaks along the bar
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.28
    mr.inputs["To Max"].default_value = 0.40
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def bar(alu, rubber, cap_m, y0):
    out = []
    sec = aero()
    frames = []
    for k in range(2):
        x = -LB / 2 + LB * k
        frames.append((Vector((x, y0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Bar", bm, [alu])
    C.add_bevel(ob, 0.0012, segments=3, angle=60)
    out.append(C.finalize(ob, angle=50))
    # rubber T-slot strip, sunk in a shallow groove at the crown
    a0 = -CH / 2 + CH * 0.30
    ztop = max(p[1] for p in sec)
    bm = bmesh.new()
    C.box_bm(bm, LB - 0.012, 0.014, 0.0026, center=(0, y0 + a0, ztop - 0.0007))
    st = C.mesh_obj("Strip", bm, [rubber])
    C.add_bevel(st, 0.0008, segments=2, angle=30)
    out.append(C.finalize(st, angle=40))
    # end caps following the section
    for s in (-1, 1):
        capsec = [(a * 1.02, b * 1.04) for a, b in sec]
        fr = []
        for j in range(7):
            t = j / 6
            sc = math.sqrt(max(1 - t * t, 0.0)) * 0.55 + 0.45 * (1 - t ** 3)
            fr.append((Vector((s * (LB / 2 - 0.004 + 0.014 * t), y0 - CH * 0.04 * t, 0.0016 * t)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                       [(a * sc, b * sc) for a, b in capsec]))
        bm = bmesh.new()
        C.sweep(bm, fr, mat=0)
        C.fix_normals(bm)
        cap = C.mesh_obj("EndCap", bm, [cap_m])
        out.append(C.finalize(cap, angle=55))
    return out


def foot(plastic, rubber, hook_m, chrome, dark, x, y0, s):
    """Tower under the bar at (x, y0); s = +-1 outboard direction along X."""
    out = []
    bm = bmesh.new()
    vs = P.superellipsoid(bm, 0.031, 0.048, 0.052, e1=0.28, e2=0.35, nu=64, nv=32)
    for v in vs:
        t = (v.co.z + 0.052) / 0.104          # 0 bottom .. 1 top
        v.co.x *= 0.78 + 0.22 * t
        v.co.y *= 0.82 + 0.18 * t
        v.co.x += s * 0.010 * (1 - t)         # leans outboard at the base
        v.co += Vector((x, y0, -0.056))
    ob = C.mesh_obj("Foot", bm, [plastic])
    out.append(C.finalize(ob, angle=45))
    # rubber pad, slightly curved to the roof
    bm = bmesh.new()
    vs = P.superellipsoid(bm, 0.028, 0.042, 0.005, e1=0.3, e2=0.3, nu=48, nv=12)
    for v in vs:
        v.co.z += 0.0009 * (v.co.x / 0.026) ** 2 * 0 + 0.002 * (v.co.y / 0.038) ** 2
        v.co += Vector((x + s * 0.010, y0, -0.111))
    out.append(C.finalize(C.mesh_obj("Pad", bm, [rubber]), angle=50))
    # lock cylinder on the outboard face
    M = Matrix.Translation((x + s * 0.0285, y0 + 0.012, -0.045)) @ Matrix.Rotation(math.radians(90 * s), 4, "Y")
    lk = C.lathe("Lock", [(0.0, 0.0, 0), (6.2 * MM, 0.0, 0), (6.2 * MM, 2.2 * MM, 0), (5.4 * MM, 3.2 * MM, 0), (0.0, 3.2 * MM, 0)],
                 [chrome], steps=48)
    lk.matrix_world = M
    out.append(C.finalize(lk, angle=40))
    bm = bmesh.new()
    C.box_bm(bm, 1.4 * MM, 6.0 * MM, 1.0 * MM, center=(0, 0, 3.4 * MM))
    key = C.mesh_obj("Keyway", bm, [dark])
    key.matrix_world = M
    out.append(C.finalize(key, angle=40))
    # clamp hook: rubber-coated steel strip down the outboard face, curling inwards
    pts = []
    for k in range(40):
        t = k / 39
        z = -0.034 - 0.074 * t
        pts.append(Vector((x + s * (0.034 + 0.005 * t), y0 - 0.016, z)))
    c = pts[-1]
    for k in range(1, 16):
        a = math.pi * k / 15
        pts.append(c + Vector((s * 0.006 * (math.cos(a) - 1) * 1.0 - s * 0.0, 0, -0.006 * math.sin(a))))
    pts += [pts[-1] + Vector((-s * 0.004 * j, 0, 0.0004 * j)) for j in range(1, 5)]
    fr = P.path_frames(pts, (0, 1, 0))
    out.append(P.tube_obj("Hook", fr, P.rrect(-0.0024, 0.0024, -0.011, 0.011, 0.0018, seg=3), [hook_m], smooth_angle=55))
    return out


def build():
    alu = mat_alu()
    rubber = C.mat_rubber("StripRubber")
    cap_m = C.mat_black_plastic("CapPA", rough=0.4, color=0.02)
    plastic = P.textured_black("FootPA", rough=0.55, v=0.022)
    hook_m = C.principled("HookCoat", (0.025, 0.025, 0.027), rough=0.6)
    C.add_noise_bump(hook_m, scale=500, strength=0.1, distance=0.0004)
    chrome = C.mat_chrome("LockChrome")
    dark = C.principled("Keyway", (0.01, 0.01, 0.01), rough=0.6)
    objs = []
    for y0 in (-GAP / 2, GAP / 2):
        objs += bar(alu, rubber, cap_m, y0)
        for s in (-1, 1):
            objs += foot(plastic, rubber, hook_m, chrome, dark, s * FX, y0, s)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("barre-tetto", objs, "barre-tetto.py",
            "roof bars (generic small hatchback): pair of silver aluminium aero crossbars on black plastic feet "
            "with rubber pads, lock cylinders and door-frame clamp hooks",
            az=36, el=34, lens=70, fill=0.9, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
