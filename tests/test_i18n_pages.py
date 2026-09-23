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


def test_dynamic_strings_and_js_literals():
    t = client.get(I.path_for("verificar", "de")).text
    assert "window.ORIGEN_T=" in t and "Buscando…" in t        # clave española dentro del diccionario inyectado
    e = client.get(I.path_for("empezar", "de")).text
    assert "Completa nombre, cooperativa y email" not in e     # el alert() va traducido
    assert "Completa nombre, cooperativa y email" in I.variant(open(os.path.join(I.WEB_DIR, "empezar.html"), encoding="utf-8").read(), "de")


BOOST = "api-saas.selvagencia.com/api/v1/public/forms/form-selva-boost-copy-f80942/embed.js"


def test_boost_form_only_in_spanish():
    """El formulario de Selva Boost (en español) va en la portada y en /empezar en español;
    los demás idiomas conservan su formulario traducido y el botón a su /empezar."""
    for path in ("/", "/empezar"):
        t = client.get(path).text
        assert t.count(BOOST) == 1 and 'id="selva-form-form-selva-boost-copy-f80942"' in t, path
        assert "<!--only:" not in t and "<!--except:" not in t
    e = client.get("/empezar").text
    assert '<form id="f"' not in e and "$('f')" not in e      # sin el formulario propio (ni su script)
    assert 'href="/empezar">Agenda una demo' not in client.get("/").text
    for lang in OTHER:
        home, start = client.get(I.path_for("landing", lang)).text, client.get(I.path_for("empezar", lang)).text
        assert BOOST not in home and BOOST not in start, lang
        assert '<form id="f"' in start and "<!--only:" not in home + start and "<!--except:" not in home + start
        assert 'href="%s"' % I.path_for("empezar", lang) in home, lang


def test_lead_accepts_lang(monkeypatch):
    monkeypatch.setattr(main.config, "GCP_PROJECT", "")
    r = client.post("/lead", json={"name": "Test", "org": "Roaster GmbH", "email": "t@example.com", "lang": "de", "page": "/de/starten"})
    assert r.status_code == 200 and r.json()["ok"]
