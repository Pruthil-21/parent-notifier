from tests.factories.accounts import sign_in


def test_sign_out_ends_the_session_and_says_so(signed_in_client):
    response = signed_in_client.post("/sign-out", follow_redirects=True)
    assert response.request.path == "/sign-in"
    assert "You have signed out." in response.get_data(as_text=True)
    assert signed_in_client.get("/").status_code == 302


def test_sign_out_deletes_the_remember_cookie(client, mentor):
    sign_in(client, remember="y")
    assert client.get_cookie("remember_token") is not None
    client.post("/sign-out")
    assert client.get_cookie("remember_token") is None
    assert client.get("/").status_code == 302


def test_sign_out_only_accepts_post(signed_in_client):
    assert signed_in_client.get("/sign-out").status_code == 405
    assert signed_in_client.get("/").status_code == 200
