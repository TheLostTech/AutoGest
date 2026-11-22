"""Rear brake drum (tamburo freno posteriore) as removed from a small car, shown from the
open side: cast-iron drum with axial cooling fins and a reinforcing band at the
mouth, machined inner braking surface with turning marks and a slight wear lip, closed
end with 4 wheel-bolt holes and an adjuster inspection hole, central hub boss with the
pressed-in wheel bearing (seal and inner race) (stub axle removed).
1 unit ~ 10 cm (203 mm drum)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from pinza import mat_rusty_iron

RD = 1.015     # braking surface radius
HT = 0.66      # height of the mouth (closed end at z=0)
PCD = 0.50


def drum(iron, mach):
    P = [(0.25, -0.10, 2), (0.40, -0.10, 0), (0.43, -0.07, 0), (0.43, -0.012, 0), (0.46, 0.0, 0),
         (1.08, 0.0, 0), (1.13, 0.03, 0), (1.15, 0.08, 0)]
    # body (axial cooling fins added by the lathe modifier) and reinforcing band at the mouth
    P += [(1.15, 0.12, 0), (1.15, 0.30, 0), (1.15, 0.50, 0), (1.15, 0.545, 0), (1.21, 0.575, 0), (1.235, 0.60, 0),
          (1.235, HT - 0.012, 0), (1.22, HT, 1),
          (RD + 0.035, HT, 0), (RD + 0.008, HT - 0.012, 0),
          (RD + 0.004, HT - 0.05, 1),                 # unworn lip at the mouth
          (RD, HT - 0.07, 1), (RD, 0.13, 1), (RD + 0.004, 0.11, 0),
          (RD - 0.04, 0.085, 0), (0.62, 0.085, 0), (0.50, 0.10, 0), (0.45, 0.16, 0),
          (0.42, 0.22, 0), (0.25, 0.22, 2)]
    NF = 30

    def fins(r, z, t):
        if r < 1.149 or z < 0.07 or z > 0.56:
            return r
        f = (t * NF / math.tau) % 1.0
        h = C.smoothstep(0.30, 0.40, f) * (1 - C.smoothstep(0.60, 0.70, f))
        taper = C.smoothstep(0.07, 0.13, z) * (1 - C.smoothstep(0.52, 0.56, z)) if z > 0.3 else C.smoothstep(0.0, 0.12, z)
        return r + 0.045 * h * taper
    ob = C.lathe("Drum", P, [iron, mach, mach], steps=NF * 10, mod=fins)
    cb = bmesh.new()
    for k in range(4):
        th = math.radians(45 + 90 * k)
        C.cyl_bm(cb, 0.068, -0.3, 0.2, seg=40, matrix=Matrix.Translation((PCD * math.cos(th), PCD * math.sin(th), 0)))
    th = math.radians(10)
    C.cyl_bm(cb, 0.055, -0.3, 0.2, seg=32, matrix=Matrix.Translation((0.80 * math.cos(th), 0.80 * math.sin(th), 0)))
    cut = C.mesh_obj("Holes", cb, [iron])
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    C.add_bevel(ob, 0.006, segments=2, angle=40)
    return [C.finalize(ob, angle=38, remove=[cut])]


def bearing(steel, seal, mach):
    out = []
    # rubber lip seal at the inboard end of the bore
    P = [(0.12, 0.20, 0), (0.25, 0.20, 0), (0.25, 0.235, 0), (0.24, 0.245, 0), (0.13, 0.245, 0), (0.12, 0.235, 0)]
    out.append(C.finalize(C.lathe("Seal", P, [seal], steps=96), angle=40))
    # steel seal casing ring
    P = [(0.235, 0.18, 0), (0.25, 0.18, 0), (0.25, 0.25, 0), (0.235, 0.25, 0)]
    out.append(C.finalize(C.lathe("SealCase", P, [steel], steps=96), angle=40))
    # inner race / spacer
    P = [(0.075, 0.12, 0), (0.125, 0.12, 0), (0.125, 0.27, 0), (0.115, 0.28, 0), (0.085, 0.28, 0), (0.075, 0.27, 0)]
    out.append(C.finalize(C.lathe("InnerRace", P, [mach], steps=96), angle=40))
    # castellated nut seen through the bore (stub axle removed -> just the bore)
    return out


def build():
    iron = mat_rusty_iron("DrumIron", base=0.08, rust=0.45, scale=3.5, seed=1.3)
    mach = C.mat_machined("BrakingSurface", color=0.55, rough=0.30, rings=900)
    # faint brown tint and darker bands in the worn track
    nt = mach.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = C._coord(nt)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 0.08, 1.0)      # bands along the drum axis
    nt.links.new(tc, mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 30.0
    nz.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 0.30
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.56, 0.56, 0.56, 1)
    mix.inputs["B"].default_value = (0.30, 0.24, 0.20, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    steel = C.principled("SealSteel", (0.55, 0.55, 0.56), metallic=1.0, rough=0.3)
    seal = C.mat_rubber("SealRubber")
    race = C.mat_machined("Race", color=0.62, rough=0.12, rings=300)
    objs = drum(iron, mach) + bearing(steel, seal, race)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("tamburo", objs, "tamburo.py",
            "rear brake drum: cast-iron drum with cooling ribs, machined inner braking surface, 4 bolt holes, hub bearing",
            az=28, el=44, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
