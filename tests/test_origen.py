"""Pruebas unitarias de Origen (sin red ni GCP). Cubren TRACES, agregación de envíos y PDFs."""
import os, sys, json, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_DD = os.path.join(tempfile.gettempdir(), "origen_test_data")
os.makedirs(_DD, exist_ok=True)
os.environ.setdefault("DATA_DIR", _DD)

from app.models import Lot, Plot, GeoPoint, DeforestationFinding as DF
from app import dossier, geo, scoring


def _lot_point():
    return Lot("LOT-PT", "Juan", "Coop", "coffee", "PE", "Cusco",
               [Plot("P1", [GeoPoint(-13.531234, -71.967891)], 2.0)], "", "", "1200")


def _lot_poly():
    return Lot("LOT-PL", "Maria", "Coop", "coffee", "PE", "San Martin",
               [Plot("P1", [GeoPoint(-6.5, -76.3), GeoPoint(-6.5, -76.29), GeoPoint(-6.49, -76.29)], 5.4)],
               "", "", "800")


def test_parse_qty_kg():
    assert dossier.parse_qty_kg("1,200 kg") == 1200.0
    assert dossier.parse_qty_kg("") == 0.0
    assert dossier.parse_qty_kg("3.5") == 3.5
    assert dossier.parse_qty_kg(None) == 0.0


def test_consignment_verdict():
    a = [(_lot_point(), [DF("P1", "negligible", False, "")])]
    assert dossier.consignment_verdict(a) == "negligible"
    assert dossier.consignment_verdict(a + [(_lot_poly(), [DF("P1", "high", True, "")])]) == "high"
    assert dossier.consignment_verdict([(_lot_point(), [DF("P1", "review", False, "")])]) == "review"


def test_traces_point_has_area_and_6_decimals():
    f = geo.lot_to_geojson(_lot_point())["features"][0]
    assert f["geometry"]["type"] == "Point"
    assert f["properties"]["ProducerCountry"] == "PE"
    assert f["properties"]["ProducerName"] == "Juan"
    assert f["properties"]["Area"] == 2.0
    assert f["geometry"]["coordinates"] == [-71.967891, -13.531234]   # [lon, lat], 6 decimales


def test_traces_polygon_has_no_area_and_closes_ring():
    f = geo.lot_to_geojson(_lot_poly())["features"][0]
    assert f["geometry"]["type"] == "Polygon"
    assert "Area" not in f["properties"]
    ring = f["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]


def test_consignment_geojson_traces(tmp_path):
    cons = {"consignment_id": "ENV-TST", "name": "x", "commodity": "coffee", "extra": {"lang": "es"}}
    items = [(_lot_point(), [DF("P1", "negligible", False, "ok")]),
             (_lot_poly(), [DF("P1", "high", True, "loss")])]
    gj = dossier.build_consignment_geojson(cons, items, str(tmp_path))
    g = json.load(open(gj))
    assert len(g["features"]) == 2
    assert g["features"][0]["properties"]["ProducerCountry"] == "PE"
    assert g["features"][1]["properties"]["risk"] == "high"
    assert [x["id"] for x in g["features"]] == [0, 1]


def test_consignment_pdf_builds(tmp_path):
    cons = {"consignment_id": "ENV-TST", "name": "Contenedor 1", "commodity": "coffee",
            "destination": "Hamburgo", "buyer": "X GmbH", "extra": {"lang": "es"}}
    items = [(_lot_point(), [DF("P1", "negligible", False, "ok")]),
             (_lot_poly(), [DF("P1", "high", True, "loss")])]
    pdf = dossier.build_consignment_pdf(cons, items, str(tmp_path), "es")
    assert os.path.getsize(pdf) > 2000
    pdf_en = dossier.build_consignment_pdf({**cons, "consignment_id": "ENV-EN"}, items, str(tmp_path), "en")
    assert os.path.getsize(pdf_en) > 2000


def test_lot_pdf_builds_both_langs(tmp_path):
    lot = _lot_point()
    fnd = [DF("P1", "negligible", False, "post-2020: sin perdida")]
    for lang in ("es", "en"):
        pdf = dossier.build_pdf(lot, fnd, "Narrativa de prueba.", "", str(tmp_path), lang)
        assert os.path.getsize(pdf) > 2000


def test_geometry_issues_flags_invalid_polygon():
    # polígono con auto-intersección (bowtie)
    bow = Plot("P1", [GeoPoint(0, 0), GeoPoint(0, 1), GeoPoint(1, 0), GeoPoint(1, 1)], 1.0)
    issues = geo.geometry_issues(bow)
    assert any("inválido" in i or "TRACES" in i for i in issues)


# ---- Simulador what-if + score de confianza ----
def _lot_multi():
    return Lot("LOT-WI", "Juan", "Coop", "coffee", "PE", "Cusco",
               [Plot("P1", [GeoPoint(-12.0, -72.0)], 1.0),
                Plot("P2", [GeoPoint(-12.1, -72.1)], 2.0),
                Plot("P3", [GeoPoint(-12.2, -72.2)], 1.0)],
               "", "", "3,000 kg", extra={"legality": {"title": "Título 123"}})


def _findings_multi():
    return [DF("P1", "negligible", False, "ok"),
            DF("P2", "high", True, "pérdida 2022"),
            DF("P3", "review", False, "borde")]


def test_simulate_distributes_kg_by_area_and_status():
    lot, fnd = _lot_multi(), _findings_multi()
    assert scoring.suggest_exclusions(fnd) == ["P2"]
    sim = scoring.simulate(lot, fnd, ["P2"])           # excluir solo la observada
    kg = {p["plot_id"]: p["kg"] for p in sim["plots"]}
    assert kg["P2"] == 1500                              # 2 de 4 ha → mitad de 3000
    assert sim["kg_remaining"] == 1500 and sim["status_after"] == "revisar"  # queda P3
    sim2 = scoring.simulate(lot, fnd, ["P2", "P3"])     # excluir ambas
    assert sim2["status_after"] == "apto" and sim2["all_clear"] is True


def test_confidence_score_bounds_and_factors():
    sc = scoring.confidence_score(_lot_multi(), _findings_multi())
    assert 0 <= sc["score"] <= 100 and sc["band"] in ("alta", "media", "baja")
    assert sum(f["weight"] for f in sc["factors"]) == 100


def test_simulate_consignment_excludes_flagged_lots():
    class L:
        def __init__(s, i, q, p): s.lot_id, s.quantity, s.producer_name = i, q, p
    items = [(L("L1", "1000 kg", "Ana"), [DF("PA", "negligible", False, "")]),
             (L("L2", "800 kg", "Beto"), [DF("PB", "high", True, "")]),
             (L("L3", "1200 kg", "Caro"), [DF("PC", "review", False, "")])]
    assert scoring.suggest_exclusions_consignment(items) == ["L2"]
    cs = scoring.simulate_consignment(items, ["L2"])
    assert cs["kg_remaining"] == 2200 and cs["n_remaining"] == 2
    assert cs["status_after"] == "revisar"


# ---- Portabilidad: export ZIP "llévate tu data" ----
def test_export_zip_has_open_formats():
    import io, json, zipfile
    from app import portability
    lots = [{"lot_id": "LOT-A", "producer_name": "Ana", "cooperative": "CoopX", "commodity": "coffee",
             "country": "PE", "region": "Cusco", "quantity": "1,200 kg", "overall_risk": "negligible",
             "plots": [{"plot_id": "P1", "points": [{"lat": -13.5, "lon": -71.9}], "area_ha": 2.0}],
             "created_at": "2026-06-26"}]
    data, n = portability.build_export_zip({"id": "coop1", "name": "Coop Demo"}, lots)
    z = zipfile.ZipFile(io.BytesIO(data))
    assert n == 1
    for f in ("lotes.csv", "lotes.geojson", "manifest.json", "LEEME.txt"):
        assert f in z.namelist()
    gj = json.loads(z.read("lotes.geojson"))
    assert gj["type"] == "FeatureCollection" and len(gj["features"]) == 1
    assert "ProducerName" in gj["features"][0]["properties"]
    assert json.loads(z.read("manifest.json"))["n_lots"] == 1
