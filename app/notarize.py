"""Notarización Fase 0: huella SHA-256 del dossier + registro con fecha (a prueba de manipulación)."""
import hashlib, datetime
from . import storage


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def notarize(lot_id, pdf_path):
    """Registra la huella del dossier con su fecha de emisión. Devuelve el registro."""
    rec = {
        "lot_id": lot_id,
        "algo": "SHA-256",
        "sha256": sha256_file(pdf_path),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "anchor": "origen-registry",   # Fase 1: anclaje público periódico (OpenTimestamps)
    }
    try:
        storage.save_notary(lot_id, rec)
    except Exception as e:
        print("notary save error:", repr(e))
    return rec
