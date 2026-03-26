import uuid
from datetime import datetime, timedelta, timezone

from app.jobs.maintenance import purge_old_payment_logs
from app.models.billing import PaymentLog
from app.models.user import User


def _ensure_user_id(db_session) -> int:
    user = db_session.query(User).filter(User.Email == "paymentlog-purge@example.test").first()
    if not user:
        user = User(
            FirstName="Job",
            LastName="Runner",
            Email="paymentlog-purge@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()
    return int(getattr(user, "UserID"))


def _insert_logs(
    db_session,
    *,
    old_count: int,
    fresh_count: int,
    now_utc: datetime,
    tag: str,
) -> None:
    user_id = _ensure_user_id(db_session)
    for idx in range(old_count):
        db_session.add(
            PaymentLog(
                UserID=user_id,
                EventType=f"{tag}_old_{idx}",
                StripeEventID=None,
                Payload="{}",
                ErrorMessage=None,
                CreatedAt=now_utc - timedelta(days=120),
            )
        )
    for idx in range(fresh_count):
        db_session.add(
            PaymentLog(
                UserID=user_id,
                EventType=f"{tag}_fresh_{idx}",
                StripeEventID=None,
                Payload="{}",
                ErrorMessage=None,
                CreatedAt=now_utc - timedelta(days=1),
            )
        )
    db_session.commit()


def test_paymentlog_purge_batched_deletes_only_old_rows(db_session):
    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    tag = f"plg{uuid.uuid4().hex[:10]}"
    _insert_logs(db_session, old_count=5, fresh_count=2, now_utc=now_utc, tag=tag)

    result = purge_old_payment_logs(
        db_session,
        retention_days=90,
        batch_size=2,
        now_utc=now_utc,
    )

    assert result["deleted_rows"] == 5
    assert result["batches"] == 3

    old_left = (
        db_session.query(PaymentLog).filter(PaymentLog.EventType.like(f"{tag}_old_%")).count()
    )
    assert old_left == 0


def test_paymentlog_purge_records_jobrunlog_on_success(db_session, monkeypatch):
    calls: list[dict] = []

    def _fake_record(*_args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.jobs.maintenance._record_job_run_log", _fake_record)

    now_utc = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
    tag = f"plg{uuid.uuid4().hex[:10]}"
    _insert_logs(db_session, old_count=1, fresh_count=0, now_utc=now_utc, tag=tag)

    purge_old_payment_logs(
        db_session,
        retention_days=90,
        batch_size=10,
        now_utc=now_utc,
    )

    assert calls
    assert calls[-1]["job_name"] == "EPU_PaymentLog_Purge"
    assert calls[-1]["succeeded"] is True
