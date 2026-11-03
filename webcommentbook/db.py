"""Everything that talks to the SQLite database lives here.

We use the sqlite3 module that comes with Python rather than a library like
SQLAlchemy. That keeps the actual SQL visible on the page where it runs, which
matters more here than saving a few lines of typing.

The validation rules for a comment also live in this file. The HTML form and
the REST API both call validate_comment(), so there is exactly one place that
decides what a valid comment looks like and the two routes can never drift
apart.
"""

import os
import sqlite3
from datetime import datetime

# The database file sits next to this module, whatever directory the app was
# started from. Working out the path from __file__ avoids the classic problem
# of "it works when I run it from the project folder and nowhere else".
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "comments.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Field limits. These are deliberately generous - they exist to stop somebody
# pasting a novel into the form, not to be strict.
MAX_NAME_LENGTH = 80
MAX_COMMENT_LENGTH = 2000


def get_connection():
    """Open a connection to the database.

    row_factory = sqlite3.Row makes each row behave like a dictionary, so we
    can write row["name"] instead of remembering that name is column 2.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def query_all(sql, args=()):
    """Run a SELECT and return every row as a list of plain dictionaries.

    We convert to dictionaries before returning so that the rest of the
    application never has to know it is dealing with sqlite3 objects - and so
    that Flask can turn the result straight into JSON.
    """
    connection = get_connection()
    try:
        rows = connection.execute(sql, args).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def query_one(sql, args=()):
    """Run a SELECT that should return a single row, or None if there is none."""
    connection = get_connection()
    try:
        row = connection.execute(sql, args).fetchone()
    finally:
        connection.close()
    return dict(row) if row is not None else None


def execute(sql, args=()):
    """Run an INSERT, UPDATE or DELETE and commit it.

    Returns (lastrowid, rowcount): the id of a newly inserted row, and how many
    rows were actually affected. The rowcount is how the API tells "I updated
    it" apart from "there was nothing there to update".
    """
    connection = get_connection()
    try:
        cursor = connection.execute(sql, args)
        connection.commit()
        return cursor.lastrowid, cursor.rowcount
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Reading comments
# ---------------------------------------------------------------------------

# The three sort orders the comments page offers, mapped to the ORDER BY clause
# each one needs. Keeping them in a dictionary means a value arriving from the
# query string can only ever pick one of these three - it is never pasted into
# the SQL, so there is nothing for anyone to inject.
SORT_ORDERS = {
    "newest": "date DESC, id DESC",
    "oldest": "date ASC, id ASC",
    "rating": "rating DESC, date DESC",
}


def list_comments(sort="newest", min_rating=None, limit=None, offset=0):
    """Return comments, optionally filtered by rating and paged."""
    order_by = SORT_ORDERS.get(sort, SORT_ORDERS["newest"])

    sql = "SELECT id, date, name, comment, rating FROM comments"
    args = []

    if min_rating is not None:
        sql += " WHERE rating >= ?"
        args.append(min_rating)

    sql += " ORDER BY " + order_by

    # SQLite requires a LIMIT before it will accept an OFFSET, so if only an
    # offset was asked for we pass -1, which means "no limit".
    if limit is not None or offset:
        sql += " LIMIT ? OFFSET ?"
        args.append(limit if limit is not None else -1)
        args.append(offset)

    return query_all(sql, tuple(args))


def get_comment(comment_id):
    """Return one comment by id, or None if that id does not exist."""
    return query_one(
        "SELECT id, date, name, comment, rating FROM comments WHERE id = ?",
        (comment_id,),
    )


def count_comments():
    """How many comments there are in total - used on the homepage."""
    row = query_one("SELECT COUNT(*) AS total FROM comments")
    return row["total"] if row else 0


def average_rating():
    """The average rating, or None when there are no comments yet."""
    row = query_one("SELECT AVG(rating) AS average FROM comments")
    if row is None or row["average"] is None:
        return None
    return round(row["average"], 1)


# ---------------------------------------------------------------------------
# Writing comments
# ---------------------------------------------------------------------------

def create_comment(data):
    """Insert a validated comment and return the row as it was stored."""
    new_id, _ = execute(
        "INSERT INTO comments (date, name, comment, rating) VALUES (?, ?, ?, ?)",
        (data["date"], data["name"], data["comment"], data["rating"]),
    )
    return get_comment(new_id)


def replace_comment(comment_id, data):
    """Overwrite every field of an existing comment. Returns None if it is gone."""
    _, affected = execute(
        "UPDATE comments SET date = ?, name = ?, comment = ?, rating = ? WHERE id = ?",
        (data["date"], data["name"], data["comment"], data["rating"], comment_id),
    )
    if affected == 0:
        return None
    return get_comment(comment_id)


def update_comment(comment_id, data):
    """Change only the fields present in data (a PATCH).

    The column names come from our own list, never from the caller, so the
    SQL we build here cannot be influenced from outside.
    """
    fields = [field for field in ("date", "name", "comment", "rating") if field in data]
    if not fields:
        # Nothing to change - just hand back what is already stored.
        return get_comment(comment_id)

    assignments = ", ".join(field + " = ?" for field in fields)
    args = [data[field] for field in fields] + [comment_id]

    _, affected = execute(
        "UPDATE comments SET " + assignments + " WHERE id = ?", tuple(args)
    )
    if affected == 0:
        return None
    return get_comment(comment_id)


def delete_comment(comment_id):
    """Delete a comment. Returns True if there was one to delete."""
    _, affected = execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    return affected > 0


# ---------------------------------------------------------------------------
# Validation - shared by the HTML form and the REST API
# ---------------------------------------------------------------------------

def validate_comment(data, partial=False):
    """Check and tidy up the values for a comment.

    Returns (cleaned, errors). If errors is an empty list the cleaned
    dictionary is safe to store; otherwise errors holds one plain-English
    message per problem, ready to show on the form or return as JSON.

    partial=True is for PATCH: a field that was not supplied is simply left
    alone instead of being reported as missing.
    """
    cleaned = {}
    errors = []

    # --- name ---
    if "name" in data:
        name = str(data["name"] or "").strip()
        if not name:
            errors.append("Please give a name.")
        elif len(name) > MAX_NAME_LENGTH:
            errors.append("Name is too long (maximum %d characters)." % MAX_NAME_LENGTH)
        else:
            cleaned["name"] = name
    elif not partial:
        errors.append("Please give a name.")

    # --- comment ---
    if "comment" in data:
        comment = str(data["comment"] or "").strip()
        if not comment:
            errors.append("Please write a comment.")
        elif len(comment) > MAX_COMMENT_LENGTH:
            errors.append(
                "Comment is too long (maximum %d characters)." % MAX_COMMENT_LENGTH
            )
        else:
            cleaned["comment"] = comment
    elif not partial:
        errors.append("Please write a comment.")

    # --- rating ---
    if "rating" in data and str(data["rating"]).strip() != "":
        try:
            # int(str(...)) rather than int(...) so that a rating sent as the
            # text "4" from the HTML form works exactly like the number 4 sent
            # as JSON. A value such as 4.5 is rejected rather than silently
            # rounded.
            rating = int(str(data["rating"]).strip())
        except (TypeError, ValueError):
            errors.append("Rating must be a whole number from 1 to 5.")
        else:
            if 1 <= rating <= 5:
                cleaned["rating"] = rating
            else:
                errors.append("Rating must be a whole number from 1 to 5.")
    elif not partial:
        errors.append("Please choose a rating from 1 to 5.")

    # --- date ---
    # The date is optional. The form never sends one and we stamp "now"; the
    # API may send one, for instance when importing older comments.
    if "date" in data and str(data["date"]).strip() != "":
        date_text = str(data["date"]).strip()
        try:
            # fromisoformat accepts both "2026-11-03" and a full timestamp.
            datetime.fromisoformat(date_text)
        except ValueError:
            errors.append(
                "Date must be in ISO format, for example 2026-11-03 or "
                "2026-11-03T14:05:00."
            )
        else:
            cleaned["date"] = date_text
    elif not partial:
        cleaned["date"] = datetime.now().isoformat(timespec="seconds")

    return cleaned, errors
