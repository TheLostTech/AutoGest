"""Worm-drive hose clamp (fascetta stringitubo), generic catalogue image for the whole
family: one stainless steel worm-drive clamp lying flat, perforated band (slanted slots
the worm engages), U-shaped housing crimped onto the band end, hex/slotted worm screw
with a helical thread, free band end sticking out past the housing."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import minuteria as M

R = 1.75        # inner band radius
BW = 0.9        # band width
BT = 0.06       # band thickness
GAP = 0.075     # radial step of the overlapping layer
TH0 = -0.30     # fixed band end (under the housing)
TH1 = math.tau + 0.95   # free end
SLANT = math.radians(14)
SL_P = 0.24     # slot pitch along the band
SL_L = 0.10     # slot length (along band)
SL_W = 0.25     # slot half width (across band)
ZM = BW / 2


def r_of(th):
    k = C.smoothstep(math.tau - 1.3, math.tau - 0.45, th)
    tail = C.smoothstep(math.tau + 0.45, TH1, th)
    return R + GAP * k + 0.10 * tail * tail


def band(steel):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    ds = 0.02
    s_tot = (TH1 - TH0) * R
    ns = int(s_tot / ds)
    nw = 30
    tans = math.tan(SLANT)
    rows = []
    for i in range(ns + 1):
        row = []
        for j in range(nw + 1):
            w = -BW / 2 + BW * j / nw
            sp = i * ds + w * tans          # sheared so slot edges follow the grid
            th = TH0 + sp / R
            rr = r_of(th)
            row.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), ZM + w)))
        rows.append(row)
    slot_cols = int(round(SL_P / ds))
    slot_len = int(round(SL_L / ds))
    for i in range(ns):
        for j in range(nw):
            wc = -BW / 2 + BW * (j + 0.5) / nw
            s_c = (i + 0.5) * ds
            in_slot = (abs(wc) < SL_W and s_c > 1.2 and s_c < s_tot - 0.25
                       and (i % slot_cols) < slot_len)
            if in_slot:
                continue
            f = bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uv].uv = (a * ds, b / nw)
    bm.normal_update()
    for f in bm.faces:
        f.normal_update()
    # outward normals
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, c.y, 0))) < 0:
            f.normal_flip()
    ob = C.mesh_obj("Band", bm, [steel])
    so = ob.modifiers.new("Solid", "SOLIDIFY")
    so.thickness = BT
    so.offset = 1.0
    so.use_even_offset = True
    C.add_bevel(ob, 0.008, segments=2, angle=50)
    return C.finalize(ob, angle=45)


# housing: inverted U sheet around the screw axis, flanges on the band
HX = R + GAP + BT + 0.005     # flange underside (on the outer layer)
SA = HX + 0.20 - 0.03         # screw axis radius (x): worm crests dip into the slots
HL = 1.25                     # housing length along the tangent (y)
SR = 0.20                     # screw major radius


def housing(steel):
    bm = bmesh.new()
    ht = 0.055
    ro = SR + 0.10              # outer radius of the U arch
    sec = []
    # outline of the U section in (u=x offset from axis, v=z offset from band middle)
    n = 16
    outer, inner = [], []
    for k in range(n + 1):
        a = math.pi * k / n            # 0..pi over the top (+x side)
        outer.append((ro * math.sin(a), ro * math.cos(a)))
        inner.append(((ro - ht) * math.sin(a), (ro - ht) * math.cos(a)))
    # flanges: extend down to the band at both sides (+-z) and out along the band width
    fl = BW / 2 + 0.06
    base = HX - SA + ht
    sec = [(base, fl), (base, ro), (0.0, ro)] + outer[1:-1] + [(0.0, -ro), (base, -ro), (base, -fl),
                                                              (base - ht, -fl), (base - ht, -(ro - ht)),
                                                              (0.0, -(ro - ht))]
    sec += inner[-2:0:-1] + [(0.0, ro - ht), (base - ht, ro - ht), (base - ht, fl)]
    frames = []
    ny = 6
    for i in range(ny + 1):
        y = -HL / 2 + HL * i / ny
        frames.append((Vector((SA, y, ZM)), Vector((1, 0, 0)), Vector((0, 0, 1)), sec))
    C.sweep(bm, frames, mat=0)
    C.fix_normals(bm)
    ob = C.mesh_obj("Housing", bm, [steel])
    C.add_bevel(ob, 0.012, segments=2, angle=40)
    return [C.finalize(ob, angle=40)]


def screw(steel):
    P = 0.11
    yl = HL / 2 + 0.25
    # threaded worm along local Z, then laid along Y
    f = M.ext_thread(SR, P, 0.0, 2 * yl - 0.1, runout0=0.0, tip_cham=(2 * yl - 0.1, SR - 0.06))
    prof = [(0.0, -0.01, 0), (SR - 0.02, -0.01, 0)]
    prof += M.thread_samples(0.0, 2 * yl - 0.1, P, per_pitch=16)
    prof += [(SR - 0.07, 2 * yl - 0.097, 0), (0.0, 2 * yl - 0.095, 0)]
    sh = M.revolve("Worm", prof, [steel], steps=128, fn=lambda tag, rr, z, t: f(rr, z, t))
    sh = C.finalize(sh, angle=80)
    # hex head with washer collar and screwdriver slot
    AF = 0.70
    a = AF / 2

    def fn(tag, r, z, t):
        rr = M.hex_r(t, AF, corner=0.97)
        return min(rr, a * 0.94 + (z + 0.42) * 1.732)
    hp = [(0.0, 0.0, 0), (0.37, 0.0, 0), (0.38, -0.02, 0), (0.37, -0.05, 0), (a * 1.0, -0.06, 0)]
    zs = [-0.06 - 0.36 * i / 20 for i in range(0, 20)]
    hp += [(a * 1.3, z, 0, "hex") for z in zs]
    hp += [(a * 0.9, -0.42, 0), (0.0, -0.42, 0)]
    hd = M.revolve("WormHead", hp, [steel], steps=360, fn=fn)
    bm = bmesh.new()
    C.box_bm(bm, 1.0, 0.09, 0.40, center=(0, 0, -0.42))
    cut = C.mesh_obj("Slot", bm, [steel])
    C.add_boolean(hd, cut)
    C.add_bevel(hd, 0.006, segments=2, angle=45)
    hd = C.finalize(hd, angle=50, remove=[cut])
    parts = [sh, hd]
    Mx = (Matrix.Translation((SA, -yl + 0.05, ZM)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
          @ Matrix.Rotation(math.radians(20), 4, "Z"))
    for o in parts:
        o.matrix_world = Mx @ o.matrix_world
    return parts


def build():
    steel = M.mat_stainless("Stainless", rough=0.24, aniso_axis="UV")
    steel2 = M.mat_stainless("Stainless2", rough=0.28)
    objs = [band(steel)] + housing(steel2) + screw(steel2)
    M.place(objs, Matrix.Rotation(math.radians(-60), 4, "Z"))
    M.drop_to_ground(objs)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("fascetta", objs, "fascetta.py",
            "stainless steel worm-drive hose clamp with perforated band, housing and slotted hex screw",
            az=-25, el=38, lens=85, fill=0.86, **M.shoot_kw())
