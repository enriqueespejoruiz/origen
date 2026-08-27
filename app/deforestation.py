import math
from . import config
from .models import Lot, DeforestationFinding

GFW_BASE = "https://data-api.globalforestwatch.org"
JRC_COG = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FOREST/GFC2020/LATEST/single-cog/JRC_GFC2020_V3_COG.tif"
_VERSION = None

def check_plots(lot: Lot):
    """Cruza cada parcela contra perdida de cobertura forestal posterior al ano de corte (EUDR: 2020)."""
    if config.GFW_API_KEY:
        return _gfw_check(lot)
    if config.EE_PROJECT:
        try:
            return _ee_check(lot)
        except Exception as e:
            return [DeforestationFinding(p.plot_id, "review", False, f"EE error: {e}") for p in lot.plots]
    return _stub_check(lot)

# ---------- Global Forest Watch (Hansen tree cover loss, licencia abierta CC-BY) ----------

def _resolve_version():
    # Usamos la version configurada (estable y consultable). La "latest" puede
    # estar restringida por GFW (403), por eso NO auto-saltamos a la mas nueva.
    return config.GFW_VERSION

def _plot_polygon(plot):
    """Convierte la parcela en un poligono GeoJSON. Punto -> cuadro del tamano de la parcela."""
    pts = plot.points
    if len(pts) >= 3:
        ring = [[p.lon, p.lat] for p in pts]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return {"type": "Polygon", "coordinates": [ring]}
    p = pts[0]
    side_m = math.sqrt(plot.area_ha * 10000.0) if (plot.area_ha and plot.area_ha > 0) else 100.0
    half = side_m / 2.0
    dlat = half / 111320.0
    dlon = half / (111320.0 * max(math.cos(math.radians(p.lat)), 0.01))
    return {"type": "Polygon", "coordinates": [[
        [p.lon - dlon, p.lat - dlat], [p.lon + dlon, p.lat - dlat],
        [p.lon + dlon, p.lat + dlat], [p.lon - dlon, p.lat + dlat],
        [p.lon - dlon, p.lat - dlat]]]}

def _gfw_loss_ha(geometry):
    import requests
    url = f"{GFW_BASE}/dataset/umd_tree_cover_loss/{_resolve_version()}/query/json"
    sql = f"SELECT SUM(area__ha) AS loss FROM results WHERE umd_tree_cover_loss__year > {config.CUTOFF_YEAR}"
    r = requests.post(url,
                      headers={"x-api-key": config.GFW_API_KEY, "Content-Type": "application/json"},
                      json={"sql": sql, "geometry": geometry}, timeout=30)
    if not r.ok: raise RuntimeError(f"{r.status_code}: {r.text[:150]}")
    rows = r.json().get("data", [])
    return float(rows[0].get("loss") or 0.0) if rows else 0.0

def _gfw_alerts(geometry):
    """Hectareas con alertas de deforestacion reciente (GFW Integrated Alerts: RADD/GLAD) tras el corte."""
    import requests
    cutoff = f"{config.CUTOFF_YEAR}-12-31"
    url = f"{GFW_BASE}/dataset/gfw_integrated_alerts/latest/query/json"
    sql = ("SELECT SUM(area__ha) AS ha FROM results "
           f"WHERE gfw_integrated_alerts__date > '{cutoff}'")
    r = requests.post(url,
                      headers={"x-api-key": config.GFW_API_KEY, "Content-Type": "application/json"},
                      json={"sql": sql, "geometry": geometry}, timeout=30)
    if not r.ok: raise RuntimeError(f"{r.status_code}: {r.text[:120]}")
    rows = r.json().get("data", [])
    return float(rows[0].get("ha") or 0.0) if rows else 0.0

def _gfw_alert_points(geometry, limit=25):
    """Coordenadas de los pixeles de alerta dentro de la parcela (para ubicar el punto en campo)."""
    import requests
    cutoff = f"{config.CUTOFF_YEAR}-12-31"
    url = f"{GFW_BASE}/dataset/gfw_integrated_alerts/latest/query/json"
    sql = ("SELECT latitude, longitude, gfw_integrated_alerts__date "
           f"FROM results WHERE gfw_integrated_alerts__date > '{cutoff}' LIMIT {limit}")
    r = requests.post(url,
                      headers={"x-api-key": config.GFW_API_KEY, "Content-Type": "application/json"},
                      json={"sql": sql, "geometry": geometry}, timeout=30)
    if not r.ok: raise RuntimeError(f"{r.status_code}: {r.text[:120]}")
    out = []
    for row in r.json().get("data", []):
        try:
            out.append({"lat": round(float(row.get("latitude")), 6),
                        "lon": round(float(row.get("longitude")), 6),
                        "date": str(row.get("gfw_integrated_alerts__date") or row.get("date") or "")[:10]})
        except Exception:
            continue
    return out

def _gfw_protected(geometry):
    """True si la parcela intersecta un area protegida (WDPA): senal de legalidad EUDR."""
    import requests
    url = f"{GFW_BASE}/dataset/wdpa_protected_areas/latest/query/json"
    r = requests.post(url,
                      headers={"x-api-key": config.GFW_API_KEY, "Content-Type": "application/json"},
                      json={"sql": "SELECT count(*) AS n FROM results", "geometry": geometry}, timeout=30)
    if not r.ok: raise RuntimeError(f"{r.status_code}: {r.text[:120]}")
    rows = r.json().get("data", [])
    return (int(rows[0].get("n") or 0) > 0) if rows else False

def _jrc_sample_points(plot, max_pts=32):
    """Puntos de muestreo del mapa JRC: centroide + vertices + rejilla interior del bounding box."""
    pts = plot.points
    lats = [p.lat for p in pts]; lons = [p.lon for p in pts]
    clat = sum(lats) / len(lats); clon = sum(lons) / len(lons)
    out = [(clat, clon)] + [(p.lat, p.lon) for p in pts]
    if len(pts) >= 3:  # rejilla 4x4 dentro del bbox, filtrada al interior del poligono (ray casting)
        def _inside(lat, lon):
            n = len(pts); j = n - 1; ok = False
            for i in range(n):
                xi, yi = pts[i].lon, pts[i].lat
                xj, yj = pts[j].lon, pts[j].lat
                if ((yi > lat) != (yj > lat)) and \
                   (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
                    ok = not ok
                j = i
            return ok
        la0, la1 = min(lats), max(lats); lo0, lo1 = min(lons), max(lons)
        for i in range(4):
            for j in range(4):
                la = la0 + (la1 - la0) * (i + 0.5) / 4
                lo = lo0 + (lo1 - lo0) * (j + 0.5) / 4
                if _inside(la, lo):
                    out.append((la, lo))
    return out[:max_pts]

def _jrc_forest(plot):
    """Fraccion [0..1] de puntos muestreados que eran bosque en 2020 segun el mapa oficial de la UE
    (JRC GFC2020 V3, COG). Muestrea centroide + vertices + rejilla interior (no un solo punto)."""
    import os as _os
    _os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    _os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    _os.environ.setdefault("GDAL_HTTP_TIMEOUT", "25")
    import rasterio
    from rasterio.warp import transform as _tf
    samples = _jrc_sample_points(plot)
    with rasterio.open("/vsicurl/" + JRC_COG) as src:
        epsg = src.crs.to_epsg() if src.crs else 4326
        if epsg and epsg != 4326:
            xs, ys = _tf("EPSG:4326", src.crs, [s[1] for s in samples], [s[0] for s in samples])
            coords = list(zip(xs, ys))
        else:
            coords = [(s[1], s[0]) for s in samples]
        vals = [int(v[0]) for v in src.sample(coords)]
    return sum(1 for v in vals if v == 1) / max(len(vals), 1)

def _gfw_check(lot: Lot):
    """Combina fuentes: perdida (Hansen) + alertas (Integrated Alerts) + WDPA + baseline JRC 2020."""
    out = []
    for pl in lot.plots:
        geom = _plot_polygon(pl)
        pt = pl.points[0] if pl.points else None
        loss = alerts = prot = jrc = None; errs = []
        try: loss = _gfw_loss_ha(geom)
        except Exception as e: print("GFW loss error:", e); errs.append("Hansen")
        try: alerts = _gfw_alerts(geom)
        except Exception as e: print("GFW alerts error:", e); errs.append("alertas")
        try: prot = _gfw_protected(geom)
        except Exception as e: print("GFW wdpa error:", e); errs.append("WDPA")
        try: jrc = _jrc_forest(pl) if pt else None
        except Exception as e: print("JRC error:", e); errs.append("JRC")
        if loss is None and alerts is None:
            out.append(DeforestationFinding(pl.plot_id, "review", False,
                "Sin respuesta de las fuentes satelitales (revisar manualmente)"))
            continue
        lv = loss or 0.0; av = alerts or 0.0
        high = (lv >= config.LOSS_THRESHOLD_HA) or (av >= config.LOSS_THRESHOLD_HA)
        # >=80% del predio figura como bosque 2020 en el mapa oficial de la UE: exige revision
        # (suele ser agroforesteria bajo sombra, pero el operador debe poder explicarlo)
        mid = (lv > 0) or (av > 0) or (prot is True) or (jrc is not None and jrc >= 0.8)
        risk = "high" if high else ("review" if mid else "negligible")
        parts = [f"perdida {lv:.2f} ha" if lv > 0 else "sin perdida"]
        srcs = ["Hansen"]
        if alerts is not None:
            parts.append(f"alertas {av:.2f} ha" if av > 0 else "sin alertas recientes"); srcs.append("alertas")
        if prot is not None:
            parts.append("EN area protegida" if prot else "fuera de areas protegidas"); srcs.append("WDPA")
        if jrc is not None:
            parts.append(f"bosque 2020 (JRC): {jrc*100:.0f}% del muestreo" if jrc > 0 else "no bosque 2020 (JRC)")
            srcs.append("JRC")
        detail = f"post-{config.CUTOFF_YEAR}: " + ", ".join(parts) + " (fuentes: " + " + ".join(srcs) + ")"
        if errs:
            detail += " · fuentes no disponibles: " + ", ".join(errs)
        apts = None
        if av > 0:  # ubicar los pixeles de alerta para que el tecnico sepa donde verificar
            try:
                apts = _gfw_alert_points(geom) or None
            except Exception as e:
                print("GFW alert points error:", e)
            if apts:
                detail += f" · alerta cerca de {apts[0]['lat']:.6f}, {apts[0]['lon']:.6f}"
                if apts[0].get("date"):
                    detail += f" ({apts[0]['date']})"
        out.append(DeforestationFinding(pl.plot_id, risk, high, detail, apts))
    return out

# ---------- Fallbacks ----------

def _stub_check(lot: Lot):
    return [DeforestationFinding(p.plot_id, "review", False,
            "Screening preliminar (sin fuente de datos configurada)") for p in lot.plots]

def _ee_check(lot: Lot):
    import ee
    ee.Initialize(project=config.EE_PROJECT)
    lossyear = ee.Image(config.HANSEN_ASSET).select("lossyear")
    cutoff = config.CUTOFF_YEAR - 2000
    out = []
    for p in lot.plots:
        pt = p.points[0]
        geom = (ee.Geometry.Point([pt.lon, pt.lat]).buffer(50)
                if len(p.points) == 1
                else ee.Geometry.Polygon([[[q.lon, q.lat] for q in p.points]]))
        val = lossyear.gt(cutoff).reduceRegion(ee.Reducer.max(), geom, 30).get("lossyear").getInfo()
        risk = ("high", True, f"Perdida tras {config.CUTOFF_YEAR} (Hansen GFC)") if val else \
               ("negligible", False, f"Sin perdida tras {config.CUTOFF_YEAR} (Hansen GFC)")
        out.append(DeforestationFinding(p.plot_id, *risk))
    return out
