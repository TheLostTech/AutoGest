"""Shared scene, lighting, material and geometry helpers for the catalogue packshots.

Every part script does:
    import common as C
    C.clear()
    objs = build()
    C.shoot("name", objs, script="name.py", az=.., el=..)
Run headless:
    Blender -b --factory-startup --python assets-src/blender/<part>.py
"""
import bpy, bmesh, math, os, json, time, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "public", "renders")
TAU = math.tau


# ----------------------------------------------------------------- utilities
def srgb(hexstr, a=1.0):
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (a,)


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.images):
        for d in list(coll):
            try:
                coll.remove(d)
            except Exception:
                pass


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_obj(name, bm, mats=()):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    for m in mats:
        me.materials.append(m)
    return link(ob)


def lathe(name, prof, mats, steps=128, closed=True, axis_mat=None, mod=None):
    """Revolve a 2D profile [(r, z, mat_index), ...] around Z.
    mat_index applies to the segment from point i to i+1.
    mod(r, z, theta) -> r optionally modulates radius (fins)."""
    bm = bmesh.new()
    rings = []
    for (r, z, _mi) in prof:
        ring = []
        for k in range(steps):
            t = TAU * k / steps
            rr = mod(r, z, t) if mod else r
            ring.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), z)))
        rings.append(ring)
    n = len(prof)
    for i in range(n if closed else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        mi = prof[i][2]
        for k in range(steps):
            k2 = (k + 1) % steps
            try:
                f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
                f.material_index = mi
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    # drop degenerate faces created at poles
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    if closed:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mats)


def box_bm(bm, sx, sy, sz, center=(0, 0, 0), mat=0, matrix=None):
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    M = Matrix.Translation(center) @ Matrix.Diagonal((sx, sy, sz, 1.0))
    if matrix is not None:
        M = matrix @ M
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mat
    return vs


def cyl_bm(bm, r, z0, z1, seg=24, matrix=None, mat=0, r1=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                radius1=r, radius2=(r if r1 is None else r1), depth=z1 - z0)
    vs = res["verts"]
    M = Matrix.Translation((0, 0, (z0 + z1) / 2))
    if matrix is not None:
        M = matrix @ M
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mat
    return vs


def add_bevel(ob, width, segments=2, angle=30, clamp=True):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = clamp
    return m


def add_boolean(ob, cutter, op="DIFFERENCE"):
    m = ob.modifiers.new("Bool", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"
    try:
        m.material_mode = "TRANSFER"
    except Exception:
        pass
    cutter.hide_render = True
    cutter.hide_viewport = True
    return m


def finalize(ob, angle=32, remove=()):
    """Apply all modifiers (or convert curve) into a plain mesh, smooth shade with
    sharp edges by angle. Returns the new mesh object."""
    for c in remove:
        c.hide_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    new = bpy.data.objects.new(ob.name + "_m", me)
    new.matrix_world = ob.matrix_world.copy()
    link(new)
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = math.radians(angle)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            try:
                e.smooth = e.calc_face_angle() < lim
            except ValueError:
                e.smooth = True
    bm.to_mesh(me)
    bm.free()
    bpy.data.objects.remove(ob, do_unlink=True)
    for c in remove:
        bpy.data.objects.remove(c, do_unlink=True)
    return new


def transform_all(objs, M):
    for o in objs:
        o.matrix_world = M @ o.matrix_world


# ----------------------------------------------------------------- materials
def _mat(name):
    m = bpy.data.materials.new(name)
    try:
        if not m.use_nodes:
            m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return m, nt, bsdf


def _set(node, name, val):
    try:
        node.inputs[name].default_value = val
    except Exception as e:
        print("input?", name, e)


def principled(name, color, metallic=0.0, rough=0.5, **kw):
    m, nt, b = _mat(name)
    _set(b, "Base Color", color if len(color) == 4 else tuple(color) + (1,))
    _set(b, "Metallic", metallic)
    _set(b, "Roughness", rough)
    for k, v in kw.items():
        _set(b, k.replace("_", " "), v)
    return m


def _coord(nt, kind="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs[kind]


def add_noise_bump(m, scale=200.0, strength=0.1, distance=0.002, detail=6.0, rough_var=0.0):
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if rough_var:
        base = b.inputs["Roughness"].default_value
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = base - rough_var
        mr.inputs["To Max"].default_value = base + rough_var
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return bump


def add_radial_aniso(m, aniso=0.6, axis="Z", rings_scale=0.0, ring_strength=0.05):
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tg = nt.nodes.new("ShaderNodeTangent")
    tg.direction_type = "RADIAL"
    tg.axis = axis
    _set(b, "Anisotropic", aniso)
    nt.links.new(tg.outputs["Tangent"], b.inputs["Tangent"])
    if rings_scale:
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type = "RINGS"
        wv.rings_direction = axis
        wv.inputs["Scale"].default_value = rings_scale
        wv.inputs["Distortion"].default_value = 2.0
        wv.inputs["Detail"].default_value = 4.0
        nt.links.new(_coord(nt), wv.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = ring_strength
        bump.inputs["Distance"].default_value = 0.001
        nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])


def edge_mask(nt, radius=0.02, gain=6.0):
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.samples = 8
    bev.inputs["Radius"].default_value = radius
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(bev.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[0].default_value = 1.0
    nt.links.new(dot.outputs["Value"], sub.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    mul.inputs[1].default_value = gain
    nt.links.new(sub.outputs[0], mul.inputs[0])
    return mul.outputs[0]


def mat_cast_iron(name="CastIron", rust=0.6, base=0.13):
    m = principled(name, (base, base, base * 1.02), metallic=0.85, rough=0.62)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # mottled cast surface
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_coord(nt), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 9.0
    nz.inputs["Detail"].default_value = 8.0
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(_coord(nt), nz2.inputs["Vector"])
    nz2.inputs["Scale"].default_value = 350.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # rust at edges, broken up by noise
    em = edge_mask(nt, 0.03, 5.0)
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.45
    ramp.inputs["From Max"].default_value = 0.7
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Value"])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.use_clamp = True
    nt.links.new(em, fac.inputs[0])
    nt.links.new(ramp.outputs["Result"], fac.inputs[1])
    fac2 = nt.nodes.new("ShaderNodeMath")
    fac2.operation = "MULTIPLY"
    fac2.inputs[1].default_value = rust
    nt.links.new(fac.outputs[0], fac2.inputs[0])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    nt.links.new(fac2.outputs[0], mixc.inputs["Factor"])
    mixc.inputs["A"].default_value = (base, base, base * 1.02, 1)
    mixc.inputs["B"].default_value = (0.20, 0.065, 0.022, 1)
    nt.links.new(mixc.outputs["Result"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.85
    mr.inputs["To Max"].default_value = 0.1
    nt.links.new(fac2.outputs[0], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Metallic"])
    return m


def mat_machined(name="Machined", color=0.52, rough=0.2, rings=600.0):
    m = principled(name, (color, color, color * 1.01), metallic=1.0, rough=rough)
    add_radial_aniso(m, 0.75, "Z", rings_scale=rings, ring_strength=0.06)
    return m


def mat_chrome(name="Chrome"):
    return principled(name, (0.92, 0.92, 0.93), metallic=1.0, rough=0.04)


def mat_black_plastic(name="BlackABS", rough=0.45, color=0.022, tex=True):
    m = principled(name, (color, color, color * 1.05), rough=rough)
    if tex:
        add_noise_bump(m, scale=900, strength=0.06, distance=0.0005, rough_var=0.05)
    return m


def mat_clear(name="Polycarbonate", rough=0.0, ior=1.585):
    m = principled(name, (1, 1, 1), rough=rough, IOR=ior)
    _set(next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), "Transmission Weight", 1.0)
    return m


def mat_rubber(name="Rubber"):
    m = principled(name, (0.028, 0.028, 0.028), rough=0.78)
    add_noise_bump(m, scale=400, strength=0.08, distance=0.001)
    return m


def mat_paint(name, color, rough=0.3, coat=0.6, metallic=0.0):
    m = principled(name, color, metallic=metallic, rough=rough)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    _set(b, "Coat Weight", coat)
    _set(b, "Coat Roughness", 0.06)
    return m


# ----------------------------------------------------------------- render setup
def setup_render(w=1024, h=1024, samples=128):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    dev = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "METAL"
            if d.use:
                dev = "GPU"
    except Exception as e:
        print("GPU setup failed:", e)
    sc.cycles.device = dev
    print("Cycles device:", dev)
    cy = sc.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.012
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 12
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 6
    cy.transmission_bounces = 12
    cy.transparent_max_bounces = 16
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    try:
        cy.film_transparent_glass = True
    except Exception:
        pass
    r = sc.render
    r.film_transparent = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 90
    vs = sc.view_settings
    for vt in ("Khronos PBR Neutral", "AgX", "Standard"):
        try:
            vs.view_transform = vt
            break
        except Exception:
            continue
    try:
        vs.look = "None"
    except Exception:
        pass
    vs.exposure = 0.0
    vs.gamma = 1.0
    print("View transform:", vs.view_transform)


def _points(objs, maxn=60000):
    pts = []
    total = sum(len(o.data.vertices) for o in objs if o.type == "MESH") or 1
    step = max(1, total // maxn)
    for o in objs:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        vs = o.data.vertices
        for i in range(0, len(vs), step):
            pts.append(mw @ vs[i].co)
    return pts


def _look(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _area(name, loc, target, size, energy, size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size = size
    ld.size_y = size_y or size
    ld.energy = energy
    try:
        ld.cycles.max_bounces = 8
    except Exception:
        pass
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    _look(ob, target)
    return ob


def setup_world(strength=0.35):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # generated z of world goes -1..1 (direction); map to ramp
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.40
    cr.elements[0].color = (0.04, 0.04, 0.045, 1)
    cr.elements[1].position = 0.80
    cr.elements[1].color = (1.0, 1.0, 1.0, 1)
    e = cr.elements.new(0.5)
    e.color = (0.22, 0.22, 0.23, 1)
    e = cr.elements.new(0.62)
    e.color = (0.30, 0.30, 0.31, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def shoot(name, objs, script, obj_desc, az=35.0, el=20.0, lens=60.0, fill=0.80,
          res=(1024, 1024), center=(0.5, 0.5), samples=128, ground=True,
          key=1.0, extra_name=None, save_blend=False, fill_w=None, fill_h=None):
    """Light, frame and render objs to public/renders/<name>.png (+ .json sidecar)."""
    t0 = time.time()
    sc = bpy.context.scene
    setup_render(res[0], res[1], samples)
    setup_world(0.35)
    pts = _points(objs)
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    Cn = (mn + mx) / 2
    R = (mx - mn).length / 2
    # ground / contact shadow
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=R * 40, location=(Cn.x, Cn.y, mn.z))
        pl = bpy.context.active_object
        pl.name = "ShadowCatcher"
        pl.is_shadow_catcher = True
    # studio lights (scaled to object size)
    E = 290.0 * R * R * key
    _area("Key", Cn + R * Vector((-2.4, -2.6, 3.4)), Cn, 3.6 * R, E)
    _area("Fill", Cn + R * Vector((3.4, -2.2, 1.2)), Cn, 4.2 * R, E * 0.38)
    _area("Top", Cn + R * Vector((0.4, 0.8, 4.6)), Cn, 5.0 * R, E * 0.55)
    _area("Rim", Cn + R * Vector((1.8, 3.6, 2.0)), Cn, 3.0 * R, E * 0.55)
    _area("Front", Cn + R * Vector((0.2, -4.6, 0.6)), Cn, 3.0 * R, E * 0.18, size_y=1.2 * R)
    # camera
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.sensor_fit = "AUTO"
    cam = link(bpy.data.objects.new("Cam", cd))
    sc.camera = cam
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    fov = 2 * math.atan(18.0 / lens)
    dist = R / math.tan(fov / 2) / fill
    W, H = res
    big = max(W, H)
    fw = fill_w or fill
    fh = fill_h or fill
    for _ in range(8):
        cam.location = Cn + d * dist
        _look(cam, Cn)
        bpy.context.view_layer.update()
        ndc = [world_to_camera_view(sc, cam, p) for p in pts]
        xs = [p.x for p in ndc]
        ys = [p.y for p in ndc]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        s = max(w / fw, h / fh)
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        cd.shift_x += (cx - center[0]) * W / big
        cd.shift_y += (cy - center[1]) * H / big
        dist *= s
    cam.location = Cn + d * dist
    _look(cam, Cn)
    os.makedirs(OUT, exist_ok=True)
    fname = (extra_name or name) + ".png"
    path = os.path.join(OUT, fname)
    sc.render.filepath = path
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    t2 = time.time()
    with open(path + ".json", "w") as f:
        json.dump({"origin": "rendered with Blender 5.3 from assets-src/blender/%s" % script,
                   "generator": "procedural", "object": obj_desc}, f, indent=2)
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"), compress=True)
    print("RENDERED %s in %.1fs (setup %.1fs)" % (path, t2 - t1, t1 - t0))
    stats(path)
    return path


def stats(path):
    import numpy as np
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    a = px[..., 3]
    ys, xs = np.nonzero(a > 0.5)
    lum = px[..., :3].mean(axis=2)[a > 0.98]
    print("STATS size=%dx%d bbox x[%d..%d] y[%d..%d] (of %d,%d) opaque=%.1f%% lum p5=%.2f p50=%.2f p95=%.2f p99.5=%.2f edge_alpha_max=%.3f" % (
        w, h, xs.min(), xs.max(), ys.min(), ys.max(), w, h, 100 * (a > 0.5).mean(),
        np.percentile(lum, 5), np.percentile(lum, 50), np.percentile(lum, 95), np.percentile(lum, 99.5),
        max(a[0, :].max(), a[-1, :].max(), a[:, 0].max(), a[:, -1].max())))
    pdir = os.environ.get("PREVIEW_DIR")
    if pdir:
        os.makedirs(pdir, exist_ok=True)
        bg = np.array([0.96, 0.96, 0.95], dtype=np.float32)
        comp = px.copy()
        comp[..., :3] = px[..., :3] + bg * (1 - a[..., None])  # premultiplied? PNG is straight
        comp[..., :3] = px[..., :3] * a[..., None] + bg * (1 - a[..., None])
        comp[..., 3] = 1
        im = bpy.data.images.new("prev", w, h)
        im.pixels.foreach_set(comp.ravel())
        im.filepath_raw = os.path.join(pdir, os.path.basename(path))
        im.file_format = "PNG"
        im.save()


def label_image(name="Label", w=1024, h=512, seed=3, border=True, barcode=True, lines=5):
    """Procedural blank adhesive label: white, thin grey border, dark-grey bars
    hinting at text and a barcode. No readable words."""
    import numpy as np
    rnd = random.Random(seed)
    img = np.ones((h, w, 4), dtype=np.float32)
    img[..., :3] = 0.985
    g = 0.62
    dark = 0.16

    def rect(x0, y0, x1, y1, v):  # y measured from top
        img[h - y1:h - y0, x0:x1, :3] = v

    if border:
        m, t = int(h * 0.045), max(2, int(h * 0.006))
        rect(m, m, w - m, m + t, g)
        rect(m, h - m - t, w - m, h - m, g)
        rect(m, m, m + t, h - m, g)
        rect(w - m - t, m, w - m, h - m, g)
    pad = int(h * 0.12)
    # heading bar
    rect(pad, pad, pad + int(w * 0.36), pad + int(h * 0.075), dark)
    y = pad + int(h * 0.15)
    for i in range(lines):
        L = int(w * rnd.uniform(0.22, 0.48))
        rect(pad, y, pad + L, y + int(h * 0.035), 0.42)
        y += int(h * 0.075)
    # small code block on right
    rect(int(w * 0.66), pad, w - pad, pad + int(h * 0.075), dark)
    rect(int(w * 0.66), pad + int(h * 0.11), int(w * 0.80), pad + int(h * 0.145), 0.42)
    if barcode:
        x = int(w * 0.60)
        x1 = w - pad
        y0, y1 = int(h * 0.52), h - pad
        while x < x1:
            bw = rnd.choice((2, 3, 3, 5, 7))
            if x + bw > x1:
                break
            rect(x, y0, x + bw, y1, 0.08)
            x += bw + rnd.choice((2, 3, 4, 6))
    im = bpy.data.images.new(name, w, h, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.pack()
    return im


def mat_label(im, name="LabelMat", rough=0.38):
    m = principled(name, (1, 1, 1), rough=rough)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    tx.interpolation = "Cubic"
    nt.links.new(_coord(nt, "UV"), tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    return m


def label_plane(name, mat, width, height, matrix):
    """Plane in local XZ (normal -Y) with 0..1 UVs, placed by matrix."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    hw, hh = width / 2, height / 2
    vs = [bm.verts.new(c) for c in ((-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh))]
    f = bm.faces.new(vs)
    for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uv].uv = c
    f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    ob = mesh_obj(name, bm, [mat])
    ob.matrix_world = matrix
    return ob


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def sweep(bm, frames, mat=0, cap=True):
    """frames: [(P, U, V, [(u, v), ...]), ...] -> skinned tube; section closed."""
    rings = [[bm.verts.new(P + u * U + v * V) for (u, v) in sec] for (P, U, V, sec) in frames]
    m = len(rings[0])
    faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(m):
            k2 = (k + 1) % m
            faces.append(bm.faces.new((a[k], a[k2], b[k2], b[k])))
    if cap:
        faces.append(bm.faces.new(rings[0][::-1]))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def fix_normals(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
