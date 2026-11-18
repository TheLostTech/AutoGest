"""Common-rail diesel injector (single): heat-tinted nozzle tip and nozzle body, nozzle
retaining nut with copper sealing washer, long slender steel body with O-ring,
high-pressure fuel inlet union on the side (hex + threaded stub), solenoid
magnet nut, black plastic connector head with 2-pin shroud and latch, and the
leak-off (return line) spigot on top.

Built along local Z (nozzle tip at z=0, head at the top), then laid down on the
ground with its axis running diagonally away from the camera.
1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
ZH = 1.40        # top of the steel body / start of plastic head


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


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=()):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    for c in cutters:
        C.add_boolean(ob, c).use_self = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
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


def thread_prof(r_root, r_crest, z0, z1, pitch):
    P = []
    z = z0
    while z + pitch <= z1 + 1e-6:
        P += [(r_root, z, 0), (r_crest, z + pitch * 0.5, 0)]
        z += pitch
    P.append((r_root, z, 0))
    return P


def heat_tint(name):
    """Ground steel with blue/straw heat tint (nozzle end)."""
    m = C.principled(name, (0.30, 0.29, 0.30), metallic=1.0, rough=0.28)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.30
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.06, 0.055, 0.05, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.42, 0.42, 0.43, 1)
    e = cr.elements.new(0.35); e.color = (0.12, 0.13, 0.22, 1)
    e = cr.elements.new(0.65); e.color = (0.40, 0.30, 0.16, 1)
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    C.add_noise_bump(m, scale=900, strength=0.04, distance=0.0003)
    return m


def steel_body(name, color=0.50, rough=0.24):
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    C.add_radial_aniso(m, 0.6, "Z", rings_scale=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 6.0
    nz.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.14
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # faint grime/oxidation
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color, color, color * 1.01, 1)
    mix.inputs["B"].default_value = (color * 0.62, color * 0.58, color * 0.50, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def lower(tint, nut_m, body_m, copper, rubber):
    out = []
    # nozzle: tip + needle guide + nozzle body
    P = [(0.0, -0.01, 0), (0.016, -0.01, 0), (0.026, 0.01, 0), (0.030, 0.05, 0), (0.032, 0.12, 0), (0.05, 0.13, 0),
         (0.078, 0.15, 0), (0.078, 0.30, 0), (0.0, 0.30, 0)]
    out.append(lathe_at("Nozzle", P, tint, steps=64))
    # retaining nut
    P = [(0.0, 0.28, 0), (0.088, 0.28, 0), (0.104, 0.30, 0), (0.106, 0.60, 0), (0.098, 0.63, 0), (0.0, 0.63, 0)]
    out.append(lathe_at("NozzleNut", P, nut_m, steps=96))
    # copper sealing washer
    out.append(lathe_at("Washer", [(0.068, 0.255, 0), (0.112, 0.255, 0), (0.115, 0.262, 0), (0.115, 0.275, 0), (0.112, 0.282, 0),
                                   (0.068, 0.282, 0)], copper, steps=64))
    # body: slender shaft, O-ring groove land, upper body
    P = [(0.0, 0.62, 0), (0.088, 0.62, 0), (0.088, 0.90, 0), (0.080, 0.905, 0), (0.080, 0.945, 0), (0.090, 0.95, 0),
         (0.092, 0.99, 0), (0.115, 1.01, 0), (0.118, 1.03, 0), (0.118, 1.26, 0), (0.11, 1.28, 0), (0.0, 1.28, 0)]
    out.append(lathe_at("Body", P, body_m, steps=96))
    # O-ring
    ring = [(0.080 + 0.022 + 0.022 * math.cos(math.tau * k / 16), 0.925 + 0.022 * math.sin(math.tau * k / 16), 0) for k in range(16)]
    out.append(lathe_at("ORing", ring, rubber, steps=64))
    # solenoid magnet nut (hex) and solenoid body
    out.append(hex_at("MagnetNut", 0.138, 1.28, 1.36, nut_m, bevel=0.01))
    out.append(lathe_at("Solenoid", [(0.0, 1.355, 0), (0.112, 1.355, 0), (0.112, ZH + 0.02, 0), (0.0, ZH + 0.02, 0)], body_m, steps=64))
    return out


def inlet(body_m, nut_m):
    out = []
    # side boss on the upper body, axis along local +X, tilted ~20 deg toward the head
    M = Matrix.Translation((0.0, 0, 1.13)) @ Matrix.Rotation(math.radians(70), 4, "Y")
    P = [(0.0, 0.0, 0), (0.085, 0.0, 0), (0.085, 0.16, 0), (0.07, 0.17, 0), (0.0, 0.17, 0)]
    out.append(lathe_at("InletBoss", P, body_m, M, steps=48, bevel=0.006))
    out.append(hex_at("InletHex", 0.095, 0.17, 0.26, nut_m, M, bevel=0.008))
    th = [(0.0, 0.26, 0)] + thread_prof(0.058, 0.066, 0.27, 0.42, 0.018) + [(0.05, 0.43, 0), (0.035, 0.44, 0), (0.0, 0.44, 0)]
    out.append(lathe_at("InletThread", th, nut_m, M, steps=64, angle=60))
    # sealing cone/bore
    out.append(lathe_at("InletBore", [(0.0, 0.441, 0), (0.026, 0.441, 0), (0.026, 0.442, 0), (0.0, 0.442, 0)],
                        C.principled("Bore", (0.03, 0.03, 0.03), rough=0.6), M, steps=24))
    return out


def head(black, grey, dark):
    out = []
    # overmoulded plastic head
    P = [(0.0, ZH - 0.02, 0), (0.122, ZH - 0.02, 0), (0.126, ZH + 0.02, 0), (0.126, ZH + 0.20, 0), (0.115, ZH + 0.24, 0),
         (0.07, ZH + 0.27, 0), (0.0, ZH + 0.27, 0)]
    out.append(lathe_at("Head", P, black, steps=64))
    # connector shroud pointing along local +Y
    def shroud(bm):
        C.box_bm(bm, 0.12, 0.20, 0.13, center=(0, 0.13, ZH + 0.12))
        C.box_bm(bm, 0.20, 0.17, 0.17, center=(0, 0.28, ZH + 0.12))
        C.box_bm(bm, 0.07, 0.10, 0.03, center=(0, 0.25, ZH + 0.215))   # latch
    cb = bmesh.new()
    C.box_bm(cb, 0.15, 0.20, 0.12, center=(0, 0.36, ZH + 0.12))
    cut = C.mesh_obj("ShroudCut", cb, [dark])
    out.append(solid("Shroud", shroud, [black], bevel=0.012, cutters=[cut]))
    # two pins inside
    bm = bmesh.new()
    for dx in (-0.035, 0.035):
        C.box_bm(bm, 0.014, 0.10, 0.03, center=(dx, 0.30, ZH + 0.12))
    out.append(solid("Pins", lambda b: [C.box_bm(b, 0.014, 0.10, 0.03, center=(dx, 0.30, ZH + 0.12)) for dx in (-0.035, 0.035)],
                     [C.principled("Tin", (0.75, 0.74, 0.70), metallic=1.0, rough=0.2)]))
    bm.free()
    # leak-off (return) spigot on top, slightly off axis toward -Y
    M = Matrix.Translation((0, -0.03, ZH + 0.25))
    P = [(0.0, 0.0, 0), (0.06, 0.0, 0), (0.06, 0.05, 0), (0.042, 0.06, 0), (0.042, 0.11, 0), (0.054, 0.125, 0),
         (0.04, 0.16, 0), (0.026, 0.16, 1), (0.026, 0.10, 1), (0.0, 0.10, 1)]
    out.append(lathe_at("Return", P, grey, M, steps=40, mats=[grey, dark]))
    return out


def build():
    tint = heat_tint("NozzleTint")
    nut = steel_body("NutSteel", 0.56, 0.22)
    body = steel_body("BodySteel", 0.46, 0.30)
    copper = C.principled("Copper", (0.78, 0.40, 0.24), metallic=1.0, rough=0.34)
    C.add_noise_bump(copper, scale=600, strength=0.05, distance=0.0004)
    rubber = C.mat_rubber("ORing")
    black = C.mat_black_plastic("HeadPA", rough=0.42, color=0.022)
    grey = C.mat_black_plastic("ReturnPA", rough=0.5, color=0.05)
    dark = C.principled("Hole", (0.008, 0.008, 0.008), rough=0.8)
    objs = lower(tint, nut, body, copper, rubber) + inlet(body, nut) + head(black, grey, dark)
    # lay it down: local Z (nozzle -> head) toward the camera-left, local +Y (connector) up
    w = Vector((-0.84, -0.54, 0.0)).normalized()
    up = Vector((0, 0, 1))
    xa = up.cross(w)
    R = Matrix(((xa.x, up.x, w.x, 0), (xa.y, up.y, w.y, 0), (xa.z, up.z, w.z, 0), (0, 0, 0, 1)))
    C.transform_all(objs, R)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("iniettore", objs, "iniettore.py",
            "common-rail diesel injector: steel body, nozzle tip with copper washer, side fuel inlet union, black connector head with return port",
            az=0, el=30, lens=80, fill=0.88, **kw)
