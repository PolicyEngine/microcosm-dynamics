"""EPUF's measurement operator, for survey-side and model-side earnings.

SSA released EPUF's annual earnings after capping them at the year's
contribution and benefit base and applying a disclosure operator
(:mod:`populace_dynamics.data.epuf`). To score any other earnings
history against EPUF in the same units, :func:`epuf_measure` applies the
same steps to it:

1. negative values become zero and values above the wage base become the
   wage base;
2. a positive value below $100 becomes that year's EPUF bottom code;
3. a value strictly inside the band one rounding base below the wage
   base becomes that year's EPUF band mean;
4. every other value is rounded to SSA's base for its level ($25 from
   $100, $100 from $1,000, $1,000 from $50,000).

Steps 2-4 cannot change whether a person-year is positive or whether it
sits exactly at the wage base, so participation and at-maximum
statistics depend only on step 1; the rest affects only how values tie
in rank statistics. The per-year constants are EPUF's own, read off the
pinned bytes into ``data/external/epuf_2006/disclosure_constants.json``.

One step is not SSA's. SSA rounded at random to one of the two
neighbouring multiples and did not publish the direction probabilities;
this operator rounds half up, deterministically, so that a scored value
never depends on a rounding seed. EPUF itself is used as published and
is never passed through this function: SSA's random rounding left a few
grid values inside the band (68,000 in 1998, for one) that step 3 would
move.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

__all__ = [
    "CONSTANTS_PATH",
    "CONSTANTS_SHA256",
    "disclosure_constants",
    "epuf_measure",
    "rounding_base",
    "wage_base",
]

_ROOT = Path(__file__).resolve().parents[3]
CONSTANTS_PATH = (
    _ROOT / "data" / "external" / "epuf_2006" / "disclosure_constants.json"
)
#: SHA-256 of the committed constants; other bytes are refused.
CONSTANTS_SHA256 = (
    "ba1f39f238278243de19b8a9d194abedffeabd855f5b97779b685d852f62a881"
)

_BOTTOM_CODE_BELOW = 100.0
_BASE_25_BELOW = 1_000.0
_BASE_100_BELOW = 50_000.0


@lru_cache(maxsize=1)
def disclosure_constants() -> dict[int, dict[str, int]]:
    """Per-year wage base, band base, bottom code and band mean."""
    raw = CONSTANTS_PATH.read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != CONSTANTS_SHA256:
        raise ValueError(
            f"{CONSTANTS_PATH} has SHA-256 {observed}, not the pinned "
            f"{CONSTANTS_SHA256}; regenerate it with "
            "scripts/extract_epuf_disclosure_constants.py and re-pin"
        )
    years = json.loads(raw)["years"]
    return {
        int(year): {
            key: int(row[key])
            for key in ("wage_base", "band_base", "bottom_code", "band_mean")
        }
        for year, row in years.items()
    }


def wage_base(year: int) -> int:
    """The contribution and benefit base of an EPUF year (1951-2006)."""
    constants = disclosure_constants()
    if int(year) not in constants:
        raise ValueError(
            f"EPUF covers 1951-2006; no disclosure constants for {year}"
        )
    return constants[int(year)]["wage_base"]


def rounding_base(values: np.ndarray) -> np.ndarray:
    """SSA's rounding base at each earnings level."""
    values = np.asarray(values, dtype=np.float64)
    return np.where(
        values < _BASE_25_BELOW,
        25.0,
        np.where(values < _BASE_100_BELOW, 100.0, 1_000.0),
    )


def epuf_measure(earnings: np.ndarray, year: int) -> np.ndarray:
    """Express one year's earnings in EPUF's capped, disclosed units.

    ``earnings`` are nominal dollars of ``year``. Missing values are
    refused: a history with gaps has to be resolved to zeros or dropped
    by the caller, because EPUF codes a year without earnings as zero.
    """
    values = np.asarray(earnings, dtype=np.float64)
    if np.isnan(values).any():
        raise ValueError("epuf_measure refuses missing earnings")
    row = disclosure_constants().get(int(year))
    if row is None:
        raise ValueError(
            f"EPUF covers 1951-2006; no disclosure constants for {year}"
        )
    cap = float(row["wage_base"])
    capped = np.clip(values, 0.0, cap)
    base = rounding_base(capped)
    # Round half up (np.round rounds half to even).
    rounded = np.floor(capped / base + 0.5) * base
    out = np.where(capped > 0.0, rounded, 0.0)
    out = np.where(
        (capped > 0.0) & (capped < _BOTTOM_CODE_BELOW),
        float(row["bottom_code"]),
        out,
    )
    out = np.where(
        (capped > cap - float(row["band_base"])) & (capped < cap),
        float(row["band_mean"]),
        out,
    )
    return np.where(capped >= cap, cap, out)
