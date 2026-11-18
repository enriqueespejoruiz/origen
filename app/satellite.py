"""Evidencia satelital propia de Origen (fuentes abiertas, uso comercial con atribución a Copernicus).

1) Sentinel-2 L2A (ESA, 10 m): composición sin nubes de la parcela en 2020 (línea base EUDR) y en los
   últimos 12 meses; NDVI medio, cambio y % del área con caída fuerte de vegetación. Genera la imagen
   "antes / después" para el dossier. Fuente: Earth Search (AWS Open Data, COGs de Element 84).
2) Sentinel-1 RTC (ESA, radar banda C, 10 m): retrodispersión VH media en 2020 y en los últimos 4 meses.
   El radar ve a través de las nubes; una caída fuerte de VH es señal de pérdida de dosel.
   Fuente: Microsoft Planetary Computer (STAC + token público).

Nada de esto decide el veredicto por sí solo: solo puede SUBIR un "negligible" a "review" (nunca bajar),
porque el EUDR penaliza el falso negativo, no el falso positivo revisado.
"""
import datetime as _dt
import math

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1/search"
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"

S2_BASE = ("2020-06-01", "2020-12-31")          # línea base EUDR (estación seca primero)
S2_LOSS_DROP = 0.20                             # caída de NDVI por píxel que cuenta como pérdida
S2_FOREST_NDVI = 0.60                           # solo píxeles con vegetación densa en 2020
S2_FLAG_PCT = 10.0                              # % del área con pérdida que sube a "revisar"
S1_FLAG_DB = 3.0                                # caída de VH (dB) que sube a "revisar"
_CLOUD_SCL = {0, 1, 3, 8, 9, 10, 11}            # sin dato, saturado, sombra, nubes, cirros, nieve


def _ring(plot):
    """Anillo lon/lat del polígono; un punto se convierte en un cuadrado del tamaño de la parcela."""
    pts = plot.points
    if len(pts) >= 3:
        ring = [(p.lon, p.lat) for p in pts]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return ring
    p = pts[0]
    side = math.sqrt(plot.area_ha * 10000.0) if (plot.area_ha and plot.area_ha > 0) else 100.0
    h = side / 2.0
    dla = h / 111320.0
    dlo = h / (111320.0 * max(math.cos(math.radians(p.lat)), 0.01))
    return [(p.lon - dlo, p.lat - dla), (p.lon + dlo, p.lat - dla), (p.lon + dlo, p.lat + dla),
            (p.lon - dlo, p.lat + dla), (p.lon - dlo, p.lat - dla)]


def _bbox(ring, pad_m=120.0):
    lons = [x for x, _ in ring]; lats = [y for _, y in ring]
    lat0 = sum(lats) / len(lats)
    dla = pad_m / 111320.0
    dlo = pad_m / (111320.0 * max(math.cos(math.radians(lat0)), 0.01))
    return [min(lons) - dlo, min(lats) - dla, max(lons) + dlo, max(lats) + dla]


def _search(url, body, timeout=40):
    import requests
    r = requests.post(url, json=body, timeout=timeout)
    r.raise_for_status()
    return r.json().get("features", [])


def _read(href, bbox_ll, shape=None):
    """Lee la ventana del bbox (lon/lat) de un COG; devuelve (array, transform, crs)."""
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    opts = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="25",
                GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_HTTP_MULTIPLEX="YES",
                GDAL_HTTP_VERSION="2", GDAL_INGESTED_BYTES_AT_OPEN="65536", GDAL_HTTP_MAX_RETRY="2",
                GDAL_HTTP_RETRY_DELAY="1")
    # Sentinel-1 en Azure termina en «.tiff» (no «.tif»): el filtro debe aceptar ambos. Se fija aquí porque
    # el chequeo del mapa JRC dejaba «.tif» solo en el entorno del proceso y GDAL rechazaba el radar.
    opts["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif,.TIF,.tiff,.TIFF"
    with rasterio.Env(**opts), rasterio.open(href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *bbox_ll)
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        out_shape = shape or (max(int(win.height), 1), max(int(win.width), 1))
        arr = src.read(1, window=win, out_shape=out_shape, boundless=True, fill_value=0,
                       resampling=Resampling.nearest)
        tr = src.window_transform(win)
        if shape:
            tr = tr * tr.scale(win.width / shape[1], win.height / shape[0])
        return arr, tr, src.crs


def _plot_mask(ring, shape, transform, crs):
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    g = transform_geom("EPSG:4326", crs, {"type": "Polygon", "coordinates": [ring]})
    return ~geometry_mask([g], out_shape=shape, transform=transform, all_touched=True)


def _composite(items, bbox_ll, ring, max_scenes=5):
    """Mediana de las 2 escenas más limpias (sin nubes ni bruma) del mismo tile MGRS. Dict o None."""
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor
    if not items:
        return None
    tile = items[0]["properties"].get("grid:code") or items[0]["properties"].get("s2:mgrs_tile")
    seen, cands = set(), []
    for i in items:   # mismo tile y una escena por fecha (Earth Search a veces repite reprocesados)
        pr = i["properties"]
        d = pr["datetime"][:10]
        if (pr.get("grid:code") or pr.get("s2:mgrs_tile")) == tile and d not in seen:
            seen.add(d); cands.append(i)
        if len(cands) >= max_scenes:
            break
    red0, tr, crs = _read(cands[0]["assets"]["red"]["href"], bbox_ll)
    shape = red0.shape
    mask = _plot_mask(ring, shape, tr, crs)
    if not mask.any():
        return None

    def load(it):
        try:
            a, pr = it["assets"], it["properties"]
            scl = _read(a["scl"]["href"], bbox_ll, shape=shape)[0]
            red = _read(a["red"]["href"], bbox_ll, shape=shape)[0]
            clear = ~np.isin(scl, list(_CLOUD_SCL)) & (red > 0)
            if clear[mask].mean() < 0.3:
                return None
            off = 1000.0 if (not pr.get("earthsearch:boa_offset_applied", True)
                             and str(pr.get("s2:processing_baseline", "0")) >= "04.00") else 0.0
            out = {"red": red}
            for k in ("green", "blue", "nir"):
                out[k] = _read(a[k]["href"], bbox_ll, shape=shape)[0]
            for k in list(out):
                v = (out[k].astype("float32") - off) / 10000.0
                v[~clear] = np.nan
                out[k] = v
            out["date"] = pr["datetime"][:10]
            return out
        except Exception as e:
            print("s2 scene error:", repr(e)[:160])
            return None
    with ThreadPoolExecutor(5) as ex:
        scenes = [x for x in ex.map(load, cands) if x]
    if not scenes:
        return None
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        # la bruma y el humo de las quemas suben el azul: nos quedamos con las 2 escenas más limpias
        scenes.sort(key=lambda sc: float(np.nanmedian(sc["blue"][mask])) if np.isfinite(sc["blue"][mask]).any() else 9.0)
        keep = scenes[:2]
        comp = {k: np.nanmedian(np.stack([sc[k] for sc in keep]), axis=0) for k in ("red", "green", "blue", "nir")}
    r, g, b, n = (comp[k] for k in ("red", "green", "blue", "nir"))
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = (n - r) / (n + r)
    valid = mask & np.isfinite(ndvi)
    return {"ndvi": ndvi, "rgb": (r, g, b), "mask": mask, "valid": valid, "dates": [sc["date"] for sc in keep],
            "transform": tr, "crs": crs, "valid_frac": float(valid.sum() / max(mask.sum(), 1))}


def _png(base, now, ring, path):
    """Imagen 'antes / después' en color natural con el contorno de la parcela."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from rasterio.warp import transform as _tf

    both = np.concatenate([np.nan_to_num(np.dstack(c["rgb"]), nan=0.0).ravel() for c in (base, now)])
    lo, hi = np.percentile(both, 2), np.percentile(both, 98)   # mismo estiramiento: colores comparables

    def to_img(c):
        rgb = np.nan_to_num(np.dstack(c["rgb"]), nan=0.0)
        rgb = np.clip((rgb - lo) / max(hi - lo, 1e-3), 0, 1) ** 0.9
        img = Image.fromarray((rgb * 255).astype("uint8")).resize((360, int(360 * rgb.shape[0] / rgb.shape[1])),
                                                                  Image.NEAREST)
        xs, ys = _tf("EPSG:4326", c["crs"], [p[0] for p in ring], [p[1] for p in ring])
        inv = ~c["transform"]
        sx = img.width / rgb.shape[1]; sy = img.height / rgb.shape[0]
        pix = []
        for x, y in zip(xs, ys):
            col, row = inv * (x, y)
            pix.append((col * sx, row * sy))
        d = ImageDraw.Draw(img)
        d.line(pix, fill=(240, 185, 74), width=3)
        return img
    a, b = to_img(base), to_img(now)
    h = max(a.height, b.height)
    canvas = Image.new("RGB", (a.width + b.width + 12, h + 30), (255, 255, 255))
    canvas.paste(a, (0, 30)); canvas.paste(b, (a.width + 12, 30))
    d = ImageDraw.Draw(canvas)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
    except Exception:
        f = ImageFont.load_default()
    d.text((4, 8), "2020 · " + base["dates"][0], fill=(6, 16, 58), font=f)
    d.text((a.width + 16, 8), "Reciente · " + now["dates"][0], fill=(6, 16, 58), font=f)
    canvas.save(path, "JPEG", quality=85)
    return path


def sentinel2_change(plot, out_path=None, today=None):
    """Compara 2020 vs últimos 12 meses en Sentinel-2. Devuelve dict de métricas (o None si no hay datos)."""
    import numpy as np
    ring = _ring(plot)
    bbox = _bbox(ring)
    today = today or _dt.date.today()
    recent = ((today - _dt.timedelta(days=365)).isoformat(), today.isoformat())

    def items(win, newest=False):
        body = {"collections": ["sentinel-2-l2a"], "bbox": bbox,
                "datetime": f"{win[0]}T00:00:00Z/{win[1]}T23:59:59Z", "limit": 60,
                "query": {"eo:cloud_cover": {"lt": 70}}}
        fs = _search(EARTH_SEARCH, body)
        if newest:   # lo más reciente posible: las escenas despejadas más nuevas primero
            fs.sort(key=lambda f: f["properties"]["datetime"], reverse=True)
        else:
            fs.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
        return fs
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as ex:
        fb, fn = ex.submit(items, S2_BASE), ex.submit(items, recent, True)
        base_items, now_items = fb.result(), fn.result()
    if not base_items or not now_items:
        return None
    b_tile = base_items[0]["properties"].get("grid:code")   # mismo tile: comparación píxel a píxel
    now_items = [f for f in now_items if f["properties"].get("grid:code") == b_tile] or now_items
    with ThreadPoolExecutor(2) as ex:
        fb, fn = ex.submit(_composite, base_items, bbox, ring, 4), ex.submit(_composite, now_items, bbox, ring, 4)
        base, now = fb.result(), fn.result()
    if not base:
        return None
    if not now or now["ndvi"].shape != base["ndvi"].shape:
        return None
    m = base["valid"] & now["valid"]
    if m.sum() < 3:
        return None
    nb, nn = base["ndvi"][m], now["ndvi"][m]
    dense = nb >= S2_FOREST_NDVI
    loss = dense & ((nb - nn) >= S2_LOSS_DROP)
    out = {
        "source": "Sentinel-2 L2A",
        "base_dates": base["dates"], "recent_dates": now["dates"],
        "ndvi_2020": round(float(np.mean(nb)), 3), "ndvi_now": round(float(np.mean(nn)), 3),
        "delta": round(float(np.mean(nn) - np.mean(nb)), 3),
        "loss_pct": round(float(100.0 * loss.sum() / max(m.sum(), 1)), 1),
        "valid_pct": round(100.0 * float(m.sum() / max(base["mask"].sum(), 1)), 0),
    }
    if out_path:
        try:
            out["image"] = _png(base, now, ring, out_path)
        except Exception as e:
            print("s2 png error:", repr(e)[:160])
    return out


def sentinel1_change(plot, today=None):
    """Retrodispersión VH (dB) media en 2020 vs últimos 4 meses (Sentinel-1 RTC). None si no hay datos."""
    import numpy as np
    import requests
    ring = _ring(plot)
    bbox = _bbox(ring, pad_m=30.0)
    today = today or _dt.date.today()
    tok = requests.get(PC_TOKEN, timeout=20).json().get("token", "")

    def mean_vh(win, n=6):
        body = {"collections": ["sentinel-1-rtc"], "bbox": bbox,
                "datetime": f"{win[0]}T00:00:00Z/{win[1]}T23:59:59Z", "limit": 30}
        fs = _search(PC_STAC, body)

        def one(f):
            try:
                arr, tr, crs = _read(f["assets"]["vh"]["href"] + "?" + tok, bbox)
                mk = _plot_mask(ring, arr.shape, tr, crs) & (arr > 0)
                if mk.sum() < 2:
                    return None
                return float(np.mean(10 * np.log10(arr[mk]))), f["properties"]["datetime"][:10]
            except Exception as e:
                m = repr(e)
                print("s1 scene error:", (m.replace(tok, "<sas>") if tok else m)[-240:])
                return None
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as ex:
            got = [g for g in ex.map(one, fs[:n]) if g]
        return (float(np.median([g[0] for g in got])), sorted(g[1] for g in got)) if got else (None, [])
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as ex:
        a = ex.submit(mean_vh, ("2020-07-01", "2020-12-31"), 4)
        b = ex.submit(mean_vh, ((today - _dt.timedelta(days=120)).isoformat(), today.isoformat()), 4)
        v0, d0 = a.result(); v1, d1 = b.result()
    if v0 is None or v1 is None:
        return None
    return {"source": "Sentinel-1 RTC", "vh_2020_db": round(v0, 2), "vh_now_db": round(v1, 2),
            "delta_db": round(v1 - v0, 2), "base_dates": d0, "recent_dates": d1}


def assess(plot, out_path=None, radar=True):
    """Evidencia combinada + decisión de escalar. Nunca lanza excepción."""
    res = {}
    try:
        res["s2"] = sentinel2_change(plot, out_path)
    except Exception as e:
        print("s2 error:", repr(e)[:200]); res["s2"] = None
    if radar:
        try:
            res["s1"] = sentinel1_change(plot)
        except Exception as e:
            print("s1 error:", repr(e)[:200]); res["s1"] = None
    s2, s1 = res.get("s2"), res.get("s1")
    res["flag"] = bool((s2 and s2["loss_pct"] >= S2_FLAG_PCT) or (s1 and s1["delta_db"] <= -S1_FLAG_DB))
    return res


def summary(res, lang="es"):
    """Una línea legible para el detalle del hallazgo."""
    if not res:
        return ""
    parts = []
    s2, s1 = res.get("s2"), res.get("s1")
    if s2:
        parts.append((f"Sentinel-2: NDVI {s2['ndvi_2020']:.2f}→{s2['ndvi_now']:.2f}, pérdida de vegetación densa "
                      f"{s2['loss_pct']:.0f}% del área") if lang != "en" else
                     (f"Sentinel-2: NDVI {s2['ndvi_2020']:.2f}→{s2['ndvi_now']:.2f}, dense-vegetation loss "
                      f"{s2['loss_pct']:.0f}% of area"))
    if s1:
        parts.append((f"radar Sentinel-1 VH {s1['delta_db']:+.1f} dB") if lang != "en" else
                     (f"Sentinel-1 radar VH {s1['delta_db']:+.1f} dB"))
    return "; ".join(parts)
