from typing import Optional

from app.core.settings import settings

# Signed cookie name for gallery scoping (stores the selected EventID)
GALLERY_COOKIE = "gallery_scope"


def _sign_scope(value: str) -> str:
    import hashlib
    import hmac

    key = (settings.SECRET_KEY or "change-me").encode("utf-8")
    sig = hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{value}:{sig}"


def _verify_scope(value: str) -> Optional[str]:
    try:
        raw, sig = value.rsplit(":", 1)
    except ValueError:
        return None
    import hashlib
    import hmac

    key = (settings.SECRET_KEY or "change-me").encode("utf-8")
    expected = hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return raw
    return None
