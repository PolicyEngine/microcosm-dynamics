"""The ``Baseline`` interface and the pieces every baseline shares.

A baseline is the set of economic and demographic paths a projection
reads besides its cohort: the COLA path, the AWI, population mortality
by single age, sex and year, fertility by single age, the claim-age
table and the DI rates.  :class:`Baseline` is the protocol the three
registered baselines implement (:mod:`~populace_dynamics.baselines`
registry); each method's docstring here is the contract.

Units follow the projection code: COLA rates are fractions keyed by
determination year (``0.028`` is 2.8 percent), as a
:class:`~populace_dynamics.estimates.parameters.COLASeries` that is also
a :class:`~populace_dynamics.scenario_benefits.COLARateSource`; CPI-W
growth is a percentage; AWI is dollars; ``q`` is a one-year death
probability at exact age (ages 0-120, :data:`MAX_AGE`); ASFR is births
per woman at single ages 14-49 (not a probability); TFR is births per
woman.

:class:`BaselineYearAwareMortality` is the generic year-aware population
mortality model: the same interface as
:class:`~populace_dynamics.cola_track_a.mortality.Tr2008YearAwareMortality`
(``bands`` of single ages, ``__call__(frame, context)``, no
``probabilities`` attribute, so the A4 DI-aware adapter passes the period
context), with ``q`` stored by year and sex instead of a 2004 table times
a ratio.  Convention (as A5's): the probability applied in projection
year ``t``, deaths between the ``t - 1`` and ``t`` states, is the year-
``t`` period ``q`` at the frame's start-of-year age ``t - 1 -
birth_year``; ages above 120 use age 120.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "AWI_FIRST_REPLACED_YEAR",
    "SEXES",
    "Baseline",
    "BaselineGapError",
    "BaselineYearAwareMortality",
    "file_sha256",
    "pad_to_max_age",
    "repo_relative",
    "replace_awi",
    "splice_cola_percent",
]

SEXES: tuple[str, ...] = ("female", "male")
#: Every baseline replaces the oracle's NAWI from this year on and keeps
#: the oracle's (policyengine-us) realized series before it.  It is the
#: legacy baseline's year (TR2008 V.C1 starts its AWI rows in 1975,
#: ``cola_track_a.runner``), kept for the 2026 baselines so that every
#: baseline shares the pre-1975 series and differs only by vintage.
AWI_FIRST_REPLACED_YEAR = 1975


class BaselineGapError(LookupError):
    """An input this baseline's sources do not supply (a named gap)."""


_ROOT = Path(__file__).resolve().parents[3]


def file_sha256(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_relative(path: Path) -> str:
    """``path`` relative to the repository root (for provenance keys)."""
    return str(Path(path).resolve().relative_to(_ROOT))


def pad_to_max_age(q: np.ndarray) -> np.ndarray:
    """``q`` for ages 0-119 extended to 0-120 by repeating age 119.

    Both 2026 sources stop at age 119 (A5's 2004 table too); the engine's
    DI rates and mortality cells run to :data:`MAX_AGE` = 120.  The
    legacy model pads the same way (``cola_track_a.mortality``).
    """
    values = np.asarray(q, dtype=np.float64)
    if values.ndim != 1 or values.size < 1 or values.size > MAX_AGE + 1:
        raise ValueError(f"q must be a vector of at most {MAX_AGE + 1} ages")
    padded = np.full(MAX_AGE + 1, values[-1])
    padded[: values.size] = values
    return padded


def splice_cola_percent(
    realized: COLASeries,
    projected_percent: Mapping[int, float],
    *,
    label: str,
) -> COLASeries:
    """Realized history with ``projected_percent`` from its first year on.

    Percentages become fractions rounded to ten decimals, as the legacy
    constructor (``cola_track_a.runner.tr2008_baseline_cola``) does, and
    :func:`~populace_dynamics.scenario_benefits.extend_cola_series`
    splices them (consecutive years, no gap, fractions in [0, 1)).
    """
    projected = {
        int(year): round(float(percent) / 100.0, 10)
        for year, percent in projected_percent.items()
    }
    return sb.extend_cola_series(realized, projected, projection_label=label)


def replace_awi(
    params: SSAParameters,
    awi: Mapping[int, float],
    *,
    revision_suffix: str,
) -> SSAParameters:
    """``params`` with NAWI replaced by ``awi`` for every year it covers.

    Years before the first year of ``awi`` keep ``params``'s series (the
    legacy ``tr2008_ssa_parameters`` rule); ``awi`` must cover
    consecutive years with positive finite amounts.
    """
    years = sorted(int(year) for year in awi)
    if not years or years != list(range(years[0], years[-1] + 1)):
        raise ValueError("awi must cover consecutive years")
    for year in years:
        amount = float(awi[year])
        if not np.isfinite(amount) or amount <= 0.0:
            raise ValueError(f"AWI for {year} must be positive and finite")
    nawi = {
        year: value for year, value in params.nawi.items() if year < years[0]
    }
    nawi.update({year: float(awi[year]) for year in years})
    return dataclasses.replace(
        params,
        nawi=dict(sorted(nawi.items())),
        pe_us_revision=f"{params.pe_us_revision}+{revision_suffix}",
    )


@dataclass(frozen=True)
class BaselineYearAwareMortality:
    """Population death probabilities by single age, sex and year.

    ``qx_by_year[year][sex]`` is a read-only vector for ages 0-120.  See
    the module docstring for the age and year convention.
    """

    baseline: str
    qx_by_year: Mapping[int, Mapping[str, np.ndarray]]
    bands: tuple[tuple[int, int], ...] = SINGLE_YEAR_AGE_BANDS
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if tuple(self.bands) != SINGLE_YEAR_AGE_BANDS:
            raise ValueError("bands must be the single-year age bands")
        frozen: dict[int, Mapping[str, np.ndarray]] = {}
        for year, by_sex in self.qx_by_year.items():
            if set(by_sex) != set(SEXES):
                raise ValueError(f"q for {year} must cover {SEXES}")
            arrays = {}
            for sex in SEXES:
                array = np.array(by_sex[sex], dtype=np.float64)
                if array.shape != (MAX_AGE + 1,):
                    raise ValueError(
                        f"{year} {sex} q must cover ages 0-{MAX_AGE}"
                    )
                if (
                    not np.isfinite(array).all()
                    or ((array < 0.0) | (array > 1.0)).any()
                ):
                    raise ValueError(f"{year} {sex} q must lie in [0, 1]")
                array.setflags(write=False)
                arrays[sex] = array
            frozen[int(year)] = MappingProxyType(arrays)
        object.__setattr__(self, "qx_by_year", MappingProxyType(frozen))
        object.__setattr__(
            self, "provenance", MappingProxyType(dict(self.provenance))
        )

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted(self.qx_by_year))

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
            by_sex = self.qx_by_year[int(year)]
        except KeyError as error:
            raise KeyError(
                f"no {self.baseline} mortality for {year}; load the model "
                "for every projection year"
            ) from error
        age = frame["age"].to_numpy(dtype=np.int64)
        if (age < 0).any():
            raise ValueError("mortality ages must be non-negative")
        index = np.minimum(age, MAX_AGE)
        sex = frame["sex"].astype(str).to_numpy()
        out = np.full(len(frame), np.nan)
        for label in SEXES:
            rows = sex == label
            out[rows] = by_sex[label][index[rows]]
        if np.isnan(out).any():
            unknown = sorted(set(sex[np.isnan(out)]))
            raise ValueError(f"unknown mortality sex labels {unknown}")
        return out

    def __call__(
        self, frame: pd.DataFrame, context: PeriodContext
    ) -> np.ndarray:
        return self.probabilities_for_year(frame, context.year)


@runtime_checkable
class Baseline(Protocol):
    """What a selectable projection baseline supplies.

    ``name`` is the registry key, ``vintage`` a human-readable label of
    the sources' vintage.  ``claim_table_max_year`` is the last claim-age
    table row the projection may read (every later year snaps to it).
    """

    name: str
    vintage: str
    claim_table_max_year: int

    def cola_rates(self, first: int, last: int) -> COLASeries:
        """Determination-year COLA fractions, realized history to ``last``.

        The series starts at the realized history's first year (1979) and
        is consecutive through ``last``.  ``first`` is the caller's first
        rate year (the A1 section 4 splice year, ``TrackAConfig.
        tr2008_first_rate_year``): the legacy baseline takes TR2008's
        rates from it on.  Every 2026 baseline instead keeps the
        committed history through 2022 and the realized V.C1 rows through
        the last actual determination year (2025) whatever ``first`` is,
        so its path does not depend on ``first``.
        """
        ...

    def cpiw_growth(self, year: int) -> float:
        """Annual-average CPI-W growth in ``year``, percent."""
        ...

    def awi(self, first: int, last: int) -> dict[int, float]:
        """AWI in dollars for every year ``first..last``."""
        ...

    def ssa_parameters(self, params: SSAParameters) -> SSAParameters:
        """``params`` with NAWI replaced by the baseline's AWI.

        Years from :data:`AWI_FIRST_REPLACED_YEAR` take the baseline's
        AWI (``dataclasses.replace(params, nawi=...)``); earlier years
        keep ``params``'s series.
        """
        ...

    def qx(self, year: int) -> dict[str, np.ndarray]:
        """Death probabilities by sex for ages 0-120 in ``year``."""
        ...

    def population_mortality(self, years: range) -> Any:
        """A year-aware single-age model covering every year in ``years``."""
        ...

    def tfr(self, year: int) -> float:
        """Period total fertility rate in ``year``, births per woman."""
        ...

    def asfr(self, year: int) -> dict[int, float]:
        """Births per woman at single ages 14-49 in ``year``."""
        ...

    def claim_pmf(self) -> dict[tuple[str, int], dict[int, float]]:
        """Claim-age PMFs by (sex, entitlement year), every table row."""
        ...

    def di_rates(
        self, spec: DIEntitlementSpec | None = None
    ) -> DIEntitlementRates:
        """DI incidence, recovery and death rates for ``spec``."""
        ...

    def value_sources(self, year: int) -> dict[str, str]:
        """Source tag of every series' value in ``year`` (derived tagged)."""
        ...

    def provenance(self) -> dict[str, Any]:
        """Sources, SHA-256 of every file read, splices and gaps."""
        ...
