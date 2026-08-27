"""Login con Google (Google Identity Services, flujo de ID token) + sesión firmada."""
from fastapi import Request, HTTPException
from . import config, storage


def verify_google_credential(credential: str) -> dict:
    """Verifica el ID token de Google y devuelve el perfil mínimo del usuario."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as grequests
    info = id_token.verify_oauth2_token(credential, grequests.Request(), config.GOOGLE_OAUTH_CLIENT_ID)
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("issuer inválido")
    if info.get("email") and info.get("email_verified") is False:
        raise ValueError("email no verificado")
    return {
        "sub": info["sub"],
        "email": info.get("email", ""),
        "name": info.get("name", "") or info.get("email", ""),
        "picture": info.get("picture", ""),
    }


def current(request: Request):
    return request.session.get("user")


def require_user(request: Request) -> dict:
    u = request.session.get("user")
    if not u:
        raise HTTPException(401, "Inicia sesión con Google")
    return u


def agent_ctx(request: Request):
    """Acceso servidor-a-servidor para el agente (Sentinel): header X-Agent-Key.
    Opera sobre una cooperativa dedicada; deshabilitado si AGENT_API_KEY está vacío."""
    key = request.headers.get("X-Agent-Key", "")
    if key and config.AGENT_API_KEY and key == config.AGENT_API_KEY:
        import re as _re
        cid = request.headers.get("X-Agent-Coop", "") or "sentinel-ops"
        if not (_re.fullmatch(r"[a-z0-9-]{3,40}", cid)
                and (cid == "sentinel-ops" or cid.startswith("piloto-"))):
            cid = "sentinel-ops"
        return {"user": {"sub": "agent-sentinel", "email": "sentinel@origen.pe",
                         "name": "Sentinel (agente)", "picture": ""},
                "coop": {"id": cid, "name": ("Sentinel Ops" if cid == "sentinel-ops" else cid),
                         "role": "admin"}}
    return None


def require_coop(request: Request) -> dict:
    """Exige usuario autenticado + cooperativa elegida. Devuelve {user, coop}.
    También acepta el acceso de agente por header (ver agent_ctx)."""
    a = agent_ctx(request)
    if a:
        return a
    u = require_user(request)
    coop = request.session.get("coop")
    if not coop:
        raise HTTPException(403, "Crea o únete a una cooperativa")
    return {"user": u, "coop": coop}
