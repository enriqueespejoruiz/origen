import json
from . import config
from .models import Lot, Plot, GeoPoint
from . import commodities as _cm

EXTRACT_PROMPT = (
    "Eres un asistente de trazabilidad agricola. A partir del texto y las imagenes, "
    "extrae los datos del lote para EUDR. Devuelve SOLO JSON con las claves: "
    "producer_name, cooperative, commodity (coffee|cocoa|oil_palm|soya|rubber|wood|cattle), region, harvest_season, "
    "plots (lista de {plot_id, points:[{lat,lon}], area_ha}). "
    "Si un dato no aparece, usa cadena vacia o lista vacia."
)

_CLIENT = None

def _client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        if config.USE_VERTEX:
            _CLIENT = genai.Client(vertexai=True, project=config.GCP_PROJECT, location=config.GCP_LOCATION)
        else:
            _CLIENT = genai.Client(api_key=config.GEMINI_API_KEY)
    return _CLIENT

_ACTIVE = None   # último modelo que respondió bien (evita reintentar uno retirado en cada llamada)

def _unavailable(e):
    """True si el error indica modelo inexistente/retirado (404, NOT_FOUND, no soportado)."""
    m = (repr(e) + " " + str(getattr(e, "message", ""))).lower()
    return any(k in m for k in ("404", "not_found", "not found", "is not supported", "retired",
                                 "no longer available", "deprecated", "does not have access"))

def models_chain():
    chain = [_ACTIVE] if _ACTIVE else []
    for m in [config.GEMINI_MODEL] + list(config.GEMINI_FALLBACKS):
        if m and m not in chain:
            chain.append(m)
    return chain

def generate(contents, cfg=None):
    """generate_content con respaldo: si el modelo fue retirado, prueba el siguiente de la lista."""
    global _ACTIVE
    last = None
    for m in models_chain():
        try:
            resp = _client().models.generate_content(model=m, contents=contents, config=cfg)
            _ACTIVE = m
            return resp
        except Exception as e:
            last = e
            if not _unavailable(e):
                raise
            print("gemini model unavailable:", m, repr(e)[:160])
    raise last if last else RuntimeError("Sin modelos Gemini configurados")

def active_model():
    return _ACTIVE or config.GEMINI_MODEL

def extract_lot(text: str, image_paths=None, lot_id="LOT-DEMO") -> Lot:
    if not config.gemini_ready():
        return _stub_extract(text, lot_id)
    client = _client()
    contents = [EXTRACT_PROMPT, "TEXTO:\n" + text]
    if image_paths:
        from google.genai import types
        for p in image_paths:
            with open(p, "rb") as f:
                contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))
    resp = generate(contents, {"response_mime_type": "application/json"})
    return _to_lot(json.loads(resp.text), lot_id, text)

def generate_dossier_narrative(lot: Lot, findings) -> str:
    from . import countries as _ct
    pais = _ct.name(_ct.of_lot(lot), "es")
    risks = ", ".join(f"{f.plot_id}:{f.risk}" for f in findings)
    if not config.gemini_ready():
        return (f"Dossier de diligencia debida (EUDR) para el lote {lot.lot_id} "
                f"({lot.commodity}, {lot.region}, {pais}). Riesgo por parcela: {risks}. "
                f"Geolocalizacion adjunta en GeoJSON para carga en TRACES NT por el operador importador.")
    resp = generate(
        (f"Redacta el resumen de un dossier de diligencia debida EUDR para el lote "
                  f"{lot.lot_id} ({lot.commodity}, {lot.region}, {pais}). Hallazgos por parcela: {risks}. "
                  f"Tono formal, ~150 palabras, en espanol."))
    return resp.text

def generate_buyer_profile(lot: Lot) -> str:
    from . import countries as _ct
    if not config.gemini_ready():
        return (f"{lot.commodity.title()} de {lot.region}, {_ct.name(_ct.of_lot(lot), 'es')} - productor {lot.producer_name} "
                f"({lot.cooperative}). {len(lot.plots)} parcelas con trazabilidad a nivel de parcela, "
                f"lista para EUDR.")
    resp = generate(
        (f"Escribe un perfil comercial breve (en ingles y espanol, ~120 palabras) para un "
                  f"comprador europeo de este lote de {lot.commodity}: productor {lot.producer_name}, "
                  f"cooperativa {lot.cooperative}, region {lot.region}, pais {_ct.name(_ct.of_lot(lot), 'es')}, {len(lot.plots)} parcelas. "
                  f"Resalta origen, trazabilidad EUDR y calidad."))
    return resp.text

def _to_lot(d, lot_id, raw) -> Lot:
    from . import countries as _ct
    plots = []
    for i, p in enumerate(d.get("plots", [])):
        pts = [GeoPoint(float(pt["lat"]), float(pt["lon"])) for pt in p.get("points", []) if "lat" in pt]
        plots.append(Plot(p.get("plot_id") or f"P{i+1}", pts, p.get("area_ha")))
    return Lot(lot_id, d.get("producer_name", ""), d.get("cooperative", ""),
               _cm.norm(d.get("commodity", "coffee")), _ct.norm(d.get("country")) or _ct.DEFAULT, d.get("region", ""), plots,
               d.get("harvest_season", ""), raw)

def _stub_extract(text, lot_id) -> Lot:
    # Parser offline determinista para demo sin API key.
    return Lot(lot_id, "Demo Productor", "Coop. Cafe del Valle", "coffee", "PE", "San Martin",
               [Plot("P1", [GeoPoint(-6.486, -76.366)], 2.1),
                Plot("P2", [GeoPoint(-6.502, -76.349)], 1.4)], "2026", text)
