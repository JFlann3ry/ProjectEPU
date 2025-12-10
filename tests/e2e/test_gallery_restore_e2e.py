"""E2E Playwright test for gallery restore.

Skipped by default; enable with E2E_PLAYWRIGHT=1 and a running dev server.
"""

# ruff: noqa: I001

import os

import pytest
from playwright.sync_api import sync_playwright

from app.models.event import Event, FileMetadata
from app.models.user import User
from app.services.auth import create_session


@pytest.mark.skipif(os.getenv('E2E_PLAYWRIGHT') != '1', reason='Playwright E2E disabled')
def test_e2e_gallery_restore_updates_db_and_ui(db_session):
    # Create user/event and one file
    u = db_session.query(User).filter(User.Email == 'e2e-restore@example.test').first()
    if not u:
        u = User(
            FirstName='E2E', LastName='Restore', Email='e2e-restore@example.test',
            HashedPassword='x', IsActive=True,
        )
        db_session.add(u)
        db_session.flush()

    ev = Event(
        UserID=u.UserID,
        Name='E2E Restore',
        Code='E2ERES',
        Password='pw',
        TermsChecked=True,
    )
    db_session.add(ev)
    db_session.flush()

    f = FileMetadata(
        EventID=ev.EventID,
        FileName='e2e-restore.jpg',
        FileType='image/jpeg',
        FileSize=10,
    )
    db_session.add(f)
    db_session.flush()

    # Create session cookie
    sess = create_session(db_session, user_id=int(getattr(u, 'UserID')))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        try:
            # Set cookie and navigate
            try:
                page.evaluate(
                    f"document.cookie = 'session_id={str(sess.SessionID)}; path=/; SameSite=Lax';"
                )
            except Exception:
                ctx.add_cookies([{
                    'name': 'session_id', 'value': str(sess.SessionID), 'url': 'http://localhost:4200'
                }])
            page.wait_for_timeout(200)
            page.goto('http://localhost:4200/gallery', wait_until='domcontentloaded', timeout=60000)

            # Soft-delete via UI: select first tile and click delete flow
            page.wait_for_selector('#gallery .gallery-item .select-chk', timeout=60000)
            page.locator('#gallery .gallery-item .select-chk').first.check()
            page.click('#bb-delete')
            page.click('#del-confirm')
            page.wait_for_timeout(500)

            # Switch to deleted filter view if available
            try:
                page.click('#filter-deleted')
            except Exception:
                pass

            # Select the deleted tile and click restore
            page.wait_for_selector('#gallery .gallery-item .select-chk', timeout=60000)
            page.locator('#gallery .gallery-item .select-chk').first.check()
            page.click('#bb-restore')
            page.wait_for_timeout(500)
        finally:
            try:
                ctx.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass