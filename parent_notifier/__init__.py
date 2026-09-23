"""Parent Notifier web application."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from parent_notifier.core.config import load_config


def create_app(env: str | None = None) -> Flask:
    """Build the app for an environment: "development", "testing" or "production".

    Without an argument the environment comes from FLASK_CONFIG, defaulting to
    development. Values in a local .env file are loaded first.
    """
    load_dotenv()
    env = env or os.environ.get("FLASK_CONFIG", "development")
    app = Flask(__name__)
    app.config.update(load_config(env, Path(app.instance_path)))
    return app
