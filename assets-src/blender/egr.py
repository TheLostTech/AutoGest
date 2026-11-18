"""EGR valve (exhaust gas recirculation) from a small diesel: grimy cast-aluminium
valve body with mounting lugs, 2-bolt lozenge exhaust flange whose port and face
are blackened by soot, outlet spigot below, crimped steel ring and black plastic
electric actuator on top with ribs and a connector shroud.

1 unit = 100 mm. Flange faces -Y (toward the camera)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RXp = Matrix.Rotation(math.pi / 2, 4, "X")    # local Z -> -Y
RY = Matrix.Rotation(math.pi / 2, 4, "Y")     # local Z -> +X
PORT = Vector((0.0, -0.60, 0.26))             # centre of the flange face
ZT = 0.52                                     # top of the valve body


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


def sooty_alu(name, base=0.34, rough=0.55, soot_center=None, soot_r=(0.20, 0.42)):
    """Grimy cast aluminium; optional soot halo around a point (object space)."""
    m = C.principled(name, (base, base, base * 0.98), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.15
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 0.9
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.04, base * 1.0, 1)
    mix1.inputs["B"].default_value = (base * 0.72, base * 0.68, base * 0.60, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    fac = g.outputs["Result"]
    if soot_center is not None:
        d = nt.nodes.new("ShaderNodeVectorMath"); d.operation = "DISTANCE"
        nt.links.new(co, d.inputs[0])
        d.inputs[1].default_value = tuple(soot_center)
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = soot_r[0]
        mr.inputs["From Max"].default_value = soot_r[1]
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(d.outputs["Value"], mr.inputs["Value"])
        # break the halo up with fine blotchy noise (sharp-ish soot edge)
        nz2 = nt.nodes.new("ShaderNodeTexNoise")
        nt.links.new(co, nz2.inputs["Vector"])
        nz2.inputs["Scale"].default_value = 18.0
        nz2.inputs["Detail"].default_value = 8.0
        nb = nt.nodes.new("ShaderNodeMapRange")
        nb.inputs["To Min"].default_value = -0.55
        nb.inputs["To Max"].default_value = 0.55
        nt.links.new(nz2.outputs["Fac"], nb.inputs["Value"])
        # noise only modulates where the halo already is: fac = clamp((mr + 2*nb*mr) * 1.5)
        nm = nt.nodes.new("ShaderNodeMath"); nm.operation = "MULTIPLY"
        nt.links.new(nb.outputs["Result"], nm.inputs[0])
        nt.links.new(mr.outputs["Result"], nm.inputs[1])
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"
        nt.links.new(nm.outputs[0], add.inputs[0])
        add.inputs[1].default_value = 2.0
        nt.links.new(mr.outputs["Result"], add.inputs[2])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.use_clamp = True
        mul.inputs[1].default_value = 1.5
        nt.links.new(add.outputs[0], mul.inputs[0])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.use_clamp = True
        nt.links.new(g.outputs["Result"], mx.inputs[0])
        nt.links.new(mul.outputs[0], mx.inputs[1])
        fac = mx.outputs[0]
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(fac, mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.03, 0.026, 0.022, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.05
    rr.inputs["To Max"].default_value = 0.85
    nt.links.new(fac, rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["To Min"].default_value = 1.0
    mm.inputs["To Max"].default_value = 0.2
    nt.links.new(fac, mm.inputs["Value"])
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 220.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.2
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def body(alu, soot):
    out = []
    # main casting: rounded block + cylindrical valve chamber
    def blk(bm):
        C.box_bm(bm, 0.86, 0.66, ZT - 0.06, center=(0.0, 0.0, 0.06 + (ZT - 0.06) / 2))
        # mounting lugs
        for (x, y) in ((0.50, 0.22), (-0.50, 0.22)):
            C.box_bm(bm, 0.22, 0.16, 0.12, center=(x, y, 0.12))
            C.cyl_bm(bm, 0.08, 0.06, 0.18, seg=24, matrix=Matrix.Translation((x + (0.08 if x > 0 else -0.08), y, 0)))
    out.append(solid("Body", blk, [alu], bevel=0.05, seg=3))
    out.append(lathe_at("Neck", [(0.19, 0.0, 1), (0.19, 0.32, 0), (0.25, 0.32, 0), (0.25, 0.0, 0)], alu,
                        Matrix.Translation((0, -0.20, 0.26)) @ RXp, steps=48, bevel=0.01, mats=[alu, soot]))
    # vertical cast ribs on the body front
    def ribs(bm):
        for x in (-0.30, 0.30):
            C.box_bm(bm, 0.06, 0.06, ZT - 0.14, center=(x, -0.33, 0.10 + (ZT - 0.14) / 2))
    out.append(solid("Ribs", ribs, [alu], bevel=0.02))
    # outlet spigot below
    out.append(lathe_at("Outlet", [(0.15, -0.14, 1), (0.21, -0.14, 0), (0.22, -0.12, 0), (0.22, -0.06, 0), (0.20, -0.04, 0),
                                   (0.20, 0.08, 0), (0.0, 0.08, 0), (0.0, -0.10, 0), (0.15, -0.10, 1)], alu,
                        Matrix.Translation((0.05, 0.05, 0)), steps=64, mats=[alu, soot]))
    return out


def flange(fl_m, soot, steel):
    out = []
    poly = hull2d(circle_pts(-0.46, 0.0, 0.15) + circle_pts(0.46, 0.0, 0.15) + circle_pts(0.0, 0.0, 0.32, 64))
    sec = resample(poly, 128)
    M = Matrix.Translation(PORT) @ RXp                    # local z along -Y
    def fl(bm):
        prism_bm(bm, sec, -0.11, 0.0, M)
    def holes(bm):
        C.cyl_bm(bm, 0.19, -0.5, 0.05, seg=64, matrix=M)
        for x in (-0.46, 0.46):
            C.cyl_bm(bm, 0.055, -0.5, 0.05, seg=24, matrix=M @ Matrix.Translation((x, 0, 0)))
    hc = cutter("FlHoles", holes, soot)
    out.append(solid("Flange", fl, [fl_m], bevel=0.016, cutters=[hc]))
    # dark throat (blind) so the port reads deep
    out.append(lathe_at("Throat", [(0.0, -0.275, 0), (0.20, -0.275, 0), (0.20, -0.265, 0), (0.0, -0.265, 0)], soot, M, steps=48))
    # poppet valve head visible deep inside
    out.append(lathe_at("Poppet", [(0.0, -0.26, 0), (0.14, -0.26, 0), (0.11, -0.23, 0), (0.03, -0.20, 0), (0.0, -0.20, 0)], soot, M, steps=48))
    # compression sleeves in the bolt holes
    for x in (-0.46, 0.46):
        out.append(lathe_at("Sleeve", [(0.042, -0.112, 0), (0.056, -0.112, 0), (0.056, 0.004, 0), (0.042, 0.004, 0)], steel,
                            M @ Matrix.Translation((x, 0, 0)), steps=24))
    return out


def actuator(black, ring_m, screw, dark):
    out = []
    # crimp ring
    out.append(lathe_at("Crimp", [(0.0, ZT - 0.02, 0), (0.44, ZT - 0.02, 0), (0.455, ZT, 0), (0.455, ZT + 0.06, 0),
                                  (0.43, ZT + 0.08, 0), (0.0, ZT + 0.08, 0)], ring_m, steps=128, bevel=0.003))

    def rib(r, z, t):
        if r < 0.40 or not (ZT + 0.14 < z < ZT + 0.44):
            return r
        v = math.cos(16 * t)
        return r + 0.018 * (max(-1, min(1, (v - 0.6) * 6)) * 0.5 + 0.5)
    P = [(0.0, ZT + 0.07, 0), (0.42, ZT + 0.07, 0), (0.42, ZT + 0.12, 0), (0.405, ZT + 0.14, 0), (0.405, ZT + 0.44, 0),
         (0.38, ZT + 0.50, 0), (0.30, ZT + 0.53, 0), (0.12, ZT + 0.55, 0), (0.0, ZT + 0.55, 0)]
    out.append(lathe_at("Actuator", P, black, steps=192, mod=rib))
    # connector shroud on the side, pointing +X, with latch
    zc = ZT + 0.33
    def con(bm):
        C.box_bm(bm, 0.30, 0.22, 0.26, center=(0.48, -0.06, zc))
        C.box_bm(bm, 0.12, 0.09, 0.04, center=(0.52, -0.06, zc + 0.15))
    def cav(bm):
        C.box_bm(bm, 0.20, 0.17, 0.21, center=(0.60, -0.06, zc))
    hc = cutter("ConnCav", cav, dark)
    out.append(solid("Conn", con, [black], bevel=0.014, cutters=[hc]))
    # moulded top boss + 3 screws on lugs
    out.append(lathe_at("TopBoss", [(0.0, ZT + 0.54, 0), (0.14, ZT + 0.54, 0), (0.14, ZT + 0.58, 0), (0.12, ZT + 0.60, 0), (0.0, ZT + 0.60, 0)],
                        black, steps=48))
    for k in range(3):
        th = math.tau * k / 3 + math.radians(-60)
        x, y = 0.47 * math.cos(th), 0.47 * math.sin(th)
        def lug(bm, x=x, y=y, th=th):
            C.box_bm(bm, 0.12, 0.12, 0.06, center=(x, y, ZT + 0.10), matrix=None)
        out.append(solid("Lug", lug, [black], bevel=0.015))
        out.append(lathe_at("Screw", [(0.0, ZT + 0.13, 0), (0.04, ZT + 0.13, 0), (0.04, ZT + 0.15, 0), (0.03, ZT + 0.165, 0), (0.0, ZT + 0.165, 0)],
                            screw, Matrix.Translation((x, y, 0)), steps=24))
    return out


def build():
    alu = sooty_alu("BodyAlu", base=0.32, rough=0.55)
    fl_m = sooty_alu("FlangeAlu", base=0.40, rough=0.42, soot_center=PORT, soot_r=(0.19, 0.36))
    soot = C.principled("Soot", (0.018, 0.017, 0.016), metallic=0.1, rough=0.9)
    C.add_noise_bump(soot, scale=150, strength=0.3, distance=0.003)
    steel = C.principled("Steel", (0.50, 0.50, 0.52), metallic=1.0, rough=0.3)
    ring = C.principled("CrimpSteel", (0.56, 0.56, 0.58), metallic=1.0, rough=0.26)
    C.add_noise_bump(ring, scale=500, strength=0.04, distance=0.0005)
    black = C.mat_black_plastic("ActuatorPBT", rough=0.42, color=0.022)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    objs = body(alu, soot) + flange(fl_m, soot, steel) + actuator(black, ring, steel, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("egr", objs, "egr.py",
            "EGR valve: cast metal body with 2-bolt exhaust flange and soot-blackened port, black electric actuator with connector",
            az=30, el=24, lens=70, fill=0.82, **kw)
