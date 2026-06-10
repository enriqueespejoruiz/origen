import os, json, datetime
from .geo import lot_to_geojson
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
        "dq": "Calidad de datos: ", "dq_ok": "Calidad de datos: geometría válida (sin auto-intersecciones; área plausible).",
        "h_eval": "Evaluación de diligencia debida",
        "h_legal": "Legalidad y tenencia — a validar con el proveedor",
        "l_title": "Título o derecho de uso del predio", "l_env": "Conformidad ambiental y forestal",
        "l_labor": "Conformidad laboral y derechos de terceros",
        "h_sources": "Fuentes de datos",
        "sources": ("Verificación basada en Hansen Global Forest Change (UMD/Google, vía Global Forest Watch). "
                    "Referencias EUDR: JRC Global Forest Cover 2020 (mapa de referencia de la UE), "
                    "GFW Integrated Alerts (RADD/GLAD), áreas protegidas (WDPA) y Geobosques/MINAM (Perú)."),
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
        "dq": "Data quality: ", "dq_ok": "Data quality: valid geometry (no self-intersections; plausible area).",
        "h_eval": "Due diligence assessment",
        "h_legal": "Legality & tenure — to be validated with the supplier",
        "l_title": "Land title or use right", "l_env": "Environmental & forest compliance",
        "l_labor": "Labour compliance & third-party rights",
        "h_sources": "Data sources",
        "sources": ("Verification based on Hansen Global Forest Change (UMD/Google, via Global Forest Watch). "
                    "EUDR references: JRC Global Forest Cover 2020 (EU reference map), "
                    "GFW Integrated Alerts (RADD/GLAD), protected areas (WDPA) and Geobosques/MINAM (Peru)."),
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

def build_pdf(lot, findings, narrative, profile, out_dir, lang=None):
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
