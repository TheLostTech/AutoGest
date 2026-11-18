"""CV drive shaft (semiasse): splined inner stub with circlip groove and seal journal,
tri-lobe tripod housing, two black rubber bellows with steel ear-clamps, steel shaft with
a rubber-mounted vibration damper, outer CV joint bell with ABS tone ring and a splined
wheel-side stub ending in a threaded section.

Built along +Z (gearbox end at z=0) and laid horizontally for the shot.
Units ~ decimetres (overall length ~83 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RS = 0.11            # shaft radius
Z_IB = 1.50          # inner housing end / inner boot start
Z_IBE = 2.45         # inner boot small end
Z_OBS = 5.25         # outer boot small end
Z_OB = 6.20          # outer boot large end / outer bell start


def spline_mod(z0, z1, rtip, n, depth):
    def mod(r, z, t):
        if abs(r - rtip) > 1e-6 or not (z0 - 1e-6 <= z <= z1 + 1e-6):
            return r
        v = math.cos(n * t)
        sq = max(-1.0, min(1.0, v * 2.5)) * 0.5 + 0.5
        return r - depth * (1 - sq)
    return mod


def bellows(name, z0, r0, z1, r1, n, amp, mat, rin0=None, rin1=None):
    """Convoluted boot from (z0, r0) to (z1, r1); n folds, amp fold depth (scaled down
    toward the small end). Solid of revolution (inside never seen)."""
    P = [(0.0, z0, 0), (rin0 or r0 - 0.01, z0, 0), (r0, z0 + 0.01, 0)]
    # plain collar at each end, folds in between
    c0, c1 = z0 + 0.12, z1 - 0.10
    P.append((r0, c0, 0))
    m = 160
    for i in range(1, m):
        u = i / m
        z = c0 + (c1 - c0) * u
        env = r0 + (r1 - r0) * u
        rel = (env - min(r0, r1)) / (abs(r1 - r0) + 1e-9)
        a = amp * (0.55 + 0.45 * rel)
        fold = 0.5 - 0.5 * math.cos(math.tau * n * u)
        P.append((env + a * fold, z, 0))
    P += [(r1, c1, 0), (r1, z1 - 0.01, 0), (rin1 or r1 - 0.01, z1, 0), (0.0, z1, 0)]
    ob = C.lathe(name, P, [mat], steps=128)
    return C.finalize(ob, angle=50)


def clamp(name, z, r, w, steel, ear_th=0.0):
    P = [(r - 0.01, z - w / 2, 0), (r + 0.012, z - w / 2, 0), (r + 0.016, z - w / 2 + 0.006, 0),
         (r + 0.016, z + w / 2 - 0.006, 0), (r + 0.012, z + w / 2, 0), (r - 0.01, z + w / 2, 0)]
    out = [C.finalize(C.lathe(name, P, [steel], steps=96), angle=40)]
    # crimped "ear"
    bm = bmesh.new()
    M = Matrix.Rotation(ear_th, 4, "Z") @ Matrix.Translation((r + 0.035, 0, z))
    C.box_bm(bm, 0.05, w * 1.1 + 0.01, w * 0.95, matrix=M)
    e = C.mesh_obj(name + "Ear", bm, [steel])
    C.add_bevel(e, 0.008, segments=2, angle=30)
    out.append(C.finalize(e, angle=35))
    return out


def inner_end(forged, mach, spl):
    out = []
    # splined stub + circlip groove, seal journal
    P = [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.105, 0.02, 0), (0.105, 0.06, 0), (0.09, 0.065, 0), (0.09, 0.085, 0),
         (0.112, 0.09, 0), (0.112, 0.48, 0), (0.13, 0.50, 0), (0.19, 0.52, 1), (0.19, 0.70, 0), (0.0, 0.70, 0)]
    ob = C.lathe("InnerStub", P, [spl, mach], steps=288, mod=spline_mod(0.09, 0.48, 0.112, 26, 0.016))
    out.append(C.finalize(ob, angle=40))
    # tri-lobe tripod housing (tulip)
    def lobe(r, z, t):
        if r < 0.30:
            return r
        return r + 0.035 * math.cos(3 * t)
    P = [(0.0, 0.66, 0), (0.20, 0.66, 0), (0.30, 0.72, 0), (0.38, 0.80, 0), (0.40, 0.86, 0),
         (0.40, 1.38, 0), (0.385, 1.44, 0), (0.35, 1.47, 0), (0.345, 1.52, 0), (0.0, 1.52, 0)]
    ob = C.lathe("Tulip", P, [forged], steps=192, mod=lobe)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35))
    return out


def shaft(shaft_m, rubber, steel):
    out = []
    P = [(0.0, 2.30, 0), (RS, 2.30, 0), (RS, Z_OBS + 0.15, 0), (0.0, Z_OBS + 0.15, 0)]
    out.append(C.finalize(C.lathe("Shaft", P, [shaft_m], steps=64), angle=40))
    # vibration damper: steel mass on rubber collars
    zc = 3.55
    P = [(RS - 0.005, zc - 0.32, 0), (0.15, zc - 0.32, 0), (0.17, zc - 0.29, 0), (0.17, zc + 0.29, 0),
         (0.15, zc + 0.32, 0), (RS - 0.005, zc + 0.32, 0)]
    out.append(C.finalize(C.lathe("DamperRubber", P, [rubber], steps=96), angle=40))
    P = [(0.16, zc - 0.25, 0), (0.235, zc - 0.25, 0), (0.25, zc - 0.235, 0), (0.25, zc + 0.235, 0),
         (0.235, zc + 0.25, 0), (0.16, zc + 0.25, 0)]
    out.append(C.finalize(C.lathe("DamperMass", P, [shaft_m], steps=128), angle=40))
    return out


def outer_end(forged, mach, spl, tone, thread):
    out = []
    # bell of the Rzeppa joint
    P = [(0.0, Z_OB - 0.02, 0), (0.36, Z_OB - 0.02, 0), (0.40, Z_OB + 0.02, 0), (0.44, Z_OB + 0.10, 0),
         (0.47, Z_OB + 0.22, 0), (0.48, Z_OB + 0.36, 0), (0.465, Z_OB + 0.52, 0), (0.43, Z_OB + 0.64, 0),
         (0.37, Z_OB + 0.74, 0), (0.33, Z_OB + 0.80, 0), (0.0, Z_OB + 0.80, 0)]
    ob = C.lathe("Bell", P, [forged], steps=192)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35))
    # ABS tone ring pressed onto the bell shoulder
    zt = Z_OB + 0.62
    def teeth(r, z, t):
        if r < 0.47:
            return r
        v = math.cos(46 * t)
        sq = max(-1.0, min(1.0, v * 3.0)) * 0.5 + 0.5
        return 0.455 + (r - 0.455) * sq
    P = [(0.40, zt - 0.05, 0), (0.455, zt - 0.05, 0), (0.50, zt - 0.05, 0), (0.50, zt + 0.05, 0),
         (0.455, zt + 0.05, 0), (0.40, zt + 0.05, 0)]
    ob = C.lathe("ToneRing", P, [tone], steps=46 * 8, mod=teeth)
    C.add_bevel(ob, 0.003, segments=1, angle=40)
    out.append(C.finalize(ob, angle=40))
    # hub seat face + splined stub + threaded end
    z0 = Z_OB + 0.80
    P = [(0.0, z0 - 0.01, 0), (0.31, z0 - 0.01, 0), (0.31, z0 + 0.05, 1), (0.29, z0 + 0.07, 1), (0.17, z0 + 0.09, 0),
         (0.15, z0 + 0.12, 0), (0.155, z0 + 0.14, 0), (0.155, z0 + 0.72, 0), (0.135, z0 + 0.75, 0), (0.0, z0 + 0.75, 0)]
    ob = C.lathe("OuterStub", P, [forged, mach], steps=320, mod=spline_mod(z0 + 0.14, z0 + 0.72, 0.155, 30, 0.018))
    out.append(C.finalize(ob, angle=40))
    out.append(C.finalize(C.lathe("Thread", thread_prof(z0 + 0.74, z0 + 1.10, 0.106, 0.092, 0.017), [thread], steps=64), angle=60))
    return out


def thread_prof(za, zb, ro, ri, pitch):
    """solid threaded section: V-teeth (as rings) between za and zb, chamfered end."""
    P = [(0.0, za, 0), (ri, za, 0)]
    z = za + pitch / 2
    while z < zb - 0.03:
        P += [(ro, z, 0), (ri, z + pitch / 2, 0)]
        z += pitch
    P += [(ri, zb - 0.012, 0), (ri - 0.012, zb, 0), (0.0, zb, 0)]
    return P


def thread_mat(name, color, rough=0.3):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = 60.0
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.01
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def forged_steel(name, base=0.30, rough=0.38):
    m = C.principled(name, (base, base, base * 1.01), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(nz.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.75, base * 0.74, base * 0.72, 1)
    col.inputs["B"].default_value = (base * 1.1, base * 1.1, base * 1.1, 1)
    em = C.edge_mask(nt, 0.01, 4.0)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(em, col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.62, 0.62, 0.62, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.10
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 500.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def build():
    forged = forged_steel("ForgedSteel", base=0.34, rough=0.36)
    mach = C.mat_machined("Journal", color=0.62, rough=0.16, rings=1400)
    spl = C.principled("Splines", (0.40, 0.40, 0.41), metallic=1.0, rough=0.28)
    C.add_noise_bump(spl, scale=700, strength=0.04, distance=0.0005, rough_var=0.06)
    shaft_m = forged_steel("ShaftSteel", base=0.12, rough=0.42)
    tone = C.principled("ToneRing", (0.30, 0.30, 0.31), metallic=1.0, rough=0.32)
    C.add_noise_bump(tone, scale=600, strength=0.05, distance=0.0005, rough_var=0.06)
    thread = thread_mat("Thread", (0.50, 0.50, 0.51), rough=0.3)
    rubber = C.mat_rubber("BootRubber")
    rb = next(n for n in rubber.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rb.inputs["Roughness"].default_value = 0.55
    clampm = C.principled("ClampZinc", (0.70, 0.71, 0.73), metallic=1.0, rough=0.26)
    C.add_noise_bump(clampm, scale=800, strength=0.03, distance=0.0005)

    objs = inner_end(forged, mach, spl)
    objs.append(bellows("InnerBoot", Z_IB - 0.02, 0.37, Z_IBE, RS + 0.045, 6, 0.07, rubber))
    objs += clamp("ClampIn1", Z_IB + 0.05, 0.372, 0.05, clampm, ear_th=math.radians(80))
    objs += clamp("ClampIn2", Z_IBE - 0.05, RS + 0.047, 0.04, clampm, ear_th=math.radians(100))
    objs += shaft(shaft_m, rubber, clampm)
    objs.append(bellows("OuterBoot", Z_OBS, RS + 0.045, Z_OB + 0.04, 0.42, 7, 0.075, rubber))
    objs += clamp("ClampOut1", Z_OB - 0.03, 0.422, 0.055, clampm, ear_th=math.radians(85))
    objs += clamp("ClampOut2", Z_OBS + 0.05, RS + 0.047, 0.04, clampm, ear_th=math.radians(95))
    objs += outer_end(forged, mach, spl, tone, thread)
    # axis Z -> X (gearbox end left), slight turn for depth
    C.transform_all(objs, Matrix.Rotation(math.radians(-34), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "Y"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("semiasse", objs, "semiasse.py",
            "CV drive shaft: splined inner stub and tripod housing, two black rubber bellows with clamps, "
            "steel shaft with vibration damper, outer CV joint with ABS tone ring, splined threaded wheel stub",
            az=8, el=30, lens=70, fill=0.92, samples=S, res=(R, R))
