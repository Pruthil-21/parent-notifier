"""The admin overview: every mentor and every class, with their counts.

Counts come from each class's latest semester through the semester counts cache, so
they match the semester pages. Only the rows on the page being shown are counted.
"""

import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.academics.views.semester_stats import Counts
from parent_notifier.services.shared import clock, departments, pagination

PER_PAGE = 25
VIEWS = ("mentors", "classes")
SENT_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class Filters:
    view: str = "mentors"
    search: str = ""
    department: str | None = None
    page: int = 1

    @classmethod
    def from_args(cls, args) -> "Filters":
        view = args.get("view", "")
        return cls(
            view=view if view in VIEWS else "mentors",
            search=" ".join(args.get("q", "").split())[:100],
            department=departments.canonical(args.get("department")),
            page=pagination.page_number(args.get("page")),
        )

    @property
    def filtered(self) -> bool:
        return bool(self.search or self.department)


@dataclass(frozen=True)
class Totals:
    mentors: int
    classes: int
    students: int


@dataclass(frozen=True)
class MentorRow:
    mentor: Mentor
    classes: int
    counts: Counts
    sent: int


@dataclass(frozen=True)
class ClassRow:
    class_group: ClassGroup
    mentor: Mentor
    semester: Semester | None
    counts: Counts
    sent: int


def _count(query) -> int:
    return db.session.scalar(select(func.count()).select_from(query.subquery()))


def totals() -> Totals:
    return Totals(
        mentors=_count(select(Mentor.id).where(Mentor.approved.is_(True))),
        classes=_count(select(ClassGroup.id)),
        students=_count(select(Student.id).where(Student.status == "active")),
    )


def phone_digits(search: str) -> str | None:
    """The last ten digits of a search that looks like a phone number, however typed."""
    digits = re.sub(r"\D", "", search)
    return digits[-10:] if len(digits) >= 4 else None


def _contains(column, text: str):
    return func.lower(column).contains(text.lower(), autoescape=True)


def _latest_semesters(class_ids: list[int]) -> dict[int, Semester]:
    if not class_ids:
        return {}
    latest = (
        select(Semester.class_id, func.max(Semester.number).label("number"))
        .where(Semester.class_id.in_(class_ids))
        .group_by(Semester.class_id)
        .subquery()
    )
    query = (
        select(Semester)
        .join(
            latest, and_(Semester.class_id == latest.c.class_id, Semester.number == latest.c.number)
        )
        .options(selectinload(Semester.class_group))
    )
    return {semester.class_id: semester for semester in db.session.scalars(query)}


def _since():
    return clock.now() - SENT_WINDOW


def mentor_page(filters: Filters) -> pagination.Page:
    query = select(Mentor).where(Mentor.approved.is_(True))
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
    page = pagination.paginate(
        query.order_by(func.lower(Mentor.full_name), Mentor.id), filters.page, PER_PAGE
    )
    ids = [mentor.id for mentor in page.items]
    classes = list(db.session.scalars(select(ClassGroup).where(ClassGroup.mentor_id.in_(ids))))
    latest = _latest_semesters([class_group.id for class_group in classes])
    counts = semester_stats.counts_for(list(latest.values()))
    sent = dict(
        db.session.execute(
            select(SendLog.mentor_id, func.count())
            .where(
                SendLog.mentor_id.in_(ids), SendLog.status == "sent", SendLog.created_at >= _since()
            )
            .group_by(SendLog.mentor_id)
        ).all()
    )
    rows = []
    for mentor in page.items:
        own = [c for c in classes if c.mentor_id == mentor.id]
        found = [counts[latest[c.id].id] for c in own if c.id in latest]
        total = Counts(
            *(sum(getattr(c, name) for c in found) for name in ("students", "at_risk", "pending"))
        )
        rows.append(MentorRow(mentor, len(own), total, sent.get(mentor.id, 0)))
    return page.with_items(rows)


def class_page(filters: Filters) -> pagination.Page:
    query = select(ClassGroup).join(Mentor, ClassGroup.mentor_id == Mentor.id)
    if filters.department:
        query = query.where(ClassGroup.department == filters.department)
    if filters.search:
        query = query.where(
            or_(
                _contains(ClassGroup.name, filters.search),
                _contains(Mentor.full_name, filters.search),
            )
        )
    page = pagination.paginate(
        query.order_by(func.lower(ClassGroup.name), func.lower(Mentor.full_name), ClassGroup.id),
        filters.page,
        PER_PAGE,
    )
    ids = [class_group.id for class_group in page.items]
    mentors = {
        m.id: m
        for m in db.session.scalars(
            select(Mentor).where(Mentor.id.in_({c.mentor_id for c in page.items}))
        )
    }
    latest = _latest_semesters(ids)
    counts = semester_stats.counts_for(list(latest.values()))
    sent = dict(
        db.session.execute(
            select(Semester.class_id, func.count(SendLog.id))
            .join(Semester, SendLog.semester_id == Semester.id)
            .where(
                Semester.class_id.in_(ids), SendLog.status == "sent", SendLog.created_at >= _since()
            )
            .group_by(Semester.class_id)
        ).all()
    )
    rows = [
        ClassRow(
            class_group,
            mentors[class_group.mentor_id],
            latest.get(class_group.id),
            counts[latest[class_group.id].id] if class_group.id in latest else Counts(),
            sent.get(class_group.id, 0),
        )
        for class_group in page.items
    ]
    return page.with_items(rows)
