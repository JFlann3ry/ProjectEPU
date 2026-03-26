import sys

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.usefixtures("db_session")
def test_webhook_rejects_malformed_json_and_logs(db_session):
    client = TestClient(app)

    headers = {"content-type": "application/json"}
    response = client.post("/stripe/webhook", content=b"{bad-json", headers=headers)

    assert response.status_code == 400
    assert response.text == "invalid"

    from app.models.billing import PaymentLog

    log = (
        db_session.query(PaymentLog)
        .filter(PaymentLog.EventType == "webhook_error")
        .order_by(PaymentLog.LogID.desc())
        .first()
    )
    assert log is not None
    assert "bad-json" in (log.Payload or "")


@pytest.mark.usefixtures("db_session")
def test_webhook_rejects_invalid_signature_and_logs(db_session, monkeypatch):
    client = TestClient(app)

    class FakeStripe:
        api_key = None

        class error:
            class SignatureVerificationError(Exception):
                pass

            class StripeError(Exception):
                pass

        class Webhook:
            @staticmethod
            def construct_event(payload, sig_header, secret):
                raise FakeStripe.error.SignatureVerificationError("invalid signature")

    monkeypatch.setitem(sys.modules, "stripe", FakeStripe)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    headers = {
        "content-type": "application/json",
        "stripe-signature": "t=1,v1=fake",
    }
    response = client.post("/stripe/webhook", content=b"{}", headers=headers)

    assert response.status_code == 400
    assert response.text == "invalid"

    from app.models.billing import PaymentLog

    log = (
        db_session.query(PaymentLog)
        .filter(PaymentLog.EventType == "webhook_error")
        .order_by(PaymentLog.LogID.desc())
        .first()
    )
    assert log is not None
    assert "invalid signature" in (log.ErrorMessage or "")


@pytest.mark.usefixtures("db_session")
def test_webhook_handles_missing_object_fields_without_error(db_session):
    client = TestClient(app)

    event = {
        "id": "evt_missing_fields",
        "type": "checkout.session.completed",
        "data": {"object": {}},
    }

    response = client.post(
        "/stripe/webhook",
        json=event,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.text == "ok"

    from app.models.billing import PaymentLog

    processed = (
        db_session.query(PaymentLog)
        .filter(PaymentLog.StripeEventID == "evt_missing_fields")
        .order_by(PaymentLog.LogID.desc())
        .first()
    )
    assert processed is not None
