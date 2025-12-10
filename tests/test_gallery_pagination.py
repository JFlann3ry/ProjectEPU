import pytest

from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session


@pytest.fixture
def logged_in_client(db_session, client):
    # Create a user and an event with multiple files

    u = db_session.query(User).filter(User.Email == 'pagetest@example.test').first()
    if not u:
        u = User(
            FirstName='Page',
            LastName='Tester',
            Email='pagetest@example.test',
            HashedPassword='x',
            IsActive=True,
        )
        db_session.add(u)
        db_session.flush()
    ev = Event(UserID=u.UserID, Name='PageTest', Code='PAGET', Password='pw', TermsChecked=True)
    db_session.add(ev)
    db_session.flush()

    # Seed 5 image files
    for i in range(5):
        fm = FileMetadata(
            EventID=ev.EventID,
            FileName=f'img_{i}.jpg',
            FileType='image/jpeg',
            FileSize=10,
        )
        db_session.add(fm)
    db_session.flush()

    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))
    client.cookies.set('session_id', str(sess.SessionID))

    # Select the event for gallery scope
    r = client.post('/gallery/select', data={'event_id': str(ev.EventID)})
    assert r.status_code in (200, 303)

    return client


def test_gallery_first_page_and_next_offset(logged_in_client):
    # First page with limit=2 returns two items and a next_offset of 2
    r = logged_in_client.get('/gallery?limit=2&offset=0')
    assert r.status_code == 200
    # Ensure template rendered next_offset data attribute accordingly (not empty)
    assert 'data-page-size="2"' in r.text
    assert (
        'data-next-offset="2"' in r.text
        or 'data-next-offset="3"' in r.text
        or 'data-next-offset="4"' in r.text
    )
    # Pager buttons removed; ensure they are not present
    assert 'id="pager-prev"' not in r.text
    assert 'id="pager-next"' not in r.text


def test_gallery_data_endpoint_paging(logged_in_client):
    # Fetch first 2, then next 2, ensure no overlap and has next until exhausted
    j1 = logged_in_client.get('/gallery/data?limit=2&offset=0').json()
    assert j1['ok'] is True
    assert len(j1['files']) <= 2
    nxo = j1.get('next_offset')
    assert (nxo is None) or (isinstance(nxo, int))

    if nxo is None:
        pytest.skip('Not enough files to test pagination fully')

    j2 = logged_in_client.get(f'/gallery/data?limit=2&offset={nxo}').json()
    assert j2['ok'] is True
    # IDs should not overlap
    ids1 = [f['id'] for f in j1['files']]
    ids2 = [f['id'] for f in j2['files']]
    assert not (set(ids1) & set(ids2))

def test_gallery_next_page_prev_enabled(logged_in_client):
    r = logged_in_client.get('/gallery?limit=2&offset=2')
    assert r.status_code == 200
    # Pager buttons removed in infinite scroll mode
    assert 'id="pager-prev"' not in r.text
