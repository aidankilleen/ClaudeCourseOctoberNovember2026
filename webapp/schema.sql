-- The shape of the database. Running seed.py applies this file.
--
-- Two tables: a course is the thing you teach, a session is one particular
-- running of it on particular dates. One course has many sessions, which is
-- why the dates are not columns on the course itself.

DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS course;

CREATE TABLE course (
    id            INTEGER PRIMARY KEY,
    slug          TEXT    NOT NULL UNIQUE,   -- short name safe to put in a URL
    title         TEXT    NOT NULL,
    summary       TEXT    NOT NULL DEFAULT '',
    duration_days INTEGER NOT NULL DEFAULT 1,

    -- Money is stored as a whole number of cents, never as a decimal. 14.50
    -- cannot be represented exactly by a computer, but 1450 can, so prices
    -- stored this way never drift by a cent.
    price_cents   INTEGER NOT NULL DEFAULT 0,
    currency      TEXT    NOT NULL DEFAULT 'EUR',

    -- 0 keeps a course in the database but off the website.
    is_published  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE session (
    id           INTEGER PRIMARY KEY,

    -- ON DELETE CASCADE: removing a course removes its sessions too, so there
    -- is never a session pointing at a course that no longer exists.
    course_id    INTEGER NOT NULL REFERENCES course(id) ON DELETE CASCADE,

    -- Dates are kept as plain text in YYYY-MM-DD order. Written that way they
    -- sort and compare correctly, so "later than today" is a simple >.
    starts_on    TEXT    NOT NULL,
    ends_on      TEXT    NOT NULL,

    location     TEXT    NOT NULL DEFAULT 'Online',
    capacity     INTEGER NOT NULL DEFAULT 12,
    places_taken INTEGER NOT NULL DEFAULT 0
);

-- Looking up "the sessions for this course, soonest first" is the one query
-- the website makes on every page load, so it gets an index.
CREATE INDEX session_by_course ON session (course_id, starts_on);
