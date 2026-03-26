import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        prod_only: bool = True,
        csp_report_only: bool = False,
        csp_report_uri: str = "",
    ):
        super().__init__(app)
        self.prod_only = prod_only or os.getenv("ENV", "dev") == "prod"
        self.csp_report_only = bool(csp_report_only)
        self.csp_report_uri = str(csp_report_uri or "").strip()

    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        content_type = response.headers.get("content-type", "").lower()
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
        is_https = request.url.scheme == "https" or forwarded_proto == "https"
        # Only set security headers for HTML responses
        if content_type.startswith("text/html") or content_type == "":
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            csp_parts = [
                "default-src 'self';",
                "script-src 'self' 'unsafe-inline' https://js.stripe.com https://cdn.jsdelivr.net;",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net;",
                "img-src 'self' data: https://*.stripe.com;",
                "font-src 'self' https://fonts.gstatic.com;",
                "connect-src 'self' https://api.stripe.com;",
                "frame-src https://js.stripe.com;",
                "object-src 'none';",
                "base-uri 'self';",
                "form-action 'self';",
            ]
            if is_https:
                csp_parts.append("upgrade-insecure-requests;")
            if self.csp_report_uri:
                csp_parts.append(f"report-uri {self.csp_report_uri};")
            csp_header = " ".join(csp_parts)
            if self.csp_report_only:
                response.headers["Content-Security-Policy-Report-Only"] = csp_header
            else:
                response.headers["Content-Security-Policy"] = csp_header
            if self.prod_only and is_https:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=63072000; includeSubDomains; preload"
                )
        return response
