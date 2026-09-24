"""Each semester's student, at-risk and pending counts, ready for pages that show many
classes at once, such as the admin overview.

The counts come from the same semester view and send log as the semester page, so both
always agree. Changes that affect them clear the cached row (imports, undo, students,
status rules, sends); a row older than MAX_AGE is worked out again as a safety net.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester, SemesterStats
from parent_notifier.services.shared import clock

MAX_AGE = timedelta(minutes=30)


@dataclass(frozen=True)
class Counts:
    students: int = 0
    at_risk: int = 0
    pending: int = 0


def invalidate(*semester_ids: int) -> None:
    """Clear the counts of these semesters; the caller commits."""
    if semester_ids:
        db.session.execute(delete(SemesterStats).where(SemesterStats.semester_id.in_(semester_ids)))


def invalidate_class(class_id: int) -> None:
    """Clear the counts of every semester in a class; the caller commits."""
    ids = select(Semester.id).where(Semester.class_id == class_id)
    db.session.execute(delete(SemesterStats).where(SemesterStats.semester_id.in_(ids)))


def _compute(semester: Semester) -> Counts:
    from parent_notifier.services.academics.views import semester_view
    from parent_notifier.services.academics.views.risk import AT_RISK
    from parent_notifier.services.messaging import send_log

    view = semester_view.build(semester.class_group, semester)
    pending = send_log.pending_ids(view.rows, send_log.marks_for(semester))
    return Counts(len(view.active_rows), view.tiles[AT_RISK], len(pending))


def counts_for(semesters: list[Semester]) -> dict[int, Counts]:
    """Counts for each semester by id, working out and saving any that are missing."""
    if not semesters:
        return {}
    fresh_after = clock.now() - MAX_AGE
    rows = db.session.scalars(
        select(SemesterStats).where(
            SemesterStats.semester_id.in_([s.id for s in semesters]),
            SemesterStats.computed_at >= fresh_after,
        )
    )
    found = {row.semester_id: Counts(row.students, row.at_risk, row.pending) for row in rows}
    missing = [semester for semester in semesters if semester.id not in found]
    if missing:
        invalidate(*(semester.id for semester in missing))
        now = clock.now()
        for semester in missing:
            counts = _compute(semester)
            found[semester.id] = counts
            db.session.add(
                SemesterStats(semester_id=semester.id, computed_at=now, **counts.__dict__)
            )
        db.session.commit()
    return found
