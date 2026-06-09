import os, json
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

def _wrap(t, n):
    words, cur, out = t.split(), "", []
    for w in words:
        if len(cur) + len(w) + 1 > n:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur: out.append(cur)
    return out

def build_pdf(lot, findings, narrative, profile, out_dir):
    _ensure(out_dir)
    path = os.path.join(out_dir, f"{lot.lot_id}_dossier.pdf")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = [h - 2 * cm]
    def line(t, size=11, dy=0.6, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(2 * cm, y[0], t[:98]); y[0] -= dy * cm
    line("Dossier de diligencia debida - EUDR", 16, 1.0, True)
    line(f"Lote: {lot.lot_id}    Producto: {lot.commodity}    Region: {lot.region}, {lot.country}")
    line(f"Productor: {lot.producer_name}    Cooperativa: {lot.cooperative}")
    line(f"Riesgo general: {overall_risk(findings).upper()}", 12, 0.9, True)
    line("Hallazgos por parcela:", 12, 0.7, True)
    for f in findings:
        line(f"  - {f.plot_id}: {f.risk} - {f.detail}", 10)
    y[0] -= 0.3 * cm; line("Resumen:", 12, 0.7, True)
    for ch in _wrap(narrative, 92): line(ch, 10, 0.5)
    y[0] -= 0.3 * cm; line("Perfil comercial:", 12, 0.7, True)
    for ch in _wrap(profile, 92): line(ch, 10, 0.5)
    c.showPage(); c.save()
    return path
