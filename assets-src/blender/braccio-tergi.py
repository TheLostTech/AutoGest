"""Front windscreen wiper arm with blade, generic small hatchback: satin-black die-cast
pivot head with the hinged plastic nut cap, pressed-steel U-channel with its exposed
tension spring and hinge rivet, flat tapering arm ending in the U-hook, and the flat
(beam) wiper blade clipped in the hook, black plastic spoiler with end caps over the
rubber wiping lip. Laid flat and diagonal, the blade turned slightly off the arm.
Arm along +X from the pivot at the origin, up is +Z."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

MM = 0.001
XC0, XC1 = 0.030, 0.170        # channel
XA1 = 0.415                    # end of the straight arm (hook start)
BL = 0.53                      # blade length
BLADE_ANG = 9.0                # blade angle off the arm (deg)


def satin_black(name="SatinBlack"):
    m = C.principled(name, (0.02, 0.02, 0.022), rough=0.45, Coat_Weight=0.15)
    C.add_noise_bump(m, scale=700, strength=0.10, distance=0.0003, rough_var=0.05)
    return m


def se(name, a, b, c, loc, mat, e1=0.35, e2=0.35, nu=64, nv=32, taper=None):
    bm = bmesh.new()
    vs = P.superellipsoid(bm, a, b, c, e1=e1, e2=e2, nu=nu, nv=nv)
    if taper:
        for v in vs:
            taper(v)
    for v in vs:
        v.co += Vector(loc)
    return C.mesh_obj(name, bm, [mat])


def head(sb, cap_m, steel):
    out = []

    def tp(v):           # narrower towards +X
        t = (v.co.x + 0.030) / 0.060
        v.co.y *= 1.0 - 0.25 * t
        v.co.z *= 1.0 - 0.30 * t
    h = se("Head", 0.030, 0.0145, 0.012, (0.006, 0, 0.012), sb, e1=0.4, e2=0.4, taper=tp)
    out.append(C.finalize(h, angle=50))
    # hinged nut cap on top of the pivot
    cap = se("Cap", 0.019, 0.0135, 0.0065, (-0.006, 0, 0.0262), cap_m, e1=0.45, e2=0.4)
    out.append(C.finalize(cap, angle=50))
    bm = bmesh.new()
    C.box_bm(bm, 0.005, 0.016, 0.004, center=(0.0135, 0, 0.0245))      # cap hinge knuckle
    k = C.mesh_obj("CapHinge", bm, [cap_m])
    C.add_bevel(k, 0.0015, segments=2, angle=30)
    out.append(C.finalize(k, angle=35))
    # hinge rivet through head and channel
    M = Matrix.Translation((0.032, 0, 0.016)) @ Matrix.Rotation(math.radians(90), 4, "X")
    rv = C.lathe("Rivet", [(0.0, -0.0118, 0), (0.0038, -0.0118, 0), (0.0042, -0.0105, 0), (0.0042, 0.0105, 0), (0.0038, 0.0118, 0),
                           (0.0, 0.0118, 0)], [steel], steps=32)
    rv.matrix_world = M
    out.append(C.finalize(rv, angle=40))
    return out


def channel(sb):
    """Inverted U channel (open underneath) from the hinge to the arm."""
    frames = []
    N = 40
    for k in range(N + 1):
        t = k / N
        x = XC0 + (XC1 - XC0) * t
        w = 0.0105 - 0.0035 * t
        h = 0.012 - 0.004 * t
        zt = 0.022 - 0.008 * t
        th = 0.0012
        sec = [(-w, zt - h), (-w, zt), (w, zt), (w, zt - h), (w - th, zt - h), (w - th, zt - th), (-w + th, zt - th), (-w + th, zt - h)]
        frames.append((Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sec))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Channel", bm, [sb])
    C.add_bevel(ob, 0.0004, segments=2, angle=40)
    return C.finalize(ob, angle=45)


def spring(steel):
    """Tension spring under the channel, hooked to the head and to the channel."""
    x0, x1 = 0.010, 0.120
    z = 0.0105
    pts = [Vector((x0 - 0.004, 0, z + 0.004)), Vector((x0, 0, z))]
    n = 22
    L = x1 - x0
    steps = 400
    for k in range(steps + 1):
        t = k / steps
        a = t * n * math.tau
        pts.append(Vector((x0 + 0.004 + (L - 0.008) * t, 0.0042 * math.sin(a), z + 0.0042 * math.cos(a))))
    pts += [Vector((x1, 0, z)), Vector((x1 + 0.006, 0, z + 0.006))]
    fr = P.path_frames(pts, (0, 0, 1))
    return P.tube_obj("Spring", fr, P.circle(0.00065, 10), [steel], smooth_angle=70)


def arm(sb):
    out = []
    pts = []
    N = 60
    for k in range(N + 1):
        t = k / N
        pts.append(Vector((XC1 - 0.020 + (XA1 - XC1 + 0.020) * t, 0, 0.0145 - 0.0060 * t)))
    # U-hook at the end: bends down and back under itself
    c = pts[-1] + Vector((0, 0, -0.0058))
    for k in range(1, 25):
        a = math.pi * k / 24
        pts.append(c + Vector((0.0058 * math.sin(a), 0, 0.0058 * math.cos(a))))
    end = pts[-1]
    pts += [end + Vector((-0.024 * j / 8, 0, 0)) for j in range(1, 9)]
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    tot = acc[-1]
    frames = []
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        U = Vector((0, 1, 0))
        V = T.cross(U) * -1
        s = acc[i] / tot
        w = 0.0050 - 0.0008 * s
        th = 0.0019 if acc[i] < tot - 0.045 else 0.0013
        frames.append((p, U, V, P.rrect(-w, w, -th, th, min(th * 0.8, 0.0012), seg=3)))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("Arm", bm, [sb]), angle=50))
    return out, c


def blade(spoiler_m, rubber, adapter_m, hook_c):
    out = []
    ang = math.radians(BLADE_ANG)
    d = Vector((math.cos(ang), math.sin(ang), 0))
    side = Vector((-d.y, d.x, 0))
    ctr = Vector((hook_c.x - 0.004, hook_c.y, hook_c.z - 0.0058))
    N = 120
    # spoiler: asymmetric wing section, height tapering to the ends
    frames, frames_r = [], []
    for k in range(N + 1):
        t = k / N
        u = (t - 0.5) * 2
        e = math.sqrt(max(1 - abs(u) ** 6, 0.02))
        x = (t - 0.5) * BL
        P0 = ctr + d * x
        hgt = 0.0135 * e
        wid = 0.0125 * (0.75 + 0.25 * e)
        sec = [(-wid, 0.0045), (-wid * 0.55, 0.0045 + hgt * 0.55), (0.0, 0.0045 + hgt), (wid * 0.35, 0.0045 + hgt * 0.75),
               (wid, 0.0048), (wid * 0.9, 0.0030), (-wid * 0.9, 0.0030)]
        frames.append((P0, side, Vector((0, 0, 1)), sec))
        rsec = [(-0.0035, 0.0032), (0.0035, 0.0032), (0.0011, 0.0006), (0.0002, 0.0), (-0.0002, 0.0), (-0.0011, 0.0006)]
        frames_r.append((P0 + d * 0.0, side, Vector((0, 0, 1)), rsec))
    bm = bmesh.new()
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Spoiler", bm, [spoiler_m])
    C.add_bevel(ob, 0.0005, segments=2, angle=40)
    out.append(C.finalize(ob, angle=50))
    bm = bmesh.new()
    C.sweep(bm, frames_r[1:-1], mat=0)
    C.fix_normals(bm)
    out.append(C.finalize(C.mesh_obj("Rubber", bm, [rubber]), angle=60))
    # end caps
    for s in (-1, 1):
        M = Matrix.Translation(ctr + d * s * (BL / 2 - 0.006)) @ Matrix.Rotation(ang, 4, "Z")
        bm = bmesh.new()
        P.superellipsoid(bm, 0.010, 0.0085, 0.0065, e1=0.5, e2=0.5, nu=48, nv=24, matrix=M @ Matrix.Translation((0, 0, 0.0075)))
        out.append(C.finalize(C.mesh_obj("EndCap", bm, [adapter_m]), angle=50))
    # central adapter that clips into the U-hook
    M = Matrix.Translation(ctr) @ Matrix.Rotation(ang, 4, "Z")
    bm = bmesh.new()
    P.superellipsoid(bm, 0.022, 0.0105, 0.0085, e1=0.25, e2=0.3, nu=48, nv=24, matrix=M @ Matrix.Translation((0, 0, 0.0115)))
    ad = C.mesh_obj("Adapter", bm, [adapter_m])
    out.append(C.finalize(ad, angle=45))
    return out


def build():
    sb = satin_black()
    cap_m = C.mat_black_plastic("CapPA", rough=0.35, color=0.025)
    steel = C.principled("SpringSteel", (0.55, 0.55, 0.57), metallic=1.0, rough=0.3)
    spoiler = C.mat_black_plastic("SpoilerPP", rough=0.42, color=0.02)
    rubber = C.mat_rubber("WiperRubber")
    adapter = C.mat_black_plastic("AdapterPOM", rough=0.3, color=0.03, tex=False)
    objs = head(sb, cap_m, steel)
    objs.append(channel(sb))
    objs.append(spring(steel))
    a, hook_c = arm(sb)
    objs += a
    # the blade hangs in the hook: it sits on the floor, the arm rests on it
    objs += blade(spoiler, rubber, adapter, hook_c)
    C.transform_all(objs, Matrix.Rotation(math.radians(66), 4, "Z") @ Matrix.Translation((-0.25, 0, 0)))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("braccio-tergi", objs, "braccio-tergi.py",
            "windscreen wiper arm with blade (generic small hatchback): black arm with pivot head, nut cap, "
            "channel and tension spring, U-hook, flat beam wiper blade with spoiler",
            az=8, el=34, lens=85, fill=0.92, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
