"""Alta resolución bajo pedido: pedido → cotización → aceptación → entrega → dossier (sin red ni GCP)."""
import os, sys, io, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_DD = os.path.join(tempfile.gettempdir(), "origen_test_hires")
os.makedirs(_DD, exist_ok=True)
os.environ.setdefault("DATA_DIR", _DD)

from fastapi.testclient import TestClient
from app import main, config, storage
from app.models import Lot, Plot, GeoPoint

A = {"X-Agent-Key": "k-test", "X-Agent-Coop": "piloto-hr"}


def _setup(monkeypatch, lot_id="LOT-HR1"):
    monkeypatch.setattr(config, "GCP_PROJECT", "")
    monkeypatch.setattr(config, "DATA_DIR", _DD)
    monkeypatch.setattr(config, "AGENT_API_KEY", "k-test")
    pts = [GeoPoint(-11.480, -74.422), GeoPoint(-11.480, -74.420), GeoPoint(-11.482, -74.420), GeoPoint(-11.482, -74.422)]
    lot = Lot(lot_id, "Productor demo", "Coop", "coffee", "PE", "Junín", [Plot("P1", pts, 2.0)],
              coop_id="piloto-hr")
    storage.save_lot(lot)
    storage.merge_lot(lot_id, {"overall_risk": "review"})
    for r in storage.list_hires(lot_id=lot_id):            # limpia corridas previas
        storage.save_hires({"id": r["id"], "status": "cancelada"})
    calls = []
    monkeypatch.setattr(main, "_run_process", lambda lid, lot: calls.append(lid) or {"overall_risk": "review"})
    return TestClient(main.app), calls


def _jpg():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (64, 48), (40, 120, 60)).save(b, "PNG"); return b.getvalue()


def test_full_flow(monkeypatch):
    c, calls = _setup(monkeypatch)
    r = c.post("/lots/LOT-HR1/hires", json={"period": "ambos", "note": "borde norte"}, headers=A)
    assert r.status_code == 200, r.text
    hid = r.json()["request"]["id"]
    assert r.json()["request"]["status"] == "solicitada"
    # un solo pedido abierto por lote
    assert c.post("/lots/LOT-HR1/hires", json={}, headers=A).status_code == 409
    # no se puede aceptar sin cotización ni entregar sin aceptación
    assert c.post(f"/lots/LOT-HR1/hires/{hid}/accept", headers=A).status_code == 409
    # admin ve la geometría para buscar en el archivo
    lst = c.get("/admin/hires?status=solicitada", headers=A).json()["requests"]
    mine = [x for x in lst if x["id"] == hid][0]
    assert mine["plots"][0]["geometry"]["type"] == "Polygon"
    q = c.post(f"/admin/hires/{hid}/quote", headers=A, json={"price_usd": 49,
               "options": [{"label": "Vantor 30 cm", "date": "2026-03-31", "resolution_m": 0.3, "cloud": 50, "secret": "x"}]})
    assert q.status_code == 200 and "secret" not in q.json()["quote"]["options"][0]
    files = {"file": ("img.png", _jpg(), "image/png")}
    form = {"source": "Vantor", "acquired": "2026-03-31", "resolution_m": "0.3", "attribution": "© Vantor 2026"}
    assert c.post(f"/admin/hires/{hid}/deliver", headers=A, files=files, data=form).status_code == 409
    a = c.post(f"/lots/LOT-HR1/hires/{hid}/accept", headers=A)
    assert a.status_code == 200 and a.json()["request"]["status"] == "aceptada"
    d = c.post(f"/admin/hires/{hid}/deliver", headers=A, files={"file": ("img.png", _jpg(), "image/png")}, data=form)
    assert d.status_code == 200, d.text
    assert calls == ["LOT-HR1"]                             # regenera el dossier
    lot = storage.load_lot("LOT-HR1")
    img = lot["extra"]["hires_images"][-1]
    assert img["source"] == "Vantor" and storage.load_image_blob("LOT-HR1", img["blob"])
    pub = c.get("/lots/LOT-HR1/hires", headers=A).json()["requests"][0]
    assert pub["status"] == "entregada" and "coop_id" not in pub


def test_admin_requires_key(monkeypatch):
    c, _ = _setup(monkeypatch, "LOT-HR2")
    assert c.get("/admin/hires").status_code == 404
    assert c.post("/admin/hires/HR-X/quote", json={"price_usd": 1}).status_code == 404


def test_dossier_includes_hires_image(monkeypatch, tmp_path):
    from app import dossier
    from app.models import DeforestationFinding as DF
    from PIL import Image
    p = tmp_path / "hr.jpg"; Image.new("RGB", (300, 200), (30, 110, 50)).save(p)
    lot = Lot("LOT-HR3", "Ana", "Coop", "coffee", "PE", "Junín", [Plot("P1", [GeoPoint(-11.48, -74.42)], 1.0)])
    pdf = dossier.build_pdf(lot, [DF("P1", "review", False, "x")], "n", "", str(tmp_path), "es",
                            hires=[(str(p), {"source": "Vantor", "acquired": "2026-03-31", "resolution_m": 0.3,
                                             "attribution": "© Vantor 2026", "label": "Después"})])
    from pypdf import PdfReader
    txt = "".join(pg.extract_text() or "" for pg in PdfReader(pdf).pages)
    assert "alta resolución" in txt and "Vantor" in txt


def test_blob_chunked_roundtrip(monkeypatch):
    """Archivos grandes (fotos, dossiers) se guardan en partes, sin tope de 1 MiB por lote."""
    store = {}

    class Doc:
        def __init__(self, k): self.k = k
        def set(self, v): store[self.k] = v
        def get(self):
            k = self.k
            class S:
                exists = k in store
                def to_dict(self_inner): return store[k]
            return S()

    class Col:
        def __init__(self, n): self.n = n
        def document(self, k): return Doc(self.n + "/" + k)

    class Client:
        def __init__(self, project=None): pass
        def collection(self, n): return Col(n)

    import types
    fake = types.ModuleType("google.cloud.firestore"); fake.Client = Client
    try:
        import google.cloud as gc
    except ImportError:
        gc = types.ModuleType("google.cloud")
        monkeypatch.setitem(sys.modules, "google", types.ModuleType("google"))
        monkeypatch.setitem(sys.modules, "google.cloud", gc)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", fake)
    monkeypatch.setattr(gc, "firestore", fake, raising=False)
    monkeypatch.setattr(config, "GCP_PROJECT", "p")
    monkeypatch.setattr(config, "DATA_DIR", tempfile.mkdtemp())
    data = os.urandom(2_500_000)
    storage.save_blob("LOT-B", "fphoto0.jpg", data)
    assert store["blobs/LOT-B__fphoto0.jpg"]["n"] == 3
    assert all(len(v.get("data", b"")) <= 900_000 for k, v in store.items() if "__fphoto0.jpg__" in k)
    os.remove(os.path.join(config.DATA_DIR, "blobs", "LOT-B__fphoto0.jpg"))   # fuerza lectura de Firestore
    assert storage.load_blob("LOT-B", "fphoto0.jpg") == data
    import base64                                                              # formato antiguo
    store["files/LOT-OLD"] = {"dossier.pdf": base64.b64encode(b"%PDF-old").decode()}
    assert storage.load_blob("LOT-OLD", "dossier.pdf") == b"%PDF-old"


def test_analyst_review(monkeypatch):
    c, calls = _setup(monkeypatch, "LOT-HR4")
    assert c.post("/admin/lots/LOT-HR4/review", json={"conclusion": "descartada", "note": "x"}).status_code == 404
    assert c.post("/admin/lots/LOT-HR4/review", headers=A, json={"conclusion": "x", "note": "y" * 30}).status_code == 400
    assert c.post("/admin/lots/LOT-HR4/review", headers=A, json={"conclusion": "descartada", "note": "corta"}).status_code == 400
    r = c.post("/admin/lots/LOT-HR4/review", headers=A, json={
        "conclusion": "descartada", "note": "El claro es la trocha existente desde 2019, visible en ambas fechas.",
        "evidence": ["Sentinel-2 2020 y oct-2026"]})
    assert r.status_code == 200 and calls == ["LOT-HR4"]
    lots = c.get("/api/lots", headers=A).json()["lots"]
    assert [l for l in lots if l["lot_id"] == "LOT-HR4"][0]["analyst"] == "descartada"


def test_dossier_shows_analyst_review(tmp_path):
    from app import dossier
    from app.models import DeforestationFinding as DF
    lot = Lot("LOT-HR5", "Ana", "Coop", "coffee", "PE", "Junín", [Plot("P1", [GeoPoint(-11.48, -74.42)], 1.0)],
              extra={"analyst_review": {"conclusion": "campo", "note": "Claro reciente de 0,2 ha en el borde norte.",
                                        "analyst": "Analista de Origen", "at": "2026-11-18T00:00:00Z"}})
    pdf = dossier.build_pdf(lot, [DF("P1", "review", False, "x")], "n", "", str(tmp_path), "es")
    from pypdf import PdfReader
    txt = "".join(pg.extract_text() or "" for pg in PdfReader(pdf).pages)
    assert "Revisión del analista" in txt and "Requiere verificación en campo" in txt
