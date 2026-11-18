"""Steering rack (scatola guida): cast-aluminium rack housing with the pinion tower near
the left end (splined input shaft with dust seal, rack-yoke adjuster plug opposite), two
mounting clamps (stamped steel omega straps with bolt holes over rubber bushes), black
rubber bellows with clamps at both ends, inner tie rods with spanner flats, threaded
adjusters and lock nuts, and forged track-rod ends with rubber-booted ball-joint studs
and nuts.

Rack axis along X; units ~ decimetres (overall width ~1.25 m)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RY = Matrix.Rotation(math.radians(90), 4, "Y")       # lathe Z -> world X
X_PIN = -2.30                                         # pinion tower position
PIN_AX = Vector((0, 0.42, 0.91)).normalized()          # pinion axis (up, leaning back)


def mat_cast_alu(name, base=0.42, rough=0.45, grain=480.0, wear=0.35):
    """Die-cast aluminium: mottled tone, sand-cast grain, brighter worn edges."""
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), mott.inputs["Vector"])
    mott.inputs["Scale"].default_value = 4.0
    mott.inputs["Detail"].default_value = 6.0
    em = C.edge_mask(nt, 0.012, 4.0)
    wmul = nt.nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = wear
    nt.links.new(em, wmul.inputs[0])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(mott.outputs["Fac"], col.inputs["Factor"])
    col.inputs["A"].default_value = (base * 0.80, base * 0.80, base * 0.78, 1)
    col.inputs["B"].default_value = (base * 1.06, base * 1.06, base * 1.05, 1)
    col2 = nt.nodes.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    nt.links.new(wmul.outputs[0], col2.inputs["Factor"])
    nt.links.new(col.outputs["Result"], col2.inputs["A"])
    col2.inputs["B"].default_value = (0.75, 0.75, 0.75, 1)
    nt.links.new(col2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough + 0.07
    rr.inputs["To Max"].default_value = rough - 0.07
    nt.links.new(mott.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = grain
    gr.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def thread_mat(name, color, rough=0.3, scale=70.0, axis="Z"):
    m = C.principled(name, color, metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = axis
    wv.wave_profile = "TRI"
    wv.inputs["Scale"].default_value = scale
    nt.links.new(C._coord(nt), wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.01
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def axis_matrix(origin, axis):
    """matrix mapping local +Z to `axis`, placed at origin."""
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(origin) @ q.to_matrix().to_4x4()


def xlathe(name, prof, mats, steps=96, mod=None, bevel=None, angle=40):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = RY.copy()
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=angle)


def bellows_prof(z0, r0, z1, r1, n, amp):
    """convoluted boot profile between (z0,r0) and (z1,r1) (z0<z1)."""
    P = [(0.0, z0, 0), (r0 - 0.01, z0, 0), (r0, z0 + 0.01, 0)]
    c0, c1 = z0 + 0.12, z1 - 0.12
    P.append((r0, c0, 0))
    m = 180
    lo, hi = min(r0, r1), max(r0, r1)
    for i in range(1, m):
        u = i / m
        z = c0 + (c1 - c0) * u
        env = r0 + (r1 - r0) * u
        rel = (env - lo) / (hi - lo + 1e-9)
        a = amp * (0.5 + 0.5 * rel)
        fold = 0.5 - 0.5 * math.cos(math.tau * n * u)
        P.append((env + a * fold, z, 0))
    P += [(r1, c1, 0), (r1, z1 - 0.01, 0), (r1 - 0.01, z1, 0), (0.0, z1, 0)]
    return P


def band(name, z, r, w, mat):
    P = [(r - 0.01, z - w / 2, 0), (r + 0.010, z - w / 2, 0), (r + 0.016, z - w / 2 + 0.006, 0),
         (r + 0.016, z + w / 2 - 0.006, 0), (r + 0.010, z + w / 2, 0), (r - 0.01, z + w / 2, 0)]
    return xlathe(name, P, [mat], steps=96)


# ----------------------------------------------------------------- housing
def housing(alu, rubber, mach, spl, zinc, black):
    out = []
    P = [(0.0, -3.05, 0), (0.22, -3.05, 0), (0.27, -3.02, 0), (0.30, -2.96, 0), (0.335, -2.86, 0),
         (0.335, -1.78, 0), (0.30, -1.66, 0), (0.255, -1.58, 0), (0.245, -1.50, 0),
         (0.245, 2.42, 0), (0.265, 2.47, 0), (0.29, 2.52, 0), (0.30, 2.58, 0), (0.30, 2.70, 0),
         (0.275, 2.74, 0), (0.22, 2.76, 0), (0.0, 2.76, 0)]
    out.append(xlathe("RackHousing", P, [alu], steps=128, bevel=0.006))
    # cast ribs bridging the pinion tower into the tube
    bm = bmesh.new()
    for dx in (-0.36, 0.36):
        M = Matrix.Translation((X_PIN + dx, 0.10, 0.18)) @ Matrix.Rotation(math.atan2(PIN_AX.y, PIN_AX.z), 4, "X").inverted()
        C.box_bm(bm, 0.07, 0.30, 0.44, matrix=M)
    rib = C.mesh_obj("Ribs", bm, [alu])
    C.add_bevel(rib, 0.02, segments=2, angle=30)
    out.append(C.finalize(rib, angle=35))
    # pinion tower
    T = axis_matrix(Vector((X_PIN, 0, 0)), PIN_AX)
    P = [(0.0, 0.0, 0), (0.34, 0.0, 0), (0.34, 0.50, 0), (0.32, 0.54, 0), (0.25, 0.56, 0),
         (0.25, 0.60, 0), (0.0, 0.60, 0)]
    tw = C.lathe("PinionTower", P, [alu], steps=96)
    tw.matrix_world = T
    C.add_bevel(tw, 0.01, segments=2, angle=35)
    out.append(C.finalize(tw, angle=35))
    # dust seal + splined input shaft
    P = [(0.0, 0.56, 0), (0.18, 0.56, 0), (0.185, 0.60, 0), (0.16, 0.64, 0), (0.135, 0.66, 0), (0.12, 0.70, 0), (0.0, 0.70, 0)]
    sl = C.lathe("DustSeal", P, [rubber], steps=64)
    sl.matrix_world = T
    out.append(C.finalize(sl, angle=40))
    def spl_mod(r, z, t):
        if abs(r - 0.10) > 1e-6 or z < 0.80:
            return r
        v = math.cos(36 * t)
        return r - 0.012 * (1 - (max(-1.0, min(1.0, v * 2.5)) * 0.5 + 0.5))
    P = [(0.0, 0.66, 0), (0.105, 0.66, 0), (0.105, 0.78, 1), (0.10, 0.80, 0), (0.10, 1.12, 0), (0.088, 1.14, 0),
         (0.088, 1.16, 0), (0.10, 1.17, 0), (0.10, 1.24, 0), (0.085, 1.26, 0), (0.0, 1.26, 0)]
    sh = C.lathe("InputShaft", P, [spl, mach], steps=36 * 8, mod=spl_mod)
    sh.matrix_world = T
    out.append(C.finalize(sh, angle=40))
    # rack-yoke adjuster boss + plug (front side, under the tower)
    Ty = axis_matrix(Vector((X_PIN, 0, 0)), Vector((0, -1, -0.15)))
    P = [(0.0, 0.0, 0), (0.22, 0.0, 0), (0.22, 0.36, 0), (0.20, 0.38, 0), (0.0, 0.38, 0)]
    yb = C.lathe("YokeBoss", P, [alu], steps=64)
    yb.matrix_world = Ty
    C.add_bevel(yb, 0.01, segments=2, angle=35)
    out.append(C.finalize(yb, angle=35))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.17, 0.37, 0.42, seg=48)
    C.cyl_bm(bm, 0.11, 0.42, 0.47, seg=6)
    pl = C.mesh_obj("YokePlug", bm, [zinc])
    pl.matrix_world = Ty
    C.add_bevel(pl, 0.008, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    # breather transfer tube between the two bellows, clipped along the housing
    zt, yt = 0.20, -0.25
    pts = [Vector((-3.25, 0.0, 0.17)), Vector((-3.05, yt * 0.6, zt + 0.06)), Vector((-2.75, yt, zt + 0.08)),
           Vector((-1.62, yt, zt + 0.04)), Vector((-1.45, yt, zt)), Vector((2.40, yt, zt)),
           Vector((2.62, yt, zt + 0.08)), Vector((2.88, yt * 0.6, zt + 0.06)), Vector((3.00, 0.0, 0.17))]
    out.append(curve_tube("BreatherTube", pts, 0.03, black))
    return out


def curve_tube(name, pts, radius, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.resolution_u = 16
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = tuple(c) + (1,)
    sp.order_u = 3
    sp.use_endpoint_u = True
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def omega_clamp(x, steel, rubber, zinc):
    out = []
    # rubber bush around the tube
    P = [(0.24, x - 0.22, 0), (0.33, x - 0.22, 0), (0.345, x - 0.20, 0), (0.345, x + 0.20, 0),
         (0.33, x + 0.22, 0), (0.24, x + 0.22, 0)]
    out.append(xlathe("Bush", P, [rubber], steps=96))
    # stamped strap: over the top, legs down, feet outward (y-z plane), width along x
    R, t, w = 0.36, 0.035, 0.34
    zf = -0.30
    path = []
    for i in range(0, 41):
        a = math.pi * i / 40
        path.append(Vector((0, -R * math.cos(a), R * math.sin(a))))
    pts = ([Vector((0, -0.70, zf)), Vector((0, -R - 0.06, zf)), Vector((0, -R, zf + 0.06))] +
           path +
           [Vector((0, R, zf + 0.06)), Vector((0, R + 0.06, zf)), Vector((0, 0.70, zf))])
    # densify the straight runs a little and build frames
    frames = []
    U = Vector((1, 0, 0))
    for i, P in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        T = (b - a).normalized()
        N = U.cross(T).normalized()
        sec = [(-w / 2, -t / 2), (w / 2, -t / 2), (w / 2, t / 2), (-w / 2, t / 2)]
        frames.append((P + Vector((x, 0, 0)), U, N, sec))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    st = C.mesh_obj("Strap", bm, [steel])
    bm = bmesh.new()
    for sy in (-0.56, 0.56):
        C.cyl_bm(bm, 0.055, zf - 0.2, zf + 0.2, seg=32, matrix=Matrix.Translation((x, sy, 0)))
    cut = C.mesh_obj("StrapHoles", bm, [steel])
    C.add_boolean(st, cut)
    C.add_bevel(st, 0.008, segments=2, angle=30)
    out.append(C.finalize(st, angle=35, remove=[cut]))
    # pressed-in steel sleeves in the bolt holes
    for sy in (-0.56, 0.56):
        sl = C.lathe("Sleeve", [(0.036, zf - 0.03, 0), (0.052, zf - 0.03, 0), (0.052, zf + 0.03, 0), (0.036, zf + 0.03, 0)], [zinc], steps=32)
        sl.matrix_world = Matrix.Translation((x, sy, 0))
        out.append(C.finalize(sl, angle=40))
    return out


# ----------------------------------------------------------------- tie rods
def tie_rod(side, x0, rod_m, thread, zinc, forged, rubber, clampm):
    """side = -1 (left) or +1 (right); x0 = housing end (bellows big end)."""
    out = []
    s = side
    L_boot = 1.30
    if s < 0:
        z0, z1 = x0 - L_boot, x0
        P = bellows_prof(z0, 0.12, z1, 0.30, 8, 0.075)
        zc_small, zc_big = z0 + 0.06, z1 - 0.06
    else:
        z0, z1 = x0, x0 + L_boot
        P = bellows_prof(z0, 0.30, z1, 0.12, 8, 0.075)
        zc_small, zc_big = z1 - 0.06, z0 + 0.06
    boot = C.lathe("Boot", P, [rubber], steps=128)
    boot.matrix_world = RY.copy()
    out.append(C.finalize(boot, angle=50))
    out.append(band("BootClampBig", zc_big, 0.30, 0.06, clampm))
    out.append(band("BootClampSmall", zc_small, 0.12, 0.04, clampm))
    xe = x0 + s * L_boot          # boot small end
    # inner tie rod, spanner flats, thread, lock nut
    a, b = sorted((xe - s * 0.1, xe + s * 0.85))
    out.append(xlathe("TieRod", [(0.0, a, 0), (0.078, a, 0), (0.078, b, 0), (0.0, b, 0)], [rod_m], steps=48))
    xf = xe + s * 0.45
    bm = bmesh.new()
    C.cyl_bm(bm, 0.105, -0.09, 0.09, seg=6)
    fl = C.mesh_obj("Flats", bm, [rod_m])
    fl.matrix_world = Matrix.Translation((xf, 0, 0)) @ RY @ Matrix.Rotation(math.radians(30), 4, "Z")
    C.add_bevel(fl, 0.012, segments=2, angle=30)
    out.append(C.finalize(fl, angle=35))
    xt0 = xe + s * 0.85
    a, b = sorted((xt0 - s * 0.02, xt0 + s * 0.30))
    out.append(xlathe("Thread", [(0.0, a, 0), (0.072, a, 0), (0.072, b, 0), (0.0, b, 0)], [thread], steps=48))
    xn = xt0 + s * 0.08
    bm = bmesh.new()
    C.cyl_bm(bm, 0.13, -0.055, 0.055, seg=6)
    nt = C.mesh_obj("LockNut", bm, [zinc])
    nt.matrix_world = Matrix.Translation((xn, 0, 0)) @ RY
    C.add_bevel(nt, 0.012, segments=2, angle=30)
    out.append(C.finalize(nt, angle=35))
    # track-rod end: threaded shank boss, forged arm, ball socket
    xs0 = xn + s * 0.06
    xs1 = xs0 + s * 0.50
    a, b = sorted((xs0, xs1))
    P = [(0.0, a, 0), (0.115, a, 0), (0.125, a + 0.02, 0), (0.125, b - 0.02, 0), (0.115, b, 0), (0.0, b, 0)]
    out.append(xlathe("RodEndShank", P, [forged], steps=64, bevel=0.006))
    xb = xs1 + s * 0.30
    # forged arm: tapered bar from the shank to the socket
    frames = []
    n = 10
    for i in range(n + 1):
        u = i / n
        Pc = Vector((xs1 - s * 0.05 + s * 0.35 * u, 0, 0.02 * u))
        hw = 0.11 - 0.02 * math.sin(math.pi * u)
        hh = 0.10 + 0.03 * u
        sec = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        frames.append((Pc, Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    arm = C.mesh_obj("RodEndArm", bm, [forged])
    C.add_bevel(arm, 0.03, segments=3, angle=30)
    out.append(C.finalize(arm, angle=35))
    # socket (vertical), boot, tapered stud, thread, nut
    P = [(0.0, -0.13, 0), (0.17, -0.13, 0), (0.20, -0.10, 0), (0.205, 0.08, 0), (0.18, 0.13, 0),
         (0.12, 0.16, 0), (0.0, 0.165, 0)]
    so = C.lathe("Socket", P, [forged], steps=96)
    so.matrix_world = Matrix.Translation((xb, 0, 0))
    C.add_bevel(so, 0.008, segments=2, angle=35)
    out.append(C.finalize(so, angle=35))
    P = [(0.0, -0.12, 0), (0.175, -0.12, 0), (0.20, -0.16, 0), (0.205, -0.21, 0), (0.18, -0.26, 0),
         (0.12, -0.30, 0), (0.085, -0.31, 0), (0.0, -0.31, 0)]
    bo = C.lathe("BallBoot", P, [rubber], steps=96)
    bo.matrix_world = Matrix.Translation((xb, 0, 0))
    out.append(C.finalize(bo, angle=50))
    P = [(0.0, -0.30, 0), (0.092, -0.30, 0), (0.07, -0.56, 0), (0.0, -0.56, 0)]
    stud = C.lathe("Stud", P, [rod_m], steps=48)
    stud.matrix_world = Matrix.Translation((xb, 0, 0))
    out.append(C.finalize(stud, angle=40))
    P = [(0.0, -0.56, 0), (0.06, -0.56, 0), (0.06, -0.78, 0), (0.05, -0.79, 0), (0.0, -0.79, 0)]
    th = C.lathe("StudThread", P, [thread], steps=48)
    th.matrix_world = Matrix.Translation((xb, 0, 0))
    out.append(C.finalize(th, angle=40))
    bm = bmesh.new()
    C.cyl_bm(bm, 0.12, -0.70, -0.60, seg=6)
    C.cyl_bm(bm, 0.12, -0.60, -0.585, seg=32, r1=0.10)
    nt = C.mesh_obj("StudNut", bm, [zinc])
    nt.matrix_world = Matrix.Translation((xb, 0, 0))
    C.add_bevel(nt, 0.01, segments=2, angle=30)
    out.append(C.finalize(nt, angle=35))
    return out


def build():
    alu = mat_cast_alu("RackAlu", base=0.40, rough=0.42)
    rubber = C.mat_rubber("BootRubber")
    rb = next(n for n in rubber.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rb.inputs["Roughness"].default_value = 0.55
    mach = C.mat_machined("ShaftMachined", color=0.60, rough=0.18, rings=1400)
    spl = C.principled("Splines", (0.46, 0.46, 0.47), metallic=1.0, rough=0.26)
    C.add_noise_bump(spl, scale=700, strength=0.04, distance=0.0005, rough_var=0.05)
    zinc = C.principled("Zinc", (0.66, 0.67, 0.69), metallic=1.0, rough=0.24)
    C.add_noise_bump(zinc, scale=900, strength=0.03, distance=0.0005)
    rod_m = C.principled("RodSteel", (0.20, 0.20, 0.205), metallic=1.0, rough=0.36)
    C.add_noise_bump(rod_m, scale=600, strength=0.05, distance=0.0005, rough_var=0.08)
    forged = C.mat_cast_iron("ForgedEnd", rust=0.25, base=0.09)
    thread = thread_mat("Thread", (0.52, 0.52, 0.53), rough=0.3, scale=70.0, axis="Z")
    clampm = C.principled("ClampSteel", (0.62, 0.63, 0.65), metallic=1.0, rough=0.28)
    strap = C.mat_paint("StrapBlack", (0.025, 0.025, 0.027, 1), rough=0.4, coat=0.2)
    C.add_noise_bump(strap, scale=700, strength=0.05, distance=0.0005)
    black = C.mat_black_plastic("Cap")

    objs = housing(alu, rubber, mach, spl, zinc, black)
    objs += omega_clamp(-1.25, strap, rubber, zinc)
    objs += omega_clamp(1.95, strap, rubber, zinc)
    objs += tie_rod(-1, -3.05, rod_m, thread, zinc, forged, rubber, clampm)
    objs += tie_rod(+1, 2.76, rod_m, thread, zinc, forged, rubber, clampm)
    C.transform_all(objs, Matrix.Rotation(math.radians(-34), 4, "Z"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("scatola-guida", objs, "scatola-guida.py",
            "steering rack: cast-aluminium housing with pinion and splined input shaft, mounting clamps "
            "with rubber bushes, black rubber bellows, tie rods with lock nuts and ball-joint track-rod ends",
            az=10, el=34, lens=70, fill=0.94, samples=S, res=(R, R))
