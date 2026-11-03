"""webcommentbook - a small guest book where visitors leave a comment and a
rating out of five.

There are two halves to this file:

  1. Three ordinary web pages, which return HTML for a person in a browser:
     the homepage, the list of comments, and the form for adding one.

  2. A REST API under /api/comments, which returns JSON for a program. It is
     what lets another application read, add, change or delete comments
     without going anywhere near the HTML.

Both halves use the same functions in db.py, including the same validation, so
a comment added through the API is checked exactly as strictly as one typed
into the form.

Run it with:  python app.py    then open http://127.0.0.1:5001
"""

import os

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

import db

app = Flask(__name__)

# Flask needs a secret key before it will use flash() - the one-off "thanks,
# your comment was added" message shown after a redirect. The fallback below
# keeps "python app.py" working on your own machine with no setup; the public
# server sets WEBCOMMENTBOOK_SECRET_KEY to a real random value, because a key
# that anyone can read in this file is no secret at all.
app.secret_key = os.environ.get(
    "WEBCOMMENTBOOK_SECRET_KEY", "webcommentbook-development-key"
)

# The key that permits changing or deleting existing comments through the API.
# It is read once, when the application starts. It is never written down in
# this project - on the server it comes from the systemd service file, which
# only root can read.
API_KEY = os.environ.get("WEBCOMMENTBOOK_API_KEY")

# The port is 5001 rather than the usual 5000 so that this application can run
# at the same time as anything else on this machine that already uses 5000.
PORT = 5001


# ---------------------------------------------------------------------------
# A small helper used by the templates
# ---------------------------------------------------------------------------

@app.template_filter("stars")
def stars_filter(rating):
    """Turn the number 4 into the string that shows four filled stars.

    Registering this as a template filter means a template can simply write
    {{ comment.rating|stars }} rather than repeating the logic each time.
    """
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return ""
    rating = max(0, min(5, rating))
    return "★" * rating + "☆" * (5 - rating)


@app.template_filter("friendly_date")
def friendly_date_filter(value):
    """Show the stored ISO date as something easier to read.

    Dates are stored as text like "2026-11-03T14:05:00". We show the date part
    and, when there is one, the time to the minute.
    """
    text = str(value or "")
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        return date_part + " at " + time_part[:5]
    return text


# ---------------------------------------------------------------------------
# The three web pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """The homepage: what this site is, plus a couple of headline numbers."""
    return render_template(
        "index.html",
        total=db.count_comments(),
        average=db.average_rating(),
        latest=db.list_comments(sort="newest", limit=3),
    )


@app.route("/comments")
def comments_page():
    """Every comment, newest first unless a different sort was asked for."""
    # Anything unrecognised in ?sort= quietly falls back to "newest" - a
    # mistyped query string should not produce an error page.
    sort = request.args.get("sort", "newest")
    if sort not in db.SORT_ORDERS:
        sort = "newest"

    return render_template(
        "comments.html",
        comments=db.list_comments(sort=sort),
        sort=sort,
    )


@app.route("/comments/new", methods=["GET", "POST"])
def add_comment_page():
    """Show the "leave a comment" form, and handle it when it is submitted."""
    if request.method == "GET":
        # An empty form, with no errors and nothing filled in yet.
        return render_template("add_comment.html", errors=[], values={})

    # request.form holds what the browser sent. We hand it straight to the same
    # validator the API uses, so the rules cannot differ between the two.
    submitted = {
        "name": request.form.get("name", ""),
        "comment": request.form.get("comment", ""),
        "rating": request.form.get("rating", ""),
    }
    cleaned, errors = db.validate_comment(submitted)

    if errors:
        # Show the form again with the problems listed and the values the
        # person typed still in place, so nothing has to be retyped.
        return render_template("add_comment.html", errors=errors, values=submitted), 400

    db.create_comment(cleaned)

    # Redirect after a successful POST so that refreshing the page afterwards
    # does not offer to submit the comment a second time.
    flash("Thank you - your comment has been added.")
    return redirect(url_for("comments_page"))


# ---------------------------------------------------------------------------
# The REST API
# ---------------------------------------------------------------------------
#
# Every route below returns JSON, never HTML, and uses the HTTP status code to
# say what happened:
#
#   200 OK          here is what you asked for
#   201 Created     a new comment was created
#   204 No Content  it was deleted, there is nothing to send back
#   400 Bad Request what you sent was not a valid comment
#   404 Not Found   there is no comment with that id
#
# The write endpoints are open: anyone who can reach the server can change the
# comments. That is intentional for a site that runs on your own machine for
# teaching. Before putting this anywhere public, the write endpoints would need
# a key or a login.


def json_error(message, status, details=None):
    """Build an error response in the one shape the whole API uses."""
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def require_api_key():
    """Check the X-API-Key header. Returns None when the caller may proceed.

    Which requests need a key, and why:

      GET     open  - the comments are public, that is the point of the site.
      POST    open  - a visitor leaving a comment is the whole purpose. It is
                      the same thing the form on the website does.
      PUT     key   - these three change or destroy a comment somebody else
      PATCH   key     left. Without a key, anyone who found the address could
      DELETE  key     quietly rewrite the page or empty it in a few seconds.

    If no key is configured at all, these requests are refused rather than
    allowed. Failing closed means a forgotten setting can never silently throw
    the site open.
    """
    if not API_KEY:
        return json_error(
            "This endpoint is not available: the server has no API key configured.",
            503,
        )
    if request.headers.get("X-API-Key") != API_KEY:
        return json_error(
            "A valid X-API-Key header is required to change or delete a comment.",
            401,
        )
    return None


def request_json():
    """Read the JSON body of a request, or (None, error_message).

    silent=True stops Flask raising on a malformed body so that we can answer
    with a tidy JSON message instead of an HTML error page.
    """
    data = request.get_json(silent=True)
    if data is None:
        return None, "Expected a JSON body with Content-Type: application/json."
    if not isinstance(data, dict):
        return None, "Expected a JSON object, for example {\"name\": \"Ann\"}."
    return data, None


@app.route("/api/comments", methods=["GET"])
def api_list_comments():
    """GET /api/comments - every comment, with optional filtering and paging.

    Query string options: ?sort=newest|oldest|rating, ?min_rating=, ?limit=,
    ?offset=
    """
    sort = request.args.get("sort", "newest")
    if sort not in db.SORT_ORDERS:
        return json_error(
            "sort must be one of: " + ", ".join(sorted(db.SORT_ORDERS)), 400
        )

    # Each of these is optional, and each must be a whole number if present.
    numbers = {}
    for field in ("min_rating", "limit", "offset"):
        raw = request.args.get(field)
        if raw is None or raw.strip() == "":
            numbers[field] = None
            continue
        try:
            numbers[field] = int(raw)
        except ValueError:
            return json_error(field + " must be a whole number.", 400)
        if numbers[field] < 0:
            return json_error(field + " cannot be negative.", 400)

    comments = db.list_comments(
        sort=sort,
        min_rating=numbers["min_rating"],
        limit=numbers["limit"],
        offset=numbers["offset"] or 0,
    )
    return jsonify({"count": len(comments), "comments": comments})


@app.route("/api/comments/<int:comment_id>", methods=["GET"])
def api_get_comment(comment_id):
    """GET /api/comments/5 - one comment."""
    comment = db.get_comment(comment_id)
    if comment is None:
        return json_error("No comment with id %d." % comment_id, 404)
    return jsonify(comment)


@app.route("/api/comments", methods=["POST"])
def api_create_comment():
    """POST /api/comments - add a comment.

    The body needs name, comment and rating. The date is optional; without one
    the comment is stamped with the current time.
    """
    data, problem = request_json()
    if problem:
        return json_error(problem, 400)

    cleaned, errors = db.validate_comment(data)
    if errors:
        return json_error("The comment is not valid.", 400, errors)

    created = db.create_comment(cleaned)

    # 201 Created, with a Location header pointing at the new comment - that is
    # how a REST client finds out where the thing it just made now lives.
    response = jsonify(created)
    response.status_code = 201
    response.headers["Location"] = url_for(
        "api_get_comment", comment_id=created["id"]
    )
    return response


@app.route("/api/comments/<int:comment_id>", methods=["PUT"])
def api_replace_comment(comment_id):
    """PUT /api/comments/5 - replace every field of a comment.

    Because this is a replacement rather than a tweak, name, comment and
    rating must all be supplied. Use PATCH to change just one of them.

    Needs an X-API-Key header.
    """
    refused = require_api_key()
    if refused:
        return refused

    data, problem = request_json()
    if problem:
        return json_error(problem, 400)

    cleaned, errors = db.validate_comment(data)
    if errors:
        return json_error("The comment is not valid.", 400, errors)

    updated = db.replace_comment(comment_id, cleaned)
    if updated is None:
        return json_error("No comment with id %d." % comment_id, 404)
    return jsonify(updated)


@app.route("/api/comments/<int:comment_id>", methods=["PATCH"])
def api_update_comment(comment_id):
    """PATCH /api/comments/5 - change only the fields you send.

    Needs an X-API-Key header.
    """
    refused = require_api_key()
    if refused:
        return refused

    data, problem = request_json()
    if problem:
        return json_error(problem, 400)

    cleaned, errors = db.validate_comment(data, partial=True)
    if errors:
        return json_error("The comment is not valid.", 400, errors)
    if not cleaned:
        return json_error(
            "Send at least one of: name, comment, rating, date.", 400
        )

    updated = db.update_comment(comment_id, cleaned)
    if updated is None:
        return json_error("No comment with id %d." % comment_id, 404)
    return jsonify(updated)


@app.route("/api/comments/<int:comment_id>", methods=["DELETE"])
def api_delete_comment(comment_id):
    """DELETE /api/comments/5 - remove a comment for good.

    Needs an X-API-Key header.
    """
    refused = require_api_key()
    if refused:
        return refused

    if not db.delete_comment(comment_id):
        return json_error("No comment with id %d." % comment_id, 404)
    # 204 means "done, and there is deliberately no body to send back".
    return "", 204


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def handle_not_found(error):
    """A missing address: JSON under /api/, an ordinary page everywhere else."""
    if request.path.startswith("/api/"):
        return json_error("No such endpoint: " + request.path, 404)
    return render_template("error.html", code=404,
                           message="That page does not exist."), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    """The right address but the wrong verb, for example GET on a POST-only route."""
    if request.path.startswith("/api/"):
        return json_error(
            "The %s method is not allowed on %s." % (request.method, request.path), 405
        )
    return render_template("error.html", code=405,
                           message="That request is not allowed here."), 405


@app.errorhandler(500)
def handle_server_error(error):
    """Something broke on our side."""
    if request.path.startswith("/api/"):
        return json_error("Something went wrong on the server.", 500)
    return render_template("error.html", code=500,
                           message="Something went wrong on the server."), 500


if __name__ == "__main__":
    # debug=True reloads the server whenever a file is saved and shows a full
    # explanation in the browser when something goes wrong. Both are helpful
    # while learning and both must be off on a public site.
    app.run(host="127.0.0.1", port=PORT, debug=True)
