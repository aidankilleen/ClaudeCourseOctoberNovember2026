# webcommentbook

A small website where visitors leave a comment and a rating out of five, and
read what everybody else wrote. It is written in Python with Flask, and keeps
its comments in a SQLite database file.

It is completely self-contained: it shares nothing with the other folders in
this repository and runs only on your own machine.

## Running it

From inside this folder, once:

```powershell
python -m venv venv                      # make a private place for the libraries
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python seed.py              # create the database with sample comments
```

Then, every time you want the site:

```powershell
venv\Scripts\python app.py
```

Open **http://127.0.0.1:5001** in a browser. Press `Ctrl+C` in the terminal to
stop it.

> The port is **5001**, not the usual 5000, so this can run at the same time as
> any other Flask site on this machine.

`seed.py` **wipes the database and starts again**, so only run it when you want
a clean slate. If you want different starting comments, edit the list at the
top of `seed.py` — that file is the record of what the site begins with.

## The three pages

| Address | What it is |
|---|---|
| `/` | Homepage: what the site is, how many comments there are, the average rating, and the three most recent |
| `/comments` | Every comment. `?sort=newest`, `?sort=oldest` or `?sort=rating` changes the order |
| `/comments/new` | The form for leaving a comment |

## What a comment is

| Field | Meaning |
|---|---|
| `id` | A number the database gives each comment. You never type this |
| `date` | When it was left, stored as ISO text such as `2026-11-03T14:05:00` |
| `name` | Who left it (up to 80 characters) |
| `comment` | What they said (up to 2000 characters) |
| `rating` | A whole number from 1 to 5, shown as stars |

## The REST web service

The same comments are available as JSON under `/api/comments`, so another
program can read and change them without touching the HTML.

| Request | What it does |
|---|---|
| `GET /api/comments` | All comments. Options: `?sort=`, `?min_rating=`, `?limit=`, `?offset=` |
| `GET /api/comments/3` | One comment, or 404 if there is no such id |
| `POST /api/comments` | Add one. Needs `name`, `comment`, `rating`; `date` optional |
| `PUT /api/comments/3` | Replace all the fields of a comment |
| `PATCH /api/comments/3` | Change only the fields you send |
| `DELETE /api/comments/3` | Remove it |

Status codes: `200` fine, `201` created, `204` deleted, `400` what you sent was
not valid, `404` no such comment.

Examples (the server must be running):

```bash
# read them all
curl http://127.0.0.1:5001/api/comments

# add one
curl -X POST http://127.0.0.1:5001/api/comments \
     -H "Content-Type: application/json" \
     -d '{"name":"Ann","comment":"Very good.","rating":5}'

# change just the rating of comment 3
curl -X PATCH http://127.0.0.1:5001/api/comments/3 \
     -H "Content-Type: application/json" \
     -d '{"rating":4}'

# delete comment 3
curl -X DELETE http://127.0.0.1:5001/api/comments/3
```

A rejected comment tells you exactly what was wrong:

```json
{
  "error": "The comment is not valid.",
  "details": ["Rating must be a whole number from 1 to 5."]
}
```

### Who is allowed to write

| Request | Needs a key? |
|---|---|
| `GET` | No — the comments are public, that is the point |
| `POST` | No — leaving a comment is the whole purpose, same as the form |
| `PUT`, `PATCH`, `DELETE` | **Yes** — an `X-API-Key` header |

The key comes from the environment variable `WEBCOMMENTBOOK_API_KEY`, read once
when the application starts. If it is not set, those three requests answer
**503** rather than going through: a forgotten setting can never accidentally
throw the site open.

Locally you usually will not set it, so `PUT`/`PATCH`/`DELETE` simply return
503 and the rest of the site works as normal. To try them:

```powershell
$env:WEBCOMMENTBOOK_API_KEY = "anything-local"   # before starting app.py
```

```bash
curl -X DELETE http://127.0.0.1:5001/api/comments/3 -H "X-API-Key: anything-local"
```

Without the header, or with the wrong value, you get **401**.

On the live server the key is set in the systemd service file, which only root
can read. It is never stored in this repository.

The same applies to `WEBCOMMENTBOOK_SECRET_KEY`, which Flask uses to sign the
session cookie. There is a development fallback in `app.py` so the site runs
locally with no setup; the server sets a real random one.

## The files

| File | What it holds |
|---|---|
| `app.py` | The web pages and the REST API — every address the site answers |
| `db.py` | All the SQL, and the validation rules shared by the form and the API |
| `schema.sql` | The single `comments` table |
| `seed.py` | Rebuilds the database with the sample comments |
| `templates/` | The HTML. `base.html` is the shared shell the others fill in |
| `static/style.css` | The whole look of the site, hand-written, no framework |
| `comments.db` | The database itself. Created by `seed.py`, not kept in git |

Anything to do with the database is in `db.py`, so the validation rules live in
one place and the form and the API can never disagree about what a valid
comment is. The SQL is written out using Python's built-in `sqlite3` module
rather than hidden behind a library, so you can read exactly what runs.
