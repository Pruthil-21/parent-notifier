"""Reading a rendered page in tests."""


def main_content(response) -> str:
    """The page's main area, without the navigation menu, which lists every class and,
    for the admin, every mentor."""
    html = response.get_data(as_text=True)
    return html[html.index("<main") :]
