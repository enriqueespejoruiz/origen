"""Notarización del dossier:
  Fase 0 — huella SHA-256 con fecha de emisión (a prueba de manipulación).
  Fase 1 — anclaje público en Bitcoin vía OpenTimestamps: se genera una prueba .ots
           verificable de forma independiente (opentimestamps.org / `ots verify`).
Todo es best-effort: si el anclaje falla (red/lib), se conserva la Fase 0 y nada se rompe."""
import hashlib, datetime
from . import storage

OTS_CALENDARS = [
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org",
    "https://finney.calendar.eternitywall.com",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ots_stamp(sha256_hex, timeout=6):
    """Ancla el hash en Bitcoin vía calendarios OpenTimestamps. Devuelve (ots_bytes, info) o (None, None)."""
    try:
        from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
        from opentimestamps.core.op import OpSHA256
        from opentimestamps.calendar import RemoteCalendar
        from opentimestamps.core.serialize import BytesSerializationContext
        digest = bytes.fromhex(sha256_hex)
        ts = Timestamp(digest)
        used = []
        for url in OTS_CALENDARS:
            try:
                ts.merge(RemoteCalendar(url).submit(digest, timeout=timeout))
                used.append(url)
            except Exception as e:
                print("ots calendar fail", url, repr(e)[:120])
        if not used:
            return None, None
        det = DetachedTimestampFile(OpSHA256(), ts)
        ctx = BytesSerializationContext()
        det.serialize(ctx)
        return ctx.getbytes(), {"type": "opentimestamps", "status": "pending", "calendars": used}
    except Exception as e:
        print("ots stamp error", repr(e))
        return None, None


def ots_status(ots_bytes):
    """Lee una prueba .ots: ¿anclada en Bitcoin (altura de bloque) o pendiente de confirmación?"""
    try:
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.core.serialize import BytesDeserializationContext
        from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation
        det = DetachedTimestampFile.deserialize(BytesDeserializationContext(ots_bytes))
        pending, bitcoin = [], []
        for _msg, att in det.timestamp.all_attestations():
            if isinstance(att, BitcoinBlockHeaderAttestation):
                bitcoin.append(att.height)
            elif isinstance(att, PendingAttestation):
                pending.append(att.uri.decode() if isinstance(att.uri, bytes) else att.uri)
        return {"anchored": bool(bitcoin), "bitcoin_blocks": sorted(bitcoin),
                "pending_calendars": pending, "sha256": det.timestamp.msg.hex()}
    except Exception as e:
        print("ots status error", repr(e))
        return None


def ots_upgrade(ots_bytes):
    """Best-effort: completa la prueba pendiente con la confirmación de Bitcoin (si el calendario
    ya la tiene). Devuelve nuevos bytes si se actualizó, o None."""
    try:
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.core.serialize import BytesDeserializationContext, BytesSerializationContext
        from opentimestamps.core.notary import PendingAttestation
        from opentimestamps.calendar import RemoteCalendar
        det = DetachedTimestampFile.deserialize(BytesDeserializationContext(ots_bytes))
        changed = [False]

        def walk(ts):
            for att in list(ts.attestations):
                if isinstance(att, PendingAttestation):
                    uri = att.uri.decode() if isinstance(att.uri, bytes) else att.uri
                    try:
                        ts.merge(RemoteCalendar(uri).get_timestamp(ts.msg, timeout=6))
                        changed[0] = True
                    except Exception as e:
                        print("ots upgrade calendar", uri, repr(e)[:100])
            for _op, sub in list(ts.ops.items()):
                walk(sub)

        walk(det.timestamp)
        if not changed[0]:
            return None
        ctx = BytesSerializationContext()
        det.serialize(ctx)
        return ctx.getbytes()
    except Exception as e:
        print("ots upgrade error", repr(e))
        return None


def notarize(lot_id, pdf_path):
    """Registra la huella del dossier + intenta anclarla en Bitcoin (OpenTimestamps). Devuelve el registro."""
    sha = sha256_file(pdf_path)
    rec = {
        "lot_id": lot_id,
        "algo": "SHA-256",
        "sha256": sha,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "anchor": "origen-registry",   # fallback Fase 0 si el anclaje no estuvo disponible
    }
    try:
        ots, info = ots_stamp(sha)
        if ots:
            storage.save_blob(lot_id, "dossier.ots", ots)          # durable (Firestore en prod)
            try:                                                    # y en disco junto al PDF (local + cache)
                import os
                ots_path = (pdf_path[:-4] if pdf_path.lower().endswith(".pdf") else pdf_path) + ".ots"
                with open(ots_path, "wb") as f:
                    f.write(ots)
            except Exception as e:
                print("ots local write error", repr(e))
            rec["anchor"] = "opentimestamps"
            rec["ots"] = info
    except Exception as e:
        print("ots notarize error", repr(e))
    try:
        storage.save_notary(lot_id, rec)
    except Exception as e:
        print("notary save error:", repr(e))
    return rec
