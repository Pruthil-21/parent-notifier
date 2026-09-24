"""The college's departments, used for mentors and classes alike."""

DEPARTMENTS = (
    "Applied Science & Humanities",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Engineering",
    "Computer Science and Design",
    "Computer Science and Engineering (IOT)",
    "Electrical Engineering",
    "Electronics & Communication",
    "Information & Communication Technology",
    "Information Technology",
    "Mechanical Engineering",
    "Mechatronics Engineering",
)
_BY_LOWER = {name.lower(): name for name in DEPARTMENTS}


def canonical(value: str | None) -> str | None:
    """The department as listed, whatever its case or spacing, or None if not listed."""
    return _BY_LOWER.get(" ".join((value or "").split()).lower())
