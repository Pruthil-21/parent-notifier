"""One pass over every page in a real browser, in light and dark, plus the flows that
only work with JavaScript: the menus, the popup, the queue and a send."""

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
    ("/search?q=avi", "Search"),
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
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/5")
    page.locator(".sheet-menu summary").click()
    page.locator(".sheet-menu").get_by_role("link", name="Upload sheet").click()
    dialog = page.locator("#upload-sheet")
    expect(dialog).to_be_visible()
    expect(page.locator(".sheet-menu")).not_to_have_attribute("open", "")
    dialog.locator("input[type=file]").set_input_files(str(sheet))
    dialog.get_by_role("button", name="Upload and review").click()
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


def test_menus_stay_on_screen_on_a_phone(signed_in, demo):
    page = signed_in
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    page.locator(".sheet-menu summary").click()
    panel = page.locator(".sheet-menu .menu__panel")
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390


def test_sidebar_sections_filter_and_stay_folded(signed_in, demo):
    page = signed_in
    page.goto(demo.url + "/help")
    classes = page.locator("#nav-children-classes")
    page.get_by_role("button", name="Filter classes").click()
    page.locator("#nav-filter-classes-input").fill("zz")
    expect(page.get_by_text("No matches")).to_be_visible()
    page.locator("#nav-filter-classes-input").fill("ce-")
    expect(classes.get_by_role("link", name="CE-A")).to_be_visible()
    page.get_by_role("button", name="Classes list").click()
    page.reload()
    expect(classes).to_be_hidden()
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    expect(classes).to_be_visible()  # the current page's section always opens


def test_resting_on_a_link_loads_its_page_before_the_click(signed_in, demo):
    """Chrome and Edge load a same-site page once the pointer rests on its link, so the
    click shows it at once. A normal browser prerenders it; under test automation the
    browser only prefetches it, which this also accepts."""
    page = signed_in
    if not page.evaluate("HTMLScriptElement.supports?.('speculationrules')"):
        pytest.skip("This browser does not support speculation rules")
    link = page.locator('.nav-pane a[title="Classes"]')
    link.hover()
    page.wait_for_timeout(1500)
    link.click()
    page.wait_for_url(f"{demo.url}/classes/")
    entry = page.evaluate(
        "(({activationStart, deliveryType}) => ({activationStart, deliveryType}))"
        "(performance.getEntriesByType('navigation')[0])"
    )
    assert entry["activationStart"] > 0 or entry["deliveryType"] == "navigational-prefetch"


def _send_first_time(page, popup):
    popup.get_by_role("button", name="Send on WhatsApp").click()
    page.get_by_role("button", name="Yes, continue").click()


def test_on_a_phone_send_saves_then_opens_the_whatsapp_app(signed_in_phone, demo):
    page = signed_in_phone
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    popup = page.locator("#student-popup")
    page.get_by_role("link", name="Riya Patel").click()
    _send_first_time(page, popup)
    open_app = popup.get_by_role("link", name="Open WhatsApp")
    expect(open_app).to_be_visible()
    expect(open_app).to_have_attribute("href", re.compile(r"^https://wa\.me/919000000103\?text="))
    expect(popup.locator('[data-slot="mark"]')).to_have_text(re.compile(r"^Sent "))
    with page.expect_popup():
        open_app.tap()
    expect(open_app).to_be_hidden()


def test_a_blocked_whatsapp_tab_offers_a_link_instead(signed_in, demo):
    page = signed_in
    page.add_init_script("window.open = () => null")  # as a pop-up blocker would
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    popup = page.locator("#student-popup")
    page.get_by_role("link", name="Isha Joshi").click()
    _send_first_time(page, popup)
    open_link = popup.get_by_role("link", name="Open WhatsApp")
    expect(open_link).to_have_attribute(
        "href", re.compile(r"^https://web\.whatsapp\.com/send\?phone=919000000104&text=")
    )
    expect(popup.get_by_role("button", name=re.compile(r"^Wait \d+ s$"))).to_be_disabled()
    expect(popup.locator('[data-slot="send-note"]')).to_contain_text("blocked the WhatsApp tab")


def test_a_touch_screen_laptop_still_gets_whatsapp_web(browser, demo):
    """A laptop whose main pointer is a finger is not mistaken for a phone."""
    from tests.e2e.conftest import sign_in

    context = browser.new_context(has_touch=True)
    page = context.new_page()
    errors = sign_in(page, demo)
    page.goto(f"{demo.url}/classes/{demo.class_id}/sem/4")
    page.get_by_role("link", name="Avi Shah").click()
    popup = page.locator("#student-popup")
    with page.expect_popup() as opened:
        _send_first_time(page, popup)
    opened.value.wait_for_url(re.compile(r"^https://web\.whatsapp\.com/send"))
    expect(popup.get_by_role("link", name="Open WhatsApp")).to_be_hidden()
    context.close()
    assert errors == []
