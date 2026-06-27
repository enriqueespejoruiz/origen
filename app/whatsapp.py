"""WhatsApp Cloud API: enviar texto (alertas/respuestas) y parsear webhooks entrantes.
Best-effort: si no hay credenciales (WHATSAPP_TOKEN/PHONE_ID), no rompe nada."""
from . import config


def send_text(to, body):
    """Envía un mensaje de texto por WhatsApp Cloud API. Devuelve True/False (best-effort)."""
    if not config.whatsapp_ready():
        print("whatsapp not configured; skip send to", to)
        return False
    try:
        import requests
        url = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}/{config.WHATSAPP_PHONE_ID}/messages"
        r = requests.post(
            url, timeout=10,
            headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text",
                  "text": {"preview_url": True, "body": (body or "")[:4000]}},
        )
        if r.status_code >= 300:
            print("whatsapp send error", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:
        print("whatsapp send exception", repr(e))
        return False


def parse_messages(payload: dict):
    """Devuelve [{from, text, media:[ids]}] desde un webhook de WhatsApp Cloud API."""
    out = []
    try:
        for entry in payload.get("entry", []):
            for ch in entry.get("changes", []):
                for msg in ch.get("value", {}).get("messages", []) or []:
                    out.append({
                        "from": msg.get("from", ""),
                        "text": (msg.get("text", {}) or {}).get("body", ""),
                        "media": [msg[k]["id"] for k in ("image", "document") if k in msg],
                    })
    except Exception as e:
        print("whatsapp parse error", repr(e))
    return out


def parse_webhook(payload: dict):
    """Compat: (texto, media_ids) del primer mensaje."""
    msgs = parse_messages(payload)
    if msgs:
        return msgs[0]["text"], msgs[0]["media"]
    return payload.get("text", ""), []
