"""Create the database and fill it with a few example comments.

  ****************************************************************
  *  WARNING: running this THROWS AWAY whatever is in the        *
  *  database and starts again. Any comment added through the    *
  *  website or the API is lost, and so is every moderator       *
  *  account.                                                    *
  ****************************************************************

Run it once before starting the application for the first time:

    python seed.py

Run it again whenever you want a clean slate. If you want a different set of
starting comments, edit SAMPLE_COMMENTS below - this file is the record of
what the site starts out with.

To add a moderator to a site that is already running, use create_admin.py
instead. It leaves the comments alone.
"""

import os

from werkzeug.security import generate_password_hash

import db

# The comments the site starts with. Dates are ISO 8601 text, which is how they
# are stored, and the ratings deliberately vary so the stars on the page are
# worth looking at.
# The one moderator the site starts with. Taking these from the environment
# means a real password need never be written down in this file; the fallback
# of admin/admin is there so that the site works the moment you have seeded it
# on your own machine, and is no use to anybody anywhere else.
ADMIN_USERNAME = os.environ.get("WEBCOMMENTBOOK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("WEBCOMMENTBOOK_ADMIN_PASSWORD", "admin")

SAMPLE_COMMENTS = [
    {
        "date": "2026-10-12T09:15:00",
        "name": "Aoife Byrne",
        "comment": "Really clear from start to finish. I came in knowing nothing "
                   "and left able to build something myself.",
        "rating": 5,
    },
    {
        "date": "2026-10-14T16:40:00",
        "name": "Tom Hegarty",
        "comment": "Good pace and plenty of examples. The room was a bit cold in "
                   "the morning, but that is hardly the course's fault.",
        "rating": 4,
    },
    {
        "date": "2026-10-19T11:05:00",
        "name": "Marta Nowak",
        "comment": "The hands-on sections were the best part. More time on those "
                   "and fewer slides would suit me.",
        "rating": 4,
    },
    {
        "date": "2026-10-23T14:20:00",
        "name": "Declan Murphy",
        "comment": "Fine, but a lot of it was already familiar. Worth saying up "
                   "front how much prior experience is assumed.",
        "rating": 3,
    },
    {
        "date": "2026-10-28T10:00:00",
        "name": "Priya Nair",
        "comment": "Excellent. The worked examples were the thing that made it "
                   "click for me, and I have used two of them since.",
        "rating": 5,
    },
    {
        "date": "2026-11-01T15:30:00",
        "name": "Sean O Riordan",
        "comment": "Enjoyed it thoroughly. I would happily sit the follow-on "
                   "course if one is offered.",
        "rating": 5,
    },
]


def build_database():
    """Drop the old tables, create them again, and insert the starting rows."""
    # schema.sql begins with DROP TABLE IF EXISTS, so running the whole file
    # clears out anything that was there before.
    with open(db.SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        schema_sql = schema_file.read()

    connection = db.get_connection()
    try:
        connection.executescript(schema_sql)
        # The comments do not mention the blocked column at all: it has a
        # DEFAULT of 0 in schema.sql, so every sample comment starts visible
        # without this having to say so.
        connection.executemany(
            "INSERT INTO comments (date, name, comment, rating) "
            "VALUES (:date, :name, :comment, :rating)",
            SAMPLE_COMMENTS,
        )

        # What is stored is a one-way hash, never the password itself - see
        # the comment on the admins table in schema.sql.
        connection.execute(
            "INSERT INTO admins (username, password_hash, created) "
            "VALUES (?, ?, datetime('now'))",
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)),
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    existed = os.path.exists(db.DATABASE_PATH)
    build_database()

    if existed:
        print("Rebuilt the existing database - everything that was in it is gone.")
    else:
        print("Created a new database.")
    print("Database file: " + db.DATABASE_PATH)
    print("Inserted %d sample comments." % len(SAMPLE_COMMENTS))
    print("Created the moderator '%s'." % ADMIN_USERNAME)

    if ADMIN_PASSWORD == "admin":
        print("")
        print("That account's password is 'admin'. That is fine on your own")
        print("machine and nowhere else - on a real server, set a password")
        print("with create_admin.py instead.")

    print("")
    print("Now run:  python app.py    and open http://127.0.0.1:5001")
