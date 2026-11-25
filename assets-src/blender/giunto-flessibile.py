"""Exhaust flex joint: stainless wire-braid sleeve over an interlock liner, crimped
stainless end collars with rolled crimp grooves, and short plain pipe stubs at both
ends (open, showing the wall), slight heat tint on the pipe ends.

Built along local Z, then laid on the ground diagonally. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
T = Matrix.Translation
I4 = Matrix.Identity(4)
RB = 0.33          # braid outer radius
LB = 1.05          # braid half length
RP = 0.252         # pipe outer radius (50 mm pipe)
LC = 0.26          # collar length
LP = 0.62          # pipe stub length beyond the collar


# ----------------------------------------------------------------- helpers
def lathe_uv(name, prof, mat, steps=128, M=I4):
    """Revolve [(r, z)] around Z with UVs: u around (0..1), v = z (object units)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for (r, z) in prof:
        rings.append([bm.verts.new((r * math.cos(TAU * k / steps), r * math.sin(TAU * k / steps), z)) for k in range(steps)])
    for i in range(len(prof) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(steps):
            k2 = (k + 1) % steps
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            for l, (uu, vv) in zip(f.loops, ((k / steps, prof[i][1]), ((k + 1) / steps, prof[i][1]),
                                             ((k + 1) / steps, prof[i + 1][1]), (k / steps, prof[i + 1][1]))):
                l[uvl].uv = (uu, vv)
    ob = C.mesh_obj(name, bm, [mat])
    ob.matrix_world = M
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def lathe_at(name, prof, mats, M=I4, steps=96, angle=40, bevel=None):
    ob = C.lathe(name, prof, mats, steps=steps)
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=angle)


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k == "op":
            n.operation = v
        elif k == "clamp":
            n.use_clamp = v
        else:
            n.inputs[k].default_value = v
    return n


def math_node(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


# ----------------------------------------------------------------- materials
def mat_braid(name="Braid", nc=18, wires=6):
    """Stainless wire braid: two helical sets of flat wire bundles at ~45 deg, alternating
    over/under (basket cells), individual wires within each bundle, dark gaps."""
    m = C.principled(name, (0.62, 0.62, 0.63), metallic=1.0, rough=0.26)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    u, v = sep.outputs["X"], sep.outputs["Y"]
    nl = nc / (TAU * RB)
    uc = math_node(nt, "MULTIPLY", u, float(nc))
    vl = math_node(nt, "MULTIPLY", v, nl)
    A = math_node(nt, "ADD", uc, vl)
    B = math_node(nt, "SUBTRACT", uc, vl)
    fa = math_node(nt, "FRACT", A)
    fb = math_node(nt, "FRACT", B)
    pa = math_node(nt, "FLOOR", A)
    pb = math_node(nt, "FLOOR", B)
    par = math_node(nt, "MODULO", math_node(nt, "ABSOLUTE", math_node(nt, "ADD", pa, pb)), 2.0)   # 0 / 1

    def hump(f):
        return math_node(nt, "SINE", math_node(nt, "MULTIPLY", f, math.pi))

    def wires_of(f):
        w = math_node(nt, "COSINE", math_node(nt, "MULTIPLY", f, TAU * wires))
        return math_node(nt, "ADD", math_node(nt, "MULTIPLY", w, 0.12), 0.88)

    ha, hb = hump(fa), hump(fb)
    # bundle A on top: profile across A, dipping at its ends (across B)
    topA = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", math_node(nt, "POWER", ha, 0.5), wires_of(fa)),
                     math_node(nt, "ADD", math_node(nt, "MULTIPLY", hb, 0.45), 0.55))
    topB = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", math_node(nt, "POWER", hb, 0.5), wires_of(fb)),
                     math_node(nt, "ADD", math_node(nt, "MULTIPLY", ha, 0.45), 0.55))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    nt.links.new(par, mix.inputs["Factor"])
    nt.links.new(topB, mix.inputs["A"])
    nt.links.new(topA, mix.inputs["B"])
    h = mix.outputs["Result"]
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = 0.018
    nt.links.new(h, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    # cavity darkening + slight grime / heat tint mottling
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.08
    cr.elements[0].color = (0.05, 0.05, 0.05, 1)
    cr.elements[1].position = 0.55
    cr.elements[1].color = (0.64, 0.64, 0.65, 1)
    nt.links.new(h, ramp.inputs["Fac"])
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Max"].default_value = 0.55
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], tint.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], tint.inputs["A"])
    tint.inputs["B"].default_value = (0.40, 0.33, 0.25, 1)
    tint.blend_type = "MULTIPLY"
    nt.links.new(tint.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.6
    rr.inputs["To Max"].default_value = 0.24
    nt.links.new(h, rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_steel(name, color=0.55, rough=0.28, heat=0.0):
    m = C.principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.5
    nz.inputs["Detail"].default_value = 7.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.45
    cr.elements[0].color = (color, color, color * 1.01, 1)
    cr.elements[1].position = 0.85
    cr.elements[1].color = (color * (1 - 0.5 * heat) + 0.30 * heat, color * (1 - 0.55 * heat) + 0.20 * heat,
                            color * (1 - 0.6 * heat) + 0.14 * heat, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.06
    mr.inputs["To Max"].default_value = rough + 0.16
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    gr = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), gr.inputs["Vector"])
    gr.inputs["Scale"].default_value = 320.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.06
    bp.inputs["Distance"].default_value = 0.002
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ----------------------------------------------------------------- parts
def build():
    braid = mat_braid()
    collar_m = mat_steel("CollarSteel", 0.60, 0.24, heat=0.2)
    C.add_radial_aniso(collar_m, 0.5, "Z")
    pipe_m = mat_steel("PipeSteel", 0.50, 0.34, heat=0.8)
    inner = C.principled("Liner", (0.10, 0.095, 0.09), metallic=0.8, rough=0.55)
    objs = []
    # braid sleeve
    prof = [(RB - 0.012, -LB - 0.02)] + [(RB, -LB + 2 * LB * i / 60) for i in range(61)] + [(RB - 0.012, LB + 0.02)]
    objs.append(lathe_uv("Braid", prof, braid, steps=192))
    # crimped end collars (built for +Z, mirrored for -Z)
    def mirror(P):
        return [(r, -z, i) for (r, z, i) in reversed(P)]
    za = LB - 0.06
    zb = za + LC
    R = RB + 0.035
    P = [(RP - 0.004, za, 0), (R - 0.01, za, 0), (R, za + 0.01, 0)]
    for g in (0.33, 0.70):
        zg = za + LC * g
        P += [(R, zg - 0.035, 0), (R - 0.022, zg - 0.012, 0), (R - 0.022, zg + 0.012, 0), (R, zg + 0.035, 0)]
    P += [(R, zb - 0.01, 0), (R - 0.01, zb, 0), (RP - 0.004, zb, 0)]
    objs.append(lathe_at("CollarA", P, [collar_m], steps=128, bevel=0.004))
    objs.append(lathe_at("CollarB", mirror(P), [collar_m], steps=128, bevel=0.004))
    # pipe stubs, hollow, chamfered open ends
    z0, z1 = zb - 0.05, zb + LP
    w = 0.016
    P = [(RP, z0, 0), (RP, z1 - 0.008, 0), (RP - 0.006, z1, 0), (RP - w, z1, 0), (RP - w, z0, 0)]
    objs.append(lathe_at("PipeA", P, [pipe_m], steps=96, angle=50))
    objs.append(lathe_at("PipeB", mirror(P), [pipe_m], steps=96, angle=50))
    # dark interlock liner inside (seen through the open ends)
    objs.append(lathe_at("Liner", [(RP - 0.03, -LB, 0), (RP - 0.016, -LB, 0), (RP - 0.016, LB, 0), (RP - 0.03, LB, 0)], [inner], steps=64))
    # lay down diagonally: axis horizontal, resting on the collars
    w = Vector((-0.80, -0.60, 0.0)).normalized()
    up = Vector((0, 0, 1))
    xa = up.cross(w)
    R = Matrix(((xa.x, up.x, w.x, 0), (xa.y, up.y, w.y, 0), (xa.z, up.z, w.z, 0), (0, 0, 0, 1)))
    C.transform_all(objs, T((0, 0, RB + 0.035)) @ R)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    prev = os.environ.get("PREV")
    C.shoot("giunto-flessibile", objs, "giunto-flessibile.py",
            "exhaust flex joint: stainless steel wire-braid sleeve with crimped end collars and short plain pipe ends",
            az=-8, el=26, lens=70, fill=0.88,
            res=(512, 512) if prev else (1024, 1024), samples=32 if prev else 128)
