"""Steering column switch assembly (devioluci / devioguida): black plastic carrier with a
round clock-spring cassette in the centre (rotor with yellow squib connector and black horn
tab, bore for the column), clamp collar with screw behind, two switch modules carrying the
stalks (left: lights / indicators with a ribbed rotary ring and end cap; right: wipers with
a rotary ring and push-button end), and wiring connectors underneath the modules.

Built facing +Z (driver side), X right, Y up; then tipped back toward the camera.
Units ~ decimetres (width across the stalks ~55 cm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C


def rrect(w, h, r, n=6):
    """rounded rectangle outline (x, y) ccw."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism(name, outline, z0, z1, mat, M=Matrix(), bevel=0.012):
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in outline]
    n = len(outline)
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    C.fix_normals(bm)
    ob = C.mesh_obj(name, bm, [mat])
    ob.matrix_world = M
    if bevel:
        C.add_bevel(ob, bevel, segments=2, angle=30)
    return C.finalize(ob, angle=35)


def cassette(black, rotor_m, yellow, conn_black):
    out = []
    P = [(0.25, -0.02, 0), (0.70, -0.02, 0), (0.73, 0.0, 0), (0.74, 0.04, 0), (0.74, 0.22, 0),
         (0.72, 0.26, 0), (0.60, 0.27, 0), (0.58, 0.29, 0), (0.30, 0.29, 0), (0.27, 0.27, 0), (0.25, 0.20, 0)]
    ob = C.lathe("Cassette", P, [black], steps=160)
    C.add_bevel(ob, 0.006, segments=2, angle=35)
    out.append(C.finalize(ob, angle=35))
    # rotor ring with drive pin and connector tower
    P = [(0.24, 0.27, 0), (0.56, 0.27, 0), (0.565, 0.31, 0), (0.55, 0.33, 0), (0.26, 0.33, 0), (0.24, 0.31, 0)]
    ob = C.lathe("Rotor", P, [rotor_m], steps=160)
    out.append(C.finalize(ob, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.24, 0.12, 0.12, center=(0.0, 0.42, 0.38))
    tw = C.mesh_obj("ConnTower", bm, [rotor_m])
    C.add_bevel(tw, 0.015, segments=2, angle=30)
    out.append(C.finalize(tw, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.09, 0.10, center=(-0.05, 0.42, 0.48))
    yc = C.mesh_obj("SquibConn", bm, [yellow])
    C.add_bevel(yc, 0.012, segments=2, angle=30)
    out.append(C.finalize(yc, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.08, 0.07, 0.10, center=(0.10, 0.42, 0.47))
    C.box_bm(bm, 0.10, 0.10, 0.06, center=(-0.40, -0.22, 0.36))
    hc = C.mesh_obj("HornTab", bm, [conn_black])
    C.add_bevel(hc, 0.01, segments=2, angle=30)
    out.append(C.finalize(hc, angle=35))
    # drive pin for the steering wheel
    bm = bmesh.new()
    C.cyl_bm(bm, 0.035, 0.33, 0.42, seg=20, matrix=Matrix.Translation((0.34, -0.26, 0)))
    pin = C.mesh_obj("DrivePin", bm, [rotor_m])
    out.append(C.finalize(pin, angle=40))
    return out


def carrier(black, zinc):
    out = []
    # rear carrier: a wide rounded plate joining the two modules behind the cassette
    out.append(prism("Carrier", rrect(2.05, 0.78, 0.18), -0.34, -0.02, black, Matrix.Translation((0, -0.05, 0))))
    # clamp collar behind
    P = [(0.24, -0.70, 0), (0.36, -0.70, 0), (0.38, -0.68, 0), (0.38, -0.34, 0), (0.24, -0.34, 0)]
    ob = C.lathe("Collar", P, [black], steps=96)
    out.append(C.finalize(ob, angle=35))
    bm = bmesh.new()
    C.box_bm(bm, 0.16, 0.20, 0.22, center=(0, -0.44, -0.55))
    lug = C.mesh_obj("ClampLug", bm, [black])
    C.add_bevel(lug, 0.02, segments=2, angle=30)
    out.append(C.finalize(lug, angle=35))
    bm = bmesh.new()
    M = Matrix.Translation((0.09, -0.44, -0.55)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    C.cyl_bm(bm, 0.05, 0.0, 0.06, seg=6, matrix=M)
    C.cyl_bm(bm, 0.025, -0.2, 0.0, seg=16, matrix=M)
    sc = C.mesh_obj("ClampScrew", bm, [zinc])
    C.add_bevel(sc, 0.006, segments=1, angle=30)
    out.append(C.finalize(sc, angle=35))
    return out


def module(side, black, conns):
    """switch module at x = side*0.95 carrying a stalk."""
    out = []
    s = side
    x = s * 0.98
    out.append(prism("Module", rrect(0.62, 0.66, 0.12), -0.40, 0.08, black, Matrix.Translation((x, -0.02, 0))))
    # stalk pivot dome
    P = [(0.0, 0.0, 0), (0.19, 0.0, 0), (0.18, 0.06, 0), (0.14, 0.11, 0), (0.0, 0.13, 0)]
    dome = C.lathe("PivotDome", P, [black], steps=64)
    dome.matrix_world = Matrix.Translation((s * 1.26, 0.0, -0.12)) @ Matrix.Rotation(math.radians(90 * s), 4, "Y")
    out.append(C.finalize(dome, angle=35))
    # connectors under the module, opening downward
    for k, (dx, w, mat) in enumerate(((-0.12, 0.26, conns[0]), (0.15, 0.18, conns[1]))):
        bm = bmesh.new()
        C.box_bm(bm, w, 0.16, 0.20, center=(x + s * dx, -0.42, -0.18))
        C.box_bm(bm, 0.06, 0.04, 0.10, center=(x + s * dx, -0.42, -0.06))   # latch
        cn = C.mesh_obj("Conn", bm, [mat])
        C.add_bevel(cn, 0.012, segments=2, angle=30)
        out.append(C.finalize(cn, angle=35))
    return out


def stalk(side, soft, ring_m, cap_m, lights=True):
    out = []
    s = side
    # quadratic path from the pivot outward, a little toward the driver and down
    A = Vector((s * 1.30, 0.0, -0.10))
    B = Vector((s * 1.85, -0.03, 0.12))
    Cc = Vector((s * 2.40, -0.12, 0.48))
    def path(u):
        return A * (1 - u) ** 2 + B * 2 * u * (1 - u) + Cc * u * u
    def tang(u):
        return ((B - A) * 2 * (1 - u) + (Cc - B) * 2 * u).normalized()
    n = 40
    frames = []
    ref = Vector((0, 1, 0))
    for i in range(n + 1):
        u = i / n * 0.70
        P = path(u)
        T = tang(u)
        U = ref.cross(T).normalized()
        V = T.cross(U).normalized()
        r = 0.15 - 0.045 * (u / 0.70)
        sec = [(r * math.cos(math.tau * j / 28), r * 0.80 * math.sin(math.tau * j / 28)) for j in range(28)]
        frames.append((P, U, V, sec))
    bm = bmesh.new()
    C.sweep(bm, frames)
    C.fix_normals(bm)
    st = C.mesh_obj("Stalk", bm, [soft])
    for p in st.data.polygons:
        p.use_smooth = True
    out.append(st)
    # end section: along the final tangent, lathe parts
    u0 = 0.70
    P0, T0 = path(u0), tang(u0)
    q = Vector((0, 0, 1)).rotation_difference(T0)
    M = Matrix.Translation(P0) @ q.to_matrix().to_4x4()
    if lights:
        prof = [(0.0, -0.02, 0), (0.078, -0.02, 0), (0.078, 0.0, 0), (0.092, 0.01, 0), (0.092, 0.24, 0),
                (0.078, 0.25, 0), (0.0, 0.25, 0)]
        def ridges(r, z, t):
            if abs(r - 0.092) > 1e-6 or not (0.02 < z < 0.23):
                return r
            return r + 0.008 * (max(-1.0, min(1.0, math.cos(40 * t) * 3)) * 0.5 + 0.5)
        ring = C.lathe("RotaryRing", prof, [ring_m], steps=320, mod=ridges)
        ring.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(ring, angle=40))
        cap = C.lathe("EndCap", [(0.0, 0.25, 0), (0.085, 0.25, 0), (0.086, 0.36, 0), (0.07, 0.40, 0),
                                  (0.035, 0.42, 0), (0.0, 0.42, 0)], [soft], steps=64)
        cap.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(cap, angle=40))
        # thin grey band separating the ring from the cap
        band = C.lathe("Band", [(0.0, 0.245, 0), (0.088, 0.245, 0), (0.088, 0.262, 0), (0.0, 0.262, 0)], [cap_m], steps=64)
        band.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(band, angle=40))
    else:
        prof = [(0.0, -0.02, 0), (0.078, -0.02, 0), (0.078, 0.0, 0), (0.090, 0.01, 0), (0.090, 0.16, 0),
                (0.078, 0.17, 0), (0.0, 0.17, 0)]
        def ridges(r, z, t):
            if abs(r - 0.090) > 1e-6 or not (0.02 < z < 0.15):
                return r
            return r + 0.008 * (max(-1.0, min(1.0, math.cos(32 * t) * 3)) * 0.5 + 0.5)
        ring = C.lathe("WiperRing", prof, [ring_m], steps=256, mod=ridges)
        ring.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(ring, angle=40))
        body = C.lathe("WiperEnd", [(0.0, 0.17, 0), (0.082, 0.17, 0), (0.084, 0.33, 0), (0.07, 0.36, 0), (0.0, 0.36, 0)], [soft], steps=64)
        body.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(body, angle=40))
        btn = C.lathe("WasherButton", [(0.0, 0.34, 0), (0.05, 0.34, 0), (0.052, 0.38, 0), (0.04, 0.395, 0), (0.0, 0.40, 0)], [cap_m], steps=48)
        btn.matrix_world = M @ Matrix.Diagonal((1.25, 1.25, 1.1, 1))
        out.append(C.finalize(btn, angle=40))
    return out


def build():
    black = C.mat_black_plastic("PA6", rough=0.42, color=0.04)
    soft = C.mat_black_plastic("SoftTouch", rough=0.5, color=0.032)
    rotor_m = C.mat_black_plastic("Rotor", rough=0.36, color=0.05)
    ring_m = C.mat_black_plastic("RingABS", rough=0.38, color=0.045)
    cap_m = C.principled("GreyCap", (0.12, 0.12, 0.125), rough=0.4)
    yellow = C.principled("SquibYellow", C.srgb("#E2B21C"), rough=0.45)
    conn_black = C.mat_black_plastic("ConnBlack", rough=0.42, color=0.02)
    conn_white = C.principled("ConnNatural", (0.62, 0.60, 0.55), rough=0.5)
    C.add_noise_bump(conn_white, scale=900, strength=0.04, distance=0.0004)
    conn_grey = C.principled("ConnGrey", (0.18, 0.19, 0.20), rough=0.45)
    zinc = C.principled("Zinc", (0.66, 0.67, 0.69), metallic=1.0, rough=0.24)

    objs = cassette(black, rotor_m, yellow, conn_black) + carrier(black, zinc)
    objs += module(-1, black, (conn_black, conn_white)) + module(+1, black, (conn_grey, conn_black))
    objs += stalk(-1, soft, ring_m, cap_m, lights=True)
    objs += stalk(+1, soft, ring_m, cap_m, lights=False)
    # blank part-number sticker on the left module (no readable text)
    lab = C.mat_label(C.label_image("DevioLabel", seed=11, lines=3), rough=0.4)
    objs.append(C.label_plane("Label", lab, 0.40, 0.22,
                              Matrix.Translation((-0.98, 0.0, 0.082)) @ Matrix.Rotation(math.radians(-90), 4, "X")))
    C.transform_all(objs, Matrix.Rotation(math.radians(-30), 4, "Z") @ Matrix.Rotation(math.radians(55), 4, "X"))
    return objs


if __name__ == "__main__":
    C.clear()
    objs = build()
    S = int(os.environ.get("SAMPLES", "128"))
    R = int(os.environ.get("RES", "1024") or 1024)
    C.shoot("devioluci", objs, "devioluci.py",
            "steering column switch assembly: black plastic clock-spring cassette with connectors, "
            "lights stalk with rotary ring and wiper stalk, wiring connectors",
            az=12, el=30, lens=70, fill=0.88, samples=S, res=(R, R))
