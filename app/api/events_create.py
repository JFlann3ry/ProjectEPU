import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.services.auth import require_user
from db import get_db

audit = logging.getLogger("audit")

router = APIRouter()


@router.get("/events/create", response_class=HTMLResponse)
async def create_event_page(
    request: Request, db: Session = Depends(get_db), user=Depends(require_user)
):
    # Provide event types for the type selector
    try:
        from app.models.event import EventType

        event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    except Exception:
        event_types = []
    # Enforce plan: require paid plan; Basic (code 'single') allows only 1 event
    from app.models.event import Event
    try:
        from app.services.billing_utils import get_active_plan

        plan_row, _features = get_active_plan(db, int(getattr(user, "UserID", 0)))
        plan_code = (plan_row.Code or "").lower() if plan_row else None
    except Exception:
        plan_code = None

    if not plan_code:
        # No active package -> go to billing/pricing
        return RedirectResponse("/billing", status_code=303)
    if plan_code == "single":
        count = db.query(Event).filter(Event.UserID == getattr(user, "UserID", None)).count()
        # Check for paid entitlement purchases that represent additional_event
        try:
            from app.models.billing import Purchase as _Purchase

            extra_entitlement = (
                db.query(_Purchase)
                .filter(
                    _Purchase.UserID == getattr(user, "UserID", None),
                    _Purchase.Amount == 0,
                    _Purchase.Status == "paid",
                )
                .order_by(_Purchase.CreatedAt.desc())
                .first()
            )
        except Exception:
            # ignore lookup errors
            pass

        if count >= 1:
            # Provide a direct link to purchase an additional event
            return templates.TemplateResponse(
                request,
                "create_event.html",
                context={
                    "error": 'Your plan allows only 1 event. Purchase an <a href="/extras?code=additional_event">additional event for £20</a> to create more.',
                    "event_types": event_types,
                },
            )
    return templates.TemplateResponse(
        request,
        "create_event.html",
        context={"event_types": event_types},
    )


@router.post("/events/create")
async def create_event_submit(
    request: Request,
    name: str = Form(...),
    date: str = Form(None),
    type: str = Form(None),
    type_custom: str = Form(None),
    terms: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    # Basic validation
    # Get event types for re-rendering on validation errors
    try:
        from app.models.event import EventType

        event_types = db.query(EventType).order_by(EventType.Name.asc()).all()
    except Exception:
        event_types = []
    # Enforce plan again on POST (same logic as GET) — use shared helper
    try:
        from app.services.billing_utils import get_active_plan

        plan_row, _features = get_active_plan(db, int(getattr(user, "UserID", 0)))
        plan_code = (plan_row.Code or "").lower() if plan_row else None
    except Exception:
        plan_code = None
    # Import Event model for count checks
    from app.models.event import Event

    if not plan_code:
        return RedirectResponse("/billing", status_code=303)
    if plan_code == "single":
        count = db.query(Event).filter(Event.UserID == getattr(user, "UserID", None)).count()
        # Allow consuming one zero-amount paid entitlement (issued when purchasing additional_event)
        try:
            from app.models.billing import Purchase as _Purchase

            entitlement = (
                db.query(_Purchase)
                .filter(
                    _Purchase.UserID == getattr(user, "UserID", None),
                    _Purchase.Amount == 0,
                    _Purchase.Status == "paid",
                )
                .order_by(_Purchase.CreatedAt.asc())
                .first()
            )
        except Exception:
            entitlement = None

        if count >= 1:
            if entitlement:
                # consume entitlement so it can't be reused
                try:
                    setattr(entitlement, "Status", "used")
                    db.commit()
                except Exception:
                    db.rollback()
            else:
                return templates.TemplateResponse(
                    request,
                    "create_event.html",
                    context={
                        "error": "Your plan allows only 1 event. Please upgrade to create more.",
                        "event_types": event_types,
                    },
                )
    if not name:
        return templates.TemplateResponse(
            request,
            "create_event.html",
            context={"error": "Event name is required.", "event_types": event_types},
        )
    if not terms:
        return templates.TemplateResponse(
            request,
            "create_event.html",
            context={
                "error": "You must agree to the terms.",
                "event_types": event_types,
            },
        )

    # Resolve or create EventType
    event_type_id = None
    pending_custom_event_type = None
    try:
        from app.models.event import EventType

        chosen = (type or "").strip()
        custom = (type_custom or "").strip()
        name_to_use = custom if (chosen.lower() == "other" and custom) else (chosen or None)
        if name_to_use:
            et = db.query(EventType).filter(EventType.Name == name_to_use).first()
            if not et:
                et = EventType(Name=name_to_use)
                db.add(et)
                db.commit()
                db.refresh(et)
            event_type_id = et.EventTypeID
            # If the user supplied a custom name (selected 'other'), record it in CustomEventType
            try:
                if chosen.lower() == "other" and custom:
                    from app.models.event import CustomEventType

                    pending_custom_event_type = CustomEventType(
                        EventID=None, EventTypeID=et.EventTypeID, CustomEventName=custom
                    )
            except Exception:
                pending_custom_event_type = None
    except Exception:
        event_type_id = None
        pending_custom_event_type = None

    # Generate a unique short event code
    import random
    import string

    def gen_code(n: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(n))

    def gen_password(n: int = 6) -> str:
        # human-friendly password: exactly n alphanumeric chars
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choice(alphabet) for _ in range(n))

    from app.models.event import Event

    code = gen_code()
    for _ in range(10):
        exists = db.query(Event).filter(Event.Code == code).first()
        if not exists:
            break
        code = gen_code()

    # Parse date if provided
    parsed_date = None
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d") if date else None
    except Exception:
        parsed_date = None

    # Create the event (generate a password and code)
    password = gen_password()
    new_event = Event(
        EventTypeID=event_type_id,
        UserID=getattr(user, "UserID", None),
        Name=name,
        Date=parsed_date,
        Code=code,
        Password=password,
        TermsChecked=True,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # If we prepared a pending CustomEventType, attach the new EventID and persist
    try:
        if 'pending_custom_event_type' in locals() and pending_custom_event_type:
            pending_custom_event_type.EventID = new_event.EventID
            db.add(pending_custom_event_type)
            db.commit()
    except Exception:
        # Don't block event creation if recording custom name fails; log and continue
        evt_id = getattr(new_event, "EventID", None)
        logging.exception("Failed to persist CustomEventType for event %s", evt_id)

    audit.info(
        "events.create.success",
        extra={
            "user_id": getattr(user, "UserID", None),
            "event_id": getattr(new_event, "EventID", None),
            "code": code,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

    return RedirectResponse(url=f"/events/{new_event.EventID}", status_code=303)
