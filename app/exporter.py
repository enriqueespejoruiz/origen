"""Exporta un GeoJSON (lote o envío) a otros formatos: KML, KMZ (Google Earth), Shapefile (.zip) y Excel.
Es el camino inverso del importador: la coop o el comprador abre sus parcelas en la herramienta que ya usa."""
import io, json, zipfile
from xml.sax.saxutils import escape

FORMATS = {"kml": ("application/vnd.google-earth.kml+xml", "kml"),
           "kmz": ("application/vnd.google-earth.kmz", "kmz"),
           "shp": ("application/zip", "zip"),
           "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")}

_WGS84_PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
              'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')


def _feats(gj):
    if isinstance(gj, (bytes, str)):
        gj = json.loads(gj)
    return [f for f in (gj.get("features") or []) if f.get("geometry")]


def _name(f, i):
    p = f.get("properties") or {}
    return str(p.get("ProducerName") or p.get("producer") or p.get("plot_id") or p.get("lot_id") or f"Parcela {i + 1}")


def _rings(geom):
    t, c = geom.get("type"), geom.get("coordinates")
    if t == "Polygon":
        return [c]
    if t == "MultiPolygon":
        return list(c)
    return []


def _ckml(ring):
    return " ".join(f"{x[0]},{x[1]},0" for x in ring)


def to_kml(gj, title="Origen"):
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
           f"<name>{escape(title)}</name>",
           '<Style id="p"><LineStyle><color>ff00d6ff</color><width>2</width></LineStyle>'
           '<PolyStyle><color>3300d6ff</color></PolyStyle></Style>']
    for i, f in enumerate(_feats(gj)):
        g = f["geometry"]; props = f.get("properties") or {}
        data = "".join(f'<Data name="{escape(str(k))}"><value>{escape(str(v))}</value></Data>'
                       for k, v in props.items() if not isinstance(v, (dict, list)) and v is not None)
        out.append(f"<Placemark><name>{escape(_name(f, i))}</name><styleUrl>#p</styleUrl>"
                   f"<ExtendedData>{data}</ExtendedData>")
        if g["type"] == "Point":
            x, y = g["coordinates"][:2]
            out.append(f"<Point><coordinates>{x},{y},0</coordinates></Point>")
        else:
            polys = _rings(g)
            if len(polys) > 1:
                out.append("<MultiGeometry>")
            for poly in polys:
                out.append("<Polygon><outerBoundaryIs><LinearRing><coordinates>" + _ckml(poly[0]) +
                           "</coordinates></LinearRing></outerBoundaryIs>" +
                           "".join("<innerBoundaryIs><LinearRing><coordinates>" + _ckml(h) +
                                   "</coordinates></LinearRing></innerBoundaryIs>" for h in poly[1:]) + "</Polygon>")
            if len(polys) > 1:
                out.append("</MultiGeometry>")
        out.append("</Placemark>")
    out.append("</Document></kml>")
    return "\n".join(out).encode("utf-8")


def to_kmz(gj, title="Origen"):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", to_kml(gj, title))
    return b.getvalue()


def _flat_props(feats):
    keys = []
    for f in feats:
        for k, v in (f.get("properties") or {}).items():
            if not isinstance(v, (dict, list)) and k not in keys:
                keys.append(k)
    return keys


def to_shapefile_zip(gj, base="origen"):
    """Dos capas en un .zip: polígonos y puntos (un Shapefile solo admite un tipo). WGS84 (.prj)."""
    import shapefile
    feats = _feats(gj)
    keys = _flat_props(feats)
    fld = {}
    for k in keys:                                   # DBF: nombres de 10 caracteres, únicos
        n = "".join(ch for ch in k if ch.isalnum())[:10] or "f"
        while n in fld.values():
            n = n[:8] + str(len(fld))
        fld[k] = n
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
        for kind, st in (("poligonos", shapefile.POLYGON), ("puntos", shapefile.POINT)):
            sel = [f for f in feats if (f["geometry"]["type"] == "Point") == (kind == "puntos")]
            if not sel:
                continue
            shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
            w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=st, encoding="utf-8")
            for k in keys:
                w.field(fld[k], "C", size=254)
            for f in sel:
                g = f["geometry"]
                if kind == "puntos":
                    w.point(*g["coordinates"][:2])
                else:
                    parts = []
                    for poly in _rings(g):
                        for j, ring in enumerate(poly):
                            r = [tuple(p[:2]) for p in ring]
                            parts.append(_orient(r, clockwise=(j == 0)))   # exterior horario, huecos antihorario
                    w.poly(parts)
                p = f.get("properties") or {}
                w.record(*[("" if p.get(k) is None else str(p.get(k)))[:254] for k in keys])
            w.close()
            name = f"{base}_{kind}"
            z.writestr(name + ".shp", shp.getvalue()); z.writestr(name + ".shx", shx.getvalue())
            z.writestr(name + ".dbf", dbf.getvalue()); z.writestr(name + ".prj", _WGS84_PRJ)
            z.writestr(name + ".cpg", "UTF-8")
    return zb.getvalue()


def _signed_area(r):
    return sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)) / 2.0


def _orient(r, clockwise=True):
    cw = _signed_area(r) < 0
    return r if cw == clockwise else list(reversed(r))


def to_xlsx(gj, title="Parcelas"):
    """Una fila por parcela: propiedades, centroide, número de vértices y polígono en WKT."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    feats = _feats(gj)
    keys = _flat_props(feats)
    wb = Workbook(); ws = wb.active; ws.title = title[:31]
    head = keys + ["latitud", "longitud", "tipo", "vertices", "wkt"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
    for f in feats:
        g = f["geometry"]; p = f.get("properties") or {}
        if g["type"] == "Point":
            x, y = g["coordinates"][:2]; nv = 1
            wkt = f"POINT ({x} {y})"
        else:
            ring = _rings(g)[0][0]
            pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
            x = sum(q[0] for q in pts) / len(pts); y = sum(q[1] for q in pts) / len(pts); nv = len(pts)
            wkt = "POLYGON ((" + ", ".join(f"{q[0]} {q[1]}" for q in ring) + "))"
        ws.append([p.get(k) for k in keys] + [round(y, 6), round(x, 6), g["type"], nv, wkt[:32000]])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 16
    b = io.BytesIO(); wb.save(b)
    return b.getvalue()


def convert(gj, fmt, base="origen"):
    fmt = (fmt or "").lower()
    if fmt == "kml":
        return to_kml(gj, base)
    if fmt == "kmz":
        return to_kmz(gj, base)
    if fmt == "shp":
        return to_shapefile_zip(gj, base)
    if fmt == "xlsx":
        return to_xlsx(gj)
    raise ValueError("formato no soportado")
