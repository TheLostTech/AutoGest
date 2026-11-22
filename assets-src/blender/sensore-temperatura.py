"""Coolant temperature sensor (sensore temperatura acqua) as removed from a small car:
turned brass body with a slim probe tip, cut V-thread, relief groove, copper sealing
washer and a chamfered 19 mm hex, rolled brass crimp over the moulded plastic head,
and the integrated two-pin connector shroud with its locking ramp and tinned blade
terminals inside."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C

Q = bool(os.environ.get("QUICK"))

# units: 1 = 1 cm. Sensor axis = local Z, probe toward -Z.
RMAJ, RMIN, PITCH = 0.60, 0.51, 0.15
ZT0, ZT1 = -1.55, -0.42           # threaded length
AF = 0.95                         # hex across-flats / 2


# ----------------------------------------------------------------- helpers
def rbox(name, mat, sx, sy, sz, center=(0, 0, 0), bevel=0.01, seg=2):
    bm = bmesh.new()
    C.box_bm(bm, sx, sy, sz, center=center)
    ob = C.mesh_obj(name, bm, [mat])
    if bevel:
        C.add_bevel(ob, bevel, segments=seg, angle=30)
    return ob


def mat_brass(name="Brass", tarnish=0.5):
    m = C.principled(name, (0.60, 0.48, 0.28), metallic=1.0, rough=0.34)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    co = C._coord(nt)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Max"].default_value = tarnish
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mc = nt.nodes.new("ShaderNodeMix")
    mc.data_type = "RGBA"
    nt.links.new(mr.outputs["Result"], mc.inputs["Factor"])
    mc.inputs["A"].default_value = (0.60, 0.48, 0.28, 1)
    mc.inputs["B"].default_value = (0.34, 0.25, 0.14, 1)
    nt.links.new(mc.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.30
    rr.inputs["To Max"].default_value = 0.50
    nt.links.new(mr.outputs["Result"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    C.add_radial_aniso(m, 0.5, "Z", rings_scale=0.0)
    g = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(co, g.inputs["Vector"])
    g.inputs["Scale"].default_value = 60.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(g.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_head(name="HeadPBT"):
    m = C.principled(name, (0.030, 0.050, 0.090), rough=0.42)
    C.add_noise_bump(m, scale=90, strength=0.06, distance=0.003, rough_var=0.06)
    return m


# ----------------------------------------------------------------- body
def thread_mod(r, z, t):
    if abs(r - RMAJ) > 1e-6:
        return r
    ph = (z / PITCH - t / math.tau) % 1.0
    tri = abs(2 * ph - 1)                       # 0 at crest centre .. 1 at root
    rr = RMIN + (RMAJ - RMIN) * min(1.0, 1.25 * (1 - tri))
    # chamfer at the start of the thread, run-out at the top
    rr = min(rr, RMIN + 0.02 + (z - ZT0) * 1.0)
    return rr


def hex_mod(r, z, t):
    if r < 0.9:
        return r
    a = (t % (math.pi / 3)) - math.pi / 6
    return min(r, AF / math.cos(a))


def body(brass, probe_m, copper):
    out = []
    # probe tip
    P = [(0.0, -2.45, 1), (0.12, -2.44, 1), (0.22, -2.40, 1), (0.27, -2.32, 1), (0.29, -2.20, 1), (0.29, -1.72, 1),
         (0.34, -1.66, 0), (0.44, -1.62, 0), (RMIN, ZT0 + 0.02, 0)]
    n = 90
    for i in range(n + 1):
        P.append((RMAJ, ZT0 + 0.03 + (ZT1 - ZT0 - 0.05) * i / n, 0))
    P += [(RMIN - 0.03, ZT1 + 0.01, 0), (RMIN - 0.05, -0.30, 0), (0.70, -0.26, 0)]
    # hex with chamfered corners
    P += [(0.90, -0.22, 0), (1.02, -0.16, 0), (1.10, -0.10, 0), (1.10, 0.48, 0), (1.02, 0.56, 0), (0.90, 0.62, 0),
          (0.84, 0.62, 0), (0.84, 0.66, 0)]
    # rolled crimp lip over the plastic head
    P += [(0.86, 0.70, 0), (0.86, 0.80, 0), (0.80, 0.86, 0), (0.72, 0.87, 0), (0.0, 0.87, 0)]
    mods = lambda r, z, t: hex_mod(r, z, t) if r >= 0.9 else thread_mod(r, z, t)
    ob = C.lathe("Body", P, [brass, probe_m], steps=192, mod=mods)
    out.append(C.finalize(ob, angle=38))
    # copper sealing washer
    P = [(RMAJ + 0.02, -0.40, 0), (1.00, -0.40, 0), (1.03, -0.37, 0), (1.03, -0.27, 0), (1.00, -0.24, 0), (RMAJ + 0.02, -0.24, 0)]
    out.append(C.finalize(C.lathe("Washer", P, [copper], steps=96), angle=40))
    return out


def head(plast, pin):
    out = []
    P = [(0.0, 0.70, 0), (0.80, 0.70, 0), (0.80, 1.05, 0), (0.86, 1.10, 0), (0.86, 1.30, 0), (0.80, 1.36, 0),
         (0.66, 1.48, 0), (0.0, 1.48, 0)]
    hd = C.lathe("Head", P, [plast], steps=96)
    C.add_bevel(hd, 0.02, segments=2, angle=30)
    out.append(C.finalize(hd, angle=35))
    # connector shroud (open toward +Z) with two blades
    sh = rbox("Shroud", plast, 1.22, 0.78, 1.25, center=(0, 0, 1.40 + 0.62), bevel=0.0)
    cb = bmesh.new()
    C.box_bm(cb, 1.04, 0.60, 1.20, center=(0, 0, 1.40 + 0.62 + 0.25))
    cut = C.mesh_obj("ShroudCut", cb, [plast])
    bo = C.add_boolean(sh, cut)
    bo.use_self = True
    C.add_bevel(sh, 0.03, segments=2, angle=30)
    out.append(C.finalize(sh, angle=35, remove=[cut]))
    # locking ramp and guide ribs on one long side, gusset ribs to the round head
    bm = bmesh.new()
    C.box_bm(bm, 0.36, 0.10, 0.34, center=(0, -0.43, 2.40))
    C.box_bm(bm, 0.36, 0.06, 0.12, center=(0, -0.47, 2.52))
    for sx in (-1, 1):
        C.box_bm(bm, 0.08, 0.10, 0.9, center=(sx * 0.34, -0.42, 2.10))
        C.box_bm(bm, 0.09, 0.36, 0.34, center=(sx * 0.66, 0.0, 1.55))
    rb = C.mesh_obj("Ribs", bm, [plast])
    C.add_bevel(rb, 0.02, segments=2, angle=30)
    out.append(C.finalize(rb, angle=35))
    bm = bmesh.new()
    for sx in (-1, 1):
        C.box_bm(bm, 0.24, 0.05, 0.70, center=(sx * 0.24, 0.0, 2.05))
    pn = C.mesh_obj("Blades", bm, [pin])
    C.add_bevel(pn, 0.012, segments=1, angle=30)
    out.append(C.finalize(pn, angle=35))
    return out


def build():
    brass = mat_brass("Brass", tarnish=0.35)
    probe_m = mat_brass("BrassProbe", tarnish=0.8)
    copper = C.principled("Copper", (0.80, 0.42, 0.28), metallic=1.0, rough=0.32)
    C.add_noise_bump(copper, scale=80, strength=0.06, distance=0.002, rough_var=0.06)
    plast = mat_head()
    pin = C.principled("TinPin", (0.80, 0.78, 0.72), metallic=1.0, rough=0.22)
    objs = body(brass, probe_m, copper) + head(plast, pin)
    # lay it down diagonally: axis tilted toward the camera-left, connector up-right
    M = Matrix.Rotation(math.radians(-38), 4, "Z") @ Matrix.Rotation(math.radians(-62), 4, "Y")
    C.transform_all(objs, M)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    C.shoot("sensore-temperatura", objs, "sensore-temperatura.py",
            "coolant temperature sensor: brass threaded body with hex and copper washer, plastic head with two-pin connector",
            az=30, el=24, lens=70, fill=0.84,
            res=(512, 512) if Q else (1024, 1024), samples=32 if Q else 128)
