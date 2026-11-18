"""Convierte una entrega de alta resolución (GeoTIFF del proveedor) en el JPG que se sube al lote.

Uso:
  python tools/hires_render.py entrega.tif parcela.geojson salida.jpg [--margen 40]

parcela.geojson: el polígono del lote (lo devuelve GET /admin/hires → plots[].geometry).
Recorta la parcela con un margen en metros, estira el color (percentiles 2–98) y dibuja el
borde en amarillo. Luego: POST /admin/hires/{id}/deliver con el JPG.
"""
import json, sys, argparse
import numpy as np
import rasterio
from rasterio.warp import transform_geom
from rasterio.windows import from_bounds
from PIL import Image, ImageDraw


def render(tif, geom, out, margin_m=40.0):
    with rasterio.open(tif) as src:
        g = transform_geom("EPSG:4326", src.crs, geom)
        ring = g["coordinates"][0] if g["type"] == "Polygon" else [g["coordinates"]]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        m = margin_m if src.crs.is_projected else margin_m / 111_320.0
        win = from_bounds(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m, src.transform)
        win = win.round_offsets().round_lengths()
        bands = [1, 2, 3] if src.count >= 3 else [1]
        arr = src.read(bands, window=win, boundless=True, fill_value=0).astype("float32")
        tr = src.window_transform(win)
    out_rgb = []
    for b in arr:
        v = b[b > 0]
        lo, hi = (np.percentile(v, 2), np.percentile(v, 98)) if v.size else (0, 1)
        out_rgb.append(np.clip((b - lo) / max(hi - lo, 1e-6) * 255, 0, 255))
    rgb = np.stack(out_rgb * (3 if len(out_rgb) == 1 else 1), axis=-1).astype("uint8")
    im = Image.fromarray(rgb)
    inv = ~tr
    px = [inv * (x, y) for x, y in ring]
    if len(px) >= 3:
        ImageDraw.Draw(im).line(px + [px[0]], fill=(255, 214, 0), width=max(2, im.width // 300))
    im.save(out, "JPEG", quality=90)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tif"); ap.add_argument("geojson"); ap.add_argument("out")
    ap.add_argument("--margen", type=float, default=40.0)
    a = ap.parse_args()
    gj = json.load(open(a.geojson))
    geom = gj.get("geometry") or (gj.get("features") or [{}])[0].get("geometry") or gj
    print(render(a.tif, geom, a.out, a.margen))
