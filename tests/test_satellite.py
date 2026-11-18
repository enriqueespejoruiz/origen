"""Evidencia satelital propia: reglas de escalamiento y dossier (sin red)."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", os.path.join(tempfile.gettempdir(), "origen_test_data"))
from app.models import Lot, Plot, GeoPoint, DeforestationFinding as DF
from app import satellite as S, dossier


def _lot():
    return Lot("LOT-SAT", "Ana", "Coop", "cocoa", "PE", "Junín",
               [Plot("P1", [GeoPoint(-11.48, -74.42)], 2.0)], "", "", "800")


def test_summary_and_flags():
    res = {"s2": {"ndvi_2020": 0.8, "ndvi_now": 0.5, "loss_pct": 22.0}, "s1": {"delta_db": -4.2}}
    line = S.summary(res)
    assert "0.80→0.50" in line and "22%" in line and "-4.2 dB" in line
    assert S.summary({}) == ""


def test_satellite_can_only_raise(monkeypatch):
    from app import deforestation as D, config
    monkeypatch.setattr(config, "GFW_API_KEY", "x")
    monkeypatch.setattr(config, "SAT_ENABLED", True)
    monkeypatch.setattr(D, "_gfw_loss_ha", lambda g: 0.0)
    monkeypatch.setattr(D, "_gfw_alerts", lambda g: 0.0)
    monkeypatch.setattr(D, "_gfw_protected", lambda g: False)
    monkeypatch.setattr(D, "_jrc_forest", lambda p: 0.1)
    monkeypatch.setattr(S, "sentinel1_change", lambda p, today=None: {"delta_db": -0.1})
    monkeypatch.setattr(S, "assess", lambda p, img=None, radar=False:
                        {"s2": {"ndvi_2020": .8, "ndvi_now": .4, "loss_pct": 30.0, "valid_pct": 100}, "flag": True})
    f = D.check_plots(_lot())[0]
    assert f.risk == "review" and "evidencia propia" in f.detail and f.sat
    monkeypatch.setattr(S, "assess", lambda p, img=None, radar=False:
                        {"s2": {"ndvi_2020": .8, "ndvi_now": .8, "loss_pct": 0.0, "valid_pct": 100}, "flag": False})
    assert D.check_plots(_lot())[0].risk == "negligible"


def test_dossier_includes_satellite_section(tmp_path):
    from PIL import Image
    img = tmp_path / "s2.jpg"
    Image.new("RGB", (732, 390), (40, 120, 60)).save(img)
    sat = {"s2": {"ndvi_2020": .8, "ndvi_now": .78, "loss_pct": 1.0, "image": str(img),
                  "base_dates": ["2020-08-28"], "recent_dates": ["2026-11-12"]}, "s1": {"delta_db": -0.2}}
    f = DF("P1", "negligible", False, "ok", None, sat)
    for lang in ("es", "en"):
        pdf = dossier.build_pdf(_lot(), [f], "Resumen.", "", str(tmp_path), lang)
        assert os.path.getsize(pdf) > 4000


def test_read_accepts_tiff_extension(monkeypatch):
    """Regresión 18-nov: el chequeo JRC dejaba CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif' y GDAL rechazaba
    el radar Sentinel-1 (archivos .tiff con token SAS). _read debe aceptar .tiff siempre."""
    import rasterio
    from app import satellite
    seen = {}

    class Env:
        def __init__(self, **kw): seen.update(kw)
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def boom(href):
        raise RuntimeError("stop")
    monkeypatch.setattr(rasterio, "Env", Env)
    monkeypatch.setattr(rasterio, "open", boom)
    monkeypatch.setenv("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    try:
        satellite._read("https://x.blob.core.windows.net/a/iw-vh.rtc.tiff?sig=1", (0, 0, 1, 1))
    except RuntimeError:
        pass
    assert ".tiff" in seen["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"]
