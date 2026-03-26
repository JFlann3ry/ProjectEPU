import json

from app.services.auth import create_session


def _as_admin(client, db_session):
    from app.models.user import User

    admin = db_session.query(User).filter(User.Email == "admin-audit@example.test").first()
    if not admin:
        admin = User(
            FirstName="Admin",
            LastName="Audit",
            Email="admin-audit@example.test",
            HashedPassword="x",
            IsActive=True,
            IsAdmin=True,
        )
        db_session.add(admin)
        db_session.flush()
    else:
        setattr(admin, "IsAdmin", True)
        db_session.flush()

    sess = create_session(db_session, user_id=int(getattr(admin, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))


def test_admin_audit_export_type_hint_filters_without_full_serialization(
    client, db_session, tmp_path, monkeypatch
):
    _as_admin(client, db_session)

    monkeypatch.chdir(tmp_path)
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "app.log"

    rows = [
        {
            "time": "2026-03-24T10:00:00",
            "level": "INFO",
            "logger": "audit",
            "message": "user action",
            "event_type": "guest_delete",
        },
        {
            "time": "2026-03-24T10:00:01",
            "level": "INFO",
            "logger": "audit",
            "message": "other event",
            "event_type": "guest_restore",
        },
    ]
    with log_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    r = client.get("/admin/audit-logs/export", params={"type_hint": "guest_delete"})
    assert r.status_code == 200

    lines = [line for line in r.text.strip().splitlines() if line.strip()]
    assert len(lines) == 1
    assert "guest_delete" in lines[0]


def test_admin_audit_export_rejects_overlong_filters(client, db_session):
    _as_admin(client, db_session)

    overlong = "x" * 513
    r = client.get("/admin/audit-logs/export", params={"contains": overlong})

    assert r.status_code == 422
    assert "too long" in r.text.lower()
