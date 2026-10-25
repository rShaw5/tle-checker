"""The checks. Each returns None when the row passes, or a plain-language reason."""
from __future__ import annotations

import math

from tle_checker.tle import LINE_LENGTH, Fields, Record, line_checksum, parse_fields

MU_KM3_S2 = 398600.4418  # Earth's gravitational parameter
EARTH_RADIUS_KM = 6378.137  # equatorial radius


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


def check_ranges(f: Fields) -> str | None:
    """Values must be inside the ranges the element set allows."""
    problems = []
    if not 0 <= f.inclination <= 180:
        problems.append(f"inclination {f.inclination:g} is outside 0 to 180 degrees")
    if not 0 <= f.eccentricity < 1:
        problems.append(f"eccentricity {f.eccentricity:g} is outside 0 up to (not including) 1")
    if not f.mean_motion > 0:
        problems.append(f"mean motion {f.mean_motion:g} is not above 0 revolutions per day")
    for label, value in (("RAAN", f.raan), ("argument of perigee", f.arg_perigee),
                         ("mean anomaly", f.mean_anomaly)):
        if not 0 <= value <= 360:
            problems.append(f"{label} {value:g} is outside 0 to 360 degrees")
    return "; ".join(problems) or None


def semi_major_axis_km(mean_motion_rev_per_day: float) -> float:
    """Kepler's third law: a = (mu / n^2) ** (1/3), with n in radians per second."""
    n = mean_motion_rev_per_day * 2 * math.pi / 86400
    return (MU_KM3_S2 / n**2) ** (1 / 3)


def perigee_altitude_km(f: Fields) -> float:
    return semi_major_axis_km(f.mean_motion) * (1 - f.eccentricity) - EARTH_RADIUS_KM


def check_orbit(f: Fields) -> str | None:
    """The lowest point of the orbit must not be below the Earth's surface."""
    if not f.mean_motion > 0:
        return None  # reported by the range check
    altitude = perigee_altitude_km(f)
    if altitude < 0:
        return (f"perigee altitude is {altitude:.1f} km, below the Earth's surface "
                f"(mean motion {f.mean_motion:g} rev/day, eccentricity {f.eccentricity:g})")
    return None
