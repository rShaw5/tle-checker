import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.helpers import fixture_text
from tle_checker.fetch import MIN_AGE_SECONDS, URL, FetchError, fetch

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
GOOD = fixture_text("three_line_good.tle").encode()


class Downloader:
    """Stands in for the network: records calls and returns canned bytes."""

    def __init__(self, data=GOOD):
        self.data, self.calls = data, []

    def __call__(self, url):
        self.calls.append(url)
        return self.data


def age_file(path, seconds):
    t = (NOW - timedelta(seconds=seconds)).timestamp()
    os.utime(path, (t, t))


class FetchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "data"

    def test_url_is_the_celestrak_active_group_in_tle_format(self):
        self.assertEqual(URL, "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle")

    def test_downloads_into_a_dated_file_and_creates_the_folder(self):
        dl = Downloader()
        path, downloaded = fetch(self.data_dir, NOW, dl)
        self.assertTrue(downloaded)
        self.assertEqual(dl.calls, [URL])
        self.assertEqual(path.name, "celestrak-active-2026-10-24T1200Z.tle")
        self.assertEqual(path.read_bytes(), GOOD)

    def test_refuses_to_download_when_a_file_is_younger_than_2_hours(self):
        dl = Downloader()
        first, _ = fetch(self.data_dir, NOW, dl)
        age_file(first, 3600)
        again, downloaded = fetch(self.data_dir, NOW, dl)
        self.assertFalse(downloaded)
        self.assertEqual(again, first)
        self.assertEqual(len(dl.calls), 1)

    def test_downloads_again_once_the_file_is_older_than_2_hours(self):
        dl = Downloader()
        first, _ = fetch(self.data_dir, NOW, dl)
        age_file(first, MIN_AGE_SECONDS + 60)
        second, downloaded = fetch(self.data_dir, NOW, dl)
        self.assertTrue(downloaded)
        self.assertEqual(len(dl.calls), 2)

    def test_two_hours_is_the_window(self):
        self.assertEqual(MIN_AGE_SECONDS, 7200)

    def test_other_files_in_the_folder_do_not_block_a_download(self):
        self.data_dir.mkdir()
        (self.data_dir / "notes.txt").write_text("x")
        _, downloaded = fetch(self.data_dir, NOW, Downloader())
        self.assertTrue(downloaded)

    def test_an_empty_response_is_rejected_and_nothing_is_saved(self):
        with self.assertRaises(FetchError):
            fetch(self.data_dir, NOW, Downloader(b""))
        self.assertEqual(list(self.data_dir.glob("*")), [])

    def test_a_response_that_is_not_tle_data_is_rejected(self):
        with self.assertRaises(FetchError):
            fetch(self.data_dir, NOW, Downloader(b"<html>rate limited</html>"))
        self.assertEqual(list(self.data_dir.glob("*")), [])

    def test_a_failed_download_does_not_block_the_next_try(self):
        def broken(url):
            raise OSError("network down")

        with self.assertRaises(FetchError):
            fetch(self.data_dir, NOW, broken)
        _, downloaded = fetch(self.data_dir, NOW, Downloader())
        self.assertTrue(downloaded)


if __name__ == "__main__":
    unittest.main()
