import pytest

from tests.factories.accounts import PASSWORD, make_mentor, sign_in


@pytest.fixture
def admin(app):
    with app.app_context():
        return make_mentor(
            full_name="Pruthil Mistry",
            username="pruthil",
            whatsapp_number="+919000000009",
            department="Computer Engineering",
            role="admin",
            password=PASSWORD,
        ).id


@pytest.fixture
def admin_client(client, admin):
    sign_in(client, username="pruthil")
    return client
