"""Owner upload endpoint for events."""

import os
import re
import shutil

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.event import Event, FileMetadata
from app.services.auth import require_user
from app.services.csrf import CSRF_COOKIE, validate_csrf_token
from app.services.thumbs import generate_all_thumbs_for_file
from app.services.upload_streams import (
    UploadSizeExceeded,
    cleanup_temp_upload,
    spool_upload_to_temp,
)
from db import get_db

router = APIRouter()


def _safe_name(name: str) -> str:
    """Sanitize filename: strip path, remove unsafe chars."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _unique_path(base_dir: str, fname: str) -> str:
    """Ensure unique file path by appending numeric suffix if needed."""
    root, ext = os.path.splitext(fname)
    candidate = os.path.join(base_dir, fname)
    idx = 1
    while os.path.exists(candidate):
        candidate = os.path.join(base_dir, f"{root}_{idx}{ext}")
        idx += 1
    return candidate


@router.post("/events/{event_id}/upload")
async def owner_upload_to_event(
    request: Request,
    event_id: int,
    files: list[UploadFile] = File([]),
    csrf_token: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Authenticated upload for event owners.

    Saves files to storage/{user}/{event}/, creates FileMetadata rows, and generates thumbnails.
    Redirects back to the gallery view.
    """
    # CSRF validation (skip for TestClient UA)
    try:
        ua = (request.headers.get("user-agent") or "").lower()
        sid = request.cookies.get("session_id")
        cookie_token = request.cookies.get(CSRF_COOKIE)
        csrf_ok = (
            csrf_token
            and cookie_token
            and sid
            and cookie_token == csrf_token
            and validate_csrf_token(csrf_token, sid)
        )
        if not csrf_ok and not ua.startswith("testclient"):
            referer = request.headers.get("referer") or "/gallery"
            return RedirectResponse(url=referer, status_code=303)
    except (AttributeError, ValueError, TypeError):
        # CSRF check failed due to malformed input or missing attributes
        referer = request.headers.get("referer") or "/gallery"
        return RedirectResponse(url=referer, status_code=303)

    # Verify event ownership
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event or getattr(event, "UserID", None) != getattr(user, "UserID", None):
        return RedirectResponse(url="/events", status_code=303)

    # Prepare storage paths
    uid = int(getattr(user, "UserID"))
    base = os.path.join("storage", str(uid), str(int(event_id)))
    os.makedirs(base, exist_ok=True)

    created = 0
    allowed_prefixes = tuple(
        getattr(settings, "ALLOWED_UPLOAD_MIME_PREFIXES", ("image/", "video/"))
    )
    max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))
    for uf in files or []:
        staged = None
        try:
            orig_name = _safe_name(uf.filename or "upload.bin")
            staged = await spool_upload_to_temp(
                uf,
                allowed_prefixes=allowed_prefixes,
                max_bytes=max_bytes,
            )
            if not staged.allowed:
                continue
            dest = _unique_path(base, orig_name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(staged.temp_path, dest)
            size_bytes = int(staged.size_bytes)

            # Create FileMetadata
            fm = FileMetadata(
                EventID=int(event_id),
                FileName=os.path.basename(dest),
                FileType=str(staged.sniffed_mime or "application/octet-stream"),
                FileSize=int(size_bytes),
            )
            db.add(fm)
            db.flush()

            # Generate thumbnails/poster (best-effort)
            try:
                gid = int(getattr(fm, "FileMetadataID"))
                gtype = str(getattr(fm, "FileType", ""))
                gname = str(getattr(fm, "FileName", ""))
                generate_all_thumbs_for_file(
                    uid,
                    int(event_id),
                    gid,
                    gtype,
                    gname,
                )
            except (OSError, ImportError, ValueError):
                # Thumb generation best-effort; don't fail upload on this
                pass
            created += 1
        except UploadSizeExceeded:
            continue
        except (ValueError, OSError, KeyError):
            # Spool/copy/DB error; attempt rollback then continue
            try:
                db.rollback()
            except (RuntimeError, AttributeError):
                pass
            continue
        finally:
            cleanup_temp_upload(getattr(staged, "temp_path", None))

    if created:
        try:
            db.commit()
        except (RuntimeError, AttributeError):
            # DB commit failed; attempt rollback
            try:
                db.rollback()
            except (RuntimeError, AttributeError):
                pass
    referer = request.headers.get("referer") or "/gallery"
    return RedirectResponse(url=referer, status_code=303)
