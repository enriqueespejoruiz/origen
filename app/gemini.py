import json
from . import config
from .models import Lot, Plot, GeoPoint

EXTRACT_PROMPT = (
    "Eres un asistente de trazabilidad agricola. A partir del texto y las imagenes, "
    "extrae los datos del lote para EUDR. Devuelve SOLO JSON con las claves: "
    "producer_name, cooperative, commodity (coffee|cocoa), region, harvest_season, "
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
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL, contents=contents,
        config={"response_mime_type": "application/json"},
    )
    return _to_lot(json.loads(resp.text), lot_id, text)

def generate_dossier_narrative(lot: Lot, findings) -> str:
    risks = ", ".join(f"{f.plot_id}:{f.risk}" for f in findings)
    if not config.gemini_ready():
        return (f"Dossier de diligencia debida (EUDR) para el lote {lot.lot_id} "
                f"({lot.commodity}, {lot.region}, Peru). Riesgo por parcela: {risks}. "
                f"Geolocalizacion adjunta en GeoJSON para carga en TRACES NT por el operador importador.")
    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=(f"Redacta el resumen de un dossier de diligencia debida EUDR para el lote "
                  f"{lot.lot_id} ({lot.commodity}, {lot.region}, Peru). Hallazgos por parcela: {risks}. "
                  f"Tono formal, ~150 palabras, en espanol."))
    return resp.text

def generate_buyer_profile(lot: Lot) -> str:
    if not config.gemini_ready():
        return (f"{lot.commodity.title()} de {lot.region}, Peru - productor {lot.producer_name} "
                f"({lot.cooperative}). {len(lot.plots)} parcelas con trazabilidad a nivel de parcela, "
                f"lista para EUDR.")
    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=(f"Escribe un perfil comercial breve (en ingles y espanol, ~120 palabras) para un "
                  f"comprador europeo de este lote de {lot.commodity}: productor {lot.producer_name}, "
                  f"cooperativa {lot.cooperative}, region {lot.region}, {len(lot.plots)} parcelas. "
                  f"Resalta origen, trazabilidad EUDR y calidad."))
    return resp.text

def _to_lot(d, lot_id, raw) -> Lot:
    plots = []
    for i, p in enumerate(d.get("plots", [])):
        pts = [GeoPoint(float(pt["lat"]), float(pt["lon"])) for pt in p.get("points", []) if "lat" in pt]
        plots.append(Plot(p.get("plot_id") or f"P{i+1}", pts, p.get("area_ha")))
    return Lot(lot_id, d.get("producer_name", ""), d.get("cooperative", ""),
               d.get("commodity", "coffee"), "PE", d.get("region", ""), plots,
               d.get("harvest_season", ""), raw)

def _stub_extract(text, lot_id) -> Lot:
    # Parser offline determinista para demo sin API key.
    return Lot(lot_id, "Demo Productor", "Coop. Cafe del Valle", "coffee", "PE", "San Martin",
               [Plot("P1", [GeoPoint(-6.486, -76.366)], 2.1),
                Plot("P2", [GeoPoint(-6.502, -76.349)], 1.4)], "2026", text)
