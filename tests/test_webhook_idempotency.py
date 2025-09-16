
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.usefixtures("db_session")
def test_webhook_idempotent(db_session):
    client = TestClient(app)
    db = db_session

    # Create a plan and a pending purchase tied to a fake session id
    from app.models.billing import PaymentLog, Purchase
    from app.models.event_plan import EventPlan

    # Reuse an existing 'single' plan if present (test DB may be pre-seeded), otherwise create it
    plan = db.query(EventPlan).filter(EventPlan.Code == "single").first()
    if not plan:
        plan = EventPlan(
            Code="single",
            Name="Basic",
            PriceCents=2500,
            Currency="GBP",
            IsActive=True,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

    # Ensure a user exists to satisfy foreign key constraints; create a lightweight
    # user in the test DB
    from app.models.user import User

    user = db.query(User).first()
    if not user:
        user = User(
            FirstName='T',
            LastName='User',
            Email='webhook@example.test',
            HashedPassword='x',
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    purchase = Purchase(
        UserID=user.UserID,
        PlanID=plan.PlanID,
        Amount=25.00,
        Currency="GBP",
        StripeSessionID="sess_test_123",
        Status="pending",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    # Build a fake Stripe event payload
    event = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "sess_test_123",
                "payment_intent": "pi_test_123",
            }
        },
    }

    headers = {"content-type": "application/json"}

    # Post the first webhook
    r1 = client.post("/stripe/webhook", json=event, headers=headers)
    assert r1.status_code == 200

    # After first, purchase should be paid
    p1 = db.query(Purchase).filter(Purchase.PurchaseID == purchase.PurchaseID).first()
    assert p1.Status == "paid"
    assert p1.StripePaymentIntentID == "pi_test_123"

    # There should be a PaymentLog entry with StripeEventID evt_test_123
    logs = db.query(PaymentLog).filter(PaymentLog.StripeEventID == "evt_test_123").all()
    assert len(logs) >= 1

    # Post the same webhook again (Stripe retry)
    r2 = client.post("/stripe/webhook", json=event, headers=headers)
    assert r2.status_code == 200

    # Ensure no duplicate handling: PaymentLog with the same StripeEventID
    # should remain unchanged (no duplicate created)
    logs2 = (
        db.query(PaymentLog)
        .filter(PaymentLog.StripeEventID == "evt_test_123")
        .all()
    )
    assert len(logs2) == len(logs)
