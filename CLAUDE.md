# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Teaching material for a Claude Code course (October–November 2026), not a product. It is
a git repository on branch `master` with a handful of commits and no remote, so there is
very little history to consult. The content is a set of unrelated exercise folders that
share only the course; they have no common build, dependency set, test suite or linter,
and nothing imports anything from a sibling folder.

Work almost always happens *inside* one folder. Two of them carry their own `CLAUDE.md`
with the real detail — **read it before touching that folder**, and prefer its instructions
to anything here:

| Folder | What it is | Own CLAUDE.md |
|---|---|---|
| `CourseWebsite/` | Flask brochure site + JSON-file REST API. **Deployed live** at https://aitrainingcourses.ie | yes — read it, especially the Deployment section, before any edit |
| `webapp/` | Flask + SQLite course site with a REST API. **Deployed live** at https://aidank.aitrainingcourses.ie | no — see below |
| `website/` | The hand-written single-page design `webapp/` was built from. Kept as the design reference and rollback target | no |
| `InvoiceProcessor/` | A Skill (`invoice-extractor`) plus sample PDFs to run it against | yes |
| `CoworkInvestigation/` | Loose documents and a standalone tkinter clock; artefacts of past exercises | no |
| `hello_world.py`, `website_prompt.txt` | A one-off script and the original prompt that produced `CourseWebsite/` | no |

`webapp/` and `CourseWebsite/` are **two unrelated sites on two different servers**. They
share no code and nothing should be copied between them. `webapp/` was deliberately built
without reference to `CourseWebsite/`.

## Per-folder commands

`CourseWebsite/` and `webapp/` have dependencies and want their own venvs; everything else
runs on a bare Python 3.12+ interpreter.

```bash
# CourseWebsite — from that folder, in its own venv
pip install -r requirements.txt
python app.py                                   # http://127.0.0.1:5000, debug auto-reload

# webapp — from that folder, in its own venv. seed.py REBUILDS the database.
pip install -r requirements.txt
python seed.py                                  # creates/overwrites courses.db
python app.py                                   # http://127.0.0.1:5000

# webapp — to exercise the write endpoints, the key must be set before app.py starts,
# or every write answers 503 by design
$env:AIDANK_API_KEY = "any-value-locally"       # PowerShell

# InvoiceProcessor — from that folder; the Skill writes invoice-output.{csv,json} here
python ".claude/skills/invoice-extractor/scripts/validate_output.py" invoice-output.json

# CoworkInvestigation — standalone GUI, no args
python CoworkInvestigation/pyclock/pyclock.py
```

There is no test suite, linter or build step anywhere in the repository. "Verifying" means
loading the page, calling the API, or running the Skill against the sample invoices — see
the folder's own `CLAUDE.md` for how.

## Things that bite

- **`CourseWebsite` is a public site.** Editing it is editing production; `db.json` on the
  server holds live API writes and must not be overwritten. The folder's `CLAUDE.md` has the
  deploy and rollback procedure — follow it rather than improvising scp commands.
- **`webapp` is also a public site**, at https://aidank.aitrainingcourses.ie. See the
  section below before deploying to it.
- **`webapp/seed.py` rebuilds the tables from scratch.** It is the record of truth for what
  the courses are, so a date added through the API survives only until the next seed. To
  make a change permanent, put it in `seed.py` — do not rely on an API write.
- **Never copy `courses.db` to or from the server.** The server's copy is live data. Deploy
  the code and run `seed.py` there, or change rows through the API.
- **`InvoiceProcessor` validates before it outputs.** A change to `SKILL.md` is checked by
  running it over all three (now five) PDFs in `invoices/`, which differ in layout and
  filename casing on purpose; `invoice-output.json` in that folder is the last run's result,
  overwritten each time.
- **Documents in `CoworkInvestigation/` are outputs, not sources.** `invoice_summary.md`,
  `receipt_summary.md` and the `.docx`/`.pdf` files were generated during exercises from the
  PDFs and images beside them; regenerate rather than hand-patch if they need to be right.
- The PDFs and images in `CoworkInvestigation/` and `InvoiceProcessor/invoices/` contain real
  supplier and invoice details. Treat them as the user's own data: they are inputs to
  exercises, not material to publish, upload or paste into anything outward-facing.

## Deploying `webapp/`

Live at **https://aidank.aitrainingcourses.ie**. Treat edits as changes to a real site.

- `ssh ptadmin@40.113.35.220` — key-based, no password prompt. Hostname `ClaudeCodeVm3`.
  The key and user are already in `~/.ssh/config`.
- The app lives in `/home/ptadmin/webapp`, the same layout as this folder, with its own
  venv at `venv/` and its SQLite database at `courses.db`.
- **gunicorn** serves `app:app` with 3 workers on `127.0.0.1:8001`, run by the systemd unit
  `aidank-webapp.service`.
- **nginx** terminates HTTPS (Let's Encrypt via Certbot, port 80 redirects to 443) and
  reverse-proxies to gunicorn. `/static/` is served straight from disk by nginx, not by
  the app, so a CSS change needs no restart.
- The API write key lives in `Environment=` inside the unit file, which is mode 600 and
  root-only. Read it with
  `sudo grep AIDANK_API_KEY /etc/systemd/system/aidank-webapp.service`. It is never in the
  repository, and if it is unset the write endpoints answer 503 rather than opening up.

Deploying is copying the changed files up and restarting the service. Copy only what
changed, and never `courses.db`, the `venv/` or `__pycache__/`:

```bash
scp webapp/app.py webapp/db.py ptadmin@40.113.35.220:~/webapp/
scp webapp/templates/index.html ptadmin@40.113.35.220:~/webapp/templates/
scp webapp/static/style.css     ptadmin@40.113.35.220:~/webapp/static/
ssh ptadmin@40.113.35.220 'sudo systemctl restart aidank-webapp'
```

A `.py` or template change needs the restart; a change to `static/` alone does not.
Changing `schema.sql` or `seed.py` means re-running `./venv/bin/python seed.py` on the
server, **which discards every row added through the API**.

Verifying a deploy (a 200 does not prove the new content is being served):

```bash
curl -s https://aidank.aitrainingcourses.ie/ | grep "<some new text>"
curl -s https://aidank.aitrainingcourses.ie/api/sessions | python -m json.tool
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
     https://aidank.aitrainingcourses.ie/api/courses      # must be 401, never 201
ssh ptadmin@40.113.35.220 'systemctl is-active aidank-webapp'
ssh ptadmin@40.113.35.220 'sudo journalctl -u aidank-webapp --since "2 minutes ago" --no-pager | tail'
```

If gunicorn fails to boot the site serves 502, and the journal has the traceback.
Rolling back: `/home/ptadmin/backups/` holds `aidank.conf.pre-flask` (the nginx config
from when this was a static site) and the previous static pages. `/var/www/aidank/` is
still in place but is no longer served.

## Audience and register

Everything here is read by course delegates who are not necessarily programmers. Code in
`CourseWebsite/` and `webapp/` is commented to explain *why* in plain language, and both
READMEs are written for someone editing the content by hand. Match that register — keep the
explanatory comments rather than trimming them as redundant, and prefer the simple, obvious
construction over the clever one.

`webapp/` deliberately uses the `sqlite3` module from the standard library rather than an
ORM, so that the SQL is visible on the page where it runs. Do not "improve" it to
SQLAlchemy without being asked.
