"""Brake pad set (pastiglie freno), one axle set of four pads as sold: two pads standing
(one showing the friction face, one the back with the stainless anti-squeal shim and the
three-finger piston clip) and two lying flat friction-up; steel backing plates with
abutment ears in black paint with worn edges, chamfered friction blocks with a centre
slot, and on one pad the electrical wear-indicator clip with its short black wire and
small two-pin plug. Pad built in the XZ plane (x along the disc arc, z radial), friction
towards -Y. 1 unit ~ 10 cm."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C
from pinza import mat_friction
from braccio import mat_worn_black

ZC = -1.05          # disc centre (pads curve around it)
TB = 0.055          # backing plate thickness
TF = 0.10           # friction thickness


def pol(r, a):
    return Vector((r * math.sin(a), 0.0, r * math.cos(a) + ZC))


def arc(r, a0, a1, n=16):
    return [pol(r, a0 + (a1 - a0) * i / n) for i in range(n + 1)]


def prism_xz(bm, pts, y0, y1, mat=0):
    a = [bm.verts.new((p.x, y0, p.z)) for p in pts]
    b = [bm.verts.new((p.x, y1, p.z)) for p in pts]
    fs = [bm.faces.new(a), bm.faces.new(b[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        fs.append(bm.faces.new((a[j], a[i], b[i], b[j])))
    for f in fs:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=fs)


def boolean(ob, cutter):
    m = C.add_boolean(ob, cutter)
    m.use_self = True
    m.use_hole_tolerant = True
    return m


def frames_along(pts):
    out = []
    n = len(pts)
    T0 = (pts[1] - pts[0]).normalized()
    U = T0.cross(Vector((0, 0, 1)))
    if U.length < 1e-3:
        U = T0.cross(Vector((1, 0, 0)))
    U.normalize()
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        U = (U - T * U.dot(T)).normalized()
        out.append((p, U, T.cross(U)))
    return out


def tube(name, pts, r, mat, seg=14):
    sec = [(r * math.cos(math.tau * i / seg), r * math.sin(math.tau * i / seg)) for i in range(seg)]
    bm = bmesh.new()
    C.sweep(bm, [(p, U, V, sec) for (p, U, V) in frames_along(pts)])
    C.fix_normals(bm)
    return C.finalize(C.mesh_obj(name, bm, [mat]), angle=70)


def bezier(p0, p1, p2, p3, n=40):
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / n for i in range(n + 1))]


def backing_outline():
    a, e = 0.47, 0.56
    pts = arc(0.80, -a + 0.03, a - 0.03, 24)
    pts += [pol(0.815, a), pol(0.93, a), pol(0.95, e - 0.01), pol(0.975, e), pol(1.105, e), pol(1.125, e - 0.01),
            pol(1.145, a), pol(1.27, a), pol(1.30, a - 0.02)]
    pts += arc(1.315, a - 0.05, -a + 0.05, 24)
    pts += [pol(1.30, -a + 0.02), pol(1.27, -a), pol(1.145, -a), pol(1.125, -e + 0.01), pol(1.105, -e), pol(0.975, -e),
            pol(0.95, -e + 0.01), pol(0.93, -a), pol(0.815, -a)]
    return pts


def friction_outline():
    a = 0.425
    pts = arc(0.84, -a + 0.07, a - 0.07, 24)
    pts += [pol(0.91, a), pol(1.20, a)]
    pts += arc(1.275, a - 0.06, -a + 0.06, 24)
    pts += [pol(1.20, -a), pol(0.91, -a)]
    return pts


def pad(tag, paint, fric, shim, clipm, back_details=False):
    out = []
    bm = bmesh.new()
    prism_xz(bm, backing_outline(), 0.0, TB)
    bp = C.mesh_obj("Backing" + tag, bm, [paint])
    C.add_bevel(bp, 0.012, segments=2, angle=30)
    out.append(C.finalize(bp, angle=35))
    bm = bmesh.new()
    prism_xz(bm, friction_outline(), -TF, 0.002)
    fr = C.mesh_obj("Friction" + tag, bm, [fric])
    cb = bmesh.new()
    C.box_bm(cb, 0.026, 0.12, 0.7, center=(0, -TF, 0.0))          # radial centre slot
    sl = C.mesh_obj("Slot", cb, [fric])
    boolean(fr, sl)
    C.add_bevel(fr, 0.014, segments=2, angle=30)
    out.append(C.finalize(fr, angle=35, remove=[sl]))
    if back_details:
        # stainless anti-squeal shim with folded tabs
        sh = [pol(0.83, -0.43)] + arc(0.83, -0.43, 0.43, 20) + arc(1.285, 0.43, -0.43, 20)
        bm = bmesh.new()
        prism_xz(bm, sh, TB, TB + 0.008)
        s = C.mesh_obj("Shim" + tag, bm, [shim])
        C.add_bevel(s, 0.003, segments=1, angle=30)
        out.append(C.finalize(s, angle=35))
        # three-finger piston clip (spring steel) at the centre
        yb = TB + 0.008
        zc = 1.05 + ZC
        bm = bmesh.new()
        for ang in (-0.75, 0.75, math.pi):
            dr = Vector((math.sin(ang), 0, math.cos(ang)))
            U = Vector((math.cos(ang), 0, -math.sin(ang)))
            frames = []
            for i in range(17):
                t = i / 16
                P = Vector((0, yb + 0.006, zc)) + dr * (0.055 + 0.20 * t) + Vector((0, 0.13 * math.sin(min(t, 0.85) / 0.85 * 2.4) ** 1.3 if t > 0 else 0, 0))
                frames.append(P)
            fr = []
            for i, P in enumerate(frames):
                T = (frames[min(i + 1, 16)] - frames[max(i - 1, 0)]).normalized()
                V = T.cross(U).normalized()
                w = 0.032 - 0.008 * i / 16
                fr.append((P, U, V, [(-w, -0.006), (w, -0.006), (w, 0.006), (-w, 0.006)]))
            C.sweep(bm, fr)
        C.cyl_bm(bm, 0.075, 0, 0.012, seg=32, matrix=Matrix.Translation((0, yb, zc)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
        C.fix_normals(bm)
        cl = C.mesh_obj("PistonClip" + tag, bm, [clipm])
        C.add_bevel(cl, 0.003, segments=1, angle=30)
        out.append(C.finalize(cl, angle=40))
    return out


def wear_indicator(black, copper):
    """clip pushed into a notch in the top edge of the friction block, wire and 2-pin plug"""
    out = []
    p = pol(1.29, 0.0)
    bm = bmesh.new()
    C.box_bm(bm, 0.09, 0.10, 0.07, center=(p.x, -TF * 0.5, p.z + 0.0))
    C.box_bm(bm, 0.05, 0.07, 0.06, center=(p.x, -TF * 0.5, p.z + 0.06))
    ck = C.mesh_obj("WearClip", bm, [black])
    C.add_bevel(ck, 0.01, segments=2, angle=30)
    out.append(C.finalize(ck, angle=35))
    a = Vector((p.x, -TF * 0.5, p.z + 0.09))
    pts = bezier(a, a + Vector((0, 0, 0.25)), a + Vector((0.55, -0.35, 0.30)), a + Vector((0.95, -0.50, 0.10)), 50)
    out.append(tube("WearWire", pts, 0.017, black))
    # tiny plug
    e = pts[-1]
    T = (pts[-1] - pts[-2]).normalized()
    M = Matrix.Translation(e) @ T.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    C.box_bm(bm, 0.075, 0.06, 0.18, center=(0, 0, 0.09))
    C.box_bm(bm, 0.03, 0.025, 0.06, center=(0, 0.04, 0.10))
    pl = C.mesh_obj("Plug", bm, [black])
    pl.matrix_world = M
    C.add_bevel(pl, 0.008, segments=2, angle=30)
    out.append(C.finalize(pl, angle=35))
    return out


def place(objs, M):
    C.transform_all(objs, M)
    return objs


def build():
    paint = mat_worn_black("BackingPaint")
    fric = mat_friction("PadFriction")
    shim = C.principled("StainlessShim", (0.66, 0.66, 0.67), metallic=1.0, rough=0.22)
    C.add_noise_bump(shim, scale=300, strength=0.15, distance=0.0008, rough_var=0.06)
    clipm = C.principled("SpringSteel", (0.55, 0.56, 0.58), metallic=1.0, rough=0.3)
    black = C.mat_black_plastic("WirePVC", rough=0.5, color=0.025)
    objs = []
    lift = -(0.80 * math.cos(0.47) + ZC)       # standing on the ends of the inner edge
    # standing, friction towards the camera
    objs += place(pad("A", paint, fric, shim, clipm), Matrix.Translation((-0.70, 0.55, 0.0 + lift + 0.005)) @ Matrix.Rotation(math.radians(-8), 4, "Z"))
    # standing, back towards the camera (shim + piston clip)
    objs += place(pad("B", paint, fric, shim, clipm, back_details=True),
                  Matrix.Translation((0.78, 0.62, lift + 0.005)) @ Matrix.Rotation(math.radians(180 + 10), 4, "Z"))
    # lying flat, friction up (one with the wear indicator)
    Rflat = Matrix.Rotation(math.radians(-90), 4, "X")
    for k, (x, y, rz, wi) in enumerate(((-0.62, -0.75, 12, True), (0.70, -0.82, -6, False))):
        g = pad("F%d" % k, paint, fric, shim, clipm)
        if wi:
            g += wear_indicator(black, None)
        # after Rflat the backing lies at z in [-TB,0] -> lift it onto the floor, centre it
        M = Matrix.Translation((x, y, TB)) @ Matrix.Rotation(math.radians(rz), 4, "Z") @ Rflat @ Matrix.Translation((0, 0, -(1.05 + ZC)))
        objs += place(g, M)
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("pastiglie", objs, "pastiglie.py",
            "brake pad set: four pads with steel backing plates, friction blocks with slot, anti-squeal shim, piston clip, wear indicator wire",
            az=18, el=30, lens=70, fill=0.86,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
