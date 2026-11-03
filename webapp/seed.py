"""Build the database and fill it with the courses.

This is how you change what the website says. Edit the COURSES list below,
run the file, and refresh the page:

    python seed.py

Running it again wipes the course and session tables and rebuilds them from
what is written here, so this file - not the database - is the real record of
what the courses are. Anything added later through the API is lost on the next
run, which is a fair trade while you are the only person editing.
"""

import db

# Prices are in whole cents: 145000 is 1,450.00 euro. See schema.sql for why.
COURSES = [
    {
        "slug": "claude-code-in-action",
        "title": "Claude Code in Action",
        "summary": (
            "A working course in Claude Code for people who have never written "
            "software and do not intend to start."
        ),
        "duration_days": 3,
        "price_cents": 145000,
        "currency": "EUR",
        "is_published": 1,
        # The dates this course runs. Add a line to add a date to the website.
        "sessions": [
            {
                "starts_on": "2026-11-09",
                "ends_on": "2026-11-11",
                "location": "Dublin city centre",
                "capacity": 12,
                "places_taken": 7,
            },
            {
                "starts_on": "2026-12-07",
                "ends_on": "2026-12-09",
                "location": "Cork",
                "capacity": 12,
                "places_taken": 2,
            },
            {
                "starts_on": "2027-01-18",
                "ends_on": "2027-01-20",
                "location": "Online",
                "capacity": 12,
                "places_taken": 0,
            },
            {
                "starts_on": "2027-02-15",
                "ends_on": "2027-02-17",
                "location": "Dublin city centre",
                "capacity": 12,
                "places_taken": 0,
            },
        ],
    },
]


def main():
    print(f"Building {db.DB_PATH}")
    db.create_tables()

    for entry in COURSES:
        # Copy the dictionary and lift the sessions out of it, because the
        # sessions belong in their own table rather than on the course row.
        course_data = {k: v for k, v in entry.items() if k != "sessions"}
        course = db.create_course(course_data)
        print(f"  course: {course['title']}")

        for session_data in entry.get("sessions", []):
            session = db.create_session({**session_data, "course_id": course["id"]})
            print(
                f"    {session['starts_on']} to {session['ends_on']}"
                f"  {session['location']}"
                f"  ({session['places_left']} of {session['capacity']} left)"
            )

    print("\nDone. Start the website with:  python app.py")


if __name__ == "__main__":
    main()
