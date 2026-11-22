"""Shared helpers for the small-hardware packshots (bolts, nuts, washers, clips, springs).

Scale: 1 unit = 1 cm.  Everything round is a revolve of a 2D profile whose radius can be
modulated per point by a function of (tag, r, z, theta): that gives real helical threads,
hexagonal heads with the classic 30-degree chamfer arcs, hex/Torx sockets and so on,
all as one clean mesh without booleans.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

TAU = math.tau
QUICK = bool(os.environ.get("QUICK"))


def shoot_kw():
    return dict(res=(512, 512), samples=32) if QUICK else dict(res=(1024, 1024), samples=128)


# ----------------------------------------------------------------- revolve
def revolve(name, prof, mats, steps=192, fn=None, closed=True):
    """prof: [(r, z, mat_index[, tag]), ...] revolved around Z.
    fn(tag, r, z, theta) -> radius (only called for points with a tag)."""
    bm = bmesh.new()
    rings = []
    for p in prof:
        r, z, _mi = p[0], p[1], p[2]
        tag = p[3] if len(p) > 3 else None
        ring = []
        for k in range(steps):
            t = TAU * k / steps
            rr, zz = r, z
            if fn and tag:
                rr = fn(tag, r, z, t)
                if isinstance(rr, tuple):
                    rr, zz = rr
            ring.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), zz)))
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
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-14]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.mesh_obj(name, bm, mats)


def seg(r0, z0, r1, z1, n, mi=0, tag=None, include_end=False):
    """n samples of a straight profile segment (end point excluded unless include_end)."""
    out = []
    m = n + (1 if include_end else 0)
    for i in range(m):
        u = i / n
        out.append((r0 + (r1 - r0) * u, z0 + (z1 - z0) * u, mi, tag))
    return out


# ----------------------------------------------------------------- shapes
def hex_r(t, af, corner=0.975, phase=0.0):
    """radius of a hexagon (across flats af) at angle t; corners slightly rounded
    (corner = fraction of the sharp corner radius kept)."""
    a = af / 2
    ph = (t - phase) % (TAU / 6) - TAU / 12
    r = a / math.cos(ph)
    rc = a / math.cos(TAU / 12) * corner
    if r > rc:   # round the corner: blend toward rc smoothly
        r = rc + (r - rc) * 0.15
    return r


def torx_r(t, a_out, a_in, phase=0.0):
    """hexalobular (Torx) socket outline radius."""
    c = math.cos(6 * (t - phase))
    # sharpen the inner lobes, round the outer ones
    s = 0.5 + 0.5 * c
    s = s ** 0.8
    return a_in + (a_out - a_in) * s


def thread_h(u, sharp=1.0):
    """0..1 thread height for phase u (0 root, 0.5 crest), trapezoid with rounding.
    sharp > 1 gives a narrower crest (self-tapping threads)."""
    tri = 1.0 - abs(2.0 * (u % 1.0) - 1.0)
    h = C.smoothstep(0.12, 0.88, tri)
    return h ** sharp if sharp != 1.0 else h


def ext_thread(r_major, pitch, z0, z1, depth=None, runout0=1.0, runout1=0.0,
               tip_cham=None, base_cham=None, left=False, sharp=1.0, tip_cone=None):
    """returns fn(r, z, t) for an external thread between z0 and z1.
    runout*: thread fades in over this many pitches at z0 / z1 (0 = sharp start).
    tip_cham: (z_end, r_at_end) chamfer cone at the z1 end (45 deg)."""
    depth = depth or 0.62 * pitch
    sgn = -1.0 if left else 1.0

    def f(r, z, t):
        u = (z - sgn * pitch * t / TAU) / pitch
        k = 1.0
        if runout0 > 0:
            k *= C.smoothstep(z0, z0 + runout0 * pitch, z)
        if runout1 > 0:
            k *= C.smoothstep(z1, z1 - runout1 * pitch, z)
        # in the run-out the root rises back to the plain shank radius
        rr = r_major - depth * (1.0 - thread_h(u, sharp)) * k
        if tip_cham:
            ze, re = tip_cham
            lim = re + abs(ze - z)
            rr = min(rr, lim)
        if tip_cone:   # (z_point, slope): pointed gimlet tip, thread runs out onto the cone
            zp, sl = tip_cone
            lim = max(0.0, (zp - z) * sl)
            core = r_major - depth
            if lim < core:
                rr = min(rr, lim + (rr - core) * max(0.0, lim / core) ** 0.5) if core > 0 else lim
        if base_cham:
            zb, rb = base_cham
            rr = min(rr, rb + abs(z - zb))
        return rr
    return f


def thread_samples(z0, z1, pitch, mi=0, tag="thr", per_pitch=16):
    n = max(2, int(round(abs(z1 - z0) / pitch * per_pitch)))
    return [(0.0, z0 + (z1 - z0) * i / n, mi, tag) for i in range(n + 1)]


def int_thread(r_minor, pitch, depth=None, cs=None):
    """internal thread (nut bore): radius grows from minor into the flanks.
    cs: [(z_face, r_at_face), ...] 90-degree countersinks at the bore ends."""
    depth = depth or 0.55 * pitch

    def f(r, z, t):
        u = (z - pitch * t / TAU) / pitch
        rr = r_minor + depth * (1.0 - thread_h(u + 0.5))
        for (zf, rf) in (cs or ()):
            rr = max(rr, rf - abs(z - zf))
        return rr
    return f


def nut_fn(af, z0, z1, cham0=True, cham1=True, rc=0.95, corner=0.975):
    """outer hex of a nut between z0 and z1 with 30-degree chamfers on the chosen faces."""
    a = af / 2

    def f(r, z, t):
        rr = hex_r(t, af, corner=corner)
        if cham0:
            rr = min(rr, a * rc + (z - z0) * 1.732)
        if cham1:
            rr = min(rr, a * rc + (z1 - z) * 1.732)
        return rr
    return f


def hex_side(z0, z1, rbig, n_end=14, n_mid=6, cham0=True, cham1=True, tag="hex", band=0.12):
    """profile samples for a hex side from z0 to z1, dense in the chamfer bands
    (excludes the z1 end point)."""
    out = []
    zs = [z0]
    za = z0 + (band if cham0 else 0.0)
    zb = z1 - (band if cham1 else 0.0)
    if cham0:
        zs += [z0 + band * i / n_end for i in range(1, n_end + 1)]
    zs += [za + (zb - za) * i / n_mid for i in range(1, n_mid + 1)]
    if cham1:
        zs += [zb + band * i / n_end for i in range(1, n_end)]
    zs = sorted(set(round(z, 7) for z in zs if z < z1 - 1e-6))
    if z1 > z0:
        return [(rbig, z, 0, tag) for z in zs]
    return [(rbig, z, 0, tag) for z in zs]


# ----------------------------------------------------------------- materials
def _b(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _noise(nt, scale, detail=4.0, kind="Object"):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(C._coord(nt, kind), nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    return nz


def _mottle(m, c_a, c_b, scale=6.0, lo=0.35, hi=0.7, r_a=None, r_b=None):
    """mix base colour (and roughness) between two values with a soft noise."""
    nt = m.node_tree
    b = _b(m)
    nz = _noise(nt, scale, 6.0)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = c_a
    mix.inputs["B"].default_value = c_b
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    if r_a is not None:
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = r_a
        rr.inputs["To Max"].default_value = r_b
        nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    return mr


def _fine_bump(m, scale=900.0, strength=0.08, distance=0.0004):
    nt = m.node_tree
    b = _b(m)
    nz = _noise(nt, scale, 8.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump


def mat_zinc(name="Zinc", tint=(0.50, 0.515, 0.55), rough=0.27, var=0.12):
    """clear/blue passivated zinc plating: bright, slightly bluish, softly mottled."""
    m = C.principled(name, tint, metallic=1.0, rough=rough)
    t2 = tuple(x * 0.86 for x in tint)
    _mottle(m, tint + (1,), (t2[0] * 0.98, t2[1], t2[2] * 1.03, 1), scale=3.5,
            r_a=rough - var * 0.5, r_b=rough + var)
    _fine_bump(m, 700.0, 0.10, 0.0004)
    return m


def mat_zinc_flake(name="ZincFlake"):
    """dull silver zinc-flake (Geomet-like) coating used on modern chassis screws."""
    m = C.principled(name, (0.40, 0.41, 0.42), metallic=1.0, rough=0.36)
    _mottle(m, (0.42, 0.43, 0.44, 1), (0.33, 0.34, 0.355, 1), scale=5.0, r_a=0.32, r_b=0.42)
    _fine_bump(m, 1400.0, 0.18, 0.0003)
    return m


def mat_black_oxide(name="BlackOxide", rough=0.30):
    """black-oxide steel with a thin oil film: dark, metallic, soft sheen, slight
    brownish variation and brighter worn edges."""
    m = C.principled(name, (0.035, 0.034, 0.033), metallic=0.9, rough=rough)
    nt = m.node_tree
    b = _b(m)
    mr = _mottle(m, (0.040, 0.039, 0.037, 1), (0.026, 0.024, 0.022, 1), scale=4.0,
                 r_a=rough - 0.06, r_b=rough + 0.10)
    _fine_bump(m, 900.0, 0.10, 0.0004)
    # edge wear: slightly brighter steel on sharp edges
    em = C.edge_mask(nt, 0.012, 4.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 0.55
    nt.links.new(em, k.inputs[0])
    nt.links.new(k.outputs[0], mix.inputs["Factor"])
    prev = b.inputs["Base Color"].links[0].from_socket
    nt.links.new(prev, mix.inputs["A"])
    mix.inputs["B"].default_value = (0.20, 0.20, 0.20, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_stainless(name="Stainless", rough=0.22, aniso_axis=None):
    m = C.principled(name, (0.66, 0.65, 0.63), metallic=1.0, rough=rough)
    _mottle(m, (0.68, 0.67, 0.65, 1), (0.60, 0.595, 0.58, 1), scale=4.0,
            r_a=rough - 0.04, r_b=rough + 0.08)
    # brushed: noise stretched along the brushing direction (object X, or UV U)
    nt = m.node_tree
    b = _b(m)
    mp = nt.nodes.new("ShaderNodeMapping")
    uv = aniso_axis == "UV"
    nt.links.new(C._coord(nt, "UV" if uv else "Object"), mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (8.0, 1800.0, 1.0) if uv else (25.0, 1800.0, 1800.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_chrome_bright(name="ChromeBright"):
    m = C.principled(name, (0.90, 0.90, 0.91), metallic=1.0, rough=0.06)
    _fine_bump(m, 600.0, 0.03, 0.0003)
    return m


def mat_plastic(name, color, rough=0.45, sss=0.0, bump=True):
    m = C.principled(name, color, rough=rough)
    b = _b(m)
    if sss:
        C._set(b, "Subsurface Weight", sss)
        C._set(b, "Subsurface Radius", (0.15, 0.15, 0.12))
        C._set(b, "Subsurface Scale", 0.05)
    if bump:
        _fine_bump(m, 1100.0, 0.05, 0.0003)
        nt = m.node_tree
        nz = _noise(nt, 60.0, 3.0)
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough - 0.05
        mr.inputs["To Max"].default_value = rough + 0.06
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


# ----------------------------------------------------------------- placement helpers
def place(objs, M):
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    return objs


def lie_on_x(objs, head_half_height, shank_r, length, roll=0.0):
    """rotate an object built along +Z (head at z<=0... tip at z=length) to lie along +X,
    tilted so it rests on both the head and the thread tip."""
    tilt = math.asin(max(0.0, (head_half_height - shank_r)) / max(length, 1e-6))
    M = Matrix.Rotation(tilt, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(roll, 4, "Z")
    return place(objs, M)


def drop_to_ground(objs, z=0.0):
    bpy.context.view_layer.update()
    mn = min((o.matrix_world @ v.co).z for o in objs if o.type == "MESH" for v in o.data.vertices)
    return place(objs, Matrix.Translation((0, 0, z - mn)))
