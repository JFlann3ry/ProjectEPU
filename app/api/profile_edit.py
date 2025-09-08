import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.models.export import UserDataExportJob
from app.models.user import User
from app.services.auth import (
    generate_email_token,
    get_current_user,
    hash_password,
    require_user,
    verify_email_token,
)
from app.services.csrf import issue_csrf_token, set_csrf_cookie, validate_csrf_token
from app.services.email_utils import send_verification_email
from app.services.export_service import build_user_export_zip
from db import get_db

router = APIRouter()


@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_page(
    request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    # If not authenticated, still issue a CSRF token so clients/tests can obtain it,
    # then redirect to the login page.
    if not user:
        token = issue_csrf_token(request.cookies.get("session_id"))
        resp = RedirectResponse("/login", status_code=302)
        # Set CSRF cookie so clients/tests can read it immediately.
        # Be explicit with cookie attributes to avoid header merging quirks.
        set_csrf_cookie(resp, token, httponly=False)
        return resp

    # Fetch latest snapshot of user from DB
    u = db.query(User).filter(User.UserID == user.UserID).first()
    token = issue_csrf_token(request.cookies.get("session_id"))
    # Email preferences for inline controls
    from app.models.user_prefs import UserEmailPreference  # noqa: I001 - local import
    prefs_row = (
        db.query(UserEmailPreference)
        .filter(UserEmailPreference.UserID == getattr(user, "UserID", None))
        .first()
    )
    email_prefs = {
        "marketing": bool(getattr(prefs_row, "MarketingOptIn", False)) if prefs_row else False,
        "product": bool(getattr(prefs_row, "ProductUpdatesOptIn", False)) if prefs_row else False,
        "reminders": bool(getattr(prefs_row, "EventRemindersOptIn", True)) if prefs_row else True,
    }
    # Latest export job
    last_job = (
        db.query(UserDataExportJob)
        .filter(UserDataExportJob.UserID == user.UserID)
        .order_by(UserDataExportJob.JobID.desc())
        .first()
    )
    # Compute export status helpers for template
    # Use aware UTC for comparisons but keep naive UTC semantics
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    export_ready = False
    export_expired = False
    cooldown_remaining_seconds = 0
    if last_job:
        status = getattr(last_job, "Status", "")
        expires_at = getattr(last_job, "ExpiresAt", None)
        completed_at = getattr(last_job, "CompletedAt", None)
        if status == "completed":
            if expires_at and isinstance(expires_at, datetime) and expires_at < now:
                export_expired = True
            else:
                export_ready = bool(getattr(last_job, "FilePath", None))
            # 24h cooldown from completion time
            if completed_at and isinstance(completed_at, datetime):
                until = completed_at + timedelta(hours=24)
                if until > now:
                    cooldown_remaining_seconds = int((until - now).total_seconds())
    resp = templates.TemplateResponse(
        request,
        "edit_profile.html",
        context={
            "user": u,
            "csrf_token": token,
            "export_job": last_job,
            "export_ready": export_ready,
            "export_expired": export_expired,
            "export_cooldown_seconds": cooldown_remaining_seconds,
            "email_prefs": email_prefs,
        },
    )
    set_csrf_cookie(resp, token, httponly=False)
    return resp


@router.post("/profile/edit", response_class=HTMLResponse)
async def edit_profile_submit(
    request: Request,
    first_name: str = Form(""),
    last_name: str = Form(""),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # CSRF check
    sid = request.cookies.get("session_id")
    if not csrf_token or not validate_csrf_token(csrf_token, sid):
        return RedirectResponse("/profile/edit?message=invalid", status_code=303)
    u = db.query(User).filter(User.UserID == user.UserID).first()
    if not u:
        return RedirectResponse("/login", status_code=302)
    # Update only names; ignore email changes
    setattr(u, "FirstName", first_name.strip()[:100])
    setattr(u, "LastName", last_name.strip()[:100])
    db.commit()
    return RedirectResponse("/profile/edit?message=saved", status_code=303)


@router.post("/profile/export/request")
async def profile_export_request(
    request: Request,
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    sid = request.cookies.get("session_id")
    if not csrf_token or not validate_csrf_token(csrf_token, sid):
        return RedirectResponse("/profile/edit?message=invalid", status_code=303)
    u = db.query(User).filter(User.UserID == user.UserID).first()
    if not u:
        return RedirectResponse("/login", status_code=302)
    # Avoid duplicate running jobs & enforce cooldown
    existing = (
        db.query(UserDataExportJob)
        .filter(UserDataExportJob.UserID == u.UserID)
        .order_by(UserDataExportJob.JobID.desc())
        .first()
    )
    if existing and getattr(existing, "Status", "") in ("queued", "running"):
        return RedirectResponse("/profile/edit?message=export_pending", status_code=303)
    # If last completed within 24h, block new request
    if existing and getattr(existing, "Status", "") == "completed":
        completed_at = getattr(existing, "CompletedAt", None)
        if completed_at and isinstance(completed_at, datetime):
            if completed_at + timedelta(hours=24) > datetime.now(timezone.utc).replace(tzinfo=None):
                return RedirectResponse("/profile/edit?message=export_cooldown", status_code=303)
    # Create job
    job = UserDataExportJob(UserID=u.UserID, Status="queued")
    db.add(job)
    db.commit()
    # Build synchronously for now
    try:
        build_user_export_zip(db, u, storage_root="storage")
        return RedirectResponse("/profile/edit?message=export_ready", status_code=303)
    except Exception:
        return RedirectResponse("/profile/edit?message=export_failed", status_code=303)


@router.get("/profile/export/download")
async def profile_export_download(db: Session = Depends(get_db), user=Depends(require_user)):
    # Get latest completed job
    job = (
        db.query(UserDataExportJob)
        .filter(UserDataExportJob.UserID == user.UserID)
        .order_by(UserDataExportJob.JobID.desc())
        .first()
    )
    if not job or getattr(job, "Status", "") != "completed":
        return RedirectResponse("/profile/edit?message=export_not_ready", status_code=303)
    # Check expiry
    expires_at = getattr(job, "ExpiresAt", None)
    if (
        expires_at
        and isinstance(expires_at, datetime)
        and expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
    ):
        return RedirectResponse("/profile/edit?message=export_expired", status_code=303)
    path = getattr(job, "FilePath", None)
    if not path or not os.path.exists(path):
        return RedirectResponse("/profile/edit?message=export_missing", status_code=303)
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/zip", filename=filename)


@router.get("/profile/password", response_class=HTMLResponse)
async def password_page(
    request: Request, db: Session = Depends(get_db), user=Depends(require_user)
):
    token = issue_csrf_token(request.cookies.get("session_id"))
    resp = templates.TemplateResponse(
        request,
        "password_change.html",
        context={"csrf_token": token},
    )
    set_csrf_cookie(resp, token, httponly=False)
    return resp


@router.post("/profile/password", response_class=HTMLResponse)
async def password_request(
    request: Request,
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # CSRF check
    sid = request.cookies.get("session_id")
    if not csrf_token or not validate_csrf_token(csrf_token, sid):
        return RedirectResponse("/profile/password?message=invalid", status_code=303)
    # Basic validation
    if not new_password or len(new_password) < 8 or new_password != confirm_password:
        return RedirectResponse("/profile/password?message=invalid", status_code=303)
    # Issue an email confirmation link that encodes the email + hashed temp
    email = user.Email
    # Create a short-lived token bound to email and the unhashed password candidate
    # We won't store it server-side; we verify token and then set hashed password.
    payload = f"{email}|{new_password}"
    token = generate_email_token(payload)
    confirm_base = str(request.url_for("password_confirm"))
    confirm_url = f"{confirm_base}?token={token}"
    try:
        await send_verification_email(email, confirm_url)
    except Exception:
        pass
    return RedirectResponse("/profile/password?message=sent", status_code=303)


@router.get("/profile/password/confirm", name="password_confirm", response_class=HTMLResponse)
async def password_confirm(request: Request, token: str = "", db: Session = Depends(get_db)):
    payload = verify_email_token(token)
    if not payload or "|" not in payload:
        return templates.TemplateResponse(
            request, "password_change_done.html", context={"ok": False}
        )
    email, new_password = payload.split("|", 1)
    # Locate user by email
    u = (
        db.query(User)
        .filter(User.Email == email, User.IsActive, ~User.MarkedForDeletion)
        .first()
    )
    if not u:
        return templates.TemplateResponse(
            request, "password_change_done.html", context={"ok": False}
        )
    setattr(u, "HashedPassword", hash_password(new_password))
    db.commit()
    return templates.TemplateResponse(request, "password_change_done.html", context={"ok": True})
