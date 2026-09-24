"""Security headers added to every response, and caching rules for static files."""

from flask import Flask, Response, request
from flask.sessions import SecureCookieSessionInterface

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
    else:
        # CSS and JavaScript: a CDN such as Vercel's keeps them until the next deploy,
        # and browsers check back each time, so a new version shows at once.
        response.headers["Cache-Control"] = "public, max-age=0, must-revalidate, s-maxage=31536000"
    return response


class StaticFilesSkipSession(SecureCookieSessionInterface):
    """CSS and JavaScript never depend on who is signed in, so their responses carry no
    session cookie and no "Vary: Cookie". Either would stop a CDN from caching them."""

    def save_session(self, app, session, response) -> None:
        if request.endpoint != "static":
            super().save_session(app, session, response)


def init_security(app: Flask) -> None:
    app.after_request(apply_security_headers)
    app.session_interface = StaticFilesSkipSession()
