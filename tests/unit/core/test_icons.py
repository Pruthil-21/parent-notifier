import pytest
from flask import render_template_string

from parent_notifier.core.icons import PATHS, render_icon


def test_icon_is_decorative_by_default():
    svg = str(render_icon("home"))
    assert svg.startswith('<svg class="icon" width="20" height="20" viewBox="0 0 20 20"')
    assert 'aria-hidden="true" focusable="false"' in svg
    assert 'fill="currentColor"' in svg
    assert PATHS["home"] in svg


def test_labelled_icon_is_announced_and_label_is_escaped():
    svg = str(render_icon("dismiss", label='Close "dialog" <now>'))
    assert 'role="img"' in svg
    assert 'aria-label="Close &#34;dialog&#34; &lt;now&gt;"' in svg
    assert "aria-hidden" not in svg


def test_size_is_forced_to_an_integer():
    assert 'width="16" height="16"' in str(render_icon("add", size=16))
    with pytest.raises(ValueError):
        render_icon("add", size='16" onload="alert(1)')


def test_unknown_icon_fails_loudly():
    with pytest.raises(KeyError, match="Unknown icon 'hom'"):
        render_icon("hom")


def test_icon_is_available_in_templates(app):
    with app.test_request_context():
        html = render_template_string('{{ icon("menu", label="Show navigation") }}')
    assert 'aria-label="Show navigation"' in html
