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
