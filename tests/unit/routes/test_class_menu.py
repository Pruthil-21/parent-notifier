from parent_notifier.routes.academics.class_menu import MenuClass, class_menu


def _menu(*classes, current=None, own=None):
    return class_menu(list(classes), lambda i: f"/c/{i}", current, own_department=own)


def _shape(entries):
    """Each entry as text: a link with its note, a heading, or a group with its insides."""
    out = []
    for entry in entries:
        if entry["kind"] == "group":
            out.append((entry["label"], _shape(entry["children"])))
        elif entry["kind"] == "heading":
            out.append(f"# {entry['label']}")
        else:
            out.append(entry["label"] + (f" · {entry['note']}" if entry["note"] else ""))
    return out


CE, IT = "Computer Engineering", "Information Technology"


def test_two_classes_stay_a_plain_list_with_their_years():
    menu = _menu(MenuClass(1, "CE-A", CE, 2024, False), MenuClass(2, "IT-A", IT, 2025, False))
    assert _shape(menu) == ["IT-A · 2025", "CE-A · 2024"]


def test_one_department_groups_by_year_newest_first():
    menu = _menu(
        MenuClass(1, "CE-B", CE, 2025, False),
        MenuClass(2, "CE-A", CE, 2025, False),
        MenuClass(3, "CE-A", CE, 2024, False),
    )
    assert _shape(menu) == ["# 2025 batch", "CE-A", "CE-B", "# 2024 batch", "CE-A"]


def test_departments_group_with_the_mentors_own_first_and_past_batches_last():
    menu = _menu(
        MenuClass(1, "CE-A", CE, 2025, False),
        MenuClass(2, "IT-A", IT, 2025, False),
        MenuClass(3, "IT-B", IT, 2024, False),
        MenuClass(4, "CE-OLD", CE, 2021, True),
        current=4,
        own=IT,
    )
    assert _shape(menu) == [
        (IT, ["# 2025 batch", "IT-A", "# 2024 batch", "IT-B"]),
        (CE, ["CE-A · 2025"]),
        ("Past batches", ["CE-OLD · 2021"]),
    ]
    past = menu[-1]
    assert past["open"] is False and past["active"] is True  # it holds the current page
