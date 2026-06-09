import os, json, datetime
from .geo import lot_to_geojson

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

def build_pdf(lot, findings, narrative, profile, out_dir):
    """Dossier de Diligencia Debida EUDR (Art. 9) con identidad de marca Origen."""
    _ensure(out_dir)
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
    RL = {"negligible": "Riesgo insignificante", "review": "Requiere revisión", "high": "Deforestación detectada"}

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
        t = Table(data, colWidths=[W*0.34, W*0.66])
        st = [("LINEBELOW",(0,0),(-1,-1),0.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
              ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
              ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]
        if fill: st.append(("BACKGROUND",(1,0),(1,-1),IVORY))
        t.setStyle(TableStyle(st)); return t

    head = Table([[Paragraph('<b>ORIGEN</b>  <font color="#C2A04C">·  Dossier de Diligencia Debida — EUDR</font>',
                             ParagraphStyle("ht", textColor=colors.white, fontSize=13, leading=16))],
                  [Paragraph(f'Lote {_esc(lot.lot_id)}  ·  {today}',
                             ParagraphStyle("hm", textColor=colors.HexColor("#CFE0D6"), fontSize=8))]], colWidths=[W])
    head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PINE),("LEFTPADDING",(0,0),(-1,-1),12),
                              ("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(0,0),12),
                              ("BOTTOMPADDING",(0,0),(0,0),2),("TOPPADDING",(0,1),(0,1),0),("BOTTOMPADDING",(0,1),(0,1),12)]))
    E += [head, Spacer(1, 10)]

    rb = Table([[Paragraph(f'<b>{RL[risk].upper()}</b>', ParagraphStyle("rb", textColor=colors.white, fontSize=11))]], colWidths=[W])
    rb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),RC[risk]),("LEFTPADDING",(0,0),(-1,-1),12),
                            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    E += [rb]

    E += [Paragraph("Producto", H),
          kv([("Producto", hs[2]), ("Código HS", hs[0]), ("Nombre científico", hs[1]),
              ("País de producción", lot.country), ("Cantidad", "— (a indicar por lote)")])]
    E += [Paragraph("Origen y cadena", H),
          kv([("Productor", lot.producer_name or "—"), ("Cooperativa / proveedor", lot.cooperative or "—"),
              ("Región", lot.region or "—"), ("N° de parcelas", str(len(lot.plots)))])]
    E += [Paragraph("Operador importador (UE) — a completar por el comprador", H),
          kv([("Nombre / razón social", ""), ("Dirección", ""), ("Número EORI", ""), ("N° de referencia DDS", "")], fill=True)]

    E += [Paragraph("Parcelas y verificación", H)]
    rows = [[Paragraph(x, TH) for x in ["Parcela", "Latitud", "Longitud", "Área (ha)", "Riesgo", "Detalle / fuente"]]]
    for f, pl in zip(findings, lot.plots):
        pt = pl.points[0] if pl.points else None
        rows.append([Paragraph(_esc(f.plot_id), TD),
                     Paragraph(f"{pt.lat:.5f}" if pt else "—", TD),
                     Paragraph(f"{pt.lon:.5f}" if pt else "—", TD),
                     Paragraph(f"{pl.area_ha}" if pl.area_ha else "—", TD),
                     Paragraph(_esc(f.risk), TD),
                     Paragraph(_esc(f.detail), TD)])
    ptab = Table(rows, colWidths=[W*x for x in (0.12, 0.17, 0.17, 0.10, 0.12, 0.32)])
    ptab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PINE),("GRID",(0,0),(-1,-1),0.4,LINE),
                              ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),
                              ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),
                              ("BOTTOMPADDING",(0,0),(-1,-1),4),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, IVORY])]))
    E += [ptab, Spacer(1, 5), Paragraph("Fecha de corte de deforestación: 31 de diciembre de 2020.", S)]

    E += [Paragraph("Evaluación de diligencia debida", H), Paragraph(_esc(narrative), P), Spacer(1, 4),
          Paragraph("Legalidad: producción declarada conforme a la legislación del país de origen (a verificar con el proveedor).", S)]

    E += [Paragraph("Fuentes de datos", H),
          Paragraph("Verificación basada en Hansen Global Forest Change (UMD/Google, vía Global Forest Watch). "
                    "Referencias EUDR: JRC Global Forest Cover 2020 (mapa de referencia de la UE), "
                    "GFW Integrated Alerts (RADD/GLAD), áreas protegidas (WDPA) y Geobosques/MINAM (Perú).", S)]

    E += [Spacer(1, 10),
          Paragraph("Paquete de datos de origen para sustentar la diligencia debida. El operador importador en la UE "
                    "valida la información y presenta la Declaración de Diligencia Debida en el sistema de la UE (TRACES). "
                    "Documento informativo; no constituye asesoría legal.", S)]

    doc.build(E)
    return path
