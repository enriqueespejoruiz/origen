import os, json, datetime
from .geo import lot_to_geojson, traces_properties, plot_geometry
from . import config

def _ensure(d): os.makedirs(d, exist_ok=True)

def overall_risk(findings):
    if any(f.risk == "high" for f in findings): return "high"
    if any(f.risk == "review" for f in findings): return "review"
    return "negligible"

def build_geojson(lot, out_dir):
    _ensure(out_dir)
    path = os.path.join(out_dir, f"{lot.lot_id}.geojson")
    with open(path, "w") as f:
        json.dump(lot_to_geojson(lot), f, indent=2)
    return path

def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# commodity -> (HS code, nombre cientifico, etiqueta)
_HS = {
    "coffee": ("0901", "Coffea arabica", "Café"),
    "cafe":   ("0901", "Coffea arabica", "Café"),
    "cacao":  ("1801", "Theobroma cacao", "Cacao"),
    "cocoa":  ("1801", "Theobroma cacao", "Cacao"),
}

# --- Textos del dossier en dos idiomas (ES / EN) ---
_STR = {
    "es": {
        "subtitle": "Dossier de Diligencia Debida — EUDR", "lot": "Lote",
        "risk": {"negligible": "Riesgo insignificante", "review": "Requiere revisión", "high": "Deforestación detectada"},
        "h_product": "Producto", "l_product": "Producto", "l_hs": "Código HS", "l_sci": "Nombre científico",
        "l_country": "País de producción", "l_qty": "Cantidad", "qty_ph": "— (a indicar por lote)",
        "h_origin": "Origen y cadena", "l_producer": "Productor", "l_coop": "Cooperativa / proveedor",
        "l_region": "Región", "l_nplots": "N° de parcelas",
        "h_buyer": "Operador importador (UE) — a completar/validar por el comprador",
        "l_bname": "Nombre / razón social", "l_bcountry": "País", "l_eori": "Número EORI", "l_dds": "N° de referencia DDS",
        "h_plots": "Parcelas y verificación",
        "th": ["Parcela", "Latitud", "Longitud", "Área (ha)", "Riesgo", "Detalle / fuente"],
        "poly": "polígono", "verts": "vért.",
        "geom_note": ("Geometría: las parcelas mayores a 4 ha se registran como polígono de límites (vértices GPS); "
                      "las coordenadas mostradas corresponden al centroide. "
                      "Fecha de corte de deforestación: 31 de diciembre de 2020."),
        "map_cap": "Ubicación de la parcela sobre imagen satelital (Esri World Imagery).",
        "h_photo": "Foto del predio", "photo_cap": "Fotografía tomada en campo durante la captura (evidencia de origen).",
        "dq": "Calidad de datos: ", "dq_ok": "Calidad de datos: geometría válida (sin auto-intersecciones; área plausible).",
        "h_eval": "Evaluación de diligencia debida",
        "h_legal": "Legalidad y tenencia — a validar con el proveedor",
        "l_title": "Título o derecho de uso del predio", "l_env": "Conformidad ambiental y forestal",
        "l_labor": "Conformidad laboral y derechos de terceros",
        "h_sources": "Fuentes de datos",
        "sources": ("Verificación por parcela cruzando cuatro fuentes satelitales: Hansen Global Forest Change "
                    "(UMD/Google, vía Global Forest Watch), JRC Global Forest Cover 2020 (mapa de referencia de la UE), "
                    "GFW Integrated Alerts (RADD/GLAD) y áreas protegidas (WDPA)."),
        "h_verify": "Verificación",
        "verify": ("<b>Verificación de autenticidad</b><br/>Escanea el código o visita {url}/verificar — "
                   "comprueba que este dossier es auténtico y su fecha de emisión mediante su huella SHA-256 registrada por Origen."),
        "disclaimer": ("Paquete de datos de origen para sustentar la diligencia debida. El operador importador en la UE "
                       "valida la información y presenta la Declaración de Diligencia Debida en el sistema de la UE (TRACES). "
                       "Documento informativo; no constituye asesoría legal."),
    },
    "en": {
        "subtitle": "Due Diligence Dossier — EUDR", "lot": "Lot",
        "risk": {"negligible": "Negligible risk", "review": "Requires review", "high": "Deforestation detected"},
        "h_product": "Product", "l_product": "Product", "l_hs": "HS code", "l_sci": "Scientific name",
        "l_country": "Country of production", "l_qty": "Quantity", "qty_ph": "— (to be specified per lot)",
        "h_origin": "Origin & chain", "l_producer": "Producer", "l_coop": "Cooperative / supplier",
        "l_region": "Region", "l_nplots": "No. of plots",
        "h_buyer": "EU importer (operator) — to be completed/validated by the buyer",
        "l_bname": "Name / legal entity", "l_bcountry": "Country", "l_eori": "EORI number", "l_dds": "DDS reference no.",
        "h_plots": "Plots & verification",
        "th": ["Plot", "Latitude", "Longitude", "Area (ha)", "Risk", "Detail / source"],
        "poly": "polygon", "verts": "verts.",
        "geom_note": ("Geometry: plots larger than 4 ha are recorded as a boundary polygon (GPS vertices); "
                      "coordinates shown are the centroid. Deforestation cut-off date: 31 December 2020."),
        "map_cap": "Plot location over satellite imagery (Esri World Imagery).",
        "h_photo": "Field photo", "photo_cap": "Photograph taken in the field during capture (origin evidence).",
        "dq": "Data quality: ", "dq_ok": "Data quality: valid geometry (no self-intersections; plausible area).",
        "h_eval": "Due diligence assessment",
        "h_legal": "Legality & tenure — to be validated with the supplier",
        "l_title": "Land title or use right", "l_env": "Environmental & forest compliance",
        "l_labor": "Labour compliance & third-party rights",
        "h_sources": "Data sources",
        "sources": ("Per-plot verification cross-checking four satellite sources: Hansen Global Forest Change "
                    "(UMD/Google, via Global Forest Watch), JRC Global Forest Cover 2020 (EU reference map), "
                    "GFW Integrated Alerts (RADD/GLAD) and protected areas (WDPA)."),
        "h_verify": "Verification",
        "verify": ("<b>Authenticity verification</b><br/>Scan the code or visit {url}/verificar — "
                   "confirm this dossier is authentic and its issue date via its SHA-256 hash registered by Origen."),
        "disclaimer": ("Origin data package to support due diligence. The EU importer (operator) validates the information "
                       "and submits the Due Diligence Statement in the EU system (TRACES). Informational document; not legal advice."),
    },
}

def plot_map_png(plot, out_path, size=(1000, 460)):
    """Renderiza la parcela (poligono o punto) sobre imagen satelital. None si falla (no rompe el dossier)."""
    try:
        from staticmap import StaticMap, CircleMarker, Line
    except Exception:
        return None
    try:
        url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        m = StaticMap(size[0], size[1], url_template=url, padding_x=50, padding_y=50)
        pts = plot.points
        if len(pts) >= 3:
            ring = [(p.lon, p.lat) for p in pts]; ring.append(ring[0])
            m.add_line(Line(ring, "#E0C277", 4))
            img = m.render()
        else:
            p = pts[0]
            m.add_marker(CircleMarker((p.lon, p.lat), "#0B3D2E", 24))
            m.add_marker(CircleMarker((p.lon, p.lat), "#E0C277", 13))
            img = m.render(zoom=16)
        img.convert("RGB").save(out_path, "JPEG", quality=82)
        return out_path
    except Exception as e:
        print("map render error:", repr(e))
        return None

def _img_dims(path, max_w, max_h):
    """Dimensiones que respetan el aspecto de la imagen dentro de un recuadro."""
    try:
        from PIL import Image as PILImage
        iw, ih = PILImage.open(path).size
        r = min(max_w / iw, max_h / ih)
        return iw * r, ih * r
    except Exception:
        return max_w, max_h

def _qr_png(data, out_dir, lot_id):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(data); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        p = os.path.join(out_dir, f"{lot_id}_qr.png")
        img.save(p)
        return p
    except Exception as e:
        print("qr error:", repr(e)); return None

def build_pdf(lot, findings, narrative, profile, out_dir, lang=None, photo_path=None):
    """Dossier de Diligencia Debida EUDR (Art. 9) — bilingüe (ES/EN)."""
    _ensure(out_dir)
    lang = (lang or (lot.extra or {}).get("lang") or "es")
    if lang not in _STR: lang = "es"
    t = _STR[lang]
    path = os.path.join(out_dir, f"{lot.lot_id}_dossier.pdf")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    PINE = colors.HexColor("#0B3D2E"); GOLD = colors.HexColor("#C2A04C")
    IVORY = colors.HexColor("#FBFAF6"); LINE = colors.HexColor("#E3DECF")
    INK = colors.HexColor("#16211B"); MUT = colors.HexColor("#6F726B")
    RC = {"negligible": colors.HexColor("#2E8B5E"), "review": GOLD, "high": colors.HexColor("#C0392B")}

    risk = overall_risk(findings)
    hs = _HS.get((lot.commodity or "").lower(), ("—", "—", lot.commodity or "—"))
    today = datetime.date.today().isoformat()

    P  = ParagraphStyle("P",  textColor=INK, fontName="Helvetica", fontSize=9.5, leading=13)
    H  = ParagraphStyle("H",  textColor=PINE, fontName="Helvetica-Bold", fontSize=12, spaceBefore=12, spaceAfter=5)
    S  = ParagraphStyle("S",  textColor=MUT, fontName="Helvetica", fontSize=8, leading=11)
    Kk = ParagraphStyle("Kk", textColor=MUT, fontName="Helvetica", fontSize=9)
    Kv = ParagraphStyle("Kv", textColor=INK, fontName="Helvetica-Bold", fontSize=9.5)
    TH = ParagraphStyle("TH", textColor=colors.white, fontName="Helvetica-Bold", fontSize=8.5)
    TD = ParagraphStyle("TD", textColor=INK, fontName="Helvetica", fontSize=8.5, leading=11)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.3*cm, bottomMargin=1.3*cm, leftMargin=1.6*cm, rightMargin=1.6*cm)
    W = doc.width
    E = []

    def kv(rows, fill=False):
        data = [[Paragraph(_esc(a), Kk), Paragraph(_esc(b) if b else "&nbsp;", Kv)] for a, b in rows]
        tb = Table(data, colWidths=[W*0.34, W*0.66])
        st = [("LINEBELOW",(0,0),(-1,-1),0.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
              ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
              ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]
        if fill: st.append(("BACKGROUND",(1,0),(1,-1),IVORY))
        tb.setStyle(TableStyle(st)); return tb

    head = Table([[Paragraph('<b>ORIGEN</b>  <font color="#C2A04C">·  ' + t["subtitle"] + '</font>',
                             ParagraphStyle("ht", textColor=colors.white, fontSize=13, leading=16))],
                  [Paragraph(f'{t["lot"]} {_esc(lot.lot_id)}  ·  {today}',
                             ParagraphStyle("hm", textColor=colors.HexColor("#CFE0D6"), fontSize=8))]], colWidths=[W])
    head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PINE),("LEFTPADDING",(0,0),(-1,-1),12),
                              ("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(0,0),12),
                              ("BOTTOMPADDING",(0,0),(0,0),2),("TOPPADDING",(0,1),(0,1),0),("BOTTOMPADDING",(0,1),(0,1),12)]))
    E += [head, Spacer(1, 10)]

    rb = Table([[Paragraph(f'<b>{t["risk"][risk].upper()}</b>', ParagraphStyle("rb", textColor=colors.white, fontSize=11))]], colWidths=[W])
    rb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),RC[risk]),("LEFTPADDING",(0,0),(-1,-1),12),
                            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    E += [rb]

    E += [Paragraph(t["h_product"], H),
          kv([(t["l_product"], hs[2]), (t["l_hs"], hs[0]), (t["l_sci"], hs[1]),
              (t["l_country"], lot.country), (t["l_qty"], lot.quantity or t["qty_ph"])])]
    E += [Paragraph(t["h_origin"], H),
          kv([(t["l_producer"], lot.producer_name or "—"), (t["l_coop"], lot.cooperative or "—"),
              (t["l_region"], lot.region or "—"), (t["l_nplots"], str(len(lot.plots)))])]
    _bx = (lot.extra or {}).get("buyer", {}) if isinstance(lot.extra, dict) else {}
    E += [Paragraph(t["h_buyer"], H),
          kv([(t["l_bname"], _bx.get("name", "")), (t["l_bcountry"], _bx.get("country", "")),
              (t["l_eori"], _bx.get("eori", "")), (t["l_dds"], _bx.get("dds", ""))], fill=True)]

    E += [Paragraph(t["h_plots"], H)]
    rows = [[Paragraph(x, TH) for x in t["th"]]]
    for f, pl in zip(findings, lot.plots):
        poly = len(pl.points) >= 3
        if pl.points:
            clat = sum(p.lat for p in pl.points) / len(pl.points)
            clon = sum(p.lon for p in pl.points) / len(pl.points)
        else:
            clat = clon = None
        label = _esc(f.plot_id) + (f'<br/><font size="7" color="#6F726B">{t["poly"]} · {len(pl.points)} {t["verts"]}</font>' if poly else "")
        rows.append([Paragraph(label, TD),
                     Paragraph(f"{clat:.5f}" if clat is not None else "—", TD),
                     Paragraph(f"{clon:.5f}" if clon is not None else "—", TD),
                     Paragraph(f"{pl.area_ha}" if pl.area_ha else "—", TD),
                     Paragraph(_esc(f.risk), TD),
                     Paragraph(_esc(f.detail), TD)])
    ptab = Table(rows, colWidths=[W*x for x in (0.12, 0.17, 0.17, 0.10, 0.12, 0.32)])
    ptab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PINE),("GRID",(0,0),(-1,-1),0.4,LINE),
                              ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),
                              ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),
                              ("BOTTOMPADDING",(0,0),(-1,-1),4),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, IVORY])]))
    E += [ptab, Spacer(1, 5), Paragraph(t["geom_note"], S)]
    for pl in lot.plots:
        try:
            mp = os.path.join(out_dir, f"{lot.lot_id}_{pl.plot_id}_map.jpg")
            if plot_map_png(pl, mp):
                from reportlab.platypus import Image as RLImage
                E += [Spacer(1, 6), RLImage(mp, width=W, height=W * 0.46), Paragraph(t["map_cap"], S)]
        except Exception as e:
            print("map embed error:", repr(e))
    try:
        from . import geo as _geo
        _gi = []
        for _pl in lot.plots: _gi += _geo.geometry_issues(_pl)
        E += [Paragraph((t["dq"] + "; ".join(_esc(x) for x in _gi) + ".") if _gi else t["dq_ok"], S)]
    except Exception:
        pass

    if photo_path and os.path.exists(photo_path):
        try:
            from reportlab.platypus import Image as RLImage
            pw, ph = _img_dims(photo_path, W * 0.6, 8.0 * cm)
            E += [Paragraph(t["h_photo"], H), RLImage(photo_path, width=pw, height=ph), Paragraph(t["photo_cap"], S)]
        except Exception as e:
            print("photo embed error:", repr(e))

    E += [Paragraph(t["h_eval"], H), Paragraph(_esc(narrative), P)]
    _lg = (lot.extra or {}).get("legality", {}) if isinstance(lot.extra, dict) else {}
    E += [Paragraph(t["h_legal"], H),
          kv([(t["l_title"], _lg.get("title", "")), (t["l_env"], _lg.get("env", "")),
              (t["l_labor"], _lg.get("labor", ""))], fill=True)]

    E += [Paragraph(t["h_sources"], H), Paragraph(t["sources"], S)]

    _qr = _qr_png(config.PUBLIC_BASE_URL + "/verificar?lot=" + lot.lot_id, out_dir, lot.lot_id)
    if _qr:
        from reportlab.platypus import Image as RLImage
        vt = Table([[RLImage(_qr, width=2.4 * cm, height=2.4 * cm),
                     Paragraph(t["verify"].replace("{url}", _esc(config.PUBLIC_BASE_URL)), S)]],
                    colWidths=[2.9 * cm, W - 2.9 * cm])
        vt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        E += [Paragraph(t["h_verify"], H), vt]

    E += [Spacer(1, 10), Paragraph(t["disclaimer"], S)]

    doc.build(E)
    return path

# ============================================================================
#  Envío / consignación: dossier CONSOLIDADO (agrega N lotes en una sola DDS)
# ============================================================================

import re as _re

def parse_qty_kg(q):
    """Extrae un número de kg de un texto libre ('1,200 kg' -> 1200.0). 0 si no hay."""
    if not q:
        return 0.0
    s = str(q).replace(",", "")
    m = _re.search(r"[\d.]+", s)
    try:
        return float(m.group()) if m else 0.0
    except Exception:
        return 0.0

def consignment_verdict(items):
    """Veredicto global del envío a partir de (lot, findings). high>review>negligible."""
    risks = [f.risk for _lot, findings in items for f in findings]
    if any(r == "high" for r in risks):
        return "high"
    if any(r == "review" for r in risks):
        return "review"
    return "negligible"

def _plot_centroid(pl):
    if pl.points:
        return (sum(p.lat for p in pl.points) / len(pl.points),
                sum(p.lon for p in pl.points) / len(pl.points))
    return (None, None)

def build_consignment_geojson(cons, items, out_dir):
    """FeatureCollection (formato TRACES) con TODAS las parcelas del envío, cada una etiquetada con lote y riesgo."""
    _ensure(out_dir)
    cid = cons.get("consignment_id")
    feats = []; fid = 0
    for lot, findings in items:
        risk_by = {f.plot_id: f.risk for f in findings}
        for pl in lot.plots:
            props = traces_properties(lot, pl, risk=risk_by.get(pl.plot_id))
            props["consignment_id"] = cid
            feats.append({"type": "Feature", "properties": props,
                          "geometry": plot_geometry(pl), "id": fid})
            fid += 1
    path = os.path.join(out_dir, f"{cid}.geojson")
    with open(path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, indent=2)
    return path

_CSTR = {
    "es": {
        "subtitle": "Dossier consolidado de envío — EUDR", "cons": "Envío",
        "verdict": {"negligible": "APTO — LIBRE DE DEFORESTACIÓN", "review": "REVISIÓN REQUERIDA",
                    "high": "ACCIÓN REQUERIDA — SEGREGAR PARCELAS"},
        "h_summary": "Resumen del envío",
        "l_id": "Identificación", "l_commodity": "Producto", "l_hs": "Código HS", "l_country": "País de producción",
        "l_dest": "Destino (UE)", "l_buyer": "Comprador / importador (UE)",
        "l_nlots": "N° de lotes", "l_nplots": "N° de parcelas", "l_vol": "Volumen total (aprox.)",
        "excl_h": "Parcelas a excluir o segregar antes de la DDS",
        "excl_t": ("Las siguientes parcelas presentan deforestación posterior al 31-dic-2020. El EUDR prohíbe "
                   "mezclarlas con material conforme: deben excluirse físicamente del envío (segregación) o "
                   "sustentarse documentalmente antes de presentar la declaración."),
        "rev_h": "Parcelas a sustentar",
        "rev_t": "Las siguientes parcelas requieren verificación documental adicional antes de la declaración:",
        "clean_t": ("Todas las parcelas del envío están libres de deforestación posterior al corte. El envío puede "
                    "consolidarse en una sola Declaración de Diligencia Debida."),
        "h_lots": "Lotes del envío", "th_lots": ["Lote", "Productor", "Región", "Parcelas", "Cantidad", "Riesgo"],
        "h_plots": "Geolocalización de todas las parcelas (Art. 9 EUDR)",
        "th_plots": ["Lote", "Parcela", "Latitud", "Longitud", "Área (ha)", "Riesgo"],
        "agg_h": "Trazabilidad y agregación",
        "agg_note": ("Una operación comercial puede acopiar de muchas parcelas, productores y regiones. El EUDR permite "
                     "una sola Declaración de Diligencia Debida por envío que liste la geolocalización de todas las "
                     "parcelas del mismo operador, producto y país. No se admite compensación de volúmenes (mass balance): "
                     "si una parcela está observada, su volumen debe segregarse o sustentarse, y no puede mezclarse con "
                     "material conforme."),
        "h_sources": "Fuentes de datos",
        "sources": ("Verificación por parcela basada en Hansen Global Forest Change (UMD/Google, vía Global Forest Watch), "
                    "JRC Global Forest Cover 2020, GFW Integrated Alerts (RADD/GLAD) y áreas protegidas (WDPA)."),
        "h_verify": "Verificación",
        "verify": ("<b>Verificación de autenticidad</b><br/>Escanea el código o visita {url}/verificar — "
                   "comprueba que este dossier consolidado es auténtico y su fecha de emisión mediante su huella SHA-256."),
        "disclaimer": ("Paquete de datos de origen consolidado para sustentar la diligencia debida de un envío. El operador "
                       "importador en la UE valida la información y presenta la DDS en el sistema de la UE (TRACES). "
                       "Documento informativo; no constituye asesoría legal."),
        "kg": "kg", "none": "—",
    },
    "en": {
        "subtitle": "Consolidated consignment dossier — EUDR", "cons": "Consignment",
        "verdict": {"negligible": "ELIGIBLE — DEFORESTATION-FREE", "review": "REVIEW REQUIRED",
                    "high": "ACTION REQUIRED — SEGREGATE PLOTS"},
        "h_summary": "Consignment summary",
        "l_id": "Identification", "l_commodity": "Product", "l_hs": "HS code", "l_country": "Country of production",
        "l_dest": "Destination (EU)", "l_buyer": "Buyer / importer (EU)",
        "l_nlots": "No. of lots", "l_nplots": "No. of plots", "l_vol": "Total volume (approx.)",
        "excl_h": "Plots to exclude or segregate before the DDS",
        "excl_t": ("The following plots show deforestation after 31 Dec 2020. The EUDR prohibits mixing them with "
                   "compliant material: they must be physically excluded from the consignment (segregation) or "
                   "substantiated before submitting the statement."),
        "rev_h": "Plots to substantiate",
        "rev_t": "The following plots require additional documentary verification before the statement:",
        "clean_t": ("All plots in the consignment are free of post-cutoff deforestation. The consignment can be "
                    "consolidated into a single Due Diligence Statement."),
        "h_lots": "Lots in the consignment", "th_lots": ["Lot", "Producer", "Region", "Plots", "Quantity", "Risk"],
        "h_plots": "Geolocation of all plots (EUDR Art. 9)",
        "th_plots": ["Lot", "Plot", "Latitude", "Longitude", "Area (ha)", "Risk"],
        "agg_h": "Traceability & aggregation",
        "agg_note": ("A commercial operation may aggregate from many plots, producers and regions. The EUDR allows a "
                     "single Due Diligence Statement per consignment listing the geolocation of all plots of the same "
                     "operator, product and country. No volume offsetting (mass balance) is allowed: if a plot is flagged, "
                     "its volume must be segregated or substantiated, and cannot be mixed with compliant material."),
        "h_sources": "Data sources",
        "sources": ("Per-plot verification based on Hansen Global Forest Change (UMD/Google, via Global Forest Watch), "
                    "JRC Global Forest Cover 2020, GFW Integrated Alerts (RADD/GLAD) and protected areas (WDPA)."),
        "h_verify": "Verification",
        "verify": ("<b>Authenticity verification</b><br/>Scan the code or visit {url}/verificar — "
                   "confirm this consolidated dossier is authentic and its issue date via its SHA-256 hash."),
        "disclaimer": ("Consolidated origin data package to support the due diligence of a consignment. The EU importer "
                       "(operator) validates the information and submits the DDS in the EU system (TRACES). "
                       "Informational document; not legal advice."),
        "kg": "kg", "none": "—",
    },
}

def build_consignment_pdf(cons, items, out_dir, lang=None):
    """Dossier CONSOLIDADO de un envío: veredicto global + todas las parcelas + segregación. Bilingüe."""
    _ensure(out_dir)
    lang = (lang or (cons.get("extra") or {}).get("lang") or "es")
    if lang not in _CSTR:
        lang = "es"
    t = _CSTR[lang]
    cid = cons.get("consignment_id")
    path = os.path.join(out_dir, f"{cid}_dossier.pdf")

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    PINE = colors.HexColor("#0B3D2E"); GOLD = colors.HexColor("#C2A04C")
    IVORY = colors.HexColor("#FBFAF6"); LINE = colors.HexColor("#E3DECF")
    INK = colors.HexColor("#16211B"); MUT = colors.HexColor("#6F726B")
    RC = {"negligible": colors.HexColor("#2E8B5E"), "review": GOLD, "high": colors.HexColor("#C0392B")}

    verdict = consignment_verdict(items)
    commodity = cons.get("commodity") or (items[0][0].commodity if items else "")
    hs = _HS.get((commodity or "").lower(), ("—", "—", commodity or "—"))
    today = datetime.date.today().isoformat()

    n_plots = sum(len(lot.plots) for lot, _ in items)
    total_kg = sum(parse_qty_kg(lot.quantity) for lot, _ in items)
    excl, rev = [], []
    for lot, findings in items:
        for f in findings:
            if f.risk == "high": excl.append((lot.lot_id, f.plot_id))
            elif f.risk == "review": rev.append((lot.lot_id, f.plot_id))

    P  = ParagraphStyle("P",  textColor=INK, fontName="Helvetica", fontSize=9.5, leading=13)
    H  = ParagraphStyle("H",  textColor=PINE, fontName="Helvetica-Bold", fontSize=12, spaceBefore=12, spaceAfter=5)
    S  = ParagraphStyle("S",  textColor=MUT, fontName="Helvetica", fontSize=8, leading=11)
    Kk = ParagraphStyle("Kk", textColor=MUT, fontName="Helvetica", fontSize=9)
    Kv = ParagraphStyle("Kv", textColor=INK, fontName="Helvetica-Bold", fontSize=9.5)
    TH = ParagraphStyle("TH", textColor=colors.white, fontName="Helvetica-Bold", fontSize=8.5)
    TD = ParagraphStyle("TD", textColor=INK, fontName="Helvetica", fontSize=8.5, leading=11)
    CL = ParagraphStyle("CL", textColor=INK, fontName="Helvetica", fontSize=9, leading=12)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.3*cm, bottomMargin=1.3*cm, leftMargin=1.6*cm, rightMargin=1.6*cm)
    W = doc.width
    E = []

    def kv(rows, fill=False):
        data = [[Paragraph(_esc(a), Kk), Paragraph(_esc(b) if b else "&nbsp;", Kv)] for a, b in rows]
        tb = Table(data, colWidths=[W*0.34, W*0.66])
        st = [("LINEBELOW",(0,0),(-1,-1),0.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
              ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
              ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]
        if fill: st.append(("BACKGROUND",(1,0),(1,-1),IVORY))
        tb.setStyle(TableStyle(st)); return tb

    head = Table([[Paragraph('<b>ORIGEN</b>  <font color="#C2A04C">·  ' + t["subtitle"] + '</font>',
                             ParagraphStyle("ht", textColor=colors.white, fontSize=13, leading=16))],
                  [Paragraph(f'{t["cons"]} {_esc(cid)}  ·  {_esc(cons.get("name",""))}  ·  {today}',
                             ParagraphStyle("hm", textColor=colors.HexColor("#CFE0D6"), fontSize=8))]], colWidths=[W])
    head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PINE),("LEFTPADDING",(0,0),(-1,-1),12),
                              ("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(0,0),12),
                              ("BOTTOMPADDING",(0,0),(0,0),2),("TOPPADDING",(0,1),(0,1),0),("BOTTOMPADDING",(0,1),(0,1),12)]))
    E += [head, Spacer(1, 10)]

    rb = Table([[Paragraph(f'<b>{t["verdict"][verdict]}</b>', ParagraphStyle("rb", textColor=colors.white, fontSize=11))]], colWidths=[W])
    rb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),RC[verdict]),("LEFTPADDING",(0,0),(-1,-1),12),
                            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    E += [rb]

    E += [Paragraph(t["h_summary"], H),
          kv([(t["l_id"], cons.get("name","") or cid), (t["l_commodity"], hs[2]), (t["l_hs"], hs[0]),
              (t["l_country"], "PE"), (t["l_dest"], cons.get("destination","")), (t["l_buyer"], cons.get("buyer","")),
              (t["l_nlots"], str(len(items))), (t["l_nplots"], str(n_plots)),
              (t["l_vol"], (f"{total_kg:,.0f} {t['kg']}" if total_kg > 0 else t["none"]))], fill=True)]

    # Veredicto explicado + segregación
    def _callout(title, body, lines, accent):
        head_p = Paragraph(f'<b>{_esc(title)}</b>', ParagraphStyle("co", textColor=accent, fontName="Helvetica-Bold", fontSize=10))
        body_p = Paragraph(_esc(body), CL)
        cells = [[head_p], [body_p]]
        if lines:
            cells.append([Paragraph(" · ".join(_esc(x) for x in lines), ParagraphStyle("col", textColor=INK, fontName="Helvetica-Bold", fontSize=9, leading=13))])
        tb = Table(cells, colWidths=[W])
        tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),IVORY),("BOX",(0,0),(-1,-1),0.6,accent),
                                ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
                                ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
        return tb

    E += [Spacer(1, 6)]
    if excl:
        E += [_callout(t["excl_h"], t["excl_t"], [f"{l} · {p}" for l, p in excl], RC["high"])]
    if rev:
        E += [Spacer(1, 6), _callout(t["rev_h"], t["rev_t"], [f"{l} · {p}" for l, p in rev], RC["review"])]
    if not excl and not rev:
        E += [_callout(t["verdict"]["negligible"], t["clean_t"], [], RC["negligible"])]

    # Tabla de lotes
    E += [Paragraph(t["h_lots"], H)]
    lrows = [[Paragraph(x, TH) for x in t["th_lots"]]]
    for lot, findings in items:
        lr = overall_risk(findings)
        lrows.append([Paragraph(_esc(lot.lot_id), TD), Paragraph(_esc(lot.producer_name or "—"), TD),
                      Paragraph(_esc(lot.region or "—"), TD), Paragraph(str(len(lot.plots)), TD),
                      Paragraph(_esc(lot.quantity or "—"), TD), Paragraph(_esc(t["verdict"][lr].split("—")[0].strip().title()), TD)])
    lt = Table(lrows, colWidths=[W*x for x in (0.17, 0.25, 0.16, 0.12, 0.15, 0.15)])
    lt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PINE),("GRID",(0,0),(-1,-1),0.4,LINE),
                            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),
                            ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),
                            ("BOTTOMPADDING",(0,0),(-1,-1),4),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, IVORY])]))
    lt.repeatRows = 1
    E += [lt]

    # Tabla de TODAS las parcelas (geolocalización Art. 9)
    E += [Paragraph(t["h_plots"], H)]
    prows = [[Paragraph(x, TH) for x in t["th_plots"]]]
    for lot, findings in items:
        risk_by = {f.plot_id: f.risk for f in findings}
        for pl in lot.plots:
            clat, clon = _plot_centroid(pl)
            poly = len(pl.points) >= 3
            label = _esc(pl.plot_id) + (f'<br/><font size="7" color="#6F726B">pol · {len(pl.points)}v</font>' if poly else "")
            prows.append([Paragraph(_esc(lot.lot_id), TD), Paragraph(label, TD),
                          Paragraph(f"{clat:.5f}" if clat is not None else "—", TD),
                          Paragraph(f"{clon:.5f}" if clon is not None else "—", TD),
                          Paragraph(f"{pl.area_ha}" if pl.area_ha else "—", TD),
                          Paragraph(_esc(risk_by.get(pl.plot_id, "")), TD)])
    pt = Table(prows, colWidths=[W*x for x in (0.17, 0.15, 0.20, 0.20, 0.13, 0.15)])
    pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PINE),("GRID",(0,0),(-1,-1),0.4,LINE),
                            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),
                            ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),
                            ("BOTTOMPADDING",(0,0),(-1,-1),4),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, IVORY])]))
    pt.repeatRows = 1
    E += [pt]

    E += [Paragraph(t["agg_h"], H), Paragraph(t["agg_note"], S)]
    E += [Paragraph(t["h_sources"], H), Paragraph(t["sources"], S)]

    _qr = _qr_png(config.PUBLIC_BASE_URL + "/verificar?lot=" + cid, out_dir, cid)
    if _qr:
        from reportlab.platypus import Image as RLImage
        vt = Table([[RLImage(_qr, width=2.4 * cm, height=2.4 * cm),
                     Paragraph(t["verify"].replace("{url}", _esc(config.PUBLIC_BASE_URL)), S)]],
                    colWidths=[2.9 * cm, W - 2.9 * cm])
        vt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        E += [Paragraph(t["h_verify"], H), vt]

    E += [Spacer(1, 10), Paragraph(t["disclaimer"], S)]

    doc.build(E)
    return path
