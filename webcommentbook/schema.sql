-- The database for webcommentbook is a single table. One row is one comment
-- left by a visitor.
--
-- SQLite has no real date type, so the date is stored as ISO 8601 text
-- ("2026-11-03T14:05:00"). Text dates in that format sort correctly, which is
-- all we need to show newest comments first.
--
-- The CHECK constraint on rating is a second line of defence: the application
-- already refuses a rating outside 1-5, but putting the rule in the database
-- too means a bad row cannot get in by any other route.

DROP TABLE IF EXISTS comments;

CREATE TABLE comments (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date    TEXT    NOT NULL,
    name    TEXT    NOT NULL,
    comment TEXT    NOT NULL,
    rating  INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5)
);
