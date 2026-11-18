"""Importación de KML, KMZ, GPX y Shapefile (.zip)."""
import io, os, sys, zipfile, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_data"))
from app import importer

KML = b"""<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Ana Quispe</name><ExtendedData><Data name="producto"><value>cacao</value></Data></ExtendedData>
<Polygon><outerBoundaryIs><LinearRing><coordinates>-74.42,-11.48,0 -74.41,-11.48,0 -74.41,-11.47,0 -74.42,-11.48,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
<Placemark><name>Beto</name><Point><coordinates>-76.37,-6.47,0</coordinates></Point></Placemark></Document></kml>"""

GPX = b"""<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
<wpt lat="-6.47" lon="-76.37"><name>Rosa</name></wpt>
<trk><name>Juan</name><trkseg><trkpt lat="-11.48" lon="-74.42"/><trkpt lat="-11.48" lon="-74.41"/><trkpt lat="-11.47" lon="-74.41"/></trkseg></trk></gpx>"""


def test_kml_and_kmz():
    rows, errs = importer.parse(KML, "fincas.kml")
    assert not errs and len(rows) == 2
    assert rows[0]["producer"] == "Ana Quispe" and rows[0]["commodity"] == "cacao" and len(rows[0]["polygon"]) == 4
    assert rows[1]["lat"] == -6.47 and rows[1]["lon"] == -76.37
    buf = io.BytesIO(); zipfile.ZipFile(buf, "w").writestr("doc.kml", KML)
    rows, errs = importer.parse(buf.getvalue(), "fincas.kmz")
    assert len(rows) == 2


def test_gpx():
    rows, errs = importer.parse(GPX, "recorrido.gpx")
    assert {r["producer"] for r in rows} == {"Rosa", "Juan"}
    assert any(r["polygon"] for r in rows)


def test_shapefile_zip(tmp_path):
    import shapefile
    base = str(tmp_path / "parcelas")
    w = shapefile.Writer(base, shapeType=shapefile.POLYGON)
    w.field("PRODUCTOR", "C"); w.field("CULTIVO", "C")
    w.poly([[[-74.42, -11.48], [-74.41, -11.48], [-74.41, -11.47], [-74.42, -11.48]]])
    w.record("Carla", "cafe"); w.close()
    open(base + ".prj", "w").write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, "w")
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        z.write(base + ext, "parcelas" + ext)
    z.close()
    rows, errs = importer.parse(buf.getvalue(), "parcelas.zip")
    assert not errs and rows[0]["producer"] == "Carla" and rows[0]["commodity"] == "cafe"
    assert abs(rows[0]["polygon"][0].lat + 11.48) < 1e-6


def test_bad_files_report_errors():
    assert importer.parse(b"<kml>", "x.kml")[1]
    assert importer.parse(b"no zip", "x.zip")[1]
