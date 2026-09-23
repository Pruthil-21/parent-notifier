def test_home_needs_sign_in(client):
    assert client.get("/").status_code == 302


def test_top_bar_shows_the_sending_number_and_account_menu(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'Sending as <span class="numeric">+91 90000 00001</span>' in html
    assert 'aria-label="Account: Asha Patel"' in html
    assert ">AP</span>" in html
    assert 'action="/sign-out"' in html
    assert 'name="csrf_token"' in html


def test_navigation_lists_home_as_current(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'aria-current="page"' in html
    assert '<h1 class="page-header__title">Home</h1>' in html
