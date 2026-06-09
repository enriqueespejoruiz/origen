from . import config
from .models import Lot, DeforestationFinding

def check_plots(lot: Lot):
    """Cruza cada parcela contra perdida de cobertura forestal posterior al ano de corte."""
    try:
        if config.EE_PROJECT:
            return _ee_check(lot)
    except Exception as e:
        return [DeforestationFinding(p.plot_id, "review", False, f"EE error: {e}") for p in lot.plots]
    return _stub_check(lot)

def _stub_check(lot: Lot):
    out = []
    for p in lot.plots:
        seed = abs((p.points[0].lat if p.points else 0) * 1000) % 10
        if seed > 7:
            out.append(DeforestationFinding(p.plot_id, "high", True, "(MOCK) perdida de cobertura tras 2020"))
        elif seed > 4:
            out.append(DeforestationFinding(p.plot_id, "review", False, "(MOCK) revisar manualmente"))
        else:
            out.append(DeforestationFinding(p.plot_id, "negligible", False, "(MOCK) sin perdida tras 2020"))
    return out

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
        recent = lossyear.gt(cutoff)
        val = recent.reduceRegion(ee.Reducer.max(), geom, 30).get("lossyear").getInfo()
        if val:
            out.append(DeforestationFinding(p.plot_id, "high", True, f"Perdida tras {config.CUTOFF_YEAR} (Hansen GFC)"))
        else:
            out.append(DeforestationFinding(p.plot_id, "negligible", False, f"Sin perdida tras {config.CUTOFF_YEAR} (Hansen GFC)"))
    return out
