import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.templates import templates
from app.models.billing import PaymentLog, Purchase
from app.models.event_plan import EventPlan
from app.services.auth import require_admin
from app.services.email_utils import send_billing_email
from db import get_db

router = APIRouter()
audit = logging.getLogger("audit")


@router.post("/admin/seed-plans", response_class=PlainTextResponse)
async def admin_seed_plans(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    # Import and run seeder logic in-process
    from app.db_seed_plans import PLANS, upsert_plan

    for spec in PLANS:
        upsert_plan(db, spec)
    return PlainTextResponse(
        "Seeded/updated plans: " + ", ".join([p.get("Code", "") for p in PLANS])
    )


@router.get("/admin/plans", response_class=PlainTextResponse)
async def admin_list_plans(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    rows = db.query(EventPlan).order_by(EventPlan.PriceCents.asc()).all()
    lines = ["Plans:"]
    for p in rows:
        lines.append(
            f"#{getattr(p,'PlanID')} code={getattr(p,'Code')} "
            f"name={getattr(p,'Name')} price={getattr(p,'PriceCents')} "
            f"{getattr(p,'Currency')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.post("/admin/refund")
async def admin_refund(
    request: Request,
    purchase_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    # Find purchase
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    # Load Stripe
    try:
        import stripe  # type: ignore

        stripe.api_key = settings.STRIPE_SECRET_KEY
    except Exception:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    pi = getattr(p, "StripePaymentIntentID", None)
    if not pi:
        raise HTTPException(status_code=400, detail="No payment intent on purchase")
    try:
        stripe.Refund.create(payment_intent=pi, reason="requested_by_customer")  # type: ignore
        setattr(p, "Status", "refunded")
        db.commit()
        # Notify user via email (best-effort)
        try:
            from app.models.user import User

            u = db.query(User).filter(User.UserID == getattr(p, "UserID", None)).first()
            to_email = getattr(u, "Email", None) if u else None
            if to_email:
                msg = (
                    "Your purchase #"
                    + str(getattr(p, "PurchaseID"))
                    + " has been refunded. "
                    + (("Reason: " + reason) if reason else "")
                )
                await send_billing_email(
                    to_email,
                    subject="Refund processed – EPU",
                    body=msg,
                )
        except Exception:
            pass
        audit.info(
            "billing.refund.success",
            extra={
                "purchase_id": int(getattr(p, "PurchaseID")),
                "admin_id": int(getattr(user, "UserID")),
            },
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        audit.error(
            "billing.refund.error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Refund failed")


@router.post("/admin/cancel")
async def admin_cancel(
    request: Request,
    purchase_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    p = db.query(Purchase).filter(Purchase.PurchaseID == int(purchase_id)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    try:
        setattr(p, "Status", "canceled")
        db.commit()
        try:
            from app.models.user import User

            u = db.query(User).filter(User.UserID == getattr(p, "UserID", None)).first()
            to_email = getattr(u, "Email", None) if u else None
            if to_email:
                msg = (
                    "Your purchase #"
                    + str(getattr(p, "PurchaseID"))
                    + " has been canceled. "
                    + (("Reason: " + reason) if reason else "")
                )
                await send_billing_email(
                    to_email,
                    subject="Subscription canceled – EPU",
                    body=msg,
                )
        except Exception:
            pass
        audit.info(
            "billing.cancel.success",
            extra={
                "purchase_id": int(getattr(p, "PurchaseID")),
                "admin_id": int(getattr(user, "UserID")),
            },
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        audit.error(
            "billing.cancel.error",
            extra={"purchase_id": int(getattr(p, "PurchaseID")), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Cancel failed")


@router.get("/admin/billing", response_class=PlainTextResponse)
async def admin_billing_list(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    rows = (
        db.query(Purchase, EventPlan)
        .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
        .order_by(Purchase.CreatedAt.desc())
        .limit(200)
        .all()
    )
    lines = ["Purchases (latest 200):"]
    for p, plan in rows:
        lines.append(
            f"#{getattr(p, 'PurchaseID')} user={getattr(p, 'UserID')} "
            f"plan={getattr(plan, 'Code')} status={getattr(p, 'Status')} "
            f"amount={getattr(p, 'Amount')} {getattr(p, 'Currency')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.get("/admin/payment-logs", response_class=PlainTextResponse)
async def admin_payment_logs(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    logs = db.query(PaymentLog).order_by(PaymentLog.CreatedAt.desc()).limit(200).all()
    lines = ["Payment Logs (latest 200):"]
    for log in logs:
        lines.append(
            f"#{getattr(log, 'LogID')} type={getattr(log, 'EventType')} "
            f"err={getattr(log, 'ErrorMessage')}"
        )
    return PlainTextResponse("\n".join(lines))


@router.get("/admin/billing/manage", response_class=HTMLResponse)
async def admin_billing_manage(
    request: Request, db: Session = Depends(get_db), user=Depends(require_admin)
):
    from app.models.user import User

    rows = (
        db.query(Purchase, EventPlan, User)
        .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
        .join(User, Purchase.UserID == User.UserID)
        .order_by(Purchase.CreatedAt.desc())
        .limit(200)
        .all()
    )
    items = []
    for p, plan, u in rows:
        items.append(
            {
                "purchase_id": int(getattr(p, "PurchaseID")),
                "user_email": str(getattr(u, "Email") or ""),
                "plan": str(getattr(plan, "Code")),
                "amount": str(getattr(p, "Amount")) + " " + str(getattr(p, "Currency")),
                "status": str(getattr(p, "Status")),
                "created": getattr(p, "CreatedAt"),
            }
        )
    return templates.TemplateResponse(request, "admin_billing.html", context={"items": items})
