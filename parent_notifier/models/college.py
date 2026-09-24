"""Settings for the whole college, kept by the admin."""

from sqlalchemy import String, event, insert
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import Timestamps

# The departments a new database starts with. After that the admin keeps the list.
DEFAULT_DEPARTMENTS = (
    "Applied Science & Humanities",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Engineering",
    "Computer Science and Design",
    "Computer Science and Engineering (IOT)",
    "Electrical Engineering",
    "Electronics & Communication",
    "Information & Communication Technology",
    "Information Technology",
    "Mechanical Engineering",
    "Mechatronics Engineering",
)


class Department(Timestamps, db.Model):
    """A department. Mentors and classes store its name, so renaming one updates them."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)

    def __repr__(self) -> str:
        return f"<Department {self.id} {self.name}>"


class Setting(Timestamps, db.Model):
    """One college-wide setting, such as who may create an account."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


@event.listens_for(Department.__table__, "after_create")
def _add_default_departments(table, connection, **_) -> None:
    """A database built with create_all(), as in tests, starts with the same list as a
    migrated one."""
    connection.execute(insert(table), [{"name": name} for name in DEFAULT_DEPARTMENTS])
