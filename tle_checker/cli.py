"""Command line entry point: python3 -m tle_checker <file> [--csv out.csv]."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from tle_checker.report import analyze, format_summary, write_csv


def _date(text: str) -> datetime:
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a date in YYYY-MM-DD form")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tle_checker",
        description="Report TLE rows that cannot be trusted, with the reason.",
    )
    parser.add_argument("file", help="TLE file (2-line or 3-line format)")
    parser.add_argument("--csv", metavar="OUT.csv", help="write flagged rows to this CSV file")
    parser.add_argument("--max-age-days", type=float, default=30,
                        help="flag epochs older than this many days (default 30)")
    parser.add_argument("--now", type=_date,
                        help="date to measure epoch age from, YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args(argv)

    now = args.now or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        with open(args.file, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
    except OSError as exc:
        print(f"cannot read {args.file}: {exc.strerror or exc}", file=sys.stderr)
        return 2

    report = analyze(text, now, args.max_age_days)
    print(format_summary(report), end="")

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as out:
                write_csv(report, out)
        except OSError as exc:
            print(f"cannot write {args.csv}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        print(f"wrote {len(report.flags)} flags to {args.csv}")
    return 0
