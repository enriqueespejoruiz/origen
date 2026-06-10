import os, uuid, json, base64, datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from . import gemini, deforestation, dossier, storage, config, auth, geo, notarize
from .models import Lot, Plot, GeoPoint, Consignment, DeforestationFinding

app = FastAPI(title="Origen - EUDR + Export Copilot")
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET,
                   same_site="lax", max_age=60 * 60 * 24 * 14)
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

def _now(): return datetime.datetime.utcnow().isoformat() + "Z"

import time as _time
_RL = {}
def _throttle(ip, bucket, limit, window=60):
    """Límite básico por IP en memoria (anti-spam). Producción: Cloud Armor / API Gateway."""
    now = _time.time(); key = (bucket, ip or "?")
    hits = [t for t in _RL.get(key, []) if now - t < window]
    if len(hits) >= limit:
        _RL[key] = hits; return False
    hits.append(now); _RL[key] = hits; return True

def _photo_path(lot_id, out_dir):
    """Devuelve la ruta local de la foto del predio (la recupera del blob durable si hace falta)."""
    p = os.path.join(out_dir, f"{lot_id}_photo.jpg")
    if os.path.exists(p):
        return p
    up = os.path.join(config.DATA_DIR, "uploads", f"{lot_id}.jpg")
    if os.path.exists(up):
        return up
    blob = storage.load_blob(lot_id, "photo.jpg")
    if blob:
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(p, "wb") as f:
                f.write(blob)
            return p
        except Exception:
            return None
    return None

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
    return {"ok": True, "model": config.GEMINI_MODEL,
            "gemini_ready": config.gemini_ready(), "auth_ready": config.auth_ready()}

@app.get("/panel")
def panel():
    return _page("panel.html")

# ---- Login con Google + cooperativa (multi-tenant) ----

class GoogleIn(BaseModel):
    credential: str

class CoopIn(BaseModel):
    name: str

@app.post("/auth/google")
def auth_google(g: GoogleIn, request: Request):
    try:
        user = auth.verify_google_credential(g.credential)
    except Exception as e:
        print("auth error:", repr(e))
        raise HTTPException(401, "No se pudo verificar la cuenta de Google")
    request.session["user"] = user
    prof = storage.get_user(user["sub"]) or {}
    if prof.get("coop_id"):
        request.session["coop"] = {"id": prof["coop_id"], "name": prof.get("coop_name", ""),
                                   "role": prof.get("role", "tecnico")}
    storage.save_user(user["sub"], {"email": user["email"], "name": user["name"], "last_login": _now()})
    return {"user": user, "coop": request.session.get("coop")}

@app.post("/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/api/me")
def api_me(request: Request):
    return {"user": auth.current(request), "coop": request.session.get("coop"),
            "client_id": config.GOOGLE_OAUTH_CLIENT_ID}

@app.post("/api/coop")
def api_coop(c: CoopIn, request: Request):
    import re
    user = auth.require_user(request)
    name = (c.name or "").strip()
    if not name:
        raise HTTPException(400, "Pon el nombre de la cooperativa")
    cid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "coop"
    coop = {"id": cid, "name": name, "role": "admin"}
    request.session["coop"] = coop
    storage.save_user(user["sub"], {"coop_id": cid, "coop_name": name, "role": "admin"})
    return {"coop": coop}

@app.get("/api/lots")
def api_lots(request: Request):
    ctx = auth.require_coop(request)
    lots = storage.list_lots(ctx["coop"]["id"])
    lots = sorted(lots, key=lambda d: d.get("created_at", ""), reverse=True)
    out = [{"lot_id": d.get("lot_id"), "producer": d.get("producer_name"),
            "commodity": d.get("commodity"), "overall_risk": d.get("overall_risk", ""),
            "created_at": d.get("created_at", ""), "captured_by": d.get("captured_by", "")} for d in lots]
    return {"coop": ctx["coop"], "lots": out}

# ---- Envíos / consignaciones (agregar N lotes en una sola DDS consolidada) ----

class ConsignmentIn(BaseModel):
    name: str = ""
    commodity: str = ""
    destination: str = ""
    buyer: str = ""
    lang: str = "es"
    lot_ids: list[str] = []

@app.post("/api/consignments")
def create_consignment(c: ConsignmentIn, request: Request):
    ctx = auth.require_coop(request)
    ids = [x for x in (c.lot_ids or []) if x]
    if not ids:
        raise HTTPException(400, "Selecciona al menos un lote")
    commodities = set(); countries = set()
    for lid in ids:
        lot = _load_owned(lid, ctx)      # valida que el lote sea de esta cooperativa
        if lot.commodity: commodities.add(lot.commodity.lower())
        countries.add(lot.country or "PE")
    # La DDS es por operador / producto / país: no se pueden mezclar en un mismo envío.
    if len(commodities) > 1:
        raise HTTPException(400, "Un envío debe ser de un solo producto (la DDS es por producto). "
                                 "Separa café y cacao en envíos distintos.")
    if len(countries) > 1:
        raise HTTPException(400, "Un envío debe ser de un solo país de producción.")
    commodity = c.commodity or (next(iter(commodities)) if len(commodities) == 1 else "")
    cid = "ENV-" + uuid.uuid4().hex[:8].upper()
    cons = Consignment(cid, ctx["coop"]["id"], (c.name or cid), commodity,
                       c.destination, c.buyer, ids, _now(), ctx["user"]["email"],
                       {"lang": c.lang or "es"})
    storage.save_consignment(cons)
    return {"consignment_id": cid, "name": cons.name}

@app.get("/api/consignments")
def api_consignments(request: Request):
    ctx = auth.require_coop(request)
    cons = storage.list_consignments(ctx["coop"]["id"])
    cons = sorted(cons, key=lambda d: d.get("created_at", ""), reverse=True)
    return {"coop": ctx["coop"], "consignments": [_consignment_summary(d) for d in cons]}

def _consignment_summary(d):
    lot_ids = d.get("lot_ids", [])
    risks = []; nplots = 0; total = 0.0; producers = set(); regions = set()
    for lid in lot_ids:
        ld = storage.load_lot(lid)
        if not ld:
            continue
        risks.append(ld.get("overall_risk", ""))
        nplots += len(ld.get("plots", []))
        total += dossier.parse_qty_kg(ld.get("quantity", ""))
        if ld.get("producer_name"): producers.add(ld["producer_name"])
        if ld.get("region"): regions.add(ld["region"])
    verdict = "high" if "high" in risks else ("review" if "review" in risks else "negligible")
    processed = bool(risks) and all(bool(r) for r in risks)
    return {"consignment_id": d.get("consignment_id"), "name": d.get("name", ""),
            "commodity": d.get("commodity", ""), "destination": d.get("destination", ""),
            "buyer": d.get("buyer", ""), "n_lots": len(lot_ids), "n_plots": nplots,
            "total_kg": round(total, 1), "producers": len(producers), "regions": len(regions),
            "verdict": verdict, "processed": processed, "created_at": d.get("created_at", "")}

def _load_owned_cons(cid, ctx):
    d = storage.load_consignment(cid)
    if not d:
        raise HTTPException(404, "Envío no encontrado")
    if d.get("coop_id") and d["coop_id"] != ctx["coop"]["id"]:
        raise HTTPException(403, "Este envío pertenece a otra cooperativa")
    return d

def _cached_findings(lot_id):
    """Reusa los findings ya calculados al procesar el lote (evita re-verificar deforestación por red)."""
    d = storage.load_lot(lot_id)
    fr = d.get("findings") if d else None
    if fr:
        try:
            return [DeforestationFinding(x["plot_id"], x["risk"], x.get("loss_after_cutoff", False),
                                         x.get("detail", "")) for x in fr]
        except Exception:
            return None
    return None

def _build_consignment_outputs(d, force=False):
    """Construye (o reutiliza) el dossier consolidado + geojson del envío."""
    out = os.path.join(config.DATA_DIR, "dossiers")
    cid = d["consignment_id"]
    pdf = os.path.join(out, f"{cid}_dossier.pdf"); gj = os.path.join(out, f"{cid}.geojson")
    if not force and os.path.exists(pdf) and os.path.exists(gj):
        return pdf, gj
    items = []
    for lid in d.get("lot_ids", []):
        try:
            lot = _load(lid)
        except HTTPException:
            continue
        findings = _cached_findings(lid) or deforestation.check_plots(lot)  # cache-first (rápido)
        items.append((lot, findings))
    if not items:
        raise HTTPException(404, "El envío no tiene lotes válidos")
    lang = (d.get("extra") or {}).get("lang", "es")
    gj = dossier.build_consignment_geojson(d, items, out)
    pdf = dossier.build_consignment_pdf(d, items, out, lang)
    try:
        storage.save_blob(cid, "dossier.pdf", open(pdf, "rb").read())
        storage.save_blob(cid, "data.geojson", open(gj, "rb").read())
    except Exception:
        pass
    try:
        notarize.notarize(cid, pdf)
    except Exception:
        pass
    return pdf, gj

@app.get("/consignments/{cid}/dossier")
def consignment_dossier(cid: str, request: Request):
    d = _load_owned_cons(cid, auth.require_coop(request))
    out = os.path.join(config.DATA_DIR, "dossiers")
    p = os.path.join(out, f"{cid}_dossier.pdf")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/pdf", filename=f"{cid}_dossier.pdf")
    blob = storage.load_blob(cid, "dossier.pdf")
    if blob:
        return Response(blob, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{cid}_dossier.pdf"'})
    try:
        p, _ = _build_consignment_outputs(d)
    except HTTPException:
        raise
    except Exception as e:
        print("consignment dossier error:", repr(e))
        raise HTTPException(503, "No se pudo generar el dossier del envío; reintenta en unos segundos.")
    return FileResponse(p, media_type="application/pdf", filename=f"{cid}_dossier.pdf")

@app.get("/consignments/{cid}/geojson")
def consignment_geojson(cid: str, request: Request):
    d = _load_owned_cons(cid, auth.require_coop(request))
    out = os.path.join(config.DATA_DIR, "dossiers")
    p = os.path.join(out, f"{cid}.geojson")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/geo+json", filename=f"{cid}.geojson")
    blob = storage.load_blob(cid, "data.geojson")
    if blob:
        return Response(blob, media_type="application/geo+json",
                        headers={"Content-Disposition": f'inline; filename="{cid}.geojson"'})
    try:
        _, p = _build_consignment_outputs(d)
    except HTTPException:
        raise
    except Exception as e:
        print("consignment geojson error:", repr(e))
        raise HTTPException(503, "No se pudo generar el GeoJSON del envío; reintenta en unos segundos.")
    return FileResponse(p, media_type="application/geo+json", filename=f"{cid}.geojson")

@app.post("/consignments/{cid}/regenerate")
def consignment_regenerate(cid: str, request: Request):
    """Reconstruye el dossier consolidado con el estado más reciente de los lotes (invalida cache)."""
    d = _load_owned_cons(cid, auth.require_coop(request))
    try:
        _build_consignment_outputs(d, force=True)
    except HTTPException:
        raise
    except Exception as e:
        print("consignment regenerate error:", repr(e))
        raise HTTPException(503, "No se pudo regenerar el envío; reintenta en unos segundos.")
    storage.merge_consignment(cid, {"generated_at": _now()})
    return {"ok": True, **_consignment_summary(d)}

@app.get("/share/c/{cid}/dossier")
def share_consignment_dossier(cid: str):
    blob = storage.load_blob(cid, "dossier.pdf")
    if blob:
        return Response(blob, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{cid}_dossier.pdf"'})
    raise HTTPException(404, "Dossier del envío no disponible todavía.")

@app.get("/share/c/{cid}/geojson")
def share_consignment_geojson(cid: str):
    blob = storage.load_blob(cid, "data.geojson")
    if blob:
        return Response(blob, media_type="application/geo+json",
                        headers={"Content-Disposition": f'inline; filename="{cid}.geojson"'})
    raise HTTPException(404, "GeoJSON del envío no disponible todavía.")

@app.get("/verificar")
def verificar():
    return _page("verificar.html")

@app.get("/api/verify")
def api_verify(lot: str = ""):
    rec = storage.get_notary(lot) if lot else None
    if not rec:
        return {"found": False}
    return {"found": True, "lot_id": rec.get("lot_id"), "sha256": rec.get("sha256"),
            "algo": rec.get("algo", "SHA-256"), "created_at": rec.get("created_at", ""),
            "anchor": rec.get("anchor", "")}

# ---- Enlace público compartible (para WhatsApp / comprador) ----

@app.get("/share/{lot_id}/dossier")
def share_dossier(lot_id: str):
    blob = storage.load_blob(lot_id, "dossier.pdf")
    if blob:
        return Response(blob, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}_dossier.pdf"'})
    raise HTTPException(404, "Dossier no disponible todavía.")

@app.get("/share/{lot_id}/geojson")
def share_geojson(lot_id: str):
    blob = storage.load_blob(lot_id, "data.geojson")
    if blob:
        return Response(blob, media_type="application/geo+json",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}.geojson"'})
    raise HTTPException(404, "GeoJSON no disponible todavía.")

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
    extra: dict | None = None              # legalidad + comprador (opcional)
    photo_base64: str | None = None

@app.post("/capture")
def capture(c: CaptureIn, request: Request):
    ctx = auth.require_coop(request)
    lot_id = "LOT-" + uuid.uuid4().hex[:8].upper()
    if c.points and len(c.points) >= 3:
        pts = [GeoPoint(float(p["lat"]), float(p["lon"])) for p in c.points]
    else:
        pts = [GeoPoint(c.lat, c.lon)]
    plot = Plot("P1", pts, c.area_ha)
    lot = Lot(lot_id, c.producer, ctx["coop"]["name"], c.commodity, "PE", c.region, [plot], "", "", c.quantity,
              ctx["coop"]["id"], ctx["user"]["email"], _now(), c.extra or {})
    if c.photo_base64:
        try:
            data = c.photo_base64.split(",", 1)[-1]
            raw = base64.b64decode(data)
            if len(raw) > 4_000_000:           # tope de tamaño (la captura ya reduce a ~640px)
                raise ValueError("photo too large")
            up = os.path.join(config.DATA_DIR, "uploads"); os.makedirs(up, exist_ok=True)
            with open(os.path.join(up, f"{lot_id}.jpg"), "wb") as f:
                f.write(raw)
            storage.save_blob(lot_id, "photo.jpg", raw)   # durable: para que aparezca en el dossier
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
def lead(l: LeadIn, request: Request):
    if not _throttle(request.client.host if request.client else "", "lead", 10, 60):
        raise HTTPException(429, "Demasiadas solicitudes; intenta en un momento.")
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
def process(lot_id: str, request: Request):
    ctx = auth.require_coop(request)
    lot = _load_owned(lot_id, ctx)
    findings = deforestation.check_plots(lot)
    lang = (lot.extra or {}).get("lang", "es") if isinstance(lot.extra, dict) else "es"
    if lang == "en":
        narrative = _fallback_narrative(lot, findings, "en")
    else:
        try: narrative = gemini.generate_dossier_narrative(lot, findings) or _fallback_narrative(lot, findings, "es")
        except Exception: narrative = _fallback_narrative(lot, findings, "es")
    out = os.path.join(config.DATA_DIR, "dossiers")
    gj = dossier.build_geojson(lot, out)
    pdf = dossier.build_pdf(lot, findings, narrative, "", out, lang, photo_path=_photo_path(lot_id, out))
    storage.upload_file(gj); storage.upload_file(pdf)
    risk = dossier.overall_risk(findings)
    try:
        storage.save_blob(lot_id, "dossier.pdf", open(pdf, "rb").read())
        storage.save_blob(lot_id, "data.geojson", open(gj, "rb").read())
        storage.merge_lot(lot_id, {"overall_risk": risk, "processed_at": _now(),
                                   "findings": [f.__dict__ for f in findings]})  # cache para envíos
    except Exception:
        pass
    geom_issues = []
    for pl in lot.plots: geom_issues += geo.geometry_issues(pl)
    notary = notarize.notarize(lot_id, pdf)
    return {"lot_id": lot_id, "overall_risk": risk, "geometry_issues": geom_issues,
            "notary": {"sha256": notary.get("sha256"), "verify_url": config.PUBLIC_BASE_URL + "/verificar?lot=" + lot_id},
            "geojson": gj, "pdf": pdf, "findings": [f.__dict__ for f in findings]}

def _fallback_narrative(lot, findings, lang="es"):
    """Resumen determinista (sin Gemini) por si la IA no responde al regenerar."""
    n = len(findings); high = sum(1 for f in findings if f.risk == "high")
    rev = sum(1 for f in findings if f.risk == "review"); clean = n - high - rev
    if lang == "en":
        s = (f"{n} plot(s) of producer {lot.producer_name or '—'} ({lot.cooperative or 'cooperative'}) were assessed, "
             f"each cross-checked against satellite deforestation sources with a 31 December 2020 cut-off. "
             f"Result: {clean} with no loss, {rev} to review and {high} with detected deforestation. ")
        s += ("Flagged plots must be excluded or substantiated before the declaration."
              if high else "No forest loss after the cut-off was detected in the assessed plots.")
        return s
    s = (f"Se evaluaron {n} parcela(s) del productor {lot.producer_name or '—'} "
         f"({lot.cooperative or 'cooperativa'}), cruzando cada una contra fuentes satelitales de "
         f"deforestación con fecha de corte 31 de diciembre de 2020. "
         f"Resultado: {clean} sin pérdida, {rev} a revisar y {high} con deforestación detectada. ")
    s += ("Las parcelas marcadas deben excluirse o sustentarse antes de la declaración."
          if high else "No se detectó pérdida de bosque posterior al corte en las parcelas evaluadas.")
    return s

def _ensure_outputs(lot_id: str):
    """Regenera dossier+geojson desde el lote durable si faltan en disco (instancias efimeras de Cloud Run)."""
    out = os.path.join(config.DATA_DIR, "dossiers")
    pdf = os.path.join(out, f"{lot_id}_dossier.pdf")
    gj  = os.path.join(out, f"{lot_id}.geojson")
    if os.path.exists(pdf) and os.path.exists(gj):
        return pdf, gj
    lot = _load(lot_id)
    findings = deforestation.check_plots(lot)
    lang = (lot.extra or {}).get("lang", "es") if isinstance(lot.extra, dict) else "es"
    if lang == "en":
        narrative = _fallback_narrative(lot, findings, "en")
    else:
        try:
            narrative = gemini.generate_dossier_narrative(lot, findings) or _fallback_narrative(lot, findings, "es")
        except Exception as e:
            print("regen narrative error:", repr(e)); narrative = _fallback_narrative(lot, findings, "es")
    gj = dossier.build_geojson(lot, out)
    pdf = dossier.build_pdf(lot, findings, narrative, "", out, lang, photo_path=_photo_path(lot_id, out))
    try:
        storage.save_blob(lot_id, "dossier.pdf", open(pdf, "rb").read())
        storage.save_blob(lot_id, "data.geojson", open(gj, "rb").read())
    except Exception:
        pass
    try: notarize.notarize(lot_id, pdf)
    except Exception: pass
    return pdf, gj

@app.get("/lots/{lot_id}/dossier")
def get_dossier(lot_id: str, request: Request):
    _load_owned(lot_id, auth.require_coop(request))
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}_dossier.pdf")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/pdf", filename=f"{lot_id}_dossier.pdf")
    blob = storage.load_blob(lot_id, "dossier.pdf")
    if blob:
        return Response(blob, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}_dossier.pdf"'})
    try:
        p, _ = _ensure_outputs(lot_id)
    except HTTPException:
        raise
    except Exception as e:
        print("dossier regen error:", repr(e))
        raise HTTPException(503, "No se pudo generar el dossier; reintenta en unos segundos.")
    return FileResponse(p, media_type="application/pdf", filename=f"{lot_id}_dossier.pdf")

@app.get("/lots/{lot_id}/geojson")
def get_geojson(lot_id: str, request: Request):
    _load_owned(lot_id, auth.require_coop(request))
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}.geojson")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/geo+json", filename=f"{lot_id}.geojson")
    blob = storage.load_blob(lot_id, "data.geojson")
    if blob:
        return Response(blob, media_type="application/geo+json",
                        headers={"Content-Disposition": f'inline; filename="{lot_id}.geojson"'})
    try:
        lot = _load(lot_id)
        gj = dossier.build_geojson(lot, os.path.join(config.DATA_DIR, "dossiers"))
    except HTTPException:
        raise
    except Exception as e:
        print("geojson build error:", repr(e))
        raise HTTPException(503, "No se pudo generar el GeoJSON; reintenta en unos segundos.")
    return FileResponse(gj, media_type="application/geo+json", filename=f"{lot_id}.geojson")

def _load(lot_id: str) -> Lot:
    d = storage.load_lot(lot_id)
    if not d:
        raise HTTPException(404, "Lote no encontrado")
    plots = [Plot(p["plot_id"], [GeoPoint(**pt) for pt in p["points"]], p.get("area_ha")) for p in d["plots"]]
    return Lot(d["lot_id"], d["producer_name"], d["cooperative"], d["commodity"],
               d.get("country", "PE"), d.get("region", ""), plots,
               d.get("harvest_season", ""), d.get("raw_notes", ""), d.get("quantity", ""),
               d.get("coop_id", ""), d.get("captured_by", ""), d.get("created_at", ""), d.get("extra", {}))

def _load_owned(lot_id: str, ctx: dict) -> Lot:
    lot = _load(lot_id)
    if lot.coop_id and lot.coop_id != ctx["coop"]["id"]:
        raise HTTPException(403, "Este lote pertenece a otra cooperativa")
    return lot
