import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.services.auth import deactivate_session, get_user_id_from_request
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = None
    try:
        user_id = get_user_id_from_request(request, db)
    except Exception:
        pass
    # Best-effort: deactivate the current session in DB
    try:
        sid = request.cookies.get("session_id")
        if sid:
            deactivate_session(db, sid)
    except Exception:
        pass
    audit.info(
        "auth.logout",
        extra={
            "user_id": user_id,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    response = RedirectResponse(url="/login", status_code=302)
    # Delete using matching attributes for reliability
    response.delete_cookie(
        key="session_id",
        path="/",
    )
    return response
