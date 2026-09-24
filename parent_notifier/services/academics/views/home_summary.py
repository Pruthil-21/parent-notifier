"""Tiles and class rows across all of a mentor's classes, for the home workspace.

Each class counts from its latest semester, built with the same semester view and send
log as the semester page, so the two pages always show the same numbers. Left and
detained students are not counted, and neither are finished batches.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.services.academics.views import semester_view
from parent_notifier.services.academics.views.risk import AT_RISK
from parent_notifier.services.messaging import send_log


@dataclass(frozen=True)
class ClassSummary:
    class_group: ClassGroup
    semester: Semester | None  # the latest semester, None before the first is added
    students: int
    at_risk: int
    pending: int

    @property
    def last_imported_at(self) -> datetime | None:
        return self.semester.last_imported_at if self.semester else None


@dataclass(frozen=True)
class HomeSummary:
    classes: list[ClassSummary]
    waiting: list[Semester]  # semesters with no sheet yet, in every class

    @property
    def at_risk(self) -> int:
        return sum(row.at_risk for row in self.classes)

    @property
    def pending(self) -> int:
        return sum(row.pending for row in self.classes)

    def only(self, figure: str) -> ClassSummary | None:
        """The one class behind a figure such as "at_risk", so its tile can open that
        class's filtered grid. None when several classes, or none, add to it."""
        found = [row for row in self.classes if getattr(row, figure)]
        return found[0] if len(found) == 1 else None


def _summarise(class_group: ClassGroup) -> ClassSummary:
    if not class_group.semesters:
        return ClassSummary(class_group, None, 0, 0, 0)
    semester = class_group.semesters[-1]
    view = semester_view.build(class_group, semester)
    pending = send_log.pending_ids(view.rows, send_log.marks_for(semester))
    return ClassSummary(
        class_group, semester, len(view.active_rows), view.tiles[AT_RISK], len(pending)
    )


def build(mentor_id: int) -> HomeSummary:
    classes = db.session.scalars(
        select(ClassGroup)
        .where(ClassGroup.mentor_id == mentor_id, ClassGroup.finished_at.is_(None))
        .options(selectinload(ClassGroup.semesters))
        .order_by(func.lower(ClassGroup.name))
    )
    waiting = db.session.scalars(
        select(Semester)
        .join(ClassGroup)
        .where(
            ClassGroup.mentor_id == mentor_id,
            ClassGroup.finished_at.is_(None),
            Semester.last_imported_at.is_(None),
        )
        .order_by(func.lower(ClassGroup.name), Semester.number)
    )
    return HomeSummary([_summarise(class_group) for class_group in classes], list(waiting))
