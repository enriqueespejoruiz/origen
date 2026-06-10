import os, uuid, json, base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from . import gemini, deforestation, dossier, storage, config
from .models import Lot, Plot, GeoPoint

app = FastAPI(title="Origen - EUDR + Export Copilot")
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

def _page(name):
    return FileResponse(os.path.join(WEB_DIR, name), media_type="text/html")

@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(os.path.join(WEB_DIR, "manifest.webmanifest"), media_type="application/manifest+json")

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(WEB_DIR, "sw.js"), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

@app.get("/")
def home():
    return _page("landing.html")

@app.get("/capturar")
def capturar():
    return _page("capturar.html")

@app.get("/normativa")
def normativa():
    return _page("normativa.html")

@app.get("/empezar")
def empezar():
    return _page("empezar.html")

@app.get("/healthz")
def healthz():
    return {"ok": True, "model": config.GEMINI_MODEL, "gemini_ready": config.gemini_ready()}

# ---- Captura estructurada de campo (tecnico de la cooperativa) ----

class CaptureIn(BaseModel):
    producer: str = ""
    cooperative: str = ""
    commodity: str = "coffee"
    region: str = ""
    area_ha: float | None = None
    lat: float
    lon: float
    points: list[dict] | None = None     # vertices [{lat,lon}] del poligono (parcelas >4 ha)
    quantity: str = ""                     # cantidad estimada del lote
    photo_base64: str | None = None

@app.post("/capture")
def capture(c: CaptureIn):
    lot_id = "LOT-" + uuid.uuid4().hex[:8].upper()
    if c.points and len(c.points) >= 3:
        pts = [GeoPoint(float(p["lat"]), float(p["lon"])) for p in c.points]
    else:
        pts = [GeoPoint(c.lat, c.lon)]
    plot = Plot("P1", pts, c.area_ha)
    lot = Lot(lot_id, c.producer, c.cooperative, c.commodity, "PE", c.region, [plot], "", "", c.quantity)
    if c.photo_base64:
        try:
            up = os.path.join(config.DATA_DIR, "uploads"); os.makedirs(up, exist_ok=True)
            data = c.photo_base64.split(",", 1)[-1]
            with open(os.path.join(up, f"{lot_id}.jpg"), "wb") as f:
                f.write(base64.b64decode(data))
        except Exception:
            pass
    storage.save_lot(lot)
    return {"lot_id": lot_id, "producer": lot.producer_name}

# ---- Captacion de leads (onboarding desde la landing) ----

class LeadIn(BaseModel):
    name: str = ""
    org: str = ""
    email: str = ""
    phone: str = ""
    role: str = ""
    commodity: str = ""
    plots: str = ""
    message: str = ""

@app.post("/lead")
def lead(l: LeadIn):
    import datetime
    rec = l.model_dump(); rec["ts"] = datetime.datetime.utcnow().isoformat() + "Z"
    print("LEAD " + json.dumps(rec, ensure_ascii=False))  # queda en los logs de Cloud Run
    saved = False
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("leads").add(rec)
            saved = True
        except Exception:
            pass
    if not saved:
        try:
            os.makedirs(config.DATA_DIR, exist_ok=True)
            with open(os.path.join(config.DATA_DIR, "leads.jsonl"), "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return {"ok": True}

# ---- Intake por texto libre (Gemini) ----

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
    try:
        storage.save_blob(lot_id, "dossier.pdf", open(pdf, "rb").read())
        storage.save_blob(lot_id, "data.geojson", open(gj, "rb").read())
    except Exception:
        pass
    return {"lot_id": lot_id, "overall_risk": dossier.overall_risk(findings),
            "geojson": gj, "pdf": pdf, "findings": [f.__dict__ for f in findings]}

def _ensure_outputs(lot_id: str):
    """Regenera dossier+geojson desde el lote durable si faltan en disco (instancias efimeras de Cloud Run)."""
    out = os.path.join(config.DATA_DIR, "dossiers")
    pdf = os.path.join(out, f"{lot_id}_dossier.pdf")
    gj  = os.path.join(out, f"{lot_id}.geojson")
    if os.path.exists(pdf) and os.path.exists(gj):
        return pdf, gj
    lot = _load(lot_id)
    findings = deforestation.check_plots(lot)
    narrative = gemini.generate_dossier_narrative(lot, findings)
    profile = gemini.generate_buyer_profile(lot)
    gj = dossier.build_geojson(lot, out)
    pdf = dossier.build_pdf(lot, findings, narrative, profile, out)
    try:
        storage.save_blob(lot_id, "dossier.pdf", open(pdf, "rb").read())
        storage.save_blob(lot_id, "data.geojson", open(gj, "rb").read())
    except Exception:
        pass
    return pdf, gj

@app.get("/lots/{lot_id}/dossier")
def get_dossier(lot_id: str):
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}_dossier.pdf")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/pdf", filename=f"{lot_id}_dossier.pdf")
    blob = storage.load_blob(lot_id, "dossier.pdf")
    if blob:
        return Response(blob, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}_dossier.pdf"'})
    p, _ = _ensure_outputs(lot_id)
    return FileResponse(p, media_type="application/pdf", filename=f"{lot_id}_dossier.pdf")

@app.get("/lots/{lot_id}/geojson")
def get_geojson(lot_id: str):
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}.geojson")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/geo+json", filename=f"{lot_id}.geojson")
    blob = storage.load_blob(lot_id, "data.geojson")
    if blob:
        return Response(blob, media_type="application/geo+json",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}.geojson"'})
    _, gj = _ensure_outputs(lot_id)
    return FileResponse(gj, media_type="application/geo+json", filename=f"{lot_id}.geojson")

def _load(lot_id: str) -> Lot:
    d = storage.load_lot(lot_id)
    if not d:
        raise HTTPException(404, "Lote no encontrado")
    plots = [Plot(p["plot_id"], [GeoPoint(**pt) for pt in p["points"]], p.get("area_ha")) for p in d["plots"]]
    return Lot(d["lot_id"], d["producer_name"], d["cooperative"], d["commodity"],
               d.get("country", "PE"), d.get("region", ""), plots,
               d.get("harvest_season", ""), d.get("raw_notes", ""), d.get("quantity", ""))
