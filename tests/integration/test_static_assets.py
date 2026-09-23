import re


def test_stylesheet_entry_declares_layers_and_imports_foundation(client):
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert "@layer foundation, shell, components, pages;" in css
    for path in re.findall(r'@import url\("([^"]+)"\)', css):
        assert client.get(f"/static/css/{path}").status_code == 200, path


def test_tokens_define_both_colour_schemes(client):
    css = client.get("/static/css/foundation/tokens.css").get_data(as_text=True)
    assert "color-scheme: light dark;" in css
    assert ':root[data-theme="dark"]' in css
    assert "--color-accent: light-dark(#0b5c73, #5db3cb);" in css
