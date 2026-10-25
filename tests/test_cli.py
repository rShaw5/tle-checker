import contextlib
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import FIXTURES
from tle_checker.cli import main

ROOT = Path(__file__).parent.parent


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main([str(a) for a in args])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_prints_summary_and_exits_zero_even_when_rows_are_flagged(self):
        code, out, _ = run_cli(FIXTURES / "bad_checksum.tle", "--now", "2008-09-25")
        self.assertEqual(code, 0)
        self.assertIn("rows read: 1", out)
        self.assertIn("checksum: 1", out)

    def test_csv_option_writes_flagged_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "out.csv")
            code, _, _ = run_cli(FIXTURES / "duplicates.tle", "--now", "2008-09-25", "--csv", target)
            self.assertEqual(code, 0)
            with open(target, newline="") as f:
                rows = list(csv.reader(f))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][2], "duplicate")

    def test_max_age_days_option(self):
        _, out, _ = run_cli(FIXTURES / "iss_good.tle", "--now", "2008-12-01", "--max-age-days", "100")
        self.assertIn("stale: 0", out)
        _, out, _ = run_cli(FIXTURES / "iss_good.tle", "--now", "2008-12-01")
        self.assertIn("stale: 1", out)

    def test_default_now_is_today(self):
        code, out, _ = run_cli(FIXTURES / "iss_good.tle")
        self.assertEqual(code, 0)
        self.assertIn("stale: 1", out)  # a 2008 epoch is stale today

    def test_missing_file_exits_nonzero_with_a_message(self):
        code, _, err = run_cli("/no/such/file.tle")
        self.assertNotEqual(code, 0)
        self.assertIn("cannot read", err)

    def test_directory_as_input_exits_nonzero(self):
        code, _, _ = run_cli(FIXTURES)
        self.assertNotEqual(code, 0)

    def test_bad_now_date_exits_nonzero(self):
        code, _, _ = run_cli(FIXTURES / "iss_good.tle", "--now", "yesterday")
        self.assertNotEqual(code, 0)

    def test_file_that_is_not_utf8_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "binary.tle")
            with open(path, "wb") as f:
                f.write(b"\xff\xfe\x00junk\n")
            code, out, _ = run_cli(path)
        self.assertEqual(code, 0)
        self.assertIn("rows read: 1", out)

    def test_runs_as_a_module(self):
        result = subprocess.run(
            [sys.executable, "-m", "tle_checker", str(FIXTURES / "iss_good.tle"), "--now", "2008-09-25"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("rows read: 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
