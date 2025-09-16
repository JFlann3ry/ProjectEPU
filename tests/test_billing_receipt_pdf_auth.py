import datetime as dt
from types import SimpleNamespace

from main import app


def test_pdf_receipt_authenticated_200(monkeypatch, client):
    # Monkeypatch auth to return a fake user
    from app.api import billing

    fake_user = SimpleNamespace(UserID=1, Email="u@example.com")
    monkeypatch.setattr(billing, "get_current_user", lambda request, db: fake_user, raising=True)

    class FakeP:
        def __init__(self):
            self.PurchaseID = 123
            self.UserID = 1
            self.Status = "paid"
            self.Amount = 12.34
            self.Currency = "GBP"
            self.CreatedAt = dt.datetime(2024, 5, 1, 10, 0, 0)
            self.StripeSessionID = "sess"
            self.PlanID = 9

    class FakePlan:
        def __init__(self):
            self.Name = "Test Plan"
            self.Code = "TEST"
            self.Description = "Test Desc"

    # Replace DB access by monkeypatching the functions that call db.query to return our fake rows.
    def fake_query_purchase(*args, **kwargs):
        return SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: FakeP()))

    def fake_query_plan(*args, **kwargs):
        return SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: FakePlan()))

    # Override get_db dependency to return our fake DB
    class DB:
        def query(self, model):
            name = getattr(model, "__name__", str(model))
            if name.endswith("Purchase"):
                return fake_query_purchase()
            return fake_query_plan()

    from db import get_db as real_get_db

    def override_get_db():  # noqa: D401
        return DB()

    app.dependency_overrides[real_get_db] = override_get_db

    r = client.get("/billing/purchase/123/receipt.pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.headers.get("content-disposition", "").lower().startswith("attachment;")
    # Cleanup overrides
    app.dependency_overrides.clear()
