"""Parent Notifier web application."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from parent_notifier.core.config import load_config
from parent_notifier.core.errors import init_error_pages
from parent_notifier.core.extensions import init_extensions
from parent_notifier.core.icons import render_icon
from parent_notifier.core.navigation import init_navigation
from parent_notifier.core.security import init_security


def create_app(env: str | None = None) -> Flask:
    """Build the app for an environment: "development", "testing" or "production".

    Without an argument the environment comes from FLASK_CONFIG, defaulting to
    development. Values in a local .env file are loaded first.
    """
    load_dotenv()
    env = env or os.environ.get("FLASK_CONFIG", "development")
    app = Flask(__name__)
    app.config.update(load_config(env, Path(app.instance_path)))
    init_extensions(app)
    app.add_template_global(render_icon, "icon")
    init_navigation(app)
    init_error_pages(app)
    init_security(app)
    return app
