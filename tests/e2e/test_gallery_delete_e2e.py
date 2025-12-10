"""E2E Playwright test for gallery delete.

Note: Suppress import-sort noise in some environments where hidden chars can
confuse sorting.
"""

# ruff: noqa: I001

from datetime import datetime, timezone
import os
import time

import pytest
from playwright.sync_api import sync_playwright

from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session

# Requires Playwright and a dev server on http://localhost:4200.
# It does a minimal check: set the session cookie, open /gallery, delete one tile,
# verify tile removal and DB soft-delete fields.

@pytest.mark.skipif(os.getenv('E2E_PLAYWRIGHT') != '1', reason='Playwright E2E disabled')
def test_e2e_gallery_delete_updates_db_and_ui(db_session):

    # Create user/event/files
    u = db_session.query(User).filter(User.Email == 'e2e-delete@example.test').first()
    if not u:
        u = User(
            FirstName='E2E', LastName='User', Email='e2e-delete@example.test',
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(UserID=u.UserID, Name='E2E Delete', Code='E2EDEL', Password='pw', TermsChecked=True)
    db_session.add(ev)
    db_session.flush()

    f = FileMetadata(EventID=ev.EventID, FileName='e2e.jpg', FileType='image/jpeg', FileSize=10)
    db_session.add(f)
    db_session.flush()
    fid = int(getattr(f, 'FileMetadataID'))

    # Create a server session (stores in DB)
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))

    # Use Playwright to open the page and perform delete
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        # Set the session cookie via document.cookie in the page context before navigation.
        # This avoids BrowserContext.add_cookies quirks on some environments. If evaluate
        # isn't available yet, fall back to context.add_cookies.
        try:
            try:
                cookie_js = (
                    f"document.cookie = 'session_id={str(sess.SessionID)}; path=/; SameSite=Lax';"
                )
                page.evaluate(cookie_js)
            except Exception:
                ctx.add_cookies([{'name': 'session_id', 'value': str(sess.SessionID), 'url': 'http://localhost:4200'}])
            # Small pause to allow cookie to be applied
            page.wait_for_timeout(200)
            page.goto('http://localhost:4200/gallery', wait_until='domcontentloaded', timeout=60000)
        except Exception:
            # Capture page snapshot and screenshot for debugging
            try:
                content = page.content()
                print('\n--- PAGE CONTENT START ---')
                print(content[:4000])
                print('\n--- PAGE CONTENT END ---')
            except Exception as _err:
                print('failed to read page.content after goto failure', _err)
            try:
                path = 'tests/e2e/_debug_screenshot.png'
                page.screenshot(path=path)
                print('wrote screenshot to', path)
            except Exception as _err:
                print('failed to write screenshot', _err)
            raise

        # Wait for the gallery to load and find our checkbox
        page.wait_for_selector(f'.select-chk[data-id="{fid}"]', timeout=5000)
        # Click the checkbox and click delete
        page.click(f'.select-chk[data-id="{fid}"]')
        page.click('#bb-delete')
        # Wait for modal, then confirm
        page.wait_for_selector('#delete-confirm', timeout=2000)
        page.click('#del-confirm')

        # Wait briefly for fetch to complete and UI to update
        time.sleep(1.0)

        # The tile should be removed from the DOM
        tiles = page.query_selector_all(f'.select-chk[data-id="{fid}"]')
        assert len(tiles) == 0

        ctx.close()
        browser.close()

    # Refresh DB object and assert Deleted/DeletedAt
    db_session.refresh(f)
    assert getattr(f, 'Deleted', False) is True
    da = getattr(f, 'DeletedAt', None)
    assert da is not None
    if da.tzinfo is None:
        da = da.replace(tzinfo=timezone.utc)
    assert (datetime.now(timezone.utc) - da).total_seconds() < 60
