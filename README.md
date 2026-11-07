# csv-data-doctor

Profile any CSV file fully locally: row and column counts, missing
values, distinct counts, inferred types, numeric stats, duplicate
rows, wrong-length rows, and entirely empty columns. No account, no
upload, no dependencies. Just Python 3 and the standard library.

## What it reports

- Row count and column count.
- Per column: missing count and percent, distinct value count, and
  inferred type.
- Numeric min, max, and mean for integer and float columns.
- Duplicate row count (each repeat after the first occurrence).
- Rows with a field count different from the header, with row
  numbers.
- Columns that are entirely empty.

## Type inference rule

A value counts as missing when it is empty or whitespace only.
Each non-missing value is classified as integer (optional sign plus
digits only), float (parses as a float but is not an integer),
boolean (true, false, yes, or no, any case), date (a real calendar
date in ISO form, YYYY-MM-DD), or string (anything else). A column
whose values all share one class gets that type, except integer
mixed with float becomes float. Any other mix becomes mixed. A
column with no non-missing values is reported as string and listed
as entirely empty.

Per-column statistics come only from rows whose field count matches
the header, so a malformed row cannot skew a column's numbers.
Duplicate detection uses every data row, including malformed ones.

## Usage

```sh
python3 csv_data_doctor.py data.csv
python3 csv_data_doctor.py data.csv --json
python3 csv_data_doctor.py data.csv --check
python3 csv_data_doctor.py data.tsv --delimiter '\t'
```

`--json` prints the full report as JSON. `--check` exits 1 when the
file has any missing values, duplicate rows, wrong-length rows, or
entirely empty columns, and exits 0 otherwise, so it works as a gate
in a script. `--delimiter` defaults to a comma; pass the literal
string `\t` for a tab-separated file. The first row is the header,
quoted fields are handled, and a UTF-8 BOM is stripped.

## Real examples

Running it on `examples/messy.csv` (a duplicate row, two missing
values, and one row with an extra field) gives:

```
CSV profile: examples/messy.csv
===============================
Rows: 5
Columns: 6
Duplicate rows: 1
Rows with wrong field count: 1 (row numbers: 6)
Entirely empty columns: none

Columns:
  name: type=string, missing=0 (0.0%), distinct=3
  age: type=integer, missing=1 (25.0%), distinct=2, min=29, max=34, mean=32.3333
  score: type=float, missing=0 (0.0%), distinct=3, min=72, max=91, mean=85
  subscribed: type=boolean, missing=0 (0.0%), distinct=3
  joined: type=date, missing=0 (0.0%), distinct=3
  notes: type=string, missing=1 (25.0%), distinct=2
```

That same file with `--check` exits 1, because it has missing
values, a duplicate row, and a wrong-length row.

Running it on `examples/clean.csv` gives:

```
CSV profile: examples/clean.csv
===============================
Rows: 3
Columns: 5
Duplicate rows: 0
Rows with wrong field count: 0
Entirely empty columns: none

Columns:
  name: type=string, missing=0 (0.0%), distinct=3
  age: type=integer, missing=0 (0.0%), distinct=3, min=28, max=34, mean=30.3333
  score: type=float, missing=0 (0.0%), distinct=3, min=72, max=91, mean=83.8333
  subscribed: type=boolean, missing=0 (0.0%), distinct=3
  joined: type=date, missing=0 (0.0%), distinct=3
```

That file with `--check` exits 0.

## Limitations

- The whole file is read into memory, so very large CSVs (many
  millions of rows) may be slow or memory heavy.
- Only one header row is supported; files without a header are
  treated as if their first data row were the header.
- Date detection covers ISO dates (YYYY-MM-DD) only; other date
  formats are reported as strings.
- Boolean detection covers true, false, yes, and no only; 1 and 0
  are reported as integers.
- This is a profiler, not a validator: it describes the file, it
  does not judge whether the data is correct for your use case.

## Tests

```sh
python3 -m unittest discover -s tests
```

28 tests, covering missing values, duplicates, type inference for
each type, numeric stats, wrong-length rows, empty columns, BOM and
quoted-field handling, tab delimiters, `--json` output, and
`--check` exit codes.

## License

MIT. See `LICENSE`.
