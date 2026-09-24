"""Headers added to every response: security, caching, and loading the next page early.

Pages are never cached, since they hold student data. Instead, Chrome and Edge are
asked to load a same-site page in the background once the mentor rests the pointer on
its link (Speculation Rules), so the click shows it at once. Any change made through
a form or the send button clears pages loaded that way, so none is ever out of date.
"""

from flask import Flask, Response, jsonify, request
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
YEAR = 365 * 24 * 60 * 60
# Static URLs carry a fingerprint of the files, so they never change under one address.
STATIC_CACHE = f"public, max-age={YEAR}, s-maxage={YEAR}, immutable"
SPECULATION_RULES_URL = "/speculation-rules.json"
# Links that download a file, open a dialog or the student window, or leave the page
# are left alone: loading those pages early would be wasted work.
SPECULATION_RULES = {
    "prerender": [
        {
            "where": {
                "and": [
                    {"href_matches": "/*"},
                    {"not": {"href_matches": "/*.xlsx"}},
                    {"not": {"href_matches": "/static/*"}},
                    {
                        "not": {
                            "selector_matches": "[download], [target], [data-dialog-open],"
                            " [data-student-link], [data-queue-open]"
                        }
                    },
                ]
            },
            "eagerness": "moderate",
        }
    ]
}
# Tells the browser to drop pages it loaded early, after something has changed.
CLEAR_SPECULATIONS = '"prefetchCache", "prerenderCache"'


def apply_security_headers(response: Response) -> Response:
    for name, value in HEADERS.items():
        response.headers.setdefault(name, value)
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    if request.endpoint == "static":
        response.headers["Cache-Control"] = STATIC_CACHE
        return response
    if request.endpoint != "speculation_rules":
        # Pages hold student and parent data; keep them out of shared browsers' caches.
        response.headers["Cache-Control"] = "no-store"
    if response.mimetype == "text/html":
        response.headers["Speculation-Rules"] = f'"{SPECULATION_RULES_URL}"'
    if request.method not in {"GET", "HEAD"}:
        response.headers["Clear-Site-Data"] = CLEAR_SPECULATIONS
    return response


def speculation_rules() -> Response:
    response = jsonify(SPECULATION_RULES)
    response.mimetype = "application/speculationrules+json"
    response.headers["Cache-Control"] = f"public, max-age=3600, s-maxage={YEAR}"
    return response


class StaticFilesSkipSession(SecureCookieSessionInterface):
    """CSS and JavaScript never depend on who is signed in, so their responses carry no
    session cookie and no "Vary: Cookie". Either would stop a CDN from caching them."""

    def save_session(self, app, session, response) -> None:
        if request.endpoint not in {"static", "speculation_rules"}:
            super().save_session(app, session, response)


def init_security(app: Flask) -> None:
    app.after_request(apply_security_headers)
    app.add_url_rule(SPECULATION_RULES_URL, "speculation_rules", speculation_rules)
    app.session_interface = StaticFilesSkipSession()
