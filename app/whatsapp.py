def parse_webhook(payload: dict):
    """Convierte un webhook (WhatsApp Cloud API, forma simplificada) en (texto, media_ids)."""
    try:
        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        text = msg.get("text", {}).get("body", "")
        media = [msg[k]["id"] for k in ("image", "document") if k in msg]
        return text, media
    except Exception:
        return payload.get("text", ""), []
