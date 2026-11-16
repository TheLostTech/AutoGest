"""Brand object: closed OEM spare-parts carton, 2:1:1, off-white with print-blue end band."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix
import common as C

BLUE = C.srgb("#1240A8")
L, D, H = 2.0, 1.0, 1.0


def carton_material():
    m = C.principled("Carton", (0.86, 0.86, 0.845), rough=0.48)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    C._set(b, "Specular IOR Level", 0.3)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(C._coord(nt, "Object"), sep.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.40
    nt.links.new(sep.outputs["X"], gt.inputs[0])
    # thin accent stripe
    g2 = nt.nodes.new("ShaderNodeMath"); g2.operation = "GREATER_THAN"; g2.inputs[1].default_value = 0.27
    l2 = nt.nodes.new("ShaderNodeMath"); l2.operation = "LESS_THAN"; l2.inputs[1].default_value = 0.315
    nt.links.new(sep.outputs["X"], g2.inputs[0]); nt.links.new(sep.outputs["X"], l2.inputs[0])
    st = nt.nodes.new("ShaderNodeMath"); st.operation = "MULTIPLY"
    nt.links.new(g2.outputs[0], st.inputs[0]); nt.links.new(l2.outputs[0], st.inputs[1])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(gt.outputs[0], mx.inputs[0]); nt.links.new(st.outputs[0], mx.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.86, 0.86, 0.845, 1)
    # BLUE is #1240A8 in linear; darkened so the *lit* front face lands near the brand value
    mix.inputs["B"].default_value = (BLUE[0] * 0.55, BLUE[1] * 0.58, BLUE[2] * 0.56, 1)
    nt.links.new(mx.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    # board texture
    C.add_noise_bump(m, scale=260, strength=0.05, distance=0.0008)
    return m


def build():
    bm = bmesh.new()
    C.box_bm(bm, L, D, H, center=(0, 0, H / 2))
    # subdivide a little so the bevel/shading stays clean
    box = C.mesh_obj("Carton", bm, [carton_material()])
    C.add_bevel(box, 0.014, segments=3, angle=40)
    box = C.finalize(box, angle=50)
    # tuck-end flaps: thin proud panels on both ends give a fine shadow line
    flaps = []
    for sx in (-1, 1):
        bm = bmesh.new()
        C.box_bm(bm, 0.006, D - 0.03, H - 0.03, center=(sx * (L / 2 + 0.002), 0, H / 2))
        fl = C.mesh_obj("Flap", bm, [box.data.materials[0]])
        C.add_bevel(fl, 0.0025, segments=2, angle=40)
        flaps.append(C.finalize(fl, angle=50))
    im = C.label_image("CartonLabel", 1024, 520, seed=7)
    lm = C.mat_label(im)
    lw, lh = 0.98, 0.50
    M = Matrix.Translation((-0.40, -D / 2 - 0.0012, 0.52))
    lab = C.label_plane("Label", lm, lw, lh, M)
    return [box, lab] + flaps


if __name__ == "__main__":
    C.clear()
    objs = build()
    desc = "closed OEM spare-parts cardboard box, off-white with #1240A8 print-blue end band and blank white label"
    C.shoot("scatola", objs, "scatola.py", desc, az=32, el=21, lens=70, fill=0.84)
    if "--wide" in sys.argv or os.environ.get("WIDE", "1") == "1":
        for o in list(bpy.data.objects):
            if o.type in ("CAMERA", "LIGHT") or o.name == "ShadowCatcher":
                bpy.data.objects.remove(o, do_unlink=True)
        C.shoot("scatola", objs, "scatola.py", desc + " (wide framing, negative space right)",
                az=32, el=21, lens=70, res=(1600, 900), center=(0.34, 0.5), fill_w=0.52, fill_h=0.66,
                extra_name="scatola-wide")
