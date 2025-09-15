from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger("billing")


def _reconcile_pending_with_stripe(db: Session, user_id: int) -> None:
    """Check pending purchases for the user against Stripe and mark paid where appropriate.

    This is a best-effort reconciliation used when webhooks may be delayed or not received.
    It is safe to call frequently and will quietly return if Stripe is not configured.
    """
    try:
        from app.core.settings import settings
        from app.models.billing import PaymentLog, Purchase
    except Exception:
        return

    # Don't attempt network calls if Stripe key is not configured
    if not getattr(settings, "STRIPE_SECRET_KEY", None):
        return

    try:
        import stripe  # type: ignore

        stripe.api_key = settings.STRIPE_SECRET_KEY
    except Exception as e:
        logger.debug("Stripe SDK not available for reconciliation: %s", e)
        return

    try:
        pending = (
            db.query(Purchase)
            .filter(Purchase.UserID == int(user_id), Purchase.Status == "pending")
            .all()
        )
    except Exception:
        return

    for p in pending:
        sid = getattr(p, "StripeSessionID", None)
        if not sid:
            continue
        try:
            sess = stripe.checkout.Session.retrieve(sid)
            # session.payment_status can be 'paid' when completed
            payment_status = None
            try:
                if isinstance(sess, dict):
                    payment_status = sess.get("payment_status")
                else:
                    payment_status = getattr(sess, "payment_status", None)
            except Exception:
                payment_status = None
            # Payment intent id may be available on the session
            pi = None
            try:
                if isinstance(sess, dict):
                    pi = sess.get("payment_intent")
                else:
                    pi = getattr(sess, "payment_intent", None)
            except Exception:
                pi = None

            if (payment_status and str(payment_status).lower() == "paid") or pi:
                try:
                    setattr(p, "Status", "paid")
                    if pi:
                        setattr(p, "StripePaymentIntentID", str(pi))
                    db.commit()
                except Exception:
                    db.rollback()
                    continue

                # Log reconciliation event
                try:
                    uid_val = getattr(p, "UserID", None)
                    db.add(
                        PaymentLog(
                            UserID=int(uid_val) if (uid_val is not None) else None,
                            EventType="reconcile_paid",
                            StripeEventID=None,
                            Payload=json.dumps({"session": sid, "payment_intent": pi}),
                        )
                    )
                    db.commit()
                except Exception:
                    db.rollback()
        except Exception as e:
            # Keep going on failures; record a small payment log for debugging
            try:
                db.add(
                    PaymentLog(
                        UserID=int(user_id) if (user_id is not None) else None,
                        EventType="reconcile_error",
                        StripeEventID=None,
                        Payload=str(sid or ""),
                        ErrorMessage=str(e),
                    )
                )
                db.commit()
            except Exception:
                db.rollback()


def get_active_plan(db: Session, user_id: int) -> Tuple[Optional[Any], Dict[str, Any]]:
    """Return (plan_row, features_dict) for the user's most recent paid plan.

    If none, returns (None, {}). Features is JSON-parsed, defaults to {}.
    """
    from app.models.billing import Purchase
    from app.models.event_plan import EventPlan

    # First, try a best-effort reconciliation of pending purchases with Stripe
    try:
        _reconcile_pending_with_stripe(db, user_id)
    except Exception:
        # Don't let reconciliation failures block plan lookup
        pass

    plan = None
    features: Dict[str, Any] = {}
    try:
        latest = (
            db.query(Purchase, EventPlan)
            .join(EventPlan, Purchase.PlanID == EventPlan.PlanID)
            .filter(
                Purchase.UserID == user_id, Purchase.Status == "paid", EventPlan.IsActive
            )
            .order_by(Purchase.CreatedAt.desc())
            .first()
        )
        if latest:
            plan = latest[1]
            raw = getattr(plan, "Features", None) or "{}"
            try:
                features = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception:
                features = {}
    except Exception:
        plan = None
        features = {}
    return plan, features


def provision_user_plan(db: Session, purchase) -> None:
    """Placeholder: perform any provisioning side-effects when a purchase is marked paid.

    Current implementation is intentionally lightweight: it looks up the plan and
    logs the intent to provision. Concrete actions (update quotas, create
    subscriptions, set flags on the Users table) can be added here later.
    This function is safe to call from webhook handlers and should not raise.
    """
    try:
        from app.models.event_plan import EventPlan

        plan = None
        try:
            plan = db.query(EventPlan).filter(
                EventPlan.PlanID == getattr(purchase, "PlanID", None)
            ).first()
        except Exception:
            plan = None

        logger.info(
            "provision_user_plan: user=%s plan=%s purchase=%s",
            getattr(purchase, "UserID", None),
            getattr(plan, "Code", None) if plan else None,
            getattr(purchase, "PurchaseID", None),
        )
        # NOTE: provisioning is intentionally a no-op for now.
        # FUTURE: update user quotas, create subscription rows, and persist provisioning events.
        try:
            from app.models.billing import ProvisionLog

            db.add(
                ProvisionLog(
                    UserID=getattr(purchase, "UserID", None),
                    PurchaseID=getattr(purchase, "PurchaseID", None),
                    Details="provision-scheduled",
                )
            )
            db.commit()
        except Exception:
            db.rollback()
    except Exception as e:
        logger.exception("provision_user_plan failed: %s", e)
