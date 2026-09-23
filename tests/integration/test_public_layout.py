from flask import render_template_string

PAGE = '{% extends "layouts/public.html" %}{% block title %}Sign in{% endblock %}'
PAGE += "{% block panel %}<h1>Sign in</h1>{% endblock %}"


def render(app):
    with app.test_request_context("/"):
        return render_template_string(PAGE)


def test_public_layout_shows_product_and_college(app):
    html = render(app)
    assert '<span class="public-panel__product">Parent Notifier</span>' in html
    assert "G. H. Patel College of Engineering &amp; Technology" in html
    assert "<h1>Sign in</h1>" in html
    assert "<title>Sign in · Parent Notifier</title>" in html


def test_public_layout_has_main_landmark_and_skip_link_without_app_shell(app):
    html = render(app)
    assert '<main id="main" class="public-frame__main" tabindex="-1">' in html
    assert 'href="#main"' in html
    assert "nav-pane" not in html
    assert "nav-pane.js" not in html
