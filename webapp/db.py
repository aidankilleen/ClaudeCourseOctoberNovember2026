"""Everything that touches the database lives in this file.

Nothing else in the application writes SQL. That is deliberate: when you want
to know how the data is read or changed, there is exactly one file to open,
and when the database changes shape, there is exactly one file to fix.

The database is a single file, courses.db, sitting next to this one. There is
no database server to install, start or keep running - SQLite is part of
Python itself.
"""

import sqlite3
from pathlib import Path

# The database file lives beside this script, wherever the application has
# been copied to. Working it out from __file__ rather than from the folder you
# happen to be standing in means it is found no matter how the app is started.
DB_PATH = Path(__file__).parent / "courses.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect():
    """Open a connection to the database.

    Two settings are applied to every connection, and both matter:

    row_factory gives back rows you can read by column name - row["title"]
    rather than row[2] - so the code stays readable when a column is added.

    The foreign_keys pragma makes SQLite actually enforce the relationship
    between a session and its course. Surprisingly, SQLite ignores foreign
    keys unless you ask for them, and it asks per connection, not once.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row):
    """Turn one database row into an ordinary dictionary.

    This is the only place the shape of the JSON is decided. Converting here,
    rather than handing raw rows to the API, means a column can be renamed or
    hidden without changing what people reading the API see.
    """
    if row is None:
        return None

    data = dict(row)

    # The database stores whole cents because that is exact. People expect to
    # see euro, so the conversion happens once, here, on the way out.
    if "price_cents" in data:
        data["price"] = data["price_cents"] / 100

    # SQLite has no true/false of its own, it stores 1 and 0. Turn it back
    # into a real boolean so the JSON says true rather than 1.
    if "is_published" in data:
        data["is_published"] = bool(data["is_published"])

    # A session that is full should say so, rather than making every caller
    # work it out from two other numbers and get it wrong somewhere.
    if "capacity" in data and "places_taken" in data:
        data["places_left"] = max(0, data["capacity"] - data["places_taken"])

    return data


# --- Reading ---------------------------------------------------------------
# Note that every query below passes its values as a second argument to
# execute(), never by pasting them into the SQL string. That is what stops
# somebody typing a course name that rewrites your database.


def list_courses(published_only=True):
    """Every course, newest sessions first. Unpublished ones are hidden."""
    sql = "SELECT * FROM course"
    params = []
    if published_only:
        sql += " WHERE is_published = 1"
    sql += " ORDER BY title"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(r) for r in rows]


def get_course(course_id):
    """One course, or None if there is no course with that id."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM course WHERE id = ?", (course_id,)
        ).fetchone()
    return row_to_dict(row)


def get_course_by_slug(slug):
    """One course, found by its short name rather than its number."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM course WHERE slug = ?", (slug,)
        ).fetchone()
    return row_to_dict(row)


def list_sessions(course_id=None, from_date=None):
    """Sessions, soonest first.

    Pass course_id to get one course's sessions. Pass from_date (as
    'YYYY-MM-DD') to leave out anything that has already happened.
    """
    sql = "SELECT * FROM session"
    where = []
    params = []

    if course_id is not None:
        where.append("course_id = ?")
        params.append(course_id)
    if from_date is not None:
        where.append("starts_on >= ?")
        params.append(from_date)

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY starts_on"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(r) for r in rows]


def get_session(session_id):
    """One session, or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM session WHERE id = ?", (session_id,)
        ).fetchone()
    return row_to_dict(row)


def courses_with_sessions(from_date=None):
    """Every published course, each with its upcoming sessions attached.

    This is what the web page needs: one call, everything on it. Doing it here
    keeps the page route short and keeps the two database trips in one place.
    """
    courses = list_courses(published_only=True)
    sessions = list_sessions(from_date=from_date)

    # Group the sessions by the course they belong to, so the loop below does
    # not go back to the database once per course.
    by_course = {}
    for session in sessions:
        by_course.setdefault(session["course_id"], []).append(session)

    for course in courses:
        course["sessions"] = by_course.get(course["id"], [])
    return courses


# --- Writing ---------------------------------------------------------------
# Each of these returns the row it created or changed, so the API can hand
# the caller back exactly what is now stored rather than what they sent.

COURSE_FIELDS = (
    "slug", "title", "summary", "duration_days",
    "price_cents", "currency", "is_published",
)

SESSION_FIELDS = (
    "course_id", "starts_on", "ends_on",
    "location", "capacity", "places_taken",
)


def create_course(data):
    """Add a course. data is a dict; unknown keys are ignored."""
    fields = [f for f in COURSE_FIELDS if f in data]
    columns = ", ".join(fields)
    # One ? per field, so the values travel separately from the SQL.
    placeholders = ", ".join("?" for _ in fields)
    values = [data[f] for f in fields]

    with connect() as conn:
        cursor = conn.execute(
            f"INSERT INTO course ({columns}) VALUES ({placeholders})", values
        )
        new_id = cursor.lastrowid
    return get_course(new_id)


def update_course(course_id, data):
    """Change some fields of a course. Returns None if it does not exist."""
    if get_course(course_id) is None:
        return None

    fields = [f for f in COURSE_FIELDS if f in data]
    if not fields:
        return get_course(course_id)

    assignments = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields] + [course_id]

    with connect() as conn:
        conn.execute(f"UPDATE course SET {assignments} WHERE id = ?", values)
    return get_course(course_id)


def delete_course(course_id):
    """Remove a course and its sessions. True if there was one to remove."""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM course WHERE id = ?", (course_id,))
        return cursor.rowcount > 0


def create_session(data):
    """Add a session to an existing course."""
    fields = [f for f in SESSION_FIELDS if f in data]
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    values = [data[f] for f in fields]

    with connect() as conn:
        cursor = conn.execute(
            f"INSERT INTO session ({columns}) VALUES ({placeholders})", values
        )
        new_id = cursor.lastrowid
    return get_session(new_id)


def update_session(session_id, data):
    """Change some fields of a session. Returns None if it does not exist."""
    if get_session(session_id) is None:
        return None

    fields = [f for f in SESSION_FIELDS if f in data]
    if not fields:
        return get_session(session_id)

    assignments = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields] + [session_id]

    with connect() as conn:
        conn.execute(f"UPDATE session SET {assignments} WHERE id = ?", values)
    return get_session(session_id)


def delete_session(session_id):
    """Remove one session. True if there was one to remove."""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM session WHERE id = ?", (session_id,))
        return cursor.rowcount > 0


# --- Setting up ------------------------------------------------------------


def create_tables():
    """Build the empty tables by running schema.sql.

    This throws away any existing course and session tables, which is why it
    lives in seed.py's path and not anywhere the running website can reach.
    """
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(sql)
