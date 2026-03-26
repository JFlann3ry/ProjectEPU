from pathlib import Path


def test_share_modal_buttons_present(client):
    """Smoke test: base template includes share modal buttons with expected IDs and aria-labels."""
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    # The share modal build is included in base.html; ensure our buttons and aria labels exist
    assert 'id="share-wa"' in text
    assert 'id="share-messenger"' in text
    assert 'id="share-email"' in text
    assert 'id="share-copy"' in text
    assert 'aria-label="Share via WhatsApp"' in text
    assert 'aria-label="Share via Messenger"' in text
    assert 'aria-label="Share via Email"' in text
    assert 'aria-label="Copy message and link"' in text


def test_modal_and_snackbar_accessibility_contract(client):
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    assert 'id="modal-root"' in text
    assert 'id="modal-root" class="modal-overlay" aria-hidden="true"' in text
    snackbar_fragment = (
        'id="snackbar" class="snackbar" role="status" ' 'aria-live="polite" aria-atomic="true"'
    )
    assert snackbar_fragment in text


def test_base_modal_keyboard_focus_hooks_present():
    js = Path("static/js/base.js").read_text(encoding="utf-8")
    assert "function onKeydown(event)" in js
    assert "if (event.key === 'Tab')" in js or "if (event.key !== 'Tab')" in js
    assert "if (event.key === 'Escape')" in js
    assert "lastFocused = document.activeElement" in js
    assert "lastFocused.focus();" in js
