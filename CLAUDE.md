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
| `webcommentbook/` | Flask + SQLite comment book with a REST API. **Deployed live** at https://aidank.aitrainingcourses.ie | no — see below |
| `webapp/` | Flask + SQLite course site with a REST API. Was the live site at https://aidank.aitrainingcourses.ie until 3 Nov 2026, when `webcommentbook/` replaced it. **No longer deployed** — kept as the rollback target | no — see below |
| `website/` | The hand-written single-page design `webapp/` was built from. Kept as the design reference and rollback target | no |
| `InvoiceProcessor/` | A Skill (`invoice-extractor`) plus sample PDFs to run it against | yes |
| `CoworkInvestigation/` | Loose documents and a standalone tkinter clock; artefacts of past exercises | no |
| `hello_world.py`, `website_prompt.txt` | A one-off script and the original prompt that produced `CourseWebsite/` | no |

`webcommentbook/`, `webapp/` and `CourseWebsite/` are **unrelated applications**. They share
no code and nothing should be copied between them. `webcommentbook/` was built from scratch
without reference to either of the others, and `webapp/` without reference to
`CourseWebsite/`. `webcommentbook/` and `webapp/` are on the same server but only one of
them is served at a time.

## Per-folder commands

`CourseWebsite/`, `webapp/` and `webcommentbook/` have dependencies and want their own
venvs; everything else runs on a bare Python 3.12+ interpreter.

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

# webcommentbook — from that folder, in its own venv. seed.py REBUILDS the database.
pip install -r requirements.txt
python seed.py                                  # creates/overwrites comments.db
python app.py                                   # http://127.0.0.1:5001, debug auto-reload

# webcommentbook — GET and POST are always open. PUT/PATCH/DELETE need this set
# before app.py starts, or they answer 503 by design
$env:WEBCOMMENTBOOK_API_KEY = "any-value-locally"   # PowerShell

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
- **`webcommentbook` is also a public site**, at https://aidank.aitrainingcourses.ie. See
  the section below before deploying to it.
- **`webcommentbook/seed.py` on the server destroys every comment visitors have left.** It
  drops the table and re-inserts the six samples. Unlike `webapp`, the live rows here are
  other people's words, not your own content — there is no copy of them anywhere else. Only
  run it on the server when you genuinely want the site emptied.
- **`webapp` is no longer served**, but it is still on the server, stopped and disabled, as
  the rollback target. Do not delete `/home/ptadmin/webapp` or its `courses.db`.
- **`webapp/seed.py` rebuilds the tables from scratch.** It is the record of truth for what
  the courses are, so a date added through the API survives only until the next seed. To
  make a change permanent, put it in `seed.py` — do not rely on an API write.
- **Never copy `courses.db` or `comments.db` to or from the server.** The server's copies are
  live data. Deploy the code and run `seed.py` there, or change rows through the API.
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

## Deploying `webcommentbook/`

Live at **https://aidank.aitrainingcourses.ie**. Treat edits as changes to a real site.

- `ssh ptadmin@40.113.35.220` — key-based, no password prompt. Hostname `ClaudeCodeVm3`.
  The key and user are already in `~/.ssh/config`.
- The app lives in `/home/ptadmin/webcommentbook`, the same layout as this folder, with its
  own venv at `venv/` and its SQLite database at `comments.db`.
- **gunicorn** serves `app:app` with 3 workers on `127.0.0.1:8002`, run by the systemd unit
  `aidank-webcommentbook.service`. (Port 8002, not 8001: the retired `webapp` unit is still
  bound to 8001 in its own unit file, so the two can never clash.)
- **nginx** terminates HTTPS (Let's Encrypt via Certbot, port 80 redirects to 443) and
  reverse-proxies to gunicorn. `/static/` is served straight from disk by nginx, not by
  the app, so a CSS change needs no restart.
- **The nginx config is `/etc/nginx/conf.d/aidank.conf`.** This server has no
  `sites-available`/`sites-enabled` directories — do not go looking for them.
- Two keys live in `Environment=` inside the unit file, which is mode 600 and root-only:
  `WEBCOMMENTBOOK_API_KEY` and `WEBCOMMENTBOOK_SECRET_KEY`. Read them with
  `sudo grep WEBCOMMENTBOOK /etc/systemd/system/aidank-webcommentbook.service`. They are
  never in the repository.
- **Who may write:** `GET` and `POST /api/comments` are open, so anyone can read the
  comments and leave one — that is the point of the site. `PUT`, `PATCH` and `DELETE`
  require an `X-API-Key` header, and answer 503 rather than opening up if the key is unset.

Deploying is copying the changed files up and restarting the service. Copy only what
changed, and never `comments.db`, the `venv/` or `__pycache__/` (the venv is Windows-built
and will not run on Linux):

```bash
scp webcommentbook/app.py webcommentbook/db.py ptadmin@40.113.35.220:~/webcommentbook/
scp webcommentbook/templates/index.html ptadmin@40.113.35.220:~/webcommentbook/templates/
scp webcommentbook/static/style.css     ptadmin@40.113.35.220:~/webcommentbook/static/
ssh ptadmin@40.113.35.220 'sudo systemctl restart aidank-webcommentbook'
```

A `.py` or template change needs the restart; a change to `static/` alone does not.
Changing `schema.sql` or `seed.py` means re-running `./venv/bin/python seed.py` on the
server, **which deletes every comment visitors have left**.

Verifying a deploy (a 200 does not prove the new content is being served):

```bash
curl -s https://aidank.aitrainingcourses.ie/ | grep "<some new text>"
curl -s https://aidank.aitrainingcourses.ie/api/comments | python -m json.tool
curl -s -o /dev/null -w "%{http_code}
" -X DELETE      https://aidank.aitrainingcourses.ie/api/comments/1   # must be 401, never 204
ssh ptadmin@40.113.35.220 'systemctl is-active aidank-webcommentbook'
ssh ptadmin@40.113.35.220 'sudo journalctl -u aidank-webcommentbook --since "2 minutes ago" --no-pager | tail'
```

If gunicorn fails to boot the site serves 502, and the journal has the traceback.

### Rolling back to `webapp`

`webapp` was the live site until 3 November 2026. Everything needed is still on the server:
`/home/ptadmin/webapp` with its `courses.db`, the `aidank-webapp.service` unit (stopped and
disabled, not removed), and `~/backups/aidank.conf.pre-commentbook` — the nginx config as it
was, pointing at port 8001 and `webapp/static`.

```bash
sudo cp ~/backups/aidank.conf.pre-commentbook /etc/nginx/conf.d/aidank.conf
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl enable --now aidank-webapp
sudo systemctl disable --now aidank-webcommentbook
```

`~/backups/` also holds `aidank.conf.pre-flask`, from further back, when the site was static
pages. `/var/www/aidank/` is still in place but is no longer served.

## Audience and register

Everything here is read by course delegates who are not necessarily programmers. Code in
`CourseWebsite/`, `webapp/` and `webcommentbook/` is commented to explain *why* in plain
language, and their READMEs are written for someone editing the content by hand. Match that register — keep the
explanatory comments rather than trimming them as redundant, and prefer the simple, obvious
construction over the clever one.

`webapp/` and `webcommentbook/` deliberately use the `sqlite3` module from the standard
library rather than an ORM, so that the SQL is visible on the page where it runs. Do not
"improve" either of them to SQLAlchemy without being asked.
