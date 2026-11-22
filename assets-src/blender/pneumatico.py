"""Car tyre (pneumatico), generic image for every size (modelled ~185/65 R15): hollow
lathe section (tread, rounded shoulders, sidewalls, beads, inner liner seen through
the bore). Tread pattern is real geometry: four circumferential grooves, angled
shoulder slots, staggered slots in the intermediate ribs and fine sipes on the
centre rib, displaced on a dense lathe grid. Sidewall carries blank moulded bands,
rim-protector line and a knurled shoulder ring; no lettering. `tyre()` is reused by
ruotino.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

# 1 unit ~ 10 cm, axis Z


def smooth(pts, it=2):
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append(tuple(0.75 * x + 0.25 * y for x, y in zip(a, b)))
            out.append(tuple(0.25 * x + 0.75 * y for x, y in zip(a, b)))
        out.append(pts[-1])
        pts = out
    return pts


def section(RB=1.905, RO=3.11, HW=0.925, TW=0.72, BW=0.76, ntread=80):
    """right half (z >= 0): outer path crown -> bead toe, inner path toe -> crown.
    Returns closed loop [(r, z, mat)], mats: 0 tread, 1 sidewall, 2 liner."""
    H = RO - RB
    outer = []
    for i in range(ntread + 1):
        z = TW * i / ntread
        outer.append((RO - 0.025 * (z / TW) ** 2, z, 0))
    sh = [(RO - 0.03, TW + 0.025), (RO - 0.07, TW + 0.10), (RO - 0.15, HW - 0.035),
          (RO - 0.27, HW - 0.002), (RB + 0.62 * H, HW + 0.002), (RB + 0.45 * H, HW - 0.015),
          (RB + 0.31 * H, HW - 0.05), (RB + 0.20 * H, HW - 0.085), (RB + 0.13 * H, BW + 0.075),
          (RB + 0.10 * H, BW + 0.09), (RB + 0.075 * H, BW + 0.06), (RB + 0.04, BW + 0.012), (RB, BW)]
    sh = resample(smooth([(r, z) for r, z in sh], 2), 140)
    outer += [(r, z, 1) for r, z in sh[1:]]
    outer.append((RB - 0.012, BW - 0.08, 1))
    outer.append((RB - 0.02, BW - 0.16, 2))
    inner = [(RB + 0.05, BW - 0.13), (RB + 0.25 * H, HW - 0.12), (RB + 0.55 * H, HW - 0.09),
             (RO - 0.26, HW - 0.13), (RO - 0.19, TW - 0.02), (RO - 0.175, TW * 0.5), (RO - 0.17, 0.0)]
    inner = smooth(inner, 2)
    return outer, [(r, z, 2) for r, z in inner]


def resample(pts, n):
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out, j = [], 0
    for i in range(n + 1):
        d = L[-1] * i / n
        while j < len(L) - 2 and L[j + 1] < d:
            j += 1
        f = (d - L[j]) / ((L[j + 1] - L[j]) or 1)
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f))
    return out


def full_loop(outer, inner):
    """points carry a kind (0 tread, 1 side, 2 liner); segment material = max of its ends"""
    right = outer + inner
    mir_inner = [(r, -z, k) for (r, z, k) in inner[::-1]]
    mir_outer = [(r, -z, k) for (r, z, k) in outer[::-1]]
    loop = right + mir_inner[1:] + mir_outer[:-1]
    n = len(loop)
    return [(r, z, max(k, loop[(i + 1) % n][2])) for i, (r, z, k) in enumerate(loop)]


def tread_fn(RO, TW, pitches=72, depth=0.085, steps=1440):
    da = math.tau / steps

    def soft(x, half_w, aa):  # 1 inside a band of half width half_w, anti-aliased edges
        return 1.0 - C.smoothstep(half_w - aa, half_w + aa, abs(x))

    def mod(r, z, t):
        if r < RO - 0.06:
            return r
        az = abs(z) * 0.72 / TW          # pattern designed for a 0.72 half tread width
        sgn = 1 if z >= 0 else -1
        d = 0.0
        # circumferential grooves
        for zc, w in ((0.20, 0.050), (0.52, 0.040)):
            d = max(d, soft(az - zc, w, 0.012))
        p = t / math.tau * pitches
        if az > 0.56:      # shoulder blocks: open lateral slots, slightly curved
            ph = p + 0.55 * (az - 0.56) + 0.6 * (az - 0.56) ** 2
            f = ph - math.floor(ph) - 0.5
            g = soft(f, 0.09, da / (math.tau / pitches) * 1.2)
            d = max(d, g * C.smoothstep(0.58, 0.62, az))
        elif 0.245 < az < 0.48:   # intermediate ribs: angled slots, staggered per side
            ph = p + sgn * 0.25 - 1.6 * (az - 0.245) * sgn
            f = ph - math.floor(ph) - 0.5
            g = soft(f, 0.07, da / (math.tau / pitches) * 1.2)
            open_end = 1.0 - C.smoothstep(0.40, 0.44, az) if sgn > 0 else C.smoothstep(0.27, 0.31, az)
            d = max(d, g * max(open_end, 0.0) * 0.85)
        elif az < 0.15:    # centre rib: fine sipes
            ph = p * 2 + 0.9 * z
            f = ph - math.floor(ph) - 0.5
            d = max(d, 0.45 * soft(f, 0.05, da / (math.tau / pitches / 2) * 1.2) * (1 - C.smoothstep(0.11, 0.14, az)))
        if az > 0.70:
            d *= 1.0 - C.smoothstep(0.70, 0.82, az) * 0.5
        return r - depth * d
    return mod


def tyre(tread_m, side_m, liner_m, RB=1.905, RO=3.11, HW=0.925, TW=0.72, BW=0.76,
         pitches=72, steps=1440, depth=0.085, bands=True):
    outer, inner = section(RB, RO, HW, TW, BW)
    loop = full_loop(outer, inner)
    tmod = tread_fn(RO, TW, pitches, depth, steps)
    H = RO - RB

    def mod(r, z, t):
        r2 = tmod(r, z, t)
        if r2 != r:
            return r2
        return r
    ob = C.lathe("Tyre", loop, [tread_m, side_m, liner_m], steps=steps, mod=mod)
    # sidewall relief: push vertices along z (moulded bands, protector rib, knurl ring)
    if bands:
        me = ob.data
        for v in me.vertices:
            x, y, z = v.co
            r = math.hypot(x, y)
            if abs(z) < HW * 0.6 or r > RO - 0.10 or r < RB + 0.02:
                continue
            u = (r - RB) / H
            s = 1 if z > 0 else -1
            dz = 0.0
            dz += 0.010 * (C.smoothstep(0.44, 0.46, u) - C.smoothstep(0.70, 0.72, u))   # lettering band
            dz += 0.006 * (C.smoothstep(0.30, 0.31, u) - C.smoothstep(0.33, 0.34, u))   # thin ring
            dz += 0.006 * (C.smoothstep(0.76, 0.77, u) - C.smoothstep(0.79, 0.80, u))   # thin ring
            if 0.83 < u < 0.90:                                                         # knurled ring
                th = math.atan2(y, x)
                dz += 0.006 * (0.5 + 0.5 * math.cos(th * 360)) * C.smoothstep(0.83, 0.84, u) * (1 - C.smoothstep(0.89, 0.90, u))
            v.co.z = z + s * dz
        me.update()
    return C.finalize(ob, angle=50)


def mats():
    tread = C.principled("TreadRubber", (0.022, 0.022, 0.023), rough=0.82)
    C.add_noise_bump(tread, scale=500, strength=0.12, distance=0.001, rough_var=0.05)
    side = C.principled("SideRubber", (0.03, 0.03, 0.031), rough=0.55)
    C.add_noise_bump(side, scale=900, strength=0.05, distance=0.0004, rough_var=0.06)
    liner = C.principled("Liner", (0.045, 0.045, 0.047), rough=0.55)
    C.add_noise_bump(liner, scale=40, strength=0.1, distance=0.002)
    return tread, side, liner


def build():
    tread, side, liner = mats()
    ob = tyre(tread, side, liner)
    objs = [ob]
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("pneumatico", objs, "pneumatico.py",
            "car tyre without rim: black rubber, tread with circumferential grooves and lateral slots, sidewall with blank moulded bands",
            az=40, el=14, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
