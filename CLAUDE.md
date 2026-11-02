# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Teaching material for a Claude Code course (October–November 2026), not a product. It is
a git repository on branch `master` with **no commits yet** and no remote — so there is no
history to consult, and nothing is version-controlled until someone commits. The content is
a set of unrelated exercise folders that share only the course; they have no common build,
dependency set, test suite or linter, and nothing imports anything from a sibling folder.

Work almost always happens *inside* one folder. Two of them carry their own `CLAUDE.md`
with the real detail — **read it before touching that folder**, and prefer its instructions
to anything here:

| Folder | What it is | Own CLAUDE.md |
|---|---|---|
| `CourseWebsite/` | Flask brochure site + JSON-file REST API. **Deployed live** at https://aitrainingcourses.ie | yes — read it, especially the Deployment section, before any edit |
| `InvoiceProcessor/` | A Skill (`invoice-extractor`) plus sample PDFs to run it against | yes |
| `CoworkInvestigation/` | Loose documents and a standalone tkinter clock; artefacts of past exercises | no |
| `hello_world.py`, `website_prompt.txt` | A one-off script and the original prompt that produced `CourseWebsite/` | no |

## Per-folder commands

Only `CourseWebsite/` has a dependency (`Flask>=3.0`); everything else runs on a bare
Python 3.12+ interpreter.

```bash
# CourseWebsite — from that folder, in its own venv
pip install -r requirements.txt
python app.py                                   # http://127.0.0.1:5000, debug auto-reload

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

## Audience and register

Everything here is read by course delegates who are not necessarily programmers. Code in
`CourseWebsite/` is commented to explain *why* in plain language, and its README is written
for someone editing `content.py` by hand. Match that register — keep the explanatory
comments rather than trimming them as redundant, and prefer the simple, obvious construction
over the clever one.
