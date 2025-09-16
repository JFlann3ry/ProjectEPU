
def test_receipt_pdf_requires_login(client):
    # Without auth, should redirect to login
    r = client.get("/billing/purchase/1/receipt.pdf", follow_redirects=False)
    assert r.status_code in (302, 303)
    loc = r.headers.get("location", "")
    assert "/login" in loc


def test_receipt_text_requires_login(client):
    r = client.get("/billing/purchase/1/receipt", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")
