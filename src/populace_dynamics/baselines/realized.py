"""Realized values the 2026 baselines splice before any projected value.

Every 2026 baseline keeps realized values through the last actual year
before it uses a projected or derived one:

* **COLA**: realized through determination year 2025.  The committed
  realized history (``data/external/ssa_cola_history.json``, loaded by
  :func:`~populace_dynamics.estimates.parameters.load_cola_history`)
  ends in 2022 and supplies every year through 2022 unchanged (the same
  floats the legacy baseline's realized years carry); TR2026 Table V.C1
  supplies the historical increases for 2023 and 2024 and the 2025
  increase as an actual (V.C1 footnote g, 2.8 percent, first paid
  January 2026), so every 2026 baseline's projected or derived rates
  start in :data:`FIRST_SPLICED_COLA_YEAR` (2023) with the realized
  rows.  V.C1's historical rows equal the committed history in every
  year both cover (1979-2022), and :func:`check_realized_cola_agreement`
  refuses any difference before a splice is built.
* **AWI**: realized through 2024, TR2026 Table VI.G1's last historical
  row; VI.G1's 2025 value is an estimate and later values projections.
  CBO publishes no AWI; its analog starts from the same 2024 actual
  (``data.cbo2026.awi``), and :func:`check_awi_anchor` refuses any
  difference between the two 2024 amounts.
"""

from __future__ import annotations

from functools import cache
from numbers import Integral

from populace_dynamics.data import cbo2026, tr2026
from populace_dynamics.estimates.parameters import (
    REQUIRED_COLA_DETERMINATION_YEARS,
    load_cola_history,
)

__all__ = [
    "FIRST_SPLICED_COLA_YEAR",
    "LAST_ACTUAL_AWI_YEAR",
    "LAST_ACTUAL_COLA_YEAR",
    "REALIZED_HISTORY_LAST_YEAR",
    "check_awi_anchor",
    "check_cola_request",
    "check_realized_cola_agreement",
    "realized_awi",
    "realized_cola_percent",
]

#: TR2026 V.C1: 2025 is the last actual automatic increase (footnote g).
LAST_ACTUAL_COLA_YEAR = 2025
#: TR2026 VI.G1: 2024 is the last historical AWI (2025 is estimated).
LAST_ACTUAL_AWI_YEAR = 2024
#: The committed realized COLA history ends with this determination year.
REALIZED_HISTORY_LAST_YEAR = REQUIRED_COLA_DETERMINATION_YEARS[-1]
#: The first determination year a 2026 baseline splices onto the history.
FIRST_SPLICED_COLA_YEAR = REALIZED_HISTORY_LAST_YEAR + 1

_REALIZED_COLA_SOURCES = ("tr2026_v_c1_historical", "tr2026_v_c1_actual")


def check_cola_request(first: int, last: int) -> tuple[int, int]:
    """Validate a 2026 baseline's ``cola_rates(first, last)`` request.

    ``first`` (the caller's first rate year, ``TrackAConfig.
    tr2008_first_rate_year``) must be an integer year no later than
    ``last``; it does not move the splice, because a 2026 baseline keeps
    every realized increase through :data:`LAST_ACTUAL_COLA_YEAR`.
    ``last`` must follow the committed history, which already covers
    every earlier year (use ``load_cola_history()`` for those).
    """
    for label, value in (("first", first), ("last", last)):
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise TypeError(f"{label} must be an integer year")
    first, last = int(first), int(last)
    if first > last:
        raise ValueError(f"first ({first}) must not follow last ({last})")
    if last < FIRST_SPLICED_COLA_YEAR:
        raise ValueError(
            f"last ({last}) must be at least {FIRST_SPLICED_COLA_YEAR}: the "
            "committed realized history covers every earlier year"
        )
    return first, last


def realized_cola_percent(year: int) -> tuple[float, str]:
    """The realized increase for ``year`` (percent) and its source tag."""
    year = int(year)
    if year > LAST_ACTUAL_COLA_YEAR:
        raise KeyError(
            f"no realized COLA for determination year {year}; the last "
            f"actual increase is {LAST_ACTUAL_COLA_YEAR}"
        )
    (entry,) = tr2026.cola_path(year, year)
    if entry.source not in _REALIZED_COLA_SOURCES:
        raise ValueError(
            f"TR2026 V.C1 {year} is {entry.source!r}, not a realized row"
        )
    return entry.percent, entry.source


def realized_awi(year: int) -> tuple[float, str]:
    """The realized AWI for ``year`` (dollars) and its source tag."""
    year = int(year)
    if year > LAST_ACTUAL_AWI_YEAR:
        raise KeyError(
            f"no realized AWI for {year}; the last historical AWI is "
            f"{LAST_ACTUAL_AWI_YEAR}"
        )
    (entry,) = tr2026.awi(year, year)
    if entry.source != "tr2026_vi_g1_historical":
        raise ValueError(f"TR2026 VI.G1 {year} is {entry.source!r}")
    return entry.amount, entry.source


@cache
def check_realized_cola_agreement() -> None:
    """Refuse a splice if V.C1's history differs from the committed one."""
    realized = load_cola_history()
    mismatched = {}
    for entry in tr2026.cola_path(
        REQUIRED_COLA_DETERMINATION_YEARS[0], REALIZED_HISTORY_LAST_YEAR
    ):
        year = entry.determination_year
        committed = 100.0 * realized.rate_for_determination_year(year)
        if round(committed, 10) != round(entry.percent, 10):
            mismatched[year] = (committed, entry.percent)
    if mismatched:
        raise ValueError(
            "TR2026 V.C1 historical increases differ from the committed "
            f"realized history: {mismatched}"
        )


@cache
def check_awi_anchor() -> None:
    """Refuse if CBO's 2024 AWI anchor is not TR2026's 2024 actual."""
    (anchor,) = cbo2026.awi(LAST_ACTUAL_AWI_YEAR, LAST_ACTUAL_AWI_YEAR)
    amount, _ = realized_awi(LAST_ACTUAL_AWI_YEAR)
    if anchor.amount != amount:
        raise ValueError(
            f"CBO's {LAST_ACTUAL_AWI_YEAR} AWI anchor {anchor.amount!r} is "
            f"not TR2026 VI.G1's {amount!r}"
        )
