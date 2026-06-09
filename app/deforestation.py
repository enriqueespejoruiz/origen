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
    global _VERSION
    if _VERSION:
        return _VERSION
    _VERSION = config.GFW_VERSION
    try:
        import re, requests
        r = requests.get(f"{GFW_BASE}/dataset/umd_tree_cover_loss", timeout=15)
        vers = [v for v in r.json().get("data", {}).get("versions", []) if re.match(r"^v\d", v)]
        if vers:
            _VERSION = sorted(vers, key=lambda v: [int(x) for x in re.findall(r"\d+", v)])[-1]
    except Exception:
        pass
    return _VERSION

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
    r.raise_for_status()
    rows = r.json().get("data", [])
    return float(rows[0].get("loss") or 0.0) if rows else 0.0

def _gfw_alerts(geometry):
    """Cuenta alertas de deforestacion reciente (GFW Integrated Alerts: RADD/GLAD) posteriores al corte."""
    import requests
    cutoff = f"{config.CUTOFF_YEAR}-12-31"
    url = f"{GFW_BASE}/dataset/gfw_integrated_alerts/latest/query/json"
    sql = ("SELECT count(*) AS n FROM results "
           f"WHERE gfw_integrated_alerts__date > '{cutoff}' "
           "AND gfw_integrated_alerts__confidence <> 'low'")
    r = requests.post(url,
                      headers={"x-api-key": config.GFW_API_KEY, "Content-Type": "application/json"},
                      json={"sql": sql, "geometry": geometry}, timeout=30)
    r.raise_for_status()
    rows = r.json().get("data", [])
    return int(rows[0].get("n") or 0) if rows else 0

def _gfw_check(lot: Lot):
    """Combina dos fuentes: perdida de bosque (Hansen) + alertas recientes (Integrated Alerts)."""
    out = []
    for pl in lot.plots:
        geom = _plot_polygon(pl)
        loss = alerts = None; errs = []
        try: loss = _gfw_loss_ha(geom)
        except Exception as e: errs.append(f"perdida:{e}")
        try: alerts = _gfw_alerts(geom)
        except Exception as e: errs.append(f"alertas:{e}")
        if loss is None and alerts is None:
            out.append(DeforestationFinding(pl.plot_id, "review", False, ("GFW error: " + "; ".join(errs))[:140]))
            continue
        lv = loss or 0.0; av = alerts or 0
        high = (lv >= config.LOSS_THRESHOLD_HA) or (av >= config.ALERTS_THRESHOLD)
        mid = (lv > 0) or (av > 0)
        risk = "high" if high else ("review" if mid else "negligible")
        parts = [f"perdida {lv:.2f} ha" if lv > 0 else "sin perdida"]
        if alerts is not None:
            parts.append(f"{av} alertas recientes" if av > 0 else "sin alertas recientes")
        detail = f"post-{config.CUTOFF_YEAR}: " + ", ".join(parts) + " (GFW: Hansen + alertas integradas)"
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
