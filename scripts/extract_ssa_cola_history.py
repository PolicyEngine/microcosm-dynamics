"""Build the committed SSA automatic-determination COLA history.

The values below are an offline transcription of SSA's published
automatic-determination COLA series.  This implementation PR deliberately
does not fetch the live page.  Its review therefore must verify the complete
transcription against:

    https://www.ssa.gov/oact/cola/colaseries.html

The extraction includes SSA determination years 1975-2022.  The
first-estimates report requires 1979-2022; the four earlier years are
committed as margin.  SSA paid the 1975-1982 adjustments beginning in July of
the named year.  Beginning with the 1983 determination, each adjustment takes
effect in December and is first reflected in January payments of the following
year.

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
    "8f1d75cab8bd1dba226c83bdff28a0ca1b21167e803eb65ff1d13d5cbe2255e0"
)

TRANSCRIPTION_VERIFICATION = (
    "The complete determination-year transcription was checked row by row "
    "against the official SSA series during the PR #286 adversarial "
    "implementation review."
)

# SSA automatic-determination COLAs, in percent, keyed by SSA's published
# determination year.  Preserve one-decimal precision even where the published
# value is a whole number.
TRANSCRIBED_COLA_PERCENT: tuple[tuple[int, float], ...] = (
    (1975, 8.0),
    (1976, 6.4),
    (1977, 5.9),
    (1978, 6.5),
    (1979, 9.9),
    (1980, 14.3),
    (1981, 11.2),
    (1982, 7.4),
    (1983, 3.5),
    (1984, 3.5),
    (1985, 3.1),
    (1986, 1.3),
    (1987, 4.2),
    (1988, 4.0),
    (1989, 4.7),
    (1990, 5.4),
    (1991, 3.7),
    (1992, 3.0),
    (1993, 2.6),
    (1994, 2.8),
    (1995, 2.6),
    (1996, 2.9),
    (1997, 2.1),
    (1998, 1.3),
    (1999, 2.5),
    (2000, 3.5),
    (2001, 2.6),
    (2002, 1.4),
    (2003, 2.1),
    (2004, 2.7),
    (2005, 4.1),
    (2006, 3.3),
    (2007, 2.3),
    (2008, 5.8),
    (2009, 0.0),
    (2010, 0.0),
    (2011, 3.6),
    (2012, 1.7),
    (2013, 1.5),
    (2014, 1.7),
    (2015, 0.0),
    (2016, 0.3),
    (2017, 2.0),
    (2018, 2.8),
    (2019, 1.6),
    (2020, 1.3),
    (2021, 5.9),
    (2022, 8.7),
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
            raise ValueError(f"duplicate COLA determination year {year}")
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
            f"required COLA determination-year coverage {required} != "
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
            "determination year"
        ),
        "unit": "percent",
        "year_basis": "determination_year",
        "year_semantics": (
            "calendar year of SSA's automatic COLA determination"
        ),
        "historical_timing": {
            "1975-1982": (
                "effective in June and first reflected in July payments "
                "of the named year"
            ),
            "1983-2022": (
                "effective in December of the determination year and first "
                "reflected in January payments of the following year"
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
                "Official automatic-determination history through "
                "determination year 2022; later live-page rows are "
                "intentionally outside this artifact's vintage."
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
            "first_determination_year": FIRST_YEAR,
            "latest_determination_year": LAST_YEAR,
            "n_observations": len(data),
            "continuous_determination_years": True,
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
