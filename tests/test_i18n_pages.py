"""Páginas públicas en varios idiomas (app/i18n_pages.py). Se salta si faltan fastapi/httpx."""
import os, sys, re, json, tempfile
import xml.etree.ElementTree as ET
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_data"))

from fastapi.testclient import TestClient  # noqa: E402
from app import main, i18n_pages as I  # noqa: E402

client = TestClient(main.app)
BASE = main._seo_base()
LANGS = I.active()
OTHER = [l for l in LANGS if l != "es"]
CASES = [(l, k) for l in LANGS for k in I.PAGES]


def _spanish_keys(key):
    with open(os.path.join(I.WEB_DIR, I.PAGES[key][0]), encoding="utf-8") as f:
        t = f.read()
    body = I.variant(t[t.lower().index("<body"):], "en")    # lo que ven los demás idiomas (sin bloques only:es)
    keys = set(I.text_chunks(body)) | set(I.attr_values(body))
    return {k for k in keys if re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]", k)}


def test_all_eu_languages_are_active():
    assert LANGS == I.ORDER, "faltan diccionarios: %s" % sorted(set(I.ORDER) - set(LANGS))


@pytest.mark.parametrize("lang", OTHER)
def test_dictionary_is_complete(lang):
    d = I.LANGS[lang]
    missing = set()
    for key in I.PAGES:
        missing |= {k for k in _spanish_keys(key) if k not in d["strings"]}
    allowed = {"Origen", "Gemini · Vertex AI", "Google Cloud Run", "Hansen · WDPA · JRC", "GeoJSON + dossier",
               "Coop. Aurora · Cusco", "María Quispe", "José Mamani", "Rosa Huamán", "SHA-256", "LOT-XXXXXXXX",
               "EN", "A", "B", "C", "D", "Switch language", "dossier + GeoJSON", "13°31′S · 71°57′W", ".ots"}
    assert missing <= allowed, sorted(missing - allowed)[:10]
    assert all(str(v).strip() for v in d["strings"].values())
    for key, meta in d["pages"].items():
        assert meta["title"] and meta["description"] and "slug" in meta, (lang, key)
        assert len(meta["title"]) <= 65 and len(meta["description"]) <= 165, (lang, key)


@pytest.mark.parametrize("lang,key", CASES)
def test_page_renders_with_hreflang_cluster(lang, key):
    path = I.path_for(key, lang)
    r = client.get(path)
    assert r.status_code == 200
    t = r.text
    assert re.search(r'<html lang="%s"' % lang, t)
    assert t.count("<title>") == 1 and t.count('<meta name="description"') == 1
    assert len(re.findall(r"<h1[\s>]", t)) == 1
    assert re.findall(r'<link rel="canonical" href="([^"]+)"', t) == [BASE + path]
    alts = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', t))
    assert set(alts) == set(LANGS) | {"x-default"}
    assert alts[lang] == BASE + path and alts["x-default"] == BASE + I.path_for(key, "en")
    assert '<meta name="i18n-server" content="%s">' % lang in t
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    assert len(ld) == 1
    graph = json.loads(ld[0].replace("<\\/", "</"))["@graph"]
    for g in graph:
        if "inLanguage" in g:
            assert g["inLanguage"] == lang
    # selector con todos los idiomas y el actual marcado
    sel = re.search(r'<details class="og-lang".*?</details>', t, re.S).group(0)
    assert sel.count("<li>") == len(LANGS) and 'aria-current="true"' in sel
    # fuera del selector, los enlaces internos se quedan en el mismo idioma
    body = re.sub(r'<details class="og-lang".*?</details>', "", t[t.index("<body"):], flags=re.S)
    if lang != "es":
        for href in re.findall(r'href="(/[^"#?]*)', body):
            assert href not in I.ES_PATH_TO_KEY or href == "/", (lang, key, href)


def test_hreflang_targets_all_resolve():
    for lang in LANGS:
        for key in I.PAGES:
            assert client.get(I.path_for(key, lang)).status_code == 200


def test_sitemap_has_alternates():
    x = client.get("/sitemap.xml").text
    root = ET.fromstring(x)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    urls = root.findall("s:url", ns)
    assert len(urls) == len(LANGS) * len(I.PAGES)
    for u in urls:
        assert len(u.findall("x:link", ns)) == len(LANGS) + 1


def test_redirects_and_404():
    r = client.get("/de", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/de/"
    assert client.get("/xx/").status_code == 404
    assert client.get("/de/no-existe").status_code == 404
    assert client.get("/zz").status_code == 404


def test_dynamic_strings_are_injected():
    t = client.get(I.path_for("verificar", "de")).text
    assert "window.ORIGEN_T=" in t and "Buscando…" in t        # clave española dentro del diccionario inyectado


BOOST_ES = "api-saas.selvagencia.com/api/v1/public/forms/form-selva-boost-copy-f80942/embed.js"
BOOST_EU = "api-saas.selvagencia.com/api/v1/public/forms/form-origen-europe/embed.js"


def test_boost_forms_by_language():
    """Portada y /empezar llevan el formulario de Selva Boost: «Form Origen» en español y
    «Form Origen EU (English)» (consentimiento RGPD) en los demás idiomas. Ya no queda el
    formulario propio que guardaba en Firestore sin avisar a nadie."""
    for lang in LANGS:
        want, other = (BOOST_ES, BOOST_EU) if lang == "es" else (BOOST_EU, BOOST_ES)
        for key in ("landing", "empezar"):
            t = client.get(I.path_for(key, lang)).text
            assert t.count(want) == 1 and other not in t, (lang, key)
            assert '<form id="f"' not in t and "<!--only:" not in t and "<!--except:" not in t, (lang, key)
        home = client.get(I.path_for("landing", lang)).text
        assert 'class="cierre-form"' in home and 'href="%s"' % I.path_for("empezar", lang) in home, lang


def test_lead_accepts_lang(monkeypatch):
    monkeypatch.setattr(main.config, "GCP_PROJECT", "")
    r = client.post("/lead", json={"name": "Test", "org": "Roaster GmbH", "email": "t@example.com", "lang": "de", "page": "/de/starten"})
    assert r.status_code == 200 and r.json()["ok"]


def test_delay_page_links_and_dates():
    """La página de aplazamientos existe en todos los idiomas, está enlazada desde portada, normativa
    y la guía del café, y lleva fecha de actualización en el Article (se revisa cada mes)."""
    for lang in LANGS:
        target = I.path_for("eudr-aplazamiento", lang)
        for key in ("landing", "normativa", "eudr-cafe-peru"):
            assert 'href="%s"' % target in client.get(I.path_for(key, lang)).text, (lang, key)
    t = client.get("/eudr-aplazamiento").text
    art = [g for g in json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)[0].replace("<\\/", "</"))["@graph"]
           if g["@type"] == "Article"][0]
    assert art["dateModified"] >= art["datePublished"] == "2026-09-23"
    assert "Actualizado el 10 de octubre de 2026" in t


def test_simplified_declaration_page():
    """Página de la declaración simplificada: en todos los idiomas, con FAQPage, enlazada desde portada (FAQ),
    normativa y aplazamiento; dice que el Perú es riesgo estándar y no promete la declaración simplificada."""
    for lang in LANGS:
        target = I.path_for("eudr-declaracion-simplificada", lang)
        for key in ("landing", "normativa", "eudr-aplazamiento"):
            assert 'href="%s"' % target in client.get(I.path_for(key, lang)).text, (lang, key)
        t = client.get(target).text
        types = [g["@type"] for g in json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)[0].replace("<\\/", "</"))["@graph"]]
        assert "FAQPage" in types and "Article" in types, lang
    t = client.get("/eudr-declaracion-simplificada").text
    assert "riesgo estándar" in t and "Costa Rica" in t


def test_new_guides_are_linked():
    """Cacao, anexo I y preguntas frecuentes existen en todos los idiomas y están enlazados desde la normativa
    (y el cacao también desde la guía del café y la portada; las preguntas frecuentes, desde el pie de la portada)."""
    for lang in LANGS:
        norm = client.get(I.path_for("normativa", lang)).text
        for key in ("eudr-cacao-peru", "eudr-anexo-1", "eudr-preguntas-frecuentes"):
            assert 'href="%s"' % I.path_for(key, lang) in norm, (lang, key)
        cafe = client.get(I.path_for("eudr-cafe-peru", lang)).text
        assert 'href="%s"' % I.path_for("eudr-cacao-peru", lang) in cafe, lang
        home = client.get(I.path_for("landing", lang)).text
        for key in ("eudr-cacao-peru", "eudr-preguntas-frecuentes"):
            assert 'href="%s"' % I.path_for(key, lang) in home, (lang, key)
        faq = client.get(I.path_for("eudr-preguntas-frecuentes", lang)).text
        graph = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', faq, re.S)[0].replace("<\\/", "</"))["@graph"]
        assert len([g for g in graph if g["@type"] == "FAQPage"][0]["mainEntity"]) == 15, lang


def test_traces_guide_is_linked():
    """La guía de la DDS en TRACES existe en todos los idiomas y la enlazan la normativa y la guía del café."""
    for lang in LANGS:
        target = I.path_for("eudr-traces-dds", lang)
        for key in ("normativa", "eudr-cafe-peru"):
            assert 'href="%s"' % target in client.get(I.path_for(key, lang)).text, (lang, key)


def test_validator_checklist_software_pages():
    """Validador GeoJSON, checklist del proveedor y software: en todos los idiomas, con FAQPage, enlazados
    (validador desde traces y portada; checklist desde traces y normativa; software desde portada y normativa),
    y los mensajes del validador traducidos en window.ORIGEN_T."""
    for lang in LANGS:
        home = client.get(I.path_for("landing", lang)).text
        tr = client.get(I.path_for("eudr-traces-dds", lang)).text
        norm = client.get(I.path_for("normativa", lang)).text
        assert 'href="%s"' % I.path_for("eudr-validador-geojson", lang) in home and 'href="%s"' % I.path_for("eudr-validador-geojson", lang) in tr
        assert 'href="%s"' % I.path_for("eudr-checklist-proveedor", lang) in tr and 'href="%s"' % I.path_for("eudr-checklist-proveedor", lang) in norm
        assert 'href="%s"' % I.path_for("eudr-software", lang) in home and 'href="%s"' % I.path_for("eudr-software", lang) in norm
        for key in ("eudr-validador-geojson", "eudr-checklist-proveedor", "eudr-software"):
            t = client.get(I.path_for(key, lang)).text
            types = [g["@type"] for g in json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)[0].replace("<\\/", "</"))["@graph"]]
            assert "FAQPage" in types, (lang, key)
        if lang != "es":
            dyn = I.LANGS[lang]["dyn"]
            assert "Sin errores: el archivo cumple las reglas de TRACES que revisamos." in dyn, lang
    assert client.get("/static/plantilla-eudr-parcelas.csv").status_code == 200
