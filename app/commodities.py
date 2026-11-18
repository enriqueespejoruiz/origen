"""Catálogo de productos del EUDR (Reglamento (UE) 2023/1115, art. 2 y Anexo I).

Los 7 productos básicos: café, cacao, palma aceitera, soya, caucho, madera y ganado bovino.
Clave interna estable (en inglés) -> nombres ES/EN, partida del SA por defecto, nombre científico
y reglas de captura. La partida exacta (p. ej. 1806 chocolate) y la especie se pueden indicar
por lote en lot.extra["hs"] y lot.extra["species"]; el dossier usa esos valores si existen.

El Anexo I también cubre derivados (chocolate, aceite de palma, muebles, papel, neumáticos...).
Origen verifica la parcela de origen; la partida del derivado la declara el operador en su DDS.
"""

CATALOG = {
    "coffee": {
        "es": "Café", "en": "Coffee", "hs": "0901", "sci": "Coffea arabica",
        "ceil_kg_ha": 2500.0,          # techo de rendimiento plausible (anti-fraude de volumen)
    },
    "cocoa": {
        "es": "Cacao", "en": "Cocoa", "hs": "1801", "sci": "Theobroma cacao",
        "ceil_kg_ha": 2000.0,
    },
    "oil_palm": {
        "es": "Palma aceitera", "en": "Oil palm", "hs": "1511", "sci": "Elaeis guineensis",
    },
    "soya": {
        "es": "Soya", "en": "Soya", "hs": "1201", "sci": "Glycine max",
    },
    "rubber": {
        "es": "Caucho natural", "en": "Natural rubber", "hs": "4001", "sci": "Hevea brasiliensis",
    },
    "wood": {
        "es": "Madera", "en": "Wood", "hs": "44", "sci": "",
        "needs_species": True,         # el EUDR pide nombre común y científico de la especie
    },
    "cattle": {
        "es": "Ganado bovino", "en": "Cattle", "hs": "0102", "sci": "Bos taurus / Bos indicus",
        "point_any_size": True,        # establecimientos: el polígono >4 ha no aplica al ganado
    },
}

ORDER = ["coffee", "cocoa", "oil_palm", "soya", "rubber", "wood", "cattle"]

_ALIASES = {
    "cafe": "coffee", "café": "coffee", "coffee": "coffee",
    "cacao": "cocoa", "cocoa": "cocoa", "chocolate": "cocoa",
    "palma": "oil_palm", "palma aceitera": "oil_palm", "palma_aceitera": "oil_palm", "oil palm": "oil_palm",
    "oil_palm": "oil_palm", "palm": "oil_palm", "palm oil": "oil_palm", "aceite de palma": "oil_palm",
    "soya": "soya", "soja": "soya", "soy": "soya", "soybean": "soya", "soybeans": "soya",
    "caucho": "rubber", "caucho natural": "rubber", "jebe": "rubber", "shiringa": "rubber", "rubber": "rubber",
    "madera": "wood", "wood": "wood", "timber": "wood", "forestal": "wood",
    "ganado": "cattle", "ganado bovino": "cattle", "bovino": "cattle", "bovinos": "cattle",
    "vacuno": "cattle", "res": "cattle", "carne": "cattle", "cattle": "cattle", "beef": "cattle",
}


def norm(value, default="coffee"):
    """Clave canónica del producto ('cacao' -> 'cocoa', 'palma' -> 'oil_palm'). Desconocido: tal cual en minúsculas."""
    s = str(value or "").strip().lower().replace("-", " ")
    if not s:
        return default
    return _ALIASES.get(s, _ALIASES.get(s.replace("_", " "), s))


def known(value):
    return norm(value, "") in CATALOG


def label(value, lang="es"):
    c = CATALOG.get(norm(value, ""))
    if not c:
        return str(value or "—")
    return c["en"] if (lang or "es").lower().startswith("en") else c["es"]


def info(value, lang="es", extra=None):
    """(partida SA, nombre científico, etiqueta) para el dossier. lot.extra puede precisar 'hs' y 'species'."""
    ex = extra if isinstance(extra, dict) else {}
    c = CATALOG.get(norm(value, ""))
    hs = str(ex.get("hs") or "").strip()
    sp = str(ex.get("species") or "").strip()
    if not c:
        return (hs or "—", sp or "—", str(value or "—"))
    en = (lang or "es").lower().startswith("en")
    if not hs:
        hs = c["hs"]
        if norm(value) == "wood":
            hs = "44 (indicate the exact heading)" if en else "44 (indicar la partida exacta)"
    if not sp:
        sp = c["sci"] or ("— (indicate the species)" if en else "— (indicar la especie)")
    return (hs, sp, c["en"] if en else c["es"])


def yield_ceiling(value):
    """Techo de rendimiento (kg/ha) para el chequeo anti-fraude. None = sin techo configurado (no se evalúa)."""
    c = CATALOG.get(norm(value, ""))
    return c.get("ceil_kg_ha") if c else None


def point_any_size(value):
    c = CATALOG.get(norm(value, ""))
    return bool(c and c.get("point_any_size"))


def options(lang="es"):
    """Lista ordenada [(clave, etiqueta)] para formularios."""
    return [(k, label(k, lang)) for k in ORDER]
