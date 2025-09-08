from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from app.core.settings import settings

CSRF_COOKIE = "csrf_token"


def _sign(value: str) -> str:
    key = (settings.SECRET_KEY or "change-me").encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_csrf_token(session_id: Optional[str]) -> str:
    # Bind token to session id (if any) + random
    nonce = os.urandom(16).hex()
    base = f"{session_id or ''}:{nonce}"
    sig = _sign(base)
    return f"{base}:{sig}"


def validate_csrf_token(token: str, session_id: Optional[str]) -> bool:
    try:
        parts = (token or "").split(":")
        if len(parts) != 3:
            return False
        base = ":".join(parts[:2])
        sig = parts[2]
        # Ensure session id match
        expected_prefix = f"{session_id or ''}:"
        if not base.startswith(expected_prefix):
            return False
        expected_sig = _sign(base)
        return hmac.compare_digest(expected_sig, sig)
    except Exception:
        return False


def set_csrf_cookie(response, token: str, httponly: bool = False) -> None:
    """Set the CSRF cookie with consistent attributes across the app.

    Parameters:
    - response: A FastAPI/Starlette Response
    - token: CSRF token string
    - httponly: Whether the cookie should be HttpOnly (default False so JS can read for forms).
    """
    try:
        response.set_cookie(
            CSRF_COOKIE,
            token,
            httponly=httponly,
            samesite="lax",
            secure=bool(getattr(settings, "COOKIE_SECURE", False)),
            path="/",
        )
    except Exception:
        # Best-effort; don't crash if a response type doesn't support cookies
        pass
