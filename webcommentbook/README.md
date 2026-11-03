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
top of `seed.py` — that file is the record of what the site begins with. It also
creates the moderator account `admin` with the password `admin`, which is fine
on your own machine and nowhere else.

## The pages

| Address | What it is |
|---|---|
| `/` | Homepage: what the site is, how many comments there are, the average rating, and the three most recent |
| `/comments` | Every comment. `?sort=newest`, `?sort=oldest` or `?sort=rating` changes the order |
| `/comments/new` | The form for leaving a comment |
| `/admin/login` | Where a moderator signs in |
| `/admin` | The moderator's grid of every comment, with a search box and a filter |

## Moderating the comments

Sign in at `/admin/login` and you get a table of every comment with two buttons
on each row.

**Block** hides a comment from visitors. The comment is not deleted: it keeps
its place on the page, and where the words were, visitors read *"This comment
was removed by a moderator."* The text is held back from the API as well, so
there is no way round it. Block it again — the button now says **Unblock** —
and the comment comes back exactly as it was. A blocked comment is also left
out of the two figures on the homepage.

**Delete** removes the comment from the database for good. It asks first,
because there is no undo. If you are not certain, block it instead.

There is deliberately **no way to edit the text of a comment**. A moderator can
leave it, hide it, or remove it, so that anything on the site is either the
visitor's own words or plainly marked as taken down.

The search box matches a word in a name or in a comment, and the drop-downs
filter by status and change the order. All three are an ordinary form: pressing
Search just reloads the page with `?q=&status=&sort=` on the end, which means
the address bar always describes what you are looking at and can be bookmarked.

### Moderator accounts

Accounts live in the `admins` table. What is stored is never the password
itself, only a one-way hash of it, so a copy of the database does not hand
anybody the account — and nothing can read a forgotten password back out.

To add a moderator, or to give an existing one a new password:

```powershell
venv\Scripts\python create_admin.py              # asks for a username and a password
venv\Scripts\python create_admin.py alice        # asks for alice's password only
```

The password is typed invisibly and asked for twice, and must be at least eight
characters.

**Use `create_admin.py`, not `seed.py`, on a site that is already running.**
`create_admin.py` touches only the `admins` table; `seed.py` throws every
comment away.

## What a comment is

| Field | Meaning |
|---|---|
| `id` | A number the database gives each comment. You never type this |
| `date` | When it was left, stored as ISO text such as `2026-11-03T14:05:00` |
| `name` | Who left it (up to 80 characters) |
| `comment` | What they said (up to 2000 characters) |
| `rating` | A whole number from 1 to 5, shown as stars |
| `blocked` | `0` normally, `1` if a moderator has hidden it. You never type this either |

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
not valid, `401` you did not send the key, `404` no such comment, `503` the
server has no key configured.

The API never gives out the words of a blocked comment either — it is exactly
as public as the page is. You get the same "removed by a moderator" text, and
`blocked` set to `1`. Nor can the API hide or show a comment: `PATCH` quietly
ignores a `blocked` field, because moderating is something a signed-in person
does on `/admin`.

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
session cookie — the cookie that remembers a moderator has signed in, as well as
the one-off "thank you" message. A visitor cannot edit a signed cookie and make
themselves an administrator. There is a development fallback in `app.py` so the
site runs locally with no setup; the server sets a real random one.

On a site served over HTTPS, set `WEBCOMMENTBOOK_HTTPS=1` as well. That tells
the application to mark the session cookie as secure, so a browser will never
send it over an unencrypted connection.

## The files

| File | What it holds |
|---|---|
| `app.py` | The web pages and the REST API — every address the site answers |
| `db.py` | All the SQL, and the validation rules shared by the form and the API |
| `schema.sql` | The `comments` and `admins` tables, used when building from scratch |
| `seed.py` | Rebuilds the database with the sample comments and a default moderator |
| `create_admin.py` | Adds a moderator, or resets a password, leaving the comments alone |
| `templates/` | The HTML. `base.html` is the shared shell the others fill in |
| `static/style.css` | The whole look of the site, hand-written, no framework |
| `comments.db` | The database itself. Created by `seed.py`, not kept in git |

A database that already exists is never rebuilt from `schema.sql`. When the
application starts it calls `ensure_schema()` in `db.py`, which adds a missing
column or table and leaves every row where it is — that is how the live site
gained its `blocked` column without losing a single comment.

Anything to do with the database is in `db.py`, so the validation rules live in
one place and the form and the API can never disagree about what a valid
comment is. The SQL is written out using Python's built-in `sqlite3` module
rather than hidden behind a library, so you can read exactly what runs.
