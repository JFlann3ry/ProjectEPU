from fastapi.testclient import TestClient

from main import app


def test_checkout_requires_auth_and_payload():
    client = TestClient(app)
    # Unauthenticated request should redirect to login (302)
    r = client.post("/create-checkout-session", json={})
    # TestClient may follow redirects; accept either an immediate 302/307 or a response
    # whose history contains a redirect entry.
    if r.status_code not in (302, 307):
        history = getattr(r, "history", []) or []
        assert any(h.status_code in (302, 307) for h in history), "Expected redirect to /login"


def test_checkout_pay_requires_auth():
    client = TestClient(app)
    r = client.get("/billing/purchase/1/pay")
    if r.status_code not in (302, 307):
        history = getattr(r, "history", []) or []
        assert any(h.status_code in (302, 307) for h in history), "Expected redirect to /login"


def test_legacy_plans_redirects_to_pricing():
    client = TestClient(app)
    r = client.get("/plans", follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/pricing" in (r.headers.get("location", "") or "")
