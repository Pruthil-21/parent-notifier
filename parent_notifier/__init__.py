"""Parent Notifier web application."""

import hashlib
import os
from functools import cache
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from parent_notifier.core.cli import init_cli
from parent_notifier.core.config import load_config
from parent_notifier.core.errors import init_error_pages
from parent_notifier.core.extensions import init_extensions
from parent_notifier.core.icons import render_icon
from parent_notifier.core.jinja_filters import init_jinja_filters
from parent_notifier.core.navigation import init_navigation
from parent_notifier.core.security import init_security
from parent_notifier.routes.blueprints import register_blueprints

STATIC_FOLDER = Path(__file__).parent / "static"


@cache
def static_version() -> str:
    """A short fingerprint of every CSS and JavaScript file. It is part of each static
    URL, so browsers can keep the files for a year and still get new ones after any
    change: relative imports inside the files carry the same fingerprint."""
    digest = hashlib.sha256()
    for path in sorted(STATIC_FOLDER.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(STATIC_FOLDER).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def create_app(env: str | None = None) -> Flask:
    """Build the app for an environment: "development", "testing" or "production".

    Without an argument the environment comes from FLASK_CONFIG, defaulting to
    development. Values in a local .env file are loaded first.
    """
    load_dotenv()
    env = env or os.environ.get("FLASK_CONFIG", "development")
    app = Flask(__name__, static_url_path=f"/static/{static_version()}")
    app.config.update(load_config(env, Path(app.instance_path)))
    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    init_extensions(app)
    app.add_template_global(render_icon, "icon")
    init_jinja_filters(app)
    register_blueprints(app)
    init_navigation(app)
    init_error_pages(app)
    init_security(app)
    init_cli(app)
    return app
