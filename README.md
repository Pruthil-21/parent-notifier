# Parent Notifier

A web app for college mentors. A mentor uploads the semester sheet with each
student's attendance and mid-sem marks, the app shows which students are at risk,
and it opens WhatsApp Web with each parent's message already typed. The mentor
presses Enter and moves on to the next parent.

## Status

Early development. This repository currently contains the project tooling; the
application arrives milestone by milestone. See [CHANGELOG.md](CHANGELOG.md) for
what has landed so far.

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

Run the checks and tests:

```
uv run ruff check .
uv run python -m scripts.checks.check_file_length
uv run python -m scripts.checks.check_folder_size
uv run pytest
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the branch, commit and pull request
conventions.

## License

No license has been chosen yet, so all rights are reserved for now.
