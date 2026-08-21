import os, uuid, json, base64, datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, Response, RedirectResponse
from pydantic import BaseModel
from . import gemini, deforestation, dossier, storage, config, auth, geo, notarize, copilot, scoring, portability, whatsapp, monitor, importer
from .models import Lot, Plot, GeoPoint, Consignment, DeforestationFinding

app = FastAPI(title="Origen - EUDR + Export Copilot")
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET,
                   same_site="lax", max_age=60 * 60 * 24 * 14)
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

def _now(): return datetime.datetime.utcnow().isoformat() + "Z"

def log(event, **kw):
    """Log estructurado en JSON (legible por Cloud Logging)."""
    try:
        print(json.dumps({"event": event, "ts": _now(), **kw}, ensure_ascii=False, default=str))
    except Exception:
        print(event, kw)

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

class InviteIn(BaseModel):
    email: str

class ChatIn(BaseModel):
    question: str
    lot_id: str | None = None

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
    else:
        inv = storage.find_coop_by_member(user.get("email", ""))   # auto-unir si fue invitado
        if inv:
            request.session["coop"] = {"id": inv["id"], "name": inv.get("name", ""), "role": "tecnico"}
            storage.save_user(user["sub"], {"coop_id": inv["id"], "coop_name": inv.get("name", ""), "role": "tecnico"})
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
    storage.save_coop({"id": cid, "name": name, "admin_email": user.get("email", ""),
                       "members": [user.get("email", "")], "created_at": _now()})
    return {"coop": coop}

@app.post("/api/coop/invite")
def api_coop_invite(inv: InviteIn, request: Request):
    ctx = auth.require_coop(request)
    if ctx["coop"].get("role") != "admin":
        raise HTTPException(403, "Solo el administrador de la cooperativa puede invitar")
    email = (inv.email or "").strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Pon un email válido")
    storage.add_coop_member(ctx["coop"]["id"], email)
    return {"ok": True, "email": email}

@app.get("/api/coop/team")
def api_coop_team(request: Request):
    ctx = auth.require_coop(request)
    coop = storage.get_coop(ctx["coop"]["id"]) or {}
    admin = coop.get("admin_email", "")
    members = coop.get("members", [])
    if not members and ctx["user"].get("email"):    # auto-sana cooperativas creadas antes de esta función
        admin = admin or ctx["user"]["email"]; members = [admin]
        storage.save_coop({"id": ctx["coop"]["id"], "name": ctx["coop"].get("name", ""),
                           "admin_email": admin, "members": members, "created_at": _now()})
    team = [{"email": m, "role": ("admin" if m == admin else "tecnico")} for m in members]
    return {"role": ctx["coop"].get("role", "tecnico"), "admin": admin, "members": team}

@app.get("/api/lots")
def api_lots(request: Request):
    ctx = auth.require_coop(request)
    lots = storage.list_lots(ctx["coop"]["id"])
    lots = sorted(lots, key=lambda d: d.get("created_at", ""), reverse=True)
    out = [{"lot_id": d.get("lot_id"), "producer": d.get("producer_name"),
            "commodity": d.get("commodity"), "overall_risk": d.get("overall_risk", ""),
            "created_at": d.get("created_at", ""), "captured_by": d.get("captured_by", ""),
            "volume_flag": bool(d.get("volume_flag"))} for d in lots]
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
    log("consignment_create", consignment_id=cid, coop=ctx["coop"]["id"], lots=len(ids), commodity=commodity)
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

@app.get("/api/lots.csv")
def lots_csv(request: Request):
    ctx = auth.require_coop(request)
    lots = sorted(storage.list_lots(ctx["coop"]["id"]), key=lambda d: d.get("created_at", ""), reverse=True)
    import io, csv
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["lot_id", "producer", "commodity", "region", "quantity_kg", "overall_risk", "n_plots", "captured_by", "created_at"])
    for d in lots:
        w.writerow([d.get("lot_id", ""), d.get("producer_name", ""), d.get("commodity", ""), d.get("region", ""),
                    d.get("quantity", ""), d.get("overall_risk", ""), len(d.get("plots", [])),
                    d.get("captured_by", ""), d.get("created_at", "")])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="origen_lotes.csv"'})

@app.get("/api/consignments.csv")
def consignments_csv(request: Request):
    ctx = auth.require_coop(request)
    cons = sorted(storage.list_consignments(ctx["coop"]["id"]), key=lambda d: d.get("created_at", ""), reverse=True)
    import io, csv
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["consignment_id", "name", "commodity", "destination", "buyer", "n_lots", "n_plots", "total_kg", "verdict", "created_at"])
    for d in cons:
        s = _consignment_summary(d)
        w.writerow([s["consignment_id"], s["name"], s["commodity"], s["destination"], s["buyer"],
                    s["n_lots"], s["n_plots"], s["total_kg"], s["verdict"], s["created_at"]])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="origen_envios.csv"'})

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

# ---- Copiloto de cumplimiento (Gemini) ----

@app.post("/lots/{lot_id}/copilot")
def lot_copilot(lot_id: str, request: Request):
    ctx = auth.require_coop(request)
    lot = _load_owned(lot_id, ctx)
    findings = _cached_findings(lot_id) or deforestation.check_plots(lot)
    out = copilot.analyze_lot(lot, findings)
    log("copilot_analyze", lot_id=lot_id, coop=ctx["coop"]["id"])
    return out

@app.post("/copilot/chat")
def copilot_chat(c: ChatIn, request: Request):
    ctx = auth.require_coop(request)
    if not (c.question or "").strip():
        raise HTTPException(400, "Escribe una pregunta")
    if not _throttle(request.client.host if request.client else "", "copilot", 30, 60):
        raise HTTPException(429, "Demasiadas consultas; espera un momento.")
    lot = findings = None
    if c.lot_id:
        try:
            lot = _load_owned(c.lot_id, ctx)
            findings = _cached_findings(c.lot_id)
        except HTTPException:
            lot = None
    return {"answer": copilot.chat(c.question.strip(), lot, findings)}

# ---- Simulador what-if de segregación + score de confianza ----

class WhatIfIn(BaseModel):
    exclude: list[str] = []

@app.get("/lots/{lot_id}/score")
def lot_score(lot_id: str, request: Request):
    ctx = auth.require_coop(request)
    lot = _load_owned(lot_id, ctx)
    findings = _cached_findings(lot_id) or deforestation.check_plots(lot)
    suggested = scoring.suggest_exclusions(findings)
    log("score", lot_id=lot_id, coop=ctx["coop"]["id"])
    return {
        "score": scoring.confidence_score(lot, findings),
        "suggest_exclude": suggested,
        "simulation": scoring.simulate(lot, findings, suggested),
    }

@app.post("/lots/{lot_id}/whatif")
def lot_whatif(lot_id: str, body: WhatIfIn, request: Request):
    ctx = auth.require_coop(request)
    lot = _load_owned(lot_id, ctx)
    findings = _cached_findings(lot_id) or deforestation.check_plots(lot)
    return scoring.simulate(lot, findings, body.exclude)

def _consignment_items(d):
    """[(lot, findings)] del envío (cache-first), reutilizando la lógica del dossier."""
    items = []
    for lid in d.get("lot_ids", []):
        try:
            lot = _load(lid)
        except HTTPException:
            continue
        items.append((lot, _cached_findings(lid) or deforestation.check_plots(lot)))
    if not items:
        raise HTTPException(404, "El envío no tiene lotes válidos")
    return items

@app.get("/consignments/{cid}/whatif")
def cons_whatif_default(cid: str, request: Request):
    d = _load_owned_cons(cid, auth.require_coop(request))
    items = _consignment_items(d)
    suggested = scoring.suggest_exclusions_consignment(items)
    return {"suggest_exclude": suggested,
            "simulation": scoring.simulate_consignment(items, suggested)}

@app.post("/consignments/{cid}/whatif")
def cons_whatif(cid: str, body: WhatIfIn, request: Request):
    d = _load_owned_cons(cid, auth.require_coop(request))
    items = _consignment_items(d)
    return scoring.simulate_consignment(items, body.exclude)

@app.post("/consignments/{cid}/segregate")
def cons_segregate(cid: str, body: WhatIfIn, request: Request):
    """Aplica una segregación DE VERDAD: quita los lotes excluidos del envío y regenera
    el dossier consolidado (el what-if solo simula; esto persiste)."""
    ctx = auth.require_coop(request)
    d = _load_owned_cons(cid, ctx)
    exclude = set(body.exclude or [])
    keep = [l for l in d.get("lot_ids", []) if l not in exclude]
    if not keep:
        raise HTTPException(400, "La exclusión dejaría el envío vacío; excluye menos lotes.")
    if len(keep) == len(d.get("lot_ids", [])):
        return {"ok": True, "changed": False, **_consignment_summary(d)}
    storage.merge_consignment(cid, {"lot_ids": keep})
    d["lot_ids"] = keep
    try:
        _build_consignment_outputs(d, force=True)   # regenera dossier + geojson ya segregados
    except HTTPException:
        raise
    except Exception as e:
        print("segregate regenerate error:", repr(e))
    log("segregate", consignment_id=cid, coop=ctx["coop"]["id"], excluded=len(exclude))
    return {"ok": True, "changed": True, "excluded": sorted(exclude & set(exclude)), **_consignment_summary(d)}

class SubstantiateIn(BaseModel):
    note: str = ""

@app.post("/lots/{lot_id}/substantiate")
def lot_substantiate(lot_id: str, body: SubstantiateIn, request: Request):
    """Registra la sustentación de un lote observado/en revisión (la alternativa a excluirlo):
    queda en el expediente del lote con autor y fecha, y aparece disponible para el dossier."""
    ctx = auth.require_coop(request)
    _load_owned(lot_id, ctx)
    note = (body.note or "").strip()
    if not note:
        raise HTTPException(400, "Escribe la justificación de la sustentación")
    d = storage.load_lot(lot_id) or {}
    extra = d.get("extra") or {}
    extra["substantiation"] = {"note": note[:2000], "by": ctx["user"].get("email", ""), "at": _now()}
    storage.merge_lot(lot_id, {"extra": extra})
    log("substantiate", lot_id=lot_id, coop=ctx["coop"]["id"])
    return {"ok": True, "lot_id": lot_id, "substantiation": extra["substantiation"]}

@app.get("/verificar")
def verificar():
    return _page("verificar.html")

def _load_ots(lot_id):
    """Lee la prueba .ots (disco junto al PDF, o blob durable). None si no existe."""
    p = os.path.join(config.DATA_DIR, "dossiers", f"{lot_id}_dossier.ots")
    if os.path.exists(p):
        try:
            return open(p, "rb").read()
        except Exception:
            pass
    return storage.load_blob(lot_id, "dossier.ots")

@app.get("/api/verify")
def api_verify(lot: str = ""):
    rec = storage.get_notary(lot) if lot else None
    if not rec:
        return {"found": False}
    out = {"found": True, "lot_id": rec.get("lot_id"), "sha256": rec.get("sha256"),
           "algo": rec.get("algo", "SHA-256"), "created_at": rec.get("created_at", ""),
           "anchor": rec.get("anchor", "")}
    if rec.get("anchor") == "opentimestamps":
        ots = _load_ots(lot)
        if ots:
            out["ots_available"] = True
            out["ots_url"] = "/verificar/" + lot + ".ots"
            st = notarize.ots_status(ots)
            if st:
                out["ots"] = {"anchored": st["anchored"], "bitcoin_blocks": st["bitcoin_blocks"],
                              "pending": len(st["pending_calendars"])}
    return out

@app.get("/verificar/{lot_id}.ots")
def download_ots(lot_id: str):
    ots = _load_ots(lot_id)
    if ots:
        return Response(ots, media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{lot_id}.ots"'})
    raise HTTPException(404, "Prueba .ots no disponible")

@app.post("/api/verify/upgrade")
def api_verify_upgrade(lot: str = ""):
    ots = _load_ots(lot) if lot else None
    if not ots:
        raise HTTPException(404, "No hay prueba .ots para este registro")
    up = notarize.ots_upgrade(ots)
    if up:
        try:
            storage.save_blob(lot, "dossier.ots", up)
            with open(os.path.join(config.DATA_DIR, "dossiers", f"{lot}_dossier.ots"), "wb") as f:
                f.write(up)
        except Exception:
            pass
    st = notarize.ots_status(up or ots)
    return {"upgraded": bool(up), "anchored": bool(st and st["anchored"]),
            "bitcoin_blocks": (st or {}).get("bitcoin_blocks", [])}

# ---- Importación masiva: la coop que YA tiene la georreferencia sube su archivo ----

@app.get("/api/import/template")
def import_template():
    return Response(importer.TEMPLATE_CSV, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="origen_plantilla_parcelas.csv"'})

@app.post("/api/import")
async def api_import(request: Request, file: UploadFile = File(...)):
    ctx = auth.require_coop(request)
    data = await file.read()
    if len(data) > 8_000_000:
        raise HTTPException(413, "Archivo muy grande (máx. 8 MB)")
    try:
        rows, errs = importer.parse(data, file.filename or "")
    except Exception as e:
        print("import parse error:", repr(e))
        raise HTTPException(400, "No pude leer el archivo. Usa la plantilla CSV/Excel o un GeoJSON.")
    if not rows:
        raise HTTPException(400, errs[0] if errs else "No encontré filas válidas en el archivo.")
    if ctx["coop"]["id"] == _DEMO_COOP["id"]:            # candado demo: 1 lote propio, 1 dossier
        if _demo_own_lots(ctx["coop"]["id"]) >= 1:
            raise HTTPException(403, "El entorno demo permite crear 1 lote propio (ya lo usaste). "
                                     "Contáctanos para activar la cuenta de tu organización.")
        if len(rows) > 1:
            rows = rows[:1]
            errs.append("Entorno demo: se importó solo la primera fila (1 lote de prueba).")
    created = importer.create_lots(rows, ctx["coop"]["id"], ctx["coop"]["name"], ctx["user"].get("email", ""))
    log("import", coop=ctx["coop"]["id"], rows=len(rows), lots=len(created), errors=len(errs))
    return {"ok": True, "rows": len(rows), "lots_created": len(created),
            "lots": created[:50], "errors": errs[:20]}

# ---- Acceso demo por link único (para prospectos: sin login, coop sandbox precargada) ----

_DEMO_COOP = {"id": "demo-origen", "name": "Cooperativa Demo Origen"}

def _demo_own_lots(coop_id):
    """Lotes creados por el visitante en la coop demo (excluye los LOT-DEMO* precargados del tour)."""
    return sum(1 for l in storage.list_lots(coop_id)
               if not str(l.get("lot_id", "")).startswith("LOT-DEMO"))

def _ensure_demo_data():
    """Crea la coop demo + 3 lotes (limpio / revisar / observado) + 1 envío, una sola vez.
    Findings precargados (deterministas): la demo no depende de servicios externos."""
    if storage.load_lot("LOT-DEMO01"):
        return
    storage.save_coop({"id": _DEMO_COOP["id"], "name": _DEMO_COOP["name"],
                       "admin_email": "demo@origen.pe", "members": ["demo@origen.pe"], "created_at": _now()})
    demo = [
        ("LOT-DEMO01", "Ana Quispe", "San Martín",
         [GeoPoint(-6.478, -76.372), GeoPoint(-6.478, -76.368), GeoPoint(-6.474, -76.368), GeoPoint(-6.474, -76.372)],
         5.2, "1,800 kg", "negligible",
         [{"plot_id": "P1", "risk": "negligible", "loss_after_cutoff": False,
           "detail": "Sin pérdida de cobertura posterior al corte (31-dic-2020) en las 4 fuentes."}],
         {"legality": {"title": "Título N.º 04512-SM", "env": "Fuera de ANP; sin cambio de uso", "labor": "Conforme"}}),
        ("LOT-DEMO02", "Beto Ríos", "Cusco",
         [GeoPoint(-12.869, -72.941)], 2.0, "900 kg", "review",
         [{"plot_id": "P1", "risk": "review", "loss_after_cutoff": False,
           "detail": "Alerta reciente a ~60 m del límite de la parcela; verificar en campo antes de exportar."}], {}),
        ("LOT-DEMO03", "Carla Díaz", "Amazonas",
         [GeoPoint(-5.751, -78.442)], 3.1, "1,200 kg", "high",
         [{"plot_id": "P1", "risk": "high", "loss_after_cutoff": True,
           "detail": "Pérdida de cobertura detectada en 2023 dentro de la parcela (Hansen + alertas integradas)."}], {}),
    ]
    for lid, prod, region, pts, ha, qty, risk, findings, extra in demo:
        lot = Lot(lid, prod, _DEMO_COOP["name"], "coffee", "PE", region,
                  [Plot("P1", pts, ha)], "", "", qty, _DEMO_COOP["id"], "demo@origen.pe", _now(), extra)
        storage.save_lot(lot)
        storage.merge_lot(lid, {"overall_risk": risk, "findings": findings, "volume_flag": False})
    storage.save_consignment(Consignment(
        "ENV-DEMO01", _DEMO_COOP["id"], "Contenedor Taipéi #1", "coffee",
        "Taipéi, TW", "Importadora Formosa Ltd.",
        ["LOT-DEMO01", "LOT-DEMO02", "LOT-DEMO03"], _now(), "demo@origen.pe", {"lang": "es"}))

@app.get("/demo")
def demo_access(request: Request, key: str = ""):
    if not config.DEMO_KEY or key != config.DEMO_KEY:
        raise HTTPException(404, "No encontrado")
    try:
        _ensure_demo_data()
    except Exception as e:
        print("demo seed error:", repr(e))
    request.session["user"] = {"sub": "demo-user", "email": "demo@origen.pe",
                               "name": "Visitante (demo)", "picture": ""}
    request.session["coop"] = {"id": _DEMO_COOP["id"], "name": _DEMO_COOP["name"], "role": "tecnico"}
    log("demo_access", ip=(request.client.host if request.client else ""))
    return RedirectResponse("/panel")

# ---- WhatsApp (Cloud API): consulta de estado por el canal de las coops ----

def _verdict_es(v):
    return {"high": "observado — requiere acción", "review": "a revisar",
            "negligible": "en orden (sin deforestación)"}.get(v, "en proceso")

def _wa_reply(text):
    """Respuesta a un mensaje entrante. Solo lecturas seguras por código; nunca ejecuta órdenes del texto."""
    import re
    m = re.search(r"(LOT-[A-Za-z0-9]+|ENV-[A-Za-z0-9]+)", (text or "").upper())
    if m:
        code = m.group(1)
        if code.startswith("ENV-"):
            d = storage.load_consignment(code)
            if d:
                s = _consignment_summary(d)
                return (f"Envío {s['name'] or code}: {_verdict_es(s['verdict'])}.\n"
                        f"{s['n_lots']} lotes · {s['n_plots']} parcelas · {s['total_kg']:.0f} kg\n"
                        f"{config.PUBLIC_BASE_URL}/s/c/{code}")
            return f"No encontré el envío {code}."
        d = storage.load_lot(code)
        if d:
            return (f"Lote {code} ({d.get('producer_name','')}): {_verdict_es(d.get('overall_risk',''))}.\n"
                    f"{config.PUBLIC_BASE_URL}/s/{code}")
        return f"No encontré el lote {code}."
    return ("Hola, soy Origen 🌱. Envíame un código de lote (LOT-…) o de envío (ENV-…) y te doy su "
            "estado EUDR.\nPanel: " + config.PUBLIC_BASE_URL + "/panel")

@app.get("/webhooks/whatsapp")
def wa_verify(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN:
        return Response(p.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(403, "verify failed")

@app.post("/webhooks/whatsapp")
async def wa_incoming(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return {"ok": True}
    for msg in whatsapp.parse_messages(payload):
        frm = msg.get("from"); txt = (msg.get("text") or "").strip()
        if frm and txt:
            whatsapp.send_text(frm, _wa_reply(txt))
    return {"ok": True}

# ---- Monitoreo continuo + alertas ----

@app.post("/cron/monitor")
def cron_monitor(request: Request):
    tok = request.headers.get("X-Cron-Token", "") or request.query_params.get("token", "")
    if not config.CRON_TOKEN or tok != config.CRON_TOKEN:
        raise HTTPException(403, "forbidden")
    res = monitor.run_monitor()
    log("cron_monitor", checked=res["checked"], alerts=res["alerts"])
    return {"checked": res["checked"], "alerts": res["alerts"]}

@app.get("/api/alerts")
def api_alerts(request: Request):
    ctx = auth.require_coop(request)
    al = sorted(storage.list_alerts(ctx["coop"]["id"]), key=lambda a: a.get("created_at", ""), reverse=True)
    return {"alerts": al}

# ---- Módulo de legalidad (checklist + documentos por lote) ----

class LegalityIn(BaseModel):
    title: str = ""
    env: str = ""
    labor: str = ""
    docs: list[dict] | None = None     # [{name, base64}]

@app.get("/api/lots/{lot_id}/legality")
def get_legality(lot_id: str, request: Request):
    ctx = auth.require_coop(request)
    _load_owned(lot_id, ctx)
    d = storage.load_lot(lot_id) or {}
    return {"legality": (d.get("extra") or {}).get("legality", {})}

@app.post("/lots/{lot_id}/legality")
def set_legality(lot_id: str, body: LegalityIn, request: Request):
    ctx = auth.require_coop(request)
    _load_owned(lot_id, ctx)
    d = storage.load_lot(lot_id) or {}
    extra = d.get("extra") or {}
    extra["legality"] = {"title": (body.title or "").strip(), "env": (body.env or "").strip(),
                         "labor": (body.labor or "").strip()}
    storage.merge_lot(lot_id, {"extra": extra})
    saved = 0
    for i, doc in enumerate((body.docs or [])[:10]):
        try:
            raw = base64.b64decode((doc.get("base64") or "").split(",", 1)[-1])
            if raw and len(raw) < 6_000_000:
                storage.save_blob(lot_id, f"legal_{i}", raw); saved += 1
        except Exception:
            pass
    log("legality", lot_id=lot_id, coop=ctx["coop"]["id"], docs=saved)
    return {"ok": True, "docs": saved, "legality": extra["legality"]}

# ---- Enlace público compartible (para WhatsApp / comprador) ----

# ---- Página del comprador (compartible) + portabilidad de datos ----

def _share_dl(kind, _id):
    base = config.PUBLIC_BASE_URL
    seg = f"c/{_id}" if kind == "c" else _id
    return {"dossier": f"{base}/share/{seg}/dossier", "geojson": f"{base}/share/{seg}/geojson"}

@app.get("/s/c/{cid}")
def share_page_cons(cid: str):
    return _page("share.html")

@app.get("/s/{lot_id}")
def share_page_lot(lot_id: str):
    return _page("share.html")

@app.get("/api/share/c/{cid}")
def api_share_cons(cid: str):
    d = storage.load_consignment(cid)
    if not d:
        raise HTTPException(404, "Envío no encontrado")
    s = _consignment_summary(d)
    return {"kind": "consignment", "id": cid, "title": s["name"] or cid,
            "commodity": s["commodity"], "destination": s["destination"], "buyer": s["buyer"],
            "verdict": s["verdict"], "processed": s["processed"],
            "n_lots": s["n_lots"], "n_plots": s["n_plots"], "total_kg": s["total_kg"],
            "producers": s["producers"], "regions": s["regions"], "created_at": s["created_at"],
            "downloads": _share_dl("c", cid), "verify_url": config.PUBLIC_BASE_URL + "/verificar"}

@app.get("/api/share/{lot_id}")
def api_share_lot(lot_id: str):
    d = storage.load_lot(lot_id)
    if not d:
        raise HTTPException(404, "Lote no encontrado")
    note = storage.get_notary(lot_id) or {}
    return {"kind": "lot", "id": lot_id, "title": d.get("producer_name") or lot_id,
            "commodity": d.get("commodity", ""), "region": d.get("region", ""),
            "destination": "", "verdict": d.get("overall_risk", ""),
            "processed": bool(d.get("overall_risk")), "n_plots": len(d.get("plots", [])),
            "total_kg": dossier.parse_qty_kg(d.get("quantity", "")), "n_lots": 1,
            "cooperative": d.get("cooperative", ""), "created_at": d.get("created_at", ""),
            "downloads": _share_dl("l", lot_id),
            "notary": {"sha256": note.get("sha256")} if note.get("sha256") else None,
            "verify_url": config.PUBLIC_BASE_URL + "/verificar?lot=" + lot_id}

@app.get("/api/export.zip")
def api_export_zip(request: Request):
    ctx = auth.require_coop(request)
    lots = sorted(storage.list_lots(ctx["coop"]["id"]), key=lambda d: d.get("created_at", ""), reverse=True)
    data, n = portability.build_export_zip(ctx["coop"], lots)
    log("export_zip", coop=ctx["coop"]["id"], lots=n)
    fn = "origen_data_" + (ctx["coop"].get("id", "coop")) + ".zip"
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})

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
    if ctx["coop"]["id"] == _DEMO_COOP["id"] and _demo_own_lots(ctx["coop"]["id"]) >= 1:
        raise HTTPException(403, "El entorno demo permite crear 1 lote propio (ya lo usaste). "
                                 "Contáctanos para activar la cuenta de tu organización.")
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
    log("capture", lot_id=lot_id, coop=ctx["coop"]["id"], by=ctx["user"].get("email", ""))
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
    log("lead", **rec)  # queda en los logs de Cloud Run
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
                                   "findings": [f.__dict__ for f in findings],
                                   "volume_flag": bool(geo.volume_issues(lot))})  # cache para envíos + anti-fraude
    except Exception:
        pass
    geom_issues = []
    for pl in lot.plots: geom_issues += geo.geometry_issues(pl)
    geom_issues += geo.volume_issues(lot)
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
