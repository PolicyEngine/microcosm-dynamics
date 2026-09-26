"""The Census threshold that defines the Track M minimum (plan fields G8, M2).

Python rules (not Axiom).  The M1 specification's threshold (section 7) is
the Census Bureau's weighted-average poverty threshold for one person aged
65 and over, of the record's section 4a threshold year.  This module loads
it from the committed capture of the Census historical threshold workbooks
of 1982, 1986, 1988, 1989, 1991, 1992 and 1994-2022 (``thresh82.xlsx`` ...
``thresh22.xlsx`` in ``data/external/census_poverty_thresholds/``, each
pinned by SHA-256 in ``scripts/capture_track_u_parameters.py``; staged
under cos decisions d194 and d279), refuses a capture whose SHA-256
differs from the pin, and refuses, with a named error, any threshold year
the capture lacks (referee R8): a year before 1982, a year after 2022, and
the years 1983-1985, 1987, 1990 and 1993, which no in-window record needs
by M4's structural count.  It reads no PSID file and no comparator value.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "AgedThresholds",
    "THRESHOLD_ROW",
    "TRACK_M_THRESHOLDS_PATH",
    "TRACK_M_THRESHOLDS_SHA256",
    "TRACK_M_THRESHOLD_YEARS",
    "ThresholdYearMissingError",
    "TRACK_M_THRESHOLD_YEARS_BEFORE_2003",
    "ThresholdsNotCapturedError",
    "captured_years_text",
    "check_threshold_years",
    "load_aged_thresholds",
]

_ROOT = Path(__file__).resolve().parents[3]

#: The threshold years before 2003 that M4's structural count (M1
#: specification sections 4, 7 and 10) shows the in-window records of the
#: registered rows need, downloaded under cos d279 ("any earlier year the
#: build proves it needs").
TRACK_M_THRESHOLD_YEARS_BEFORE_2003: tuple[int, ...] = (
    1982,
    1986,
    1988,
    1989,
    1991,
    1992,
    *range(1994, 2003),
)
#: The threshold years the Track M capture covers: those fifteen, and every
#: Census workbook from ``thresh03.xlsx`` (staged under cos d194) to
#: ``thresh22.xlsx`` (downloaded under cos d279).  Section 7 of the M1
#: specification says which of them Track M needs and why; any other year
#: needs a download and a new capture before a run that needs it.
TRACK_M_THRESHOLD_YEARS: tuple[int, ...] = (
    *TRACK_M_THRESHOLD_YEARS_BEFORE_2003,
    *range(2003, 2023),
)
#: The capture ``scripts/capture_track_u_parameters.py --track-m-census-dir``
#: writes from the committed workbooks, and its pin.
TRACK_M_THRESHOLDS_PATH = (
    _ROOT / "data" / "external" / "census_poverty_thresholds_1982_2022.json"
)
TRACK_M_THRESHOLDS_SHA256 = (
    "4493b8d5823ea12912212d892f98ef4777098ce34b01857cedc35d444a8b99cd"
)
_THRESHOLDS_SCHEMA_VERSION = "populace_dynamics.census_poverty_thresholds.v1"
#: The capture row G8 reads: the weighted average for one person aged 65
#: and over ("One person (unrelated individual)", "65 years and over").
THRESHOLD_ROW = "one_65_plus"


class ThresholdsNotCapturedError(RuntimeError):
    """The Census one-person 65+ threshold capture file is missing (M2)."""


class ThresholdYearMissingError(LookupError):
    """A threshold year a record needs is not in the capture (R8).

    Raised by :meth:`AgedThresholds.for_year` and, before anything is
    computed, by :func:`check_threshold_years`.  A year the capture lacks
    needs a Census download (cos d279 covers any earlier year the build
    proves it needs) and a new capture, hashed and pinned.
    """


@dataclass(frozen=True)
class AgedThresholds:
    """The threshold that defines the minimum (G8), annual dollars by year.

    The primary is the Census weighted-average poverty threshold for one
    person aged 65 and older (:func:`load_aged_thresholds`).  Tests pass
    INVENTED values.
    """

    annual: Mapping[int, float]
    source: Mapping[str, Any]

    def __post_init__(self) -> None:
        for year, value in self.annual.items():
            if isinstance(year, bool) or not isinstance(year, int):
                raise TypeError(f"threshold year {year!r} must be an int")
            if not (math.isfinite(float(value)) and value > 0):
                raise ValueError(f"threshold for {year} must be positive")

    def for_year(self, year: int) -> float:
        if year not in self.annual:
            raise ThresholdYearMissingError(
                f"no aged one-person threshold for {year} (captured: "
                f"{captured_years_text(self.annual)})"
            )
        return float(self.annual[year])


def captured_years_text(years: Iterable[int]) -> str:
    """The years as runs, e.g. ``1982, 1986, 1988-1989, 1994-2022``."""

    ordered = sorted(set(years))
    if not ordered:
        return "none"
    runs: list[list[int]] = [[ordered[0], ordered[0]]]
    for year in ordered[1:]:
        if year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return ", ".join(
        f"{first}" if first == last else f"{first}-{last}"
        for first, last in runs
    )


def load_aged_thresholds(
    path: Path = TRACK_M_THRESHOLDS_PATH,
    *,
    expected_sha256: str = TRACK_M_THRESHOLDS_SHA256,
) -> AgedThresholds:
    """The Census one-person 65+ weighted averages, 1982-2022 (G8; M2).

    Reads the committed capture of the Census historical threshold
    workbooks of :data:`TRACK_M_THRESHOLD_YEARS` (each pinned by SHA-256
    in ``scripts/capture_track_u_parameters.py``), refuses a file whose
    SHA-256 is not :data:`TRACK_M_THRESHOLDS_SHA256` or whose captured
    years are not exactly :data:`TRACK_M_THRESHOLD_YEARS`, and returns the
    :data:`THRESHOLD_ROW` weighted average of every one of those years, as
    printed.  A missing file raises :class:`ThresholdsNotCapturedError`.
    """

    path = Path(path)
    if not path.is_file():
        raise ThresholdsNotCapturedError(
            f"the Track M Census threshold capture {path} is missing: run "
            "scripts/capture_track_u_parameters.py --track-m-census-dir "
            "data/external/census_poverty_thresholds"
        )
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError(
            f"{path} sha256 {digest} != pinned {expected_sha256}: not the "
            "committed Track M threshold capture"
        )
    data = json.loads(raw)
    if data.get("schema_version") != _THRESHOLDS_SCHEMA_VERSION:
        raise ValueError(f"{path}: schema {data.get('schema_version')!r}")
    years = TRACK_M_THRESHOLD_YEARS
    if data.get("years") != [years[0], years[-1]]:
        raise ValueError(f"{path}: years {data.get('years')}")
    if data.get("captured_years") != list(years):
        raise ValueError(
            f"{path}: captured years {data.get('captured_years')} are not "
            f"{captured_years_text(years)}"
        )
    if sorted(data.get("weighted_average", {})) != sorted(map(str, years)):
        raise ValueError(f"{path}: weighted averages for other years")
    annual: dict[int, float] = {}
    for year in years:
        value = data["weighted_average"][str(year)][THRESHOLD_ROW]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{path}: {year} {THRESHOLD_ROW} {value!r}")
        annual[year] = float(value)
    return AgedThresholds(
        annual,
        {
            "kind": "census_capture",
            "path": (
                str(path.relative_to(_ROOT))
                if path.is_relative_to(_ROOT)
                else str(path)
            ),
            "sha256": digest,
            "row": THRESHOLD_ROW,
            "years": [years[0], years[-1]],
            "captured_years": list(years),
        },
    )


def check_threshold_years(
    needed: Mapping[int, int] | Iterable[int], thresholds: AgedThresholds
) -> None:
    """Refuse, before any computation, a threshold year not captured (R8).

    ``needed`` is the set of threshold years the cohort's in-window records
    and the wage-indexed base years require (or a mapping from each year to
    the number of records that need it).  Raises
    :class:`ThresholdYearMissingError` naming every missing year.
    """

    counts = (
        dict(needed)
        if isinstance(needed, Mapping)
        else {year: None for year in needed}
    )
    missing = sorted(set(counts) - set(thresholds.annual))
    if missing:
        detail = ", ".join(
            f"{year}" + (f" ({counts[year]} records)" if counts[year] else "")
            for year in missing
        )
        raise ThresholdYearMissingError(
            f"threshold years {detail} are not in the capture (captured: "
            f"{captured_years_text(thresholds.annual)}); a year not captured "
            "needs a Census download (cos d279: any earlier year the build "
            "proves it needs), captured, hashed and pinned before the run"
        )
