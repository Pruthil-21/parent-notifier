"""The admin's list of accounts and each account's details."""

from dataclasses import dataclass

from sqlalchemy import func, or_, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.services.admin.overview import phone_digits
from parent_notifier.services.shared import departments, pagination

PER_PAGE = 25


@dataclass(frozen=True)
class Filters:
    search: str = ""
    department: str | None = None
    page: int = 1

    @classmethod
    def from_args(cls, args) -> "Filters":
        return cls(
            search=" ".join(args.get("q", "").split())[:100],
            department=departments.canonical(args.get("department")),
            page=pagination.page_number(args.get("page")),
        )

    @property
    def filtered(self) -> bool:
        return bool(self.search or self.department)


def _contains(column, text: str):
    return func.lower(column).contains(text.lower(), autoescape=True)


def account_page(filters: Filters) -> pagination.Page:
    """Approved accounts, with how many classes each has. Requests are listed apart."""
    classes = (
        select(func.count(ClassGroup.id)).where(ClassGroup.mentor_id == Mentor.id).scalar_subquery()
    )
    query = select(Mentor, classes).where(Mentor.approved.is_(True))
    if filters.department:
        query = query.where(Mentor.department == filters.department)
    if filters.search:
        matches = [
            _contains(Mentor.full_name, filters.search),
            _contains(Mentor.username, filters.search),
        ]
        if digits := phone_digits(filters.search):
            matches.append(Mentor.whatsapp_number.contains(digits, autoescape=True))
        query = query.where(or_(*matches))
    query = query.order_by(func.lower(Mentor.full_name), Mentor.id)
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    number = min(max(1, filters.page), max(1, -(-total // PER_PAGE)))
    rows = db.session.execute(query.limit(PER_PAGE).offset((number - 1) * PER_PAGE)).all()
    return pagination.Page([(mentor, count) for mentor, count in rows], number, PER_PAGE, total)


def get_account(account_id: int) -> Mentor | None:
    return db.session.get(Mentor, account_id)


def classes_of(mentor: Mentor) -> list[ClassGroup]:
    query = select(ClassGroup).where(ClassGroup.mentor_id == mentor.id)
    return list(db.session.scalars(query.order_by(func.lower(ClassGroup.name))))


def recent_activity(mentor: Mentor, limit: int = 10) -> list[ActivityEntry]:
    query = select(ActivityEntry).where(ActivityEntry.actor_id == mentor.id)
    return list(db.session.scalars(query.order_by(ActivityEntry.id.desc()).limit(limit)))


def menu_links() -> list[tuple[int, str]]:
    """Each approved account's id and name, in name order, for the admin's menu."""
    query = (
        select(Mentor.id, Mentor.full_name)
        .where(Mentor.approved.is_(True))
        .order_by(func.lower(Mentor.full_name), Mentor.id)
    )
    return [(account_id, name) for account_id, name in db.session.execute(query)]
