"""Turbocharger for a small diesel: snail-shaped cast-iron turbine housing with a
2-bolt inlet flange and a round 3-stud outlet flange, cast-aluminium compressor
housing (spiral volute, axial inlet with the compressor wheel visible inside,
tangential outlet), cast-iron centre bearing cartridge with oil feed line and oil
return flange/pipe, and a wastegate actuator canister on a bracket with its rod
running to the wastegate lever on the turbine side.

Shaft along X: compressor at +X, turbine at -X. 1 unit = 100 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

FAST = bool(os.environ.get("PK_FAST"))
I4 = Matrix.Identity(4)
RY = Matrix.Rotation(math.pi / 2, 4, "Y")        # local Z -> +X
RYm = Matrix.Rotation(-math.pi / 2, 4, "Y")      # local Z -> -X
XA = Vector((1, 0, 0))


# ----------------------------------------------------------------- helpers
def circ(r, n=40, ph=0.0):
    return [(r * math.cos(math.tau * k / n + ph), r * math.sin(math.tau * k / n + ph)) for k in range(n)]


def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def frame_to(P, Z):
    """Matrix placing local Z along direction Z at point P."""
    q = Vector(Z).normalized().to_track_quat("Z", "Y")
    return Matrix.Translation(P) @ q.to_matrix().to_4x4()


def prism_bm(bm, sec, z0, z1, M=I4, mat=0):
    fr = [(Vector((0, 0, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), sec) for z in (z0, z1)]
    faces = C.sweep(bm, fr, mat=mat)
    vs = list({v for f in faces for v in f.verts})
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    return faces


def solid(name, fill, mats, bevel=0.0, seg=2, angle=32, cutters=(), raw=False):
    bm = bmesh.new()
    fill(bm)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, mats)
    if raw:
        return ob
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


def tube(name, pts, r, mat, res=4, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    cu.resolution_u = 16
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts):
        p.co = c
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = C.link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return C.finalize(ob, angle=50)


def cast_alu(name, base=0.42, rough=0.48, grime=0.75, grain=140.0, wear=0.3):
    m = C.principled(name, (base, base, base * 0.985), metallic=1.0, rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 6.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.25
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
    em = C.edge_mask(nt, 0.015, 4.0)
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
    bp.inputs["Strength"].default_value = 0.18
    bp.inputs["Distance"].default_value = 0.003
    nt.links.new(gr.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def hot_iron(name="TurbineIron"):
    """Cast iron after heat cycles: dark grey-brown, rusty bloom, coarse sand-cast grain."""
    m = C.mat_cast_iron(name, rust=0.75, base=0.11)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # overall heat oxidation: patches of brown-red scale over the grey iron
    link = next(l for l in nt.links if l.to_node == b and l.to_socket.name == "Base Color")
    src = link.from_socket
    nt.links.remove(link)
    m2 = nt.nodes.new("ShaderNodeMapRange")
    m2.inputs["From Min"].default_value = 0.42
    m2.inputs["From Max"].default_value = 0.68
    m2.inputs["To Max"].default_value = 0.85
    nt.links.new(nz.outputs["Fac"], m2.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(m2.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(src, mix.inputs["A"])
    mix.inputs["B"].default_value = (0.16, 0.075, 0.04, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["To Min"].default_value = 0.8
    mm.inputs["To Max"].default_value = 0.3
    nt.links.new(m2.outputs["Result"], mm.inputs["Value"])
    for l in [l for l in nt.links if l.to_node == b and l.to_socket.name == "Metallic"]:
        nt.links.remove(l)
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    return m


# ----------------------------------------------------------------- volutes
def volute(name, xc, r_in, rho0, rho1, th_end, sign, out_len, mat, turns=0.88, n=96):
    """Spiral scroll around the X axis whose section grows from rho0 to rho1, ending
    in a straight tangential pipe. Returns (obj, end point, tangent, radial)."""
    frames = []
    for i in range(n + 1):
        t = i / n
        th = th_end - sign * turns * math.tau * (1 - t)
        rho = rho0 + (rho1 - rho0) * (t ** 0.9)
        R = r_in + rho * 0.92
        rad = Vector((0, math.cos(th), math.sin(th)))
        frames.append((Vector((xc, 0, 0)) + R * rad, rad, XA, circ(rho, 40)))
    th = th_end
    tang = sign * Vector((0, -math.sin(th), math.cos(th)))
    radv = Vector((0, math.cos(th), math.sin(th)))
    Pe = frames[-1][0]
    for s in (0.12, out_len * 0.6, out_len):
        frames.append((Pe + tang * s, radv, XA, circ(rho1, 40)))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    C.add_bevel(ob, 0.006, segments=1, angle=40)
    return C.finalize(ob, angle=50), Pe + tang * out_len, tang, radv


def compressor(alu, bore_m, wheel_m, dark):
    out = []
    xc = 0.66
    vol, Pe, tang, radv = volute("CompVolute", xc, 0.30, 0.05, 0.215, 0.0, 1, 0.42, alu)
    out.append(vol)
    # cover: inlet neck with hose bead, shroud, back plate
    P = [(0.235, 0.62, 1), (0.235, 1.12, 0), (0.26, 1.15, 0), (0.30, 1.15, 0), (0.32, 1.13, 0), (0.32, 1.07, 0),
         (0.30, 1.05, 0), (0.30, 0.98, 0), (0.33, 0.96, 0), (0.33, 0.92, 0), (0.30, 0.90, 0), (0.31, 0.84, 0),
         (0.40, 0.80, 0), (0.52, 0.78, 0), (0.56, 0.72, 0), (0.58, 0.56, 0), (0.62, 0.52, 0), (0.62, 0.44, 0),
         (0.40, 0.42, 0), (0.0, 0.42, 0), (0.0, 0.62, 0)]
    ob = C.lathe("CompCover", P, [alu, bore_m], steps=160)
    ob.matrix_world = RY
    C.add_bevel(ob, 0.006, segments=1, angle=35)
    out.append(C.finalize(ob, angle=40))
    # machined bore surface inside the inlet
    out.append(lathe_at("Bore", [(0.236, 0.64, 0), (0.236, 1.135, 0), (0.234, 1.135, 0), (0.234, 0.64, 0)], bore_m, RY, steps=96))
    # compressor wheel: hub + twisted blades + nose nut
    out.append(lathe_at("Hub", [(0.0, 0.62, 0), (0.21, 0.62, 0), (0.20, 0.66, 0), (0.12, 0.76, 0), (0.07, 0.90, 0),
                                (0.05, 1.04, 0), (0.0, 1.04, 0)], wheel_m, RY, steps=64))
    out.append(hex_at("NoseNut", 0.035, 1.04, 1.09, wheel_m, RY, bevel=0.004))
    def blades(bm):
        for k in range(12):
            full = k % 2 == 0
            x0, x1 = 0.65, (1.08 if full else 0.90)
            fr = []
            for j in range(9):
                x = x0 + (x1 - x0) * j / 8
                ph = math.tau * k / 12 + 0.95 * (1.08 - x) / 0.44
                U = Vector((0, math.cos(ph), math.sin(ph)))
                V = Vector((0, -math.sin(ph), math.cos(ph)))
                tip = 0.228 if x < 0.62 else 0.228 - 0.10 * (x - 0.62) / 0.35 * 0.0
                fr.append((Vector((x, 0, 0)), U, V, [(0.04, -0.007), (tip, -0.006), (tip, 0.006), (0.04, 0.007)]))
            C.sweep(bm, fr)
    out.append(solid("Blades", blades, [wheel_m], bevel=0.002, angle=50))
    # outlet lip with bead and dark throat
    Mo = frame_to(Pe, tang)
    out.append(lathe_at("OutLip", [(0.17, -0.02, 1), (0.215, -0.02, 0), (0.24, 0.02, 0), (0.24, 0.06, 0), (0.215, 0.08, 0),
                                   (0.215, 0.14, 0), (0.17, 0.14, 0)], alu, Mo, steps=64, mats=[alu, bore_m]))
    out.append(lathe_at("OutDark", [(0.0, 0.0, 0), (0.172, 0.0, 0), (0.172, 0.01, 0), (0.0, 0.01, 0)], dark, Mo, steps=48))
    return out


def turbine(iron, steel, soot):
    out = []
    xc = -0.66
    vol, Pe, tang, radv = volute("TurbVolute", xc, 0.25, 0.05, 0.235, math.pi, 1, 0.30, iron)
    out.append(vol)
    # centre body and axial outlet with round flange
    P = [(0.0, -0.40, 0), (0.50, -0.40, 0), (0.54, -0.46, 0), (0.54, -0.56, 0), (0.48, -0.70, 0), (0.34, -0.80, 0),
         (0.32, -0.90, 0), (0.46, -0.92, 0), (0.46, -1.02, 0), (0.24, -1.02, 1), (0.24, -0.70, 1), (0.0, -0.70, 0)]
    ob = C.lathe("TurbBody", P, [iron, soot], steps=160)
    ob.matrix_world = RY
    C.add_bevel(ob, 0.008, segments=1, angle=35)
    out.append(C.finalize(ob, angle=40))
    for k in range(3):
        th = math.tau * k / 3 + 0.5
        M = RYm @ Matrix.Translation((0.38 * math.cos(th), 0.38 * math.sin(th), 1.02))
        out.append(lathe_at("OStud", [(0.0, 0.0, 0), (0.032, 0.0, 0), (0.032, 0.18, 0), (0.024, 0.19, 0), (0.0, 0.19, 0)], steel, M, steps=20))
        out.append(hex_at("ONut", 0.05, 0.0, 0.07, steel, M))
    # inlet flange (2 bolts) at the end of the scroll pipe
    Mi = frame_to(Pe, tang)
    def fl(bm):
        sec = rrect(0.66, 0.40, 0.17)
        prism_bm(bm, sec, -0.08, 0.0, Mi @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    holes = bmesh.new()
    for s in (-1, 1):
        C.cyl_bm(holes, 0.048, -0.2, 0.1, seg=24, matrix=Mi @ Matrix.Translation((0, s * 0.24, 0)))
    C.cyl_bm(holes, 0.15, -0.03, 0.1, seg=40, matrix=Mi)
    hc = C.mesh_obj("FlHoles", holes, [soot])
    bm = bmesh.new(); fl(bm); C.fix_normals(bm)
    f = C.mesh_obj("InFlange", bm, [iron])
    C.add_boolean(f, hc).use_self = True
    C.add_bevel(f, 0.012, segments=2, angle=30)
    out.append(C.finalize(f, angle=35, remove=[hc]))
    # heat shield disc between turbine and cartridge
    out.append(lathe_at("Shield", [(0.12, -0.42, 0), (0.50, -0.42, 0), (0.52, -0.38, 0), (0.50, -0.37, 0), (0.12, -0.37, 0)],
                        steel, RY, steps=96))
    return out, Pe, tang


def cartridge(iron2, steel, alu):
    out = []
    P = [(0.0, -0.38, 0), (0.33, -0.38, 0), (0.34, -0.33, 0), (0.24, -0.29, 0), (0.22, -0.20, 0), (0.25, -0.12, 0),
         (0.25, 0.12, 0), (0.22, 0.20, 0), (0.24, 0.30, 0), (0.36, 0.33, 0), (0.37, 0.42, 0), (0.0, 0.42, 0)]
    out.append(lathe_at("Cartridge", P, iron2, RY, steps=96, bevel=0.006))
    # oil inlet boss (top) and return pad (bottom)
    def bosses(bm):
        C.box_bm(bm, 0.24, 0.24, 0.20, center=(0.02, 0, 0.24))
        C.box_bm(bm, 0.28, 0.30, 0.16, center=(0.0, 0, -0.24))
    out.append(solid("OilBosses", bosses, [iron2], bevel=0.03))
    # V-band style clamp ring on compressor side
    out.append(lathe_at("Clamp", [(0.56, 0.40, 0), (0.64, 0.40, 0), (0.66, 0.43, 0), (0.64, 0.47, 0), (0.56, 0.47, 0)],
                        steel, RY, steps=128))
    return out


def oil_lines(steel, zinc, rubber, iron2):
    out = []
    # feed: banjo fitting on top + pipe
    out.append(hex_at("FeedUnion", 0.07, 0.34, 0.42, zinc, Matrix.Translation((0.02, 0, 0))))
    pts = [(0.02, 0, 0.42), (0.02, 0.02, 0.62), (0.08, 0.20, 0.80), (0.20, 0.46, 0.86), (0.30, 0.78, 0.86)]
    out.append(tube("FeedPipe", pts, 0.032, steel))
    out.append(hex_at("FeedNut", 0.055, 0.0, 0.10, zinc, frame_to(Vector((0.30, 0.78, 0.86)), Vector((0.1, 1, 0)))))
    # return: flange + short pipe + hose stub
    def rf(bm):
        C.box_bm(bm, 0.30, 0.20, 0.05, center=(0.0, 0, -0.345))
    out.append(solid("RetFlange", rf, [zinc], bevel=0.012))
    for s in (-1, 1):
        out.append(hex_at("RetBolt", 0.04, -0.40, -0.37, zinc, Matrix.Translation((s * 0.11, 0, 0))))
    pts = [(0.0, 0, -0.37), (0.0, 0, -0.55), (0.06, 0.04, -0.72)]
    out.append(tube("RetPipe", pts, 0.06, steel))
    out.append(lathe_at("RetHose", [(0.0, -0.95, 0), (0.08, -0.95, 0), (0.08, -0.66, 0), (0.0, -0.66, 0)], rubber,
                        Matrix.Translation((0.03, 0.02, 0)), steps=40, bevel=0.01))
    return out


def actuator(paint, zinc, steel, rubber, iron):
    out = []
    y, z = -0.62, 0.92
    M = Matrix.Translation((0.90, y, z)) @ RYm            # canister axis along -X
    P = [(0.0, -0.02, 0), (0.22, -0.02, 0), (0.28, 0.02, 0), (0.30, 0.10, 0), (0.335, 0.12, 0), (0.335, 0.155, 0),
         (0.30, 0.17, 0), (0.29, 0.26, 0), (0.24, 0.31, 0), (0.10, 0.33, 0), (0.0, 0.33, 0)]
    out.append(lathe_at("Canister", P, paint, M, steps=96, bevel=0.004))
    # vacuum nipple on the back face (+X) and short hose
    out.append(lathe_at("Nipple", [(0.0, -0.02, 0), (0.035, -0.02, 0), (0.035, -0.12, 0), (0.045, -0.13, 0), (0.03, -0.16, 0), (0.0, -0.16, 0)],
                        zinc, M @ Matrix.Translation((0.12, 0.08, 0)), steps=24))
    # bracket from canister to compressor housing
    def br(bm):
        C.box_bm(bm, 0.05, 0.50, 0.62, center=(0.56, -0.50, 0.74))
        C.box_bm(bm, 0.22, 0.40, 0.05, center=(0.46, -0.40, 0.48))
    out.append(solid("Bracket", br, [zinc], bevel=0.01))
    for dz in (-0.14, 0.14):
        out.append(hex_at("BrNut", 0.045, 0.0, 0.05, zinc, Matrix.Translation((0.53, y, z + dz)) @ RYm))
    # rod with adjuster + lever on the turbine side
    x0, x1 = 0.55, -0.80
    out.append(lathe_at("Rod", [(0.0, 0.0, 0), (0.024, 0.0, 0), (0.024, x0 - x1, 0), (0.0, x0 - x1, 0)], steel,
                        Matrix.Translation((x0, y, z)) @ RYm, steps=24))
    out.append(hex_at("RodNut", 0.045, 0.0, 0.06, zinc, Matrix.Translation((-0.40, y, z)) @ RYm))
    out.append(lathe_at("RodEnd", [(0.0, 0.0, 0), (0.042, 0.0, 0), (0.042, 0.22, 0), (0.0, 0.22, 0)], steel,
                        Matrix.Translation((-0.48, y, z)) @ RYm, steps=24, bevel=0.006))
    piv = Vector((-0.86, -0.42, 0.52))
    end = Vector((-0.80, y, z))
    d = end - piv
    def lever(bm):
        Mz = frame_to(piv + d / 2, Vector((1, 0, 0)))
        ang = math.atan2(d.z, d.y)
        Ml = Matrix.Translation(piv + d / 2) @ Matrix.Rotation(ang, 4, "X")
        C.box_bm(bm, 0.04, d.length + 0.12, 0.10, matrix=Ml)
    out.append(solid("Lever", lever, [steel], bevel=0.01))
    out.append(lathe_at("Pivot", [(0.0, 0.0, 0), (0.07, 0.0, 0), (0.07, 0.10, 0), (0.0, 0.10, 0)], iron,
                        Matrix.Translation(piv + Vector((0.02, 0, 0))) @ RY, steps=32, bevel=0.008))
    out.append(lathe_at("Clip", [(0.0, 0.0, 0), (0.035, 0.0, 0), (0.035, 0.07, 0), (0.0, 0.07, 0)], zinc,
                        Matrix.Translation(end + Vector((-0.04, 0, 0))) @ RYm, steps=20))
    return out


def build():
    alu = cast_alu("CompAlu", base=0.40, rough=0.42, grime=0.65, grain=200.0, wear=0.25)
    bore = C.mat_machined("CompBore", color=0.48, rough=0.25, rings=400)
    wheel = C.mat_machined("Wheel", color=0.70, rough=0.22, rings=600)
    dark = C.principled("Dark", (0.015, 0.015, 0.015), rough=0.7)
    iron = hot_iron()
    iron2 = C.mat_cast_iron("CartIron", rust=0.25, base=0.16)
    soot = C.principled("Soot", (0.03, 0.028, 0.026), metallic=0.3, rough=0.8)
    C.add_noise_bump(soot, scale=200, strength=0.2, distance=0.002)
    steel = C.principled("Steel", (0.50, 0.50, 0.51), metallic=1.0, rough=0.30)
    C.add_noise_bump(steel, scale=400, strength=0.04, distance=0.0008)
    zinc = C.principled("Zinc", (0.62, 0.60, 0.50), metallic=1.0, rough=0.32)
    C.add_noise_bump(zinc, scale=400, strength=0.04, distance=0.0008)
    paint = C.mat_paint("ActuatorBlack", (0.02, 0.02, 0.022, 1), rough=0.38, coat=0.3)
    rubber = C.mat_rubber("Hose")
    objs = compressor(alu, bore, wheel, dark)
    t, Pe, tang = turbine(iron, steel, soot)
    objs += t + cartridge(iron2, steel, alu) + oil_lines(steel, zinc, rubber, iron2) + actuator(paint, zinc, steel, rubber, iron2)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    kw = dict(res=(512, 512), samples=32) if FAST else {}
    C.shoot("turbina", objs, "turbina.py",
            "turbocharger: cast-iron turbine housing, aluminium compressor housing with visible wheel, centre cartridge with oil lines, wastegate actuator",
            az=38, el=22, lens=70, fill=0.84, **kw)
