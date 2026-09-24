from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.college import Department
from tests.factories.academics import make_class
from tests.factories.accounts import PASSWORD

BASE = "/admin/settings/departments"


def _id(app, name):
    with app.app_context():
        return db.session.scalars(db.select(Department.id).filter_by(name=name)).one()


def test_the_admin_adds_renames_and_removes_departments(app, admin_client, mentor):
    with app.app_context():
        class_id = make_class(mentor, department="Civil Engineering").id
    page = admin_client.get(BASE).get_data(as_text=True)
    assert "Mechatronics Engineering" in page and "In use" in page

    assert admin_client.post(BASE, data={"name": " Physics "}).headers["Location"] == BASE
    taken = admin_client.post(BASE, data={"name": "civil engineering"}).get_data(as_text=True)
    assert "Civil Engineering is already listed" in taken

    admin_client.post("/admin/users/confirm-password", data={"password": PASSWORD})
    civil = _id(app, "Civil Engineering")
    admin_client.post(f"{BASE}/{civil}/rename", data={"name": "Civil Engg"})
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).department == "Civil Engg"
    refused = admin_client.post(f"{BASE}/{civil}/remove").get_data(as_text=True)
    assert "Still used by 0 mentors and 1 classes" in refused
    admin_client.post(f"{BASE}/{_id(app, 'Physics')}/remove")
    assert 'value="Physics"' not in admin_client.get(BASE).get_data(as_text=True)
