import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, prod_only: bool = True):
        super().__init__(app)
        self.prod_only = prod_only or os.getenv("ENV", "dev") == "prod"

    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        content_type = response.headers.get("content-type", "").lower()
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
                "upgrade-insecure-requests;",
            ]
            csp_header = " ".join(csp_parts)
            response.headers["Content-Security-Policy"] = csp_header
            if self.prod_only:
                response.headers[
                    "Strict-Transport-Security"
                ] = "max-age=63072000; includeSubDomains; preload"
        return response
