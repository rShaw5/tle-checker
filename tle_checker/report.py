"""Run every check over a file's text and format the results."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from typing import TextIO

from tle_checker.checks import (
    check_checksum,
    check_duplicates,
    check_malformed,
    check_orbit,
    check_pairing,
    check_ranges,
    check_stale,
)
from tle_checker.tle import Record, parse_fields, parse_text

CHECKS = ("malformed", "checksum", "pairing", "ranges", "orbit", "stale", "duplicate")


@dataclass(frozen=True)
class Flag:
    record: Record
    check: str
    reason: str


@dataclass
class Report:
    rows_read: int
    flags: list[Flag] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        """Rows flagged by each check (a row is counted once per check)."""
        counts = {name: 0 for name in CHECKS}
        for flag in self.flags:
            counts[flag.check] += 1
        return counts

    @property
    def rows_flagged(self) -> int:
        return len({id(flag.record) for flag in self.flags})


def analyze(text: str, now: datetime, max_age_days: float = 30) -> Report:
    records = parse_text(text)
    duplicates = check_duplicates(records)
    flags: list[Flag] = []
    for i, record in enumerate(records):
        found: list[tuple[str, str | None]] = [
            ("malformed", check_malformed(record)),
            ("checksum", check_checksum(record)),
            ("pairing", check_pairing(record)),
        ]
        try:
            fields = parse_fields(record)
        except ValueError:
            fields = None  # already reported by the malformed check
        if fields is not None:
            found += [
                ("ranges", check_ranges(fields)),
                ("orbit", check_orbit(fields)),
                ("stale", check_stale(fields, now, max_age_days)),
            ]
        found.append(("duplicate", duplicates.get(i)))
        flags += [Flag(record, name, reason) for name, reason in found if reason]
    return Report(rows_read=len(records), flags=flags)


def format_summary(report: Report) -> str:
    lines = [f"rows read: {report.rows_read}", f"rows flagged: {report.rows_flagged}",
             "flagged rows per check:"]
    lines += [f"  {name}: {count}" for name, count in report.counts.items()]
    return "\n".join(lines) + "\n"


def _safe_cell(text: str) -> str:
    """Stop a spreadsheet from running a name such as '=1+1' as a formula."""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def write_csv(report: Report, out: TextIO) -> None:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["catalog_number", "name", "check", "reason"])
    for flag in report.flags:
        writer.writerow([_safe_cell(flag.record.catalog), _safe_cell(flag.record.name),
                         flag.check, flag.reason])
