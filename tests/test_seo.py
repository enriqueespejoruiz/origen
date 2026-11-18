"""SEO de las páginas públicas (se salta si no están FastAPI/httpx, como en el CI mínimo)."""
import os, sys, re, json, gzip, tempfile

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_data"))

from fastapi.testclient import TestClient  # noqa: E402
from app import main  # noqa: E402

client = TestClient(main.app)
BASE = main._seo_base()
PUBLIC = ["/", "/normativa", "/eudr-cafe-peru", "/eudr-cacao-peru", "/eudr-aplazamiento", "/eudr-traces-dds",
          "/eudr-anexo-1", "/eudr-preguntas-frecuentes", "/eudr-declaracion-simplificada", "/eudr-validador-geojson",
          "/eudr-checklist-proveedor", "/eudr-software", "/empezar", "/verificar", "/eudr-software-importadores", "/eudr-30-diciembre-2026",
          "/eudr-caucho", "/eudr-palma", "/eudr-soya", "/eudr-madera", "/eudr-ganado"]


def _jsonld(html_text):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S)
    assert len(blocks) == 1
    return json.loads(blocks[0])["@graph"]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_page_seo_basics(path):
    r = client.get(path)
    assert r.status_code == 200
    t = r.text
    assert "X-Robots-Tag" not in r.headers
    assert t.count("<title") == 1
    assert t.count('name="description"') == 1
    assert len(re.findall(r"<h1[\s>]", t)) == 1
    assert re.findall(r'<link rel="canonical" href="([^"]+)"', t) == [BASE + path]
    # el servidor entrega el idioma: i18n.js no traduce ni autodetecta en páginas indexables
    assert '<meta name="i18n-server" content="es">' in t
    for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
        assert t.count('property="%s"' % prop) == 1, prop
    assert 'content="' + BASE + '/static/og.png"' in t
    assert "Organization" in [g["@type"] for g in _jsonld(t)]


def test_article_and_breadcrumb_on_guides():
    for path in ("/normativa", "/eudr-cafe-peru", "/eudr-cacao-peru", "/eudr-aplazamiento", "/eudr-traces-dds",
                 "/eudr-anexo-1", "/eudr-preguntas-frecuentes"):
        g = {x["@type"]: x for x in _jsonld(client.get(path).text)}
        assert g["Article"]["headline"] and g["Article"]["inLanguage"] == "es"
        assert g["Article"]["mainEntityOfPage"] == BASE + path
        assert [i["item"] for i in g["BreadcrumbList"]["itemListElement"]] == [BASE + "/", BASE + path]


def test_landing_graph():
    types = [g["@type"] for g in _jsonld(client.get("/").text)]
    assert {"Organization", "WebSite", "SoftwareApplication", "FAQPage"} <= set(types)


def test_faq_page_graph():
    """La página de preguntas frecuentes lleva FAQPage con todas sus preguntas (y respuestas sin HTML)."""
    t = client.get("/eudr-preguntas-frecuentes").text
    faq = [g for g in _jsonld(t) if g["@type"] == "FAQPage"][0]
    assert len(faq["mainEntity"]) == t.count("<summary>") == 15
    for q in faq["mainEntity"]:
        assert q["name"].endswith("?") and q["acceptedAnswer"]["text"] and "<" not in q["acceptedAnswer"]["text"]


@pytest.mark.parametrize("path", ["/capturar", "/panel"])
def test_app_screens_stay_noindex(path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers.get("X-Robots-Tag") == main._NOINDEX
    assert 'i18n-auto' not in r.text and 'i18n-server' not in r.text   # la app conserva la autodetección ES/EN
    assert 'rel="canonical"' not in r.text


def test_static_html_copies_are_noindex():
    r = client.get("/static/landing.html")
    assert r.status_code == 200 and r.headers.get("X-Robots-Tag", "").startswith("noindex")
    assert "X-Robots-Tag" not in client.get("/static/og.png").headers


def test_gzip_and_head():
    r = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
    h = client.head("/normativa")
    assert h.status_code == 200 and h.content == b""


def test_robots_and_sitemap():
    assert "Sitemap: " + BASE + "/sitemap.xml" in client.get("/robots.txt").text
    locs = re.findall(r"<loc>([^<]+)</loc>", client.get("/sitemap.xml").text)
    assert {BASE + p for p in PUBLIC} <= set(locs)
    I = main.i18n_pages
    assert len(locs) == len(set(locs)) == sum(len(I.langs_for(k)) for k in I.PAGES)


def test_i18n_js_respects_public_pages():
    js = open(os.path.join(main.WEB_DIR, "i18n.js"), encoding="utf-8").read()
    assert 'meta[name="i18n-auto"][content="off"]' in js
    assert 'meta[name="i18n-server"]' in js


def test_privacy_pages():
    """Aviso de privacidad: español (Ley 29733) y inglés (RGPD), fuera de Google, con los datos reales del
    responsable; los pies enlazan la versión en español desde /es y la inglesa desde los demás idiomas."""
    for path, must in (("/privacidad", ("SELVA MARKETING SOSTENIBLE S.A.C.", "20615597393", "hola@selvagencia.com", "Cinco años")),
                       ("/en/privacy", ("SELVA MARKETING SOSTENIBLE S.A.C.", "20615597393", "hola@selvagencia.com", "Article 6(1)(a)", "Five years"))):
        r = client.get(path)
        assert r.status_code == 200 and "noindex" in r.headers.get("X-Robots-Tag", ""), path
        for m in must:
            assert m in r.text, (path, m)
    es = client.get("/").text
    assert 'href="/privacidad"' in es and 'href="/en/privacy"' not in es
    de = client.get(main.i18n_pages.path_for("landing", "de")).text
    assert 'href="/en/privacy"' in de and 'href="/privacidad"' not in de
    assert "/privacidad" not in client.get("/sitemap.xml").text
