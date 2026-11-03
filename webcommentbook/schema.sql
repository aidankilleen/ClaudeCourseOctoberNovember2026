-- The database for webcommentbook is two tables.
--
-- "comments" is the heart of it: one row is one comment left by a visitor.
-- "admins" holds the people allowed to moderate those comments.
--
-- SQLite has no real date type, so dates are stored as ISO 8601 text
-- ("2026-11-03T14:05:00"). Text dates in that format sort correctly, which is
-- all we need to show newest comments first.
--
-- The CHECK constraints are a second line of defence: the application already
-- refuses a rating outside 1-5, but putting the rule in the database too means
-- a bad row cannot get in by any other route.
--
-- NOTE: this file is only used when building a database from scratch, because
-- it begins by throwing the old tables away. An existing database - such as the
-- live one, full of real visitors' comments - is brought up to date instead by
-- ensure_schema() in db.py, which adds what is missing without deleting
-- anything.

DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS admins;

CREATE TABLE comments (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date    TEXT    NOT NULL,
    name    TEXT    NOT NULL,
    comment TEXT    NOT NULL,
    rating  INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    -- 0 means the comment shows normally, 1 means a moderator has taken it
    -- down. We keep the row rather than deleting it, so that blocking can be
    -- undone and so the page can still say that something was removed.
    blocked INTEGER NOT NULL DEFAULT 0 CHECK (blocked IN (0, 1))
);

-- One row per administrator. Note what is NOT stored here: the password
-- itself. Only a one-way hash of it, so that a copy of this database does not
-- hand somebody the account. Checking a password means hashing what was typed
-- and comparing the two hashes - the original can never be read back out.
CREATE TABLE admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created       TEXT    NOT NULL
);
