"""The record of each confirmed import, with what the semester held before it."""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import UTCDateTime
from parent_notifier.services.shared import clock


class ImportBatch(db.Model):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), index=True
    )
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(120))
    round: Mapped[int]
    previous_round: Mapped[int]
    added_count: Mapped[int]
    updated_count: Mapped[int]
    # Subjects, members, results and changed identities as they were before the import,
    # so undo can put them back exactly.
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: clock.now())
    undone_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
