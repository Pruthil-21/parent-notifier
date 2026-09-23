"""Security headers added to every response."""

from flask import Flask, Response, request

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)

HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}

HSTS = "max-age=31536000; includeSubDomains"


def apply_security_headers(response: Response) -> Response:
    for name, value in HEADERS.items():
        response.headers.setdefault(name, value)
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    # Pages hold student and parent data; keep them out of shared browsers' caches.
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


def init_security(app: Flask) -> None:
    app.after_request(apply_security_headers)
