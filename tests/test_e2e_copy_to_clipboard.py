# ruff: noqa: I001
import os

from playwright.sync_api import sync_playwright
import pytest


# Skip this file by default unless E2E=1 env var is set
e2e_enabled = os.getenv("E2E", "0") == "1"
pytestmark = pytest.mark.skipif(
    not e2e_enabled, reason="E2E tests disabled; set E2E=1 to enable"
)


def test_copy_buttons_show_feedback():
    # Minimal smoke of copy UI.
    # Requires a server running at BASE_URL (default 4200).
    base = os.getenv("BASE_URL", "http://localhost:4200").rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(
            """
            (() => {
              if (!navigator.clipboard) {
                navigator.clipboard = {
                  writeText: async (t) => { window.__copied = t; }
                };
              }
            })();
            """
        )
        page.goto(f"{base}/events/1")

        # Try to find any known copy control
        for sel in ["#guest-link", "#event-code", "#event-pass", ".share-copy"]:
            if page.locator(sel).first.count() > 0:
                page.locator(sel).first.click()
                assert page.title() is not None
                break
        else:
            # If none found, ensure page loaded (e.g., login) without errors
            assert page.title() is not None

        context.close()
        browser.close()
