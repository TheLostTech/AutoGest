"""Clutch master cylinder (pompa frizione): small cast-aluminium cylinder body with
casting ribs, oval two-stud mounting flange for the pedal-box bulkhead, reservoir feed
spigot on top (angled hose barb in a rubber grommet), outlet port at the front with a
flare nut and a short steel pipe stub, black rubber dust boot at the back and the
chromed pushrod with adjusting thread, lock nut and the clevis fork with its pin and
spring clip.

Cylinder axis along +X (outlet at +X); units ~ decimetres (~25 cm overall)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("FAST"))
RY = Matrix.Rotation(math.radians(90), 4, "Y")      # lathe Z -> world +X
RYn = Matrix.Rotation(math.radians(-90), 4, "Y")    # lathe Z -> world -X
RB = 0.17           # body radius
XF = 1.30           # front end of the body


def fin(ob, bevel=None, angle=35, seg=2, cutters=()):
    for c in cutters:
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return C.finalize(ob, angle=angle, remove=list(cutters))


def lathe_at(name, prof, mats, M, steps=96, bevel=None, angle=40, mod=None, cutters=()):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = M
    return fin(ob, bevel=bevel, angle=angle, cutters=cutters)


def hexp(name, r, z0, z1, mat, M, bevel=0.006):
    bm = bmesh.new()
    C.cyl_bm(bm, r, z0, z1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    return fin(C.mesh_obj(name, bm, [mat]), bevel=bevel)


def axis_matrix(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def frames_along(pts, sec):
    out = []
    n = len(pts)
    prevU = None
    for i, P in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prevU is None:
            U = T.cross(Vector((0, 0, 1)))
            if U.length < 1e-4:
                U = T.cross(Vector((1, 0, 0)))
        else:
            U = prevU - T * prevU.dot(T)
        U.normalize()
        V = T.cross(U).normalized()
        prevU = U
        out.append((P, U, V, sec))
    return out


def bezier(p0, p1, p2, p3, n):
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / n for i in range(n + 1))]


def thread_mat(name, color, rough=0.3, scale=40.0):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = scale
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.008
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_cast_alu(name, base=0.46, rough=0.44):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 8.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.05
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = 1.0
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.05, base * 1.03, 1)
    mix1.inputs["B"].default_value = (base * 0.82, base * 0.81, base * 0.77, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.13, 0.12, 0.10, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 600.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.14
    bp.inputs["Distance"].default_value = 0.0006
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def body(alu, steel, rubber, black, pipe_m):
    out = []
    P = [(0.0, 0.0, 0), (RB, 0.0, 0), (RB, 0.20, 0), (RB + 0.02, 0.22, 0), (RB + 0.02, 0.30, 0), (RB, 0.32, 0),
         (RB - 0.01, XF - 0.20, 0), (RB - 0.03, XF - 0.12, 0), (0.12, XF - 0.10, 0), (0.12, XF, 0), (0.0, XF, 0)]
    out.append(lathe_at("Body", P, [alu], RY, steps=96, bevel=0.008))
    # casting ribs along the underside and flanks
    bm = bmesh.new()
    for a in (math.radians(-90), math.radians(-30), math.radians(-150)):
        M = Matrix.Rotation(a, 4, "X") @ Matrix.Translation((0.72, 0, RB - 0.01))
        C.box_bm(bm, 0.78, 0.035, 0.05, matrix=M)
    out.append(fin(C.mesh_obj("Ribs", bm, [alu]), bevel=0.012))
    # oval mounting flange at the rear with two studs
    bm = bmesh.new()
    n = 40
    sec = []
    for i in range(n):
        t = math.tau * i / n
        c, s = math.cos(t), math.sin(t)
        # stadium shape: long along Y
        y = 0.42 * math.copysign(abs(c) ** 0.6, c)
        z = 0.20 * s
        sec.append((y, z))
    C.sweep(bm, [(Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec) for x in (0.0, 0.075)])
    C.fix_normals(bm)
    fl = C.mesh_obj("Flange", bm, [alu])
    cb = bmesh.new()
    for sy in (-1, 1):
        C.cyl_bm(cb, 0.04, -0.3, 0.3, seg=24, matrix=Matrix.Translation((0, sy * 0.31, 0)) @ RY)
    out.append(fin(fl, bevel=0.012, cutters=[C.mesh_obj("FlHoles", cb, [])]))
    for sy in (-1, 1):
        out.append(lathe_at("Stud", [(0.0, -0.32, 0), (0.038, -0.32, 0), (0.038, 0.0, 0), (0.0, 0.0, 0)],
                            [steel], Matrix.Translation((0.0, sy * 0.31, 0)) @ RY, steps=24))
        out.append(hexp("StudHead", 0.065, 0.0, 0.035, steel, Matrix.Translation((0.075, sy * 0.31, 0)) @ RY))
    # reservoir feed: boss, grommet and angled barb on top
    xr = 0.78
    out.append(lathe_at("FeedBoss", [(0.0, 0.0, 0), (0.12, 0.0, 0), (0.12, RB + 0.08, 0), (0.105, RB + 0.095, 0), (0.0, RB + 0.095, 0)],
                        [alu], Matrix.Translation((xr, 0, 0)), steps=64, bevel=0.006))
    out.append(lathe_at("Grommet", [(0.0, RB + 0.09, 0), (0.10, RB + 0.09, 0), (0.11, RB + 0.11, 0), (0.09, RB + 0.15, 0),
                                    (0.0, RB + 0.15, 0)], [rubber], Matrix.Translation((xr, 0, 0)), steps=48, angle=50))
    Mb = Matrix.Translation((xr, 0, RB + 0.15)) @ Matrix.Rotation(math.radians(-55), 4, "Y")
    P = [(0.0, -0.06, 0), (0.05, -0.06, 0), (0.05, 0.10, 0), (0.062, 0.12, 0), (0.045, 0.16, 0), (0.062, 0.19, 0),
         (0.045, 0.23, 0), (0.035, 0.23, 0), (0.0, 0.23, 0)]
    out.append(lathe_at("Barb", P, [black], Mb, steps=48, bevel=0.003))
    # outlet: flare nut + short pipe curling down
    out.append(hexp("FlareNut", 0.075, 0.0, 0.10, steel, Matrix.Translation((XF, 0, 0)) @ RY, bevel=0.008))
    p0 = Vector((XF + 0.10, 0, 0))
    pts = bezier(p0, p0 + Vector((0.25, 0, 0)), p0 + Vector((0.35, -0.08, -0.15)), p0 + Vector((0.30, -0.20, -0.42)), 30)
    sec = [(0.028 * math.cos(math.tau * j / 16), 0.028 * math.sin(math.tau * j / 16)) for j in range(16)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec))
    out.append(fin(C.mesh_obj("Pipe", bm, [pipe_m]), angle=60))
    T = (pts[-1] - pts[-2]).normalized()
    out.append(hexp("PipeNut", 0.065, -0.10, 0.0, steel, axis_matrix(pts[-1], T), bevel=0.007))
    return out


def pushrod(rubber, chrome, thread, zinc, forged):
    out = []
    # dust boot behind the flange (toward -X)
    P = [(0.0, 0.0, 0), (0.15, 0.0, 0), (0.155, 0.04, 0), (0.12, 0.08, 0), (0.135, 0.12, 0), (0.10, 0.16, 0),
         (0.115, 0.20, 0), (0.08, 0.24, 0), (0.09, 0.28, 0), (0.055, 0.32, 0), (0.05, 0.36, 0), (0.0, 0.36, 0)]
    out.append(lathe_at("Boot", P, [rubber], RYn, steps=96, angle=50))
    out.append(lathe_at("Rod", [(0.0, 0.30, 0), (0.042, 0.30, 0), (0.042, 1.00, 0), (0.0, 1.00, 0)], [chrome], RYn, steps=32))
    out.append(lathe_at("RodThread", [(0.0, 0.98, 0), (0.046, 0.98, 0), (0.046, 1.30, 0), (0.0, 1.30, 0)], [thread], RYn, steps=32))
    out.append(hexp("LockNut", 0.085, 1.10, 1.17, zinc, RYn, bevel=0.008))
    # clevis fork: threaded boss + two ears with cross hole (pin along Z)
    xc = 1.17
    out.append(lathe_at("ClevisBoss", [(0.0, xc, 0), (0.085, xc, 0), (0.09, xc + 0.02, 0), (0.09, xc + 0.20, 0), (0.0, xc + 0.20, 0)],
                        [forged], RYn, steps=48, bevel=0.006))
    bm = bmesh.new()
    C.box_bm(bm, 0.07, 0.20, 0.15, center=(-(xc + 0.235), 0, 0))
    for sz in (-1, 1):
        C.box_bm(bm, 0.30, 0.20, 0.045, center=(-(xc + 0.40), 0, sz * 0.075))
        C.cyl_bm(bm, 0.10, sz * 0.075 - 0.0225, sz * 0.075 + 0.0225, seg=32, matrix=Matrix.Translation((-(xc + 0.55), 0, 0)))
    cb = bmesh.new()
    C.cyl_bm(cb, 0.04, -0.3, 0.3, seg=24, matrix=Matrix.Translation((-(xc + 0.55), 0, 0)))
    out.append(fin(C.mesh_obj("Clevis", bm, [forged]), bevel=0.01, cutters=[C.mesh_obj("PinHole", cb, [])]))
    # clevis pin with head + spring clip
    out.append(lathe_at("Pin", [(0.0, -0.16, 0), (0.038, -0.16, 0), (0.038, 0.13, 0), (0.0, 0.13, 0)], [zinc],
                        Matrix.Translation((-(xc + 0.55), 0, 0)), steps=24))
    out.append(lathe_at("PinHead", [(0.0, 0.10, 0), (0.065, 0.10, 0), (0.065, 0.135, 0), (0.05, 0.15, 0), (0.0, 0.15, 0)], [zinc],
                        Matrix.Translation((-(xc + 0.55), 0, 0)), steps=32))
    pts = [Vector((-(xc + 0.55) + 0.06 * math.cos(t), 0.06 * math.sin(t), -0.135)) for t in
           (math.radians(a) for a in range(-160, 170, 10))]
    pts.append(pts[-1] + Vector((0.12, 0.0, 0)))
    sec = [(0.009 * math.cos(math.tau * j / 8), 0.009 * math.sin(math.tau * j / 8)) for j in range(8)]
    bm = bmesh.new()
    C.sweep(bm, frames_along(pts, sec))
    out.append(fin(C.mesh_obj("Clip", bm, [zinc]), angle=60))
    return out


def build():
    alu = mat_cast_alu("MasterAlu", base=0.46, rough=0.44)
    steel = C.principled("Zinc", (0.64, 0.64, 0.60), metallic=1.0, rough=0.26)
    C.add_noise_bump(steel, scale=900, strength=0.03, distance=0.0005)
    rubber = C.mat_rubber("BootRubber")
    black = C.mat_black_plastic("BarbPA", rough=0.42, color=0.03)
    pipe_m = C.principled("PipeSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.28)
    chrome = C.principled("RodChrome", (0.80, 0.80, 0.81), metallic=1.0, rough=0.10)
    thread = thread_mat("Thread", (0.55, 0.55, 0.56), rough=0.28, scale=40.0)
    forged = C.principled("ClevisSteel", (0.26, 0.26, 0.27), metallic=1.0, rough=0.38)
    C.add_noise_bump(forged, scale=500, strength=0.06, distance=0.0006, rough_var=0.08)
    objs = body(alu, steel, rubber, black, pipe_m) + pushrod(rubber, chrome, thread, steel, forged)
    C.transform_all(objs, Matrix.Rotation(math.radians(-25), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("pompa-frizione", objs, "pompa-frizione.py",
            "clutch master cylinder: cast-aluminium body with oval two-stud mounting flange, reservoir hose "
            "spigot, outlet flare nut and pipe stub, rubber boot, pushrod with clevis fork and pin",
            az=30, el=26, lens=70, fill=0.88, **kw)
