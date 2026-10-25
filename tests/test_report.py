import csv
import io
import unittest
from datetime import datetime, timezone

from tests.helpers import fixture_text
from tle_checker.report import CHECKS, analyze, format_summary, write_csv

NOW = datetime(2008, 9, 25, tzinfo=timezone.utc)


def run(name, **kw):
    return analyze(fixture_text(name), NOW, **kw)


class AnalyzeTest(unittest.TestCase):
    def test_clean_file_has_no_flags(self):
        report = run("three_line_good.tle")
        self.assertEqual(report.rows_read, 2)
        self.assertEqual(report.flags, [])
        self.assertEqual(report.rows_flagged, 0)

    def test_checksum_failure_flags_only_the_checksum_check(self):
        report = run("bad_checksum.tle")
        self.assertEqual([f.check for f in report.flags], ["checksum"])

    def test_pairing_failure(self):
        report = run("pairing_mismatch.tle")
        self.assertEqual([f.check for f in report.flags], ["pairing"])

    def test_range_failures(self):
        report = run("bad_ranges.tle")
        self.assertEqual(report.rows_read, 5)
        self.assertEqual(report.counts["ranges"], 5)
        self.assertEqual(report.counts["orbit"], 0)

    def test_orbit_failures(self):
        report = run("impossible_orbit.tle")
        self.assertEqual(report.rows_read, 3)
        self.assertEqual(report.counts["orbit"], 2)
        self.assertEqual(report.counts["ranges"], 0)

    def test_stale_follows_the_now_date_and_limit(self):
        later = analyze(fixture_text("iss_good.tle"), datetime(2008, 12, 1, tzinfo=timezone.utc))
        self.assertEqual(later.counts["stale"], 1)
        looser = analyze(fixture_text("iss_good.tle"),
                         datetime(2008, 12, 1, tzinfo=timezone.utc), max_age_days=100)
        self.assertEqual(looser.counts["stale"], 0)

    def test_duplicates(self):
        report = run("duplicates.tle")
        self.assertEqual(report.rows_read, 4)
        self.assertEqual(report.counts["duplicate"], 2)
        self.assertEqual(report.rows_flagged, 2)

    def test_malformed_input_is_flagged_not_a_crash(self):
        report = run("malformed.tle")
        self.assertEqual(report.rows_read, 6)
        self.assertEqual(report.counts["malformed"], 6)
        self.assertEqual(report.rows_flagged, 6)

    def test_binary_style_garbage_does_not_crash(self):
        report = analyze("\x00\x01\xff garbage\n1 \n2 \n1 2\n", NOW)
        self.assertGreaterEqual(report.rows_read, 1)

    def test_a_row_failing_two_checks_counts_once_in_rows_flagged(self):
        text = fixture_text("bad_checksum.tle")
        report = analyze(text, datetime(2008, 12, 1, tzinfo=timezone.utc))
        self.assertEqual({f.check for f in report.flags}, {"checksum", "stale"})
        self.assertEqual(report.rows_flagged, 1)

    def test_flags_keep_file_order(self):
        report = run("bad_ranges.tle")
        self.assertEqual([f.record.name for f in report.flags][0], "BAD INCLINATION")


class OutputTest(unittest.TestCase):
    def test_summary_lists_rows_and_every_check(self):
        text = format_summary(run("duplicates.tle"))
        self.assertIn("rows read: 4", text)
        self.assertIn("rows flagged: 2", text)
        for check in CHECKS:
            self.assertIn(check + ":", text)
        self.assertIn("duplicate: 2", text)

    def test_csv_has_header_and_one_line_per_flag(self):
        buf = io.StringIO()
        write_csv(run("bad_checksum.tle"), buf)
        rows = list(csv.reader(io.StringIO(buf.getvalue())))
        self.assertEqual(rows[0], ["catalog_number", "name", "check", "reason"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][:3], ["25544", "ISS (ZARYA)", "checksum"])
        self.assertIn("checksum", rows[1][3])

    def test_csv_neutralises_names_that_a_spreadsheet_would_run_as_a_formula(self):
        line1, line2 = fixture_text("bad_checksum.tle").splitlines()[1:3]
        buf = io.StringIO()
        write_csv(analyze("=HYPERLINK(1)\n" + line1 + "\n" + line2 + "\n", NOW), buf)
        rows = list(csv.reader(io.StringIO(buf.getvalue())))
        self.assertEqual(rows[1][1], "'=HYPERLINK(1)")


if __name__ == "__main__":
    unittest.main()
