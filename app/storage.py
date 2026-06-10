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
