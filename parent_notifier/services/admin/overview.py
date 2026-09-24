"""The admin overview: what needs attention across the college's current classes, and
the full class list behind it.

Counts come from each class's latest semester through the semester counts cache, so
they match the semester pages. Finished batches are left out of the overview; the class
list can show them.
"""

import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.academics.views.semester_stats import Counts
from parent_notifier.services.shared import clock, departments, pagination

PER_PAGE = 25
SENT_WINDOW = timedelta(days=7)
STATUSES = ("current", "finished", "all")
SORTS = {
    "name": "Class name",
    "pending": "Most pending",
    "at_risk": "Most at risk",
    "students": "Most students",
    "last_sheet": "Latest sheet",
}


@dataclass(frozen=True)
class ClassRow:
    class_group: ClassGroup
    mentor: Mentor
    semester: Semester | None
    counts: Counts
    sent: int


@dataclass(frozen=True)
class Figures:
    """Totals over some classes: the tiles, and each department's row."""

    classes: int = 0
    students: int = 0
    at_risk: int = 0
    pending: int = 0
    sent: int = 0

    @classmethod
    def of(cls, rows: list[ClassRow]) -> "Figures":
        return cls(
            classes=len(rows),
            students=sum(row.counts.students for row in rows),
            at_risk=sum(row.counts.at_risk for row in rows),
            pending=sum(row.counts.pending for row in rows),
            sent=sum(row.sent for row in rows),
        )


@dataclass(frozen=True)
class Overview:
    totals: Figures
    departments: list[tuple[str, Figures]]
    pending: pagination.Page  # classes with messages still to send, most first
    department: str | None


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


def _sent_by_class(class_ids: list[int]) -> dict[int, int]:
    if not class_ids:
        return {}
    return dict(
        db.session.execute(
            select(Semester.class_id, func.count(SendLog.id))
            .join(Semester, SendLog.semester_id == Semester.id)
            .where(
                Semester.class_id.in_(class_ids),
                SendLog.status == "sent",
                SendLog.created_at >= _since(),
            )
            .group_by(Semester.class_id)
        ).all()
    )


def class_rows(classes: list[ClassGroup]) -> list[ClassRow]:
    """Each class with its mentor, latest semester, counts and messages sent this week."""
    ids = [class_group.id for class_group in classes]
    mentors = {
        m.id: m
        for m in db.session.scalars(
            select(Mentor).where(Mentor.id.in_({c.mentor_id for c in classes}))
        )
    }
    latest = _latest_semesters(ids)
    counts = semester_stats.counts_for(list(latest.values()))
    sent = _sent_by_class(ids)
    return [
        ClassRow(
            class_group,
            mentors[class_group.mentor_id],
            latest.get(class_group.id),
            counts[latest[class_group.id].id] if class_group.id in latest else Counts(),
            sent.get(class_group.id, 0),
        )
        for class_group in classes
    ]


def _by_name(row: ClassRow) -> tuple:
    return (row.class_group.name.lower(), row.mentor.full_name.lower(), row.class_group.id)


def overview(department: str | None, page: int) -> Overview:
    """Totals and departments cover every current class; `department` narrows only the
    list of classes with pending messages."""
    classes = list(db.session.scalars(select(ClassGroup).where(ClassGroup.finished_at.is_(None))))
    rows = class_rows(classes)
    names = sorted({row.class_group.department for row in rows})
    by_department = [
        (name, Figures.of([row for row in rows if row.class_group.department == name]))
        for name in names
    ]
    pending = [
        row
        for row in rows
        if row.counts.pending and (department is None or row.class_group.department == department)
    ]
    pending.sort(key=lambda row: (-row.counts.pending, -row.counts.at_risk, *_by_name(row)))
    return Overview(
        totals=Figures.of(rows),
        departments=by_department,
        pending=pagination.paginate_list(pending, page, PER_PAGE),
        department=department,
    )


@dataclass(frozen=True)
class ClassFilters:
    search: str = ""
    department: str | None = None
    year: int | None = None
    status: str = "current"
    sort: str = "name"
    page: int = 1

    @classmethod
    def from_args(cls, args) -> "ClassFilters":
        year = args.get("year", "")
        status = args.get("status", "")
        sort = args.get("sort", "")
        return cls(
            search=" ".join(args.get("q", "").split())[:100],
            department=departments.canonical(args.get("department")),
            year=int(year) if year.isdecimal() and len(year) == 4 else None,
            status=status if status in STATUSES else "current",
            sort=sort if sort in SORTS else "name",
            page=pagination.page_number(args.get("page")),
        )

    @property
    def filtered(self) -> bool:
        return bool(self.search or self.department or self.year or self.status != "current")


def batch_years() -> list[int]:
    query = select(ClassGroup.admission_year).distinct()
    return sorted(db.session.scalars(query), reverse=True)


def _last_sheet(row: ClassRow) -> tuple:
    """Newest sheet first; classes without one go last."""
    when = row.semester.last_imported_at if row.semester else None
    return (when is None, -when.timestamp() if when else 0, *_by_name(row))


def _sort_key(sort: str):
    if sort == "last_sheet":
        return _last_sheet
    if sort in ("pending", "at_risk", "students"):
        return lambda row: (-getattr(row.counts, sort), *_by_name(row))
    return _by_name


def class_page(filters: ClassFilters) -> pagination.Page:
    """Every class matching the filters, sorted, one page at a time."""
    query = select(ClassGroup).join(Mentor, ClassGroup.mentor_id == Mentor.id)
    if filters.status == "current":
        query = query.where(ClassGroup.finished_at.is_(None))
    elif filters.status == "finished":
        query = query.where(ClassGroup.finished_at.is_not(None))
    if filters.department:
        query = query.where(ClassGroup.department == filters.department)
    if filters.year:
        query = query.where(ClassGroup.admission_year == filters.year)
    if filters.search:
        query = query.where(
            or_(
                _contains(ClassGroup.name, filters.search),
                _contains(Mentor.full_name, filters.search),
            )
        )
    rows = class_rows(list(db.session.scalars(query)))
    rows.sort(key=_sort_key(filters.sort))
    return pagination.paginate_list(rows, filters.page, PER_PAGE)
