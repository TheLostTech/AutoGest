"""Rigenera le miniature WebP (256 px) dei render del catalogo.

    python3 scripts/miniature-render.py

Legge public/renders/*.png e scrive public/renders/mini/<nome>.webp quando manca o è più vecchia del PNG.
"""
import os
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "renders")
OUT = os.path.join(ROOT, "mini")
os.makedirs(OUT, exist_ok=True)
n = 0
for f in sorted(os.listdir(ROOT)):
    if not f.endswith(".png"):
        continue
    src, dst = os.path.join(ROOT, f), os.path.join(OUT, f[:-4] + ".webp")
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        continue
    im = Image.open(src).convert("RGBA")
    im.thumbnail((256, 256), Image.LANCZOS)
    im.save(dst, "WEBP", quality=82, method=6)
    n += 1
print(f"{n} miniature aggiornate in {OUT}")
