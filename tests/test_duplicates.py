import unittest

from tests.helpers import fixture_text
from tle_checker.checks import check_duplicates
from tle_checker.tle import parse_text


class DuplicatesCheckTest(unittest.TestCase):
    def test_no_duplicates_gives_no_flags(self):
        records = parse_text(fixture_text("three_line_good.tle"))
        self.assertEqual(check_duplicates(records), {})

    def test_same_catalog_with_different_elements_flags_every_copy(self):
        records = parse_text(fixture_text("duplicates.tle"))
        flags = check_duplicates(records)
        self.assertEqual(sorted(flags), [0, 1])
        self.assertIn("25544", flags[0])
        self.assertIn("2 times", flags[0])

    def test_identical_repeat_is_not_flagged(self):
        records = parse_text(fixture_text("duplicates.tle"))
        flags = check_duplicates(records)
        self.assertNotIn(2, flags)
        self.assertNotIn(3, flags)

    def test_trailing_whitespace_does_not_make_copies_differ(self):
        text = fixture_text("iss_good.tle")
        records = parse_text(text + text.replace("\n", "   \n"))
        self.assertEqual(check_duplicates(records), {})

    def test_rows_that_could_not_be_paired_are_ignored(self):
        records = parse_text(fixture_text("malformed.tle"))
        self.assertEqual(check_duplicates(records), {})


if __name__ == "__main__":
    unittest.main()
