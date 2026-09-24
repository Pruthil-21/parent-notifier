import re
from pathlib import Path

import pytest

from parent_notifier import static_version
from parent_notifier.core.security import CONTENT_SECURITY_POLICY

STATIC = f"/static/{static_version()}"

TEMPLATES = Path(__file__).resolve().parents[2] / "parent_notifier" / "templates"


@pytest.mark.parametrize("path", ["/no-such-page", f"{STATIC}/css/app.css"])
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
    assert client.get(f"{STATIC}/css/app.css").headers.get("Cache-Control") != "no-store"


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


def test_static_files_can_be_kept_by_a_cdn_even_when_signed_in(signed_in_client):
    """Vercel's CDN caches a response only with s-maxage and no cookie attached."""
    response = signed_in_client.get(f"{STATIC}/css/app.css")
    assert response.headers["Cache-Control"] == (
        "public, max-age=31536000, s-maxage=31536000, immutable"
    )
    assert "Set-Cookie" not in response.headers
    assert "Cookie" not in response.headers.get("Vary", "")


def test_static_urls_carry_a_fingerprint_of_the_files(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert f'href="{STATIC}/css/app.css"' in html
    assert signed_in_client.get("/static/css/app.css").status_code == 404


def test_pages_ask_the_browser_to_load_the_next_page_early(signed_in_client):
    page = signed_in_client.get("/")
    assert page.headers["Speculation-Rules"] == '"/speculation-rules.json"'
    rules = signed_in_client.get("/speculation-rules.json")
    assert rules.mimetype == "application/speculationrules+json"
    rule = rules.get_json()["prerender"][0]
    assert rule["eagerness"] == "moderate"
    excluded = str(rule["where"])
    for skipped in ("/*.xlsx", "[download]", "[data-dialog-open]", "[data-student-link]"):
        assert skipped in excluded
    assert "Speculation-Rules" not in signed_in_client.get(f"{STATIC}/css/app.css").headers


def test_every_change_drops_pages_loaded_early(signed_in_client):
    response = signed_in_client.post("/profile/theme", data={"theme": "dark"})
    assert response.headers["Clear-Site-Data"] == '"prefetchCache", "prerenderCache"'
    assert "Clear-Site-Data" not in signed_in_client.get("/").headers
