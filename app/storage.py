import os, json
from dataclasses import asdict
from . import config

def save_lot(lot):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("lots").document(lot.lot_id).set(asdict(lot))
            return "firestore"
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, f"{lot.lot_id}.json"), "w") as f:
        json.dump(asdict(lot), f, indent=2, default=str)
    return "local"

def load_lot(lot_id):
    """Lee un lote desde Firestore si esta disponible; si no, del archivo local."""
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("lots").document(lot_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, f"{lot_id}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None

def upload_file(path):
    if config.GCS_BUCKET:
        try:
            from google.cloud import storage
            blob = storage.Client(project=config.GCP_PROJECT or None).bucket(config.GCS_BUCKET).blob(os.path.basename(path))
            blob.upload_from_filename(path)
            return f"gs://{config.GCS_BUCKET}/{os.path.basename(path)}"
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return path

_CHUNK = 900_000          # Firestore: máx. ~1 MiB por documento → un archivo grande va en partes

def _blob_local(lot_id, name):
    return os.path.join(config.DATA_DIR, "blobs", f"{lot_id}__{name}")

def save_blob(lot_id, name, data: bytes):
    """Guarda un archivo (pdf/geojson/foto/imagen) de forma durable, cada uno en sus propios documentos
    de Firestore y partido en trozos de 900 KB. Antes todos los archivos de un lote iban en UN documento
    (files/{lote}) y al pasar de 1 MiB (fotos + dossier) la escritura fallaba en silencio."""
    try:
        os.makedirs(os.path.join(config.DATA_DIR, "blobs"), exist_ok=True)
        with open(_blob_local(lot_id, name), "wb") as f:
            f.write(data)
    except Exception as e:
        print("STORAGE-LOCAL:", repr(e)[:120])
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            col = firestore.Client(project=config.GCP_PROJECT).collection("blobs")
            key = f"{lot_id}__{name}"
            parts = [data[i:i + _CHUNK] for i in range(0, len(data), _CHUNK)] or [b""]
            for i, part in enumerate(parts):
                col.document(f"{key}__{i}").set({"data": part})
            col.document(key).set({"lot_id": lot_id, "name": name, "n": len(parts), "size": len(data)})
            return "firestore"
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return "local"

def load_blob(lot_id, name):
    """Lee un archivo durable. Formato nuevo (blobs/, en partes) y, si no está, el antiguo (files/{lote})."""
    import base64
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            db = firestore.Client(project=config.GCP_PROJECT)
            key = f"{lot_id}__{name}"
            meta = db.collection("blobs").document(key).get()
            if meta.exists:
                n = int(meta.to_dict().get("n") or 0)
                out = b""
                for i in range(n):
                    d = db.collection("blobs").document(f"{key}__{i}").get()
                    if not d.exists:
                        out = None; break
                    out += bytes(d.to_dict().get("data") or b"")
                if out:
                    return out
            doc = db.collection("files").document(lot_id).get()     # formato antiguo
            if doc.exists:
                v = doc.to_dict().get(name)
                if v:
                    return base64.b64decode(v)
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = _blob_local(lot_id, name)
    return open(fp, "rb").read() if os.path.exists(fp) else None

# ---------- Usuarios y multi-tenant (login con Google) ----------

def get_user(sub):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("users").document(sub).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, "users", f"{sub}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None

def save_user(sub, data):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("users").document(sub).set(data, merge=True)
            return "firestore"
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    d = os.path.join(config.DATA_DIR, "users"); os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, f"{sub}.json")
    cur = json.load(open(fp)) if os.path.exists(fp) else {}
    cur.update(data); json.dump(cur, open(fp, "w"))
    return "local"

def merge_lot(lot_id, fields):
    """Mezcla campos (p. ej. overall_risk) en el documento del lote."""
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("lots").document(lot_id).set(fields, merge=True)
            return
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, f"{lot_id}.json")
    if os.path.exists(fp):
        d = json.load(open(fp)); d.update(fields)
        json.dump(d, open(fp, "w"), indent=2, default=str)

def list_lots(coop_id, limit=300):
    out = []
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = (firestore.Client(project=config.GCP_PROJECT).collection("lots")
                 .where(filter=FieldFilter("coop_id", "==", coop_id)).limit(limit))
            for d in q.stream():
                out.append(d.to_dict())
            return out
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "LOT-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("lot_id") and d.get("coop_id") == coop_id:
                out.append(d)
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return out

def coop_restricted(coop_id):
    """True si la coop opera en modo evaluación (marca de muestra + topes): la demo siempre;
    las coops 'piloto-*' y las cuentas nuevas hasta aprobarse. Coops antiguas sin el campo
    'approved' quedan aprobadas (grandfathering) para no marcar clientes existentes."""
    cid = str(coop_id or "")
    if cid == "demo-origen":
        return True
    c = get_coop(cid)
    if c and "approved" in c:
        if not c["approved"]:
            return True
        # suscripción vencida (plan_until pasado) => vuelve a modo evaluación
        pu = str(c.get("plan_until") or "")
        if pu:
            import datetime as _dt
            try:
                if pu[:10] < _dt.datetime.utcnow().strftime("%Y-%m-%d"):
                    return True
            except Exception:
                pass
        return False
    return cid.startswith("piloto-")


def set_coop_approved(coop_id, approved=True):
    c = get_coop(coop_id) or {"id": coop_id}
    c["approved"] = bool(approved)
    save_coop(c)
    return c


def list_all_lots(limit=1000):
    """Todos los lotes (para el monitoreo continuo, multi-coop)."""
    out = []
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            for d in firestore.Client(project=config.GCP_PROJECT).collection("lots").limit(limit).stream():
                out.append(d.to_dict())
            return out
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "LOT-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("lot_id"):
                out.append(d)
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return out

# ---------- Alertas de monitoreo continuo ----------

def save_alert(alert):
    """Guarda una alerta (id autogenerado). Devuelve el id."""
    import uuid, datetime
    aid = alert.get("id") or ("AL-" + uuid.uuid4().hex[:10])
    alert["id"] = aid
    alert.setdefault("created_at", datetime.datetime.utcnow().isoformat() + "Z")
    alert.setdefault("read", False)
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("alerts").document(aid).set(alert)
            return aid
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    d = os.path.join(config.DATA_DIR, "alerts"); os.makedirs(d, exist_ok=True)
    json.dump(alert, open(os.path.join(d, f"{aid}.json"), "w"), default=str)
    return aid

def list_alerts(coop_id, limit=50):
    out = []
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = (firestore.Client(project=config.GCP_PROJECT).collection("alerts")
                 .where(filter=FieldFilter("coop_id", "==", coop_id)).limit(limit))
            for d in q.stream():
                out.append(d.to_dict())
            return out
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "alerts", "AL-*.json")):
        try:
            d = json.load(open(fp))
            if d.get("coop_id") == coop_id:
                out.append(d)
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return out

# ---------- Envíos / consignaciones (agregación de lotes) ----------

def save_consignment(c):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("consignments").document(c.consignment_id).set(asdict(c))
            return "firestore"
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, f"{c.consignment_id}.json"), "w") as f:
        json.dump(asdict(c), f, indent=2, default=str)
    return "local"

def load_consignment(cid):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("consignments").document(cid).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, f"{cid}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None

def list_consignments(coop_id, limit=300):
    out = []
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = (firestore.Client(project=config.GCP_PROJECT).collection("consignments")
                 .where(filter=FieldFilter("coop_id", "==", coop_id)).limit(limit))
            for d in q.stream():
                out.append(d.to_dict())
            return out
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "ENV-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("coop_id") == coop_id:
                out.append(d)
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return out

def merge_consignment(cid, fields):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("consignments").document(cid).set(fields, merge=True)
            return
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, f"{cid}.json")
    if os.path.exists(fp):
        d = json.load(open(fp)); d.update(fields)
        json.dump(d, open(fp, "w"), indent=2, default=str)

# ---------- Cooperativas (equipo / invitaciones) ----------

def save_coop(coop):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("coops").document(coop["id"]).set(coop, merge=True)
            return
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    d = os.path.join(config.DATA_DIR, "coops"); os.makedirs(d, exist_ok=True)
    json.dump(coop, open(os.path.join(d, f"{coop['id']}.json"), "w"), indent=2, default=str)

def get_coop(cid):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("coops").document(cid).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, "coops", f"{cid}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None

def add_coop_member(cid, email, name=""):
    coop = get_coop(cid) or {"id": cid, "members": []}
    members = coop.get("members", [])
    if email and email not in members:
        members.append(email)
    coop["members"] = members
    save_coop(coop)
    return coop

def find_coop_by_member(email):
    """Devuelve la cooperativa cuyo equipo incluye este email (para auto-unir al iniciar sesión)."""
    if not email:
        return None
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = (firestore.Client(project=config.GCP_PROJECT).collection("coops")
                 .where(filter=FieldFilter("members", "array_contains", email)).limit(1))
            for d in q.stream():
                return d.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "coops", "*.json")):
        try:
            c = json.load(open(fp))
            if email in (c.get("members") or []):
                return c
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    return None

def save_notary(lot_id, rec):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("notary").document(lot_id).set(rec, merge=True)
            return
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    d = os.path.join(config.DATA_DIR, "notary"); os.makedirs(d, exist_ok=True)
    json.dump(rec, open(os.path.join(d, f"{lot_id}.json"), "w"))

def get_notary(lot_id):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("notary").document(lot_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, "notary", f"{lot_id}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None

# ---------- Pedidos de imagen de alta resolución (servicio bajo pedido) ----------

def save_hires(rec):
    """Crea o actualiza un pedido de alta resolución (id HR-…). Devuelve el id."""
    import uuid, datetime
    hid = rec.get("id") or ("HR-" + uuid.uuid4().hex[:8].upper())
    rec["id"] = hid
    rec.setdefault("created_at", datetime.datetime.utcnow().isoformat() + "Z")
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("hires_requests").document(hid).set(rec, merge=True)
            return hid
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    d = os.path.join(config.DATA_DIR, "hires"); os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, f"{hid}.json")
    cur = json.load(open(fp)) if os.path.exists(fp) else {}
    cur.update(rec)
    json.dump(cur, open(fp, "w"), indent=2, default=str)
    return hid

def get_hires(hid):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("hires_requests").document(hid).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    fp = os.path.join(config.DATA_DIR, "hires", f"{hid}.json")
    return json.load(open(fp)) if os.path.exists(fp) else None

def list_hires(lot_id=None, status=None, limit=200):
    """Pedidos de alta resolución, filtrados por lote y/o estado (más recientes primero)."""
    out = []
    done = False
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = firestore.Client(project=config.GCP_PROJECT).collection("hires_requests")
            if lot_id:
                q = q.where(filter=FieldFilter("lot_id", "==", lot_id))
            elif status:
                q = q.where(filter=FieldFilter("status", "==", status))
            out = [d.to_dict() for d in q.limit(limit).stream()]
            done = True
        except Exception as e:
            print("STORAGE-FALLBACK:", repr(e)[:200])
    if not done:
        import glob
        for fp in glob.glob(os.path.join(config.DATA_DIR, "hires", "HR-*.json")):
            try:
                out.append(json.load(open(fp)))
            except Exception:
                continue
    if lot_id:
        out = [r for r in out if r.get("lot_id") == lot_id]
    if status:
        out = [r for r in out if r.get("status") == status]
    out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return out[:limit]

def save_image_blob(lot_id, name, data: bytes):
    return save_blob(lot_id, name, data)

def load_image_blob(lot_id, name):
    return load_blob(lot_id, name)
