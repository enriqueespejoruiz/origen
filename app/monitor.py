"""Monitoreo continuo: re-verifica las parcelas de los lotes y crea una alerta si el veredicto
EMPEORA respecto al último (una parcela se volvió no conforme). Pensado para correr periódicamente
vía Cloud Scheduler → POST /cron/monitor."""
import datetime
from . import deforestation, storage
from .portability import _to_lot

_RANK = {"negligible": 0, "review": 1, "high": 2}


def _verdict(findings):
    if any(f.risk == "high" for f in findings):
        return "high"
    if any(f.risk == "review" for f in findings):
        return "review"
    return "negligible"


def run_monitor(coop_id=None, limit=500, notify=None):
    """Re-verifica lotes y crea alertas si el riesgo empeora.
    notify(alert) es un callback opcional (p. ej. enviar WhatsApp). Devuelve {checked, alerts, new}."""
    lots = storage.list_lots(coop_id) if coop_id else storage.list_all_lots(limit)
    checked, new = 0, []
    for d in lots[:limit]:
        lid = d.get("lot_id")
        prev = d.get("overall_risk", "")
        if not lid or not prev:          # nunca procesado: no hay base para comparar
            continue
        try:
            findings = deforestation.check_plots(_to_lot(d))
        except Exception as e:
            print("monitor check error", lid, repr(e))
            continue
        cur = _verdict(findings)
        checked += 1
        if _RANK.get(cur, 0) > _RANK.get(prev, 0):
            alert = {
                "lot_id": lid, "coop_id": d.get("coop_id", ""),
                "producer": d.get("producer_name", ""), "commodity": d.get("commodity", ""),
                "from": prev, "to": cur,
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            try:
                storage.save_alert(alert)
            except Exception as e:
                print("alert save error", repr(e))
            try:    # actualiza el estado almacenado + cache de findings
                storage.merge_lot(lid, {"overall_risk": cur, "findings": [
                    {"plot_id": f.plot_id, "risk": f.risk,
                     "loss_after_cutoff": getattr(f, "loss_after_cutoff", False),
                     "detail": f.detail} for f in findings]})
            except Exception as e:
                print("monitor merge error", repr(e))
            new.append(alert)
            if notify:
                try:
                    notify(alert)
                except Exception as e:
                    print("monitor notify error", repr(e))
    return {"checked": checked, "alerts": len(new), "new": new}
