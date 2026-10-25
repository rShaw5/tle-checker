import unittest
from datetime import datetime, timezone

from tests.helpers import fixture_text
from tle_checker.checks import check_stale
from tle_checker.tle import parse_fields, parse_text


def iss_fields():
    return parse_fields(parse_text(fixture_text("iss_good.tle"))[0])


def day(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


# ISS fixture epoch: 2008 day 264.51782528 = 2008-09-20 12:25 UTC
class StaleCheckTest(unittest.TestCase):
    def test_recent_epoch_passes(self):
        self.assertIsNone(check_stale(iss_fields(), day(2008, 9, 25), 30))

    def test_exactly_at_the_limit_passes(self):
        self.assertIsNone(check_stale(iss_fields(), day(2008, 10, 20), 30))

    def test_just_over_the_limit_is_flagged(self):
        self.assertIsNotNone(check_stale(iss_fields(), day(2008, 10, 21), 30))

    def test_reason_gives_epoch_age_and_limit(self):
        reason = check_stale(iss_fields(), day(2008, 12, 1), 30)
        self.assertIn("2008-09-20", reason)
        self.assertIn("72", reason)  # about 72.5 days old
        self.assertIn("30", reason)

    def test_limit_is_configurable(self):
        self.assertIsNone(check_stale(iss_fields(), day(2008, 12, 1), 100))
        self.assertIsNotNone(check_stale(iss_fields(), day(2008, 9, 30), 5))

    def test_epoch_in_the_future_is_not_flagged(self):
        self.assertIsNone(check_stale(iss_fields(), day(2008, 1, 1), 30))


if __name__ == "__main__":
    unittest.main()
