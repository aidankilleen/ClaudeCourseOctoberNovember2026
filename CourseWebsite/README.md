# Professional Training — brochure website

A one-page brochure site built with Flask and Jinja2. No database, no build tools,
no JavaScript — just Python, one HTML template and one CSS file.

## Files

| File | What it is |
|------|------------|
| `content.py` | **All the text on the site.** This is the only file you need to edit. |
| `app.py` | The Flask app: the page route and the API routes. |
| `templates/index.html` | The page layout. |
| `static/style.css` | The styling (colours are set at the top of the file). |
| `db.json` | The course records used by the API. |
| `db.py` | Reads and writes `db.json`. Nothing else touches that file. |
| `requirements.txt` | The one dependency, Flask. |

## Install

You need Python 3.12 or newer. From this folder:

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open <http://127.0.0.1:5000> in your browser. Press `Ctrl+C` in the terminal
to stop the server.

The server runs in debug mode, so when you save a change it reloads by itself —
just refresh the browser.

## Editing the content

Open `content.py`. Everything is a plain Python variable with a comment above it:

- `COMPANY` — company name and tagline. (The copyright year in the footer is not
  listed here: it comes from today's date, so it updates itself every January.)
- `NAV` — the links in the header
- `HERO` — the headline, tagline and button at the top of the page
- `ABOUT` — the About Us paragraph
- `COURSES` — the list of courses
- `BENEFITS` — the Why Choose Us points
- `TESTIMONIALS` — the client quotes
- `CONTACT` — email, phone and address

### Example: adding a course

Add another block to the `COURSES` list, keeping the same three keys:

```python
COURSES = [
    # ... the existing courses ...
    {
        "title": "Time Management",
        "description": "Prioritising, planning your week and protecting focus time.",
        "duration": "1 day",
    },
]
```

Save the file, refresh the browser, and the new course card appears. The same
works for `BENEFITS` and `TESTIMONIALS` — the page loops over whatever is in the
lists, so you can add or remove items freely.

### Tips

- Keep the quotes `"` and the commas `,` exactly where they are.
- A long piece of text can be split over several lines by wrapping it in
  brackets, as the existing entries do.
- If a nav link stops working, check that its `href` in `NAV` (for example
  `#courses`) still matches a section `id` in `templates/index.html`.

## The hero photo

`static/images/hero.jpg` is the background photo in the banner at the top of the page.

- Source: [Campaign Creators on Unsplash](https://unsplash.com/photos/man-standing-in-front-of-people-sitting-beside-table-with-laptop-computers-gMsnXqILjp4)
- Licence: the [Unsplash Licence](https://unsplash.com/license) — free to use commercially,
  no attribution required (crediting the photographer is appreciated but optional).

To swap it, save a new image as `static/images/hero.jpg` (around 1920px wide works well)
and refresh — no code change needed. To use a different filename, or to remove the photo
and go back to a plain colour, edit the `.hero` rule in `static/style.css`; the comment
above it explains both.

## The API

As well as the web page, the app serves the course records in `db.json` as JSON.
Anything you add, change or delete through the API is written straight back to
`db.json`, so it is still there after you restart the server.

| Method | Path | What it does |
|--------|------|--------------|
| `GET` | `/api/courses` | All records |
| `GET` | `/api/courses/<id>` | One record, or 404 |
| `POST` | `/api/courses` | Add a record. Returns 201 and the new record, including its id |
| `PUT` | `/api/courses/<id>` | Replace a record. All fields must be sent |
| `PATCH` | `/api/courses/<id>` | Change only the fields you send |
| `DELETE` | `/api/courses/<id>` | Remove a record. Returns 204 |

A record has three fields — `title`, `description` and `duration`. The `id` is
assigned by the server; sending one in the body has no effect. Any key that isn't
one of the three is ignored rather than stored.

```bash
curl http://127.0.0.1:5000/api/courses

curl -X POST http://127.0.0.1:5000/api/courses \
  -H "Content-Type: application/json" \
  -d '{"title":"Time Management","description":"Protecting focus time.","duration":"1 day"}'

curl -X PATCH http://127.0.0.1:5000/api/courses/6 \
  -H "Content-Type: application/json" -d '{"duration":"2 days"}'

curl -X DELETE http://127.0.0.1:5000/api/courses/6
```

A bad request answers 400 with a message saying what was wrong — a body that isn't
a JSON object, a `POST`/`PUT` missing a field, or a `PATCH` that would change
nothing. An id that doesn't exist answers 404; `PUT` will not create a record at an
id of your choosing.

Note that `db.json` and the `COURSES` list in `content.py` are two separate copies
of the same courses: the web page reads `content.py`, the API reads `db.json`. A
course added through the API will not appear on the page.

## Changing the look

Open `static/style.css`. The first block (`:root`) holds the colours, maximum page
width and corner rounding. Changing `--accent` there, for instance, restyles every
button, link and highlight on the page.
