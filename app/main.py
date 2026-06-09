import os, uuid, json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from . import gemini, deforestation, dossier, storage, config
from .models import Lot, Plot, GeoPoint

app = FastAPI(title="Origen - EUDR + Export Copilot")

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

@app.get("/")
def home():
    return FileResponse(os.path.join(WEB_DIR, "index.html"), media_type="text/html")

@app.get("/healthz")
def healthz():
    return {"ok": True, "model": config.GEMINI_MODEL, "gemini_ready": config.gemini_ready()}

@app.post("/intake")
async def intake(notes: str = Form(""), images: list[UploadFile] = File(default=[])):
    lot_id = "LOT-" + uuid.uuid4().hex[:8].upper()
    up = os.path.join(config.DATA_DIR, "uploads"); os.makedirs(up, exist_ok=True)
    paths = []
    for im in images:
        fp = os.path.join(up, f"{lot_id}_{im.filename}")
        with open(fp, "wb") as f: f.write(await im.read())
        paths.append(fp)
    lot = gemini.extract_lot(notes, paths, lot_id)
    storage.save_lot(lot)
    return {"lot_id": lot_id, "producer": lot.producer_name, "plots": len(lot.plots)}

@app.post("/lots/{lot_id}/process")
def process(lot_id: str):
    lot = _load(lot_id)
    findings = deforestation.check_plots(lot)
    narrative = gemini.generate_dossier_narrative(lot, findings)
    profile = gemini.generate_buyer_profile(lot)
    out = os.path.join(config.DATA_DIR, "dossiers")
    gj = dossier.build_geojson(lot, out)
    pdf = dossier.build_pdf(lot, findings, narrative, profile, out)
    storage.upload_file(gj); storage.upload_file(pdf)
    return {"lot_id": lot_id, "overall_risk": dossier.overall_risk(findings),
            "geojson": gj, "pdf": pdf, "findings": [f.__dict__ for f in findings]}

@app.get("/lots/{lot_id}/dossier")
def get_dossier(lot_id: str):
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}_dossier.pdf")
    if not os.path.exists(p):
        raise HTTPException(404, "Genera el dossier con POST /lots/{id}/process primero")
    return FileResponse(p, media_type="application/pdf")

def _load(lot_id: str) -> Lot:
    fp = os.path.join(config.DATA_DIR, f"{lot_id}.json")
    if not os.path.exists(fp):
        raise HTTPException(404, "Lote no encontrado")
    d = json.load(open(fp))
    plots = [Plot(p["plot_id"], [GeoPoint(**pt) for pt in p["points"]], p.get("area_ha")) for p in d["plots"]]
    return Lot(d["lot_id"], d["producer_name"], d["cooperative"], d["commodity"],
               d.get("country", "PE"), d.get("region", ""), plots,
               d.get("harvest_season", ""), d.get("raw_notes", ""))
