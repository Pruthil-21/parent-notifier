"""Moving classes between mentors, approving requests and deleting accounts."""

from sqlalchemy import delete, func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.imports import StagedSheet


class NameClashError(Exception):
    """The new mentor already has classes with these names."""

    def __init__(self, names: list[str]) -> None:
        super().__init__(", ".join(names))
        self.names = names


class ClassesRemainError(Exception):
    """An account with classes cannot be deleted; move or delete them first."""


def mentors_except(account: Mentor) -> list[Mentor]:
    """Approved accounts that can take over classes from this one."""
    query = select(Mentor).where(Mentor.approved.is_(True), Mentor.id != account.id)
    return list(db.session.scalars(query.order_by(func.lower(Mentor.full_name))))


def transfer_classes(classes: list[ClassGroup], to_mentor: Mentor) -> None:
    """Give the classes to another mentor with everything in them. Their send history
    keeps who sent each message. Sheets waiting for Confirm are dropped, since they
    belonged to the old mentor's session."""
    taken = set(
        db.session.scalars(
            select(func.lower(ClassGroup.name)).where(ClassGroup.mentor_id == to_mentor.id)
        )
    )
    clashes = sorted(c.name for c in classes if c.name.lower() in taken)
    if clashes:
        raise NameClashError(clashes)
    ids = [class_group.id for class_group in classes]
    db.session.execute(delete(StagedSheet).where(StagedSheet.class_id.in_(ids)))
    for class_group in classes:
        class_group.mentor_id = to_mentor.id
    db.session.commit()


def requests() -> list[Mentor]:
    """Accounts waiting for approval, oldest first."""
    query = select(Mentor).where(Mentor.approved.is_(False)).order_by(Mentor.created_at)
    return list(db.session.scalars(query))


def approve(account: Mentor) -> None:
    account.approved = True
    db.session.commit()


def reject(account: Mentor) -> None:
    """A request that is turned down is deleted; nothing else belongs to it yet."""
    db.session.delete(account)
    db.session.commit()


def delete_account(account: Mentor) -> None:
    has_classes = db.session.scalar(select(func.count()).where(ClassGroup.mentor_id == account.id))
    if has_classes:
        raise ClassesRemainError(account.username)
    db.session.delete(account)
    db.session.commit()
