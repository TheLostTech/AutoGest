"""Small inline-4 petrol engine (1.2-1.4 L class) as removed from a car: cast-aluminium
block and cylinder head, black ribbed valve cover with four coil-on-plug units and filler
cap, black plastic intake manifold with plenum and throttle body, cast-iron exhaust
manifold behind an embossed aluminised heat shield, black timing-belt cover, crank
pulley with poly-V accessory belt round alternator, idler and water-pump pulleys,
alternator on its cast bracket, blue oil filter, dipstick with yellow handle, oil sump,
flywheel with ring gear on the bellhousing face, coolant hoses and lifting eyes.

Crank axis along X (timing end at +X), exhaust side -Y, intake side +Y, Z up.
1 unit ~ 0.42 m (block length)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

RY = Matrix.Rotation(math.pi / 2, 4, "Y")       # lathe Z -> world +X
CYL_X = (-0.293, -0.098, 0.098, 0.293)          # cylinder centres
BELT_X = (0.612, 0.668)                         # accessory belt plane
PUL = {  # accessory pulleys in the front plane: (y, z, r)
    "crank": (0.0, 0.0, 0.165),
    "alt": (-0.44, 0.27, 0.066),
    "idler": (-0.17, 0.53, 0.068),
    "pump": (0.13, 0.43, 0.105),
}


# ----------------------------------------------------------------- local helpers
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


def circle_pts(cx, cy, r, n=64):
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


def rrect(w, h, r, n=10):
    """Rounded rectangle centred at 0, CCW, in (u, v)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def loft(name, frames, mat):
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    return C.mesh_obj(name, bm, [mat])


def loft_z(name, layers, mat, cx=0.0, cy=0.0):
    """layers: [(z, w, h, r)] rounded-rect sections stacked along Z."""
    fr = [(Vector((cx, cy, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), rrect(w, h, r)) for (z, w, h, r) in layers]
    return loft(name, fr, mat)


def prism_x(name, sec, x0, x1, mat):
    fr = [(Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec) for x in (x0, x1)]
    return loft(name, fr, mat)


def lathe_x(name, prof, mats, at=(0, 0), steps=128, mod=None):
    ob = C.lathe(name, prof, mats, steps=steps, mod=mod)
    ob.matrix_world = Matrix.Translation((0, at[0], at[1])) @ RY
    return ob


def ring_x(name, r0, r1, x0, x1, mat, at=(0, 0), steps=64, ch=0.0):
    P = [(r0, x0, 0), (r1 - ch, x0, 0), (r1, x0 + ch, 0), (r1, x1 - ch, 0), (r1 - ch, x1, 0), (r0, x1, 0)]
    return C.finalize(lathe_x(name, P, [mat], at=at, steps=steps), angle=40)


def lathe_at(name, prof, mat, M, steps=64, mod=None, angle=40):
    ob = C.lathe(name, prof, [mat], steps=steps, mod=mod)
    ob.matrix_world = M
    return C.finalize(ob, angle=angle)


def hex_at(name, r, a0, a1, mat, M, bevel=0.004):
    bm = bmesh.new()
    C.cyl_bm(bm, r, a0, a1, seg=6, matrix=M @ Matrix.Rotation(math.pi / 6, 4, "Z"))
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def boxes(name, specs, mat, bevel=0.01, holes=()):
    """specs: [(sx, sy, sz, center[, matrix])]; holes: [(r, z0, z1, matrix)] boolean cylinders."""
    bm = bmesh.new()
    for s in specs:
        C.box_bm(bm, s[0], s[1], s[2], center=s[3], matrix=(s[4] if len(s) > 4 else None))
    ob = C.mesh_obj(name, bm, [mat])
    cut = None
    if holes:
        cb = bmesh.new()
        for (r, z0, z1, M) in holes:
            C.cyl_bm(cb, r, z0, z1, seg=24, matrix=M)
        cut = C.mesh_obj(name + "Holes", cb, [mat])
        C.add_boolean(ob, cut)
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=32, remove=[cut] if cut else [])


def catmull(pts, n=12):
    """Centripetal-ish Catmull-Rom through pts (Vectors), n samples per segment."""
    P = [pts[0] * 2 - pts[1]] + list(pts) + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1].copy())
    return out


def tube(name, pts, r, mat, res=3, caps=True, seg=20):
    """Round tube along a smooth path, rotation-minimising frames (no twisting)."""
    path = catmull([Vector(p) for p in pts])
    T = [(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() for i in range(len(path))]
    a = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    U = T[0].cross(a).normalized()
    sec = [(r * math.cos(math.tau * k / seg), r * math.sin(math.tau * k / seg)) for k in range(seg)]
    frames = []
    for i, P in enumerate(path):
        if i:
            U = (U - T[i] * U.dot(T[i])).normalized()
        V = T[i].cross(U).normalized()
        frames.append((P, U, V, sec))
    bm = bmesh.new()
    C.sweep(bm, frames, cap=caps)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    for f in ob.data.polygons:
        f.use_smooth = len(f.vertices) == 4
    return ob


# ----------------------------------------------------------------- materials
def cast_alu(name, base=0.42, rough=0.50, grime=0.85):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.10
    g = nt.nodes.new("ShaderNodeMapRange")
    g.inputs["From Min"].default_value = 0.35
    g.inputs["From Max"].default_value = 0.95
    g.inputs["To Min"].default_value = grime
    g.inputs["To Max"].default_value = 0.0
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (base * 1.05, base * 1.05, base * 1.03, 1)
    mix1.inputs["B"].default_value = (base * 0.78, base * 0.76, base * 0.70, 1)
    nt.links.new(nz.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"
    nt.links.new(g.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.09, 0.085, 0.075, 1)
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.25
    nt.links.new(g.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 520.0
    gr.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.16
    bp.inputs["Distance"].default_value = 0.0008
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def worn_paint(name, color, rough=0.32, coat=0.4, wear=0.8, metal=0.5, edge=0.01):
    m = C.mat_paint(name, color, rough=rough, coat=coat)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    em = C.edge_mask(nt, edge, 7.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 30.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.62
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    f = nt.nodes.new("ShaderNodeMath"); f.operation = "MULTIPLY"; f.use_clamp = True
    nt.links.new(em, f.inputs[0]); nt.links.new(mr.outputs["Result"], f.inputs[1])
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"; f2.use_clamp = True
    f2.inputs[1].default_value = wear
    nt.links.new(f.outputs[0], f2.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = color
    mix.inputs["B"].default_value = (metal, metal, metal, 1)
    nt.links.new(f2.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(f2.outputs[0], b.inputs["Metallic"])
    return m


def heat_shield_mat(name="Aluminised"):
    m = C.principled(name, (0.62, 0.62, 0.61), metallic=1.0, rough=0.32)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "SMOOTH_F1"
    vo.inputs["Scale"].default_value = 38.0
    vo.inputs["Randomness"].default_value = 0.25
    nt.links.new(C._coord(nt), vo.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.55
    bp.inputs["Distance"].default_value = 0.006
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.22
    mr.inputs["To Max"].default_value = 0.42
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # heat tint
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.62, 0.62, 0.61, 1)
    mix.inputs["B"].default_value = (0.64, 0.58, 0.50, 1)
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.5
    mr2.inputs["From Max"].default_value = 0.75
    nt.links.new(nz.outputs["Fac"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def block(alu):
    out = []
    sec = [(-0.29, 0.0), (0.29, 0.0), (0.29, 0.15), (0.245, 0.29), (0.245, 0.525), (-0.245, 0.525),
           (-0.245, 0.29), (-0.29, 0.15)]
    sec = [(-y, z) for (y, z) in sec][::-1] if False else sec
    b = prism_x("Block", sec, -0.50, 0.50, alu)
    C.add_bevel(b, 0.014, segments=2, angle=25)
    out.append(C.finalize(b, angle=30))
    # cylinder-wall bulges and vertical ribs on both flanks
    specs = []
    for s in (-1, 1):
        for x in (-0.49, -0.195, 0.0, 0.195, 0.49):
            specs.append((0.028, 0.03, 0.40, (x * 0.96, s * 0.252, 0.32)))
        specs.append((0.98, 0.03, 0.035, (0.0, s * 0.30, 0.12)))
    out.append(boxes("BlockRibs", specs, alu, bevel=0.008))
    for x in CYL_X:
        for s in (-1, 1):
            out.append(lathe_at("Bulge", [(0.0, 0.29, 0), (0.07, 0.29, 0), (0.085, 0.33, 0), (0.085, 0.50, 0), (0.0, 0.50, 0)],
                                alu, Matrix.Translation((x, s * 0.19, 0)), steps=48))
    return out


def sump(alu, steel):
    out = []
    fl = loft_z("SumpFlange", [(-0.035, 0.97, 0.59, 0.04), (0.0, 0.97, 0.59, 0.04)], alu)
    C.add_bevel(fl, 0.008, segments=2, angle=30)
    out.append(C.finalize(fl, angle=30))
    pan = loft_z("Sump", [(-0.30, 0.80, 0.44, 0.07), (-0.25, 0.86, 0.50, 0.07), (-0.035, 0.93, 0.55, 0.05)], alu, cx=-0.02)
    C.add_bevel(pan, 0.02, segments=3, angle=25)
    out.append(C.finalize(pan, angle=30))
    # stiffening ribs on the side of the sump
    specs = [(0.025, 0.03, 0.21, (x, -0.255, -0.15)) for x in (-0.30, -0.10, 0.10, 0.30)]
    out.append(boxes("SumpRibs", specs, alu, bevel=0.008))
    # flange bolts (heads below the flange)
    for x in (-0.44, -0.26, -0.08, 0.10, 0.28, 0.44):
        out.append(hex_at("PanBolt", 0.018, -0.06, -0.035, steel, Matrix.Translation((x, -0.275, 0))))
    # drain plug
    out.append(hex_at("Drain", 0.03, -0.0, 0.035, steel, Matrix.Translation((0.25, -0.24, -0.25)) @ Matrix.Rotation(math.pi / 2, 4, "X")))
    return out


def head(alu, steel):
    out = []
    bm = bmesh.new()
    C.box_bm(bm, 1.0, 0.49, 0.275, center=(0, 0, 0.665))
    C.box_bm(bm, 0.985, 0.47, 0.04, center=(0, 0, 0.79))  # cam-carrier step
    h = C.mesh_obj("Head", bm, [alu])
    C.add_bevel(h, 0.014, segments=2, angle=30)
    out.append(C.finalize(h, angle=30))
    # head gasket edge
    g = loft_z("Gasket", [(0.522, 1.004, 0.494, 0.01), (0.532, 1.004, 0.494, 0.01)], steel)
    out.append(C.finalize(g, angle=30))
    # head bolts heads along the flanks (just visible under the cover lip)
    # lifting eyes
    for (x, y, rot) in ((0.44, -0.20, 0.0), (-0.46, 0.20, math.pi)):
        M = Matrix.Translation((x, y, 0.80)) @ Matrix.Rotation(rot, 4, "Z")
        bm = bmesh.new()
        C.box_bm(bm, 0.09, 0.016, 0.16, center=(0, 0, 0.06), matrix=M)
        C.box_bm(bm, 0.09, 0.06, 0.016, center=(0, 0.03, -0.008), matrix=M)
        e = C.mesh_obj("LiftEye", bm, [steel])
        cb = bmesh.new()
        C.cyl_bm(cb, 0.022, -0.05, 0.05, seg=24, matrix=M @ Matrix.Translation((0, 0, 0.10)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        cut = C.mesh_obj("EyeHole", cb, [steel])
        C.add_boolean(e, cut)
        C.add_bevel(e, 0.006, segments=2, angle=30)
        out.append(C.finalize(e, angle=35, remove=[cut]))
    return out


def valve_cover(black, coil_m, conn_m, steel):
    out = []
    vc = loft_z("ValveCover", [(0.805, 0.985, 0.47, 0.05), (0.83, 0.985, 0.47, 0.05), (0.835, 0.95, 0.44, 0.05),
                               (0.925, 0.93, 0.41, 0.07), (0.955, 0.89, 0.34, 0.09), (0.965, 0.85, 0.28, 0.09)], black)
    C.add_bevel(vc, 0.012, segments=3, angle=20)
    out.append(C.finalize(vc, angle=28))
    # moulded ribs on the cover sides + bolt bosses round the lip
    specs = []
    for x in (-0.40, -0.20, 0.0, 0.20, 0.40):
        for s in (-1, 1):
            specs.append((0.02, 0.03, 0.08, (x, s * 0.207, 0.875), Matrix.Rotation(-s * math.radians(12), 4, "X") if False else None))
    specs = [sp[:4] for sp in specs]
    out.append(boxes("VCRibs", specs, black, bevel=0.006))
    for x in (-0.44, -0.15, 0.15, 0.44):
        for s in (-1, 1):
            out.append(hex_at("VCBolt", 0.017, 0.83, 0.85, steel, Matrix.Translation((x, s * 0.225, 0))))
    # coil-on-plug units in a row
    for x in CYL_X:
        bm = bmesh.new()
        C.box_bm(bm, 0.085, 0.12, 0.065, center=(x, 0.0, 0.995))
        C.box_bm(bm, 0.05, 0.05, 0.016, center=(x + 0.05, 0.035, 0.972))   # fixing ear
        cl = C.mesh_obj("Coil", bm, [coil_m])
        C.add_bevel(cl, 0.014, segments=3, angle=30)
        out.append(C.finalize(cl, angle=30))
        bm = bmesh.new()
        C.box_bm(bm, 0.055, 0.05, 0.045, center=(x, -0.075, 1.0))
        cn = C.mesh_obj("CoilPlug", bm, [conn_m])
        C.add_bevel(cn, 0.008, segments=2, angle=30)
        out.append(C.finalize(cn, angle=30))
        out.append(hex_at("CoilBolt", 0.012, 0.98, 0.992, steel, Matrix.Translation((x + 0.06, 0.035, 0))))
    # small wiring loom along the coils
    pts = [Vector((-0.45, -0.115, 0.972)), Vector((-0.293, -0.112, 0.975)), Vector((-0.098, -0.115, 0.975)),
           Vector((0.098, -0.112, 0.975)), Vector((0.293, -0.115, 0.975)), Vector((0.40, -0.135, 0.968)), Vector((0.46, -0.19, 0.94))]
    out.append(tube("Loom", pts, 0.012, conn_m))
    # oil filler cap with grip ribs
    def knurl(r, z, t):
        return r + (0.006 if (r > 0.05 and math.cos(12 * t) > 0.3) else 0)
    out.append(lathe_at("FillerCap", [(0.0, 0.955, 0), (0.06, 0.955, 0), (0.06, 0.985, 0), (0.052, 1.0, 0), (0.0, 1.0, 0)],
                        black, Matrix.Translation((-0.39, 0.06, 0)), steps=96, mod=knurl))
    return out


def timing_cover(black):
    out = []
    pts = circle_pts(0.0, 0.02, 0.13, 64) + circle_pts(-0.11, 0.69, 0.155, 64) + circle_pts(0.11, 0.69, 0.155, 64)
    sec = resample(hull2d(pts), 160)
    tc = prism_x("TimingCover", sec, 0.49, 0.575, black)
    C.add_bevel(tc, 0.02, segments=3, angle=30)
    out.append(C.finalize(tc, angle=30))
    # split line rib and stiffening ribs
    specs = [(0.02, 0.36, 0.022, (0.585, 0.0, 0.40)), (0.02, 0.022, 0.30, (0.585, -0.12, 0.62)),
             (0.02, 0.022, 0.30, (0.585, 0.12, 0.62))]
    out.append(boxes("TCRibs", specs, black, bevel=0.007))
    return out


def crank_pulley(dark, rubber, steel):
    out = []
    P = [(0.04, 0.575, 0), (0.09, 0.575, 0), (0.09, 0.60, 0), (0.168, 0.605, 0), (0.168, 0.612, 0)]
    x = 0.616
    for i in range(6):
        P += [(0.158, x, 0), (0.168, x + 0.0045, 0)]
        x += 0.009
    P += [(0.158, x, 0), (0.168, x + 0.004, 0), (0.168, 0.685, 0), (0.16, 0.695, 0), (0.135, 0.695, 0),
          (0.13, 0.69, 0), (0.122, 0.69, 0), (0.118, 0.695, 0), (0.07, 0.698, 0), (0.06, 0.712, 0), (0.04, 0.712, 0)]
    out.append(C.finalize(lathe_x("CrankPulley", P, [dark], steps=160), angle=40))
    out.append(ring_x("DamperRubber", 0.118, 0.132, 0.684, 0.693, rubber, steps=128))
    out.append(ring_x("Washer", 0.0, 0.05, 0.712, 0.722, steel, ch=0.003))
    out.append(hex_at("CrankBolt", 0.034, 0.722, 0.76, steel, Matrix.Translation((0, 0, 0)) @ RY @ Matrix.Rotation(0, 4, "Z")))
    return out


def accessory_pulleys(steel, dark, alu):
    out = []
    # water pump pulley: stamped steel dish with 3 bolts
    y, z, r = PUL["pump"]
    P = [(0.04, 0.575, 0), (0.05, 0.575, 0), (0.05, 0.60, 0), (r, 0.605, 0), (r + 0.008, 0.61, 0), (r + 0.008, 0.616, 0),
         (r, 0.62, 0), (r, 0.66, 0), (r + 0.008, 0.664, 0), (r + 0.008, 0.672, 0), (r - 0.01, 0.672, 0), (0.05, 0.668, 0),
         (0.04, 0.668, 0)]
    out.append(C.finalize(lathe_x("PumpPulley", P, [dark], at=(y, z), steps=128), angle=40))
    for k in range(3):
        t = math.tau * k / 3
        out.append(hex_at("PPBolt", 0.013, 0.668, 0.684, steel,
                          Matrix.Translation((0, y + 0.045 * math.cos(t), z + 0.045 * math.sin(t))) @ RY))
    out.append(ring_x("PumpHub", 0.0, 0.05, 0.56, 0.578, alu, at=(y, z)))
    # idler / tensioner: smooth pulley on an arm
    y, z, r = PUL["idler"]
    P = [(0.03, 0.598, 0), (r + 0.006, 0.598, 0), (r + 0.006, 0.606, 0), (r, 0.61, 0), (r, 0.672, 0),
         (r + 0.006, 0.676, 0), (r + 0.006, 0.684, 0), (0.03, 0.684, 0)]
    out.append(C.finalize(lathe_x("Idler", P, [steel], at=(y, z), steps=96), angle=40))
    out.append(ring_x("IdlerCap", 0.0, 0.035, 0.684, 0.70, dark, at=(y, z), ch=0.006))
    arm = boxes("TensArm", [(0.025, 0.06, 0.20, (0.588, y + 0.045, z - 0.085),
                             Matrix.Translation((0, 0, 0)))], dark, bevel=0.008)
    out.append(arm)
    # alternator pulley + alternator body
    y, z, r = PUL["alt"]
    P = [(0.02, 0.585, 0), (r + 0.006, 0.585, 0), (r + 0.006, 0.605, 0)]
    x = 0.612
    for i in range(6):
        P += [(r - 0.008, x, 0), (r + 0.002, x + 0.0045, 0)]
        x += 0.009
    P += [(r - 0.008, x, 0), (r + 0.006, x + 0.004, 0), (r + 0.006, 0.684, 0), (0.02, 0.684, 0)]
    out.append(C.finalize(lathe_x("AltPulley", P, [steel], at=(y, z), steps=128), angle=40))
    out.append(hex_at("AltNut", 0.026, 0.684, 0.71, steel, Matrix.Translation((0, y, z)) @ RY))
    return out


def alternator(alu, steel, black, copper):
    out = []
    y, z, _ = PUL["alt"]

    def ribs(r, xx, t):
        if r < 0.145:
            return r
        return r + 0.008 * (1 if math.cos(22 * t) > 0.2 else 0)
    P = [(0.03, 0.20, 0), (0.12, 0.20, 0), (0.145, 0.215, 0), (0.15, 0.24, 0), (0.15, 0.53, 0), (0.14, 0.555, 0),
         (0.10, 0.565, 0), (0.04, 0.565, 0), (0.04, 0.585, 0), (0.02, 0.585, 0)]
    body = lathe_x("AltBody", P, [alu], at=(y, z), steps=176, mod=ribs)
    # cooling slots
    cb = bmesh.new()
    for k in range(10):
        t = math.tau * (k + 0.5) / 10
        M = Matrix.Translation((0.40, y + 0.15 * math.cos(t), z + 0.15 * math.sin(t))) @ Matrix.Rotation(t, 4, "X")
        C.box_bm(cb, 0.07, 0.06, 0.05, matrix=M)
    cut = C.mesh_obj("AltSlots", cb, [alu])
    C.add_boolean(body, cut)
    C.add_bevel(body, 0.004, segments=2, angle=30)
    out.append(C.finalize(body, angle=35, remove=[cut]))
    out.append(ring_x("AltStator", 0.12, 0.158, 0.37, 0.43, steel, at=(y, z), steps=128))
    out.append(ring_x("AltWinding", 0.0, 0.135, 0.36, 0.44, copper, at=(y, z), steps=64))
    out.append(ring_x("AltRearCap", 0.0, 0.12, 0.18, 0.20, black, at=(y, z), ch=0.012))
    # bracket: cast arms from the block side to the alternator ears
    specs = [(0.06, 0.14, 0.07, (xx, -0.30, z + 0.15)) for xx in (0.26, 0.52)]
    specs += [(0.32, 0.03, 0.16, (0.39, -0.275, z + 0.12))]
    out.append(boxes("AltBracket", specs, alu, bevel=0.012))
    for xx in (0.26, 0.52):
        out.append(ring_x("AltEar", 0.018, 0.045, xx - 0.035, xx + 0.035, alu, at=(-0.37, z + 0.15), ch=0.006))
    out.append(C.finalize(lathe_x("AltThrough", [(0.0, 0.205, 0), (0.016, 0.205, 0), (0.016, 0.58, 0), (0.0, 0.58, 0)],
                                  [steel], at=(-0.37, z + 0.15), steps=24), angle=40))
    out.append(hex_at("AltBoltHead", 0.025, 0.55, 0.575, steel, Matrix.Translation((0, -0.37, z + 0.15)) @ RY))
    return out


def belt(rubber):
    pts = []
    for (y, z, r) in PUL.values():
        pts += circle_pts(y, z, r + 0.008, 96)
    path = resample(hull2d(pts), 320)
    n = len(path)
    bm = bmesh.new()
    rings = []
    hw, ht = (BELT_X[1] - BELT_X[0]) / 2, 0.009
    xc = (BELT_X[0] + BELT_X[1]) / 2
    sec = [(-hw, -ht), (hw, -ht), (hw, ht), (-hw, ht)]
    for i in range(n):
        a, b = path[i - 1], path[(i + 1) % n]
        T = Vector((0, b[0] - a[0], b[1] - a[1])).normalized()
        U = Vector((1, 0, 0))
        V = T.cross(U).normalized()
        P = Vector((xc, path[i][0], path[i][1]))
        rings.append([bm.verts.new(P + u * U + v * V) for (u, v) in sec])
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    C.fix_normals(bm)
    ob = C.mesh_obj("Belt", bm, [rubber])
    C.add_bevel(ob, 0.003, segments=2, angle=40)
    return C.finalize(ob, angle=40)


def exhaust(iron, shield_m, steel):
    out = []
    out.append(boxes("ExFlange", [(0.84, 0.03, 0.13, (0.0, -0.262, 0.665))], iron, bevel=0.01))
    for x in CYL_X:
        for dz in (-0.045, 0.045):
            out.append(hex_at("ExNut", 0.017, 0.0, 0.022, steel, Matrix.Translation((x + 0.07, -0.277, 0.665 + dz)) @ Matrix.Rotation(math.pi / 2, 4, "X")))
    for x in CYL_X:
        pts = [Vector((x, -0.27, 0.665)), Vector((x * 0.95, -0.33, 0.64)), Vector((x * 0.5 + 0.03, -0.375, 0.55)),
               Vector((x * 0.18 + 0.03, -0.39, 0.47)), Vector((x * 0.06 + 0.03, -0.40, 0.40))]
        out.append(tube("Runner", pts, 0.042, iron))
    out.append(lathe_at("Collector", [(0.0, 0.28, 0), (0.085, 0.28, 0), (0.095, 0.32, 0), (0.10, 0.39, 0), (0.085, 0.43, 0), (0.0, 0.44, 0)],
                        iron, Matrix.Translation((0.03, -0.40, 0)), steps=64))
    # downpipe flange (3-stud) and studs
    pts = circle_pts(0, 0, 0.09, 48)
    for t in (0.0, math.pi):
        pts += circle_pts(0.115 * math.cos(t), 0.115 * math.sin(t), 0.03, 24)
    sec = resample(hull2d(pts), 96)
    fl = loft("DPFlange", [(Vector((0.03, -0.40, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (0.255, 0.285)], iron)
    C.add_bevel(fl, 0.008, segments=2, angle=30)
    out.append(C.finalize(fl, angle=30))
    for t in (0.0, math.pi):
        M = Matrix.Translation((0.03 + 0.115 * math.cos(t), -0.40 + 0.115 * math.sin(t), 0))
        out.append(lathe_at("Stud", [(0.0, 0.215, 0), (0.011, 0.215, 0), (0.011, 0.29, 0), (0.0, 0.29, 0)], steel, M, steps=16))
        out.append(hex_at("DPNut", 0.02, 0.23, 0.255, steel, M))
    # lambda sensor
    M = Matrix.Translation((0.10, -0.46, 0.37)) @ Matrix.Rotation(math.radians(-60), 4, "X") @ Matrix.Rotation(math.radians(30), 4, "Y")
    out.append(hex_at("LambdaHex", 0.026, 0.0, 0.03, steel, M))
    out.append(lathe_at("Lambda", [(0.0, 0.03, 0), (0.02, 0.03, 0), (0.02, 0.10, 0), (0.012, 0.11, 0), (0.0, 0.11, 0)], steel, M, steps=24))
    # heat shield: curved embossed sheet over the runners
    prof = []
    for k in range(13):
        a = math.radians(-8 + 100 * k / 12)
        prof.append((-0.265 - 0.18 * math.sin(a), 0.66 + 0.18 * math.cos(a)))
    prof += [(-0.452, 0.54), (-0.448, 0.48), (-0.435, 0.44)]
    NX = 40
    x0, x1 = -0.43, 0.33
    bm = bmesh.new()
    grid = []
    for i in range(NX + 1):
        u = i / NX
        x = x0 + (x1 - x0) * u
        e = min(u, 1 - u)
        pull = (1 - C.smoothstep(0.0, 0.07, e))       # ends fold toward the head
        row = []
        for (yy, zz) in prof:
            yy2 = yy + (-0.265 - yy) * 0.55 * pull
            row.append(bm.verts.new((x, yy2, zz)))
        grid.append(row)
    for i in range(NX):
        for j in range(len(prof) - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    sh = C.mesh_obj("HeatShield", bm, [shield_m])
    so = sh.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = 0.008
    so.offset = 1
    sub = sh.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    out.append(C.finalize(sh, angle=50))
    for x in (-0.36, -0.03, 0.27):
        out.append(hex_at("ShieldBolt", 0.02, 0.0, 0.02, steel, Matrix.Translation((x, -0.30, 0.83)) @ Matrix.Rotation(math.radians(-30), 4, "X")))
    return out


def intake(plastic, alu, black, steel):
    out = []
    out.append(boxes("InFlange", [(0.86, 0.03, 0.13, (0.0, 0.262, 0.665))], plastic, bevel=0.01))
    for x in CYL_X:
        pts = [Vector((x, 0.26, 0.665)), Vector((x, 0.35, 0.69)), Vector((x, 0.44, 0.76)), Vector((x, 0.49, 0.84))]
        out.append(tube("InRunner", pts, 0.05, plastic, res=4))
    fr = []
    for (x, k) in ((-0.47, 0.80), (-0.45, 0.94), (-0.42, 1.0), (0.38, 1.0), (0.41, 0.94), (0.43, 0.80)):
        fr.append((Vector((x, 0.50, 0.90)), Vector((0, 1, 0)), Vector((0, 0, 1)), rrect(0.26 * k, 0.20 * k, 0.07 * k)))
    pl = loft("Plenum", fr, plastic)
    C.add_bevel(pl, 0.01, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    out.append(boxes("PlenumRibs", [(0.016, 0.27, 0.21, (x, 0.50, 0.90)) for x in (-0.30, -0.10, 0.10, 0.30)], plastic, bevel=0.006))
    specs = [(0.02, 0.03, 0.24, (x, 0.50, 0.93), Matrix.Translation((0, 0, 0))) for x in (-0.35, -0.15, 0.05, 0.25)]
    specs = [(0.018, 0.27, 0.27, (x, 0.50, 0.93)) for x in (-0.35, -0.15, 0.05, 0.25)]
    # throttle body on the +X end of the plenum
    out.append(ring_x("TBNeck", 0.0, 0.09, 0.40, 0.46, plastic, at=(0.50, 0.90)))
    out.append(ring_x("TBFlange", 0.0, 0.11, 0.46, 0.48, alu, at=(0.50, 0.90), ch=0.006))
    out.append(C.finalize(lathe_x("ThrottleBody", [(0.06, 0.48, 0), (0.085, 0.48, 0), (0.085, 0.58, 0), (0.095, 0.585, 0),
                                                   (0.095, 0.60, 0), (0.06, 0.60, 0)], [alu], at=(0.50, 0.90), steps=96), angle=40))
    out.append(ring_x("TBBore", 0.0, 0.061, 0.50, 0.505, black, at=(0.50, 0.90)))
    out.append(boxes("TBMotor", [(0.10, 0.08, 0.14, (0.535, 0.40, 0.89))], black, bevel=0.015))
    # PCV hose from the cover to the plenum
    out.append(tube("PCV", [Vector((-0.40, 0.13, 0.94)), Vector((-0.40, 0.25, 1.03)), Vector((-0.40, 0.38, 1.02))], 0.018, black))
    return out


def oil_filter(paint, alu, steel):
    out = []
    d = Vector((0, -0.8, -0.6)).normalized()
    M = Matrix.Translation((-0.30, -0.27, 0.15)) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    out.append(lathe_at("FilterBoss", [(0.0, -0.03, 0), (0.075, -0.03, 0), (0.075, 0.035, 0), (0.0, 0.035, 0)], alu, M, steps=64))

    def grip(r, z, t):
        if 0.205 < z < 0.24 and r > 0.08:
            return r + (0.004 if math.cos(28 * t) > 0 else 0)
        return r
    P = [(0.0, 0.035, 0), (0.078, 0.035, 0), (0.088, 0.045, 0), (0.09, 0.06, 0), (0.09, 0.20, 0), (0.09, 0.21, 0), (0.09, 0.232, 0), (0.09, 0.237, 0),
         (0.08, 0.25, 0), (0.035, 0.255, 0), (0.0, 0.255, 0)]
    out.append(lathe_at("OilFilter", P, paint, M, steps=168, mod=grip, angle=35))
    return out


def dipstick(steel, yellow):
    out = []
    pts = [Vector((-0.44, -0.30, 0.18)), Vector((-0.45, -0.33, 0.40)), Vector((-0.46, -0.33, 0.70)), Vector((-0.46, -0.30, 0.90))]
    out.append(tube("DipTube", pts, 0.012, steel))
    out.append(lathe_at("DipCap", [(0.0, 0.0, 0), (0.02, 0.0, 0), (0.02, 0.03, 0), (0.0, 0.03, 0)], yellow,
                        Matrix.Translation((-0.46, -0.30, 0.90)), steps=24))
    # loop handle
    bm = bmesh.new()
    seg, R, r = 40, 0.04, 0.009
    rings = []
    for i in range(seg):
        a = math.tau * i / seg
        c = Vector((-0.46 + R * math.cos(a), -0.30, 0.97 + R * math.sin(a)))
        n = Vector((math.cos(a), 0, math.sin(a)))
        rings.append([bm.verts.new(c + r * (math.cos(b) * n + math.sin(b) * Vector((0, 1, 0)))) for b in
                      [math.tau * k / 12 for k in range(12)]])
    for i in range(seg):
        a0, a1 = rings[i], rings[(i + 1) % seg]
        for k in range(12):
            bm.faces.new((a0[k], a0[(k + 1) % 12], a1[(k + 1) % 12], a1[k]))
    C.fix_normals(bm)
    h = C.mesh_obj("DipHandle", bm, [yellow])
    for f in h.data.polygons:
        f.use_smooth = True
    out.append(h)
    return out


def rear(alu, steel, gear_m):
    out = []
    pts = [(-0.31, -0.04), (0.31, -0.04), (0.31, 0.17), (0.27, 0.31), (0.27, 0.53), (-0.27, 0.53), (-0.27, 0.31), (-0.31, 0.17)]
    pts = circle_pts(0, 0, 0.27, 48) + pts
    sec = resample(hull2d(pts), 128)
    rp = prism_x("RearFace", sec, -0.53, -0.50, alu)
    C.add_bevel(rp, 0.008, segments=2, angle=30)
    out.append(C.finalize(rp, angle=30))
    # flywheel with ring gear
    NT = 110

    def teeth(r, z, t):
        if r < 0.315:
            return r
        return r - 0.012 * (1 if math.cos(NT * t) < 0 else 0)
    P = [(0.05, -0.53, 0), (0.30, -0.53, 0), (0.30, -0.535, 0), (0.325, -0.535, 0), (0.325, -0.565, 0), (0.30, -0.565, 0),
         (0.28, -0.575, 0), (0.05, -0.575, 0)]
    out.append(C.finalize(lathe_x("Flywheel", P, [gear_m], steps=NT * 4, mod=teeth), angle=30))
    out.append(ring_x("FlyFace", 0.10, 0.27, -0.578, -0.575, steel, steps=128))
    for k in range(6):
        t = math.tau * k / 6
        out.append(hex_at("FlyBolt", 0.02, -0.598, -0.578, steel,
                          Matrix.Translation((0, 0.07 * math.cos(t), 0.07 * math.sin(t))) @ RY))
    return out


def coolant(alu, rubber, steel):
    out = []
    # thermostat housing on the intake side, front end of the head
    out.append(boxes("ThermoHousing", [(0.12, 0.08, 0.10, (0.42, 0.285, 0.72))], alu, bevel=0.015))
    out.append(ring_x("ThermoOutlet", 0.0, 0.034, 0.47, 0.56, alu, at=(0.30, 0.74)))
    out.append(tube("UpperHose", [Vector((0.53, 0.30, 0.74)), Vector((0.59, 0.31, 0.73)), Vector((0.625, 0.32, 0.67)),
                                  Vector((0.63, 0.33, 0.60))], 0.042, rubber, res=4))
    out.append(ring_x("Clamp", 0.0, 0.046, 0.53, 0.55, steel, at=(0.30, 0.74), steps=48))
    # heater hose off the rear of the head
    out.append(tube("HeaterHose", [Vector((-0.50, -0.12, 0.72)), Vector((-0.57, -0.13, 0.71)), Vector((-0.61, -0.16, 0.64)),
                                   Vector((-0.62, -0.18, 0.56))], 0.026, rubber, res=4))
    out.append(ring_x("HoseStub", 0.0, 0.03, -0.53, -0.495, alu, at=(-0.12, 0.72)))
    return out


def build():
    alu = cast_alu("CastAlu", base=0.42, rough=0.50)
    alu2 = cast_alu("HeadAlu", base=0.47, rough=0.44)
    steel = C.principled("ZincSteel", (0.58, 0.59, 0.61), metallic=1.0, rough=0.28)
    C.add_noise_bump(steel, scale=800, strength=0.03, distance=0.0005)
    dark = C.principled("DarkSteel", (0.07, 0.07, 0.075), metallic=0.9, rough=0.38)
    C.add_noise_bump(dark, scale=500, strength=0.05, distance=0.0006, rough_var=0.06)
    black = C.mat_black_plastic("CoverPA", rough=0.50, color=0.024)
    plastic = C.mat_black_plastic("IntakePA", rough=0.40, color=0.03)
    coil_m = C.mat_black_plastic("CoilPBT", rough=0.28, color=0.018)
    conn_m = C.mat_black_plastic("ConnGrey", rough=0.45, color=0.09)
    rubber = C.mat_rubber("Rubber")
    iron = C.mat_cast_iron("ExIron", rust=0.9, base=0.14)
    shield = heat_shield_mat()
    filt = worn_paint("FilterBlue", C.srgb("#1E3F8F"), rough=0.28, coat=0.5)
    yellow = C.mat_paint("Yellow", C.srgb("#F2B705"), rough=0.35, coat=0.2)
    copper = C.principled("Copper", (0.8, 0.45, 0.28), metallic=1.0, rough=0.32)
    fly = C.mat_machined("Flywheel", color=0.50, rough=0.24, rings=300.0)

    objs = []
    objs += block(alu)
    objs += sump(alu, steel)
    objs += head(alu2, steel)
    objs += valve_cover(black, coil_m, conn_m, steel)
    objs += timing_cover(black)
    objs += crank_pulley(dark, rubber, steel)
    objs += accessory_pulleys(steel, dark, alu)
    objs += alternator(alu2, steel, black, copper)
    objs.append(belt(rubber))
    objs += exhaust(iron, shield, steel)
    objs += intake(plastic, alu2, black, steel)
    objs += oil_filter(filt, alu, steel)
    objs += dipstick(steel, yellow)
    objs += rear(alu, steel, fly)
    objs += coolant(alu2, rubber, steel)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("motore", objs, "motore.py",
            "small inline-4 petrol engine: aluminium block and head, black valve cover with coil packs, plastic intake "
            "manifold, exhaust manifold with embossed heat shield, timing cover, crank pulley and accessory belt, "
            "alternator, blue oil filter, sump, flywheel",
            az=30, el=24, lens=70, fill=0.86)
