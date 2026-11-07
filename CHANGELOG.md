# Changelog

## 1.0.0 (2026-10-30)

- First release.
- Zero-dependency Python CLI: profile any CSV file fully locally.
- Reports row and column counts, per-column missing count and
  percent, distinct counts, inferred types (integer, float,
  boolean, date, string, mixed), numeric min/max/mean, duplicate
  rows, wrong-length rows, and entirely empty columns.
- `--json`, `--check`, and `--delimiter` flags (including the
  literal string `\t` for tab-separated files).
- Header row, quoted fields, and UTF-8 BOM handling.
- 28 passing tests.
