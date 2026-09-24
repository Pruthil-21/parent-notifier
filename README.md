# Parent Notifier

A web app for college mentors. A mentor uploads the semester sheet with each
student's attendance and mid-sem marks, the app shows which students are at risk,
and it opens WhatsApp Web with each parent's message already typed. The mentor
presses Enter and moves on to the next parent.

## Status

Version 0.2.0 works end to end on one computer: mentor accounts, classes and
semesters, sheet import with review and undo, the semester workspace, and sending each
parent their message through WhatsApp Web with pacing and a daily limit. It adds a home
workspace across all classes, a light and dark theme saved per mentor, and a help page.
Running it on a shared college server comes next. Each release is described on the
[Releases](https://github.com/Pruthil-21/parent-notifier/releases) page.

## What it will do

- Keep one class per batch, with a semester added whenever the batch moves up.
- Import a semester sheet, show every problem with its row number, and save nothing
  until the mentor confirms. The last import can be undone.
- Mark each student At risk (attendance below 75% in any subject's theory or
  practical), Needs attention (mid-sem below the pass mark) or Doing well.
- Write each parent's message from a template in English or Gujarati, with an
  optional note from the mentor.
- Walk through every parent still waiting for a message, spacing the sends out to
  protect the mentor's WhatsApp number.

## Sheet format

One row per student: enrollment number, student name, parent name, parent phone,
then one column per subject. Each subject cell looks like this:

```
Theory=86,Practical=92,Marks=16
```

`Marks` is the mid-sem score. `AB` marks an absent student, and a blank value means
there is no data yet.

## Tech stack

Python 3.12+, Flask, SQLAlchemy with SQLite, server-rendered Jinja templates with
plain CSS and JavaScript modules. No build step and no outside network calls at
runtime.

## Getting started

You need Python 3.12 or newer, Git, and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/Pruthil-21/parent-notifier.git
cd parent-notifier
uv sync
uv run pre-commit install
```

Create the database, load the demo (a fictional class with two imported semesters) and
start the app at http://127.0.0.1:5000:

```
uv run flask --app parent_notifier db upgrade
uv run flask --app parent_notifier seed-demo
uv run flask --app parent_notifier run
```

Sign in with the username and password that `seed-demo` prints. The sample sheets it
loads are in `samples/`; `uv run python scripts/dev/make_samples.py` rebuilds them.

Run the linter, the formatter check and the tests:

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

The browser smoke tests are separate. They need a Playwright browser: install Chromium
once, or use an installed Edge with `--browser-channel msedge`.

```
uv run playwright install chromium
uv run pytest -m e2e
```

## Contributing

- Work on a short-lived branch and open a pull request against `main`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/),
  one logical change per commit, with its tests.
- The pre-commit hooks must pass: lint, formatting and the commit message format.
- Never commit real student or parent data.

## License

No license has been chosen yet, so all rights are reserved for now.
