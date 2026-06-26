"""Portabilidad de datos: la cooperativa se lleva TODA su data en formatos abiertos.
Genera un ZIP (CSV + GeoJSON TRACES + manifest JSON + dossiers). Es lo contrario a los
portales de traders que retienen la data del productor: aquí la coop es dueña y la exporta."""
import io, csv, json, zipfile, datetime
from . import storage, geo, config
from .models import Lot, Plot, GeoPoint


def _to_lot(d):
    plots = [Plot(p["plot_id"], [GeoPoint(**pt) for pt in p.get("points", [])], p.get("area_ha"))
             for p in d.get("plots", [])]
    return Lot(d.get("lot_id", ""), d.get("producer_name", ""), d.get("cooperative", ""),
               d.get("commodity", ""), d.get("country", "PE"), d.get("region", ""), plots,
               d.get("harvest_season", ""), d.get("raw_notes", ""), d.get("quantity", ""),
               d.get("coop_id", ""), d.get("captured_by", ""), d.get("created_at", ""), d.get("extra", {}))


def build_export_zip(coop, lot_dicts):
    """Devuelve (bytes_zip, n_lotes). coop: dict con id/name. lot_dicts: lista de lotes (dicts)."""
    now = datetime.datetime.utcnow().isoformat() + "Z"
    buf = io.BytesIO()
    feats, manifest_lots = [], []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # 1) CSV de lotes
        s = io.StringIO(); w = csv.writer(s)
        w.writerow(["lot_id", "producer", "commodity", "region", "quantity_kg",
                    "overall_risk", "n_plots", "captured_by", "created_at"])
        for d in lot_dicts:
            w.writerow([d.get("lot_id", ""), d.get("producer_name", ""), d.get("commodity", ""),
                        d.get("region", ""), d.get("quantity", ""), d.get("overall_risk", ""),
                        len(d.get("plots", [])), d.get("captured_by", ""), d.get("created_at", "")])
        z.writestr("lotes.csv", s.getvalue())

        # 2) GeoJSON combinado (TRACES) + manifest + dossiers
        for d in lot_dicts:
            lid = d.get("lot_id", "")
            try:
                fc = geo.lot_to_geojson(_to_lot(d))
                for f in fc.get("features", []):
                    f.setdefault("properties", {})["lot_id"] = lid
                    feats.append(f)
            except Exception as e:
                print("export geojson error", lid, repr(e))
            note = storage.get_notary(lid) or {}
            manifest_lots.append({
                "lot_id": lid, "producer": d.get("producer_name", ""),
                "commodity": d.get("commodity", ""), "region": d.get("region", ""),
                "quantity": d.get("quantity", ""), "overall_risk": d.get("overall_risk", ""),
                "n_plots": len(d.get("plots", [])), "created_at": d.get("created_at", ""),
                "notary": ({"sha256": note.get("sha256"), "created_at": note.get("created_at")}
                           if note else None),
            })
            try:
                blob = storage.load_blob(lid, "dossier.pdf")
                if blob:
                    z.writestr(f"dossiers/{lid}.pdf", blob)
            except Exception:
                pass

        z.writestr("lotes.geojson", json.dumps(
            {"type": "FeatureCollection", "features": feats}, ensure_ascii=False, indent=2))
        z.writestr("manifest.json", json.dumps({
            "generated_at": now, "format": "Origen export v1",
            "cooperative": {"id": coop.get("id", ""), "name": coop.get("name", "")},
            "n_lots": len(lot_dicts), "lots": manifest_lots,
        }, ensure_ascii=False, indent=2))
        z.writestr("LEEME.txt", _readme(coop, len(lot_dicts), now))

    return buf.getvalue(), len(lot_dicts)


def _readme(coop, n, now):
    base = getattr(config, "PUBLIC_BASE_URL", "")
    return (
        "ORIGEN — Tu data, en tus manos\n"
        "================================\n\n"
        f"Cooperativa: {coop.get('name', '')}\n"
        f"Generado:    {now}\n"
        f"Lotes:       {n}\n\n"
        "Esta data es TUYA. Te la llevas en formatos abiertos, sin candados:\n"
        "  - lotes.csv      Tabla de todos tus lotes (Excel, Sheets, lo que uses).\n"
        "  - lotes.geojson  Geometrías parcela por parcela en formato TRACES (listo para la UE).\n"
        "  - manifest.json  Todo legible por máquina: lotes, veredictos y sellos de notarización.\n"
        "  - dossiers/      Tus dossiers EUDR en PDF.\n\n"
        "Puedes abrir estos archivos en cualquier herramienta, dárselos a cualquier comprador o\n"
        "auditor, o migrarlos a otro sistema. Origen no retiene tu data: la gobierna la cooperativa.\n\n"
        f"Generado con Origen — {base}\n"
    )
