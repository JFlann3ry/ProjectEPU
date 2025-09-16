import pytest

from app.models.email_change import EmailChangeRequest
from app.models.user import User


@pytest.mark.usefixtures("client", "db_session")
def test_email_change_confirm_and_reverse(client, db_session):
    # Create a user record
    # Ensure user model is imported so its table is present in metadata
    import app.models.user  # noqa: F401

    u = User(Email="old@example.com", HashedPassword="x", FirstName="Test", LastName="User")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # Create a token for new email
    from app.services.auth import generate_email_token
    # If using sqlite in tests, ensure all tables are created in this in-memory DB
    try:
        from app.models.user import Base as UserBase

        if getattr(db_session.bind.dialect, "name", "") == "sqlite":
            # Remove schema names from Table objects so SQLite can create them
            tbls = list(UserBase.metadata.tables.values())
            for tbl in tbls:
                try:
                    tbl.schema = None
                except Exception:
                    continue
            UserBase.metadata.create_all(bind=db_session.bind)
    except Exception:
        pass

    payload = f"{u.UserID}|new@example.com"
    token = generate_email_token(payload)

    # Create EmailChangeRequest directly
    # Ensure EmailChangeRequests table exists in sqlite test DB
    try:
        tbl = EmailChangeRequest.__table__
        try:
            tbl.schema = None
        except Exception:
            pass
        tbl.create(bind=db_session.bind, checkfirst=True)
    except Exception:
        pass
    req = EmailChangeRequest(
        UserID=u.UserID,
        OldEmail=u.Email,
        NewEmail="new@example.com",
        Token=token,
        IsActive=True,
    )
    db_session.add(req)
    db_session.commit()

    # Call confirm endpoint
    resp = client.get(f"/profile/email/confirm?token={token}")
    assert resp.status_code == 200

    # Reload user from DB and assert email updated
    u_db = db_session.query(User).filter(User.UserID == u.UserID).first()
    assert u_db.Email == "new@example.com"

    # Create another change and reverse it before confirmation
    payload2 = f"{u.UserID}|other@example.com"
    token2 = generate_email_token(payload2)
    req2 = EmailChangeRequest(
        UserID=u.UserID,
        OldEmail=u_db.Email,
        NewEmail="other@example.com",
        Token=token2,
        IsActive=True,
    )
    db_session.add(req2)
    db_session.commit()

    resp2 = client.get(f"/profile/email/reverse?token={token2}")
    assert resp2.status_code == 200

    u_db2 = db_session.query(User).filter(User.UserID == u.UserID).first()
    # Email should remain as previously confirmed
    assert u_db2.Email == "new@example.com"
