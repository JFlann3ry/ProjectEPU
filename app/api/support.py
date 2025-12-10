from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.settings import settings
from app.core.templates import templates
from app.services.csrf import set_csrf_cookie
from app.services.email_utils import send_support_email

router = APIRouter()


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    # Issue CSRF token and set cookie
    try:
        from app.services.csrf import issue_csrf_token  # type: ignore  # noqa: E402
    except Exception:  # pragma: no cover
        from ..services.csrf import issue_csrf_token  # type: ignore  # noqa: E402
    session_id = request.cookies.get("session_id")
    token = issue_csrf_token(session_id)
    # Allow preselecting topic via query (?topic=Billing) for convenience
    qp = dict(request.query_params)
    rqid = qp.get("request_id") or getattr(getattr(request, "state", object()), "request_id", None)
    form = {"topic": qp.get("topic", "")}
    resp = templates.TemplateResponse(
        request,
        "contact.html",
        context={
            "csrf_token": token,
            "form": form,
            "request_id": rqid,
            # Provide a best-effort page URL (referer) if available
            "request_url": request.headers.get("referer") or "",
        },
    )
    set_csrf_cookie(resp, token, httponly=True)
    return resp


@router.post("/contact")
async def contact_submit(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    topic: str = Form("Other"),
    order_number: str = Form(""),
    event_url: str = Form(""),
    message: str = Form(""),
    captcha_token: str = Form(""),
    csrf_token: str = Form(""),
    hp: str = Form(""),
):
    client_ip = request.client.host if request.client else "unknown"
    # Lazy imports for env resilience
    try:
        from app.services.rate_limit import allow as rl_allow  # type: ignore  # noqa: E402
    except Exception:  # pragma: no cover
        from ..services.rate_limit import allow as rl_allow  # type: ignore  # noqa: E402
    try:
        from app.services.captcha import verify_captcha  # type: ignore  # noqa: E402
    except Exception:  # pragma: no cover
        from ..services.captcha import verify_captcha  # type: ignore  # noqa: E402
    try:
        from app.services.csrf import (
            CSRF_COOKIE,
            issue_csrf_token,
            validate_csrf_token,
        )  # type: ignore  # noqa: E402
    except Exception:  # pragma: no cover
        from ..services.csrf import (
            CSRF_COOKIE,
            issue_csrf_token,
            validate_csrf_token,
        )  # type: ignore  # noqa: E402
    # Shared rate limit (Redis if configured)
    if not rl_allow(
        f"contact:{client_ip}",
        int(getattr(settings, "CONTACT_RATE_LIMIT_ATTEMPTS", 3)),
        int(getattr(settings, "CONTACT_RATE_LIMIT_WINDOW_SECONDS", 60)),
    ):
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = templates.TemplateResponse(
            request,
            "contact.html",
            context={
                "error": "Too many requests. Please wait a minute and try again.",
            "csrf_token": token,
            },
            status_code=429,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp

    # Honeypot: if filled, drop silently as success
    if hp:
        return RedirectResponse("/contact/sent", status_code=303)

    if not (name and email and message and topic):
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = templates.TemplateResponse(
            request,
            "contact.html",
            context={
                "error": "All fields are required.",
            "csrf_token": token,
                "form": {
                    "name": name,
                    "email": email,
                    "topic": topic,
                    "order_number": order_number,
                    "event_url": event_url,
                    "message": message,
                },
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp

    # CSRF validation
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not csrf_token
        or not validate_csrf_token(csrf_token, request.cookies.get("session_id"))
        or cookie_token != csrf_token
    ):
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = templates.TemplateResponse(
            request,
            "contact.html",
            context={
                "error": "Invalid form token. Please refresh and try again.",
            "csrf_token": token,
                "form": {
                    "name": name,
                    "email": email,
                    "topic": topic,
                    "order_number": order_number,
                    "event_url": event_url,
                    "message": message,
                },
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp

    # CAPTCHA verification (Turnstile/hCaptcha)
    captcha_secret = getattr(settings, "CAPTCHA_SECRET", "")
    if captcha_secret and not await verify_captcha(captcha_token, client_ip):
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = templates.TemplateResponse(
            request,
            "contact.html",
            context={
                "error": "Please complete the CAPTCHA.",
            "csrf_token": token,
                "form": {
                    "name": name,
                    "email": email,
                    "topic": topic,
                    "order_number": order_number,
                    "event_url": event_url,
                    "message": message,
                },
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp

    # Validate lengths (defense-in-depth; UI already limits)
    if len(name) > 80 or len(email) > 254 or len(message) > 2000:
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = templates.TemplateResponse(
            request,
            "contact.html",
            context={
                "error": "One or more fields exceed the allowed length.",
            "csrf_token": token,
                "form": {
                    "name": name,
                    "email": email,
                    "topic": topic,
                    "order_number": order_number,
                    "event_url": event_url,
                    "message": message,
                },
            },
            status_code=400,
        )
        set_csrf_cookie(resp, token, httponly=True)
        return resp

    try:
        extra = {}
        if (topic or "").lower() == "billing":
            extra = {"order_number": order_number or "", "event_url": event_url or ""}
        await send_support_email(name=name, from_email=email, message=message, topic=topic, **extra)
    except Exception:
        # Swallow errors to avoid leaking config; pretend success
        pass
    return RedirectResponse("/contact/sent", status_code=303)


@router.get("/contact/sent", response_class=HTMLResponse)
async def contact_sent(request: Request):
    return templates.TemplateResponse(request, "contact_sent.html")
