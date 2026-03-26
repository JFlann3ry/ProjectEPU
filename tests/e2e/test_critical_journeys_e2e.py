"""Critical journey E2E smoke coverage.

These tests are Playwright-gated and intended to validate that core journey entry
points render correctly and expose actionable controls.
"""

# ruff: noqa: I001

import os

from playwright.sync_api import sync_playwright
import pytest

from app.models.event import FileMetadata, Event
from app.models.user import User
from app.services.auth import create_session


pytestmark = pytest.mark.skipif(
    os.getenv("E2E_PLAYWRIGHT") != "1",
    reason="Playwright E2E disabled",
)


def _new_page(base_url: str = "http://localhost:4200"):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(base_url=base_url)
    page = ctx.new_page()
    return p, browser, ctx, page


def _close_page(p, browser, ctx):
    try:
        ctx.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
    try:
        p.stop()
    except Exception:
        pass


def _login_cookie(page, ctx, session_id: str):
    try:
        page.evaluate(f"document.cookie = 'session_id={session_id}; path=/; SameSite=Lax';")
    except Exception:
        ctx.add_cookies(
            [{"name": "session_id", "value": session_id, "url": "http://localhost:4200"}]
        )


@pytest.mark.e2e
@pytest.mark.playwright
def test_e2e_signup_and_login_pages_render_forms():
    p, browser, ctx, page = _new_page()
    try:
        page.goto("/signup", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('form[action="/auth/signup"]', timeout=10000)
        assert page.locator("#first_name").count() == 1
        assert page.locator("#email").count() >= 1

        page.goto("/login", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('form[action="/auth/login"]', timeout=10000)
        assert page.locator("#password").count() == 1
    finally:
        _close_page(p, browser, ctx)


@pytest.mark.e2e
@pytest.mark.playwright
def test_e2e_event_create_page_available_for_authenticated_user(db_session):
    user = db_session.query(User).filter(User.Email == "e2e-create@example.test").first()
    if not user:
        user = User(
            FirstName="E2E",
            LastName="Creator",
            Email="e2e-create@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    session = create_session(db_session, user_id=int(getattr(user, "UserID")))

    p, browser, ctx, page = _new_page()
    try:
        _login_cookie(page, ctx, str(session.SessionID))
        page.wait_for_timeout(200)
        page.goto("/events/create", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('form[action="/events/create"]', timeout=10000)
        assert page.locator("#name").count() == 1
        assert page.locator("#terms").count() == 1
    finally:
        _close_page(p, browser, ctx)


@pytest.mark.e2e
@pytest.mark.playwright
def test_e2e_guest_upload_page_accepts_file_selection(db_session, tmp_path):
    host = db_session.query(User).filter(User.Email == "e2e-guest-host@example.test").first()
    if not host:
        host = User(
            FirstName="E2E",
            LastName="Host",
            Email="e2e-guest-host@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(host)
        db_session.flush()

    event = Event(
        UserID=int(getattr(host, "UserID")),
        Name="E2E Guest Upload",
        Code="E2EGUP",
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(event)
    db_session.flush()

    probe = tmp_path / "probe.jpg"
    probe.write_bytes(b"\xff\xd8\xff\xd9")

    p, browser, ctx, page = _new_page()
    try:
        page.goto("/guest/upload/E2EGUP", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#guest-upload-form", timeout=10000)
        page.set_input_files("#file", str(probe))
        page.check("#terms")
        page.wait_for_timeout(250)
        assert page.locator("#upload-btn").is_enabled()
    finally:
        _close_page(p, browser, ctx)


@pytest.mark.e2e
@pytest.mark.playwright
def test_e2e_checkout_entrypoints_visible_on_pricing_page():
    p, browser, ctx, page = _new_page()
    try:
        page.goto("/pricing", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("main", timeout=10000)

        purchase_buttons = page.locator(".js-plan-continue")
        signup_links = page.locator('a[href="/signup"]')
        has_purchase = purchase_buttons.count() > 0
        has_signup = signup_links.count() > 0

        assert has_purchase or has_signup
    finally:
        _close_page(p, browser, ctx)


@pytest.mark.e2e
@pytest.mark.playwright
def test_e2e_gallery_bulk_delete_entrypoint_visible_and_actionable(db_session):
    user = db_session.query(User).filter(User.Email == "e2e-gallery-bulk@example.test").first()
    if not user:
        user = User(
            FirstName="E2E",
            LastName="Gallery",
            Email="e2e-gallery-bulk@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    event = Event(
        UserID=int(getattr(user, "UserID")),
        Name="E2E Bulk Gallery",
        Code="E2EGBK",
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(event)
    db_session.flush()

    file_row = FileMetadata(
        EventID=int(getattr(event, "EventID")),
        FileName="e2e-bulk.jpg",
        FileType="image/jpeg",
        FileSize=10,
        Deleted=False,
    )
    db_session.add(file_row)
    db_session.flush()

    session = create_session(db_session, user_id=int(getattr(user, "UserID")))

    p, browser, ctx, page = _new_page()
    try:
        _login_cookie(page, ctx, str(session.SessionID))
        page.wait_for_timeout(200)
        page.goto("/gallery", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#gallery .select-chk", timeout=10000)

        delete_button = page.locator("#bb-delete")
        assert delete_button.count() == 1
        assert delete_button.is_disabled()

        page.locator("#gallery .select-chk").first.check()
        page.wait_for_timeout(200)
        assert delete_button.is_enabled()

        page.click("#bb-delete")
        page.wait_for_selector("#delete-confirm", timeout=5000)
        modal_display = page.eval_on_selector(
            "#delete-confirm", "el => getComputedStyle(el).display"
        )
        assert modal_display != "none"
    finally:
        _close_page(p, browser, ctx)
