"""Build the committed SSA automatic-determination COLA history.

The values below are an offline transcription of SSA's published
automatic-determination COLA series.  This implementation PR deliberately
does not fetch the live page.  Its review therefore must verify the complete
transcription against:

    https://www.ssa.gov/oact/cola/colaseries.html

The extraction includes first-payment years 1975-2022.  The first-estimates
report requires 1979-2022; the four earlier years are committed as margin.
SSA paid the 1975-1982 adjustments beginning in July of the named year.  The
1983 transition year had no adjustment, and the 1984-2022 rows are the COLAs
first paid in January of the named year after taking effect the prior December.

Run from the repository root::

    .venv/bin/python scripts/extract_ssa_cola_history.py
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "external" / "ssa_cola_history.json"

SCHEMA_VERSION = "ssa_cola_history.v1"
SOURCE_URL = "https://www.ssa.gov/oact/cola/colaseries.html"
RETRIEVAL_DATE = "2026-07-24"
VINTAGE_YEAR = 2022
FIRST_YEAR = 1975
LAST_YEAR = 2022
REQUIRED_FIRST_YEAR = 1979
REQUIRED_LAST_YEAR = 2022

# sha256 of ``canonical_content_bytes(data)`` for the complete transcription.
# It is a review pin: changing any year or percentage requires deliberately
# updating this digest and the independent all-row test.
CONTENT_SHA256 = (
    "488618df8a8ea05f929d0f8ecc7eb79d240bee39adaea0572e9d73d339a54d69"
)

TRANSCRIPTION_VERIFICATION = (
    "Offline transcription; no web fetch was performed for this "
    "implementation PR. The complete 1975-2022 transcription requires "
    "verification at implementation review against "
    "https://www.ssa.gov/oact/cola/colaseries.html."
)

# SSA automatic-determination COLAs, in percent, keyed by the calendar year in
# which the increase was first paid.  Preserve one-decimal precision even where
# the published value is a whole number.  The 1983 zero records the transition
# from July adjustments to January payments; the next 3.5 percent increase was
# first paid in January 1984.
TRANSCRIBED_COLA_PERCENT: tuple[tuple[int, float], ...] = (
    (1975, 8.0),
    (1976, 6.4),
    (1977, 5.9),
    (1978, 6.5),
    (1979, 9.9),
    (1980, 14.3),
    (1981, 11.2),
    (1982, 7.4),
    (1983, 0.0),
    (1984, 3.5),
    (1985, 3.5),
    (1986, 3.1),
    (1987, 1.3),
    (1988, 4.2),
    (1989, 4.0),
    (1990, 4.7),
    (1991, 5.4),
    (1992, 3.7),
    (1993, 3.0),
    (1994, 2.6),
    (1995, 2.8),
    (1996, 2.6),
    (1997, 2.9),
    (1998, 2.1),
    (1999, 1.3),
    (2000, 2.5),
    (2001, 3.5),
    (2002, 2.6),
    (2003, 1.4),
    (2004, 2.1),
    (2005, 2.7),
    (2006, 4.1),
    (2007, 3.3),
    (2008, 2.3),
    (2009, 5.8),
    (2010, 0.0),
    (2011, 0.0),
    (2012, 3.6),
    (2013, 1.7),
    (2014, 1.5),
    (2015, 1.7),
    (2016, 0.0),
    (2017, 0.3),
    (2018, 2.0),
    (2019, 2.8),
    (2020, 1.6),
    (2021, 1.3),
    (2022, 5.9),
)


def canonical_content_bytes(data: Mapping[str, float]) -> bytes:
    """Return the exact canonical bytes covered by ``CONTENT_SHA256``."""
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def content_sha256(data: Mapping[str, float]) -> str:
    """Hash the canonical year-to-percentage payload."""
    return hashlib.sha256(canonical_content_bytes(data)).hexdigest()


def transcribed_data() -> dict[str, float]:
    """Validate and return the transcribed year-to-COLA mapping."""
    data: dict[str, float] = {}
    for year, percentage in TRANSCRIBED_COLA_PERCENT:
        key = str(year)
        if key in data:
            raise ValueError(f"duplicate COLA payment year {year}")
        if percentage < 0 or percentage > 100:
            raise ValueError(
                f"COLA percentage for {year} is outside [0, 100]: "
                f"{percentage}"
            )
        data[key] = percentage

    years = sorted(int(year) for year in data)
    expected = list(range(FIRST_YEAR, LAST_YEAR + 1))
    if years != expected:
        raise ValueError(
            f"COLA years {years} != expected {FIRST_YEAR}-{LAST_YEAR}"
        )

    required = [
        year
        for year in range(REQUIRED_FIRST_YEAR, REQUIRED_LAST_YEAR + 1)
        if str(year) in data
    ]
    expected_required = list(
        range(REQUIRED_FIRST_YEAR, REQUIRED_LAST_YEAR + 1)
    )
    if required != expected_required:
        raise ValueError(
            f"required COLA payment-year coverage {required} != "
            f"{REQUIRED_FIRST_YEAR}-{REQUIRED_LAST_YEAR}"
        )

    digest = content_sha256(data)
    if digest != CONTENT_SHA256:
        raise ValueError(
            f"transcribed COLA content sha256 {digest} != pinned "
            f"{CONTENT_SHA256}; re-verify every row against {SOURCE_URL}"
        )
    return data


def build() -> dict[str, Any]:
    """Assemble the deterministic external-reference artifact."""
    data = transcribed_data()
    return {
        "schema_version": SCHEMA_VERSION,
        "series": (
            "Social Security automatic-determination COLA history by "
            "first payment year"
        ),
        "unit": "percent",
        "year_basis": "first_payment_year",
        "year_semantics": (
            "calendar year in which payments reflecting the COLA begin"
        ),
        "historical_timing": {
            "1975-1982": (
                "effective in June and first reflected in July payments "
                "of the named year"
            ),
            "1983": (
                "transition year with no COLA; the next adjustment was "
                "first reflected in January 1984 payments"
            ),
            "1984-2022": (
                "effective in December of the prior year and first "
                "reflected in January payments of the named year"
            ),
        },
        "vintage_year": VINTAGE_YEAR,
        "provenance": {
            "source": (
                "Social Security Administration, Office of the Chief "
                "Actuary, Cost-of-Living Adjustments"
            ),
            "source_url": SOURCE_URL,
            "retrieval_date": RETRIEVAL_DATE,
            "vintage": (
                "History through first payment year 2022 (the 2021 "
                "determination); later live-page rows are intentionally "
                "outside this artifact's vintage."
            ),
            "transcription_method": (
                "Values manually transcribed into "
                "scripts/extract_ssa_cola_history.py; the build performs no "
                "network access."
            ),
            "transcription_verification": TRANSCRIPTION_VERIFICATION,
            "content_sha256": CONTENT_SHA256,
            "content_hash_basis": (
                "sha256 of the UTF-8 canonical JSON encoding of the complete "
                "data object (sorted keys, compact separators, trailing "
                "newline)"
            ),
        },
        "validation": {
            "first_payment_year": FIRST_YEAR,
            "latest_payment_year": LAST_YEAR,
            "n_observations": len(data),
            "continuous_payment_years": True,
            "required_coverage": {
                "first_year": REQUIRED_FIRST_YEAR,
                "last_year": REQUIRED_LAST_YEAR,
                "n_years": REQUIRED_LAST_YEAR - REQUIRED_FIRST_YEAR + 1,
                "complete": True,
            },
        },
        "build": {
            "built_by": "scripts/extract_ssa_cola_history.py",
            "content_sha256": CONTENT_SHA256,
            "reproducible": (
                "rendered deterministically from the pinned in-script "
                "transcription; no network or wall-clock timestamp is used"
            ),
        },
        "data": data,
    }


def main() -> None:
    artifact = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(
        f"wrote {OUT_PATH} "
        f"({artifact['validation']['n_observations']} observations)"
    )
    print(f"json sha256: {digest}")


if __name__ == "__main__":
    main()
