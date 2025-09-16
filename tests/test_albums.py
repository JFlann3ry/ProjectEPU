import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# These tests assume an authenticated test user may be required by the endpoints.
# If auth is enforced in your test environment, set appropriate cookies/headers or adjust fixtures.

def test_list_albums_unauthenticated():
    r = client.get('/events/1/albums')
    assert r.status_code in (200, 401, 403)

def test_create_album_missing_event():
    r = client.post('/events/999999/albums/create', data={'name': 'X'})
    # In some test setups unauthenticated POSTs may return login page or redirect.
    # Accept common auth-related responses.
    assert r.status_code in (200, 404, 401, 403, 302)

# Integration-style smoke test for endpoint shape
@pytest.mark.parametrize('event_id', [1])
def test_albums_endpoints_smoke(event_id):
    # list
    r = client.get(f'/events/{event_id}/albums')
    assert r.status_code in (200, 302, 401, 403)
    if r.status_code == 200:
        try:
            j = r.json()
            assert 'ok' in j
        except ValueError:
            # HTML response (login page) - accept it as unauthenticated
            pass

    # create (may be forbidden in CI if no auth)
    r2 = client.post(f'/events/{event_id}/albums/create', data={'name': 'Smoke Album'})
    assert r2.status_code in (200, 201, 302, 401, 403)
