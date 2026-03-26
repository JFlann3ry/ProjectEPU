from app.services.auth import require_admin
from main import app


def test_billing_admin_routes_still_registered(client):
    def fake_admin():
        return object()

    app.dependency_overrides[require_admin] = fake_admin
    try:
        plans = client.get("/admin/plans")
        logs = client.get("/admin/payment-logs")

        assert plans.status_code == 200
        assert "Plans:" in plans.text
        assert logs.status_code == 200
        assert "Payment Logs" in logs.text
    finally:
        app.dependency_overrides.clear()
