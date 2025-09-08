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
    from app.models.billing import Purchase
    from app.models.event import Event
    from app.models.event_plan import EventPlan

    plan_code = None
    try:
        latest = (
            db.query(Purchase, EventPlan)
            .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
            .filter(
                Purchase.UserID == getattr(user, "UserID", None),
                Purchase.Status == "paid",
                EventPlan.IsActive,
            )
            .order_by(Purchase.CreatedAt.desc())
            .first()
        )
        if latest:
            plan_code = (latest[1].Code or "").lower()
    except Exception:
        plan_code = None

    if not plan_code:
    # No active package -> go to billing/pricing
        return RedirectResponse("/billing", status_code=303)
    if plan_code == "single":
        count = db.query(Event).filter(Event.UserID == getattr(user, "UserID", None)).count()
        if count >= 1:
            return templates.TemplateResponse(
                request,
                "create_event.html",
                context={
                    "error": "Your plan allows only 1 event. Please upgrade to create more.",
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
    # Enforce plan again on POST (same logic as GET)
    from app.models.billing import Purchase
    from app.models.event import Event
    from app.models.event_plan import EventPlan

    plan_code = None
    try:
        latest = (
            db.query(Purchase, EventPlan)
            .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
            .filter(
                Purchase.UserID == getattr(user, "UserID", None),
                Purchase.Status == "paid",
                EventPlan.IsActive,
            )
            .order_by(Purchase.CreatedAt.desc())
            .first()
        )
        if latest:
            plan_code = (latest[1].Code or "").lower()
    except Exception:
        plan_code = None
    if not plan_code:
        return RedirectResponse("/billing", status_code=303)
    if plan_code == "single":
        count = db.query(Event).filter(Event.UserID == getattr(user, "UserID", None)).count()
        if count >= 1:
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
    except Exception:
        event_type_id = None

    # Generate a unique short event code
    import random
    import string

    def gen_code(n: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
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

    # Create the event (Password required by schema; store empty for now)
    new_event = Event(
        EventTypeID=event_type_id,
        UserID=getattr(user, "UserID", None),
        Name=name,
        Date=parsed_date,
        Code=code,
        Password="",
        TermsChecked=True,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

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
