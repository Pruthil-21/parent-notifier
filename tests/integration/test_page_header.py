from flask import flash, render_template_string

PAGE = """{% extends "layouts/app.html" %}
{% from "components/navigation/breadcrumb.html" import breadcrumb %}
{% from "components/navigation/action_bar.html" import action_bar %}
{% block breadcrumb %}{{ breadcrumb([("Home", "/"), ("Classes", "/classes"), ("CE-A", None)]) }}
{% endblock %}
{% block page_title %}CE-A{% endblock %}
{% block actions %}{% call action_bar() %}<button class="button">Upload sheet</button>{% endcall %}
{% endblock %}"""

UNTITLED = '{% extends "layouts/app.html" %}{% block content %}<p>Body</p>{% endblock %}'


def render(app, template, messages=()):
    with app.test_request_context("/"):
        for text, category in messages:
            flash(text, category)
        return render_template_string(template)


def test_breadcrumb_links_ancestors_and_marks_current_page(app):
    html = render(app, PAGE)
    assert '<nav class="breadcrumb" aria-label="Breadcrumb">' in html
    assert '<a href="/classes">Classes</a>' in html
    assert '<span aria-current="page">CE-A</span>' in html
    assert 'href="None"' not in html


def test_title_row_and_action_bar(app):
    html = render(app, PAGE)
    assert '<h1 class="page-header__title">CE-A</h1>' in html
    assert '<div class="action-bar">' in html
    assert "Upload sheet" in html


def test_page_without_title_has_no_empty_heading(app):
    assert "<h1" not in render(app, UNTITLED)


def test_message_bar_roles_follow_category(app):
    html = render(app, UNTITLED, [("Sheet imported.", "success"), ("Row 4 is invalid.", "error")])
    assert 'class="message-bar message-bar--success" role="status"' in html
    assert 'class="message-bar message-bar--error" role="alert"' in html
    assert 'aria-label="Dismiss message"' in html


def test_message_text_is_escaped_and_unknown_category_is_info(app):
    html = render(app, UNTITLED, [("<b>bold</b>", "surprise")])
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "message-bar--info" in html
    assert "message-bar--surprise" not in html


def test_no_message_stack_without_messages(app):
    assert "message-stack" not in render(app, UNTITLED)
