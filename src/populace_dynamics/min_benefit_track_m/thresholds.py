"""The Census threshold that defines the Track M minimum (plan fields G8, M2).

Python rules (not Axiom).  The M1 specification's threshold (section 7) is
the Census Bureau's weighted-average poverty threshold for one person aged
65 and over, of the record's section 4a threshold year.  This module loads
it from the committed capture of the Census historical threshold workbooks
``thresh03.xlsx`` ... ``thresh22.xlsx`` (``data/external/
census_poverty_thresholds/``, each pinned by SHA-256 in
``scripts/capture_track_u_parameters.py``; staged under cos decisions d194
and d279), refuses a capture whose SHA-256 differs from the pin, and
refuses, with a named error, any threshold year the capture lacks
(referee R8).  It reads no PSID file and no comparator value.
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
    "ThresholdsNotCapturedError",
    "check_threshold_years",
    "load_aged_thresholds",
]

_ROOT = Path(__file__).resolve().parents[3]

#: The threshold years the Track M capture covers: every Census workbook
#: from ``thresh03.xlsx`` (staged under cos d194) to ``thresh22.xlsx``
#: (downloaded under cos d279).  Section 7 of the M1 specification says
#: which of them Track M needs and why; a year before 2003 needs a
#: download (d279 covers "any earlier year the build proves it needs").
TRACK_M_THRESHOLD_YEARS: tuple[int, ...] = tuple(range(2003, 2023))
#: The capture ``scripts/capture_track_u_parameters.py --track-m-census-dir``
#: writes from the committed workbooks, and its pin.
TRACK_M_THRESHOLDS_PATH = (
    _ROOT / "data" / "external" / "census_poverty_thresholds_2003_2022.json"
)
TRACK_M_THRESHOLDS_SHA256 = (
    "65bbcd83cad97b94526b8c71417b9b4986a5bc878285b87832cfb102bc11e3c5"
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
    computed, by :func:`check_threshold_years`.  A year before 2003 needs a
    Census download (cos d279 covers any earlier year the build proves it
    needs).
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
                f"{_span(self.annual)})"
            )
        return float(self.annual[year])


def _span(years: Iterable[int]) -> str:
    ordered = sorted(years)
    return f"{ordered[0]}-{ordered[-1]}" if ordered else "none"


def load_aged_thresholds(
    path: Path = TRACK_M_THRESHOLDS_PATH,
    *,
    expected_sha256: str = TRACK_M_THRESHOLDS_SHA256,
) -> AgedThresholds:
    """The Census one-person 65+ weighted averages, 2003-2022 (G8; M2).

    Reads the committed capture of the Census historical threshold
    workbooks (``thresh03.xlsx`` ... ``thresh22.xlsx``, each pinned by
    SHA-256 in ``scripts/capture_track_u_parameters.py``), refuses a file
    whose SHA-256 is not :data:`TRACK_M_THRESHOLDS_SHA256`, and returns the
    :data:`THRESHOLD_ROW` weighted average of every year in
    :data:`TRACK_M_THRESHOLD_YEARS`, as printed.  A missing file raises
    :class:`ThresholdsNotCapturedError`.
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
            f"{_span(thresholds.annual)}); a year before 2003 needs a Census "
            "download (cos d279: any earlier year the build proves it "
            "needs), captured, hashed and pinned before the run"
        )


# ---------------------------------------------------------------------------
# Work years, threshold and minimum
# ---------------------------------------------------------------------------
