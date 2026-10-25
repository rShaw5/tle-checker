import unittest

from tests.helpers import fixture_text
from tle_checker.tle import line_checksum, parse_fields, parse_text


class ChecksumArithmeticTest(unittest.TestCase):
    def test_digits_add_up_and_minus_counts_as_one(self):
        # digits 1+2+3 = 6, one minus = 1, letters and spaces = 0
        self.assertEqual(line_checksum("1 2 3 - A"), 7)

    def test_result_is_taken_mod_10(self):
        self.assertEqual(line_checksum("99"), 8)

    def test_only_first_68_characters_count(self):
        body = "1" * 68
        self.assertEqual(line_checksum(body + "9"), line_checksum(body))


class ParseTextTest(unittest.TestCase):
    def test_three_line_format_keeps_the_name(self):
        records = parse_text(fixture_text("iss_good.tle"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "ISS (ZARYA)")
        self.assertTrue(records[0].line1.startswith("1 25544U"))
        self.assertTrue(records[0].line2.startswith("2 25544"))
        self.assertEqual(records[0].problem, "")

    def test_two_line_format_has_no_name(self):
        records = parse_text(fixture_text("two_line_good.tle"))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].name, "")

    def test_catalog_number_comes_from_line_1(self):
        records = parse_text(fixture_text("three_line_good.tle"))
        self.assertEqual([r.catalog for r in records], ["25544", "99001"])

    def test_blank_lines_and_windows_line_endings_are_ignored(self):
        text = fixture_text("iss_good.tle").replace("\n", "\r\n\r\n")
        records = parse_text(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].problem, "")

    def test_empty_input_gives_no_rows(self):
        self.assertEqual(parse_text(""), [])

    def test_line_1_without_line_2_is_a_problem_row(self):
        line1 = fixture_text("iss_good.tle").splitlines()[1]
        records = parse_text("SOME NAME\n" + line1 + "\n")
        self.assertEqual(len(records), 1)
        self.assertIn("line 2", records[0].problem)
        self.assertEqual(records[0].name, "SOME NAME")

    def test_line_2_without_line_1_is_a_problem_row(self):
        line2 = fixture_text("iss_good.tle").splitlines()[2]
        records = parse_text(line2 + "\n")
        self.assertEqual(len(records), 1)
        self.assertIn("line 1", records[0].problem)

    def test_unrecognised_line_is_a_problem_row(self):
        records = parse_text("this is not a tle\n")
        self.assertEqual(len(records), 1)
        self.assertNotEqual(records[0].problem, "")

    def test_every_row_in_a_messy_file_is_kept(self):
        records = parse_text(fixture_text("malformed.tle"))
        self.assertEqual(len(records), 6)

    def test_line_numbers_point_at_the_source_file(self):
        records = parse_text(fixture_text("three_line_good.tle"))
        self.assertEqual([r.line_no for r in records], [2, 5])


class ParseFieldsTest(unittest.TestCase):
    def setUp(self):
        self.record = parse_text(fixture_text("iss_good.tle"))[0]

    def test_reads_the_orbital_elements(self):
        f = parse_fields(self.record)
        self.assertAlmostEqual(f.inclination, 51.6416)
        self.assertAlmostEqual(f.raan, 247.4627)
        self.assertAlmostEqual(f.eccentricity, 0.0006703)
        self.assertAlmostEqual(f.arg_perigee, 130.5360)
        self.assertAlmostEqual(f.mean_anomaly, 325.0288)
        self.assertAlmostEqual(f.mean_motion, 15.72125391)

    def test_epoch_is_a_utc_datetime(self):
        f = parse_fields(self.record)
        self.assertEqual((f.epoch.year, f.epoch.month, f.epoch.day), (2008, 9, 20))
        self.assertEqual(f.epoch.hour, 12)

    def test_two_digit_years_pivot_at_57(self):
        line1 = self.record.line1
        old = type(self.record)(
            self.record.name, line1[:18] + "99" + line1[20:], self.record.line2, 1
        )
        self.assertEqual(parse_fields(old).epoch.year, 1999)

    def test_wrong_length_raises(self):
        short = type(self.record)("", self.record.line1[:60], self.record.line2, 1)
        with self.assertRaises(ValueError):
            parse_fields(short)

    def test_non_numeric_field_raises(self):
        bad = parse_text(fixture_text("malformed.tle"))
        reasons = []
        for r in bad:
            if r.problem:
                continue
            try:
                parse_fields(r)
            except ValueError as e:
                reasons.append(str(e))
        self.assertTrue(any("epoch" in s for s in reasons))
        self.assertTrue(any("eccentricity" in s for s in reasons))

    def test_nan_is_not_accepted_as_a_number(self):
        line2 = self.record.line2[:8] + "     nan" + self.record.line2[16:]
        bad = type(self.record)("", self.record.line1, line2, 1)
        with self.assertRaises(ValueError):
            parse_fields(bad)


if __name__ == "__main__":
    unittest.main()
