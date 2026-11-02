#!/usr/bin/env python3
"""Validate an invoice-extractor output file (CSV or JSON).

Usage:
    python validate_output.py <output-file> [--format csv|json]

Format is inferred from the file extension when --format is not given.

Exit codes:
    0  valid (warnings may still be printed)
    1  validation errors found
    2  could not read or parse the file
"""

import argparse
import csv
import json
import os
import re
import sys

FIELDS = [
    "sequenceNo",
    "invoiceNo",
    "invoiceDate",
    "supplierName",
    "total",
    "vat",
    "errors",
    "notes",
]
TEXT_FIELDS = ["invoiceNo", "supplierName", "errors", "notes"]
NUMERIC_FIELDS = ["total", "vat"]

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
NUMBER_RE = re.compile(r"^-?\d+\.\d{2}$")

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_row(where, row):
    """row: dict of field -> value, values as read (str for CSV, native for JSON)."""
    # sequenceNo
    seq = row.get("sequenceNo")
    if isinstance(seq, bool) or not isinstance(seq, int):
        try:
            int(str(seq).strip())
        except (TypeError, ValueError):
            err(f"{where}: sequenceNo is not a whole number: {seq!r}")

    # dates
    date = row.get("invoiceDate")
    if date is None or str(date).strip() == "":
        warn(f"{where}: invoiceDate is empty")
    elif not DATE_RE.match(str(date)):
        err(f"{where}: invoiceDate {date!r} is not in dd/mm/yyyy format")

    # numbers
    for field in NUMERIC_FIELDS:
        value = row.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            err(f"{where}: {field} is empty (missing values must be 0.00)")
        elif isinstance(value, str) and not NUMBER_RE.match(value.strip()):
            err(f"{where}: {field} {value!r} is not a number with 2 decimal places")

    # text fields that should carry data
    for field in ("invoiceNo", "supplierName"):
        value = row.get(field)
        if value is None or str(value).strip() == "":
            warn(f"{where}: {field} is empty")


def check_sequence(seqs):
    expected = list(range(1, len(seqs) + 1))
    if seqs != expected:
        err(f"sequenceNo values {seqs} are not 1..{len(seqs)} in order")


def validate_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    rows = [r for r in rows if r and any(cell.strip() for cell in r)]
    if not rows:
        err("file is empty")
        return

    header = [cell.strip() for cell in rows[0]]
    if header != FIELDS:
        err(f"header row is {header}, expected {FIELDS}")
        return

    if len(rows) == 1:
        err("file has a header row but no invoice rows")
        return

    seqs = []
    for index, raw in enumerate(rows[1:], start=1):
        where = f"row {index + 1}"
        if len(raw) != len(FIELDS):
            err(f"{where}: has {len(raw)} fields, expected {len(FIELDS)}")
            continue
        row = dict(zip(FIELDS, [cell.strip() for cell in raw]))
        check_row(where, row)
        try:
            seqs.append(int(row["sequenceNo"]))
        except ValueError:
            seqs.append(None)
    if all(s is not None for s in seqs):
        check_sequence(seqs)


def validate_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        err(f"top level JSON is {type(data).__name__}, expected a list of invoices")
        return
    if not data:
        err("JSON list is empty")
        return

    seqs = []
    for index, row in enumerate(data, start=1):
        where = f"entry {index}"
        if not isinstance(row, dict):
            err(f"{where}: is {type(row).__name__}, expected an object")
            continue

        missing = [f for f in FIELDS if f not in row]
        if missing:
            err(f"{where}: missing field(s) {', '.join(missing)}")
        extra = [k for k in row if k not in FIELDS]
        if extra:
            err(f"{where}: unexpected field(s) {', '.join(extra)}")
        if missing:
            continue

        for field in TEXT_FIELDS:
            if not isinstance(row[field], str):
                err(f"{where}: {field} must be a string, got {type(row[field]).__name__}")
        for field in NUMERIC_FIELDS:
            if isinstance(row[field], bool) or not isinstance(row[field], (int, float)):
                err(f"{where}: {field} must be a number, got {type(row[field]).__name__}")
        if not isinstance(row["invoiceDate"], str):
            err(f"{where}: invoiceDate must be a string, got {type(row['invoiceDate']).__name__}")

        check_row(where, row)
        seq = row["sequenceNo"]
        seqs.append(seq if isinstance(seq, int) and not isinstance(seq, bool) else None)

    if seqs and all(s is not None for s in seqs):
        check_sequence(seqs)


def main():
    parser = argparse.ArgumentParser(description="Validate invoice-extractor output.")
    parser.add_argument("path", help="CSV or JSON output file to validate")
    parser.add_argument("--format", choices=["csv", "json"], help="override format detection")
    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"FAIL: no such file: {args.path}")
        return 2

    fmt = args.format or ("json" if args.path.lower().endswith(".json") else "csv")

    try:
        if fmt == "json":
            validate_json(args.path)
        else:
            validate_csv(args.path)
    except (json.JSONDecodeError, UnicodeDecodeError, csv.Error) as exc:
        print(f"FAIL: could not parse {args.path} as {fmt}: {exc}")
        return 2

    for message in warnings:
        print(f"WARN: {message}")
    for message in errors:
        print(f"ERROR: {message}")

    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s) in {args.path}")
        return 1

    print(f"OK: {args.path} is valid ({fmt}, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
