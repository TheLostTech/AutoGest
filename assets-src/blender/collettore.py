"""Plastic intake manifold for an inline-4 (glass-filled nylon, black/dark grey):
mounting flange to the head with four ports, bolt holes and steel compression
limiters, four curved runners that loop out and up into a long plenum on top,
stiffening webs, injector bosses, MAP sensor with connector and a vacuum nipple
on the plenum, and the 4-hole throttle-body flange at the end of the plenum.

Head flange in the X-Z plane facing +Y; runners curl toward -Y and up into the
plenum (along X); throttle flange at +X. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # local Z -> +X
RXn = Matrix.Rotation(-math.pi / 2, 4, "X")     # local Z -> +Y
CX = (-1.32, -0.44, 0.44, 1.32)
PL_Y, PL_Z = -0.66, 1.24                        # plenum axis
PATH = [(0.0, 0.0), (-0.40, 0.0), (-0.92, 0.10), (-1.24, 0.45), (-1.26, 0.86), (-1.04, 1.16), (-0.72, 1.26)]


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


def cutter(name, fill, mat):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def lathe_at(name, prof, mat, M=I4, steps=64, bevel=0.0, angle=40, mats=None):
    ob = C.lathe(name, prof, mats or [mat], steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=1, angle=35)
    return C.finalize(ob, angle=angle)


def catmull(pts, n_per=10):
    """Centripetal-ish Catmull-Rom through 2D points -> list of (p, tangent)."""
    P = [Vector(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            p = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            d = 0.5 * ((-p0 + p2) + 2 * (2 * p0 - 5 * p1 + 4 * p2 - p3) * t + 3 * (-p0 + 3 * p1 - 3 * p2 + p3) * t2)
            out.append((p, d.normalized()))
    d = (P[-2] - P[-3]).normalized()
    out.append((P[-2], d))
    return out


def nylon(name, color=0.04, rough=0.55):
    m = C.principled(name, (color, color, color * 1.04), rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 220.0
    nz.inputs["Detail"].default_value = 3.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.08
    mr.inputs["To Max"].default_value = rough + 0.08
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.12
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (color * 1.6, color * 1.55, color * 1.45, 1)
    mix.inputs["B"].default_value = (color, color, color * 1.04, 1)
    nt.links.new(ao.outputs["AO"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ----------------------------------------------------------------- parts
def head_flange(pa, steel, dark):
    out = []
    bolts = [(-1.84, 0.0), (-0.88, 0.28), (0.0, -0.28), (0.88, 0.28), (1.84, 0.0)]
    def fl(bm):
        prism_bm(bm, rrect(3.96, 0.80, 0.16), -0.14, 0.0, RXn)
        # bolt bosses on the back of the flange
        for (x, z) in bolts:
            C.cyl_bm(bm, 0.12, -0.30, -0.10, seg=32, matrix=Matrix.Translation((x, 0, z)) @ RXn)
    def holes(bm):
        for x in CX:
            prism_bm(bm, rrect(0.34, 0.42, 0.13), -0.5, 0.2, Matrix.Translation((x, 0, 0)) @ RXn)
        for (x, z) in bolts:
            C.cyl_bm(bm, 0.062, -0.6, 0.2, seg=24, matrix=Matrix.Translation((x, 0, z)) @ RXn)
    hc = cutter("FlHoles", holes, dark)
    out.append(solid("HeadFlange", fl, [pa], bevel=0.016, cutters=[hc]))
    for (x, z) in bolts:
        out.append(lathe_at("Limiter", [(0.062, -0.30, 0), (0.08, -0.30, 0), (0.08, 0.004, 0), (0.062, 0.004, 0)], steel,
                            Matrix.Translation((x, 0, z)) @ RXn, steps=32))
    # port liners: short hollow necks behind the flange, dark inside, so the ports read deep
    def lin(bm):
        for x in CX:
            prism_bm(bm, rrect(0.44, 0.52, 0.18), -0.36, -0.02, Matrix.Translation((x, 0, 0)) @ RXn)
    def lcut(bm):
        for x in CX:
            prism_bm(bm, rrect(0.34, 0.42, 0.13), -0.60, 0.2, Matrix.Translation((x, 0, 0)) @ RXn)
    lc = cutter("LinerCut", lcut, dark)
    out.append(solid("Liners", lin, [pa], bevel=0.01, cutters=[lc]))
    return out


def runners(pa, dark):
    out = []
    samples = catmull(PATH, 12)
    for x in CX:
        frames = []
        n = len(samples)
        for i, (p, d) in enumerate(samples):
            t = Vector((0, d.x, d.y))
            nrm = Vector((0, -d.y, d.x))
            w = 0.36 + 0.04 * (i / (n - 1))
            frames.append((Vector((x, p.x - 0.12, p.y)), Vector((1, 0, 0)), nrm, rrect(w, 0.40, 0.14)))
        # start inside the flange
        frames = [f for f in frames if f[0].y < -0.33]
        frames.insert(0, (Vector((x, -0.33, 0.0)), Vector((1, 0, 0)), frames[0][2], frames[0][3]))
        bm = bmesh.new()
        fs = C.sweep(bm, frames)
        fs[-2].material_index = 1          # start cap seen through the port: dark
        C.fix_normals(bm)
        ob = C.mesh_obj("Runner", bm, [pa, dark])
        C.add_bevel(ob, 0.01, segments=1, angle=40)
        out.append(C.finalize(ob, angle=45))
    # webs between neighbouring runners (outer curl)
    def webs(bm):
        for x in (-0.88, 0.0, 0.88):
            sec = [(p.x - 0.12, p.y) for (p, d) in catmull(PATH, 6)[3:-3]]
            # thin plate following the curl, slightly inset
            pts = [(y * 0.92, z * 0.92 + 0.08) for (y, z) in sec]
            fr = []
            for (y, z) in pts:
                fr.append((Vector((x, y, z)), Vector((1, 0, 0)), Vector((0, 0, 1)), [(-0.03, -0.12), (0.03, -0.12), (0.03, 0.12), (-0.03, 0.12)]))
            C.sweep(bm, fr)
    out.append(solid("Webs", webs, [pa], bevel=0.008, angle=45))
    return out


def plenum(pa, steel, dark, black, tin):
    out = []
    M = Matrix.Translation((0, PL_Y, PL_Z)) @ RY @ Matrix.Rotation(math.pi / 2, 4, "Z")
    def pl(bm):
        prism_bm(bm, rrect(0.84, 0.64, 0.30), -2.05, 2.02, M)
        # end dome on -X
        prism_bm(bm, rrect(0.70, 0.52, 0.24), -2.15, -2.05, M)
        # moulded ribs around the plenum
        for x in (-1.75, -0.88, 0.0, 0.88, 1.75):
            prism_bm(bm, rrect(0.88, 0.68, 0.32), x - 0.03, x + 0.03, M)
    out.append(solid("Plenum", pl, [pa], bevel=0.02, angle=40))
    # neck + throttle-body flange at +X
    out.append(lathe_at("Neck", [(0.0, 1.95, 0), (0.33, 1.95, 0), (0.33, 2.42, 0), (0.0, 2.42, 0)], pa,
                        Matrix.Translation((0, PL_Y, PL_Z)) @ RY, steps=64, bevel=0.01))
    Mf = Matrix.Translation((0, PL_Y, PL_Z)) @ RY
    def tf(bm):
        prism_bm(bm, rrect(0.96, 0.96, 0.18), 2.40, 2.52, Mf)
    def tholes(bm):
        C.cyl_bm(bm, 0.27, 2.2, 2.7, seg=64, matrix=Mf)
        for sx in (-1, 1):
            for sy in (-1, 1):
                C.cyl_bm(bm, 0.05, 2.2, 2.7, seg=24, matrix=Mf @ Matrix.Translation((sx * 0.35, sy * 0.35, 0)))
    hc = cutter("TFHoles", tholes, dark)
    out.append(solid("ThrottleFlange", tf, [pa], bevel=0.014, cutters=[hc]))
    out.append(lathe_at("TFThroat", [(0.0, 2.10, 0), (0.28, 2.10, 0), (0.28, 2.12, 0), (0.0, 2.12, 0)], dark, Mf, steps=48))
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(lathe_at("TFInsert", [(0.05, 2.40, 0), (0.07, 2.40, 0), (0.07, 2.525, 0), (0.05, 2.525, 0)], steel,
                                Mf @ Matrix.Translation((sx * 0.35, sy * 0.35, 0)), steps=24))
    # MAP sensor on top of the plenum
    zt = PL_Z + 0.32
    def mp(bm):
        C.box_bm(bm, 0.30, 0.26, 0.10, center=(1.15, PL_Y, zt + 0.04))
        C.box_bm(bm, 0.20, 0.20, 0.14, center=(1.15, PL_Y, zt + 0.14))
        C.box_bm(bm, 0.12, 0.24, 0.16, center=(1.15, PL_Y - 0.18, zt + 0.14))
    def mcav(bm):
        C.box_bm(bm, 0.09, 0.2, 0.12, center=(1.15, PL_Y - 0.25, zt + 0.14))
    mc = cutter("MapCav", mcav, dark)
    out.append(solid("MapSensor", mp, [black], bevel=0.012, cutters=[mc]))
    out.append(lathe_at("MapScrew", [(0.0, zt + 0.09, 0), (0.04, zt + 0.09, 0), (0.04, zt + 0.11, 0), (0.03, zt + 0.12, 0), (0.0, zt + 0.12, 0)],
                        steel, Matrix.Translation((1.32, PL_Y + 0.08, 0)), steps=24))
    # vacuum nipple (brake booster) on the plenum
    Mv = Matrix.Translation((-1.2, PL_Y, zt - 0.02))
    out.append(lathe_at("Nipple", [(0.0, 0.0, 0), (0.09, 0.0, 0), (0.09, 0.06, 0), (0.06, 0.08, 0), (0.06, 0.18, 0), (0.075, 0.20, 0),
                                   (0.055, 0.26, 0), (0.035, 0.26, 1), (0.035, 0.12, 1), (0.0, 0.12, 1)], pa, Mv, steps=40,
                        mats=[pa, dark]))
    return out


def injector_bosses(pa, dark):
    out = []
    for x in CX:
        M = Matrix.Translation((x, -0.40, 0.18)) @ Matrix.Rotation(math.radians(-35), 4, "X")
        out.append(lathe_at("InjBoss", [(0.065, 0.0, 1), (0.065, 0.20, 0), (0.11, 0.20, 0), (0.12, 0.18, 0), (0.12, -0.05, 0), (0.0, -0.05, 0), (0.0, 0.10, 0), (0.065, 0.10, 1)],
                            pa, M, steps=40, mats=[pa, dark]))
    return out


def build():
    pa = nylon("PA66GF30", color=0.035, rough=0.55)
    steel = C.principled("Brass", (0.62, 0.50, 0.30), metallic=1.0, rough=0.32)
    C.add_noise_bump(steel, scale=500, strength=0.04, distance=0.0005)
    dark = C.principled("Cavity", (0.006, 0.006, 0.006), rough=0.8)
    black = C.mat_black_plastic("SensorPBT", rough=0.38, color=0.018)
    tin = C.principled("Tin", (0.75, 0.74, 0.70), metallic=1.0, rough=0.2)
    objs = head_flange(pa, steel, dark) + runners(pa, dark) + plenum(pa, steel, dark, black, tin) + injector_bosses(pa, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("collettore", objs, "collettore.py",
            "plastic intake manifold for an inline-4: four curved runners into a plenum, head flange with ports, throttle-body flange",
            az=140, el=26, lens=70, fill=0.86, **kw)
