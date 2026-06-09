"""Pipeline demo end-to-end. Corre sin credenciales (modo STUB)."""
from app import gemini, deforestation, dossier, storage, config

def main():
    notes = ("Soy Juan Perez, cooperativa Cafe del Valle, San Martin. Tengo dos parcelas de cafe: "
             "parcela 1 en -6.486,-76.366 (2.1 ha) y parcela 2 en -6.502,-76.349 (1.4 ha). Cosecha 2026.")
    lot = gemini.extract_lot(notes, [], "LOT-DEMO01")
    where = storage.save_lot(lot)
    findings = deforestation.check_plots(lot)
    narrative = gemini.generate_dossier_narrative(lot, findings)
    profile = gemini.generate_buyer_profile(lot)
    out = "./_data/dossiers"
    gj = dossier.build_geojson(lot, out)
    pdf = dossier.build_pdf(lot, findings, narrative, profile, out)
    print("== Origen MVP - pipeline demo ==")
    print("Modo Gemini :", "API/Vertex" if config.gemini_ready() else "STUB (sin API key)")
    print("Lote        :", lot.lot_id, "| productor:", lot.producer_name, "| parcelas:", len(lot.plots))
    print("Storage     :", where)
    print("Riesgo gral :", dossier.overall_risk(findings))
    for f in findings:
        print("   -", f.plot_id, f.risk, "|", f.detail)
    print("GeoJSON     :", gj)
    print("PDF dossier :", pdf)

if __name__ == "__main__":
    main()
