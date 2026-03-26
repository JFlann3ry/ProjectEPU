from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.middleware_security import SecurityHeadersMiddleware


def test_csp_report_only_header_is_emitted_when_enabled():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, csp_report_only=True)

    @app.get("/")
    def home():
        return Response("<html><body>ok</body></html>", media_type="text/html")

    client = TestClient(app)
    r = client.get("/")

    assert r.status_code == 200
    assert "content-security-policy" not in r.headers
    ro = r.headers.get("content-security-policy-report-only", "")
    assert "default-src 'self'" in ro


def test_csp_report_uri_is_appended_when_configured():
    app = FastAPI()
    app.add_middleware(
        SecurityHeadersMiddleware,
        csp_report_only=True,
        csp_report_uri="/csp-report",
    )

    @app.get("/")
    def home():
        return Response("<html><body>ok</body></html>", media_type="text/html")

    client = TestClient(app)
    r = client.get("/")

    assert r.status_code == 200
    ro = r.headers.get("content-security-policy-report-only", "")
    assert "report-uri /csp-report;" in ro
