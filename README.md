# tle-checker

Checks public satellite orbit data and reports every row that can't be trusted, with the reason.

Satellite positions are published as two-line element sets (TLEs): two 69-character lines of fixed-width numbers per object. Tracking software, collision screening and pass predictions all start from them, so a corrupted digit or an out-of-date row turns into a wrong answer further down the line. This tool reads a TLE file and flags the rows that fail any of six checks.

## The checks

| Check | What it catches | Why it matters |
|---|---|---|
| **checksum** | The last digit of each line must equal the sum of the line's digits (a minus sign counts as 1), mod 10. | A mismatch means the line was changed or corrupted after it was written. |
| **pairing** | Line 1 starts with `1 `, line 2 with `2 `, and both carry the same catalog number. | Two lines from different satellites glued together describe an orbit nobody is on. |
| **ranges** | Inclination 0 to 180°, eccentricity 0 up to 1, mean motion above 0, and the three angles 0 to 360°. | Values outside these ranges can't describe a real orbit. |
| **orbit** | Works out the orbit's size from the mean motion (Kepler's third law), then its lowest point from the eccentricity. Flags any orbit whose lowest point is below Earth's surface. | Each number can be in range while the combination is impossible. |
| **stale** | Flags rows whose epoch is older than a limit (default 30 days). | Predictions from old elements drift further from the real position every day. |
| **duplicate** | The same catalog number appearing more than once with different elements. | Two different answers for one object means at least one is wrong. |

Rows the parser can't read at all are reported as **malformed** instead of being skipped.

## A real run

Against CelesTrak's active-satellites feed, downloaded 2026-10-25 06:39 UTC:

| | Rows |
|---|---|
| Rows read | 15,910 |
| Flagged at the default 30-day limit | 0 |
| Flagged at a 3-day limit | 118, all stale |

The oldest epoch in the download was 18.9 days old and the median was 0.8 days. CelesTrak already cleans this feed, so a clean result is the expected one; the checks earn their place on data that hasn't been through that, such as hand-edited files, old archives, or copies passed between tools.

Here is what flagged rows look like, from the deliberately broken files in `tests/fixtures/` (CSV output, trimmed):

```
catalog_number,name,check,reason
25544,ISS (ZARYA),checksum,line 1 checksum digit is 0 but the digits add up to 7
90010,TOO FAST,orbit,"perigee altitude is -115.6 km, below the Earth's surface (mean motion 17.5 rev/day, eccentricity 0.0006703)"
90011,TOO ECCENTRIC,orbit,"perigee altitude is -320.3 km, below the Earth's surface (mean motion 15.7213 rev/day, eccentricity 0.1)"
25544,ISS MISMATCH,pairing,line 1 has catalog number '25544' but line 2 has '25545'
25544,ISS MISMATCH,duplicate,catalog number 25544 appears 2 times with 2 different sets of elements
```

## Run it

Python 3.10 or later, standard library only. Nothing to install.

```bash
python3 -m unittest -v
```

```bash
python3 -m tle_checker.fetch
```

```bash
python3 -m tle_checker data/celestrak-active-<date>.tle --csv flagged.csv
```

- `fetch` saves the feed into `data/`. CelesTrak asks users not to download the same data again within an update cycle, so it reuses any download younger than two hours instead of fetching again.
- `--max-age-days N` changes the stale limit, and `--now YYYY-MM-DD` measures age from a fixed date, which makes runs repeatable.
- Both 2-line and 3-line (name line first) files work.
- Exit code 0 for a completed run, 2 for unreadable input, an unwritable CSV, or a bad option.

## Tests

98 tests, written before the code they cover. They use small hand-made files in `tests/fixtures/` (a known-good ISS element set plus broken copies of it) and never touch the network. GitHub Actions runs them on every push.

## Known limits

- The checksum misses errors that keep the digit sum the same, such as two swapped digits.
- The perigee figure is an estimate from Kepler's third law. It ignores Earth's flattening and the SGP4 model's corrections, which is enough to catch an orbit that is underground and not enough for close calls.
- A line with the wrong first character is reported as malformed, since the parser pairs lines by that character.
- An epoch later than `--now` is not flagged.
- Duplicates are compared within one file only, and malformed rows are left out of the comparison.
- These fields aren't checked: classification, international designator, drag terms, element set number and revolution number.
- A 2-line file whose first line starts with `1 ` or `2 ` and is really a name would be misread.
- In the CSV, names that start with `=`, `+`, `-` or `@` get a leading apostrophe so spreadsheets don't run them as formulas.

## About the author

Built by Robin Shaw, a software engineer. More of my work is on [my portfolio](https://rshaw5.github.io) and [GitHub](https://github.com/rShaw5), and the best way to reach me is [LinkedIn](https://www.linkedin.com/in/rshaw5/).
