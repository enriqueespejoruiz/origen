from .models import Lot, Plot

def _r6(v):
    """≥6 decimales como exige el sistema de la UE (TRACES trunca a 6)."""
    return round(float(v), 6)

def plot_geometry(plot: Plot):
    if len(plot.points) == 1:
        p = plot.points[0]
        return {"type": "Point", "coordinates": [_r6(p.lon), _r6(p.lat)]}
    ring = [[_r6(p.lon), _r6(p.lat)] for p in plot.points]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}

def traces_properties(lot: Lot, plot: Plot, risk=None):
    """Propiedades en el formato del sistema de información de la UE (TRACES):
    ProducerName, ProducerCountry (ISO2), ProductionPlace y Area (ha; requerida para puntos)."""
    props = {
        "ProducerName": lot.producer_name or "",
        "ProducerCountry": (lot.country or "PE"),
        "ProductionPlace": lot.region or lot.lot_id,
    }
    if len(plot.points) < 3 and plot.area_ha:   # punto: el área no se deriva de la geometría
        props["Area"] = round(float(plot.area_ha), 4)
    # extras de trazabilidad (TRACES ignora claves que no reconoce)
    props["lot_id"] = lot.lot_id
    props["plot_id"] = plot.plot_id
    if risk:
        props["risk"] = risk
    return props

def lot_to_geojson(lot: Lot):
    """GeoJSON conforme al formato de carga de TRACES (un Feature por parcela)."""
    feats = []
    for i, pl in enumerate(lot.plots):
        feats.append({
            "type": "Feature",
            "properties": traces_properties(lot, pl),
            "geometry": plot_geometry(pl),
            "id": i,
        })
    return {"type": "FeatureCollection", "features": feats}

def volume_issues(lot):
    """Anti-fraude de volumen: kg declarados vs rendimiento plausible del área total de las parcelas.
    Devuelve notas si el volumen es inverosímil (posible mezcla de origen no declarada)."""
    import re as _re
    from . import config
    issues = []
    try:
        total_ha = sum((p.area_ha or 0.0) for p in lot.plots)
        q = str(getattr(lot, "quantity", "") or "").replace(",", "")
        m = _re.search(r"[\d.]+", q)
        kg = float(m.group()) if m else 0.0
        if total_ha > 0 and kg > 0:
            ceil = config.YIELD_CEIL_KG_HA.get((lot.commodity or "").lower(), 2500.0)
            yld = kg / total_ha
            if yld > ceil:
                issues.append(
                    f"volumen declarado ({kg:.0f} kg) inverosímil para {total_ha:.1f} ha "
                    f"(≈{yld:.0f} kg/ha; techo plausible ~{ceil:.0f} kg/ha): revisar posible mezcla de origen")
    except Exception as e:
        print("volume check error:", repr(e))
    return issues

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
