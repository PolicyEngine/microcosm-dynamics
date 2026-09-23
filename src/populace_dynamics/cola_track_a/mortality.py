"""Year-aware population mortality for Track A from the A2 capture.

TR2008 publishes no projected death probabilities by single age and sex
(A2 ``tr2008.GAPS``, first entry).  The A2 module proposes a substitute,
not adopted: the SSA 2004 period life table (a 2008-vintage SSA source,
equal to Supplement 2008 Table 4.C6) scaled by the ratio of TR2008's
age-sex-adjusted death rate in the projection year to its rate in a base
year, for the V.A1 age group containing the age (under 65, 65 and over).
:class:`Tr2008YearAwareMortality` applies exactly that substitute through
:func:`populace_dynamics.data.tr2008.period_life_table_2004` and
:func:`populace_dynamics.data.tr2008.mortality_improvement_ratio`; it
adds no rate of its own.

The model is single-year-of-age, so it exposes the A4 constant
``SINGLE_YEAR_AGE_BANDS`` as ``bands`` (the DI-aware mortality adapter
takes its multiplier base and its netting cells from them).  It is a
callable ``(frame, context) -> probabilities`` and deliberately has no
``probabilities`` attribute, so the A4 adapter passes the period context
and the model reads the projection year from it.

Conventions (A5, not ratified):

* The probability applied in projection year ``t`` (deaths between the
  ``t - 1`` and ``t`` states) is ``qx_2004(age, sex) * ratio(t, age)``,
  where ``age`` is the frame's start-of-year age (``t - 1 - birth_year``,
  the age the A4 adapter validates).
* Ages above the table's last age (119) use the last row.  Products above
  one are clipped to one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
)
from populace_dynamics.engine.loop import PeriodContext

__all__ = [
    "Tr2008YearAwareMortality",
    "load_tr2008_mortality",
]

_SEXES = ("female", "male")
_OLD_AGE_GROUP_START = 65


@dataclass(frozen=True)
class Tr2008YearAwareMortality:
    """``qx_2004 x ASADR(t, group) / ASADR(base, group)`` by single age."""

    qx_by_sex: Mapping[str, np.ndarray]
    ratio_by_year: Mapping[int, tuple[float, float]]
    alternative: str
    base_year: int
    bands: tuple[tuple[int, int], ...] = SINGLE_YEAR_AGE_BANDS
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if set(self.qx_by_sex) != set(_SEXES):
            raise ValueError(f"qx_by_sex must cover {_SEXES}")
        for sex, values in self.qx_by_sex.items():
            array = np.asarray(values, dtype=np.float64)
            if array.shape != (MAX_AGE + 1,):
                raise ValueError(f"{sex} qx must cover ages 0-{MAX_AGE}")
            if (
                not np.isfinite(array).all()
                or ((array < 0) | (array > 1)).any()
            ):
                raise ValueError(f"{sex} qx must lie in [0, 1]")
        for year, ratios in self.ratio_by_year.items():
            if len(ratios) != 2 or not all(
                np.isfinite(value) and value > 0 for value in ratios
            ):
                raise ValueError(f"ratios for {year} must be two positives")

    def probabilities_for_year(
        self, frame: pd.DataFrame, year: int
    ) -> np.ndarray:
        """Death probabilities in ``year`` for the frame's rows."""
        missing = {"age", "sex"} - set(frame.columns)
        if missing:
            raise ValueError(
                f"mortality frame is missing columns {sorted(missing)}"
            )
        try:
            under_65, over_65 = self.ratio_by_year[int(year)]
        except KeyError as error:
            raise KeyError(
                f"no TR2008 mortality ratio for {year}; load the model for "
                "every projection year"
            ) from error
        age = frame["age"].to_numpy(dtype=np.int64)
        if (age < 0).any():
            raise ValueError("mortality ages must be non-negative")
        index = np.minimum(age, MAX_AGE)
        sex = frame["sex"].astype(str).to_numpy()
        out = np.full(len(frame), np.nan)
        for label in _SEXES:
            rows = sex == label
            out[rows] = np.asarray(self.qx_by_sex[label])[index[rows]]
        if np.isnan(out).any():
            unknown = sorted(set(sex[np.isnan(out)]))
            raise ValueError(f"unknown mortality sex labels {unknown}")
        ratio = np.where(age >= _OLD_AGE_GROUP_START, over_65, under_65)
        return np.clip(out * ratio, 0.0, 1.0)

    def __call__(
        self, frame: pd.DataFrame, context: PeriodContext
    ) -> np.ndarray:
        return self.probabilities_for_year(frame, context.year)


def load_tr2008_mortality(
    years: range,
    *,
    alternative: str = "intermediate",
    base_year: int = 2004,
) -> Tr2008YearAwareMortality:
    """Build the A2 substitute for every projection year in ``years``."""

    qx_by_sex: dict[str, np.ndarray] = {}
    for sex in _SEXES:
        rows = tr2008.period_life_table_2004(sex)
        ages = [row.age for row in rows]
        if ages != list(range(len(rows))):
            raise ValueError("the 2004 period life table is not age-ordered")
        values = np.asarray([row.qx for row in rows], dtype=np.float64)
        padded = np.full(MAX_AGE + 1, values[-1])
        padded[: len(values)] = values
        qx_by_sex[sex] = padded
    ratios = {
        int(year): (
            tr2008.mortality_improvement_ratio(
                int(year),
                0,
                alternative=alternative,
                base_year=base_year,
            ),
            tr2008.mortality_improvement_ratio(
                int(year),
                _OLD_AGE_GROUP_START,
                alternative=alternative,
                base_year=base_year,
            ),
        )
        for year in years
    }
    last_table_age = len(tr2008.period_life_table_2004("male")) - 1
    return Tr2008YearAwareMortality(
        qx_by_sex=qx_by_sex,
        ratio_by_year=ratios,
        alternative=alternative,
        base_year=base_year,
        provenance={
            "basis": (
                "A2 proposed substitute (not adopted): SSA 2004 period life "
                "table x TR2008 V.A1 age-sex-adjusted death-rate ratio "
                "(projection year / base year) for the under-65 or "
                "65-and-over group"
            ),
            "life_table": "tr2008.period_life_table_2004",
            "ratio": "tr2008.mortality_improvement_ratio",
            "alternative": alternative,
            "base_year": base_year,
            "last_table_age": last_table_age,
            "ages_above_table": "last table row",
            "age_convention": "start-of-year age (year - 1 - birth_year)",
            "files_verified_by": "tr2008 module SHA-256 pins",
        },
    )
