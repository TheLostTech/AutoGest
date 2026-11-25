"""Wheel nut (dado ruota), generic catalogue image for the whole family: one open-ended
M12 x 1.5 wheel nut, 19 mm hex, with the 60-degree conical seat, bright chrome plated,
standing on its seat and seen from above so the threaded bore shows.

Clean construction (no radius tricks on the hex, which gave jagged chamfer arcs): a hex
prism with rounded corners intersected with the 30-degree chamfer cone, united with the
turned conical seat/collar, then the helical threaded bore cut out. The white floor is
hidden from glossy rays and a soft glossy-only studio card gives the chrome a readable
light-to-dark gradient instead of blown-out white."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

AF = 1.9
P = 0.15
RMIN = 0.52
ZCT = 0.52     # cone top
ZH0 = 0.58     # hex bottom
HT = 1.95      # total height
AZ, EL = -30, 30


def hex_core(mat):
    """Hex prism, corners rounded, chamfered top and bottom by a revolved cone."""
    a = AF / 2
    rcorner = a / math.cos(math.pi / 6)
    bm = bmesh.new()
    vb = [bm.verts.new((rcorner * math.cos(k * math.pi / 3), rcorner * math.sin(k * math.pi / 3), ZH0 - 0.02))
          for k in range(6)]
    vt = [bm.verts.new((v.co.x, v.co.y, HT)) for v in vb]
    for k in range(6):
        k2 = (k + 1) % 6
        bm.faces.new((vb[k], vb[k2], vt[k2], vt[k]))
    bm.faces.new(vb[::-1])
    bm.faces.new(vt)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    vert_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1]
    bmesh.ops.bevel(bm, geom=vert_edges, offset=0.06, segments=6, profile=0.5, affect="EDGES")
    ob = C.mesh_obj("Hex", bm, [mat])
    # chamfer solid: 30-degree cone at the top face, a light one at the bottom
    rch = a * 0.955
    rb = a * 1.0
    big = rcorner + 0.1
    prof = [(0.0, ZH0 - 0.03, 0), (rb, ZH0 - 0.03, 0), (big, ZH0 - 0.03 + (big - rb) / 1.732, 0),
            (big, HT - (big - rch) / 1.732, 0), (rch, HT, 0), (0.0, HT, 0)]
    ch = C.lathe("Chamfer", prof, [mat], steps=256)
    m = C.add_boolean(ob, ch, "INTERSECT")
    return ob, ch


def seat(mat):
    """Turned conical seat and collar, overlapping into the hex for the union."""
    t30 = math.tan(math.radians(30))
    r0 = 0.70
    prof = [(0.60, 0.0, 0), (r0 - 0.012, 0.0, 0), (r0, 0.010, 0)]
    for i in range(1, 9):
        z = 0.010 + (ZCT - 0.010) * i / 8
        prof.append((r0 + (z - 0.010) * t30, z, 0))
    rt = prof[-1][0]
    prof += [(rt + 0.006, ZCT + 0.010, 0), (rt + 0.006, ZH0 - 0.012, 0), (rt - 0.008, ZH0, 0),
             (AF / 2 * 0.9, ZH0 + 0.06, 0), (0.60, ZH0 + 0.06, 0)]
    return C.lathe("Seat", prof, [mat], steps=256)


def bore_cutter(mat):
    """Solid of the threaded hole (helical M12 x 1.5 thread, 90-degree countersinks)."""
    fb = M.int_thread(RMIN, P, cs=[(0.0, 0.66), (HT, 0.66)])
    z0, z1 = -0.12, HT + 0.12
    n = int((z1 - z0) / P * 16)
    prof = [(0.0, z0, 0)] + [(0.0, z0 + (z1 - z0) * i / n, 0, "bore") for i in range(n + 1)] + [(0.0, z1, 0)]
    return M.revolve("Bore", prof, [mat], steps=240, fn=lambda tag, r, z, t: fb(r, z, t))


def nut(mat):
    ob, ch = hex_core(mat)
    st = seat(mat)
    C.add_boolean(ob, st, "UNION")
    C.add_bevel(ob, 0.008, segments=3, angle=50)
    bc = bore_cutter(mat)
    mb = C.add_boolean(ob, bc, "DIFFERENCE")
    mb.solver = "MANIFOLD"
    return C.finalize(ob, angle=26, remove=[ch, st, bc])


def chrome():
    m = M.mat_chrome_bright("Chrome")
    b = M._b(m)
    C._set(b, "Base Color", (0.80, 0.81, 0.83, 1))
    C._set(b, "Roughness", 0.08)
    return m


def studio_card(center, normal, view, dist, size, lo=0.10, hi=1.0, strength=1.0, band=(0.30, 0.70), name="Card"):
    """Large soft emissive card seen only by glossy rays, placed where `normal` reflects
    the view direction: gives polished metal a smooth studio gradient (dark-to-white
    along the card's up axis), never pure black."""
    v = view.normalized()
    n = normal.normalized()
    r = (2 * n.dot(v) * n - v).normalized()
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    h = size / 2
    vs = [bm.verts.new(c) for c in ((-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0))]
    f = bm.faces.new(vs)
    for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uv].uv = c
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position = band[0]
    cr.elements[0].color = (lo, lo, lo, 1)
    cr.elements[1].position = band[1]
    cr.elements[1].color = (hi, hi, hi, 1)
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob = C.mesh_obj(name, bm, [m])
    z = (-r).normalized()
    up = Vector((0, 0, 1))
    x = up.cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x).normalized()
    Mx = Matrix.Identity(4)
    for i, ax in enumerate((x, y, z)):
        Mx[0][i], Mx[1][i], Mx[2][i] = ax.x, ax.y, ax.z
    Mx.translation = Vector(center) + r * dist
    ob.matrix_world = Mx
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    return ob


def glossy_dome(center, radius, K, stops, name="Dome"):
    """Big sphere seen only by glossy rays (replaces the plain studio world in the
    reflections): emission brightness ramps with the direction from the centre against
    K, so differently oriented flats of a polished part reflect different greys."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=radius)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(nrm.outputs[0], dot.inputs[0])
    dot.inputs[1].default_value = tuple(Vector(K).normalized())
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (stops[0][1],) * 3 + (1,)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (stops[-1][1],) * 3 + (1,)
    for pos, val in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (val, val, val, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob = C.mesh_obj(name, bm, [m])
    ob.location = center
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    return ob


def hide_floor_from_glossy():
    """The white shadow catcher reflected in the chrome blew it out to white: hide it
    from glossy rays (contact shadow kept); the big rim light, mirrored flat in the top
    face, is hidden from glossy rays too."""
    orig = C._area

    def _area(name, *a, **k):
        pl = bpy.data.objects.get("ShadowCatcher")
        if pl is not None:
            pl.visible_glossy = False
        ob = orig(name, *a, **k)
        if name == "Rim":
            ob.visible_glossy = False
        return ob
    C._area = _area


def view_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def build():
    ob = nut(chrome())
    ob.matrix_world = Matrix.Rotation(math.radians(8), 4, "Z")
    return [ob]


if __name__ == "__main__":
    hide_floor_from_glossy()
    C.clear()
    objs = build()
    v = view_dir(AZ, EL)
    c = Vector((0, 0, HT * 0.5))
    # the flats facing the camera reflect the space below the horizon, which the plain
    # studio world leaves black: a glossy-only dome, bright up-left, dark down-right
    glossy_dome(c, 40.0, (-0.55, -0.25, 0.80), [(0.0, 0.05), (0.35, 0.16), (0.6, 0.50), (0.85, 0.92), (1.0, 1.0)])
    C.shoot("dado-ruota", objs, "dado-ruota.py",
            "open-ended wheel nut M12x1.5, 19 mm hex, 60-degree conical seat, chrome plated",
            az=AZ, el=EL, lens=85, fill=0.84, **M.shoot_kw())
