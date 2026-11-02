# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page brochure site for a fictional training company ("Professional Training"),
plus a JSON-file-backed REST API over the same courses. Teaching material for a Claude
Code course. Flask + Jinja2 only: no database, no build step, no JavaScript, no test
suite. Python 3.12+. The content is fictional but the site is live — see
**Deployment** before changing anything that will be pushed.

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell/cmd); source .venv/bin/activate elsewhere
pip install -r requirements.txt
python app.py                     # http://127.0.0.1:5000, debug=True (auto-reload)
```

There is no test suite, linter or build. Verifying the **page** means loading it and
looking at it. Verifying the **API** means calling it — and since every write lands in
`db.json`, point `db.DB_PATH` at a throwaway copy first rather than editing the real
file as a side effect of testing:

```python
# python -c "..." — no server needed, Flask's test client calls the routes directly.
from pathlib import Path
import tempfile, shutil, db, app

tmp = Path(tempfile.mkdtemp())
shutil.copy(db.DB_PATH, tmp / "db.json")
db.DB_PATH = tmp / "db.json"          # must be set before the first request

c = app.app.test_client()
print(c.post("/api/courses", json={"title": "T", "description": "D", "duration": "1 day"}).get_json())
```

## Architecture

Content and presentation are deliberately kept apart, and that separation is the point
of the project — keep it intact when editing.

### The website

- `content.py` — every piece of user-visible text, as plain module-level Python
  dicts/lists (`COMPANY`, `NAV`, `HERO`, `ABOUT`, `COURSES`, `BENEFITS`,
  `TESTIMONIALS`, `CONTACT`). Content changes belong here, not in the template.
- `app.py` — the page route (`/`) imports `content` as a module and passes it to the
  template as `c`, plus `year` from `date.today()` (the footer year is deliberately
  not stored in `content.py`).
- `templates/index.html` — the whole page. Sections loop over the lists in `c`, so
  adding an item to `COURSES`/`BENEFITS`/`TESTIMONIALS` needs no template change.
  Adding a *new kind* of section does.
- `static/style.css` — all styling. Colours, `--max-width`, `--gap` and `--radius`
  live in the `:root` block at the top; restyle through those tokens rather than
  hard-coding values further down.

Constraints that follow:

- A dict in a content list must keep the keys the template reads (a course needs
  `title`, `description`, `duration`).
- `HERO["offer"]` is the one optional key: the template wraps the badge in
  `{% if c.HERO.offer %}`, so deleting that line removes the promotional pill and
  leaves the rest of the hero alone. Its styling is `.hero-offer` in `style.css`.
- Each `NAV` entry's `href` (`#about`, `#courses`, …) must match a `<section id=...>`
  in `index.html`; they break silently if they drift.
- The hero background image is referenced from the `.hero` rule in `style.css` as
  `static/images/hero.jpg`, not from the template.

### The API

Same split: `db.py` owns the storage, `app.py` owns the HTTP.

- `db.json` — a plain JSON array of course records, each an integer `id` plus the keys
  in `db.FIELDS`. Hand-editable; re-read on every call, so edits apply immediately.
- `db.py` — the only module that opens `db.json`. Routes call `read_all`, `read_one`,
  `create`, `update`, `delete` and never import `json` themselves. `_write_all` writes
  a temp file and `os.replace`s it into place, so an interrupted write leaves the old
  file rather than a truncated one.
- Routes: `GET`/`POST` on `/api/courses`, `GET`/`PUT`/`PATCH`/`DELETE` on
  `/api/courses/<int:course_id>`. `db.update(..., replace=True)` is PUT; the default
  merge is PATCH. PUT will not create at a caller-chosen id — a missing id is 404.
- `_fields_from_request(required)` does all request validation and returns a
  `(fields, error)` pair — check `error` first, it is a finished response. `_not_found`
  is the shared 404.
- `id` is server-assigned: `db.update` sets it last, so a body containing one cannot
  move a record. Unknown keys are dropped by `db.fields_only`, never rejected — except
  a PATCH of *only* unknown keys, which is a 400 rather than a silent no-op.

To add a field to a course: add it to `db.FIELDS`, and to the existing records in
`db.json` if `PUT` callers will be required to send it.

### Where the two halves meet (they don't)

`db.json` and `content.COURSES` are independent copies of the same courses — the page
renders `content.py`, the API serves `db.json`. A course added via `POST` does not
appear on the website. Unifying them means pointing the courses section at
`db.read_all()` in the page route and template; it has been offered and not taken, so
don't do it unasked.

## Deployment

This project is not only teaching material — it is deployed and publicly reachable at
**https://aitrainingcourses.ie** (and `www.`). Treat edits as changes to a real site.

The server:

- `ssh ptadmin@172.205.113.37` — key-based, no password prompt. Hostname `ClaudeCodeVm2`.
- The site lives in `/home/ptadmin/CourseWebsite`, the same layout as this folder.
- **gunicorn** serves `app:app` with 3 workers on `127.0.0.1:8000`, run by the systemd
  unit `coursewebsite.service` from the venv at `~/CourseWebsite/venv`.
- **nginx** reverse-proxies to it and terminates HTTPS (Let's Encrypt, managed by
  Certbot; port 80 redirects to 443).
- `ptadmin` has passwordless sudo, which is what makes the restart below work.

There is no git remote, no CI and no build step on the server: deploying is copying the
changed files up and restarting the service. Copy only the files you changed.

```bash
# From the project root. Back up what you are about to overwrite, so a bad deploy
# can be undone without rebuilding anything.
ssh ptadmin@172.205.113.37 'cd ~/CourseWebsite && mkdir -p ~/backups/<change-name>/templates ~/backups/<change-name>/static && cp content.py ~/backups/<change-name>/ && cp templates/index.html ~/backups/<change-name>/templates/ && cp static/style.css ~/backups/<change-name>/static/'

scp content.py          ptadmin@172.205.113.37:~/CourseWebsite/
scp templates/index.html ptadmin@172.205.113.37:~/CourseWebsite/templates/
scp static/style.css     ptadmin@172.205.113.37:~/CourseWebsite/static/

ssh ptadmin@172.205.113.37 'sudo systemctl restart coursewebsite'
```

`.py` and template changes need the restart; a change to `static/` alone does not, but
restarting anyway is harmless. Rolling back is copying the backup over the live files
and restarting again.

**Never `scp` `db.json` unless that is explicitly the task.** It is live data: the API
writes to it on the server, so the server's copy drifts from this one, and overwriting
it silently discards every course added through the API. The same goes for `scp -r` of
the whole folder — it would take `db.json` and the server's `venv` with it.

Verifying a deploy (do all three — a 200 does not prove the new content is being served):

```bash
# 1. the files really arrived: compare against local hashes
ssh ptadmin@172.205.113.37 'cd ~/CourseWebsite && md5sum content.py templates/index.html static/style.css'
# 2. the service came back up and the page serves the change
ssh ptadmin@172.205.113.37 'systemctl is-active coursewebsite; curl -s -w "http %{http_code}\n" https://aitrainingcourses.ie/ | grep -o "<some new text>"'
# 3. nothing blew up at boot
ssh ptadmin@172.205.113.37 'sudo journalctl -u coursewebsite --since "2 minutes ago" --no-pager | tail'
```

If gunicorn fails to boot (a syntax error in `content.py`, say), the unit keeps
restarting and the site serves a 502 — the journal is where the traceback is.

Render the page locally and look at it before uploading. Because changes are public the
moment the service restarts, confirm the file list with the user before each deploy
rather than pushing on your own initiative, and tell them afterwards what to check in a
browser: these checks prove the HTML and CSS are being served, not that the result looks
right.

## Known limits

Deliberate, given the teaching purpose — don't "fix" them unprompted:

- Writes are not locked. The dev server is threaded, so two overlapping writes can lose
  one. The atomic replace prevents a corrupt file, not a lost update.
- `_next_id` is `max(id) + 1`, so deleting the newest record frees its id for reuse.
- No auth, no pagination, no rate limiting on the API.

## Audience

The README is written for non-programmers who will edit `content.py` by hand. Code
comments throughout explain *why* in plain language and at that level — match that
register rather than stripping the comments as redundant.
