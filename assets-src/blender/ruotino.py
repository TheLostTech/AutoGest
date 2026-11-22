"""Space-saver spare wheel (ruotino di scorta), T125/80 R15 type: narrow pressed-steel
wheel painted in the usual warning yellow, with a thin, lightly treaded temporary
tyre. Reuses the steel-wheel builder from cerchio-ferro.py and the tyre builder from
pneumatico.py with narrow parameters."""
import sys, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy, bmesh, math
from mathutils import Matrix, Vector
import common as C


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CF = load("cerchio-ferro")
PN = load("pneumatico")


def build():
    paint = CF.mat_wheel_paint("SpareYellow", C.srgb("#C99A1E"), metallic=0.0)
    wheel = CF.wheel(paint, R=1.905, s=0.70, n_vents=6, vent=(0.17, 0.24))
    tread, side, liner = PN.mats()
    tyre = PN.tyre(tread, side, liner, RB=1.905, RO=2.90, HW=0.62, TW=0.46, BW=0.50,
                   pitches=60, steps=1200, depth=0.05)
    objs = wheel + [tyre]
    C.transform_all(objs, Matrix.Rotation(math.radians(90), 4, "X"))
    lowest = min((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)
    C.transform_all(objs, Matrix.Translation((0, 0, -lowest)))
    return objs


if __name__ == "__main__":
    q = bool(os.environ.get("QUICK"))
    C.clear()
    objs = build()
    C.shoot("ruotino", objs, "ruotino.py",
            "space-saver spare wheel: narrow yellow-painted steel wheel with thin temporary tyre",
            az=34, el=16, lens=70, fill=0.84,
            res=(512, 512) if q else (1024, 1024), samples=32 if q else 128)
