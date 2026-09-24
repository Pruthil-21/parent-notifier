"""The announcement banner: one at a time, published and removed by the admin."""

from sqlalchemy import delete, exists, select

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.college import Announcement, AnnouncementDismissal


def current() -> Announcement | None:
    return db.session.scalar(select(Announcement).order_by(Announcement.id.desc()).limit(1))


def publish(text: str, dismissible: bool, by: Mentor) -> Announcement:
    """Replaces any current announcement, so everyone sees the new one, even mentors who
    closed the old one."""
    db.session.execute(delete(Announcement))
    announcement = Announcement(text=text, dismissible=dismissible, created_by_id=by.id)
    db.session.add(announcement)
    db.session.commit()
    return announcement


def remove() -> bool:
    """False when there was nothing to remove."""
    removed = db.session.execute(delete(Announcement)).rowcount
    db.session.commit()
    return bool(removed)


def dismiss(announcement_id: int, mentor: Mentor) -> None:
    """Only the current announcement, and only one the admin let mentors close."""
    announcement = current()
    if announcement is None or announcement.id != announcement_id or not announcement.dismissible:
        return
    if db.session.get(AnnouncementDismissal, (announcement.id, mentor.id)) is None:
        db.session.add(AnnouncementDismissal(announcement_id=announcement.id, mentor_id=mentor.id))
        db.session.commit()


def visible_for(mentor: Mentor) -> Announcement | None:
    closed = exists().where(
        AnnouncementDismissal.announcement_id == Announcement.id,
        AnnouncementDismissal.mentor_id == mentor.id,
    )
    query = select(Announcement).where(~closed).order_by(Announcement.id.desc()).limit(1)
    return db.session.scalar(query)
