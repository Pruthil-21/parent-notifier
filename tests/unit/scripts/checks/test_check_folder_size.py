from scripts.checks.check_folder_size import FAIL_AT, WARN_AT, check, files_per_folder


def files(folder: str, count: int) -> list[str]:
    return [f"{folder}/module_{index}.py" for index in range(count)]


def test_small_folder_passes():
    assert check(files("app/services", WARN_AT - 1)) == []


def test_folder_at_warning_size_warns():
    [finding] = check(files("app/services", WARN_AT))
    assert finding.level == "warning"
    assert finding.message.startswith("app/services/ holds 9 files")


def test_folder_at_fail_size_fails():
    [finding] = check(files("app/services", FAIL_AT))
    assert finding.level == "error"


def test_init_license_and_readme_are_not_counted():
    paths = [*files("app", WARN_AT - 1), "app/__init__.py", "app/LICENSE", "app/README.md"]
    assert files_per_folder(paths)["app"] == WARN_AT - 1
    assert check(paths) == []


def test_exempt_folders_are_skipped():
    icons = files("parent_notifier/static/icons/fluent", 40)
    assert check([*files("migrations/versions", FAIL_AT), *icons]) == []


def test_root_files_are_exempt():
    assert check([f"config_{index}.toml" for index in range(FAIL_AT)]) == []


def test_catch_all_names_fail():
    findings = check(["app/utils.py", "static/js/helpers.js", "app/phone.py"])
    assert [f.level for f in findings] == ["error", "error"]
    assert "app/utils.py" in findings[0].message
