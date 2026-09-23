from flask import Flask

from parent_notifier import create_app


def test_create_app_for_testing():
    app = create_app("testing")
    assert isinstance(app, Flask)
    assert app.config["ENV_NAME"] == "testing"
    assert app.testing is True


def test_environment_comes_from_flask_config(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    assert create_app().config["ENV_NAME"] == "testing"
