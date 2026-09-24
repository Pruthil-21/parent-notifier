# Parent Notifier

Semester reports for parents, sent through WhatsApp Web in a few clicks.

[![CI](https://github.com/Pruthil-21/parent-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/Pruthil-21/parent-notifier/actions/workflows/ci.yml)
![Version](https://img.shields.io/badge/version-0.2.0-0b5c73)
![Python](https://img.shields.io/badge/python-3.12%2B-3776ab)
![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230)

Parent Notifier is a web app for college faculty mentors. A mentor uploads the
semester sheet with each student's attendance and Mid-Sem marks. The app shows which
students need attention, then opens WhatsApp Web with each parent's message already
written. The mentor checks it, presses send, and moves on to the next parent.

It is built for one college first (G. H. Patel College of Engineering & Technology)
and runs on a single computer today.

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Sheet format](#sheet-format)
- [Getting started](#getting-started)
- [Deploy for testing (Vercel and Supabase)](#deploy-for-testing-vercel-and-supabase)
- [Configuration](#configuration)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Security and privacy](#security-and-privacy)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

**Classes and semesters**
- One class per batch, with a semester added as the batch moves up.
- A home workspace with students at risk, parents still to message and semesters
  waiting for a sheet, across every class.

**Sheet import**
- Upload `.xlsx` or `.csv`, review every problem with its row number, and save nothing
  until you confirm.
- Student details carry over from earlier semesters, and the review lists any
  differences.
- Undo the last import, or download the current data to edit and upload again.

**Student status**
- Each student is marked At risk, Needs attention, Doing well or No data, using
  thresholds set per class.
- Search, filter and sort the class, and open any student for a subject-by-subject view.

**Messaging**
- Messages in English or Gujarati from editable templates, with an optional note.
- A queue that walks through every parent still waiting for a message.
- Pacing to protect the mentor's WhatsApp number: a gap between sends, a pause after
  each burst and a daily limit.
- A record of every message sent, with its exact text.

**Everyday use**
- Light and dark themes, saved per mentor.
- Quick page changes: in Chrome and Edge, a page starts loading when you point at
  its link, and CSS and JavaScript are cached until they change.
- Built for keyboard use and WCAG 2.2 AA. Every page except the message window works
  without JavaScript.

## How it works

1. **Set up a class**: name, department and admission year, then add the current semester.
2. **Upload the sheet**: the review page shows new and changed students and any errors.
   Confirm to save.
3. **Check the status**: tiles and the student list show who is at risk and why.
4. **Message parents**: open a student or start the queue. Each send opens WhatsApp Web
   with the parent's number and message filled in.

| Status | Rule (defaults, editable per class) |
|---|---|
| At risk | Theory or Practical attendance below 75% in any subject |
| Needs attention | Attendance fine, but Mid-Sem below 7 (out of 20) or absent in any subject |
| Doing well | Neither of the above |
| No data | In the sheet, but no figures yet |

The app never sends anything by itself. WhatsApp Web sends from whichever account is
signed in, so the app shows the mentor's number as "Sending as" and asks them to
confirm it once per browser session.

## Sheet format

One row per student. The first four columns identify the student; every column after
that is one subject, headed with its name.

| Enrollment No | Student Name | Parent Name | Parent Phone | Data Structures | DBMS |
|---|---|---|---|---|---|
| 230120107001 | Student Name | Parent Name | 9000000001 | `Theory=86,Practical=92,Marks=16` | `Theory=79,Marks=AB` |

- `Theory` and `Practical` are attendance percentages; `Marks` is the Mid-Sem score.
- `AB` means absent. Leave a part out when there is no figure yet.
- The reader is forgiving: `;` or new lines between parts, `:` for `=`, `82%`,
  `16/20`, lowercase, and short keys (`Th`, `Pr`, `Mid`) all work.

The app offers a blank sheet format and a pre-filled sheet for each semester, and its
Help page covers every rule.

## Getting started

### Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Git

### Install

```
git clone https://github.com/Pruthil-21/parent-notifier.git
cd parent-notifier
uv sync
uv run pre-commit install
```

### Run with demo data

```
uv run flask --app parent_notifier db upgrade
uv run flask --app parent_notifier seed-demo
uv run flask --app parent_notifier run
```

Open http://127.0.0.1:5000 and sign in with the username and password that
`seed-demo` prints. The demo is a fictional class with two imported semesters. Its
sheets are in `samples/`, and `uv run python scripts/dev/make_samples.py` rebuilds
them. `seed-demo` refuses to run in production.

## Deploy for testing (Vercel and Supabase)

The app runs on Vercel's free plan with a free Supabase Postgres database. Use it for
testing with the fictional demo data only; real student records belong on the college
server planned for 1.0.0.

1. **Create the database.** Create a Supabase project in the **Mumbai (ap-south-1)**
   region, where the app also runs. Open **Connect**, choose
   **Transaction pooler** and copy the address (it ends in `:6543/postgres`). Put your
   database password in place of `[YOUR-PASSWORD]`.
2. **Create the Vercel project.** Import this repository in Vercel; it detects the app
   from `pyproject.toml`. Before the first deploy, add these environment variables:

   | Variable | Value |
   |---|---|
   | `FLASK_CONFIG` | `production` |
   | `SECRET_KEY` | a long random value, from `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | the Supabase address from step 1 |

3. **Deploy.** The build creates the tables in Supabase. The app runs in Vercel's
   Mumbai region (`bom1`, set in `vercel.json`), and Vercel's CDN keeps the CSS and
   JavaScript near each visitor until the next deploy.
4. **Load the demo data (optional).** From your computer, in PowerShell:

   ```
   $env:DATABASE_URL = "<the Supabase address>"
   $env:FLASK_CONFIG = "development"
   uv run flask --app parent_notifier seed-demo
   ```

5. **Keep it private.** In the Vercel project, check **Settings → Deployment
   Protection**. Anyone who can open the site can also create an account.

Things that behave differently on Vercel:

- The first visit after a quiet spell is slower while a server starts.
- Sheets are limited to 4 MB, below Vercel's 4.5 MB request cap.
- The sign-in lockout counts attempts per server, so it is weaker than on one computer.
- Supabase pauses free projects after a week without use; resume it from the dashboard.

## Configuration

Settings come from environment variables, or from a git-ignored `.env` file in the
project folder.

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_CONFIG` | `development` | `development`, `testing` or `production` |
| `SECRET_KEY` | generated into `instance/` | Required in production |
| `DATABASE_URL` | `sqlite:///instance/parent_notifier.db` | SQLite or Postgres, such as a Supabase address |
| `APP_TIMEZONE` | `Asia/Kolkata` | Dates shown, and when the daily send limit resets |
| `MAX_UPLOAD_MB` | `5` (`4` on Vercel) | Largest sheet accepted |
| `SESSION_COOKIE_SECURE` | `false` (`true` on Vercel) | Set to `true` when served over HTTPS |
| `TRUST_PROXY` | `false` (`true` on Vercel) | Trust the proxy's forwarded address and https headers |
| `RUN_MIGRATIONS` | `true` | Set to `false` to skip migrations in the Vercel build |
| `COLLEGE_NAME` | G. H. Patel College of Engineering & Technology | Signs the English message |
| `COLLEGE_NAME_GU` | The same name in Gujarati | Signs the Gujarati message |
| `COLLEGE_SHORT_NAME` | `GCET` | Shown in the top bar |

The message wording lives in `message_templates/parent_report.en.txt` and
`parent_report.gu.txt`. Edits apply to the next message without a restart.

## Testing

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

`pytest` runs the unit and integration tests in parallel. The browser smoke tests are
kept separate because they need a Playwright browser:

```
uv run playwright install chromium
uv run pytest -m e2e
```

On Windows, `uv run pytest -m e2e --browser-channel msedge` uses the installed Edge
instead. To run the tests against Postgres, set `TEST_DATABASE_URL` to an empty
database and run them one at a time with `uv run pytest -n 0`.

CI runs lint, formatting and tests on Ubuntu and Windows, the tests again on
Postgres, and the smoke tests on Ubuntu.

| Layer | Covers |
|---|---|
| Unit | Sheet parsing, status rules, pacing, message rendering, phone numbers, undo |
| Integration | Every route: sign-in, ownership, forms, import review and undo, sending, pacing |
| End to end | Every page in light and dark, at desktop and phone width; the menus, an import, the message window, a send and the queue |

## Project layout

```
parent_notifier/
  core/             app setup: config, extensions, security headers, navigation, icons
  models/           database tables
  forms/            form validation
  routes/           pages and endpoints, grouped by area
  services/         business rules: imports, status, messaging, exports
  templates/        Jinja layouts, components and pages
  static/           CSS (cascade layers) and JavaScript modules, no build step
message_templates/  the parent message in English and Gujarati
migrations/         database migrations (Alembic)
samples/            fictional demo sheets
tests/              unit, integration and end-to-end tests
```

## Security and privacy

Parent Notifier holds students' records and parents' phone numbers, so it keeps them
close.

- **Data stays where you run it.** On a college computer everything is in one SQLite
  file; a test deployment on Vercel keeps it in your own Supabase database. The app
  makes no other outside calls; only the mentor's browser talks to WhatsApp Web.
- **Each mentor sees only their own classes.** Every query is scoped to the signed-in
  mentor, and anything else answers "not found".
- **Accounts.** Passwords are hashed with scrypt, repeated failed sign-ins are locked
  out for a while, and a one-time recovery code resets a forgotten password.
- **Web protections.** CSRF tokens on every form and request, a strict Content
  Security Policy with no inline scripts, and hardened cookies.
- **Uploads.** Size, type, row and column limits, checks against zip bombs and XML
  attacks, and nothing saved before review.
- **Downloads.** Spreadsheet formulas are neutralised, so a sheet can't run anything
  when opened.

Never commit real student or parent data. The demo and tests use fictional people and
numbers starting at +91 90000 00001.

## Roadmap

- [x] **0.1.0**: accounts, classes, sheet import with review and undo, the semester
  workspace, WhatsApp messaging with pacing
- [x] **0.2.0**: home workspace, light and dark themes, help page, browser smoke tests
- [ ] **1.0.0**: running on a shared college server (Waitress as a Windows service, a
  backup and restore guide), after college approval

Each release is described on the [Releases](https://github.com/Pruthil-21/parent-notifier/releases) page.

## Contributing

- Work on a short-lived branch and open a pull request against `main`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/),
  one logical change per commit, with its tests.
- The pre-commit hooks must pass: lint, formatting and the commit message format.

## License

No license has been chosen yet, so all rights are reserved for now.
