"""Everything that talks to the SQLite database lives here.

We use the sqlite3 module that comes with Python rather than a library like
SQLAlchemy. That keeps the actual SQL visible on the page where it runs, which
matters more here than saving a few lines of typing.

The validation rules for a comment also live in this file. The HTML form and
the REST API both call validate_comment(), so there is exactly one place that
decides what a valid comment looks like and the two routes can never drift
apart.

There are two tables: "comments", and "admins" for the people who are allowed
to moderate them. A moderator can hide a comment or delete it, which is why
comments carry a "blocked" flag.
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
# Bringing an existing database up to date
# ---------------------------------------------------------------------------

def ensure_schema():
    """Add anything the database is missing, without disturbing what is there.

    This exists to solve one specific problem. seed.py builds the database by
    running schema.sql, which begins by DROPping the tables - fine on your own
    machine, a disaster on the live site, where every row is a comment a real
    visitor left and there is no copy of it anywhere else.

    So when this application grows a new column or a new table, the live
    database is brought up to date by this function instead: it looks at what
    is already there and adds only the missing pieces. Both steps below are
    safe to run every single time the application starts, and neither of them
    changes or removes an existing row.

    They are also safe to run several times at once. On the live server
    gunicorn starts three copies of the application together, and all three
    reach this function within the same moment. Each one can therefore look at
    the database, see the same missing column, and try to add it - so the
    second and third have to expect that the job is already done rather than
    falling over. That is exactly what happened the first time this was
    deployed: two workers tried to add the column, one of them failed, and the
    site was down until systemd restarted it.
    """
    connection = get_connection()
    try:
        # PRAGMA table_info asks SQLite to describe a table. Each row it
        # returns describes one column, and row["name"] is that column's name.
        rows = connection.execute("PRAGMA table_info(comments)").fetchall()
        existing = [row["name"] for row in rows]

        if existing and "blocked" not in existing:
            # An older database, from before moderation existed. Everything
            # already in it was visible, and DEFAULT 0 keeps it that way.
            try:
                connection.execute(
                    "ALTER TABLE comments ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError as problem:
                # "duplicate column name" means another copy of the application
                # added it a fraction of a second ago. That is the result we
                # wanted, so there is nothing to report. Any other complaint
                # from SQLite is a genuine problem and is allowed through.
                if "duplicate column name" not in str(problem):
                    raise

        # IF NOT EXISTS does the same job for a whole table that the check
        # above does for a single column.
        connection.execute(
            "CREATE TABLE IF NOT EXISTS admins ("
            "    id            INTEGER PRIMARY KEY AUTOINCREMENT,"
            "    username      TEXT    NOT NULL UNIQUE,"
            "    password_hash TEXT    NOT NULL,"
            "    created       TEXT    NOT NULL"
            ")"
        )
        connection.commit()
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


def list_comments(sort="newest", min_rating=None, limit=None, offset=0,
                  blocked=None, search=None):
    """Return comments, optionally filtered and paged.

    blocked says which comments are wanted: None for all of them, False for
    only the ones visitors can read, True for only the blocked ones. The
    moderator's page asks for each of the three at different moments. The
    public pages ask for all of them and hide the text of the blocked ones
    instead, so that a visitor can see something was taken down.

    search matches a word anywhere in the name or the comment. Only the
    moderator's page uses it.

    The conditions are gathered in a list and joined with AND rather than being
    glued on to the SQL one at a time, because there can now be several of them
    and only the first one is allowed to say WHERE.
    """
    order_by = SORT_ORDERS.get(sort, SORT_ORDERS["newest"])

    sql = "SELECT id, date, name, comment, rating, blocked FROM comments"
    conditions = []
    args = []

    if min_rating is not None:
        conditions.append("rating >= ?")
        args.append(min_rating)

    if blocked is not None:
        conditions.append("blocked = ?")
        args.append(1 if blocked else 0)

    if search:
        # The % signs go into the value we hand to SQLite, never into the SQL
        # itself, so whatever somebody types in the search box is only ever
        # treated as text to look for.
        conditions.append("(name LIKE ? OR comment LIKE ?)")
        args.append("%" + search + "%")
        args.append("%" + search + "%")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

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
        "SELECT id, date, name, comment, rating, blocked FROM comments WHERE id = ?",
        (comment_id,),
    )


def count_comments(blocked=None):
    """How many comments there are - used on the homepage and the admin page.

    blocked works exactly as it does in list_comments(): None counts them all,
    False counts only the ones visitors can read, True only the blocked ones.
    """
    sql = "SELECT COUNT(*) AS total FROM comments"
    args = ()
    if blocked is not None:
        sql += " WHERE blocked = ?"
        args = (1 if blocked else 0,)
    row = query_one(sql, args)
    return row["total"] if row else 0


def average_rating(blocked=None):
    """The average rating, or None when there is nothing to average.

    The homepage passes blocked=False: a comment a moderator has taken down
    should not go on quietly affecting the headline figure.
    """
    sql = "SELECT AVG(rating) AS average FROM comments"
    args = ()
    if blocked is not None:
        sql += " WHERE blocked = ?"
        args = (1 if blocked else 0,)
    row = query_one(sql, args)
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


def set_blocked(comment_id, blocked):
    """Hide a comment from visitors, or put it back. Returns the row, or None.

    This is deliberately a function of its own rather than another field in
    update_comment(). Blocking is not editing: a moderator may take a comment
    down, but the words stay exactly as the person wrote them. Keeping the two
    apart is what makes that impossible to get wrong later.
    """
    _, affected = execute(
        "UPDATE comments SET blocked = ? WHERE id = ?",
        (1 if blocked else 0, comment_id),
    )
    if affected == 0:
        return None
    return get_comment(comment_id)


def delete_comment(comment_id):
    """Delete a comment. Returns True if there was one to delete."""
    _, affected = execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    return affected > 0


# ---------------------------------------------------------------------------
# Administrators
# ---------------------------------------------------------------------------
#
# Only the hash of a password is ever stored or handed back. The hashing itself
# does not happen here: it belongs with the code that has the typed-in password
# in its hands, which is app.py when somebody logs in and create_admin.py when
# somebody sets one.

def get_admin(username):
    """Look up one administrator by name, or None if there is no such account."""
    return query_one(
        "SELECT id, username, password_hash, created FROM admins WHERE username = ?",
        (username,),
    )


def count_admins():
    """How many administrator accounts exist."""
    row = query_one("SELECT COUNT(*) AS total FROM admins")
    return row["total"] if row else 0


def create_or_update_admin(username, password_hash):
    """Add an administrator, or give an existing one a new password.

    Returns True if the account was created and False if an existing one was
    updated, which is all create_admin.py needs in order to say which it did.

    ON CONFLICT means "if a row with this username already exists, update it
    rather than failing", so resetting a forgotten password needs no separate
    command.
    """
    existed = get_admin(username) is not None
    execute(
        "INSERT INTO admins (username, password_hash, created) VALUES (?, ?, ?) "
        "ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash",
        (username, password_hash, datetime.now().isoformat(timespec="seconds")),
    )
    return not existed


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
