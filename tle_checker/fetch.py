"""Download CelesTrak's active-satellites TLE feed into data/, at most once per 2 hours.

Run with: python3 -m tle_checker.fetch
CelesTrak asks users not to download the same data again within an update cycle,
so this refuses to download while a saved file is younger than two hours.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from tle_checker.tle import parse_text

URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
MIN_AGE_SECONDS = 2 * 60 * 60
PREFIX = "celestrak-active-"


class FetchError(Exception):
    pass


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "tle-checker/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def recent_file(data_dir: Path, now: datetime) -> Path | None:
    """The newest saved download younger than MIN_AGE_SECONDS, if any."""
    if not data_dir.is_dir():
        return None
    young = [p for p in data_dir.glob(PREFIX + "*.tle")
             if now.timestamp() - p.stat().st_mtime < MIN_AGE_SECONDS]
    return max(young, key=lambda p: p.stat().st_mtime, default=None)


def fetch(data_dir: Path, now: datetime,
          downloader: Callable[[str], bytes] = download) -> tuple[Path, bool]:
    """Return (path, downloaded). downloaded is False when a recent file was reused."""
    data_dir = Path(data_dir)
    existing = recent_file(data_dir, now)
    if existing is not None:
        return existing, False
    try:
        data = downloader(URL)
    except OSError as exc:
        raise FetchError(f"download failed: {exc}") from exc
    text = data.decode("utf-8", errors="replace")
    if not any(not r.problem for r in parse_text(text)):
        raise FetchError("the response does not look like TLE data, so it was not saved")
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / f"{PREFIX}{now:%Y-%m-%dT%H%M}Z.tle"
    partial = target.with_suffix(".part")
    partial.write_bytes(data)
    partial.replace(target)
    return target, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m tle_checker.fetch", description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="data", help="folder for downloads (default: data)")
    args = parser.parse_args(argv)
    try:
        path, downloaded = fetch(Path(args.data_dir), datetime.now(timezone.utc))
    except FetchError as exc:
        print(f"fetch: {exc}", file=sys.stderr)
        return 1
    if downloaded:
        print(f"downloaded {path}")
    else:
        print(f"not downloaded: {path} is younger than 2 hours, using it instead")
    return 0


if __name__ == "__main__":
    sys.exit(main())
