from fastapi.testclient import TestClient


def test_security_headers_present_on_html(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "upgrade-insecure-requests" not in csp


def test_security_headers_add_https_upgrade_when_forwarded_proto_is_https(client: TestClient):
    r = client.get("/", headers={"x-forwarded-proto": "https"})
    assert r.status_code == 200
    csp = r.headers.get("content-security-policy", "")
    assert "upgrade-insecure-requests" in csp


def test_security_headers_not_added_to_plain_text_health(client: TestClient):
    r = client.get("/health.txt")
    assert r.status_code == 200
    assert "content-security-policy" not in r.headers
    assert "x-frame-options" not in r.headers
