import unittest

from tests.helpers import fixture_text
from tle_checker.checks import check_checksum
from tle_checker.tle import parse_text


class ChecksumCheckTest(unittest.TestCase):
    def test_known_good_iss_record_passes(self):
        record = parse_text(fixture_text("iss_good.tle"))[0]
        self.assertIsNone(check_checksum(record))

    def test_wrong_check_digit_on_line_1_is_flagged(self):
        record = parse_text(fixture_text("bad_checksum.tle"))[0]
        reason = check_checksum(record)
        self.assertIn("line 1", reason)
        self.assertIn("checksum", reason)
        self.assertIn("0", reason)  # the digit found in the file
        self.assertIn("7", reason)  # the digit the line adds up to

    def test_both_lines_wrong_reports_both(self):
        good = parse_text(fixture_text("iss_good.tle"))[0]
        bad = type(good)(good.name, good.line1[:-1] + "1", good.line2[:-1] + "1", 1)
        reason = check_checksum(bad)
        self.assertIn("line 1", reason)
        self.assertIn("line 2", reason)

    def test_last_character_that_is_not_a_digit_is_flagged(self):
        good = parse_text(fixture_text("iss_good.tle"))[0]
        bad = type(good)(good.name, good.line1[:-1] + "X", good.line2, 1)
        self.assertIn("not a digit", check_checksum(bad))

    def test_lines_of_the_wrong_length_are_left_to_the_malformed_check(self):
        good = parse_text(fixture_text("iss_good.tle"))[0]
        short = type(good)(good.name, good.line1[:50], good.line2, 1)
        self.assertIsNone(check_checksum(short))

    def test_record_with_a_missing_line_is_skipped(self):
        record = parse_text("this is not a tle\n")[0]
        self.assertIsNone(check_checksum(record))


class MalformedCheckTest(unittest.TestCase):
    def test_good_record_is_fine(self):
        from tle_checker.checks import check_malformed

        record = parse_text(fixture_text("iss_good.tle"))[0]
        self.assertIsNone(check_malformed(record))

    def test_every_row_of_the_messy_file_is_flagged_with_a_reason(self):
        from tle_checker.checks import check_malformed

        records = parse_text(fixture_text("malformed.tle"))
        reasons = [check_malformed(r) for r in records]
        self.assertTrue(all(reasons), reasons)

    def test_truncated_line_names_the_length(self):
        from tle_checker.checks import check_malformed

        records = parse_text(fixture_text("malformed.tle"))
        truncated = [r for r in records if r.name == "ISS (ZARYA)"][0]
        self.assertIn("40 characters", check_malformed(truncated))


if __name__ == "__main__":
    unittest.main()
