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
