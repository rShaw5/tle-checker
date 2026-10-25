import unittest
from dataclasses import replace

from tests.helpers import fixture_text
from tle_checker.checks import check_orbit, perigee_altitude_km, semi_major_axis_km
from tle_checker.tle import parse_fields, parse_text


def iss_fields():
    return parse_fields(parse_text(fixture_text("iss_good.tle"))[0])


class OrbitMathTest(unittest.TestCase):
    def test_iss_semi_major_axis_is_about_6731_km(self):
        self.assertAlmostEqual(semi_major_axis_km(15.72125391), 6730.96, delta=0.5)

    def test_geostationary_mean_motion_gives_42164_km(self):
        # one revolution per sidereal day
        self.assertAlmostEqual(semi_major_axis_km(1.00273791), 42164.2, delta=1.0)

    def test_iss_perigee_altitude_is_about_348_km(self):
        self.assertAlmostEqual(perigee_altitude_km(iss_fields()), 348.3, delta=0.5)


class OrbitCheckTest(unittest.TestCase):
    def test_iss_passes(self):
        self.assertIsNone(check_orbit(iss_fields()))

    def test_perigee_below_the_surface_is_flagged_with_the_altitude(self):
        reason = check_orbit(replace(iss_fields(), mean_motion=17.5))
        self.assertIn("-115", reason)
        self.assertIn("km", reason)

    def test_high_eccentricity_that_dips_underground_is_flagged(self):
        self.assertIsNotNone(check_orbit(replace(iss_fields(), eccentricity=0.1)))

    def test_perigee_just_above_the_surface_passes(self):
        self.assertIsNone(check_orbit(replace(iss_fields(), eccentricity=0.05)))

    def test_mean_motion_of_zero_is_left_to_the_range_check(self):
        self.assertIsNone(check_orbit(replace(iss_fields(), mean_motion=0.0)))

    def test_fixture_file(self):
        records = parse_text(fixture_text("impossible_orbit.tle"))
        results = {r.name: check_orbit(parse_fields(r)) for r in records}
        self.assertIsNotNone(results["TOO FAST"])
        self.assertIsNotNone(results["TOO ECCENTRIC"])
        self.assertIsNone(results["OK ECCENTRIC"])


if __name__ == "__main__":
    unittest.main()
