"""Reads and writes db.json, the small JSON file behind the REST API.

Nothing else in the app opens that file. Every route goes through the functions
here, so if the storage ever changes - a different filename, or a real database -
there is only one file to rewrite.

A record is a dictionary with an integer "id" plus the keys listed in FIELDS:

    {"id": 1, "title": "...", "description": "...", "duration": "2 days"}

The file is read fresh on every call rather than loaded once at start-up, so you
can edit db.json by hand and see the change on the next request - the same way
content.py already works.
"""

import json
import os
import tempfile
from pathlib import Path

DB_PATH = Path(__file__).parent / "db.json"

# The keys a record is allowed to have, besides "id". Anything else sent to the
# API is dropped rather than written to the file, so a typo in a request cannot
# quietly invent a new field that the rest of the app knows nothing about.
FIELDS = ("title", "description", "duration")


# --- Reading -----------------------------------------------------------------

def read_all():
    """Return every record as a list of dictionaries."""
    # A missing or empty file means "nothing stored yet" rather than an error,
    # so the API still answers sensibly before anyone has added a record.
    if not DB_PATH.exists():
        return []
    text = DB_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return json.loads(text)


def read_one(record_id):
    """Return the record with this id, or None if there isn't one.

    Routes use the None to decide when to answer 404.
    """
    for record in read_all():
        if record.get("id") == record_id:
            return record
    return None


# --- Writing -----------------------------------------------------------------

def create(data):
    """Add a new record and return it, with the id that was assigned."""
    records = read_all()
    record = {"id": _next_id(records), **fields_only(data)}
    records.append(record)
    _write_all(records)
    return record


def update(record_id, data, replace=False):
    """Change an existing record and return it, or None if it doesn't exist.

    By default only the keys present in `data` are changed, which is what PATCH
    wants. Pass replace=True for PUT: the stored record becomes exactly the
    fields given, and anything left out is dropped.
    """
    records = read_all()
    for position, record in enumerate(records):
        if record.get("id") == record_id:
            fields = fields_only(data)
            updated = fields if replace else {**record, **fields}
            # The id belongs to the store, not the request body, so it is set
            # last - a caller cannot change it by sending a different one.
            updated = {**updated, "id": record_id}
            records[position] = updated
            _write_all(records)
            return updated
    return None


def delete(record_id):
    """Remove a record. Returns True if one was removed, False if not found."""
    records = read_all()
    remaining = [r for r in records if r.get("id") != record_id]
    if len(remaining) == len(records):
        return False
    _write_all(remaining)
    return True


# --- Helpers -----------------------------------------------------------------

def fields_only(data):
    """Keep just the keys listed in FIELDS, ignoring anything else sent in."""
    return {key: data[key] for key in FIELDS if key in data}


def _next_id(records):
    """One higher than the largest id currently in the file.

    Worth knowing: deleting the newest record frees its id for the next one
    created. That is fine here, but if you ever hand these ids out to other
    systems you would want to store a counter instead of working it out.
    """
    return max((r.get("id", 0) for r in records), default=0) + 1


def _write_all(records):
    """Write the whole list back to db.json.

    The new contents go to a temporary file first and are then moved into place
    in a single step. If the program stops halfway through a write, db.json is
    still the old file rather than a half-written one.
    """
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=DB_PATH.parent, delete=False, suffix=".tmp"
    ) as temp:
        json.dump(records, temp, indent=2, ensure_ascii=False)
        temp.write("\n")
        temp_path = temp.name
    os.replace(temp_path, DB_PATH)
