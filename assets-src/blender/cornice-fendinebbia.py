"""Front fog light bezel (left), generic small hatchback: black grained-plastic surround
that wraps round the bumper corner, with the round 80 mm opening for the fog lamp framed
by a gloss-black stepped sleeve and a thin satin-chrome ring, a recessed blind vent with
three horizontal slats beside it, a return flange round the edge, snap hooks on the back
and a screw lug at the outer end. Face towards -Y, outer (wrap) end at +X."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
import panel as P

OUT = Vector((0, -1, 0))
RX = Matrix.Rotation(math.radians(90), 4, "X")     # Z -> -Y
RXm = Matrix.Rotation(math.radians(-90), 4, "X")   # Z -> +Y
HC = Vector((0.030, 0.000))                         # opening centre (x, z)
RO = 0.041                                          # opening radius
SL = (-0.092, -0.022, -0.026, 0.024)                # vent slot x0, x1, z0, z1
T = 0.0028


def face_y(x, z):
    u = max(x + 0.04, 0.0)
    return 1.15 * u * u - 0.12 * z


def lift3(q, dd=0.0):
    return Vector((q.x, face_y(q.x, q.y) + dd, q.y))


def outline():
    pts = P.rounded([Vector(p) for p in ((-0.112, -0.040), (0.082, -0.052), (0.116, -0.010), (0.096, 0.050),
                                          (-0.094, 0.044), (-0.118, 0.004))],
                    [0.018, 0.026, 0.022, 0.020, 0.018, 0.016], closed=True, seg=16)
    pts = P.resample(pts, 320, closed=True)
    if P.signed_area(pts) < 0:
        pts = pts[::-1]
    return pts


def bool_cut(ob, cut):
    m = C.add_boolean(ob, cut)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def face(tex):
    poly = outline()
    ob = P.fan_obj("Bezel", poly, Vector((-0.005, 0.0)), 40, lift3, [tex], OUT, power=1.2)
    P.solidify(ob, T, offset=-1)
    # opening and vent slot cutters (prisms through the shell)
    cb = bmesh.new()
    circ = [HC + Vector((RO * math.cos(math.tau * k / 96), RO * math.sin(math.tau * k / 96))) for k in range(96)]
    P.prism_bm(cb, circ, lift3, -0.02, 0.03)
    slot = P.rounded([Vector(p) for p in ((SL[0], SL[2]), (SL[1], SL[2]), (SL[1], SL[3]), (SL[0], SL[3]))], [0.008] * 4,
                     closed=True, seg=8)
    slot = P.resample(slot, 80, closed=True)
    if P.signed_area(slot) < 0:
        slot = slot[::-1]
    cut2 = bmesh.new()
    P.prism_bm(cut2, slot, lift3, -0.02, 0.03)
    c1 = C.mesh_obj("OpenCut", cb, [tex])
    c2 = C.mesh_obj("SlotCut", cut2, [tex])
    bool_cut(ob, c1)
    bool_cut(ob, c2)
    C.add_bevel(ob, 0.0006, segments=2, angle=35)
    return C.finalize(ob, angle=40, remove=[c1, c2]), slot


def flange(tex):
    fr = P.frames_on_surface(outline(), lift3, OUT, closed=True)
    return P.tube_obj("Flange", fr, P.rrect(-0.0028, 0.0010, -0.016, 0.0006, 0.0012, seg=3), [tex], closed=True, smooth_angle=50)


def slot_parts(tex, dark, slot):
    out = []
    # recessed wall round the slot and blind backing
    fr = P.frames_on_surface(slot, lift3, OUT, closed=True)
    out.append(P.tube_obj("SlotWall", fr, P.rrect(-0.0016, 0.0005, -0.012, 0.0005, 0.0006, seg=2), [tex], closed=True, smooth_angle=50))
    rows = []
    for t in (0.0, 1.0):
        z = SL[2] - 0.004 + (SL[3] - SL[2] + 0.008) * t
        rows.append([lift3(Vector((SL[0] - 0.004 + (SL[1] - SL[0] + 0.008) * k / 30, z)), 0.012) for k in range(31)])
    ob = P.grid_obj("SlotBack", rows, [dark], OUT)
    out.append(C.finalize(ob, angle=40))
    # three slats, each a thin blade tipped down towards the front
    for z in (-0.013, 0.0, 0.013):
        pts = [lift3(Vector((SL[0] + 0.001 + (SL[1] - SL[0] - 0.002) * k / 30, z)), 0.002) for k in range(31)]
        frm = P.path_frames(pts, (0, 0, 1))
        sec = [(-0.0035, -0.0012), (0.0055, -0.0008), (0.0058, 0.0007), (-0.0035, 0.0011)]   # (a = back, b = up)
        frm = [(p, (B.cross(A)).normalized() * 0 + Vector((0, 1, 0)), Vector((0, 0, 1))) for (p, A, B) in frm]
        out.append(P.tube_obj("Slat", frm, sec, [tex], smooth_angle=40, bevel=0.0004))
    return out


def opening_parts(gloss, chrome):
    out = []
    y0 = face_y(HC.x, HC.y)
    # gloss-black stepped sleeve running back from the opening (follows the face tilt roughly)
    sl = C.lathe("Sleeve", [(RO - 0.0002, -0.002, 0), (RO + 0.0032, -0.002, 0), (RO + 0.0032, 0.004, 0), (RO + 0.0016, 0.006, 0),
                            (RO + 0.0016, 0.020, 0), (RO - 0.0010, 0.020, 0), (RO - 0.0010, 0.008, 0), (RO - 0.0045, 0.006, 0),
                            (RO - 0.0045, 0.003, 0), (RO - 0.0002, 0.001, 0)], [gloss], steps=128)
    sl.matrix_world = Matrix.Translation((HC.x, y0, HC.y)) @ Matrix.Rotation(math.atan(1.15 * 2 * max(HC.x + 0.04, 0.0)), 4, "Z") \
        @ Matrix.Rotation(math.atan(0.12), 4, "X") @ RXm
    Msl = sl.matrix_world.copy()
    out.append(C.finalize(sl, angle=40))
    ring = C.lathe("ChromeRing", [(RO + 0.0032, -0.0022, 0), (RO + 0.0058, -0.0016, 0), (RO + 0.0062, 0.0004, 0), (RO + 0.0032, 0.0008, 0)],
                   [chrome], steps=128)
    ring.matrix_world = Msl
    out.append(C.finalize(ring, angle=40))
    return out


def back_fixings(raw):
    out = []
    for (x, z, up) in ((-0.07, 0.044, 1), (0.05, 0.050, 1), (-0.05, -0.042, -1), (0.06, -0.050, -1)):
        y = face_y(x, z) + 0.014
        bm = bmesh.new()
        C.box_bm(bm, 0.013, 0.0024, 0.020, center=(x, y, z + up * 0.006))
        C.box_bm(bm, 0.013, 0.0048, 0.0032, center=(x, y - 0.0030, z + up * 0.0145))
        ob = C.mesh_obj("SnapHook", bm, [raw])
        C.add_bevel(ob, 0.0005, segments=2, angle=30)
        out.append(C.finalize(ob, angle=35))
    # screw lug at the outer end
    x, z = 0.112, 0.016
    y = face_y(x, z) + 0.012
    bm = bmesh.new()
    C.box_bm(bm, 0.004, 0.030, 0.026, center=(x - 0.004, y + 0.010, z))
    ob = C.mesh_obj("Lug", bm, [raw])
    cb = bmesh.new()
    C.cyl_bm(cb, 0.0048, -0.03, 0.03, seg=24, matrix=Matrix.Translation((x - 0.004, y + 0.016, z)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    cut = C.mesh_obj("LugHole", cb, [raw])
    bool_cut(ob, cut)
    C.add_bevel(ob, 0.001, segments=2, angle=30)
    out.append(C.finalize(ob, angle=35, remove=[cut]))
    return out


def build():
    tex = P.textured_black("BezelPP", rough=0.6, v=0.022)
    raw = P.textured_black("RawPP", rough=0.58, v=0.03)
    gloss = C.principled("GlossBlack", (0.010, 0.010, 0.011), rough=0.12, Coat_Weight=0.8)
    chrome = C.principled("SatinChrome", (0.88, 0.88, 0.89), metallic=1.0, rough=0.12)
    dark = C.principled("VentBack", (0.012, 0.012, 0.013), rough=0.8)
    f, slot = face(tex)
    objs = [f, flange(tex)]
    objs += slot_parts(tex, dark, slot)
    objs += opening_parts(gloss, chrome)
    objs += back_fixings(raw)
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    r = int(os.environ.get("RES", "1024"))
    C.shoot("cornice-fendinebbia", objs, "cornice-fendinebbia.py",
            "front fog light bezel (generic small hatchback): black grained plastic surround with round fog lamp opening, "
            "gloss black sleeve and chrome ring, slatted blind vent, snap hooks on the back",
            az=-24, el=18, lens=70, fill=0.86, res=(r, r), samples=int(os.environ.get("SAMPLES", "128")))
