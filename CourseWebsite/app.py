"""A tiny Flask app that serves the one-page Professional Training website,
plus a small REST API for the course records in db.json.

The page has one route. All of its text comes from content.py, which is passed
into the template as "c". The one exception is the copyright year, which is
worked out here rather than stored.

The API lives under /api/. It never touches db.json directly - all reading and
writing goes through db.py.
"""

from datetime import date

from flask import Flask, jsonify, render_template, request, url_for

import content
import db

app = Flask(__name__)


# --- The website -------------------------------------------------------------

@app.route("/")
def home():
    """Render the single brochure page."""
    # Worked out fresh on every visit, so the footer is still right even if the
    # server has been running since last year.
    return render_template("index.html", c=content, year=date.today().year)


# --- The REST API ------------------------------------------------------------
# One route per method, each a few lines, because each one does a different
# thing with the request. The shared pieces - reading the file, allocating ids,
# writing safely - all live in db.py.

@app.route("/api/courses", methods=["GET"])
def list_courses():
    """Return every record in db.json."""
    return jsonify(db.read_all())


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """Return one record, or 404 if there is no record with that id."""
    course = db.read_one(course_id)
    if course is None:
        return _not_found(course_id)
    return jsonify(course)


@app.route("/api/courses", methods=["POST"])
def create_course():
    """Add a new record. The id is assigned here, not sent by the caller."""
    fields, error = _fields_from_request(required=db.FIELDS)
    if error:
        return error
    course = db.create(fields)
    # 201 Created, with a Location header pointing at the new record - that is
    # how the caller learns the id it was given.
    return jsonify(course), 201, {"Location": url_for("get_course", course_id=course["id"])}


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def replace_course(course_id):
    """Replace a record outright. Every field must be sent."""
    fields, error = _fields_from_request(required=db.FIELDS)
    if error:
        return error
    course = db.update(course_id, fields, replace=True)
    if course is None:
        return _not_found(course_id)
    return jsonify(course)


@app.route("/api/courses/<int:course_id>", methods=["PATCH"])
def patch_course(course_id):
    """Change only the fields that were sent, leaving the rest as they are."""
    fields, error = _fields_from_request(required=())
    if error:
        return error
    course = db.update(course_id, fields)
    if course is None:
        return _not_found(course_id)
    return jsonify(course)


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """Remove a record. 204 means it is gone and there is nothing to send back."""
    if not db.delete(course_id):
        return _not_found(course_id)
    return "", 204


# --- Shared bits of the API --------------------------------------------------

def _not_found(course_id):
    """The 404 every route gives when the id doesn't match a record."""
    return jsonify({"error": f"No course with id {course_id}."}), 404


def _fields_from_request(required):
    """Pull the record fields out of the request body.

    Returns a (fields, error) pair. When the body was usable, `error` is None.
    Otherwise `error` is a finished response the route can return as it is, and
    `fields` is None - so every route checks the error before using the fields.
    """
    # silent=True makes Flask hand back None for a missing or malformed body
    # rather than raising, so we can answer with a clear message of our own.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (
            jsonify({"error": "The request body must be a JSON object."}),
            400,
        )

    fields = db.fields_only(data)

    missing = [name for name in required if name not in fields]
    if missing:
        return None, (
            jsonify({"error": "Missing required field(s): " + ", ".join(missing)}),
            400,
        )

    # Catches a PATCH whose body is empty or made up entirely of unknown keys,
    # which would otherwise be accepted and change nothing.
    if not fields:
        return None, (
            jsonify({"error": "No known fields given. Expected: " + ", ".join(db.FIELDS)}),
            400,
        )

    return fields, None


if __name__ == "__main__":
    # debug=True reloads the page automatically when you edit a file.
    app.run(debug=True)
