import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csv_data_doctor import infer_type, main, profile

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "csv_data_doctor.py",
)


def write_temp(content, suffix=".csv", encoding="utf-8"):
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding=encoding
    )
    handle.write(content)
    handle.close()
    return handle.name


def profile_of(content, delimiter=","):
    path = write_temp(content)
    try:
        return profile(path, delimiter)
    finally:
        os.unlink(path)


def column(report, name):
    for col in report["column_profiles"]:
        if col["name"] == name:
            return col
    raise AssertionError(f"column {name!r} not found")


def run_cli(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True,
        text=True,
    )


class TestMissingAndShape(unittest.TestCase):
    def test_missing_count_and_percent(self):
        report = profile_of("a,b\n1,\n,2\n3,4\n")
        self.assertEqual(column(report, "a")["missing"], 1)
        self.assertEqual(column(report, "a")["missing_percent"], 33.33)
        self.assertEqual(column(report, "b")["missing"], 1)

    def test_whitespace_only_counts_as_missing(self):
        report = profile_of("a\n   \n5\n")
        self.assertEqual(column(report, "a")["missing"], 1)

    def test_duplicate_rows_counted(self):
        report = profile_of("a,b\n1,2\n3,4\n1,2\n1,2\n")
        self.assertEqual(report["duplicate_rows"], 2)

    def test_wrong_length_rows_counted_and_excluded(self):
        report = profile_of("a,b\n1,2\n3,4,5\n6,7\n")
        self.assertEqual(report["wrong_length_rows"], [3])
        self.assertEqual(report["rows"], 3)
        self.assertEqual(column(report, "a")["distinct"], 2)

    def test_entirely_empty_column(self):
        report = profile_of("a,b\n1,\n2,\n")
        self.assertEqual(report["entirely_empty_columns"], ["b"])
        self.assertEqual(column(report, "b")["missing"], 2)
        self.assertEqual(column(report, "b")["missing_percent"], 100.0)

    def test_distinct_count_ignores_missing(self):
        report = profile_of("a\nx\nx\n\n y\n")
        self.assertEqual(column(report, "a")["distinct"], 2)


class TestTypeInference(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(infer_type(["1", "-4", "+7"]), "integer")

    def test_float(self):
        self.assertEqual(infer_type(["1.5", "2"]), "float")
        self.assertEqual(infer_type(["1e3", "2.5"]), "float")

    def test_boolean(self):
        self.assertEqual(infer_type(["yes", "NO", "True"]), "boolean")

    def test_date(self):
        self.assertEqual(infer_type(["2024-01-01", "2023-12-31"]), "date")

    def test_string(self):
        self.assertEqual(infer_type(["hello", "world"]), "string")

    def test_mixed_number_and_string(self):
        self.assertEqual(infer_type(["12", "hello"]), "mixed")

    def test_mixed_date_and_string(self):
        self.assertEqual(infer_type(["2024-01-01", "soon"]), "mixed")

    def test_invalid_date_is_string(self):
        self.assertEqual(infer_type(["2024-02-30"]), "string")


class TestNumericStats(unittest.TestCase):
    def test_min_max_mean(self):
        report = profile_of("n\n10\n20\n30\n")
        col = column(report, "n")
        self.assertEqual(col["min"], 10.0)
        self.assertEqual(col["max"], 30.0)
        self.assertEqual(col["mean"], 20.0)

    def test_no_stats_for_string_column(self):
        report = profile_of("s\na\nb\n")
        col = column(report, "s")
        self.assertNotIn("min", col)
        self.assertNotIn("mean", col)


class TestInputHandling(unittest.TestCase):
    def test_utf8_bom_stripped(self):
        path = write_temp("a,b\n1,2\n", encoding="utf-8-sig")
        try:
            report = profile(path, ",")
        finally:
            os.unlink(path)
        self.assertEqual(report["column_profiles"][0]["name"], "a")

    def test_quoted_fields_with_commas(self):
        report = profile_of('name,age\n"Doe, Jane",34\n')
        self.assertEqual(column(report, "name")["distinct"], 1)
        self.assertEqual(column(report, "age")["type"], "integer")

    def test_tab_delimiter(self):
        report = profile_of("a\tb\n1\t2\n", delimiter="\t")
        self.assertEqual(report["columns"], 2)
        self.assertEqual(column(report, "a")["type"], "integer")

    def test_empty_file_errors(self):
        path = write_temp("")
        try:
            with self.assertRaises(ValueError):
                profile(path, ",")
        finally:
            os.unlink(path)


class TestCli(unittest.TestCase):
    def test_json_output_parses(self):
        path = write_temp("a,b\n1,2\n")
        try:
            result = run_cli([path, "--json"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["rows"], 1)
        self.assertEqual(data["columns"], 2)

    def test_check_exits_1_on_missing(self):
        path = write_temp("a,b\n1,\n")
        try:
            result = run_cli([path, "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)

    def test_check_exits_1_on_duplicates(self):
        path = write_temp("a\n1\n1\n")
        try:
            result = run_cli([path, "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)

    def test_check_exits_1_on_wrong_length(self):
        path = write_temp("a,b\n1,2,3\n")
        try:
            result = run_cli([path, "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)

    def test_check_exits_1_on_entirely_empty_column(self):
        path = write_temp("a,b\n1,\n2,\n")
        try:
            result = run_cli([path, "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)

    def test_check_exits_0_on_clean(self):
        path = write_temp("a,b\n1,2\n3,4\n")
        try:
            result = run_cli([path, "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 0)

    def test_cli_tab_literal_delimiter(self):
        path = write_temp("a\tb\n1\t2\n")
        try:
            result = run_cli([path, "--delimiter", "\\t", "--check"])
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 0)

    def test_cli_missing_file_exits_2(self):
        result = run_cli(["/tmp/does-not-exist-csv-doctor.csv"])
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
