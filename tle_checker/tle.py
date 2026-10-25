"""Parsing of TLE text into records and numeric fields. Standard library only."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

LINE_LENGTH = 69
_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")


@dataclass(frozen=True)
class Record:
    """One satellite entry as found in the file.

    line1 or line2 is an empty string when the file did not contain it.
    problem is set by the parser when the lines could not be paired.
    line_no is the 1-based line number of the first line of the entry.
    """

    name: str
    line1: str
    line2: str
    line_no: int
    problem: str = ""

    @property
    def catalog(self) -> str:
        for line in (self.line1, self.line2):
            if len(line) >= 7:
                return line[2:7].strip()
        return ""


@dataclass(frozen=True)
class Fields:
    epoch: datetime
    inclination: float
    raan: float
    eccentricity: float
    arg_perigee: float
    mean_anomaly: float
    mean_motion: float


def line_checksum(line: str) -> int:
    """Sum of the digits in the first 68 characters, '-' counting as 1, mod 10."""
    total = 0
    for ch in line[:68]:
        if ch in "0123456789":
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def parse_text(text: str) -> list[Record]:
    """Split TLE text (2-line or 3-line format) into records, keeping every row.

    Anything that cannot be paired becomes a Record with problem set.
    """
    lines = [(n, s.rstrip()) for n, s in enumerate(text.splitlines(), start=1)]
    lines = [(n, s) for n, s in lines if s.strip()]
    records: list[Record] = []
    i = 0
    while i < len(lines):
        n, text_line = lines[i]
        nxt = lines[i + 1][1] if i + 1 < len(lines) else None
        if text_line.startswith("1 "):
            if nxt is not None and nxt.startswith("2 "):
                records.append(Record("", text_line, nxt, n))
                i += 2
            else:
                records.append(Record("", text_line, "", n, "line 1 is not followed by line 2"))
                i += 1
        elif text_line.startswith("2 "):
            records.append(Record("", "", text_line, n, "line 2 has no line 1 before it"))
            i += 1
        elif nxt is not None and nxt.startswith("1 "):
            # Name line. Pair it with the line 1 / line 2 that follow.
            n1, line1 = lines[i + 1]
            if i + 2 < len(lines) and lines[i + 2][1].startswith("2 "):
                records.append(Record(text_line.strip(), line1, lines[i + 2][1], n1))
                i += 3
            else:
                records.append(
                    Record(text_line.strip(), line1, "", n1, "line 1 is not followed by line 2")
                )
                i += 2
        else:
            records.append(
                Record(text_line.strip(), "", "", n,
                       "unrecognised line (expected a name, line 1 or line 2)")
            )
            i += 1
    return records


def _number(text: str, label: str) -> float:
    s = text.strip()
    if not _NUMBER.fullmatch(s):
        raise ValueError(f"{label} field is not a number: {text!r}")
    return float(s)


def parse_fields(record: Record) -> Fields:
    """Read the numeric elements. Raises ValueError if any field is unreadable."""
    for label, line in (("line 1", record.line1), ("line 2", record.line2)):
        if len(line) != LINE_LENGTH:
            raise ValueError(f"{label} has {len(line)} characters, expected {LINE_LENGTH}")
    l1, l2 = record.line1, record.line2

    year_text = l1[18:20]
    if not year_text.isdigit() or not year_text.isascii():
        raise ValueError(f"epoch year field is not a number: {year_text!r}")
    year = int(year_text)
    year += 2000 if year < 57 else 1900
    day = _number(l1[20:32], "epoch day")
    if not 1 <= day < 367:
        raise ValueError(f"epoch day {day} is outside 1 to 366.99")
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1)

    ecc_text = l2[26:33]
    if not (ecc_text.isdigit() and ecc_text.isascii()):
        raise ValueError(f"eccentricity field is not 7 digits: {ecc_text!r}")

    return Fields(
        epoch=epoch,
        inclination=_number(l2[8:16], "inclination"),
        raan=_number(l2[17:25], "RAAN"),
        eccentricity=int(ecc_text) / 1e7,
        arg_perigee=_number(l2[34:42], "argument of perigee"),
        mean_anomaly=_number(l2[43:51], "mean anomaly"),
        mean_motion=_number(l2[52:63], "mean motion"),
    )
