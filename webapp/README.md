# The course website

A website whose content comes out of a database rather than being typed into
the HTML. Change a date or a price in the database and the page says something
different the next time anybody loads it. The same information is also
available as JSON, for programs rather than people.

Written in Python, using Flask. The database is SQLite, which is a single file
and needs nothing installed.

## Running it on your own machine

Once, to set up:

```bash
python -m venv venv
venv\Scripts\activate          # Windows. On a Mac or Linux: source venv/bin/activate
pip install -r requirements.txt
python seed.py                 # builds courses.db and fills it in
```

Then, every time you want to look at it:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. Leave it running while you work; it notices when
you change a file and reloads itself.

## Changing what the website says

**Course dates, prices and places** live in the database. Edit the `COURSES`
list at the top of `seed.py` and run `python seed.py` again. Refresh the page.

Running `seed.py` rebuilds the tables from scratch, so that file is the real
record of what the courses are. Anything added through the API is thrown away
the next time you run it.

**Everything else** — the headline, the three days, the two lists — lives in
`templates/index.html` and is ordinary HTML you can edit directly.

**How it looks** is `static/style.css`. The colours are all set in one block
at the top, so changing `--ink` changes the whole site.

## What each file is for

| File | What it does |
|---|---|
| `app.py` | The web addresses: what to send back for each one. Start here. |
| `db.py` | Every question asked of the database. Nothing else writes SQL. |
| `schema.sql` | The shape of the tables. |
| `seed.py` | Builds the database and fills it with the courses. |
| `templates/index.html` | The page, with gaps where the database values go. |
| `templates/404.html` | What people see at an address that does not exist. |
| `static/style.css` | How it all looks. |
| `courses.db` | The database itself. Not in git — it is data, not code. |

## The API

Reading is open to anybody:

```bash
curl http://127.0.0.1:5000/api/courses
curl http://127.0.0.1:5000/api/courses/1
curl http://127.0.0.1:5000/api/courses/1/sessions
curl "http://127.0.0.1:5000/api/sessions?from=today"
```

| Method | Address | Needs a key |
|---|---|---|
| GET | `/api/courses`, `/api/courses/<id>`, `/api/courses/<id>/sessions` | no |
| GET | `/api/sessions`, `/api/sessions/<id>` | no |
| POST | `/api/courses`, `/api/sessions` | yes |
| PUT | `/api/courses/<id>`, `/api/sessions/<id>` | yes |
| DELETE | `/api/courses/<id>`, `/api/sessions/<id>` | yes |

### Changing things through the API

Anything that changes the database needs a key, sent as an `X-API-Key` header.
The key is read from an environment variable, so it is never written down in
the code:

```bash
# Windows PowerShell
$env:AIDANK_API_KEY = "pick-something-long-and-random"
python app.py
```

```bash
curl -X POST http://127.0.0.1:5000/api/courses \
  -H "X-API-Key: pick-something-long-and-random" \
  -H "Content-Type: application/json" \
  -d '{"slug": "one-day-intro", "title": "A one-day introduction", "price_cents": 50000}'
```

If no key has been set, writing is refused entirely — the API answers 503
rather than letting anybody through. A missing setting must never mean "open".

## Two things worth knowing

**Prices are stored as whole cents.** 1,450 euro is stored as `145000`. A
computer cannot hold 14.50 exactly, so prices kept as decimals slowly drift;
whole numbers never do. The conversion back to euro happens in one place, in
`db.py`.

**Dates are stored as `2026-11-09`.** Written that way they sort correctly as
plain text, so "later than today" is a simple comparison. They are turned into
"9 to 11 November 2026" only when the page is drawn.
