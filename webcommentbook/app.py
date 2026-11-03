"""webcommentbook - a small guest book where visitors leave a comment and a
rating out of five.

There are three parts to this file:

  1. Ordinary web pages, which return HTML for a person in a browser: the
     homepage, the list of comments, and the form for adding one.

  2. A REST API under /api/comments, which returns JSON for a program. It is
     what lets another application read, add, change or delete comments
     without going anywhere near the HTML.

  3. The moderator's pages under /admin, where somebody who has logged in can
     see every comment in a grid and either block one - which hides the words
     from visitors but keeps the comment in place - or delete it outright.
     There is deliberately no way to edit the text of somebody else's comment.

Both halves use the same functions in db.py, including the same validation, so
a comment added through the API is checked exactly as strictly as one typed
into the form.

Run it with:  python app.py    then open http://127.0.0.1:5001
"""

import hmac
import os
import secrets

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

import db

app = Flask(__name__)

# Flask needs a secret key before it will use flash() - the one-off "thanks,
# your comment was added" message shown after a redirect - and before it will
# use the session, which is how the site remembers that a moderator has logged
# in. Both are stored in a cookie that Flask signs with this key, so that a
# visitor cannot simply edit the cookie and declare themselves an
# administrator. The fallback below keeps "python app.py" working on your own
# machine with no setup; the public server sets WEBCOMMENTBOOK_SECRET_KEY to a
# real random value, because a key that anyone can read in this file is no
# secret at all.
app.secret_key = os.environ.get(
    "WEBCOMMENTBOOK_SECRET_KEY", "webcommentbook-development-key"
)

# The key that permits changing or deleting existing comments through the API.
# It is read once, when the application starts. It is never written down in
# this project - on the server it comes from the systemd service file, which
# only root can read.
API_KEY = os.environ.get("WEBCOMMENTBOOK_API_KEY")

# The session cookie is sent back to this site only, is hidden from any
# JavaScript on the page, and - on a site served over HTTPS - is never sent
# over a plain unencrypted connection. The last one is switched off while you
# are working on your own machine, where http://127.0.0.1 is all there is; the
# live server sets WEBCOMMENTBOOK_HTTPS=1 so the cookie is protected there.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("WEBCOMMENTBOOK_HTTPS") == "1"

# The port is 5001 rather than the usual 5000 so that this application can run
# at the same time as anything else on this machine that already uses 5000.
PORT = 5001

# What a visitor sees in place of a comment a moderator has taken down. The
# comment keeps its place on the page, so it is plain that something was
# removed rather than quietly disappearing.
BLOCKED_TEXT = "This comment was removed by a moderator."

# Bring the database up to date before serving anything. This adds a missing
# column or table and never deletes a row, so it is safe on the live site -
# unlike seed.py, which would throw away every comment visitors have left.
db.ensure_schema()


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


def hide_blocked(comments):
    """Replace the words of any blocked comment before they leave the server.

    A blocked comment keeps its row and its place in the list, but the text
    itself must not be sent out again - not on the page and not through the
    API either, where it would be exactly as public.

    Everything a visitor can reach goes through here. The moderator's grid is
    the one place that does not, because somebody deciding whether a comment
    should stay has to be able to read it.
    """
    public = []
    for comment in comments:
        if comment.get("blocked"):
            # A copy, so that blanking the text for the page cannot possibly
            # reach back and change what is stored in the database.
            comment = dict(comment)
            comment["comment"] = BLOCKED_TEXT
        public.append(comment)
    return public


# ---------------------------------------------------------------------------
# The public web pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """The homepage: what this site is, plus a couple of headline numbers."""
    # The headline figures count only the comments visitors can actually read:
    # a comment that has been taken down should not go on affecting them.
    return render_template(
        "index.html",
        total=db.count_comments(blocked=False),
        average=db.average_rating(blocked=False),
        latest=hide_blocked(db.list_comments(sort="newest", limit=3)),
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
        comments=hide_blocked(db.list_comments(sort=sort)),
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
#   401 Unauthorized   you did not send the key these endpoints require
#   503 Unavailable    the server has no key configured, so it refuses outright
#
# Reading and adding a comment are open to anyone, because that is the point of
# the site. Changing or deleting one needs the key - see require_api_key()
# below, which explains the reasoning in full.
#
# The text of a blocked comment is never returned here either: the API is just
# as public as the page is.


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
    comments = hide_blocked(comments)
    return jsonify({"count": len(comments), "comments": comments})


@app.route("/api/comments/<int:comment_id>", methods=["GET"])
def api_get_comment(comment_id):
    """GET /api/comments/5 - one comment."""
    comment = db.get_comment(comment_id)
    if comment is None:
        return json_error("No comment with id %d." % comment_id, 404)
    return jsonify(hide_blocked([comment])[0])


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
# The moderator's pages
# ---------------------------------------------------------------------------
#
# A moderator logs in with a username and a password, both held in the admins
# table. From the grid at /admin they can do exactly two things to a comment:
#
#   block   hide the words from visitors, reversibly. The comment stays where
#           it is and the page says it was removed.
#   delete  remove the row for good.
#
# What they cannot do is change what somebody wrote. There is no edit form, and
# nothing on these pages calls db.update_comment(), so a comment on the site is
# always either the visitor's own words or plainly marked as taken down.

# The filter the status drop-down offers, and what each one means to
# db.list_comments(). As with SORT_ORDERS in db.py, keeping them in a
# dictionary means a value arriving in the query string can only ever pick one
# of these three - it is never pasted into any SQL.
STATUS_FILTERS = {
    "all": None,
    "visible": False,
    "blocked": True,
}


def current_admin():
    """The name of the logged-in moderator, or None if nobody is logged in."""
    return session.get("admin")


@app.context_processor
def template_globals():
    """Make these available to every template without passing them in.

    base.html uses current_admin to decide whether to show "Signed in as ..."
    and the sign-out button, and every template inherits base.html.

    csrf_token here is the function itself, not a token, so that a template
    writes {{ csrf_token() }} and a token is only created on the pages that
    actually contain a form. An ordinary visitor reading the comments never
    needs one.
    """
    return {"current_admin": current_admin(), "csrf_token": csrf_token}


def require_login():
    """Returns None when a moderator is logged in, or a redirect if not.

    This is the same shape as require_api_key() above: an early-return guard
    rather than a decorator, so that each route begins by saying out loud what
    it requires.

    The address that was being asked for is carried along in ?next=, so that
    logging in lands you where you were going rather than always at the grid.
    """
    if current_admin():
        return None
    return redirect(url_for("admin_login", next=request.full_path))


def csrf_token():
    """The token that proves a form was served by this site.

    Without this, any other website could contain a hidden form pointing at our
    delete address. A moderator who happened to be logged in and visited that
    page would have their browser send the request, cookie and all, and the
    comment would vanish - they would never see it happen. That trick is called
    cross-site request forgery.

    The cure is a random value kept in the session, put into every form we
    serve, and checked when the form comes back. Another site can make a
    browser send a request, but it cannot read our session, so it cannot guess
    the value to put in it.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    """Returns None if the submitted form carried the right token.

    compare_digest compares the two values in a way that always takes the same
    length of time, which gives away nothing about how much of a guess was
    right.
    """
    sent = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if expected and hmac.compare_digest(sent, expected):
        return None
    return render_template(
        "error.html",
        code=400,
        message="That form has expired. Please go back to the admin page and try again.",
    ), 400


def admin_url_from_form():
    """Back to the grid the moderator came from, with their search still on it.

    The three values are read from hidden fields in the form and handed to
    url_for, which puts them back in the query string. They are never used as
    an address themselves, so there is nothing here for anyone to redirect
    somebody else somewhere unexpected.
    """
    status = request.form.get("status", "all")
    return url_for(
        "admin_page",
        q=request.form.get("q", "") or None,
        status=status if status in STATUS_FILTERS else None,
        sort=request.form.get("sort") if request.form.get("sort") in db.SORT_ORDERS else None,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Show the log-in form, and handle it when it is submitted."""
    if request.method == "GET":
        return render_template("admin_login.html", errors=[], values={})

    refused = check_csrf()
    if refused:
        return refused

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    admin = db.get_admin(username)

    # One message for every kind of failure. Saying "no such user" would tell
    # somebody guessing which usernames are worth attacking.
    if admin is None or not check_password_hash(admin["password_hash"], password):
        return render_template(
            "admin_login.html",
            errors=["That username and password do not match."],
            values={"username": username},
        ), 401

    # A brand new session for the logged-in moderator. Clearing it first means
    # that nothing from before the log-in, including the old form token, can be
    # carried over into the logged-in one.
    session.clear()
    session["admin"] = admin["username"]

    flash("Signed in as " + admin["username"] + ".")

    # ?next= came from the browser, so it is only trusted as far as "a path on
    # this same site". Anything else - most of all a full address somewhere
    # else - is ignored and we go to the grid instead.
    destination = request.args.get("next", "")
    if destination.startswith("/") and not destination.startswith("//"):
        return redirect(destination)
    return redirect(url_for("admin_page"))


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    """Sign out. POST, not GET, so that no mere link can log somebody out."""
    refused = check_csrf()
    if refused:
        return refused

    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("home"))


@app.route("/admin")
def admin_page():
    """The grid: every comment, with a search box and a status filter."""
    refused = require_login()
    if refused:
        return refused

    # Anything unrecognised quietly falls back to the default, exactly as the
    # public comments page does with ?sort=.
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    if status not in STATUS_FILTERS:
        status = "all"
    sort = request.args.get("sort", "newest")
    if sort not in db.SORT_ORDERS:
        sort = "newest"

    comments = db.list_comments(
        sort=sort,
        blocked=STATUS_FILTERS[status],
        search=search or None,
    )

    return render_template(
        "admin.html",
        comments=comments,
        search=search,
        status=status,
        sort=sort,
        total=db.count_comments(),
        blocked_total=db.count_comments(blocked=True),
    )


@app.route("/admin/comments/<int:comment_id>/block", methods=["POST"])
def admin_block_comment(comment_id):
    """Hide a comment from visitors, or put it back."""
    refused = require_login()
    if refused:
        return refused
    refused = check_csrf()
    if refused:
        return refused

    # The form says which of the two it wants, so that the button is never
    # guessing at the current state of a row somebody else may just have
    # changed.
    blocked = request.form.get("action") == "block"

    comment = db.set_blocked(comment_id, blocked)
    if comment is None:
        flash("There is no comment with id %d - somebody may have deleted it." % comment_id)
    elif blocked:
        flash("Comment %d is blocked. Visitors now see that it was removed." % comment_id)
    else:
        flash("Comment %d is visible again." % comment_id)

    return redirect(admin_url_from_form())


@app.route("/admin/comments/<int:comment_id>/delete", methods=["GET", "POST"])
def admin_delete_comment(comment_id):
    """Ask first, then delete.

    The GET shows the comment and asks whether to go ahead; the POST does it.
    A confirmation page rather than a pop-up box, because there is no
    JavaScript anywhere in this project and a plain page is easier to follow.
    """
    refused = require_login()
    if refused:
        return refused

    if request.method == "GET":
        comment = db.get_comment(comment_id)
        if comment is None:
            flash("There is no comment with id %d." % comment_id)
            return redirect(url_for("admin_page"))
        return render_template(
            "admin_delete.html",
            comment=comment,
            search=request.args.get("q", ""),
            status=request.args.get("status", "all"),
            sort=request.args.get("sort", "newest"),
        )

    refused = check_csrf()
    if refused:
        return refused

    if db.delete_comment(comment_id):
        flash("Comment %d has been deleted." % comment_id)
    else:
        flash("There is no comment with id %d - it may already be gone." % comment_id)

    return redirect(admin_url_from_form())


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
