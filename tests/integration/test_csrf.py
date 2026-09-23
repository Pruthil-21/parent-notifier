import re

import pytest

from tests.factories.accounts import PASSWORD


@pytest.fixture
def csrf_client(app):
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()


def _token(html: str) -> str:
    return re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)


def test_post_without_token_is_refused_with_a_way_forward(csrf_client, mentor):
    response = csrf_client.post("/sign-in", data={"username": "ashapatel", "password": PASSWORD})
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "This form has expired" in html
    assert "CSRF" not in html


def test_post_with_token_from_the_form_is_accepted(csrf_client, mentor):
    token = _token(csrf_client.get("/sign-in").get_data(as_text=True))
    response = csrf_client.post(
        "/sign-in", data={"username": "ashapatel", "password": PASSWORD, "csrf_token": token}
    )
    assert response.status_code == 302


def test_sign_out_needs_a_token_too(csrf_client, mentor):
    token = _token(csrf_client.get("/sign-in").get_data(as_text=True))
    csrf_client.post(
        "/sign-in", data={"username": "ashapatel", "password": PASSWORD, "csrf_token": token}
    )
    assert csrf_client.post("/sign-out").status_code == 400
    assert csrf_client.get("/").status_code == 200
