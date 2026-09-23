"""Páginas públicas en varios idiomas, servidas desde el servidor.

Una sola plantilla por página (el HTML en español de web/) y un diccionario por idioma en
web/i18n/<idioma>.json. El servidor traduce los nodos de texto, ajusta los enlaces internos al
idioma y agrega canonical, hreflang, Open Graph y JSON-LD. Así Google indexa cada idioma en su
propia URL (/de/eudr-verordnung, /fr/reglement-eudr…) y no depende de JavaScript.

Formato del diccionario:
{
  "lang": "de", "name": "Deutsch", "og_locale": "de_DE",
  "labels": {"language": "Sprache"},
  "app_description": "...",
  "pages": {"landing": {"slug": "", "title": "...", "description": "...", "og_title": "...",
                        "og_description": "...", "crumb": "..."}, ...},
  "strings": {"<texto en español>": "<traducción>"},   # nodos de texto y atributos visibles
  "dyn": {"<texto en español>": "<traducción>"},       # textos que el JS inserta después (verificar/empezar)
  "js": {"<literal en español>": "<traducción>"}        # literales de <script> (alert)
}
Un idioma sin archivo no se sirve ni aparece en hreflang ni en el sitemap.
"""
import os, re, json, html as _html

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
I18N_DIR = os.path.join(WEB_DIR, "i18n")

# clave -> (plantilla en español, ruta pública en español)
PAGES = {
    "landing": ("landing.html", "/"),
    "normativa": ("normativa.html", "/normativa"),
    "eudr-cafe-peru": ("eudr-cafe-peru.html", "/eudr-cafe-peru"),
    "eudr-cacao-peru": ("eudr-cacao-peru.html", "/eudr-cacao-peru"),
    "eudr-aplazamiento": ("eudr-aplazamiento.html", "/eudr-aplazamiento"),
    "eudr-traces-dds": ("eudr-traces-dds.html", "/eudr-traces-dds"),
    "eudr-anexo-1": ("eudr-anexo-1.html", "/eudr-anexo-1"),
    "eudr-preguntas-frecuentes": ("eudr-preguntas-frecuentes.html", "/eudr-preguntas-frecuentes"),
    "empezar": ("empezar.html", "/empezar"),
    "verificar": ("verificar.html", "/verificar"),
}
FILE_TO_KEY = {f: k for k, (f, _) in PAGES.items()}
ES_PATH_TO_KEY = {p: k for k, (_, p) in PAGES.items()}

ORDER = ["es", "en", "de", "fr", "it", "nl", "pt", "pl", "sv", "da", "fi", "cs", "sk", "hu",
         "ro", "bg", "el", "hr", "sl", "et", "lv", "lt"]
NATIVE = {"es": "Español", "en": "English", "de": "Deutsch", "fr": "Français", "it": "Italiano",
          "nl": "Nederlands", "pt": "Português", "pl": "Polski", "sv": "Svenska", "da": "Dansk",
          "fi": "Suomi", "cs": "Čeština", "sk": "Slovenčina", "hu": "Magyar", "ro": "Română",
          "bg": "Български", "el": "Ελληνικά", "hr": "Hrvatski", "sl": "Slovenščina", "et": "Eesti",
          "lv": "Latviešu", "lt": "Lietuvių"}
ES_LABELS = {"language": "Idioma"}
FAQ_PAGES = ("landing", "eudr-preguntas-frecuentes")   # páginas con FAQPage (<details><summary>P</summary><p>R</p>)
ES_CRUMB = {"landing": "Origen", "normativa": "Normativa EUDR", "eudr-cafe-peru": "EUDR para el café peruano",
            "eudr-cacao-peru": "EUDR para el cacao peruano",
            "eudr-aplazamiento": "Aplazamiento del EUDR", "eudr-traces-dds": "La DDS en TRACES",
            "eudr-anexo-1": "Anexo I del EUDR", "eudr-preguntas-frecuentes": "Preguntas frecuentes",
            "empezar": "Empezar", "verificar": "Verificar dossier"}

# Etiquetas: respeta atributos entre comillas (un ">" dentro de un atributo no corta la etiqueta).
_TAG = re.compile(r"""(<(?:"[^"]*"|'[^']*'|[^'">])*>)""")
_PROTECT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->|<svg\b.*?</svg>)", re.S | re.I)
_ATTR = re.compile(r'(\s(?:placeholder|aria-label|alt|title)=")([^"]*)(")')
# Bloques por idioma en las plantillas: <!--only:es-->…<!--/only:es--> solo existe en esos idiomas;
# <!--except:es-->…<!--/except:es--> existe en todos menos en esos (p. ej. el formulario de Boost, que está en español).
_ONLY = re.compile(r"<!--only:([a-z,]+)-->(.*?)<!--/only:\1-->", re.S)
_EXCEPT = re.compile(r"<!--except:([a-z,]+)-->(.*?)<!--/except:\1-->", re.S)


def variant(html_text, lang):
    html_text = _ONLY.sub(lambda m: m.group(2) if lang in m.group(1).split(",") else "", html_text)
    return _EXCEPT.sub(lambda m: "" if lang in m.group(1).split(",") else m.group(2), html_text)


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _load():
    out = {}
    for code in ORDER[1:]:
        f = os.path.join(I18N_DIR, code + ".json")
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        d["strings"] = {norm(k): v for k, v in (d.get("strings") or {}).items()}
        d["dyn"] = {norm(k): v for k, v in (d.get("dyn") or {}).items()}
        d["js"] = d.get("js") or {}
        out[code] = d
    return out


LANGS = _load()
_CACHE = {}


def active():
    return ["es"] + [c for c in ORDER[1:] if c in LANGS]


def path_for(key, lang):
    if lang == "es":
        return PAGES[key][1]
    return "/" + lang + "/" + LANGS[lang]["pages"][key]["slug"]


def resolve(lang, slug):
    """Devuelve la clave de página para /<lang>/<slug>, o None."""
    d = LANGS.get(lang)
    if not d:
        return None
    for key, meta in d["pages"].items():
        if key in PAGES and meta.get("slug", None) == slug:
            return key
    return None


# ── Inventario y traducción del HTML ─────────────────────────────────────────

def text_chunks(html_text):
    """Recorre el HTML fuera de <script>/<style>/<svg>/comentarios y entrega (índice, texto) de
    cada nodo de texto. Es la misma segmentación que usa translate(): sirve para armar el inventario."""
    for part_i, part in enumerate(_PROTECT.split(html_text)):
        if part_i % 2 == 1:
            continue
        for j, ch in enumerate(_TAG.split(part)):
            if j % 2 == 0 and ch.strip():
                yield norm(_html.unescape(ch))


def attr_values(html_text):
    for part_i, part in enumerate(_PROTECT.split(html_text)):
        if part_i % 2 == 1:
            continue
        for m in _ATTR.finditer(part):
            v = norm(_html.unescape(m.group(2)))
            if v:
                yield v


def _js_literal(s, quote):
    return quote + s.replace("\\", "\\\\").replace(quote, "\\" + quote) + quote


def translate(html_text, strings, js=None):
    out = []
    for part_i, part in enumerate(_PROTECT.split(html_text)):
        if part_i % 2 == 1:
            if js and part[:7].lower() == "<script":
                for es, tr in js.items():
                    for q in ("'", '"'):
                        part = part.replace(_js_literal(es, q), _js_literal(tr, q))
            out.append(part)
            continue
        for j, ch in enumerate(_TAG.split(part)):
            if j % 2 == 1:
                out.append(_ATTR.sub(lambda m: m.group(1) + (
                    _html.escape(strings[norm(_html.unescape(m.group(2)))], quote=True)
                    if norm(_html.unescape(m.group(2))) in strings else m.group(2)) + m.group(3), ch))
                continue
            if not ch.strip():
                out.append(ch)
                continue
            key = norm(_html.unescape(ch))
            if key in strings:
                tr = strings[key]
                lead = ch[:len(ch) - len(ch.lstrip())]
                trail = ch[len(ch.rstrip()):]
                if tr[:1] in ".,;:!?)»":      # «operators .» -> «operators.»: la puntuación va pegada
                    lead = ""
                out.append(lead + _html.escape(tr, quote=False) + trail)
            else:
                out.append(ch)
    return "".join(out)


def _rewrite_links(html_text, lang):
    def repl(m):
        url = m.group(2)
        path, sep, rest = re.match(r"([^#?]*)([#?]?)(.*)", url).groups()
        key = ES_PATH_TO_KEY.get(path or "/")
        if key is None:
            return m.group(0)
        return m.group(1) + path_for(key, lang) + sep + rest + m.group(3)
    return re.sub(r'(\shref=")(/[^"]*|/)(")', repl, html_text)


# ── Etiquetas de <head> ──────────────────────────────────────────────────────

def _strip_head_meta(text):
    text = re.sub(r"<title[^>]*>.*?</title>\s*", "", text, count=1, flags=re.S | re.I)
    text = re.sub(r'<meta\s+name="description"[^>]*>\s*', "", text, flags=re.I)
    text = re.sub(r'<meta\s+property="og:[^"]*"[^>]*>\s*', "", text, flags=re.I)
    return text


def _meta_of(text, key, es_desc_fallback):
    """Metadatos en español, tomados de la plantilla (fuente única de verdad del sitio en español)."""
    def grab(pat):
        m = re.search(pat, text, re.S | re.I)
        return _html.unescape(norm(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else ""
    title = grab(r"<title[^>]*>(.*?)</title>")
    desc = grab(r'<meta\s+name="description"\s+content="([^"]*)"') or es_desc_fallback
    return {"slug": None, "title": title, "description": desc,
            "og_title": grab(r'<meta\s+property="og:title"\s+content="([^"]*)"') or title,
            "og_description": grab(r'<meta\s+property="og:description"\s+content="([^"]*)"') or desc,
            "crumb": ES_CRUMB.get(key, title)}


def _faq(html_text):
    items = []
    for q, a in re.findall(r"<details[^>]*>\s*<summary[^>]*>(.*?)</summary>\s*<p[^>]*>(.*?)</p>", html_text, re.S):
        q = _html.unescape(norm(re.sub(r"<[^>]+>", " ", q)))
        a = _html.unescape(norm(re.sub(r"<[^>]+>", " ", a)))
        a = re.sub(r"\s+([,.;:])", r"\1", a)
        if q and a:
            items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})
    return {"@type": "FAQPage", "mainEntity": items} if items else None


def _jsonld(key, lang, html_text, meta, base, articles, app_desc_es):
    org_id = base + "/#org"
    graph = [{"@type": "Organization", "@id": org_id, "name": "Origen", "url": base + "/",
              "logo": base + "/static/icon-512.png",
              "parentOrganization": {"@type": "Organization", "name": "Selva Ecomarketing",
                                     "legalName": "Selva Marketing Sostenible S.A.C.", "taxID": "20615597393",
                                     "url": "https://selvagencia.com/"}}]
    url = base + path_for(key, lang)
    home = base + path_for("landing", lang)
    if key == "landing":
        graph.append({"@type": "WebSite", "@id": home + "#website", "url": home, "name": "Origen",
                      "inLanguage": lang, "publisher": {"@id": org_id}})
        desc = app_desc_es if lang == "es" else LANGS[lang].get("app_description") or app_desc_es
        graph.append({"@type": "SoftwareApplication", "name": "Origen", "url": home,
                      "applicationCategory": "BusinessApplication", "operatingSystem": "Web, Android, iOS",
                      "inLanguage": lang, "publisher": {"@id": org_id}, "description": desc})
    if key in FAQ_PAGES:
        faq = _faq(html_text)
        if faq:
            graph.append(faq)
    if key in articles:
        pub, mod = articles[key]
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.S | re.I)
        headline = _html.unescape(norm(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else meta["title"]
        graph.append({"@type": "Article", "@id": url + "#article", "mainEntityOfPage": url,
                      "headline": headline, "description": meta["description"], "inLanguage": lang,
                      "image": base + "/static/og.png", "datePublished": pub, "dateModified": mod,
                      "author": {"@id": org_id}, "publisher": {"@id": org_id}})
    if key != "landing":
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Origen", "item": home},
            {"@type": "ListItem", "position": 2, "name": meta.get("crumb") or meta["title"], "item": url}]})
    return {"@context": "https://schema.org", "@graph": graph}


# ── Selector de idioma ───────────────────────────────────────────────────────

_SEL_CSS = """<style>
.og-lang{position:relative;display:inline-block}
.og-lang>summary{list-style:none;cursor:pointer;user-select:none;display:inline-flex;align-items:center;gap:6px}
.og-lang>summary::-webkit-details-marker{display:none}
.og-lang>summary::after{content:"";width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid currentColor;opacity:.85}
.og-lang[open]>summary::after{transform:rotate(180deg)}
.og-lang:not([open])>ul{display:none}
.og-lang>ul{position:absolute;right:0;top:calc(100% + 8px);z-index:60;margin:0;padding:8px;list-style:none;
 background:#fff;border:1px solid #C3CAD5;box-shadow:0 12px 32px rgba(11,13,18,.18);
 display:grid;grid-template-columns:1fr 1fr;gap:2px 10px;width:max-content;max-width:min(360px,calc(100vw - 32px));
 max-height:70vh;overflow:auto;text-align:left}
.og-lang>ul a{display:block;padding:6px 10px;color:#0B0D12!important;text-decoration:none;font:500 14px/1.3 system-ui,-apple-system,'Segoe UI',sans-serif;white-space:nowrap;letter-spacing:0;text-transform:none}
.og-lang>ul a:hover,.og-lang>ul a:focus{background:#EEF2FA}
.og-lang>ul a[aria-current]{font-weight:700;background:#F3F5F9}
@media(max-width:520px){
 .og-lang>ul{position:fixed;left:16px;right:16px;top:64px;width:auto;max-width:none}
 .nl>.og-lang{display:none}
}
</style>"""

# Solo en las traducciones: palabras largas (búlgaro, finés, húngaro…) en los sellos del landing.
_I18N_CSS = """<style>
.sello .big{max-width:100%;overflow-wrap:anywhere;hyphens:auto}
h1,h2,h3{overflow-wrap:break-word;hyphens:auto}
@media(max-width:520px){.sello .big{font-size:clamp(24px,8vw,38px)}
 .nl>.og-lang{display:inline-block!important}
 .nl .og-lang>summary.lang{display:inline-flex!important;margin-right:0}
 .nl a[href="/panel"]{display:none}
 .nav .btn-ochre{padding:9px 10px;font-size:11px}}
</style>"""

_POS_PROPS = ("position", "top", "right", "bottom", "left", "z-index", "margin", "margin-left",
              "margin-right", "margin-top", "margin-bottom")


def _selector(button_html, key, lang):
    attrs = dict(re.findall(r'\s([a-zA-Z-]+)(?:="([^"]*)")?', re.match(r"<button([^>]*)>", button_html).group(1)))
    style = attrs.get("style") or ""
    det_style, sum_style = [], []
    for decl in [d.strip() for d in style.split(";") if d.strip()]:
        prop = decl.split(":", 1)[0].strip().lower()
        (det_style if prop in _POS_PROPS else sum_style).append(decl)
    cls = attrs.get("class")
    label = (LANGS[lang].get("labels") or {}).get("language") if lang != "es" else ES_LABELS["language"]
    items = []
    for code in active():
        cur = ' aria-current="true"' if code == lang else ""
        items.append('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>' % (
            path_for(key, code), code, code, cur, NATIVE[code]))
    return ('<details class="og-lang" data-noi18n%s>'
            '<summary data-langbtn%s%s aria-label="%s">%s</summary><ul>%s</ul></details>') % (
        (' style="%s"' % ";".join(det_style)) if det_style else "",
        (' class="%s"' % cls) if cls else "",
        (' style="%s"' % ";".join(sum_style)) if sum_style else "",
        _html.escape(label or "Idioma", quote=True), lang.upper(), "".join(items))


# ── Render ───────────────────────────────────────────────────────────────────

def render(key, lang, base, seo_desc=None, articles=None, app_desc_es=""):
    """HTML final de la página `key` en `lang` (con caché en memoria: las plantillas no cambian en caliente)."""
    ck = (key, lang, base)
    if ck in _CACHE:
        return _CACHE[ck]
    fname = PAGES[key][0]
    with open(os.path.join(WEB_DIR, fname), encoding="utf-8") as f:
        text = variant(f.read(), lang)
    articles = articles or {}
    es_meta = _meta_of(text, key, (seo_desc or {}).get(fname, ""))
    if lang == "es":
        meta = es_meta
    else:
        d = LANGS[lang]
        meta = dict(es_meta)
        meta.update({k: v for k, v in d["pages"][key].items() if v})
        text = translate(text, d["strings"], d["js"])
        text = _rewrite_links(text, lang)
        text = re.sub(r'<html\s+lang="[^"]*"', '<html lang="%s"' % lang, text, count=1)
    text = _strip_head_meta(text)
    text = text.replace('content="/static/', 'content="' + base + '/static/')
    m = re.search(r"<button[^>]*\sdata-langbtn[^>]*>.*?</button>", text, re.S)
    if m:
        text = text[:m.start()] + _selector(m.group(0), key, lang) + text[m.end():]
    url = base + path_for(key, lang)
    esc = lambda v: _html.escape(v or "", quote=True)
    tags = ["<title>%s</title>" % _html.escape(meta["title"], quote=False),
            '<meta name="description" content="%s">' % esc(meta["description"]),
            '<meta name="i18n-server" content="%s">' % lang,
            '<link rel="canonical" href="%s">' % url]
    for code in active():
        tags.append('<link rel="alternate" hreflang="%s" href="%s">' % (code, base + path_for(key, code)))
    xdef = "en" if "en" in LANGS else "es"
    tags.append('<link rel="alternate" hreflang="x-default" href="%s">' % (base + path_for(key, xdef)))
    og_locale = "es_LA" if lang == "es" else LANGS[lang].get("og_locale", lang)
    tags += ['<meta property="og:type" content="%s">' % ("article" if key in articles else "website"),
             '<meta property="og:site_name" content="Origen">',
             '<meta property="og:locale" content="%s">' % og_locale,
             '<meta property="og:url" content="%s">' % url,
             '<meta property="og:title" content="%s">' % esc(meta.get("og_title") or meta["title"]),
             '<meta property="og:description" content="%s">' % esc(meta.get("og_description") or meta["description"]),
             '<meta property="og:image" content="%s/static/og.png">' % base,
             '<meta name="twitter:card" content="summary_large_image">']
    if lang != "es" and LANGS[lang].get("dyn"):
        tags.append("<script>window.ORIGEN_T=%s;</script>" % json.dumps(LANGS[lang]["dyn"], ensure_ascii=False).replace("</", "<\\/"))
    tags.append('<script type="application/ld+json">%s</script>' % json.dumps(
        _jsonld(key, lang, text, meta, base, articles, app_desc_es), ensure_ascii=False).replace("</", "<\\/"))
    tags.append(_SEL_CSS)
    if lang != "es":
        tags.append(_I18N_CSS)
    tail = [t for t in tags if t.startswith("<script") or t.startswith("<style")]
    top = [t for t in tags if t not in tail]
    # arriba, justo después de <meta charset>; el JSON-LD y el CSS del selector, al final del <head>
    text = re.sub(r"(<head[^>]*>\s*(?:<meta\s+charset=[^>]*>)?)", lambda mm: mm.group(1) + "\n" + "\n".join(top) + "\n", text, count=1)
    text = text.replace("</head>", "\n".join(tail) + "\n</head>", 1)
    _CACHE[ck] = text
    return text


def sitemap(base):
    urls = []
    for key in PAGES:
        alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (c, base + path_for(key, c)) for c in active())
        xdef = "en" if "en" in LANGS else "es"
        alts += '<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % (base + path_for(key, xdef))
        for code in active():
            urls.append("<url><loc>%s</loc>%s</url>" % (base + path_for(key, code), alts))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            + "".join(urls) + "</urlset>\n")
