import re
import pytest
from playwright.sync_api import Page

LIVE_CODE = "PLAYHUD"

@pytest.fixture(scope="session")
def ensure_live_event(db_session):
    from app.models.event import Event
    e = Event(
        UserID=1,
        Name="HUD Focus Event",
        Code=LIVE_CODE,
        Password="x",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(e)
    db_session.flush()
    return e

@pytest.mark.playwright
@pytest.mark.e2e
def test_live_hud_tab_order(page: Page, ensure_live_event):
    # Navigate to live slideshow
    page.goto(f"/live/{LIVE_CODE}")

    # Wait for status pill
    page.wait_for_selector("#status")

    # HUD control order we expect (status pill is not focusable)
    expected_order = ["#prev", "#play", "#pause", "#next", "#dec", "#inc", "#fs"]

    # Collect tabbable elements manually by pressing Tab repeatedly and recording active element IDs
    visited = []
    for _ in range(len(expected_order) + 5):  # safety upper bound
        page.keyboard.press("Tab")
        active_id = page.evaluate("document.activeElement && document.activeElement.id || ''")
        if active_id and active_id not in visited:
            visited.append(active_id)
        if len(visited) >= len(expected_order):
            break

    assert visited == [x.lstrip('#') for x in expected_order], f"Tab order mismatch: {visited} vs {expected_order}"

    # Keyboard activation checks: Prev/Next should not throw; Play should toggle visibility of Pause
    page.keyboard.press("Home")  # ensure starting at first focusable element (best-effort)
    page.keyboard.press("Enter")  # activate Prev (no error expected)

    # Focus Play and press Space
    page.focus("#play")
    page.keyboard.press("Space")
    # Pause button should become visible
    pause_display = page.eval_on_selector("#pause", "el => getComputedStyle(el).display")
    assert pause_display != "none", "Pause button should be visible after starting playback"

    # Press Space again to pause
    page.keyboard.press("Space")
    pause_display2 = page.eval_on_selector("#pause", "el => getComputedStyle(el).display")
    assert pause_display2 == "none", "Pause button should hide after pausing"

    # Fullscreen toggle via Enter
    page.focus("#fs")
    page.keyboard.press("Enter")
    is_fullscreen = page.evaluate("document.fullscreenElement !== null")
    assert is_fullscreen, "Fullscreen should be active after activating Fullscreen button"

    # Exit fullscreen via Escape
    page.keyboard.press("Escape")
    is_fullscreen2 = page.evaluate("document.fullscreenElement === null")
    assert is_fullscreen2, "Fullscreen should exit on Escape"

    # Reduced motion media query present (CSS check via text snapshot)
    html = page.content()
    assert "prefers-reduced-motion" in html

    # Robots noindex meta present
    assert re.search(r'<meta[^>]+name="robots"[^>]+noindex', html, re.IGNORECASE), "Noindex meta missing"
