"""Engine water (coolant) pump: cast-aluminium body with an irregular mounting flange,
five bolt ears with holes and the machined gasket face; on the back the black
composite impeller with curved vanes; on the front the ribbed bearing housing and
long bearing nose carrying a pressed-steel poly-V pulley with hub bolts; weep hole.

Built along local Z (gasket face at z=0, impeller below, pulley above), then
turned so the impeller faces the camera at an angle. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
EARS = [(math.radians(a), r) for a, r in ((15, 0.64), (90, 0.60), (160, 0.66), (230, 0.62), (305, 0.64))]
FT = 0.16          # flange thickness
ZN = 0.80          # end of bearing nose


# ----------------------------------------------------------------- helpers
def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(math.tau * k / n), cy + r * math.sin(math.tau * k / n)) for k in range(n)]


def resample(poly, n):
    L = [0.0]
    P = poly + [poly[0]]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + math.dist(a, b))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


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


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None, mod=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps, mod=mod)
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
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.15
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
    em = C.edge_mask(nt, 0.012, 4.0)
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
    bp.inputs["Strength"].default_value = 0.30
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def flange_outline():
    pts = circle_pts(0.0, 0.0, 0.46, 72)
    for th, r in EARS:
        pts += circle_pts(r * math.cos(th), r * math.sin(th), 0.12, 24)
    return resample(hull2d(pts), 160)


def body(alu, face_m, dark):
    out = []
    sec = flange_outline()
    def fl(bm):
        prism_bm(bm, sec, 0.0, FT, mat=0)
        # thin machined gasket land on the back face
        prism_bm(bm, sec, -0.012, 0.002, mat=1)
    def holes(bm):
        for th, r in EARS:
            C.cyl_bm(bm, 0.048, -0.2, 0.4, seg=24, matrix=Matrix.Translation((r * math.cos(th), r * math.sin(th), 0)))
        C.cyl_bm(bm, 0.40, -0.2, 0.04, seg=96)       # impeller chamber
    hc = cutter("FlHoles", holes, dark)
    bm = bmesh.new(); fl(bm); C.fix_normals(bm)
    ob = C.mesh_obj("Flange", bm, [alu, face_m])
    C.add_boolean(ob, hc).use_self = True
    C.add_bevel(ob, 0.025, segments=3, angle=30)
    out.append(C.finalize(ob, angle=32, remove=[hc]))
    # bolt bosses on the front of each ear
    for th, r in EARS:
        out.append(lathe_at("EarBoss", [(0.048, FT - 0.01, 0), (0.095, FT - 0.01, 0), (0.095, FT + 0.10, 0), (0.08, FT + 0.115, 0),
                                        (0.048, FT + 0.115, 0)], alu, Matrix.Translation((r * math.cos(th), r * math.sin(th), 0)),
                            steps=40, bevel=0.006))
    # bearing housing: cone + nose, with radial ribs
    def rib(r, z, t):
        if not (FT + 0.02 < z < 0.42) or r < 0.2:
            return r
        v = math.cos(6 * t)
        return r + 0.05 * (max(-1, min(1, (v - 0.85) * 12)) * 0.5 + 0.5) * (1 - (z - FT) / 0.34)
    P = [(0.0, FT - 0.01, 0), (0.46, FT - 0.01, 0), (0.44, FT + 0.06, 0), (0.30, FT + 0.22, 0), (0.22, 0.42, 0),
         (0.19, 0.46, 0), (0.19, ZN, 0), (0.17, ZN + 0.02, 0), (0.0, ZN + 0.02, 0)]
    out.append(lathe_at("Housing", P, alu, steps=192, mod=rib, bevel=0.006))
    # weep hole boss
    def weep(bm):
        C.cyl_bm(bm, 0.05, 0.0, 0.10, seg=24, matrix=Matrix.Translation((0, -0.20, 0.52)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    out.append(solid("Weep", weep, [alu], bevel=0.01))
    out.append(lathe_at("WeepHole", [(0.0, 0.0, 0), (0.025, 0.0, 0), (0.025, 0.002, 0), (0.0, 0.002, 0)], dark,
                        Matrix.Translation((0, -0.301, 0.52)) @ Matrix.Rotation(math.pi / 2, 4, "X"), steps=16))
    return out


def impeller(comp, steel):
    out = []
    # back plate disc + hub
    out.append(lathe_at("ImpDisc", [(0.0, -0.06, 0), (0.36, -0.06, 0), (0.36, -0.035, 0), (0.0, -0.035, 0)], comp, steps=96, bevel=0.004))
    out.append(lathe_at("ImpHub", [(0.0, -0.26, 0), (0.06, -0.26, 0), (0.10, -0.22, 0), (0.12, -0.10, 0), (0.12, -0.05, 0), (0.0, -0.05, 0)],
                        comp, steps=48, bevel=0.004))
    out.append(lathe_at("ShaftEnd", [(0.0, -0.275, 0), (0.04, -0.275, 0), (0.04, -0.25, 0), (0.0, -0.25, 0)], steel, steps=24))
    # curved vanes
    def vanes(bm):
        n = 8
        for k in range(n):
            a0 = math.tau * k / n
            pts_o, pts_i = [], []
            for j in range(13):
                t = j / 12
                r = 0.10 + 0.255 * t
                a = a0 + 0.9 * t
                th = 0.016
                # normal in-plane direction for thickness
                pts_o.append(((r + 0.0) * math.cos(a) - th * math.sin(a), (r + 0.0) * math.sin(a) + th * math.cos(a)))
                pts_i.append(((r + 0.0) * math.cos(a) + th * math.sin(a), (r + 0.0) * math.sin(a) - th * math.cos(a)))
            sec = pts_o + pts_i[::-1]
            prism_bm(bm, sec, -0.20, -0.055)
        # vane height tapers toward the rim
        for vv in bm.verts:
            if vv.co.z < -0.1:
                r = math.hypot(vv.co.x, vv.co.y)
                vv.co.z = -0.055 - (0.145 - 0.09 * max(0.0, (r - 0.10) / 0.26))
    out.append(solid("Vanes", vanes, [comp], bevel=0.004, angle=40))
    return out


def pulley(steel, bolt):
    out = []
    z0 = ZN - 0.10
    P = [(0.17, z0, 0), (0.46, z0, 0), (0.48, z0 + 0.015, 0)]
    z = z0 + 0.035
    for i in range(6):
        P += [(0.455, z, 0), (0.478, z + 0.012, 0)]
        z += 0.024
    P += [(0.455, z, 0), (0.48, z + 0.012, 0), (0.48, z + 0.03, 0), (0.46, z + 0.045, 0), (0.30, z + 0.045, 0),
          (0.28, z + 0.02, 0), (0.28, z0 + 0.06, 0), (0.17, z0 + 0.04, 0)]
    out.append(lathe_at("Pulley", P, steel, steps=200, bevel=0.002))
    zt = z + 0.045
    # hub cup and flange with 4 bolts
    out.append(lathe_at("Hub", [(0.0, ZN - 0.02, 0), (0.28, ZN - 0.02, 0), (0.28, zt, 0), (0.0, zt, 0)], steel, steps=96))
    for k in range(4):
        th = math.tau * k / 4 + math.pi / 4
        M = Matrix.Translation((0.18 * math.cos(th), 0.18 * math.sin(th), 0))
        out.append(hex_at("HubBolt", 0.045, zt, zt + 0.05, bolt, M))
        out.append(lathe_at("HubWasher", [(0.0, zt - 0.001, 0), (0.06, zt - 0.001, 0), (0.06, zt + 0.008, 0), (0.0, zt + 0.008, 0)], bolt, M, steps=24))
    out.append(lathe_at("Centre", [(0.0, zt, 0), (0.07, zt, 0), (0.07, zt + 0.02, 0), (0.0, zt + 0.02, 0)], bolt, steps=32))
    return out


def build():
    alu = cast_alu("PumpAlu", base=0.36, rough=0.56, grime=0.7, grain=180.0, wear=0.35)
    face = C.principled("GasketFace", (0.46, 0.46, 0.46), metallic=1.0, rough=0.32)
    C.add_radial_aniso(face, 0.5, "Z", rings_scale=40.0, ring_strength=0.03)
    dark = C.principled("Cavity", (0.03, 0.03, 0.03), metallic=0.5, rough=0.6)
    comp = C.mat_black_plastic("ImpellerPPS", rough=0.40, color=0.03)
    steel = C.principled("PulleySteel", (0.22, 0.22, 0.23), metallic=1.0, rough=0.34)
    C.add_noise_bump(steel, scale=500, strength=0.05, distance=0.0006)
    bolt = C.principled("Zinc", (0.60, 0.60, 0.62), metallic=1.0, rough=0.28)
    objs = body(alu, face, dark) + impeller(comp, bolt) + pulley(steel, bolt)
    # axis: local -Z (impeller) toward the camera-right, slightly down; ears asymmetric
    R = Matrix.Rotation(math.radians(5), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "Y")
    C.transform_all(objs, R)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("pompa-acqua", objs, "pompa-acqua.py",
            "engine water pump: cast aluminium body with bolt flange, black impeller on the back, bearing housing and poly-V pulley on the front",
            az=30, el=22, lens=70, fill=0.82, **kw)
