import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.models.user import User, UserSession
from app.services.auth import require_user
from app.services.email_utils import send_account_deletion_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.get("/account/delete", response_class=HTMLResponse)
async def account_delete_page(request: Request):
    return templates.TemplateResponse(request, "account_delete.html")


@router.post("/account/delete", response_class=HTMLResponse)
async def account_delete(
    request: Request,
    confirm: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    if not confirm:
        return templates.TemplateResponse(
            request,
            "account_delete.html",
            context={"error": "You must confirm account deletion."},
        )
    user_id = None
    user_id = user.UserID
    user = db.query(User).filter(User.UserID == user_id).first() if user_id is not None else None
    if not user:
        return RedirectResponse("/login", status_code=302)
    audit.warning(
        "account.delete.requested",
        extra={
            "user_id": user_id,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    setattr(user, "MarkedForDeletion", True)
    # Deactivate all sessions for this user
    db.query(UserSession).filter(UserSession.UserID == user_id).update(
        {UserSession.IsActive: False}
    )
    db.commit()
    # Send improved confirmation email
    try:
        await send_account_deletion_email(str(user.Email))
    except Exception:
        pass
    # Remove session cookie
    response = templates.TemplateResponse(request, "account_delete_confirmed.html")
    response.delete_cookie(key="session_id", path="/")
    audit.info(
        "account.delete.confirmed",
        extra={
            "user_id": user_id,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return response


# Note: logout route lives in app/api/logout.py
