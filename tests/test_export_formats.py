"""Exportar a KML/KMZ/Shapefile/Excel y volver a importar con nuestro importador (ida y vuelta)."""
import os, sys, io, zipfile, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_export"))

from app import exporter, importer

RING = [[-74.422, -11.480], [-74.420, -11.480], [-74.420, -11.482], [-74.422, -11.482], [-74.422, -11.480]]
GJ = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"ProducerName": "Ana Quispe", "Area": 2.0, "lot_id": "LOT-1"},
     "geometry": {"type": "Polygon", "coordinates": [RING]}},
    {"type": "Feature", "properties": {"ProducerName": "Luis Rojas", "Area": 1.2, "lot_id": "LOT-2"},
     "geometry": {"type": "Point", "coordinates": [-74.43, -11.49]}}]}


def _rows(data, name):
    return importer.parse(data, name)


def _check(rows):
    rows = rows[0] if isinstance(rows, tuple) else rows
    assert len(rows) == 2
    txt = repr(rows)
    assert "Ana Quispe" in txt and "Luis Rojas" in txt


def test_kml_roundtrip():
    b = exporter.convert(GJ, "kml")
    assert b.startswith(b"<?xml") and b"Ana Quispe" in b
    _check(_rows(b, "x.kml"))


def test_kmz_roundtrip():
    b = exporter.convert(GJ, "kmz")
    assert zipfile.ZipFile(io.BytesIO(b)).namelist() == ["doc.kml"]
    _check(_rows(b, "x.kmz"))


def test_shapefile_zip():
    b = exporter.convert(GJ, "shp", "LOT-1")
    names = zipfile.ZipFile(io.BytesIO(b)).namelist()
    assert "LOT-1_poligonos.shp" in names and "LOT-1_puntos.prj" in names
    import shapefile
    z = zipfile.ZipFile(io.BytesIO(b))
    r = shapefile.Reader(shp=io.BytesIO(z.read("LOT-1_poligonos.shp")), dbf=io.BytesIO(z.read("LOT-1_poligonos.dbf")))
    assert len(r.shapes()[0].points) == 5 and r.records()[0][0] == "Ana Quispe"


def test_xlsx():
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(exporter.convert(GJ, "xlsx"))).active
    head = [c.value for c in ws[1]]
    assert "wkt" in head and ws.max_row == 3
    assert ws.cell(2, head.index("wkt") + 1).value.startswith("POLYGON")


def test_unknown_format():
    import pytest
    with pytest.raises(ValueError):
        exporter.convert(GJ, "dwg")


def test_endpoints(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main, config, storage
    from app.models import Lot, Plot, GeoPoint
    monkeypatch.setattr(config, "GCP_PROJECT", "")
    monkeypatch.setattr(config, "AGENT_API_KEY", "k")
    h = {"X-Agent-Key": "k", "X-Agent-Coop": "piloto-exp"}
    pts = [GeoPoint(-11.480, -74.422), GeoPoint(-11.480, -74.420), GeoPoint(-11.482, -74.420)]
    storage.save_lot(Lot("LOT-EXP1", "Ana", "Coop", "coffee", "PE", "Junín", [Plot("P1", pts, 2.0)], coop_id="piloto-exp"))
    c = TestClient(main.app)
    r = c.get("/lots/LOT-EXP1/export.kmz", headers=h)
    assert r.status_code == 200 and "LOT-EXP1.kmz" in r.headers["content-disposition"]
    assert c.get("/lots/LOT-EXP1/export.dwg", headers=h).status_code == 404
    assert c.get("/lots/LOT-EXP1/export.kml").status_code in (401, 403)
    r = c.get("/api/lots/export.xlsx", headers=h)
    assert r.status_code == 200 and r.content[:2] == b"PK"
