"""The checks. Each returns None when the row passes, or a plain-language reason."""
from __future__ import annotations

from tle_checker.tle import LINE_LENGTH, Record, line_checksum, parse_fields


def check_malformed(record: Record) -> str | None:
    """Rows the parser could not pair, or whose lines cannot be read as numbers."""
    if record.problem:
        return record.problem
    try:
        parse_fields(record)
    except ValueError as exc:
        return str(exc)
    return None


def check_checksum(record: Record) -> str | None:
    """The last character of each 69-character line must equal the digit sum mod 10."""
    problems = []
    for label, line in (("line 1", record.line1), ("line 2", record.line2)):
        if len(line) != LINE_LENGTH:
            continue  # reported by the malformed check
        expected = line_checksum(line)
        found = line[68]
        if found not in "0123456789":
            problems.append(f"{label} checksum character {found!r} is not a digit "
                            f"(digits add up to {expected})")
        elif int(found) != expected:
            problems.append(f"{label} checksum digit is {found} but the digits add up to {expected}")
    return "; ".join(problems) or None


def check_pairing(record: Record) -> str | None:
    """Line 1 starts "1 ", line 2 starts "2 ", and both carry the same catalog number."""
    if record.problem or not record.line1 or not record.line2:
        return None
    problems = []
    if not record.line1.startswith("1 "):
        problems.append('line 1 must start with "1 "')
    if not record.line2.startswith("2 "):
        problems.append('line 2 must start with "2 "')
    cat1, cat2 = record.line1[2:7].strip(), record.line2[2:7].strip()
    if cat1 != cat2:
        problems.append(f"line 1 has catalog number {cat1!r} but line 2 has {cat2!r}")
    return "; ".join(problems) or None
