"""Simulador what-if de segregación EUDR + score de confianza del lote.
Determinista y barato (sin Gemini). Reutiliza geo.volume_issues / geo.geometry_issues.

El EUDR no permite mass-balance: una parcela observada debe excluirse del envío o
sustentarse. Este módulo deja al usuario simular esa exclusión y ver, en vivo, el
volumen y el estado resultante; y resume la "salud" del lote en un score explicable."""
import re
from . import geo


# ---------- helpers de volumen ----------
def _total_kg(lot):
    q = str(getattr(lot, "quantity", "") or "").replace(",", "")
    m = re.search(r"[\d.]+", q)
    try:
        return float(m.group()) if m else 0.0
    except Exception:
        return 0.0


def _kg_by_plot(lot):
    """Reparte el volumen del lote entre parcelas por área (o a partes iguales si no hay áreas).
    El volumen es a nivel lote; este prorrateo es una aproximación para el what-if."""
    kg = _total_kg(lot)
    plots = lot.plots or []
    if not plots:
        return {}, kg
    areas = {p.plot_id: (p.area_ha or 0.0) for p in plots}
    tot_a = sum(areas.values())
    out = {}
    for p in plots:
        out[p.plot_id] = kg * (areas[p.plot_id] / tot_a) if tot_a > 0 else kg / len(plots)
    return out, kg


def _status_from_risks(risks):
    if "high" in risks:
        return "no_apto"
    if "review" in risks:
        return "revisar"
    return "apto"


# ---------- simulación de segregación ----------
def suggest_exclusions(findings):
    """Parcelas que conviene excluir por defecto: las observadas (high)."""
    return [f.plot_id for f in findings if f.risk == "high"]


def simulate(lot, findings, exclude_ids):
    """Simula excluir parcelas del envío y devuelve volumen restante + estado resultante."""
    exclude = set(exclude_ids or [])
    kg_by, kg_total = _kg_by_plot(lot)
    area_by = {p.plot_id: (p.area_ha or 0.0) for p in (lot.plots or [])}
    risk_by = {f.plot_id: f.risk for f in findings}

    plots, kg_rem, ha_rem, rem_risks = [], 0.0, 0.0, []
    for p in (lot.plots or []):
        inc = p.plot_id not in exclude
        risk = risk_by.get(p.plot_id, "negligible")
        plots.append({
            "plot_id": p.plot_id, "risk": risk,
            "area_ha": round(area_by.get(p.plot_id, 0.0), 3),
            "kg": round(kg_by.get(p.plot_id, 0.0)),
            "included": inc,
        })
        if inc:
            kg_rem += kg_by.get(p.plot_id, 0.0)
            ha_rem += area_by.get(p.plot_id, 0.0)
            rem_risks.append(risk)

    ids = {p.plot_id for p in (lot.plots or [])}
    n_excl = len(exclude & ids)
    status_before = _status_from_risks([f.risk for f in findings])
    status_after = _status_from_risks(rem_risks)
    high_rem = [p["plot_id"] for p in plots if p["included"] and p["risk"] == "high"]
    rev_rem = [p["plot_id"] for p in plots if p["included"] and p["risk"] == "review"]

    if status_after == "apto":
        sug = "Con esta exclusión el envío queda apto: las parcelas restantes están en orden."
    elif high_rem:
        sug = ("Aún quedan parcelas observadas (" + ", ".join(high_rem) +
               "): exclúyelas o no podrás declarar el envío como conforme.")
    else:
        sug = ("Quedan parcelas a revisar (" + ", ".join(rev_rem) +
               "): sustenta su legalidad/origen o exclúyelas.")

    return {
        "plots": plots,
        "kg_total": round(kg_total), "kg_remaining": round(kg_rem),
        "kg_excluded": round(kg_total - kg_rem), "ha_remaining": round(ha_rem, 3),
        "n_total": len(ids), "n_remaining": len(ids) - n_excl, "n_excluded": n_excl,
        "pct_kept": round(100 * kg_rem / kg_total) if kg_total else None,
        "status_before": status_before, "status_after": status_after,
        "all_clear": status_after == "apto", "suggestion": sug,
    }


# ---------- simulación a nivel envío (consignación) ----------
def _worst_risk(findings):
    risks = [f.risk for f in findings]
    if "high" in risks:
        return "high"
    if "review" in risks:
        return "review"
    return "negligible"


def suggest_exclusions_consignment(items):
    """Lotes que conviene excluir del contenedor: los que tienen alguna parcela observada."""
    return [lot.lot_id for lot, findings in items if any(f.risk == "high" for f in findings)]


def simulate_consignment(items, exclude_lot_ids):
    """What-if a nivel envío: excluir lotes observados y ver volumen/estado del contenedor.
    items = [(lot, findings)]; la unidad de exclusión es el lote completo."""
    exclude = set(exclude_lot_ids or [])
    rows, kg_rem, kg_total, rem_risks = [], 0.0, 0.0, []
    for lot, findings in items:
        kg = _total_kg(lot)
        risk = _worst_risk(findings)
        inc = lot.lot_id not in exclude
        rows.append({
            "plot_id": lot.lot_id, "label": getattr(lot, "producer_name", "") or "",
            "risk": risk, "kg": round(kg), "area_ha": None, "included": inc,
        })
        kg_total += kg
        if inc:
            kg_rem += kg
            rem_risks.append(risk)

    ids = {r["plot_id"] for r in rows}
    n_excl = len(exclude & ids)
    status_before = _status_from_risks([r["risk"] for r in rows])
    status_after = _status_from_risks(rem_risks)
    high_rem = [r["plot_id"] for r in rows if r["included"] and r["risk"] == "high"]
    rev_rem = [r["plot_id"] for r in rows if r["included"] and r["risk"] == "review"]

    if status_after == "apto":
        sug = "Con esta exclusión el envío queda apto: todos los lotes restantes están en orden."
    elif high_rem:
        sug = ("Aún quedan lotes observados (" + ", ".join(high_rem) +
               "): exclúyelos del contenedor o sustenta su origen.")
    else:
        sug = ("Quedan lotes a revisar (" + ", ".join(rev_rem) +
               "): verifícalos antes de declarar el envío.")

    return {
        "plots": rows, "level": "consignment",
        "kg_total": round(kg_total), "kg_remaining": round(kg_rem),
        "kg_excluded": round(kg_total - kg_rem), "ha_remaining": None,
        "n_total": len(ids), "n_remaining": len(ids) - n_excl, "n_excluded": n_excl,
        "pct_kept": round(100 * kg_rem / kg_total) if kg_total else None,
        "status_before": status_before, "status_after": status_after,
        "all_clear": status_after == "apto", "suggestion": sug,
    }


# ---------- score de confianza ----------
def confidence_score(lot, findings):
    """0–100 con factores explicables. Determinista; reutiliza los chequeos del MVP."""
    n = max(len(findings), 1)
    neg = sum(1 for f in findings if f.risk == "negligible")
    rev = sum(1 for f in findings if f.risk == "review")
    high = sum(1 for f in findings if f.risk == "high")

    conf01 = (neg * 1.0 + rev * 0.55 + high * 0.0) / n

    gp = lot.plots or []
    good_geo = 0
    for p in gp:
        try:
            if not geo.geometry_issues(p):
                good_geo += 1
        except Exception:
            pass
    geo01 = (good_geo / len(gp)) if gp else 0.5

    try:
        vol01 = 0.35 if geo.volume_issues(lot) else 1.0
    except Exception:
        vol01 = 0.7

    _lg = (lot.extra or {}).get("legality", {}) if isinstance(lot.extra, dict) else {}
    filled = sum(1 for k in ("title", "env", "labor") if str(_lg.get(k, "")).strip())
    legal01 = filled / 3.0

    factors = [
        {"key": "conformidad", "label": "Conformidad de parcelas", "weight": 40,
         "value": round(conf01 * 100),
         "note": f"{neg} en orden · {rev} a revisar · {high} observadas"},
        {"key": "geometria", "label": "Calidad geométrica (TRACES)", "weight": 25,
         "value": round(geo01 * 100),
         "note": f"{good_geo}/{len(gp)} parcelas sin problemas de geometría"},
        {"key": "volumen", "label": "Plausibilidad de volumen", "weight": 20,
         "value": round(vol01 * 100),
         "note": "kg/ha dentro de lo plausible" if vol01 >= 0.99 else "volumen a revisar (posible mezcla)"},
        {"key": "legalidad", "label": "Legalidad documentada", "weight": 15,
         "value": round(legal01 * 100),
         "note": f"{filled}/3 campos de legalidad completados"},
    ]
    score = round(sum(f["weight"] * f["value"] / 100 for f in factors))
    band = "alta" if score >= 80 else ("media" if score >= 60 else "baja")
    return {"score": score, "band": band, "factors": factors}
