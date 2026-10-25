import unittest
from dataclasses import replace

from tests.helpers import fixture_text
from tle_checker.checks import check_ranges
from tle_checker.tle import parse_fields, parse_text


def iss_fields():
    return parse_fields(parse_text(fixture_text("iss_good.tle"))[0])


class RangesCheckTest(unittest.TestCase):
    def test_iss_passes(self):
        self.assertIsNone(check_ranges(iss_fields()))

    def test_boundary_values_pass(self):
        f = replace(iss_fields(), inclination=180.0, raan=360.0, arg_perigee=0.0,
                    mean_anomaly=360.0, eccentricity=0.0)
        self.assertIsNone(check_ranges(f))

    def test_inclination_above_180(self):
        self.assertIn("inclination", check_ranges(replace(iss_fields(), inclination=190.0)))

    def test_negative_inclination(self):
        self.assertIn("inclination", check_ranges(replace(iss_fields(), inclination=-1.0)))

    def test_eccentricity_of_1_or_more(self):
        self.assertIn("eccentricity", check_ranges(replace(iss_fields(), eccentricity=1.0)))
        self.assertIn("eccentricity", check_ranges(replace(iss_fields(), eccentricity=1.2)))

    def test_zero_mean_motion(self):
        self.assertIn("mean motion", check_ranges(replace(iss_fields(), mean_motion=0.0)))

    def test_negative_mean_motion(self):
        self.assertIn("mean motion", check_ranges(replace(iss_fields(), mean_motion=-2.0)))

    def test_each_angle_above_360(self):
        for name, label in (("raan", "RAAN"), ("arg_perigee", "argument of perigee"),
                            ("mean_anomaly", "mean anomaly")):
            reason = check_ranges(replace(iss_fields(), **{name: 360.5}))
            self.assertIn(label, reason)

    def test_negative_angle(self):
        self.assertIn("RAAN", check_ranges(replace(iss_fields(), raan=-0.5)))

    def test_several_problems_are_all_reported(self):
        reason = check_ranges(replace(iss_fields(), inclination=200.0, mean_motion=0.0))
        self.assertIn("inclination", reason)
        self.assertIn("mean motion", reason)

    def test_reason_includes_the_offending_value(self):
        self.assertIn("190", check_ranges(replace(iss_fields(), inclination=190.0)))

    def test_fixture_file_each_bad_field_is_found(self):
        records = parse_text(fixture_text("bad_ranges.tle"))
        reasons = {r.name: check_ranges(parse_fields(r)) for r in records}
        self.assertIn("inclination", reasons["BAD INCLINATION"])
        self.assertIn("RAAN", reasons["BAD RAAN"])
        self.assertIn("mean motion", reasons["BAD MEAN MOTION"])
        self.assertIn("mean anomaly", reasons["BAD MEAN ANOMALY"])
        self.assertIn("argument of perigee", reasons["BAD ARG PERIGEE"])


if __name__ == "__main__":
    unittest.main()
