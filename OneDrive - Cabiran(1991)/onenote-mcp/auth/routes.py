"""
Auth endpoints:
  GET  /auth/login    — redirect to Microsoft login
  GET  /auth/callback — exchange authorization code for tokens
  GET  /auth/status   — current auth state (no token values)
  POST /auth/logout   — clear local token cache
"""

import os
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from auth.token_cache import (
    SCOPES,
    build_msal_app,
    clear_token_cache,
    load_token_cache,
    save_token_cache,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_STATE_STORE: dict[str, str] = {}  # in-memory CSRF state; single-user deployment


def _redirect_uri() -> str:
    return os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/callback")


@router.get("/login")
def login(request: Request):
    cache = load_token_cache()
    app = build_msal_app(cache)
    state = secrets.token_urlsafe(32)
    _STATE_STORE["pending"] = state
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=_redirect_uri(),
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return HTMLResponse(
            f"<h2>Authentication failed</h2><p>{error}</p>",
            status_code=400,
        )
    stored_state = _STATE_STORE.pop("pending", None)
    if not stored_state or state != stored_state:
        return HTMLResponse(
            "<h2>Authentication failed</h2><p>Invalid or expired state parameter.</p>",
            status_code=400,
        )
    cache = load_token_cache()
    app = build_msal_app(cache)
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=_redirect_uri(),
    )
    if "error" in result:
        logger.error("Token acquisition failed: %s", result.get("error_description"))
        return HTMLResponse(
            f"<h2>Token acquisition failed</h2><p>{result.get('error_description')}</p>",
            status_code=400,
        )
    save_token_cache(cache)
    return HTMLResponse(
        "<h2>Authentication successful</h2>"
        "<p>You may close this window. Claude can now access your OneNote.</p>"
    )


@router.get("/status")
def status():
    cache = load_token_cache()
    app = build_msal_app(cache)
    accounts = app.get_accounts()
    if not accounts:
        return JSONResponse({"authenticated": False})
    account = accounts[0]
    # Silent token acquisition to get fresh expiry info (no network call if cached)
    result = app.acquire_token_silent(scopes=SCOPES, account=account)
    if not result or "error" in result:
        return JSONResponse({"authenticated": False, "reason": "token_expired_or_missing"})
    expires_in = result.get("expires_in", 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    return JSONResponse({
        "authenticated": True,
        "username": account.get("username"),
        "tenant_id": account.get("home_account_id", "").split(".")[1] if "." in account.get("home_account_id", "") else None,
        "scopes_granted": result.get("scope", ""),
        "token_expires_at": datetime.fromtimestamp(now_ts + expires_in, tz=timezone.utc).isoformat(),
    })


@router.post("/logout")
def logout():
    clear_token_cache()
    return JSONResponse({
        "logged_out": True,
        "note": "Local token cache cleared. Tokens are NOT revoked at Microsoft.",
    })
