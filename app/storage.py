import os, json
from dataclasses import asdict
from . import config

def save_lot(lot):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("lots").document(lot.lot_id).set(asdict(lot))
            return "firestore"
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
            pass
    return path

def save_blob(lot_id, name, data: bytes):
    """Guarda un archivo generado (pdf/geojson) de forma durable para servirlo desde cualquier instancia."""
    import base64
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("files").document(lot_id)\
                .set({name: base64.b64encode(data).decode()}, merge=True)
            return "firestore"
        except Exception:
            pass
    return "local"

def load_blob(lot_id, name):
    """Lee un archivo generado desde el almacenamiento durable (Firestore). None si no existe."""
    import base64
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("files").document(lot_id).get()
            if doc.exists:
                v = doc.to_dict().get(name)
                if v:
                    return base64.b64decode(v)
        except Exception:
            pass
    return None

# ---------- Usuarios y multi-tenant (login con Google) ----------

def get_user(sub):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("users").document(sub).get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
            pass
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "LOT-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("lot_id") and d.get("coop_id") == coop_id:
                out.append(d)
        except Exception:
            pass
    return out

def list_all_lots(limit=1000):
    """Todos los lotes (para el monitoreo continuo, multi-coop)."""
    out = []
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            for d in firestore.Client(project=config.GCP_PROJECT).collection("lots").limit(limit).stream():
                out.append(d.to_dict())
            return out
        except Exception:
            pass
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "LOT-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("lot_id"):
                out.append(d)
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
            pass
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "alerts", "AL-*.json")):
        try:
            d = json.load(open(fp))
            if d.get("coop_id") == coop_id:
                out.append(d)
        except Exception:
            pass
    return out

# ---------- Envíos / consignaciones (agregación de lotes) ----------

def save_consignment(c):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("consignments").document(c.consignment_id).set(asdict(c))
            return "firestore"
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
            pass
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "ENV-*.json")):
        try:
            d = json.load(open(fp))
            if isinstance(d, dict) and d.get("coop_id") == coop_id:
                out.append(d)
        except Exception:
            pass
    return out

def merge_consignment(cid, fields):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("consignments").document(cid).set(fields, merge=True)
            return
        except Exception:
            pass
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
        except Exception:
            pass
    d = os.path.join(config.DATA_DIR, "coops"); os.makedirs(d, exist_ok=True)
    json.dump(coop, open(os.path.join(d, f"{coop['id']}.json"), "w"), indent=2, default=str)

def get_coop(cid):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("coops").document(cid).get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass
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
        except Exception:
            pass
    import glob
    for fp in glob.glob(os.path.join(config.DATA_DIR, "coops", "*.json")):
        try:
            c = json.load(open(fp))
            if email in (c.get("members") or []):
                return c
        except Exception:
            pass
    return None

def save_notary(lot_id, rec):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            firestore.Client(project=config.GCP_PROJECT).collection("notary").document(lot_id).set(rec, merge=True)
            return
        except Exception:
            pass
    d = os.path.join(config.DATA_DIR, "notary"); os.makedirs(d, exist_ok=True)
    json.dump(rec, open(os.path.join(d, f"{lot_id}.json"), "w"))

def get_notary(lot_id):
    if config.GCP_PROJECT:
        try:
            from google.cloud import firestore
            doc = firestore.Client(project=config.GCP_PROJECT).collection("notary").document(lot_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass
    fp = os.path.join(config.DATA_DIR, "notary", f"{lot_id}.json")
    if os.path.exists(fp):
        return json.load(open(fp))
    return None
