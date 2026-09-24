"""One page of a long list, with what the page links need."""

from dataclasses import dataclass, replace
from math import ceil

from sqlalchemy import func, select

from parent_notifier.core.extensions import db


@dataclass(frozen=True)
class Page:
    items: list
    number: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, ceil(self.total / self.per_page))

    @property
    def first(self) -> int:
        return (self.number - 1) * self.per_page + 1 if self.total else 0

    @property
    def last(self) -> int:
        return min(self.number * self.per_page, self.total)

    def with_items(self, items: list) -> "Page":
        return replace(self, items=items)


def paginate(query, number: int, per_page: int) -> Page:
    """Run an ordered select for one page. A page past the end shows the last one."""
    total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    number = min(max(1, number), max(1, ceil(total / per_page)))
    items = list(db.session.scalars(query.limit(per_page).offset((number - 1) * per_page)))
    return Page(items, number, per_page, total)


def paginate_list(items: list, number: int, per_page: int) -> Page:
    """The same for a list already in memory, such as rows sorted by a count."""
    total = len(items)
    number = min(max(1, number), max(1, ceil(total / per_page)))
    return Page(items[(number - 1) * per_page : number * per_page], number, per_page, total)


def page_number(value: str | None) -> int:
    return int(value) if value and value.isdecimal() and len(value) < 6 else 1
