"""Copiloto de cumplimiento EUDR (Gemini) — explica hallazgos, recomienda exclusión/sustento,
redacta legalidad y responde preguntas. Con fallbacks deterministas para no romper la demo."""
import json
from . import config

_EUDR = (
    "Contexto EUDR (Reglamento UE 2023/1115): para café y cacao que entran a la UE hay que probar, "
    "parcela por parcela, que el producto no viene de tierra deforestada después del 31-dic-2020, "
    "además de legalidad. Obligatorio desde 30-dic-2026 (grandes/medianos) y 30-jun-2027 (pequeños). "
    "No se permite mezclar material conforme con no conforme (no hay mass-balance): una parcela "
    "observada debe segregarse (excluirse del envío) o sustentarse con documentos. La Declaración de "
    "Diligencia Debida (DDS) la presenta el operador importador en la UE vía TRACES."
)
_ROLE = ("Eres el copiloto de cumplimiento EUDR de Origen: experto, honesto y claro. Hablas en español "
         "sencillo para el gerente de una cooperativa de café o cacao del Perú. No inventes datos ni cifras.")


def _gemini(prompt, json_mode=False):
    from . import gemini as g
    cfg = {"response_mime_type": "application/json"} if json_mode else None
    resp = g._client().models.generate_content(model=config.GEMINI_MODEL, contents=prompt, config=cfg)
    return resp.text


def _findings_text(findings):
    return "\n".join(f"- Parcela {f.plot_id}: riesgo={f.risk}; {f.detail}" for f in findings) or "- (sin hallazgos)"


def analyze_lot(lot, findings):
    """{resumen, parcelas:[{plot_id, explicacion, accion}], recomendacion, legalidad}."""
    base = {
        "resumen": _fb_resumen(lot, findings),
        "parcelas": [{"plot_id": f.plot_id, "explicacion": _fb_expl(f), "accion": _fb_accion(f)} for f in findings],
        "recomendacion": _fb_reco(findings),
        "legalidad": _fb_legal(lot),
        "fuente": "reglas",
    }
    if not config.gemini_ready():
        return base
    prompt = (
        _ROLE + " " + _EUDR + "\n\n"
        f"Lote {lot.lot_id} ({lot.commodity}, región {lot.region or '—'}, productor {lot.producer_name or '—'}). "
        f"Hallazgos por parcela:\n{_findings_text(findings)}\n\n"
        "Devuelve SOLO JSON con las claves exactas: "
        "resumen (1-2 frases del estado del lote), "
        "parcelas (lista de {plot_id, explicacion: por qué ese veredicto en lenguaje claro y breve, "
        "accion: 'ninguna' | 'sustentar' | 'excluir'}), "
        "recomendacion (qué debe hacer la cooperativa para dejar el lote listo), "
        "legalidad (borrador breve de sustentación de legalidad y tenencia para adjuntar). "
        "Si una parcela está observada, dilo con claridad."
    )
    try:
        d = json.loads(_gemini(prompt, json_mode=True))
        return {
            "resumen": d.get("resumen") or base["resumen"],
            "parcelas": d.get("parcelas") or base["parcelas"],
            "recomendacion": d.get("recomendacion") or base["recomendacion"],
            "legalidad": d.get("legalidad") or base["legalidad"],
            "fuente": "gemini",
        }
    except Exception as e:
        print("copilot analyze error:", repr(e))
        return base


def chat(question, lot=None, findings=None):
    if not config.gemini_ready():
        return _fb_chat()
    ctx = ""
    if lot is not None:
        ctx = (f"\nLote en contexto: {lot.lot_id} ({lot.commodity}, {lot.region or '—'}). "
               f"Hallazgos:\n{_findings_text(findings or [])}\n")
    prompt = (_ROLE + " " + _EUDR + ctx + f"\nPregunta del usuario: {question}\n"
              "Responde útil, honesto y breve (máx ~130 palabras). Si no lo sabes, dilo.")
    try:
        return (_gemini(prompt) or "").strip() or _fb_chat()
    except Exception as e:
        print("copilot chat error:", repr(e))
        return _fb_chat()


# ---- fallbacks deterministas (sin Gemini) ----
def _fb_expl(f):
    return {"high": "Se detectó posible deforestación después del corte (31-dic-2020).",
            "review": "Hay una señal dudosa cerca del límite que conviene verificar antes de exportar.",
            "negligible": "Sin pérdida de bosque tras el corte; la parcela está en orden."}.get(f.risk, f.detail)

def _fb_accion(f):
    return {"high": "excluir", "review": "sustentar", "negligible": "ninguna"}.get(f.risk, "sustentar")

def _fb_resumen(lot, findings):
    high = sum(1 for f in findings if f.risk == "high"); rev = sum(1 for f in findings if f.risk == "review")
    if high:
        return f"El lote {lot.lot_id} tiene {high} parcela(s) observada(s): hay que excluirlas o sustentarlas antes de exportar."
    if rev:
        return f"El lote {lot.lot_id} tiene {rev} parcela(s) a revisar; el resto está en orden."
    return f"El lote {lot.lot_id} está en orden: sin deforestación posterior al corte."

def _fb_reco(findings):
    high = [f.plot_id for f in findings if f.risk == "high"]
    rev = [f.plot_id for f in findings if f.risk == "review"]
    if high:
        return ("Excluye del envío las parcelas " + ", ".join(high) +
                " o sustenta su legalidad/origen con documentos, y vuelve a generar el dossier.")
    if rev:
        return "Verifica las parcelas " + ", ".join(rev) + " antes de enviar; si están bien, el lote queda listo."
    return "El lote puede consolidarse en la DDS; comparte el dossier con tu comprador."

def _fb_legal(lot):
    return (f"La producción del lote {lot.lot_id} proviene de predios de "
            f"{lot.cooperative or 'la cooperativa'} en {lot.region or 'la región'}, Perú, bajo tenencia "
            "conforme a la legislación nacional. Adjuntar título o derecho de uso del predio y la "
            "conformidad ambiental, forestal y laboral por parcela.")

def _fb_chat():
    return ("Soy el copiloto EUDR de Origen. Puedo explicarte los hallazgos de un lote, decirte qué "
            "parcela excluir o sustentar y ayudarte con la sustentación. Abre un lote y pulsa "
            "«Copiloto», o pregúntame algo concreto sobre el EUDR.")
