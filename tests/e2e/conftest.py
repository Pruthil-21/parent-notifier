"""A live server for the browser smoke tests, with CSRF protection switched back on.

Run them with `uv run pytest -m e2e`; locally `--browser-channel msedge` uses the Edge
already installed instead of a downloaded Chromium.
"""

import os
import threading
from dataclasses import dataclass

import pytest
from werkzeug.serving import make_server

from parent_notifier import create_app
from parent_notifier.core.extensions import db
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import PASSWORD, make_mentor


@dataclass(frozen=True)
class Demo:
    url: str
    class_id: int


@pytest.fixture(scope="session")
def demo(tmp_path_factory):
    folder = tmp_path_factory.mktemp("e2e")
    previous = os.environ.get("DATABASE_URL")
    sqlite = f"sqlite:///{(folder / 'e2e.db').as_posix()}"
    os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", sqlite)
    try:
        app = create_app("testing")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL")
        else:
            os.environ["DATABASE_URL"] = previous
    app.instance_path = str(folder / "instance")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        mentor = make_mentor(password=PASSWORD)
        class_group = make_class(mentor)
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
        make_semester(class_group, 5)
        class_id = class_group.id
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield Demo(f"http://127.0.0.1:{server.server_port}", class_id)
    server.shutdown()
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def signed_in(page, demo):
    """A signed-in page that fails the test on any script error or console error."""
    errors = []

    def on_console(message):
        url = message.location.get("url", "")
        # The browser asks for a favicon the app doesn't have, and Windows sometimes
        # reports a network change mid-load; neither is a fault in the page.
        if message.type != "error" or url.endswith("/favicon.ico"):
            return
        if "net::ERR_NETWORK_CHANGED" not in message.text:
            errors.append(f"{message.text} {url}")

    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", on_console)
    # WhatsApp Web is never contacted; the tab gets a stand-in page instead.
    page.context.route("https://web.whatsapp.com/**", lambda route: route.fulfill(body="ok"))
    page.goto(f"{demo.url}/sign-in")
    page.fill("input[name=username]", "ashapatel")
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{demo.url}/")
    yield page
    assert errors == []
