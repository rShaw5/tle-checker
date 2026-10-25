import unittest

from tests.helpers import fixture_text
from tle_checker.checks import check_pairing
from tle_checker.tle import Record, parse_text


class PairingCheckTest(unittest.TestCase):
    def test_matching_pair_passes(self):
        record = parse_text(fixture_text("iss_good.tle"))[0]
        self.assertIsNone(check_pairing(record))

    def test_different_catalog_numbers_are_flagged_with_both_numbers(self):
        record = parse_text(fixture_text("pairing_mismatch.tle"))[0]
        reason = check_pairing(record)
        self.assertIn("25544", reason)
        self.assertIn("25545", reason)

    def test_line_2_not_starting_with_2_is_flagged(self):
        lines = fixture_text("pairing_bad_prefix.tle").splitlines()
        record = Record(lines[0], lines[1], lines[2], 2)
        self.assertIn('line 2 must start with "2 "', check_pairing(record))

    def test_line_1_not_starting_with_1_is_flagged(self):
        lines = fixture_text("iss_good.tle").splitlines()
        record = Record("", "9" + lines[1][1:], lines[2], 1)
        self.assertIn('line 1 must start with "1 "', check_pairing(record))

    def test_parser_reports_a_bad_prefix_as_a_problem_row_instead(self):
        records = parse_text(fixture_text("pairing_bad_prefix.tle"))
        self.assertTrue(all(r.problem for r in records))

    def test_record_with_a_missing_line_is_skipped(self):
        record = parse_text("this is not a tle\n")[0]
        self.assertIsNone(check_pairing(record))


if __name__ == "__main__":
    unittest.main()
