import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.billing import PaymentLog, Purchase
from app.models.event_plan import EventPlan
from app.services.auth import get_current_user
from app.services.email_utils import send_billing_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


def _compose_receipt_text(p, plan, user_email: str) -> str:
    """Create a plain-text receipt body for download/email."""
    lines = [
        "EPU – Receipt",
        "----------------------------------------",
        f"Receipt #: {getattr(p, 'PurchaseID')}",
        f"Date: {getattr(p, 'CreatedAt')}",
        f"Status: {getattr(p, 'Status')}",
        "",
        "Billed To:",
        f"  {user_email or 'User'}",
        "",
        "Item:",
        f"  Plan: {getattr(plan, 'Name', 'Plan') if plan else 'Plan'}",
        f"  Code: {getattr(plan, 'Code', '') if plan else ''}",
        "",
        "Totals:",
        f"  Amount: {getattr(p, 'Amount')} {getattr(p, 'Currency')}",
        "",
        "Notes:",
        "  This is a receipt for your records. It is not a VAT invoice.",
        "  For questions, contact support via /contact.",
    ]
    return "\n".join(lines)


@router.get("/billing/purchase/{purchase_id}", response_class=HTMLResponse)
async def billing_purchase_details(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Show details for a single purchase with actions to download/email receipt."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")

    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    details = {
        "id": int(getattr(p, "PurchaseID")),
        "status": str(getattr(p, "Status")),
        "amount": str(getattr(p, "Amount")) + " " + str(getattr(p, "Currency")),
        "created": getattr(p, "CreatedAt"),
        "plan_code": str(getattr(plan, "Code", "")) if plan else "",
        "plan_name": str(getattr(plan, "Name", "Plan")) if plan else "Plan",
        "plan_desc": str(getattr(plan, "Description", "") or "") if plan else "",
        "session": str(getattr(p, "StripeSessionID", "") or ""),
    }
    return templates.TemplateResponse(
        request,
        "billing_purchase.html",
        context={
            "purchase": details,
            "sent": 1 if (request.query_params.get("sent") == "1") else 0,
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@router.get("/billing/purchase/{purchase_id}/receipt")
async def billing_purchase_receipt(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Return a downloadable plain-text receipt for the purchase."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()

    user_email = getattr(user, "Email", "")
    body = _compose_receipt_text(p, plan, user_email)
    filename = f"receipt-{getattr(p, 'PurchaseID')}.txt"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/billing/purchase/{purchase_id}/receipt.pdf")
async def billing_purchase_receipt_pdf(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Return a downloadable PDF receipt for the purchase."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()

    try:
        # Lazy import so environments without reportlab can still run most routes
        from app.services.pdf_utils import ReceiptPDF

        pdf = ReceiptPDF()
        created = getattr(p, "CreatedAt")
        if not isinstance(created, datetime):
            created = datetime.now(timezone.utc)
        amount = getattr(p, "Amount", 0)
        currency = str(getattr(p, "Currency", "GBP") or "GBP")
        body = pdf.build(
            receipt_no=int(getattr(p, "PurchaseID")),
            date=created,
            status=str(getattr(p, "Status", "")).lower(),
            billed_to=str(getattr(user, "Email", "") or "User"),
            plan_name=str(getattr(plan, "Name", "Plan")) if plan else "Plan",
            plan_code=str(getattr(plan, "Code", "")) if plan else "",
            description=str(getattr(plan, "Description", "") or "") if plan else "",
            amount=amount,
            currency=currency,
        )
    except Exception:
        # Fallback to text if PDF generation fails
        user_email = getattr(user, "Email", "")
        body_text = _compose_receipt_text(p, plan, user_email)
        filename = f"receipt-{getattr(p, 'PurchaseID')}.txt"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
        }
        return Response(content=body_text, media_type="text/plain; charset=utf-8", headers=headers)

    filename = f"receipt-{getattr(p, 'PurchaseID')}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "no-store",
    }
    return Response(content=body, media_type="application/pdf", headers=headers)


@router.post("/billing/purchase/{purchase_id}/email-receipt")
async def billing_purchase_email_receipt(
    request: Request, purchase_id: int, db: Session = Depends(get_db)
):
    """Email a simple receipt to the user's email address."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p or int(getattr(p, "UserID")) != int(getattr(user, "UserID")):
        raise HTTPException(status_code=404, detail="Purchase not found")
    plan = db.query(EventPlan).filter(EventPlan.PlanID == getattr(p, "PlanID", None)).first()
    to_email = getattr(user, "Email", None)
    if not to_email:
        raise HTTPException(status_code=400, detail="No email on account")

    # Simple rate limit: max 1 receipt email per user per rolling hour
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_count = (
            db.query(PaymentLog)
            .filter(
                PaymentLog.UserID == int(getattr(user, "UserID")),
                PaymentLog.EventType == "email_receipt",
                PaymentLog.CreatedAt >= cutoff,
            )
            .count()
        )
        if recent_count >= 1:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        pass

    body = _compose_receipt_text(p, plan, to_email)
    try:
        await send_billing_email(to_email, subject="Your receipt – EPU", body=body)
        try:
            import json

            payload = json.dumps({"purchase_id": int(getattr(p, "PurchaseID")), "to": to_email})
        except Exception:
            payload = None
        log = PaymentLog(
            UserID=int(getattr(user, "UserID")),
            EventType="email_receipt",
            Payload=payload,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass
    pid = int(getattr(p, "PurchaseID"))
    return RedirectResponse(
        f"/billing/purchase/{pid}?sent=1",
        status_code=303,
    )
