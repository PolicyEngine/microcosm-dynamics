"""Single-age fertility shapes for baselines that publish only a TFR.

The 2026 Trustees Report publishes the period total fertility rate
(Table V.A1) but no age-specific fertility schedule in the captured
sources (``data/external/tr2026/provenance.md``: "No ASFR schedule was
invented").  A TR2026 baseline therefore derives single-age rates as a
fixed age *shape* scaled each year to the published TFR.  Two shapes
are supplied; the choice is a builder default awaiting ratification and
every derived value is tagged with it:

``nchs2024`` (default)
    NCHS final 2024 age-specific fertility rates in eight five-year
    bands, 10-14 to 45-49 (``data/external/nchs_asfr_2024.json``, from
    *Births: Final Data for 2024*, NVSR 75(2); the file records the
    Socrata query, its response SHA-256 and the NCHS TFR check).  Each
    band total (five times the rate per 1,000, divided by 1,000) is
    spread over its single ages by
    :func:`~populace_dynamics.baselines.interpolation.ungroup_band_totals`
    (mean-preserving, non-negative).  The fertility step exposes ages
    14-49, so the mass the interpolation places at ages 10-13 is added
    to age 14 (``fold_under_14_into_14``): the shape keeps every birth
    and its sum equals the NCHS TFR, 1.5995.  NCHS's 45-49 rate counts
    births to women 45 and over (the file's ``band_note``), and stays in
    ages 45-49.
``cbo2026``
    CBO's January 2026 single-age (14-49) all-women schedule for the
    same year, as published (:func:`populace_dynamics.data.cbo2026.asfr`),
    used only for its age pattern; covered 2021-2099.

``asfr(year) = shape(age) * TFR(year) / sum(shape)``, so the derived
schedule sums to the baseline's TFR to floating-point rounding.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import numpy as np

from populace_dynamics.baselines.interpolation import ungroup_band_totals
from populace_dynamics.data import cbo2026

__all__ = [
    "AsfrShape",
    "FERTILE_AGES",
    "NCHS_ASFR_PATH",
    "NCHS_ASFR_SHA256",
    "NCHS_BANDS",
    "NCHS_VINTAGE",
    "SHAPES",
    "age_shape",
    "nchs_published_tfr",
    "nchs_single_age_shape",
    "scale_shape_to_tfr",
]

AsfrShape = Literal["nchs2024", "cbo2026"]
SHAPES: tuple[AsfrShape, ...] = ("nchs2024", "cbo2026")
#: Single ages at which the fertility step exposes women (CBO's ages).
FERTILE_AGES: tuple[int, ...] = tuple(range(14, 50))
_ROOT = Path(__file__).resolve().parents[3]
NCHS_ASFR_PATH = _ROOT / "data" / "external" / "nchs_asfr_2024.json"
NCHS_ASFR_SHA256 = (
    "578742b151d5656231527175e5e4c29c0554ade8bb56807235d6a75890594f60"
)
NCHS_VINTAGE = "2024"
#: NCHS's eight published bands as single-year edges [lower, upper).
NCHS_BANDS: tuple[tuple[str, int, int], ...] = (
    ("10-14", 10, 15),
    ("15-19", 15, 20),
    ("20-24", 20, 25),
    ("25-29", 25, 30),
    ("30-34", 30, 35),
    ("35-39", 35, 40),
    ("40-44", 40, 45),
    ("45-49", 45, 50),
)


@cache
def _nchs_document() -> dict:
    raw = NCHS_ASFR_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != NCHS_ASFR_SHA256:
        raise ValueError(
            f"{NCHS_ASFR_PATH.name} sha256 {digest} != pinned "
            f"{NCHS_ASFR_SHA256}; re-pin deliberately"
        )
    document = json.loads(raw)
    if document.get("measure") != "age_specific_fertility_rate_per_1000_women":
        raise ValueError("NCHS ASFR file measure is not per 1,000 women")
    return document


@cache
def nchs_single_age_shape() -> MappingProxyType:
    """NCHS 2024 rates spread to single ages 14-49 (births per woman).

    Read-only mapping; its values sum to the NCHS 2024 TFR (per woman).
    """
    table = _nchs_document()["tables"][NCHS_VINTAGE]
    if set(table) != {label for label, _, _ in NCHS_BANDS}:
        raise ValueError("NCHS ASFR table bands differ from NCHS_BANDS")
    edges = [NCHS_BANDS[0][1], *(upper for _, _, upper in NCHS_BANDS)]
    totals = [
        (upper - lower) * float(table[label]) / 1000.0
        for label, lower, upper in NCHS_BANDS
    ]
    values = ungroup_band_totals(edges, totals)
    ages = range(edges[0], edges[-1])
    by_age = dict(zip(ages, values.tolist(), strict=True))
    first = FERTILE_AGES[0]
    shape = {age: by_age[age] for age in FERTILE_AGES}
    shape[first] = sum(value for age, value in by_age.items() if age <= first)
    return MappingProxyType(shape)


def nchs_published_tfr() -> float:
    """The NCHS 2024 TFR the file records, per woman (1599.5 / 1000)."""
    return float(_nchs_document()["total_fertility_rate"][NCHS_VINTAGE]) / (
        1000.0
    )


def age_shape(shape: AsfrShape, year: int) -> dict[int, float]:
    """The unscaled single-age shape ``shape`` supplies for ``year``."""
    if shape == "nchs2024":
        return dict(nchs_single_age_shape())
    if shape == "cbo2026":
        return cbo2026.asfr(year, "all")
    raise ValueError(f"unknown ASFR shape {shape!r}; expected {SHAPES}")


def scale_shape_to_tfr(
    shape: dict[int, float], tfr: float
) -> dict[int, float]:
    """``shape`` rescaled so that its single-age values sum to ``tfr``."""
    values = np.asarray(list(shape.values()), dtype=np.float64)
    if not np.isfinite(tfr) or tfr < 0.0:
        raise ValueError(f"TFR must be finite and non-negative, got {tfr!r}")
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("shape values must be finite and non-negative")
    total = float(values.sum())
    if total <= 0.0:
        raise ValueError("an all-zero shape cannot be scaled to a TFR")
    factor = float(tfr) / total
    return {int(age): float(value) * factor for age, value in shape.items()}
