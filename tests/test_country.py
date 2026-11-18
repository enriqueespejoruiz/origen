"""País de producción: ya no es «PE» fijo. Lote CO → dossier y GeoJSON dicen CO; importación con
columna `pais`/`country`; un lote antiguo sin país cae en PE (sin migrar nada)."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_country"))

from app import countries as ct, geo, dossier, importer, storage, config
from app.models import Lot, Plot, GeoPoint, DeforestationFinding as DF


def _lot(country, lot_id="LOT-CO1"):
    return Lot(lot_id, "Ana", "Coop", "coffee", country, "Huila", [Plot("P1", [GeoPoint(2.19, -75.63)], 1.0)])


def test_norm_and_fallback():
    assert ct.norm("co") == "CO" and ct.norm("Colombia") == "CO" and ct.norm("Perú") == "PE"
    assert ct.norm("Costa de Marfil") == "CI" and ct.norm("zz") == ""
    assert ct.of_lot({"country": ""}) == "PE" and ct.of_lot({}) == "PE"      # lote viejo
    assert ct.of_lot({"country": "BR"}) == "BR"
    assert ct.name("CO", "en") == "Colombia" and ct.name("DE") == "Alemania"


def test_geojson_uses_lot_country(tmp_path):
    gj = json.load(open(dossier.build_geojson(_lot("CO"), str(tmp_path))))
    assert {f["properties"]["ProducerCountry"] for f in gj["features"]} == {"CO"}
    old = _lot("", "LOT-OLD")
    gj = json.load(open(dossier.build_geojson(old, str(tmp_path))))
    assert gj["features"][0]["properties"]["ProducerCountry"] == "PE"


def test_dossier_prints_country(tmp_path):
    from pypdf import PdfReader
    pdf = dossier.build_pdf(_lot("CO"), [DF("P1", "negligible", False, "ok")], "n", "", str(tmp_path), "es")
    txt = "".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    assert "Colombia (CO)" in txt and "Perú" not in txt


def test_import_country_column(monkeypatch):
    monkeypatch.setattr(config, "GCP_PROJECT", "")
    csv = ("productor,producto,pais,region,lat,lon,area_ha\n"
           "Ana,cafe,CO,Huila,2.19,-75.63,1\n"
           "Kofi,cacao,Ghana,Ashanti,6.69,-1.62,2\n"
           "Luis,cafe,,Cusco,-13.5,-72.0,1\n"
           "Mal,cafe,XX,Nada,1,1,1\n").encode()
    rows, errs = importer.parse(csv, "p.csv")
    assert len(rows) == 3 and any("XX" in e for e in errs)
    created = importer.create_lots(rows, "c1", "Coop", "a@b.c", default_country="EC")
    by = {c["producer"]: storage.load_lot(c["lot_id"])["country"] for c in created}
    assert by == {"Ana": "CO", "Kofi": "GH", "Luis": "EC"}          # vacío → país de la organización


def test_capture_and_coop_country(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(config, "GCP_PROJECT", "")
    monkeypatch.setattr(config, "AGENT_API_KEY", "k")
    h = {"X-Agent-Key": "k", "X-Agent-Coop": "piloto-co"}
    c = TestClient(main.app)
    r = c.post("/capture", headers=h, json={"producer": "Ana", "commodity": "cafe", "country": "co",
                                            "region": "Huila", "lat": 2.19, "lon": -75.63, "area_ha": 1})
    assert r.status_code == 200
    assert storage.load_lot(r.json()["lot_id"])["country"] == "CO"
    assert c.post("/capture", headers=h, json={"producer": "X", "country": "Narnia", "lat": 1, "lon": 1}).status_code == 400
    lst = c.get("/api/countries?lang=en").json()["countries"]
    assert lst[0]["code"] == "PE" and any(x["code"] == "CI" for x in lst)


def test_consignment_multi_country(tmp_path):
    from pypdf import PdfReader
    items = [(_lot("CO", "LOT-A"), [DF("P1", "negligible", False, "")]),
             (_lot("PE", "LOT-B"), [DF("P1", "negligible", False, "")])]
    cons = {"consignment_id": "ENV-T", "name": "Mixto", "commodity": "coffee", "lot_ids": ["LOT-A", "LOT-B"]}
    pdf = dossier.build_consignment_pdf(cons, items, str(tmp_path), "es")
    txt = "".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    assert "Colombia (CO)" in txt and "Perú (PE)" in txt
