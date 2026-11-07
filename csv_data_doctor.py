#!/usr/bin/env python3
"""csv-data-doctor: profile a CSV file fully locally.

Usage:
    python3 csv_data_doctor.py data.csv
    python3 csv_data_doctor.py data.csv --json
    python3 csv_data_doctor.py data.csv --check
    python3 csv_data_doctor.py data.tsv --delimiter '\t'

The first row is treated as the header. Quoted fields are handled by
the csv module, and a UTF-8 BOM at the start of the file is stripped.

A value counts as missing when it is empty or whitespace only.
Per-column statistics are computed only from rows whose field count
matches the header; rows with a wrong field count are counted and
reported separately, so they cannot skew a column's numbers.

Type inference rule, applied to the non-missing values of a column:
each value is classified as integer, float, boolean, date, or
string. Integer means an optional sign followed by digits only.
Float means it parses as a float but is not an integer. Boolean
means one of true, false, yes, no (any case). Date means an ISO
date, YYYY-MM-DD, that is a real calendar date. Anything else is a
string. If every value has the same class, that is the column type,
except that integer mixed with float becomes float. If any string
is mixed with another class, or boolean or date is mixed with a
different class, the column type is mixed. A column with no
non-missing values is reported as string and listed as entirely
empty.
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime

BOOLEAN_VALUES = {"true", "false", "yes", "no"}
INTEGER_RE = re.compile(r"^[+-]?\d+$")


def classify_value(value):
    """Classify one non-missing value into integer, float, boolean,
    date, or string, following the rule in the module docstring."""
    text = value.strip()
    if INTEGER_RE.match(text):
        return "integer"
    if text.lower() in BOOLEAN_VALUES:
        return "boolean"
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return "date"
    except ValueError:
        pass
    if text.lower() in ("nan", "inf", "+inf", "-inf", "infinity"):
        return "string"
    try:
        float(text)
        return "float"
    except ValueError:
        pass
    return "string"


def infer_type(values):
    """Infer a column type from its non-missing values."""
    if not values:
        return "string"
    classes = {classify_value(v) for v in values}
    if len(classes) == 1:
        return classes.pop()
    if classes <= {"integer", "float"}:
        return "float"
    return "mixed"


def profile(path, delimiter):
    """Profile the CSV at path. Returns a report dict."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if not rows:
        raise ValueError("file is empty: no header row found")
    header = rows[0]
    column_count = len(header)
    data_rows = rows[1:]

    wrong_length_rows = []
    good_rows = []
    for index, row in enumerate(data_rows, start=2):
        if len(row) != column_count:
            wrong_length_rows.append(index)
        else:
            good_rows.append(row)

    seen = set()
    duplicate_count = 0
    for row in data_rows:
        key = tuple(row)
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)

    columns = []
    for col_index, name in enumerate(header):
        values = [row[col_index] for row in good_rows]
        non_missing = [v for v in values if v.strip() != ""]
        missing = len(values) - len(non_missing)
        total = len(values)
        missing_percent = round(100.0 * missing / total, 2) if total else 0.0
        col_type = infer_type(non_missing)
        column = {
            "name": name,
            "missing": missing,
            "missing_percent": missing_percent,
            "distinct": len(set(non_missing)),
            "type": col_type,
        }
        if col_type in ("integer", "float"):
            numbers = [float(v) for v in non_missing]
            column["min"] = min(numbers)
            column["max"] = max(numbers)
            column["mean"] = round(sum(numbers) / len(numbers), 4)
        if not non_missing:
            column["entirely_empty"] = True
        columns.append(column)

    entirely_empty = [c["name"] for c in columns if c.get("entirely_empty")]
    total_missing = sum(c["missing"] for c in columns)
    has_issues = (
        total_missing > 0
        or duplicate_count > 0
        or len(wrong_length_rows) > 0
        or len(entirely_empty) > 0
    )
    return {
        "file": path,
        "rows": len(data_rows),
        "columns": column_count,
        "column_profiles": columns,
        "duplicate_rows": duplicate_count,
        "wrong_length_rows": wrong_length_rows,
        "entirely_empty_columns": entirely_empty,
        "has_issues": has_issues,
    }


def format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def render_text(report):
    lines = []
    lines.append("CSV profile: " + report["file"])
    lines.append("=" * (len(lines[0])))
    lines.append(f"Rows: {report['rows']}")
    lines.append(f"Columns: {report['columns']}")
    lines.append(f"Duplicate rows: {report['duplicate_rows']}")
    if report["wrong_length_rows"]:
        lines.append(
            "Rows with wrong field count: "
            + str(len(report["wrong_length_rows"]))
            + " (row numbers: "
            + ", ".join(str(n) for n in report["wrong_length_rows"])
            + ")"
        )
    else:
        lines.append("Rows with wrong field count: 0")
    if report["entirely_empty_columns"]:
        lines.append(
            "Entirely empty columns: "
            + ", ".join(report["entirely_empty_columns"])
        )
    else:
        lines.append("Entirely empty columns: none")
    lines.append("")
    lines.append("Columns:")
    for col in report["column_profiles"]:
        line = (
            f"  {col['name']}: type={col['type']}, "
            f"missing={col['missing']} ({col['missing_percent']}%), "
            f"distinct={col['distinct']}"
        )
        if "min" in col:
            line += (
                f", min={format_number(col['min'])}, "
                f"max={format_number(col['max'])}, "
                f"mean={format_number(col['mean'])}"
            )
        lines.append(line)
    return "\n".join(lines)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Profile a CSV file: missing values, types, "
        "numeric stats, duplicates, and shape problems."
    )
    parser.add_argument("csv_path", help="path to the CSV file")
    parser.add_argument(
        "--json", action="store_true", help="print the report as JSON"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when the file has any missing values, duplicate "
        "rows, wrong-length rows, or entirely empty columns; exit 0 "
        "otherwise",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="field delimiter (default: comma; pass the literal "
        "string \\t for a tab)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    delimiter = args.delimiter
    if delimiter == "\\t":
        delimiter = "\t"
    if len(delimiter) != 1:
        print("error: --delimiter must be a single character", file=sys.stderr)
        return 2
    try:
        report = profile(args.csv_path, delimiter)
    except FileNotFoundError:
        print(f"error: file not found: {args.csv_path}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    if args.check and report["has_issues"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
