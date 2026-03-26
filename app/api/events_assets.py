import logging
import os
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.event import Event
from app.services.auth import require_user
from app.services.upload_streams import (
    UploadSizeExceeded,
    cleanup_temp_upload,
    spool_upload_to_temp,
)
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/events/{event_id}/qr/logo")
async def upload_qr_logo(
    request,
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        return JSONResponse({"ok": False, "error": "Event not found"}, status_code=404)
    # Ownership check
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    except Exception:
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    # Validate
    if not file or not file.filename:
        return JSONResponse({"ok": False, "error": "No file"}, status_code=400)
    ctype = getattr(file, "content_type", "") or ""
    if not (ctype.startswith("image/")):
        return JSONResponse({"ok": False, "error": "Unsupported type"}, status_code=400)
    try:
        staged = await spool_upload_to_temp(
            file,
            allowed_prefixes=("image/",),
            max_bytes=512 * 1024,
        )
    except UploadSizeExceeded:
        return JSONResponse({"ok": False, "error": "File too large"}, status_code=400)
    if not staged.allowed:
        cleanup_temp_upload(staged.temp_path)
        return JSONResponse({"ok": False, "error": "Unsupported type"}, status_code=400)
    # Save under static/uploads/qrs/{event_id}/logo.png
    project_root = Path(__file__).resolve().parents[2]
    out_dir = project_root / "static" / "uploads" / "qrs" / str(event_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    try:
        img = Image.open(staged.temp_path).convert("RGBA")
        img.save(out_path, format="PNG")
    except Exception:
        shutil.copyfile(staged.temp_path, out_path)
    finally:
        cleanup_temp_upload(staged.temp_path)
    rel = "/static/uploads/qrs/" + str(event_id) + "/logo.png"
    return JSONResponse({"ok": True, "path": rel})


@router.post("/events/{event_id}/banner")
async def upload_banner_ajax(
    request,
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    event = db.query(Event).filter(Event.EventID == event_id).first()
    if not event:
        return JSONResponse({"ok": False, "error": "Event not found"}, status_code=404)
    # Ownership check
    try:
        if getattr(event, "UserID", None) != getattr(user, "UserID", None):
            return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    except Exception:
        return JSONResponse({"ok": False, "error": "Forbidden"}, status_code=403)
    # Basic validation
    if not file or not file.filename:
        return JSONResponse({"ok": False, "error": "No file"}, status_code=400)
    ctype = getattr(file, "content_type", "") or ""
    if not ctype.startswith("image/"):
        return JSONResponse({"ok": False, "error": "Unsupported type"}, status_code=400)
    max_bytes = int(getattr(settings, "MAX_UPLOAD_BYTES", 200_000_000))
    try:
        staged = await spool_upload_to_temp(
            file,
            allowed_prefixes=("image/",),
            max_bytes=max_bytes,
        )
    except UploadSizeExceeded:
        return JSONResponse({"ok": False, "error": "File too large"}, status_code=400)
    if not staged.allowed:
        cleanup_temp_upload(staged.temp_path)
        return JSONResponse({"ok": False, "error": "Unsupported type"}, status_code=400)

    # Safe name and save under static/uploads/event_{id}_banner_{safe}
    def _safe_name(name: str) -> str:
        name = name.replace("\\", "/").split("/")[-1]
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)

    safe = _safe_name(file.filename)
    banner_path = f"static/uploads/event_{event_id}_banner_{safe}"
    os.makedirs(os.path.dirname(banner_path), exist_ok=True)
    try:
        # Try to normalise image where possible
        img = Image.open(staged.temp_path).convert("RGBA")
        img.save(banner_path)
    except Exception:
        shutil.copyfile(staged.temp_path, banner_path)
    finally:
        cleanup_temp_upload(staged.temp_path)
    rel = f"/{banner_path}"
    try:
        audit.info(
            "events.edit.asset.banner_updated",
            extra={
                "event_id": event_id,
                "file_name": getattr(file, "filename", None),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
    except Exception:
        pass
    return JSONResponse({"ok": True, "path": rel})
