"""Extract SSA's published EPUF tables into a committed JSON.

The tables are the reproduction targets for
``populace_dynamics.data.epuf``: every value here is printed by SSA in
Compson (2011, Social Security Bulletin 71(4)) or Compson (2012,
Research and Statistics Note 2012-01) and is recomputed from the staged
EPUF bytes by ``tests/data/test_epuf.py``. Sources are the page texts
committed beside the output (``data/external/epuf_2006/*.source.txt``,
retrieved 2026-10-01 through the in-app browser because www.ssa.gov
answers curl with HTTP 403); each table records the 1-based line of
its caption in that text and the text's SHA-256.

Usage::

    uv run python scripts/extract_epuf_published_tables.py

Writes ``data/external/epuf_2006/published_tables.json``. Deterministic:
re-running on the same texts reproduces the same bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data" / "external" / "epuf_2006"
SSB = FOLDER / "ssb_v71n4p33.source.txt"
RSN = FOLDER / "rsn2012-01.source.txt"
OUT = FOLDER / "published_tables.json"

SSB_URL = "https://www.ssa.gov/policy/docs/ssb/v71n4/v71n4p33.html"
RSN_URL = "https://www.ssa.gov/policy/docs/rsnotes/rsn2012-01.html"

_YEAR = re.compile(r"^(18|19|20)\d\d$")
_FOOTNOTE = re.compile(r"\s+[a-z]$")


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").replace("\xa0", " ").splitlines()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(cell: str) -> float:
    return float(_FOOTNOTE.sub("", cell.strip()).replace(",", ""))


def _caption_line(lines: list[str], caption: str) -> int:
    matches = [i for i, line in enumerate(lines) if line.strip() == caption]
    if len(matches) != 1:
        raise ValueError(f"caption {caption!r} found {len(matches)} times")
    return matches[0]


def _rows(lines: list[str], start: int) -> list[list[str]]:
    """Tab-split year rows after ``start`` until the first non-year row
    that follows at least one year row."""
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        cells = line.split("\t")
        if _YEAR.match(cells[0].strip()):
            rows.append(cells)
        elif rows:
            break
    return rows


def _table(lines, caption, columns, *, kind=float):
    start = _caption_line(lines, caption)
    out = {}
    for cells in _rows(lines, start):
        if len(cells) < len(columns) + 1:
            raise ValueError(f"short row under {caption!r}: {cells}")
        values = [_number(cell) for cell in cells[1 : len(columns) + 1]]
        out[cells[0].strip()] = {
            name: kind(value)
            for name, value in zip(columns, values, strict=False)
        }
    return start + 1, out


def build() -> dict:
    ssb = _lines(SSB)
    rsn = _lines(RSN)
    tables = {}

    line, rows = _table(
        ssb,
        "Table A1.",
        ["all", "men", "men_pct", "women", "women_pct", "unknown"],
    )
    tables["ssb_table_a1_records"] = {
        "source": "ssb",
        "caption_line": line,
        "description": (
            "Number of individuals with taxable earnings records in "
            "EPUF, by sex, 1951-2006 (persons with an annual row)"
        ),
        "unit": "persons",
        "rows": {
            year: {
                key: int(row[key])
                for key in ("all", "men", "women", "unknown")
            }
            for year, row in rows.items()
        },
    }

    line, rows = _table(
        ssb,
        "Table 4.",
        [
            "mean_all",
            "median_all",
            "mean_men",
            "median_men",
            "mean_women",
            "median_women",
            "mean_unknown",
            "median_unknown",
        ],
    )
    tables["ssb_table_4_mean_median"] = {
        "source": "ssb",
        "caption_line": line,
        "description": (
            "Average and median taxable earnings in EPUF, by sex, "
            "1951-2006 (dollars; means rounded to the dollar)"
        ),
        "unit": "dollars",
        "rows": rows,
    }

    for key, caption, columns in (
        (
            "ssb_chart_3_birth_year",
            "### Table equivalent for Chart 3. Number of individuals in "
            "EPUF, by year of birth",
            ["thousands"],
        ),
        (
            "ssb_chart_4_birth_year_sex",
            "### Table equivalent for Chart 4. Number of individuals in "
            "EPUF, by year of birth and sex",
            ["men_thousands", "women_thousands"],
        ),
    ):
        line, rows = _table(ssb, caption, columns)
        tables[key] = {
            "source": "ssb",
            "caption_line": line,
            "description": caption.removeprefix("### Table equivalent for "),
            "unit": "thousands of persons, 2 decimals",
            "rows": rows,
        }

    line, rows = _table(
        rsn,
        "Table 8.",
        [
            "supplement_all",
            "supplement_men",
            "supplement_women",
            "epuf_all",
            "epuf_men",
            "epuf_women",
        ],
    )
    tables["rsn_table_8_pct_below_max"] = {
        "source": "rsn",
        "caption_line": line,
        "description": (
            "Percentage of all, male and female workers with earnings "
            "below the taxable maximum, 1951-2006 (Supplement and EPUF "
            "columns; EPUF columns are the reproduction target)"
        ),
        "unit": "percent, 1 decimal",
        "rows": rows,
    }

    return {
        "schema_version": "epuf_published_tables.v1",
        "generator": "scripts/extract_epuf_published_tables.py",
        "sources": {
            "ssb": {
                "citation": (
                    "Compson, Michael. 2011. 'The 2006 Earnings Public-Use "
                    "Microdata File: An Introduction.' Social Security "
                    "Bulletin 71(4)."
                ),
                "url": SSB_URL,
                "text": str(SSB.relative_to(ROOT)),
                "text_sha256": _sha256(SSB),
            },
            "rsn": {
                "citation": (
                    "Compson, Michael. 2012. 'Comparing Earnings Estimates "
                    "from the 2006 Earnings Public-Use File and the Annual "
                    "Statistical Supplement.' Research and Statistics Note "
                    "No. 2012-01."
                ),
                "url": RSN_URL,
                "text": str(RSN.relative_to(ROOT)),
                "text_sha256": _sha256(RSN),
            },
        },
        "retrieved": "2026-10-01",
        "tables": tables,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=1, sort_keys=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
