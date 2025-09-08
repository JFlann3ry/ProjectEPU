from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_signup_weak_password_shows_policy():
    r = client.post(
        "/auth/signup",
        data={
            "first_name": "A",
            "last_name": "B",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert r.status_code == 200
    assert "Password requirements not met" in r.text


def test_signup_duplicate_email(monkeypatch):
    # Force create_user to return None simulating uniqueness violation
    from app.services import auth as auth_service

    def fake_create_user(db, first_name, last_name, email, password):
        return None

    monkeypatch.setattr(auth_service, "create_user", fake_create_user)

    r = client.post(
        "/auth/signup",
        data={
            "first_name": "A",
            "last_name": "B",
            "email": "exists@example.com",
            "password": "Str0ng!Pass",
        },
    )
    assert r.status_code == 200
    assert "Email already registered" in r.text
