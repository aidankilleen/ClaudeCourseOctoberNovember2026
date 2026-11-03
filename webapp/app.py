"""The website and its API.

One Flask application serves both:

  - GET /          the web page, built from the database
  - GET /api/...   the same information as JSON, for programs rather than people

Reading is open to anybody. Changing anything needs a key, because this runs
on the public internet and an unprotected write endpoint is an invitation.

Run it for yourself with:   python app.py
"""

import hmac
import os
from datetime import date
from functools import wraps

from flask import Flask, jsonify, render_template, request

import db

app = Flask(__name__)

# The key that permits writing. It is read from the environment rather than
# written here, so that it never ends up in the repository by accident.
API_KEY = os.environ.get("AIDANK_API_KEY")


# --- Who is allowed to change things ---------------------------------------


def requires_key(view):
    """Refuse the request unless it carries the right X-API-Key header.

    Put @requires_key above any route that changes the database.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        # If no key has been configured, refuse everything rather than
        # allowing everything. A missing setting must never mean "open" -
        # that is the mistake that puts databases on the news.
        if not API_KEY:
            return jsonify(
                {"error": "Writing is disabled: no API key is configured."}
            ), 503

        supplied = request.headers.get("X-API-Key", "")

        # compare_digest rather than == : it always takes the same amount of
        # time, so an attacker cannot learn the key one character at a time by
        # measuring how long each guess took.
        if not hmac.compare_digest(supplied, API_KEY):
            return jsonify({"error": "A valid X-API-Key header is required."}), 401

        return view(*args, **kwargs)

    return wrapper


# --- Turning stored values into something readable -------------------------
# The database holds dates as 2026-11-09 and prices as 145000, because those
# are exact and sort correctly. People want "9 to 11 November 2026" and
# "1,450". These two filters do that translation, in the template only, so
# the stored values are never themselves changed.


@app.template_filter("daterange")
def daterange(session):
    """'9 to 11 November 2026', without repeating the month when it is shared."""
    start = date.fromisoformat(session["starts_on"])
    end = date.fromisoformat(session["ends_on"])

    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day} to {end.day} {start.strftime('%B %Y')}"
    if start.year == end.year:
        return f"{start.day} {start.strftime('%B')} to {end.day} {end.strftime('%B %Y')}"
    return (
        f"{start.day} {start.strftime('%B %Y')}"
        f" to {end.day} {end.strftime('%B %Y')}"
    )


@app.template_filter("longdate")
def longdate(iso_date):
    """'2026-11-09' becomes '9 November 2026'."""
    parsed = date.fromisoformat(iso_date)
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def human_list(items):
    """['Cork', 'Dublin', 'Online'] becomes 'Cork, Dublin and Online'.

    Joining with commas and a final "and" is the sort of thing that looks
    trivial until a list has exactly two items in it.
    """
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


@app.template_filter("money")
def money(cents, currency="EUR"):
    """145000 becomes 1,450 - with no trailing .00 when there are no cents."""
    symbols = {"EUR": "€", "GBP": "£", "USD": "$"}
    symbol = symbols.get(currency, "")
    amount = cents / 100
    if amount == int(amount):
        return f"{symbol}{int(amount):,}"
    return f"{symbol}{amount:,.2f}"


def json_body():
    """The JSON the caller sent, or None if they sent something else.

    silent=True stops Flask raising on malformed JSON, so the route can
    answer with a tidy 400 instead of a stack trace.
    """
    return request.get_json(silent=True)


# --- The web page -----------------------------------------------------------


@app.route("/")
def home():
    """The course page, rendered from whatever is in the database right now."""
    today = date.today().isoformat()

    # Only sessions that have not already happened: a page advertising last
    # month's course is worse than one advertising none.
    courses = db.courses_with_sessions(from_date=today)

    # Flattened and sorted, for the parts of the page that just want "the next
    # dates" without caring which course they belong to.
    upcoming = db.list_sessions(from_date=today)

    # The page is about one course at the moment, so it uses the first one.
    # When there is more than one to show, this is the line that changes.
    course = courses[0] if courses else None

    # The soonest session, used for the headline claims near the top. Every
    # one of these may be None, and the template checks before using them -
    # a site with no dates in it yet must still render.
    next_session = upcoming[0] if upcoming else None

    # Where the course runs is no longer typed into the page: it is whichever
    # places have a session coming up. sorted(set(...)) removes duplicates and
    # puts them in a predictable order.
    locations = human_list(sorted({s["location"] for s in upcoming})) or "Online"

    return render_template(
        "index.html",
        courses=courses,
        upcoming=upcoming,
        course=course,
        next_session=next_session,
        locations=locations,
    )


# --- The API: reading -------------------------------------------------------


@app.route("/api/courses")
def api_courses():
    """Every published course.

    Add ?all=1 to include unpublished ones as well.
    """
    include_all = request.args.get("all") == "1"
    return jsonify(db.list_courses(published_only=not include_all))


@app.route("/api/courses/<int:course_id>")
def api_course(course_id):
    """One course."""
    course = db.get_course(course_id)
    if course is None:
        return jsonify({"error": f"No course with id {course_id}."}), 404
    return jsonify(course)


@app.route("/api/courses/<int:course_id>/sessions")
def api_course_sessions(course_id):
    """The sessions belonging to one course."""
    if db.get_course(course_id) is None:
        return jsonify({"error": f"No course with id {course_id}."}), 404
    return jsonify(db.list_sessions(course_id=course_id))


@app.route("/api/sessions")
def api_sessions():
    """Every session.

    Add ?from=YYYY-MM-DD to leave out anything earlier, or ?from=today.
    """
    from_date = request.args.get("from")
    if from_date == "today":
        from_date = date.today().isoformat()
    return jsonify(db.list_sessions(from_date=from_date))


@app.route("/api/sessions/<int:session_id>")
def api_session(session_id):
    """One session."""
    session = db.get_session(session_id)
    if session is None:
        return jsonify({"error": f"No session with id {session_id}."}), 404
    return jsonify(session)


# --- The API: changing things ----------------------------------------------


@app.route("/api/courses", methods=["POST"])
@requires_key
def api_create_course():
    """Add a course. slug and title are the two fields that must be there."""
    data = json_body()
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object."}), 400

    missing = [f for f in ("slug", "title") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}."}), 400

    # A slug has to be unique, and a clear message beats a database error.
    if db.get_course_by_slug(data["slug"]) is not None:
        return jsonify({"error": f"A course with slug '{data['slug']}' already exists."}), 409

    # 201 Created, and the Location header points at the thing just made.
    course = db.create_course(data)
    return jsonify(course), 201, {"Location": f"/api/courses/{course['id']}"}


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
@requires_key
def api_update_course(course_id):
    """Change an existing course. Send only the fields you want changed."""
    data = json_body()
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object."}), 400

    course = db.update_course(course_id, data)
    if course is None:
        return jsonify({"error": f"No course with id {course_id}."}), 404
    return jsonify(course)


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
@requires_key
def api_delete_course(course_id):
    """Remove a course, and with it every session of that course."""
    if not db.delete_course(course_id):
        return jsonify({"error": f"No course with id {course_id}."}), 404
    # 204 means "done, and there is deliberately nothing to send back".
    return "", 204


@app.route("/api/sessions", methods=["POST"])
@requires_key
def api_create_session():
    """Add a session to a course."""
    data = json_body()
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object."}), 400

    missing = [f for f in ("course_id", "starts_on", "ends_on") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}."}), 400

    if db.get_course(data["course_id"]) is None:
        return jsonify({"error": f"No course with id {data['course_id']}."}), 400

    session = db.create_session(data)
    return jsonify(session), 201, {"Location": f"/api/sessions/{session['id']}"}


@app.route("/api/sessions/<int:session_id>", methods=["PUT"])
@requires_key
def api_update_session(session_id):
    """Change an existing session."""
    data = json_body()
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object."}), 400

    session = db.update_session(session_id, data)
    if session is None:
        return jsonify({"error": f"No session with id {session_id}."}), 404
    return jsonify(session)


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
@requires_key
def api_delete_session(session_id):
    """Remove one session."""
    if not db.delete_session(session_id):
        return jsonify({"error": f"No session with id {session_id}."}), 404
    return "", 204


# --- When things go wrong ---------------------------------------------------
# Without these, a wrong URL under /api returns Flask's HTML error page, which
# is confusing for something expecting JSON.


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "No such endpoint."}), 404
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "That method is not allowed on this endpoint."}), 405


if __name__ == "__main__":
    # Only for working on your own machine. In production gunicorn runs the
    # app instead, and debug mode is never switched on there - it would let a
    # visitor run Python on the server.
    app.run(debug=True, port=5000)
