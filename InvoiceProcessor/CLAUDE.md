# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A teaching sandbox for the Claude Code course (October–November 2026), not an application.
The deliverable is a **Skill** and the sample data used to exercise it. There is no package
manifest, build system or test suite, and the only Python here is the Skill's own validator,
which runs on a bare interpreter with no dependencies.

- `.claude/skills/invoice-extractor/SKILL.md` — the Skill under development
- `.claude/skills/invoice-extractor/scripts/validate_output.py` — the structural validator
  the Skill is required to run before showing any result
- `invoices/` — five sample PDFs used as input
- `invoice-output.json` — the last run's output, overwritten on every run. It is a scratch
  artefact, not a source file; never hand-edit it to make a run look right.

The repository root is one level up (`..`), which is a git repo with no commits yet. Nothing
here is version-controlled until someone commits, so an overwritten `SKILL.md` is gone.

## Exercising the Skill

Invoke it via the Skill tool as `invoice-extractor` (that is the frontmatter `name`; the
directory name is incidental). It takes a file *or* a folder plus an optional `csv`/`json`
format, defaulting to CSV. Reading the PDFs is done with the Read tool, which renders them
directly — no extraction library is involved.

The five samples are the de facto regression set and differ deliberately, so a change to
`SKILL.md` is checked against **all** of them, not just one:

| File | Why it is in the set |
|---|---|
| `invoice1.pdf` | A normal VAT invoice (Microsoft Ireland) |
| `Invoice2.pdf` | Capitalised filename; VAT number present but no VAT line |
| `invoice3.pdf` | VAT number printed inconsistently in header vs footer |
| `AK20260001- Invoice - ClaudeCode Course.pdf` | Spaces in filename; total disagrees with the line items |
| `AK20260002- Invoice - ClaudeCode Course 2.pdf` | Near-identical to the above, but dated `31/04/2026` — a well-formed impossible date |

The last two exist to prove the `errors` field works. The expected behaviour is that the
Skill *reports* those problems in `errors` and still produces valid output — it must not
silently correct them, and the validator deliberately accepts `31/04/2026` so that such a
date lands in `errors` rather than failing the run.

## The validate-before-output loop

`SKILL.md` requires every run to write its output to `invoice-output.csv` / `.json` in the
working directory and then validate it before anything is shown to the user:

```bash
python ".claude/skills/invoice-extractor/scripts/validate_output.py" invoice-output.json
# add --format csv|json when the extension does not match
```

Exit 0 = valid, 1 = `ERROR:` lines, 2 = missing or unparseable. `WARN:` lines (empty invoice
number, supplier or date) do not fail the run. The validator checks **structure only** —
field names and order, `sequenceNo` running 1..n, `dd/mm/yyyy` dates, two-decimal numbers.
It cannot tell whether a value matches the invoice, so a green run is not a correct run:
read the PDFs back when a value looks wrong, rather than reformatting until it passes.

Changing the output shape means changing `FIELDS` in `validate_output.py` and the CSV header
and JSON example in `SKILL.md` together; they are three copies of the same contract and the
validator rejects unexpected JSON keys outright.

## Editing SKILL.md

The frontmatter `name` and `description` are what Claude matches on to decide whether to
load the Skill, so editing `description` changes *triggering*, not behaviour — keep it
concrete about invoices and extraction. The body is the instruction set that loads once
triggered.

Much of that body is accumulated tuning against the samples, not arbitrary prose: the
EUR-for-Irish-suppliers assumption, "no VAT on training", and the instruction not to note
things that are correct all exist to suppress noise that earlier runs produced. The HTML
comment above the VAT paragraph records why it is there. Keep that convention when adding a
rule for the same reason, and treat removing one as a behaviour change to re-run the set
against.

## Handling the data

The PDFs are real invoices with real supplier and customer details. They are course inputs:
do not publish them, upload them to an external service, or paste their contents anywhere
outward-facing.
