import math
from . import config
from .models import Lot, DeforestationFinding

GFW_BASE = "https://data-api.globalforestwatch.org"
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

def _gfw_check(lot: Lot):
    """Combina fuentes: perdida (Hansen) + alertas recientes (Integrated Alerts) + areas protegidas (WDPA)."""
    out = []
    for pl in lot.plots:
        geom = _plot_polygon(pl)
        loss = alerts = prot = None
        try: loss = _gfw_loss_ha(geom)
        except Exception as e: print("GFW loss error:", e)
        try: alerts = _gfw_alerts(geom)
        except Exception as e: print("GFW alerts error:", e)
        try: prot = _gfw_protected(geom)
        except Exception as e: print("GFW wdpa error:", e)
        if loss is None and alerts is None:
            out.append(DeforestationFinding(pl.plot_id, "review", False,
                "GFW: sin respuesta de las fuentes (revisar manualmente)"))
            continue
        lv = loss or 0.0; av = alerts or 0.0
        high = (lv >= config.LOSS_THRESHOLD_HA) or (av >= config.LOSS_THRESHOLD_HA)
        mid = (lv > 0) or (av > 0) or (prot is True)
        risk = "high" if high else ("review" if mid else "negligible")
        parts = [f"perdida {lv:.2f} ha" if lv > 0 else "sin perdida"]
        srcs = ["Hansen"]
        if alerts is not None:
            parts.append(f"alertas {av:.2f} ha" if av > 0 else "sin alertas recientes"); srcs.append("alertas")
        if prot is not None:
            parts.append("EN area protegida" if prot else "fuera de areas protegidas"); srcs.append("WDPA")
        detail = f"post-{config.CUTOFF_YEAR}: " + ", ".join(parts) + " (GFW: " + " + ".join(srcs) + ")"
        out.append(DeforestationFinding(pl.plot_id, risk, high, detail))
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
