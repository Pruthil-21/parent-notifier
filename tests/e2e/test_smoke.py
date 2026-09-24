"""One pass over every page in a real browser, in light and dark, plus the flows that
only work with JavaScript: the theme menu, the popup, the queue and a send."""

import re
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from tests.factories.workbooks import make_xlsx

pytestmark = pytest.mark.e2e

PAGES = [
    ("/", "Home"),
    ("/classes", "Classes"),
    ("/classes/new", "New class"),
    ("/classes/{id}/sem/4", "CE-A"),
    ("/classes/{id}/sem/4/upload", "Upload Sem 4 sheet"),
    ("/classes/{id}/sem/4/students/new", "Add student to Sem 4"),
    ("/classes/{id}/settings", "Class settings"),
    ("/profile/", "Profile"),
    ("/help", "Help"),
]


def choose_theme(page, label: str) -> None:
    page.click("[data-theme-menu] summary")
    with page.expect_response("**/profile/theme") as saved:
        page.get_by_role("button", name=label, exact=True).click()
    assert saved.value.status == 204


@pytest.mark.parametrize(("theme", "width"), [("Light", 1366), ("Dark", 390)])
def test_every_page_loads(signed_in, demo, theme, width):
    page = signed_in
    page.set_viewport_size({"width": width, "height": 900})
    choose_theme(page, theme)
    for path, title in PAGES:
        response = page.goto(demo.url + path.format(id=demo.class_id))
        assert response.ok, path
        expect(page.locator("html")).to_have_attribute("data-theme", theme.lower())
        expect(page.locator("h1")).to_have_text(title)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 0, f"{path} scrolls sideways by {overflow}px"


def test_theme_choice_is_kept_on_the_account(signed_in, demo):
    page = signed_in
    choose_theme(page, "Dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("[data-theme-menu] summary")).to_have_attribute("aria-label", "Theme: Dark")
    choose_theme(page, "System")


def test_sheet_import_through_review(signed_in, demo, tmp_path):
    page = signed_in
    sheet = tmp_path / "sem5.xlsx"
    sheet.write_bytes(make_xlsx())
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/5/upload")
    page.set_input_files("input[type=file]", str(sheet))
    page.get_by_role("button", name="Upload and review").click()
    page.get_by_role("button", name="Confirm import").click()
    expect(page.locator(".tiles")).to_be_visible()
    assert page.url.endswith(f"/classes/{demo.class_id}/sem/5")


def test_popup_queue_and_send(signed_in, demo):
    page = signed_in
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    popup = page.locator("#student-popup")

    page.get_by_role("link", name="Om Desai").click()
    expect(popup.locator("#popup-name")).to_have_text("Om Desai")
    expect(popup.locator('[data-slot="message"]')).to_contain_text("Om Desai")
    popup.get_by_role("button", name="Send on WhatsApp").click()
    with page.expect_popup() as opened:
        page.get_by_role("button", name="Yes, continue").click()
    whatsapp = opened.value
    whatsapp.wait_for_url(re.compile(r"^https://web\.whatsapp\.com/send"))
    query = parse_qs(urlsplit(whatsapp.url).query)
    assert query["phone"] == ["919000000102"]
    assert "Om Desai" in query["text"][0]
    expect(popup.locator('[data-slot="mark"]')).to_have_text(re.compile(r"^Sent "))
    popup.locator("[data-dialog-close]").first.click()

    page.locator("[data-queue-open]").click()
    position = popup.locator('[data-slot="queue-position"]')
    expect(position).to_have_text(re.compile(r"^Parent 1 of \d+$"))
    popup.get_by_role("button", name="Skip").click()
    expect(position).to_have_text(re.compile(r"^Parent 2 of \d+$"))
