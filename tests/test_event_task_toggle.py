import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.usefixtures("db_session")
def test_toggle_task_happy_path(db_session):
    client = TestClient(app)
    db = db_session

    # Create a user and event to act on
    from app.models.event import Event
    from app.models.user import User

    u = db.query(User).filter(User.Email == "task_test@example.com").first()
    if not u:
        u = User(
            FirstName="Task",
            LastName="Tester",
            Email="task_test@example.com",
            HashedPassword="x",
            IsActive=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)

    e = db.query(Event).filter(Event.Code == "TASK1").first()
    if not e:
        e = Event(
            EventTypeID=None,
            UserID=u.UserID,
            Name="Task Event",
            Code="TASK1",
            Password="pw",
            TermsChecked=True,
        )
        db.add(e)
        db.commit()
        db.refresh(e)

    # Create session cookie for user
    from app.services.auth import create_session

    sess = create_session(db, user_id=int(u.UserID))
    client.cookies.set('session_id', str(sess.SessionID))

    # Toggle the task (should create)
    e_id_val = int(getattr(e, 'EventID'))
    res = client.post(
        '/events/task/toggle',
        data={
            'event_id': str(e_id_val),
            'task_key': 'purchase_extras',
        },
    )
    assert res.status_code == 200
    j = res.json()
    assert j.get('ok') is True
    assert j.get('done') in (True, False)

    # Missing params
    r2 = client.post('/events/task/toggle', data={'task_key': 'purchase_extras'})
    assert r2.status_code == 400

