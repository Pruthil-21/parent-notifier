"""Search, status filter and sorting for the student grid.

Values come from the page's query string, so each one is checked against a fixed list;
anything unexpected falls back to the default rather than raising an error.
"""

from dataclasses import dataclass

from parent_notifier.services.academics.views import risk
from parent_notifier.services.academics.views.semester_view import StudentRow

INACTIVE = "inactive"
PENDING = "pending"
STATUS_FILTERS = {
    "": "All active students",
    risk.AT_RISK: "At risk",
    risk.NEEDS_ATTENTION: "Needs attention",
    risk.DOING_WELL: "Doing well",
    risk.NO_DATA: "No data",
    PENDING: "Message pending",
    INACTIVE: "Left or detained",
}
SORTS = ("enrollment", "name", "attendance")
MAX_SEARCH = 100


@dataclass(frozen=True)
class GridQuery:
    search: str = ""
    status: str = ""
    sort: str = "enrollment"
    descending: bool = False

    @classmethod
    def from_args(cls, args) -> "GridQuery":
        status = args.get("status", "")
        sort = args.get("sort", "enrollment")
        return cls(
            search=" ".join(args.get("q", "").split())[:MAX_SEARCH],
            status=status if status in STATUS_FILTERS else "",
            sort=sort if sort in SORTS else "enrollment",
            descending=args.get("dir") == "desc",
        )

    @property
    def filtered(self) -> bool:
        return bool(self.search or self.status)


def _matches(row: StudentRow, query: GridQuery, pending: set[int]) -> bool:
    if query.status == INACTIVE:
        in_status = not row.active
    elif query.status == PENDING:
        in_status = row.id in pending
    else:
        in_status = row.active and (not query.status or row.band == query.status)
    needle = query.search.casefold()
    found = not needle or any(
        needle in value.casefold() for value in (row.full_name, row.parent_name, row.enrollment_no)
    )
    return in_status and found


def _sort_key(row: StudentRow, sort: str):
    if sort == "name":
        return (row.full_name.casefold(), row.enrollment_no)
    if sort == "attendance":
        # Students without figures go last whichever way the list is sorted.
        missing = row.lowest is None
        return (missing, row.lowest.percent if row.lowest else 0, row.enrollment_no)
    return (row.enrollment_no,)


def apply(
    rows: list[StudentRow], query: GridQuery, pending: set[int] | None = None
) -> list[StudentRow]:
    """`pending` holds the ids of parents still to be messaged, for that filter."""
    kept = [row for row in rows if _matches(row, query, pending or set())]
    ordered = sorted(kept, key=lambda row: _sort_key(row, query.sort), reverse=query.descending)
    if query.sort == "attendance" and query.descending:
        ordered = [row for row in ordered if row.lowest] + [r for r in ordered if not r.lowest]
    return ordered
