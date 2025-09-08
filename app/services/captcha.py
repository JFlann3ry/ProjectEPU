from __future__ import annotations

from typing import Optional

from app.core.settings import settings

try:
    import httpx  # type: ignore
except Exception:
    httpx = None  # type: ignore


async def verify_captcha(token: str, remote_ip: Optional[str] = None) -> bool:
    secret = (settings.CAPTCHA_SECRET or "").strip()
    if not secret:
        # CAPTCHA disabled
        return True
    provider = (settings.CAPTCHA_PROVIDER or "turnstile").lower()
    try:
        if provider == "hcaptcha":
            url = "https://hcaptcha.com/siteverify"
            data = {"secret": secret, "response": token}
            if remote_ip:
                data["remoteip"] = remote_ip
        else:
            # default: Cloudflare Turnstile
            url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
            data = {"secret": secret, "response": token}
            if remote_ip:
                data["remoteip"] = remote_ip
        if httpx is None:
            return False
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, data=data)
            if r.status_code != 200:
                return False
            j = r.json()
            # Turnstile: { success: bool, ... }, hCaptcha: { success: bool, ... }
            return bool(j.get("success"))
    except Exception:
        return False
