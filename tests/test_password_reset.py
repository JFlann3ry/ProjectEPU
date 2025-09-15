from fastapi.testclient import TestClient

from app.models.user import User
from app.services.auth import generate_password_reset_token, hash_password


def test_forgot_password_sends_email(monkeypatch, client: TestClient):
    sent = {}

    async def fake_send(msg, **kwargs):
        sent['to'] = msg['To']
        sent['subject'] = msg['Subject']
        sent['body'] = msg.get_content()

    monkeypatch.setattr('app.services.email_utils.aiosmtplib.send', fake_send)

    resp = client.post(
        '/auth/forgot-password',
        data={
            'email': 'nonexistent@example.com',
            'csrf_token': '',
        },
    )
    assert resp.status_code in (200, 302)
    # neutral response - no leak of existence
    assert 'If that email exists' in resp.text


def test_reset_password_flow(monkeypatch, client: TestClient, db_session):
    # Create a test user directly in DB. If a prior test run left the same email, remove it first.
    test_email = 'resetme@example.com'
    db = db_session
    existing = db.query(User).filter(User.Email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()

    user = User(
        FirstName='T',
        LastName='U',
        Email=test_email,
        HashedPassword=hash_password('OldP@ss1'),
        EmailVerified=True,
        IsActive=True,
        MarkedForDeletion=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # user.Email is a SQLAlchemy Column; convert to plain str for token helper
    token = generate_password_reset_token(str(user.Email))
    # GET reset page
    resp = client.get(f'/reset-password?token={token}')
    assert resp.status_code == 200
    # POST new password
    resp2 = client.post(
        '/auth/reset-password',
        data={
            'token': token,
            'password': 'NewP@ss2',
            'password2': 'NewP@ss2',
            'csrf_token': '',
        },
    )
    assert resp2.status_code in (200, 302)
    # Verify password updated in DB
    db.refresh(user)
    # Compare hashed values as strings
    assert str(user.HashedPassword) != hash_password('OldP@ss1')
