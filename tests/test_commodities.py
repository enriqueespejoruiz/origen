"""Pruebas del catálogo de productos EUDR y del respaldo de modelo Gemini (sin red ni GCP)."""
import os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_DD = os.path.join(tempfile.gettempdir(), "origen_test_data")
os.makedirs(_DD, exist_ok=True)
os.environ.setdefault("DATA_DIR", _DD)

from app.models import Lot, Plot, GeoPoint, DeforestationFinding as DF
from app import commodities as cm, geo, dossier


def test_norm_aliases_cover_all_seven():
    assert cm.norm("café") == "coffee" and cm.norm("Cacao") == "cocoa"
    assert cm.norm("Palma aceitera") == "oil_palm" and cm.norm("palma") == "oil_palm"
    assert cm.norm("soja") == "soya" and cm.norm("jebe") == "rubber"
    assert cm.norm("Madera") == "wood" and cm.norm("ganado bovino") == "cattle"
    assert cm.norm("") == "coffee"                       # valor por defecto histórico
    assert set(cm.ORDER) == set(cm.CATALOG) and len(cm.ORDER) == 7


def test_labels_and_info_bilingual():
    assert cm.label("oil_palm", "es") == "Palma aceitera" and cm.label("oil_palm", "en") == "Oil palm"
    assert cm.info("cacao", "en") == ("1801", "Theobroma cacao", "Cocoa")
    hs, sci, lbl = cm.info("wood", "es")
    assert hs.startswith("44") and "especie" in sci and lbl == "Madera"
    hs, sci, _ = cm.info("wood", "en", {"species": "Tornillo — Cedrelinga cateniformis", "hs": "4407"})
    assert hs == "4407" and sci.startswith("Tornillo")
    assert cm.info("quinua") == ("—", "—", "quinua")      # desconocido: no inventa partida


def test_cattle_points_any_size():
    assert cm.point_any_size("ganado") is True and cm.point_any_size("coffee") is False


def _lot(com, qty, area=2.0):
    return Lot("LOT-C", "Ana", "Coop", com, "PE", "Ucayali",
               [Plot("P1", [GeoPoint(-8.4, -74.6)], area)], "", "", qty)


def test_volume_check_only_where_a_ceiling_exists():
    assert geo.volume_issues(_lot("coffee", "9000 kg"))          # 4.500 kg/ha > 2.500: alerta
    assert not geo.volume_issues(_lot("cacao", "3000 kg"))        # 1.500 kg/ha: plausible
    assert geo.volume_issues(_lot("oil_palm", "50000 kg")) == []  # sin techo: no se evalúa
    assert geo.volume_issues(_lot("cattle", "999999")) == []


def test_dossier_for_new_commodities(tmp_path):
    for com, lang in (("oil_palm", "en"), ("wood", "es"), ("cattle", "es"), ("rubber", "en")):
        lot = _lot(com, "1000 kg", 6.0)
        pdf = dossier.build_pdf(lot, [DF("P1", "negligible", False, "ok")], "Resumen.", "", str(tmp_path), lang)
        assert os.path.getsize(pdf) > 2000


def test_gemini_falls_back_when_model_retired(monkeypatch):
    from app import gemini, config
    calls = []

    class Models:
        def generate_content(self, model, contents, config=None):
            calls.append(model)
            if model == "modelo-retirado":
                raise RuntimeError("404 NOT_FOUND: Publisher model was not found")
            class R: text = "ok"
            return R()

    class Client: models = Models()

    monkeypatch.setattr(gemini, "_client", lambda: Client())
    monkeypatch.setattr(gemini, "_ACTIVE", None)
    monkeypatch.setattr(config, "GEMINI_MODEL", "modelo-retirado")
    monkeypatch.setattr(config, "GEMINI_FALLBACKS", ["modelo-vigente"])
    assert gemini.generate("hola").text == "ok"
    assert calls == ["modelo-retirado", "modelo-vigente"]
    assert gemini.active_model() == "modelo-vigente"
    calls.clear()
    gemini.generate("otra")                                   # recuerda el modelo que funcionó
    assert calls == ["modelo-vigente"]


def test_gemini_does_not_mask_other_errors(monkeypatch):
    import pytest
    from app import gemini, config

    class Models:
        def generate_content(self, model, contents, config=None):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    class Client: models = Models()

    monkeypatch.setattr(gemini, "_client", lambda: Client())
    monkeypatch.setattr(gemini, "_ACTIVE", None)
    monkeypatch.setattr(config, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(config, "GEMINI_FALLBACKS", ["m2"])
    with pytest.raises(RuntimeError):
        gemini.generate("x")


def test_private_responses_are_not_cacheable():
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    r = c.get("/lots/LOT-NOEXISTE/dossier")
    assert "no-store" in r.headers.get("cache-control", "")
    assert r.headers.get("cdn-cache-control") == "no-store"
    assert "no-store" not in c.get("/").headers.get("cache-control", "")
