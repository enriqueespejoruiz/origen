from .models import Lot, Plot

def plot_geometry(plot: Plot):
    if len(plot.points) == 1:
        p = plot.points[0]
        return {"type": "Point", "coordinates": [p.lon, p.lat]}
    ring = [[p.lon, p.lat] for p in plot.points]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}

def lot_to_geojson(lot: Lot):
    feats = []
    for pl in lot.plots:
        feats.append({
            "type": "Feature",
            "properties": {
                "plot_id": pl.plot_id, "lot_id": lot.lot_id,
                "producer": lot.producer_name, "commodity": lot.commodity,
                "area_ha": pl.area_ha,
            },
            "geometry": plot_geometry(pl),
        })
    return {"type": "FeatureCollection", "features": feats}

def geometry_issues(plot):
    """Problemas de geometría que afectan calidad/aceptación (TRACES rechaza polígonos inválidos)."""
    import math
    issues = []
    pts = plot.points
    if len(pts) >= 3:
        try:
            from shapely.geometry import Polygon as _P
            poly = _P([(p.lon, p.lat) for p in pts])
            if not poly.is_valid:
                issues.append("polígono inválido (auto-intersección); TRACES lo rechazaría")
            latm = sum(p.lat for p in pts) / len(pts)
            m2 = 111320.0 * (111320.0 * max(math.cos(math.radians(latm)), 0.01))
            area_ha = abs(poly.area) * m2 / 10000.0
            if area_ha < 0.01:
                issues.append("área demasiado pequeña (<0.01 ha); revisar captura")
            elif area_ha > 5000:
                issues.append("área inusualmente grande (>5000 ha); revisar")
        except Exception as e:
            print("geom check error:", repr(e))
    elif pts:
        p = pts[0]
        if not (-90 <= p.lat <= 90 and -180 <= p.lon <= 180):
            issues.append("coordenadas fuera de rango")
    return issues
