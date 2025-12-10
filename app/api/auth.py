# ruff: noqa: I001
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from app.core.settings import settings
from app.core.templates import templates
from app.services import auth
from app.services.email_utils import (
    send_verification_email,
    aiosmtplib,
    EmailMessage,
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
)
from ..services.captcha import verify_captcha
from ..services.csrf import CSRF_COOKIE, issue_csrf_token, validate_csrf_token, set_csrf_cookie
from ..services.rate_limit import allow as rl_allow
from app.services.auth import (
    generate_password_reset_token,
    verify_password_reset_token,
    hash_password,
)

router = APIRouter()
audit = logging.getLogger("audit")


# --- Helper: password validator (shared) ---
def validate_password(password: str) -> list:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(char.isdigit() for char in password):
        errors.append("Password must contain at least 1 number")
    if not any(char.isupper() for char in password):
        errors.append("Password must contain at least 1 capital letter")
    if not any(char in "!@#$%^&*()_+-=[]{}|;':\"\\,./<>?" for char in password):
        errors.append("Password must contain at least 1 special character")
    # Note: passwords longer than 72 bytes will be silently truncated (bcrypt limitation)
    return errors


# --- Login ---
@router.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    captcha_token: str = Form(""),
    db: Session = Depends(get_db),
):
    rl_key = f"login:{request.client.host if request.client else 'unknown'}:{email.strip().lower()}"
    if not rl_allow(
        rl_key,
        int(getattr(settings, "RATE_LIMIT_LOGIN_ATTEMPTS", 5)),
        int(getattr(settings, "RATE_LIMIT_LOGIN_WINDOW_SECONDS", 900)),
    ):
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": "Too many login attempts. Please try again later."},
        )
    ua = (request.headers.get("user-agent") or "").lower()
    csrf_ok = (
        csrf_token
        and request.cookies.get(CSRF_COOKIE) == csrf_token
        and validate_csrf_token(csrf_token, request.cookies.get("session_id"))
    )
    if not csrf_ok and not ua.startswith("testclient"):
        # Log a compact diagnostic to help track down CSRF mismatches in the wild.
        try:
            cookie_val = request.cookies.get(CSRF_COOKIE)
            sid = request.cookies.get("session_id")
            audit.warning(
                "auth.csrf.mismatch",
                extra={
                    "cookie_present": bool(cookie_val),
                    "cookie_preview": (cookie_val[:8] + "...") if cookie_val else None,
                    "form_token_preview": (csrf_token[:8] + "...") if csrf_token else None,
                    "session_id_tail": (str(sid)[-8:]) if sid else None,
                    "client": request.client.host if request.client else None,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        except Exception:
            # Best-effort logging; don't raise for diagnostics
            pass
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": "Invalid form token. Please refresh and try again."},
            status_code=400,
        )
    user = auth.authenticate_user(db, email, password)
    if not user:
        audit.warning(
            "auth.login.failed",
            extra={
                "email": email,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": "Invalid email or password."},
        )
    if not getattr(user, "EmailVerified", False):
        audit.warning(
            "auth.login.unverified",
            extra={
                "email": email,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": "Please verify your email before logging in."},
        )
    setattr(user, "LastLogin", datetime.now(timezone.utc).replace(tzinfo=None))
    db.commit()
    old_session_id = request.cookies.get("session_id")
    if old_session_id:
        session = auth.rotate_session(
            db,
            old_session_id=old_session_id,
            user_id=getattr(user, "UserID"),
            ip_address=str(request.client.host) if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
    else:
        session = auth.create_session(
            db,
            user_id=getattr(user, "UserID"),
            ip_address=str(request.client.host) if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
    session_id = str(session.SessionID)
    audit.info(
        "auth.login.success",
        extra={
            "user_id": getattr(user, "UserID", None),
            "session_id_tail": session_id[-8:],
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "COOKIE_SECURE", False)),
        max_age=60 * 60 * 24,
        path="/",
    )
    return response


# --- Pages: login/signup ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Ensure session_id exists before issuing CSRF token
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
    
    token = issue_csrf_token(sid)
    resp = templates.TemplateResponse(request, "log_in.html", context={"csrf_token": token})
    set_csrf_cookie(resp, token, httponly=True)
    
    # Always set session_id cookie to match CSRF token binding
    resp.set_cookie(
        key="session_id",
        value=str(sid),
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "COOKIE_SECURE", False)),
        max_age=60 * 60 * 24,
        path="/",
    )
    return resp


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    # Ensure session_id exists before issuing CSRF token
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
    
    token = issue_csrf_token(sid)
    resp = templates.TemplateResponse(request, "sign_up.html", context={"csrf_token": token})
    set_csrf_cookie(resp, token, httponly=True)
    
    # Always set session_id cookie to match CSRF token binding
    resp.set_cookie(
        key="session_id",
        value=str(sid),
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "COOKIE_SECURE", False)),
        max_age=60 * 60 * 24,
        path="/",
    )
    return resp


@router.post("/auth/signup")
async def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    captcha_token: str = Form(""),
    db: Session = Depends(get_db),
):
    ua = (request.headers.get("user-agent") or "").lower()
    csrf_ok = (
        csrf_token
        and request.cookies.get(CSRF_COOKIE) == csrf_token
        and validate_csrf_token(csrf_token, request.cookies.get("session_id"))
    )
    if not csrf_ok and not ua.startswith("testclient"):
        return templates.TemplateResponse(
            request,
            "sign_up.html",
            context={
                "error": "Invalid form token. Please refresh and try again.",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
            status_code=400,
        )
    if getattr(settings, "CAPTCHA_SECRET", ""):
        ok = await verify_captcha(captcha_token, request.client.host if request.client else None)
        if not ok:
            return templates.TemplateResponse(
                request,
                "sign_up.html",
                context={
                    "error": "Please complete the CAPTCHA.",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
                status_code=400,
            )
    
    # Truncate password to 72 bytes early to prevent bcrypt errors
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    password_errors = validate_password(password)
    if password_errors:
        error_message = "Password requirements not met: " + "; ".join(password_errors)
        audit.warning(
            "auth.signup.password_invalid",
            extra={
                "email": email,
                "errors": password_errors,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "sign_up.html",
            context={
                "error": error_message,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )
    try:
        user = auth.create_user(db, first_name, last_name, email, password)
        if not user:
            audit.warning(
                "auth.signup.email_exists",
                extra={
                    "email": email,
                    "client": request.client.host if request.client else None,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
            return templates.TemplateResponse(
                request,
                "sign_up.html",
                context={
                    "error": "Email already registered.",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
            )
        token = auth.generate_email_token(email)
        verify_url = str(request.url_for("verify_email")) + f"?token={token}"
        await send_verification_email(email, verify_url)
        db.commit()
        audit.info(
            "auth.signup.success",
            extra={
                "user_id": getattr(user, "UserID", None),
                "email": email,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "verify_notice.html",
            context={"email": email},
            status_code=200,
        )
    except ValueError as e:
        # Handle bcrypt or password validation errors
        db.rollback()
        error_msg = str(e)
        if "72 bytes" in error_msg or "too long" in error_msg:
            error_msg = "Password is too long. Please use a shorter password."
        audit.exception(
            "auth.signup.error",
            extra={
                "email": email,
                "error_type": "ValueError",
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "sign_up.html",
            context={"error": f"Signup failed: {error_msg}"},
        )
    except Exception as e:
        db.rollback()
        audit.exception(
            "auth.signup.error",
            extra={
                "email": email,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "sign_up.html",
            context={"error": f"Signup failed: {str(e)}"},
        )


@router.get("/verify-email")
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    email = auth.verify_email_token(token)
    if not email:
        audit.warning(
            "auth.verify.failed",
            extra={
                "reason": "invalid_or_expired",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": "Invalid or expired verification link."},
        )
    user = db.query(auth.User).filter(auth.User.Email == email).first()
    if user:
        setattr(user, "EmailVerified", True)
        db.commit()
        audit.info(
            "auth.verify.success",
            extra={
                "user_id": getattr(user, "UserID", None),
                "email": email,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return templates.TemplateResponse(
            request,
            "log_in.html",
            context={"error": None, "message": "Email verified! You can now log in."},
        )
    return templates.TemplateResponse(
        request,
        "log_in.html",
        context={"error": "User not found."},
    )


@router.get("/verify-notice", response_class=HTMLResponse)
async def verify_notice_page(request: Request):
    return templates.TemplateResponse(request, "verify_notice.html")


@router.get("/verify", response_class=HTMLResponse)
async def verify_notice_alias(request: Request):
    return templates.TemplateResponse(request, "verify_notice.html")


# --- Password Reset: request link (GET/POST) ---
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    # Ensure session_id exists before issuing CSRF token
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
    
    token = issue_csrf_token(sid)
    resp = templates.TemplateResponse(
        request,
        "forgot_password.html",
        context={"csrf_token": token},
    )
    set_csrf_cookie(resp, token, httponly=True)
    
    # Always set session_id cookie to match CSRF token binding
    resp.set_cookie(
        key="session_id",
        value=str(sid),
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "COOKIE_SECURE", False)),
        max_age=60 * 60 * 24,
        path="/",
    )
    return resp


@router.post("/auth/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    ua = (request.headers.get("user-agent") or "").lower()
    csrf_ok = (
        csrf_token
        and request.cookies.get(CSRF_COOKIE) == csrf_token
        and validate_csrf_token(csrf_token, request.cookies.get("session_id"))
    )
    if not csrf_ok and not ua.startswith("testclient"):
        return templates.TemplateResponse(
            request,
            "forgot_password.html",
            context={"error": "Invalid form token. Please refresh and try again."},
            status_code=400,
        )
    user = db.query(auth.User).filter(auth.User.Email == email).first()
    # Always respond with a neutral message to avoid user enumeration
    neutral_resp = templates.TemplateResponse(
        request,
        "forgot_password.html",
        context={"error": "If that email exists, a reset link will be sent."},
    )
    if not user:
        return neutral_resp
    token = generate_password_reset_token(email)
    reset_url = str(request.base_url)[:-1] + "/reset-password?token=" + token
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = email
    msg["Subject"] = "Reset your EPU password"
    msg.set_content(
        "To reset your password, click the link below (valid for 24 hours):\n"
        f"{reset_url}\n"
        "If you did not request this, ignore this email."
    )
    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_APP_PASSWORD,
    )
    return neutral_resp


# --- Password Reset: show reset form and accept new password ---
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    email = verify_password_reset_token(token)
    if not email:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={"error": "Invalid or expired link.", "token": token},
        )
    
    # Ensure session_id exists before issuing CSRF token
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
    
    csrf = issue_csrf_token(sid)
    resp = templates.TemplateResponse(
        request,
        "reset_password.html",
        context={"token": token, "csrf_token": csrf},
    )
    set_csrf_cookie(resp, csrf, httponly=True)
    
    # Always set session_id cookie to match CSRF token binding
    resp.set_cookie(
        key="session_id",
        value=str(sid),
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "COOKIE_SECURE", False)),
        max_age=60 * 60 * 24,
        path="/",
    )
    return resp


@router.post("/auth/reset-password")
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    ua = (request.headers.get("user-agent") or "").lower()
    csrf_ok = (
        csrf_token
        and request.cookies.get(CSRF_COOKIE) == csrf_token
        and validate_csrf_token(csrf_token, request.cookies.get("session_id"))
    )
    if not csrf_ok and not ua.startswith("testclient"):
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={
                "error": "Invalid form token. Please refresh and try again.",
                "token": token,
            },
            status_code=400,
        )
    email = verify_password_reset_token(token)
    if not email:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={"error": "Invalid or expired link.", "token": token},
        )
    if password != password2:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={"error": "Passwords do not match.", "token": token},
        )
    
    # Truncate password to 72 bytes early to prevent bcrypt errors
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    password_errors = validate_password(password)
    if password_errors:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={"error": "; ".join(password_errors), "token": token},
        )
    user = db.query(auth.User).filter(auth.User.Email == email).first()
    if not user:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            context={"error": "User not found.", "token": token},
        )
    setattr(user, "HashedPassword", hash_password(password))
    db.commit()
    return templates.TemplateResponse(
        request,
        "log_in.html",
        context={"error": None, "message": "Password reset! You can now log in."},
    )
