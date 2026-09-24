"""The Classes menu: grouped by department, then batch year, newest first.

A level appears only when it offers a choice. One or two classes stay a plain list; one
department needs no department group; a department with one batch needs no year
headings. Where there is no year heading, each class shows its year beside the name.
Finished batches go last, in a folded Past batches group.
"""

from collections.abc import Callable
from dataclasses import dataclass

from parent_notifier.core.navigation import nav_group, nav_heading, nav_link, slug

# Up to this many classes are simply listed, however they are spread.
PLAIN_LIST = 2


@dataclass(frozen=True)
class MenuClass:
    id: int
    name: str
    department: str
    admission_year: int
    finished: bool


def _ordered(classes: list[MenuClass]) -> list[MenuClass]:
    return sorted(classes, key=lambda c: (-c.admission_year, c.name.lower(), c.id))


def _links(classes, url, current_id, with_year: bool) -> list[dict]:
    return [
        nav_link(
            c.name, url(c.id), c.id == current_id, str(c.admission_year) if with_year else None
        )
        for c in _ordered(classes)
    ]


def _by_year(classes, url, current_id) -> list[dict]:
    years = sorted({c.admission_year for c in classes}, reverse=True)
    if len(years) == 1:
        return _links(classes, url, current_id, with_year=True)
    entries = []
    for year in years:
        entries.append(nav_heading(f"{year} batch"))
        entries += _links([c for c in classes if c.admission_year == year], url, current_id, False)
    return entries


def class_menu(
    classes: list[MenuClass],
    url: Callable[[int], str],
    current_id: int | None,
    own_department: str | None = None,
    prefix: str = "classes",
) -> list[dict]:
    current = [c for c in classes if not c.finished]
    finished = [c for c in classes if c.finished]
    if len(current) <= PLAIN_LIST:
        entries = _links(current, url, current_id, with_year=True)
    else:
        # The mentor's own department first, the rest A to Z.
        names = sorted({c.department for c in current}, key=lambda d: (d != own_department, d))
        if len(names) == 1:
            entries = _by_year(current, url, current_id)
        else:
            entries = [
                nav_group(
                    f"{prefix}-{slug(name)}",
                    name,
                    _by_year([c for c in current if c.department == name], url, current_id),
                )
                for name in names
            ]
    if finished:
        entries.append(
            nav_group(
                f"{prefix}-past",
                "Past batches",
                _links(finished, url, current_id, with_year=True),
                open_by_default=False,
            )
        )
    return entries
