"""The admin's Mentors menu: department, then each mentor, then that mentor's classes.

Departments and mentors start folded, since there can be many; the ones holding the
page being shown open. With a single department there is no department level. A
mentor's name opens their page and each class opens its read-only view.
"""

from collections import defaultdict

from flask import request, url_for
from flask_login import current_user

from parent_notifier.core.navigation import nav_group, nav_link, slug
from parent_notifier.services.admin import users

NO_DEPARTMENT = "No department"


def _class_links(classes, current_class_id) -> list[dict]:
    ordered = sorted(
        classes, key=lambda c: (c.finished_at is not None, -c.admission_year, c.name.lower(), c.id)
    )
    return [
        nav_link(
            c.name,
            url_for("admin_classes.open_class", class_id=c.id),
            c.id == current_class_id,
            f"{c.admission_year}, finished" if c.finished_at else str(c.admission_year),
        )
        for c in ordered
    ]


def mentor_links() -> list[dict]:
    if not (current_user.is_authenticated and current_user.is_admin):
        return []
    view_args = request.view_args or {}
    current_account = view_args.get("account_id") if request.blueprint == "admin_users" else None
    current_class = view_args.get("class_id") if request.blueprint == "admin_classes" else None
    accounts, classes = users.menu_rows()
    by_mentor = defaultdict(list)
    for class_row in classes:
        by_mentor[class_row.mentor_id].append(class_row)

    def entry(account) -> dict:
        url = url_for("admin_users.detail", account_id=account.id)
        current = account.id == current_account
        links = _class_links(by_mentor[account.id], current_class)
        if not links:
            return nav_link(account.full_name, url, current)
        return nav_group(
            f"mentors-m{account.id}",
            account.full_name,
            links,
            url=url,
            current=current,
            open_by_default=False,
        )

    names = sorted({account.department or NO_DEPARTMENT for account in accounts})
    if len(names) <= 1:
        return [entry(account) for account in accounts]
    # "No department" goes last rather than in A to Z order.
    names.sort(key=lambda name: name == NO_DEPARTMENT)
    return [
        nav_group(
            f"mentors-d-{slug(name)}",
            name,
            [entry(a) for a in accounts if (a.department or NO_DEPARTMENT) == name],
            open_by_default=False,
        )
        for name in names
    ]
