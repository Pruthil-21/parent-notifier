from pathlib import Path

from scripts.checks.check_file_length import HARD_LIMIT, SOFT_LIMIT, check, main


def write_lines(root: Path, relative: str, count: int) -> str:
    file = root / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("x = 1\n" * count, encoding="utf-8")
    return relative


def test_short_file_passes(tmp_path):
    path = write_lines(tmp_path, "app/views.py", SOFT_LIMIT)
    assert check([path], tmp_path) == []


def test_file_over_soft_limit_warns(tmp_path):
    path = write_lines(tmp_path, "app/views.py", SOFT_LIMIT + 1)
    [finding] = check([path], tmp_path)
    assert finding.level == "warning"
    assert "201 lines" in finding.message


def test_file_over_hard_limit_fails(tmp_path):
    path = write_lines(tmp_path, "static/app.js", HARD_LIMIT + 1)
    [finding] = check([path], tmp_path)
    assert finding.level == "error"


def test_unchecked_suffixes_and_migrations_are_skipped(tmp_path):
    paths = [
        write_lines(tmp_path, "uv.lock", HARD_LIMIT + 1),
        write_lines(tmp_path, "migrations/versions/0001_initial.py", HARD_LIMIT + 1),
    ]
    assert check(paths, tmp_path) == []


def test_missing_file_is_ignored(tmp_path):
    assert check(["gone.py"], tmp_path) == []


def test_main_exit_code_reflects_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_lines(tmp_path, "ok.py", 10)
    write_lines(tmp_path, "big.py", HARD_LIMIT + 1)
    assert main(["ok.py"]) == 0
    assert main(["big.py"]) == 1
