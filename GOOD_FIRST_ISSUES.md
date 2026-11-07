# Good first issues

Small, testable tasks for first-time contributors. No network access needed.

1. Add a `--limit` option that profiles only the first N data rows
   of a large file, and report how many rows were skipped. Scope:
   add the flag, slice the rows before profiling, add tests.
2. Report the top 5 most frequent values per string column in the
   JSON output. Scope: extend the column profile, add unit tests,
   document the new field in the README.
3. Accept additional date formats (for example DD/MM/YYYY) in type
   inference, guarded so ambiguous values stay strings. Scope:
   extend the date classifier, add tests for each new format and
   for the ambiguous cases, document the rule.
4. Add a `--column` filter that profiles only one named column.
   Scope: add the flag, filter before profiling, add a CLI test
   for the flag and for an unknown column name.
