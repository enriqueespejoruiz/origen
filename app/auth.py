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


def require_coop(request: Request) -> dict:
    """Exige usuario autenticado + cooperativa elegida. Devuelve {user, coop}."""
    u = require_user(request)
    coop = request.session.get("coop")
    if not coop:
        raise HTTPException(403, "Crea o únete a una cooperativa")
    return {"user": u, "coop": coop}
