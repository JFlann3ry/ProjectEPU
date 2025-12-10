import datetime as _dt
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.gallery import DELETION_LOGS
from app.core.settings import settings
from app.core.templates import templates
from app.models import AppErrorLog
from app.models.billing import Purchase
from app.models.event import Event, FileMetadata, Theme, ThemeAudit
from app.models.user import User
from app.services.auth import require_admin
from app.services.csrf import CSRF_COOKIE, issue_csrf_token, validate_csrf_token
from db import get_db

router = APIRouter()

audit = logging.getLogger("audit")


def _ensure_admin(user) -> None:
    if not bool(getattr(user, "IsAdmin", False)):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    q: Optional[str] = None,
    users_page: int = 1,
    uploads_page: int = 1,
    page_size: int = 10,
):

    total_users = db.query(User).count()
    total_events = db.query(Event).count()
    total_files = db.query(FileMetadata).count()
    total_purchases = db.query(Purchase).count()

    # Top events by file count
    top_events = (
        db.query(Event.EventID, Event.Name, func.count(FileMetadata.FileMetadataID).label("count"))
        .join(FileMetadata, FileMetadata.EventID == Event.EventID, isouter=True)
        .group_by(Event.EventID, Event.Name)
        .order_by(func.count(FileMetadata.FileMetadataID).desc())
        .limit(5)
        .all()
    )

    # Recent signups and uploads with simple pagination
    ps = max(1, min(int(page_size or 10), 50))
    up = max(1, int(users_page or 1))
    up_offset = (up - 1) * ps
    rp = max(1, int(uploads_page or 1))
    rp_offset = (rp - 1) * ps
    recent_users = (
        db.query(User).order_by(User.DateCreated.desc()).offset(up_offset).limit(ps).all()
    )
    recent_uploads = (
        db.query(FileMetadata)
        .order_by(FileMetadata.UploadDate.desc())
        .offset(rp_offset)
        .limit(ps)
        .all()
    )

    # Recent error lines from log (best-effort, tail last ~2000 bytes)
    recent_errors = []
    log_path = "logs/app.log"
    try:
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                # Seek to near end of file (~2KB from end)
                try:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(size - 2048, 0), 0)
                except Exception:
                    pass
                data = f.read().decode(errors="ignore")
            for line in data.splitlines():
                if "ERROR" in line or "Exception" in line:
                    recent_errors.append(line)
            recent_errors = recent_errors[-20:]
    except Exception:
        recent_errors = []

    # Simple search across users and events if q provided
    search_results = {"users": [], "events": []}
    if q:
        q_like = f"%{q}%"
        search_results["users"] = (
            db.query(User)
            .filter(
                or_(
                    User.Email.ilike(q_like),
                    User.FirstName.ilike(q_like),
                    User.LastName.ilike(q_like),
                )
            )
            .limit(10)
            .all()
        )
        search_results["events"] = (
            db.query(Event)
            .filter(or_(Event.Name.ilike(q_like), Event.Code.ilike(q_like)))
            .limit(10)
            .all()
        )

    # Approx storage usage (bytes) by walking storage dir (best-effort)
    storage_root = os.path.join("storage")
    storage_bytes = 0
    try:
        for root, _, files in os.walk(storage_root):
            for f in files:
                p = os.path.join(root, f)
                try:
                    storage_bytes += os.path.getsize(p)
                except Exception:
                    pass
    except Exception:
        storage_bytes = 0

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        context={
            "stats": {
                "users": total_users,
                "events": total_events,
                "files": total_files,
                "purchases": total_purchases,
                "storage_bytes": storage_bytes,
            },
            "top_events": top_events,
            "recent_users": recent_users,
            "recent_uploads": recent_uploads,
            "recent_errors": recent_errors,
            "q": q or "",
            "search_results": search_results,
            "users_page": up,
            "uploads_page": rp,
            "page_size": ps,
        },
    )


@router.get("/admin/errors", response_class=HTMLResponse)
async def admin_errors_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    request_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
):
    ps = max(1, min(int(page_size or 25), 200))
    p = max(1, int(page or 1))
    q = db.query(AppErrorLog)
    if request_id:
        q = q.filter(AppErrorLog.RequestID == request_id)
    # Simple date filters (YYYY-MM-DD)
    if since:
        try:
            dt = _dt.datetime.fromisoformat(since)
            q = q.filter(AppErrorLog.OccurredAt >= dt)
        except Exception:
            pass
    if until:
        try:
            dt = _dt.datetime.fromisoformat(until)
            q = q.filter(AppErrorLog.OccurredAt <= dt)
        except Exception:
            pass
    total = q.count()
    rows = (
        q.order_by(AppErrorLog.OccurredAt.desc())
        .offset((p - 1) * ps)
        .limit(ps)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "admin_errors.html",
        context={
            "rows": rows,
            "total": total,
            "page": p,
            "page_size": ps,
            "request_id": request_id or "",
            "since": since or "",
            "until": until or "",
        },
    )


@router.get("/admin/mini-dashboard", response_class=HTMLResponse)
async def admin_mini_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    # Recent AppErrorLog entries
    rows = (
        db.query(AppErrorLog)
        .order_by(AppErrorLog.OccurredAt.desc())
        .limit(10)
        .all()
    )
    # Recent delete/restore operations captured in-memory
    recent_actions = list(DELETION_LOGS[-10:])
    return templates.TemplateResponse(
        request,
        "admin_mini_dashboard.html",
        context={
            "error_rows": rows,
            "recent_actions": recent_actions,
            "debug_routes_enabled": bool(
                getattr(settings, "DEBUG_ROUTES_ENABLED", False)
            ),
        },
    )


@router.get("/admin/audit-logs")
async def download_audit_logs(request: Request, user=Depends(require_admin)):
    # Serve a stable snapshot of the log to avoid Content-Length
    # mismatches if the file grows during send
    log_path = "logs/app.log"
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="No logs available")
    try:
        size = os.path.getsize(log_path)
    except Exception:
        size = None
    try:
        with open(log_path, "rb") as f:
            data = f.read(size if isinstance(size, int) and size >= 0 else -1)
    except Exception:
        # Fallback: empty response if read fails
        data = b""
    headers = {
        "Content-Disposition": "attachment; filename=audit.log",
        "Cache-Control": "no-store",
    }
    return Response(content=data, media_type="text/plain; charset=utf-8", headers=headers)


def _redact_record(obj: dict) -> dict:
    if not isinstance(obj, dict):
        return obj
    redact_keys = {
        "Password",
        "HashedPassword",
        "token",
        "Token",
        "session_id",
        "StripeSecretKey",
        "GMAIL_PASS",
    }
    res = {}
    for k, v in obj.items():
        if any(k.lower() == rk.lower() for rk in redact_keys):
            res[k] = "[REDACTED]"
        else:
            res[k] = v
    return res


@router.get("/admin/components", response_class=HTMLResponse)
async def admin_components_page(request: Request, user=Depends(require_admin)):
    return templates.TemplateResponse(request, "admin_components.html")


@router.get("/admin/audit-logs/export")
async def filter_audit_logs(
    request: Request,
    level: Optional[str] = None,
    logger: Optional[str] = None,
    contains: Optional[str] = None,
    type_hint: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user=Depends(require_admin),
):
    """
    Filter JSON log lines and return as redacted JSONL.
    Query params:
      - level: INFO|WARNING|ERROR|DEBUG
      - logger: app|audit (substring match)
      - contains: substring to search in message
      - type_hint: substring to search in structured message/extra
      - since/until: ISO date substrings to match on 'time'
    """
    log_path = "logs/app.log"
    if not os.path.exists(log_path):
        return PlainTextResponse("", status_code=200)
    lines_out: list[str] = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    # skip non-JSON lines when filtering
                    continue
                if level and str(obj.get("level", "")).upper() != level.upper():
                    continue
                if logger and logger.lower() not in str(obj.get("logger", "")).lower():
                    continue
                if contains and contains.lower() not in str(obj.get("message", "")).lower():
                    continue
                if type_hint:
                    # scan serialized obj for substring
                    if type_hint.lower() not in json.dumps(obj).lower():
                        continue
                if since:
                    t = str(obj.get("time", ""))
                    if since not in t:
                        continue
                if until:
                    t = str(obj.get("time", ""))
                    if until not in t:
                        continue
                obj = _redact_record(obj)
                lines_out.append(json.dumps(obj, ensure_ascii=False))
    except Exception:
        pass
    data = ("\n".join(lines_out) + ("\n" if lines_out else "")).encode("utf-8")
    headers = {"Content-Disposition": "attachment; filename=audit_filtered.jsonl"}
    return Response(content=data, media_type="application/x-ndjson", headers=headers)


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    q: Optional[str] = None,
    is_admin: Optional[bool] = None,
    verified: Optional[bool] = None,
    active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
):
    from app.models.user import User

    ps = max(1, min(int(page_size or 20), 100))
    p = max(1, int(page or 1))
    qy = db.query(User)
    if q:
        q_like = f"%{q}%"
        qy = qy.filter(
            or_(User.Email.ilike(q_like), User.FirstName.ilike(q_like), User.LastName.ilike(q_like))
        )
    if is_admin is not None:
        qy = qy.filter(User.IsAdmin == bool(is_admin))
    if verified is not None:
        qy = qy.filter(User.EmailVerified == bool(verified))
    if active is not None:
        qy = qy.filter(User.IsActive == bool(active))
    total = qy.count()
    rows = qy.order_by(desc(User.DateCreated)).offset((p - 1) * ps).limit(ps).all()

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "rows": rows,
            "q": q or "",
            "is_admin": is_admin,
            "verified": verified,
            "active": active,
            "page": p,
            "page_size": ps,
            "total": total,
        },
    )


@router.post("/admin/users/{user_id}/set-admin")
async def admin_set_admin(
    user_id: int,
    is_admin: int = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    from app.models.user import User

    target = db.query(User).filter(User.UserID == int(user_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    want_admin = bool(int(is_admin))

    # Prevent removing the last admin (including self-demote)
    if not want_admin:
        current_admins = db.query(User).filter(User.IsAdmin, User.IsActive).count()
        if current_admins <= 1 and bool(getattr(target, "IsAdmin", False)):
            raise HTTPException(status_code=400, detail="Cannot remove the last active admin")

    setattr(target, "IsAdmin", want_admin)
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/admin/event/{event_id}", response_class=HTMLResponse)
async def admin_event_detail(
    event_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    from app.models.event import Event
    from app.models.user import User

    ev = db.query(Event).filter(Event.EventID == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    owner = db.query(User).filter(User.UserID == ev.UserID).first()
    return templates.TemplateResponse(
        request,
        "admin_event.html",
        context={"event": ev, "owner": owner},
    )


@router.post("/admin/seed-themes")
async def admin_seed_themes(
    request: Request, user=Depends(require_admin), csrf_token: str = Form("")
):
    # Use in-process seeder to insert/update default themes
    try:
        # Optional CSRF check (best-effort)
        cookie_token = request.cookies.get(CSRF_COOKIE)
        if cookie_token and csrf_token:
            if (
                not validate_csrf_token(csrf_token, request.cookies.get("session_id"))
                or cookie_token != csrf_token
            ):
                raise HTTPException(
                    status_code=400, detail="Invalid form token. Please refresh and try again."
                )
        from app.db_seed_themes import seed_themes

        seed_themes()
        return RedirectResponse("/admin/themes", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding themes failed: {e}")



@router.get("/admin/themes", response_class=HTMLResponse)
async def admin_list_themes(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    id: int | None = None,
):
    from app.models.event import Theme

    themes = db.query(Theme).order_by(Theme.Name.asc()).all()
    selected = None
    if id:
        selected = db.query(Theme).filter(Theme.ThemeID == int(id)).first()
    if not selected and themes:
        selected = themes[0]
    token = issue_csrf_token(request.cookies.get("session_id"))
    resp = templates.TemplateResponse(
        request,
        "admin_themes.html",
        context={"themes": themes, "selected": selected, "csrf_token": token},
    )
    # Set CSRF cookie for form POST verification
    resp.set_cookie(CSRF_COOKIE, token, httponly=False, samesite="lax")
    return resp


@router.post("/admin/themes/{theme_id}/update")
async def admin_update_theme(
    theme_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    Name: str = Form(...),
    Description: str = Form(""),
    BackgroundColour: str = Form(""),
    TextColour: str = Form(""),
    ButtonColour1: str = Form(""),
    ButtonColour2: str = Form(""),
    AccentColour: str = Form(""),
    InputBackgroundColour: str = Form(""),
    DropzoneBackgroundColour: str = Form(""),
    ButtonStyle: str = Form(""),
    FontFamily: str = Form(""),
    BackgroundImage: str = Form(""),
    IsActive: int = Form(0),
    csrf_token: str = Form(""),
):
    from app.models.event import Theme

    theme = db.query(Theme).filter(Theme.ThemeID == int(theme_id)).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not csrf_token
        or not validate_csrf_token(csrf_token, request.cookies.get("session_id"))
        or cookie_token != csrf_token
    ):
        raise HTTPException(
            status_code=400, detail="Invalid form token. Please refresh and try again."
        )

    # Basic sanitization/normalization
    def norm_color(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return v
        if not v.startswith("#") and v.startswith("rgb") is False:
            v = "#" + v
        return v

    # Capture before state for audit diff
    before = {
        "Name": getattr(theme, "Name", None),
        "Description": getattr(theme, "Description", None),
        "BackgroundColour": getattr(theme, "BackgroundColour", None),
        "TextColour": getattr(theme, "TextColour", None),
        "ButtonColour1": getattr(theme, "ButtonColour1", None),
        "ButtonColour2": getattr(theme, "ButtonColour2", None),
        "ButtonStyle": getattr(theme, "ButtonStyle", None),
        "AccentColour": getattr(theme, "AccentColour", None),
        "InputBackgroundColour": getattr(theme, "InputBackgroundColour", None),
        "DropzoneBackgroundColour": getattr(theme, "DropzoneBackgroundColour", None),
        "FontFamily": getattr(theme, "FontFamily", None),
        "BackgroundImage": getattr(theme, "BackgroundImage", None),
    "IsActive": getattr(theme, "IsActive", None),
    }

    setattr(theme, "Name", Name.strip())
    setattr(theme, "Description", (Description or "").strip() or None)
    setattr(theme, "BackgroundColour", norm_color(BackgroundColour) or None)
    setattr(theme, "TextColour", norm_color(TextColour) or None)
    setattr(theme, "ButtonColour1", norm_color(ButtonColour1) or None)
    setattr(theme, "ButtonColour2", norm_color(ButtonColour2) or None)
    setattr(
        theme,
        "ButtonStyle",
        (
            (ButtonStyle or "").strip()
            if (ButtonStyle or "").strip() in ("gradient", "solid")
            else None
        ),
    )
    setattr(theme, "AccentColour", norm_color(AccentColour) or None)
    setattr(theme, "InputBackgroundColour", norm_color(InputBackgroundColour) or None)
    setattr(theme, "DropzoneBackgroundColour", norm_color(DropzoneBackgroundColour) or None)
    setattr(theme, "FontFamily", (FontFamily or "").strip() or None)
    setattr(theme, "BackgroundImage", (BackgroundImage or "").strip() or None)
    # Handle boolean checkbox
    try:
        want_active = bool(int(IsActive))
    except Exception:
        want_active = False
    setattr(theme, "IsActive", want_active)
    db.add(theme)
    db.commit()
    # Compute simple diff
    after = {
        "Name": getattr(theme, "Name", None),
        "Description": getattr(theme, "Description", None),
        "BackgroundColour": getattr(theme, "BackgroundColour", None),
        "TextColour": getattr(theme, "TextColour", None),
        "ButtonColour1": getattr(theme, "ButtonColour1", None),
        "ButtonColour2": getattr(theme, "ButtonColour2", None),
        "ButtonStyle": getattr(theme, "ButtonStyle", None),
        "AccentColour": getattr(theme, "AccentColour", None),
        "InputBackgroundColour": getattr(theme, "InputBackgroundColour", None),
        "DropzoneBackgroundColour": getattr(theme, "DropzoneBackgroundColour", None),
        "FontFamily": getattr(theme, "FontFamily", None),
        "BackgroundImage": getattr(theme, "BackgroundImage", None),
    "IsActive": getattr(theme, "IsActive", None),
    }
    changes = {}
    for k in after.keys():
        if before.get(k) != after.get(k):
            changes[k] = {"from": before.get(k), "to": after.get(k)}
    # Emit audit log entry and persist ThemeAudit row
    try:
        audit.info(
            "admin.theme.update",
            extra={
                "theme_id": int(getattr(theme, "ThemeID")),
                "admin_user_id": int(getattr(user, "UserID", 0) or 0),
                "request_id": getattr(request.state, "request_id", None),
                "client": request.client.host if request.client else None,
                "changes": changes,
            },
        )
        # DB audit persistence
        try:
            ta = ThemeAudit(
                ThemeID=int(getattr(theme, "ThemeID")),
                UserID=int(getattr(user, "UserID", 0) or 0),
                ClientIP=(request.client.host if request.client else None),
                UserAgent=request.headers.get("user-agent"),
                RequestID=getattr(request.state, "request_id", None),
                Changes=json.dumps(changes, ensure_ascii=False) if changes else None,
            )
            db.add(ta)
            db.commit()
        except Exception:
            pass
    except Exception:
        pass
    return RedirectResponse(url=f"/admin/themes?id={theme.ThemeID}", status_code=303)


@router.get("/admin/themes/{theme_id}/export")
async def admin_export_theme(
    theme_id: int, db: Session = Depends(get_db), user=Depends(require_admin)
):
    theme = db.query(Theme).filter(Theme.ThemeID == int(theme_id)).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    data = {
        "Name": getattr(theme, "Name", None),
        "Description": getattr(theme, "Description", None),
        "BackgroundColour": getattr(theme, "BackgroundColour", None),
        "TextColour": getattr(theme, "TextColour", None),
        "ButtonColour1": getattr(theme, "ButtonColour1", None),
        "ButtonColour2": getattr(theme, "ButtonColour2", None),
        "ButtonStyle": getattr(theme, "ButtonStyle", None),
        "AccentColour": getattr(theme, "AccentColour", None),
        "InputBackgroundColour": getattr(theme, "InputBackgroundColour", None),
        "DropzoneBackgroundColour": getattr(theme, "DropzoneBackgroundColour", None),
        "FontFamily": getattr(theme, "FontFamily", None),
    "BackgroundImage": getattr(theme, "BackgroundImage", None),
    "IsActive": getattr(theme, "IsActive", None),
    }
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    try:
        tid = int(getattr(theme, "ThemeID"))  # type: ignore[arg-type]
    except Exception:
        tid = 0
    headers = {"Content-Disposition": f"attachment; filename=theme_{tid}.json"}
    return Response(content=payload, media_type="application/json; charset=utf-8", headers=headers)


@router.post("/admin/themes/{theme_id}/duplicate")
async def admin_duplicate_theme(
    theme_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    csrf_token: str = Form(""),
):
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not csrf_token
        or not validate_csrf_token(csrf_token, request.cookies.get("session_id"))
        or cookie_token != csrf_token
    ):
        raise HTTPException(
            status_code=400, detail="Invalid form token. Please refresh and try again."
        )
    theme = db.query(Theme).filter(Theme.ThemeID == int(theme_id)).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    # Create a shallow copy with a new name
    t2 = Theme()
    for field in [
        "BackgroundColour",
        "TextColour",
        "ButtonColour1",
        "ButtonColour2",
        "ButtonStyle",
        "AccentColour",
        "InputBackgroundColour",
        "DropzoneBackgroundColour",
        "FontFamily",
        "BackgroundImage",
    ]:
        setattr(t2, field, getattr(theme, field))
    # Preserve active state on duplicate (default to True if unknown)
    try:
        setattr(t2, "IsActive", bool(getattr(theme, "IsActive", True)))
    except Exception:
        setattr(t2, "IsActive", True)
    base_name = getattr(theme, "Name", "Theme") or "Theme"
    new_name = base_name + " Copy"
    # Ensure uniqueness best-effort
    existing = db.query(Theme).filter(Theme.Name == new_name).count()
    if existing:
        new_name = f"{base_name} Copy {existing+1}"
    setattr(t2, "Name", new_name)
    setattr(t2, "Description", getattr(theme, "Description", None))
    db.add(t2)
    db.commit()
    try:
        audit.info(
            "admin.theme.duplicate",
            extra={
                "src_theme_id": int(getattr(theme, "ThemeID")),
                "new_theme_id": int(getattr(t2, "ThemeID")),
                "admin_user_id": int(getattr(user, "UserID", 0) or 0),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
    except Exception:
        pass
    return RedirectResponse(url=f"/admin/themes?id={t2.ThemeID}", status_code=303)


@router.get("/admin/themes/audit", response_class=HTMLResponse)
async def admin_themes_audit(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    theme_id: Optional[int] = None,
    admin_user_id: Optional[int] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):

    # Theme list for filter dropdown
    themes = db.query(Theme).order_by(Theme.Name.asc()).all()

    qy = (
        db.query(ThemeAudit, Theme, User)
        .join(Theme, Theme.ThemeID == ThemeAudit.ThemeID, isouter=True)
        .join(User, User.UserID == ThemeAudit.UserID, isouter=True)
    )
    if theme_id:
        qy = qy.filter(ThemeAudit.ThemeID == int(theme_id))
    if admin_user_id:
        qy = qy.filter(ThemeAudit.UserID == int(admin_user_id))
    if q:
        q_like = f"%{q.lower()}%"
        qy = qy.filter(
            or_(func.lower(Theme.Name).like(q_like), func.lower(ThemeAudit.Changes).like(q_like))
        )

    # Best-effort parse of since/until (YYYY-MM-DD)
    def _parse_date(s: Optional[str]):
        try:
            if not s:
                return None
            return _dt.datetime.fromisoformat(s)
        except Exception:
            return None

    since_dt = _parse_date(since)
    until_dt = _parse_date(until)
    if since_dt:
        qy = qy.filter(ThemeAudit.ChangedAt >= since_dt)
    if until_dt:
        # include full day if a date is supplied without time
        if until and len(str(until)) == 10:
            until_dt = until_dt + _dt.timedelta(days=1)
        qy = qy.filter(ThemeAudit.ChangedAt < until_dt)

    ps = max(1, min(int(page_size or 20), 100))
    p = max(1, int(page or 1))
    total = qy.count()
    rows = qy.order_by(desc(ThemeAudit.ChangedAt)).offset((p - 1) * ps).limit(ps).all()

    shaped = []
    for ta, t, u in rows:
        try:
            ch = json.loads(getattr(ta, "Changes") or "{}")
        except Exception:
            ch = {}
        ch_list = []
        for k, v in ch.items():
            ch_list.append({"key": k, "from": v.get("from"), "to": v.get("to")})
        shaped.append(
            {
                "audit": ta,
                "theme": t,
                "user": u,
                "changes": ch_list,
                "changes_count": len(ch_list),
            }
        )

    max_page = (total + ps - 1) // ps if ps else 1
    return templates.TemplateResponse(
        request,
        "admin_themes_audit.html",
        context={
            "themes": themes,
            "results": shaped,
            "total": total,
            "page": p,
            "page_size": ps,
            "max_page": max_page,
            "filters": {
                "theme_id": theme_id,
                "admin_user_id": admin_user_id,
                "q": q or "",
                "since": since or "",
                "until": until or "",
            },
        },
    )


@router.get("/admin/components", response_class=HTMLResponse)
async def admin_components(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    return templates.TemplateResponse(request, "admin_components.html")
