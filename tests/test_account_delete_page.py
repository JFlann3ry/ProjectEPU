from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_account_delete_page_uses_extracted_script():
    client = TestClient(app)
    r = client.get("/account/delete")
    assert r.status_code == 200
    assert "js/pages/account_delete.js" in r.text
    assert "document.getElementById('confirm-delete')" not in r.text


def test_account_delete_confirmed_template_uses_extracted_script():
    content = (
        Path(__file__).parent.parent / "templates" / "account_delete_confirmed.html"
    ).read_text()
    assert "js/pages/account_delete_confirmed.js" in content
    assert "setTimeout" not in content
