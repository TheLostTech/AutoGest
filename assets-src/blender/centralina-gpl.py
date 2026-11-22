"""LPG injection ECU: small extruded aluminium box with ribbed top, side mounting flanges
with slotted holes, black plastic end caps held by screws, blank label, and its
wiring-loom tail: rubber grommet, corrugated loom sleeve curving across the floor and
splitting at a taped junction into thinner branches that end in assorted black/grey
connectors (2-pin injector plugs, a multi-pin plug) and a blade fuse holder.

1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
from mathutils.geometry import interpolate_bezier
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
LB, WB, HB = 1.30, 0.86, 0.30      # box length (X), width (Y), height (Z)


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


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), M=I4):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    ob.matrix_world = M
    for c in cutters:
        c.matrix_world = M
        m = C.add_boolean(ob, c)
        m.use_self = True
        m.use_hole_tolerant = True
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
        C.add_bevel(ob, bevel, segments=2, angle=35)
    return C.finalize(ob, angle=angle)


def axis_frame(P, d):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    x = up.cross(d).normalized()
    y = d.cross(x)
    return Matrix(((x.x, y.x, d.x, P[0]), (x.y, y.y, d.y, P[1]), (x.z, y.z, d.z, P[2]), (0, 0, 0, 1)))


def smooth_path(ctrl, res=24):
    """Catmull-Rom-like smooth polyline through ctrl using auto bezier handles."""
    P = [Vector(c) for c in ctrl]
    out = []
    for i in range(len(P) - 1):
        p0, p1 = P[i], P[i + 1]
        tin = (P[i + 1] - P[i - 1]) if i > 0 else (P[1] - P[0])
        tout = (P[i + 2] - P[i]) if i + 2 < len(P) else (P[-1] - P[-2])
        h1 = p0 + tin * (1 / 6.0) * (1.0 if i > 0 else 2.0)
        h2 = p1 - tout * (1 / 6.0) * (1.0 if i + 2 < len(P) else 2.0)
        seg = interpolate_bezier(p0, h1, h2, p1, res)
        out += seg[:-1] if i < len(P) - 2 else seg
    return out


def sweep_uv(name, ctrl, r, mat, seg=24, res=24, cap=True):
    """Tube along a smooth path with UVs (u around, v = arc length) and parallel-transport frames."""
    pts = smooth_path(ctrl, res)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    tans = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tans.append((b - a).normalized())
    n = tans[0].orthogonal().normalized()
    rings, vs = [], []
    s = 0.0
    for i, (p, t) in enumerate(zip(pts, tans)):
        if i:
            s += (p - pts[i - 1]).length
            n = (n - t * n.dot(t)).normalized()
        bvec = t.cross(n)
        rings.append([bm.verts.new(p + r * (math.cos(TAU * k / seg) * n + math.sin(TAU * k / seg) * bvec)) for k in range(seg)])
        vs.append(s)
    for i in range(len(rings) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for l, uv in zip(f.loops, ((k / seg, vs[i]), ((k + 1) / seg, vs[i]), ((k + 1) / seg, vs[i + 1]), (k / seg, vs[i + 1]))):
                l[uvl].uv = uv
            f.smooth = True
    if cap:
        f = bm.faces.new(rings[0][::-1])
        f.smooth = True
        f = bm.faces.new(rings[-1])
        f.smooth = True
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    return ob, pts


# ----------------------------------------------------------------- materials
def mat_extruded(name="EcuAlu", base=0.56, rough=0.30):
    m = C.principled(name, (base, base, base * 1.01), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.02, 1.0, 1.0)     # die lines along X
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 300.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mo = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(tc.outputs["Object"], mo.inputs["Vector"])
    mo.inputs["Scale"].default_value = 4.0
    mo.inputs["Detail"].default_value = 6.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.05
    mr.inputs["To Max"].default_value = rough + 0.15
    nt.links.new(mo.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    em = C.edge_mask(nt, 0.01, 4.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MULTIPLY"
    mx.inputs[1].default_value = 0.4
    nt.links.new(em, mx.inputs[0])
    nt.links.new(mx.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (base, base, base * 1.01, 1)
    mix.inputs["B"].default_value = (0.80, 0.80, 0.80, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_corrugated(name="Loom", pitch=0.045, color=0.03):
    """Corrugated loom sleeve: ridges around the tube (UV v = arc length)."""
    m = C.principled(name, (color, color, color * 1.06), rough=0.42)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = TAU / pitch
    nt.links.new(sep.outputs["Y"], mul.inputs[0])
    sn = nt.nodes.new("ShaderNodeMath")
    sn.operation = "SINE"
    nt.links.new(mul.outputs[0], sn.inputs[0])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.012
    nt.links.new(sn.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_tape(name="Tape", color=0.02):
    """PVC loom tape: spiral overlapping wraps (UV based), slightly glossy."""
    m = C.principled(name, (color, color, color * 1.05), rough=0.30)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "MULTIPLY_ADD"
    a.inputs[1].default_value = 1.0 / 0.06
    nt.links.new(sep.outputs["Y"], a.inputs[0])
    nt.links.new(sep.outputs["X"], a.inputs[2])
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    nt.links.new(a.outputs[0], fr.inputs[0])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.004
    nt.links.new(fr.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def box(alu, black, steel, dark):
    out = []
    # extrusion profile in YZ: body with two side flanges, top ribs
    def prof(bm):
        sec = rrect(WB, HB, 0.05)
        prism_bm(bm, sec, -LB / 2, LB / 2, M=T((0, 0, HB / 2)) @ Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        for s in (-1, 1):
            C.box_bm(bm, LB, 0.20, 0.035, center=(0, s * (WB / 2 + 0.08), 0.0175))
        for k in range(7):
            y = -0.30 + 0.10 * k
            C.box_bm(bm, LB, 0.035, 0.035, center=(0, y, HB + 0.012))

    def holes(bm):
        for s in (-1, 1):
            for x in (-0.40, 0.40):
                prism_bm(bm, rrect(0.16, 0.07, 0.034), -0.2, 0.2, M=T((x, s * (WB / 2 + 0.10), 0)))
    out.append(solid("Housing", prof, [alu], bevel=0.008, cutters=[cutter("FlangeSlots", holes, dark)]))
    # end caps
    for s in (-1, 1):
        def cap(bm, s=s):
            prism_bm(bm, rrect(WB + 0.02, HB + 0.02, 0.06), 0.0, 0.08,
                     M=T((s * LB / 2, 0, HB / 2)) @ Matrix.Rotation(s * math.pi / 2, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        out.append(solid("EndCap", cap, [black], bevel=0.02))
        for y in (-0.30, 0.30):
            for z in (0.07, HB - 0.07):
                M = T((s * (LB / 2 + 0.08), y, z)) @ Matrix.Rotation(s * math.pi / 2, 4, "Y")
                out.append(lathe_at("CapScrew", [(0.0, 0.0, 0), (0.035, 0.0, 0), (0.035, 0.02, 0), (0.028, 0.03, 0), (0.0, 0.03, 0)],
                                    steel, M, steps=24))
    # label on top between ribs? -> on the flat end of top (no ribs at x>0.2): use a raised plate instead
    im = C.label_image("GasEcuLabel", 1024, 600, seed=17, lines=5)
    M = T((-0.05, 0.0, HB + 0.031)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    out.append(C.label_plane("Label", C.mat_label(im), 0.78, 0.50, M))
    return out


def loom(rubber, corr, tape, wire_m, black, grey, red, tin, dark):
    out = []
    x0 = LB / 2 + 0.08
    # grommet on the +X end cap
    M = axis_frame((x0, 0.15, HB / 2), (1, 0, 0))
    out.append(lathe_at("Grommet", [(0.0, 0.0, 0), (0.13, 0.0, 0), (0.13, 0.05, 0), (0.10, 0.08, 0), (0.09, 0.20, 0), (0.07, 0.24, 0),
                                    (0.0, 0.24, 0)], rubber, M, steps=48, bevel=0.006))
    # corrugated trunk curving toward the camera and to the left across the floor
    ctrl = [(x0 + 0.18, 0.15, HB / 2), (x0 + 0.45, 0.10, 0.12), (x0 + 0.70, -0.25, 0.075), (x0 + 0.55, -0.75, 0.075),
            (x0 + 0.10, -1.00, 0.075), (x0 - 0.45, -1.05, 0.075)]
    ob, pts = sweep_uv("Trunk", ctrl, 0.075, corr, seg=28, res=20)
    out.append(C.finalize(ob, angle=60))
    j = pts[-1]
    tdir = (pts[-1] - pts[-3]).normalized()
    # taped junction
    ob, _ = sweep_uv("Junction", [tuple(j - tdir * 0.04), tuple(j + tdir * 0.14)], 0.085, tape, seg=28, res=8)
    out.append(C.finalize(ob, angle=60))
    jp = j + tdir * 0.12
    # branches: (end point, connector kind)
    br = [((x0 - 1.30, -0.62, 0.035), "multi"), ((x0 - 1.45, -1.05, 0.03), "two"), ((x0 - 1.30, -1.45, 0.03), "two"),
          ((x0 - 0.85, -1.62, 0.03), "fuse")]
    for i, (e, kind) in enumerate(br):
        e = Vector(e)
        mid = jp + tdir * 0.20 + (e - jp) * 0.45
        mid.z = 0.035
        r = 0.035 if kind != "multi" else 0.05
        ob, bp = sweep_uv("Branch%d" % i, [tuple(jp - tdir * 0.05), tuple(jp + tdir * 0.12), tuple(mid), tuple(e)], r, tape, seg=16, res=16)
        out.append(C.finalize(ob, angle=60))
        d = (bp[-1] - bp[-4]).normalized()
        d.z = 0
        d.normalize()
        out += connector(kind, e, d, black, grey, red, tin, dark, rubber)
    return out


def connector(kind, P, d, black, grey, red, tin, dark, rubber):
    out = []
    M = axis_frame(P, d)
    if kind == "two":
        def bd(bm):
            prism_bm(bm, rrect(0.18, 0.13, 0.025), 0.02, 0.26)
            C.box_bm(bm, 0.06, 0.03, 0.12, center=(0.0, 0.075, 0.18))
            C.cyl_bm(bm, 0.045, -0.04, 0.04, seg=24)
        def cv(bm):
            prism_bm(bm, rrect(0.13, 0.08, 0.02), 0.14, 0.30)
        out.append(solid("Plug2", bd, [grey], bevel=0.008, cutters=[cutter("Plug2Cav", cv, dark)], M=M))
        def pins(bm):
            for dx in (-0.03, 0.03):
                C.box_bm(bm, 0.02, 0.02, 0.06, center=(dx, 0.0, 0.17))
        out.append(solid("Pins", pins, [tin], M=M))
    elif kind == "multi":
        def bd(bm):
            prism_bm(bm, rrect(0.36, 0.17, 0.03), 0.02, 0.32)
            C.box_bm(bm, 0.10, 0.04, 0.16, center=(0.0, 0.10, 0.20))
            C.box_bm(bm, 0.16, 0.10, 0.08, center=(0.0, 0.0, -0.01))
        def cv(bm):
            prism_bm(bm, rrect(0.30, 0.11, 0.02), 0.18, 0.36)
        out.append(solid("PlugM", bd, [black], bevel=0.01, cutters=[cutter("PlugMCav", cv, dark)], M=M))
        def pins(bm):
            for r in (-0.025, 0.025):
                for k in range(6):
                    C.box_bm(bm, 0.016, 0.016, 0.06, center=(-0.105 + 0.042 * k, r, 0.20))
        out.append(solid("PinsM", pins, [tin], M=M))
    else:  # inline blade-fuse holder: body + hinged lid
        def bd(bm):
            prism_bm(bm, rrect(0.16, 0.12, 0.04), -0.02, 0.28)
        out.append(solid("FuseHolder", bd, [black], bevel=0.012, M=M))
        def lid(bm):
            prism_bm(bm, rrect(0.17, 0.13, 0.045), 0.28, 0.40)
            C.box_bm(bm, 0.05, 0.03, 0.08, center=(0.0, 0.075, 0.30))
        out.append(solid("FuseLid", lid, [black], bevel=0.012, M=M))
        # wire continues out the far side, short and cut
        e = M @ Vector((0, 0, 0.40))
        ob, _ = sweep_uv("FuseWire", [tuple(e), tuple(e + d * 0.18), tuple(e + d * 0.30 + Vector((0.05, -0.08, -0.015)))], 0.022,
                         red, seg=12, res=10)
        out.append(C.finalize(ob, angle=60))
    return out


def build():
    alu = mat_extruded()
    black = C.mat_black_plastic("CapPA", rough=0.45, color=0.022)
    grey = C.mat_black_plastic("PlugGrey", rough=0.50, color=0.10)
    steel = C.principled("ScrewSteel", (0.55, 0.55, 0.57), metallic=1.0, rough=0.3)
    dark = C.principled("Cavity", (0.01, 0.01, 0.01), rough=0.8)
    rubber = C.mat_rubber("Grommet")
    corr = mat_corrugated()
    tape = mat_tape()
    red = C.principled("RedWire", (0.42, 0.03, 0.03), rough=0.35)
    tin = C.principled("Tin", (0.78, 0.76, 0.70), metallic=1.0, rough=0.2)
    objs = box(alu, black, steel, dark)
    objs += loom(rubber, corr, tape, None, black, grey, red, tin, dark)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("centralina-gpl", objs, "centralina-gpl.py",
            "LPG injection ECU: small extruded aluminium box with mounting flanges and black end caps, wiring loom tail in "
            "corrugated sleeve splitting into branches with connectors and a fuse holder",
            az=24, el=40, lens=70, fill=0.86,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
