import pytest
from flask import abort, request

from parent_notifier import create_app


@pytest.fixture
def app():
    app = create_app("testing")
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.route("/fail/<int:code>")
    def fail(code):
        abort(code)

    @app.route("/crash")
    def crash():
        raise RuntimeError("database password is hunter2")

    @app.route("/upload", methods=["POST"])
    def upload():
        # The limit applies when the body is read, as every real upload route does.
        return str(len(request.get_data()))

    return app


@pytest.mark.parametrize(
    ("path", "code", "title"),
    [
        ("/no-such-page", 404, "Page not found"),
        ("/fail/400", 400, "That request could not be used"),
        ("/fail/403", 403, "You do not have access to this page"),
        ("/fail/429", 429, "Too many attempts"),
    ],
)
def test_error_pages_keep_status_and_explain(client, path, code, title):
    response = client.get(path)
    html = response.get_data(as_text=True)
    assert response.status_code == code
    assert f"<h1>{title}</h1>" in html
    assert f"Error {code}" in html
    assert "Go to your home page" in html


def test_oversized_upload_names_the_limit(client):
    response = client.post("/upload", data=b"x" * (2 * 1024 * 1024))
    assert response.status_code == 413
    assert "The file is larger than 1 MB." in response.get_data(as_text=True)


def test_unexpected_error_hides_internals(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = app.test_client().get("/crash")
    html = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "Something went wrong on our side" in html
    assert "hunter2" not in html
    assert "Traceback" not in html


def test_error_page_does_not_echo_the_address(client):
    html = client.get("/<script>alert(1)</script>").get_data(as_text=True)
    assert "alert(1)" not in html
