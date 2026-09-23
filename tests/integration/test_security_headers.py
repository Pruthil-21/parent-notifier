import re
from pathlib import Path

import pytest

from parent_notifier.core.security import CONTENT_SECURITY_POLICY

TEMPLATES = Path(__file__).resolve().parents[2] / "parent_notifier" / "templates"


@pytest.mark.parametrize("path", ["/no-such-page", "/static/css/app.css"])
def test_every_response_carries_security_headers(client, path):
    headers = client.get(path).headers
    assert headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "same-origin"
    assert "camera=()" in headers["Permissions-Policy"]


def test_policy_allows_only_own_scripts_and_no_framing():
    assert "script-src 'self'" in CONTENT_SECURITY_POLICY
    assert "'unsafe-inline'" not in CONTENT_SECURITY_POLICY
    assert "'unsafe-eval'" not in CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
    assert "object-src 'none'" in CONTENT_SECURITY_POLICY


def test_pages_are_not_cached_but_static_files_are(client):
    assert client.get("/no-such-page").headers["Cache-Control"] == "no-store"
    assert client.get("/static/css/app.css").headers.get("Cache-Control") != "no-store"


def test_hsts_only_over_https(client):
    assert "Strict-Transport-Security" not in client.get("/no-such-page").headers
    secure = client.get("/no-such-page", base_url="https://localhost")
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_templates_use_no_inline_scripts_styles_or_handlers():
    """The policy blocks these, so they must never appear in templates."""
    for template in TEMPLATES.rglob("*.html"):
        html = template.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)", html), template
        assert " style=" not in html, template
        assert not re.search(r"\son[a-z]+=", html), template
