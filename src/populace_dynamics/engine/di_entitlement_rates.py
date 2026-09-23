"""Fitted SSDI disabled-worker entitlement rates (Track A item A4).

This module turns the extracted <=2008 inputs in
``data/external/di_asr_2008/tables.json`` (built by
``scripts/extract_di_asr_2008.py``) into the annual transition
probabilities used by :mod:`populace_dynamics.engine.di_entitlement`:

* **Award incidence per population.**  For each age band and sex,
  ``awards / (resident population - disabled-worker stock)`` in the fit
  year: disabled-worker awards by age at entitlement (SSA DI Annual
  Statistical Report, Table 36), July 1 resident population by single year of
  age (Census Bureau national estimates, same vintage), and the December
  disabled-worker stock (ASR Table 20).  The denominator is the whole
  non-entitled population, not the disability-insured population, so the
  rate folds the fit year's insured share into the hazard and the model never
  encodes insured status.  That is the plan's proposed primary; it is an
  explicit :class:`DIEntitlementSpec` field, not a hidden assumption.
* **Recovery** (benefits terminated because the worker no longer meets the
  medical standards: medical improvement, work above SGA, miscellaneous).
  The age and sex profile is SSA Actuarial Study No. 118 (1996-2000
  experience): Table 19 by attained age, or Tables 14A-14B by select age and
  duration.  By default one level factor rescales the profile so that the
  expected recoveries on the fit year's exposure equal ASR Table 50's
  recoveries.  The Actuarial Study probabilities are multiple-decrement
  probabilities, but the loop draws recovery only for the survivors of the
  mortality step, so the realized recovery probability is ``(1 - q_death)
  * q_recovery``: 2.5 percent below the fit's target on the 2008 exposure.
  The fit does not correct for that.
* **Death** of disabled workers.  The reference profile is Actuarial Study
  No. 118 Table 12 (attained age, ages 16-74) and Table 7C (ages 75-110), or
  Tables 7A-7C by select age and duration.  In the default ``multiplier``
  mode the engine applies ``q_DI_ref * q_population_engine /
  q_population_ref``, where ``q_population_ref`` is the NCHS United States
  2000 life table *at the population model's own age resolution*: the
  stationary-population (``l_x``-weighted) mean of the NCHS 2000
  probabilities over the population model's age band containing the person
  (the single-age probability for a single-year-of-age model).  The
  multiplier is therefore constant within each population age band, so it
  carries the engine's mortality level (and any improvement) relative to
  NCHS 2000 without reshaping the Actuarial Study age profile.  The 2008
  Trustees Report likewise moves long-range DI death rates at the same rate
  as general-population death rates by age and sex.  ``explicit`` mode
  applies the Actuarial Study probabilities themselves.
* **Everyone else.**  The population mortality model and the NCHS table are
  all-person mortality: their deaths already include disabled workers'.
  By default (``non_di_mortality="net_of_di_origin"``) the adapter therefore
  scales the non-DI-origin probabilities within each population age band and
  sex so that the cell's expected deaths stay equal to the population
  model's; the component redistributes deaths rather than adding them.
  ``population_total`` keeps the population probabilities for non-DI-origin
  persons, which adds the disabled-worker excess deaths on top of the
  population model (about 25 to 35 percent more deaths at ages 45-64 at the
  2008 disabled-worker prevalence).

Rates are fit or taken from data years no later than 2008 (the DYNASIM
information date).  The 2023 DI Annual Statistical Report in
``data/external/di_asr_2023`` is validation-only and is never read here.

Arrays are indexed ``[sex_index, age]`` with ``sex_index`` from
:data:`SEXES` and ``age`` in ``0..MAX_AGE``.  Every age used for a lookup is
the person's age at the start of the projection year
(``year - 1 - birth_year``); see :mod:`populace_dynamics.engine.di_entitlement`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "DEATH_LEVELS",
    "DEATH_MODES",
    "DEFAULT_INPUTS_PATH",
    "DIEntitlementRates",
    "DIEntitlementSpec",
    "FIT_YEARS",
    "INCIDENCE_BANDS",
    "INCIDENCE_BASES",
    "INFORMATION_BOUNDARY_YEAR",
    "MAX_AGE",
    "NCHS_2000_PATH",
    "NON_DI_MORTALITY",
    "POST_CONVERSION_MORTALITY",
    "RECOVERY_LEVELS",
    "SEXES",
    "SINGLE_YEAR_AGE_BANDS",
    "SelectUltimateTable",
    "TERMINATION_BASES",
    "fit_di_entitlement_rates",
    "load_di_entitlement_rates",
    "pending_decisions",
    "validate_age_bands",
]

_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS_PATH = (
    _ROOT / "data" / "external" / "di_asr_2008" / "tables.json"
)
NCHS_2000_PATH = _ROOT / "data" / "external" / "nchs_life_tables_2000.json"

INPUTS_SCHEMA_VERSION = "di_entitlement_inputs.v1"
INFORMATION_BOUNDARY_YEAR = 2008
SEXES = ("female", "male")
MAX_AGE = 120
#: Age resolution of a single-year-of-age population mortality model, for
#: callers of the multiplier death mode whose model has no ``bands``.
SINGLE_YEAR_AGE_BANDS: tuple[tuple[int, int], ...] = tuple(
    (age, age) for age in range(MAX_AGE + 1)
)

#: Award-incidence age bands (inclusive start-of-year ages) and the ASR
#: Table 36 / Table 20 age group each band is fit on.  The last band covers
#: the ages below the full retirement age; the adapter never exposes anyone
#: in or after the calendar year of FRA attainment.
INCIDENCE_BANDS: tuple[tuple[int, int, str], ...] = (
    (18, 24, "Under 25"),
    (25, 29, "25–29"),
    (30, 34, "30–34"),
    (35, 39, "35–39"),
    (40, 44, "40–44"),
    (45, 49, "45–49"),
    (50, 54, "50–54"),
    (55, 59, "55–59"),
    (60, 64, "60–64"),
    (65, 69, "65–FRA"),
)
#: Single ages that represent each ASR group in the fit denominators and in
#: the recovery/death level fits.  "Under 25" starts at the minimum award
#: age; "65–FRA" is age 65 only (FRA was 65y10m-66 for the fit-year cohorts).
_GROUP_AGES: dict[str, tuple[int, int]] = {
    "Under 25": (18, 24),
    "25–29": (25, 29),
    "30–34": (30, 34),
    "35–39": (35, 39),
    "40–44": (40, 44),
    "45–49": (45, 49),
    "50–54": (50, 54),
    "55–59": (55, 59),
    "60–64": (60, 64),
    "65–FRA": (65, 65),
}
#: ASR 2007 labels its oldest award group "65 or older"; entitlement ends at
#: FRA, so it is the same 65-to-FRA group.
_GROUP_ALIASES = {"65 or older": "65–FRA"}

FIT_YEARS = ("2008", "2007", "2007-2008")
INCIDENCE_BASES = ("per_population_non_entitled", "per_insured")
DEATH_MODES = ("multiplier", "explicit")
DEATH_LEVELS = ("as118_published", "asr_fitted")
RECOVERY_LEVELS = ("asr_fitted", "as118_published")
TERMINATION_BASES = ("attained_age", "select_and_ultimate")
POST_CONVERSION_MORTALITY = ("di_origin", "population")
NON_DI_MORTALITY = ("net_of_di_origin", "population_total")


@dataclass(frozen=True)
class DIEntitlementSpec:
    """Every modeling choice of the DI entitlement component, made explicit.

    Defaults are the critical-path plan's proposed primary where the plan
    names one (``incidence_basis``) and otherwise the builder's proposed
    primary.  None of these has been ratified; :func:`pending_decisions`
    lists them for the A1 specification freeze.
    """

    #: Calendar year(s) whose SSA awards, stock, and terminations fit the
    #: incidence and termination levels.  ``"2007"`` uses only information
    #: published by September 2008; ``"2008"`` uses 2008 data (published
    #: July 2009); ``"2007-2008"`` pools both years.
    fit_year: str = "2008"
    #: ``per_population_non_entitled`` (plan primary): awards over the whole
    #: non-entitled population, so insured status is never encoded.
    #: ``per_insured`` would need rates per disability-insured person and an
    #: insured-status column; no such rates are captured, so fitting refuses.
    incidence_basis: str = "per_population_non_entitled"
    #: ``multiplier``: q_DI_ref * q_population_engine / q_population_ref
    #: (NCHS 2000 averaged over the population model's age band).
    #: ``explicit``: the Actuarial Study probabilities.
    death_mode: str = "multiplier"
    #: Explicit mode only: ``as118_published`` keeps the 1996-2000 level;
    #: ``asr_fitted`` rescales it to the fit year's ASR Table 50 deaths.
    death_level: str = "as118_published"
    #: ``asr_fitted``: rescale the Actuarial Study recovery profile to the fit
    #: year's ASR Table 50 recoveries.  ``as118_published``: 1996-2000 level.
    recovery_level: str = "asr_fitted"
    #: ``attained_age`` (Actuarial Study Tables 12/19) needs no award year;
    #: ``select_and_ultimate`` (Tables 7A-7C/14A-14B) needs the award year of
    #: every disabled-worker-origin person, including the opening stock.
    termination_basis: str = "attained_age"
    #: ``di_origin``: persons converted at FRA keep disabled-worker mortality
    #: (Actuarial Study No. 118 follows them past conversion).
    #: ``population``: they revert to population mortality.
    post_conversion_mortality: str = "di_origin"
    #: ``net_of_di_origin``: the population model is all-person mortality,
    #: so within each population age band and sex the non-DI-origin
    #: probabilities are scaled to keep the cell's expected (weighted) deaths
    #: equal to the population model's.  ``population_total``: non-DI-origin
    #: persons keep the population probabilities, so the DI-origin excess
    #: deaths are added to the population model's total.
    non_di_mortality: str = "net_of_di_origin"
    #: Minimum start-of-year age exposed to award incidence.
    min_award_age: int = 18
    #: Birth month assumed when the frame has no ``birth_month`` column; it
    #: fixes the calendar year in which FRA (in months) is attained.
    assumed_birth_month: int = 7
    #: Refuse frames whose ``age`` column disagrees with ``year - birth_year``.
    validate_age_column: bool = True

    def __post_init__(self) -> None:
        choices = {
            "fit_year": (self.fit_year, FIT_YEARS),
            "incidence_basis": (self.incidence_basis, INCIDENCE_BASES),
            "death_mode": (self.death_mode, DEATH_MODES),
            "death_level": (self.death_level, DEATH_LEVELS),
            "recovery_level": (self.recovery_level, RECOVERY_LEVELS),
            "termination_basis": (self.termination_basis, TERMINATION_BASES),
            "post_conversion_mortality": (
                self.post_conversion_mortality,
                POST_CONVERSION_MORTALITY,
            ),
            "non_di_mortality": (self.non_di_mortality, NON_DI_MORTALITY),
        }
        for name, (value, allowed) in choices.items():
            if value not in allowed:
                raise ValueError(f"{name} must be one of {allowed}: {value!r}")
        if self.death_mode == "multiplier" and self.death_level != (
            "as118_published"
        ):
            raise ValueError(
                "death_level applies only to explicit death rates; the "
                "multiplier takes its level from the engine's population "
                "mortality"
            )
        lowest_band_age = INCIDENCE_BANDS[0][0]
        if not lowest_band_age <= int(self.min_award_age) <= 64:
            # Below the lowest fitted band the incidence is zero, so a lower
            # minimum would be accepted but have no effect.
            raise ValueError(
                f"min_award_age must lie in [{lowest_band_age}, 64]; the "
                f"fitted incidence bands start at age {lowest_band_age}"
            )
        if not 1 <= int(self.assumed_birth_month) <= 12:
            raise ValueError("assumed_birth_month must lie in [1, 12]")

    def as_dict(self) -> dict[str, Any]:
        return {
            "fit_year": self.fit_year,
            "incidence_basis": self.incidence_basis,
            "death_mode": self.death_mode,
            "death_level": self.death_level,
            "recovery_level": self.recovery_level,
            "termination_basis": self.termination_basis,
            "post_conversion_mortality": self.post_conversion_mortality,
            "non_di_mortality": self.non_di_mortality,
            "min_award_age": int(self.min_award_age),
            "assumed_birth_month": int(self.assumed_birth_month),
            "validate_age_column": bool(self.validate_age_column),
        }


_PENDING: tuple[tuple[str, str, str], ...] = (
    (
        "incidence_basis",
        "plan section 4 A4 proposes per-population incidence (avoids "
        "encoding insured status); unratified until the A1 freeze",
        "per_insured (refused: no per-insured rates captured)",
    ),
    (
        "death_mode",
        "plan section 4 A4 leaves 'DI mortality multiplier or life table, "
        "frozen'; builder default multiplier",
        "explicit",
    ),
    (
        "fit_year",
        "task: 2008 (or 2007) DI ASR; 2008 data were released July 2009",
        "2007 (released September 2008); 2007-2008 pooled",
    ),
    (
        "recovery_level",
        "builder default: Actuarial Study No. 118 profile rescaled to the "
        "fit year's ASR recoveries",
        "as118_published (1996-2000 level)",
    ),
    (
        "termination_basis",
        "builder default: attained-age aggregates, because the PSID opening "
        "stock has no observed award year",
        "select_and_ultimate (needs award years)",
    ),
    (
        "post_conversion_mortality",
        "builder default: converted disabled workers keep DI-origin "
        "mortality",
        "population",
    ),
    (
        "non_di_mortality",
        "review default: the population mortality model (like NCHS 2000) "
        "is all-person mortality, so keeping it for non-DI-origin persons "
        "adds the disabled-worker excess deaths on top (about 25-35 percent "
        "more deaths at ages 45-64 at 2008 DI prevalence)",
        "population_total (non-DI-origin persons keep the population "
        "probabilities)",
    ),
    (
        "death_level",
        "explicit mode only; builder default keeps the 1996-2000 level",
        "asr_fitted",
    ),
)


def pending_decisions(
    spec: DIEntitlementSpec | None = None,
) -> list[dict[str, str]]:
    """List the choices that await the A1 specification freeze."""
    resolved = spec or DIEntitlementSpec()
    values = resolved.as_dict()
    return [
        {
            "field": name,
            "value": str(values[name]),
            "basis": basis,
            "alternatives": alternatives,
        }
        for name, basis, alternatives in _PENDING
    ]


def validate_age_bands(
    age_bands: Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    """Check a population model's inclusive age bands; clip them to MAX_AGE.

    The bands must start at age 0, be contiguous and non-overlapping, and
    reach ``MAX_AGE`` (the same contract as
    :class:`populace_dynamics.engine.steps.AgeSexMortalityModel`).
    """
    bands = [(int(lower), int(upper)) for lower, upper in age_bands]
    if not bands or bands[0][0] != 0:
        raise ValueError("population age bands must start at age 0")
    previous_upper = -1
    for lower, upper in bands:
        if lower != previous_upper + 1 or upper < lower:
            raise ValueError(
                "population age bands must be contiguous and non-overlapping"
            )
        previous_upper = upper
    if previous_upper < MAX_AGE:
        raise ValueError(f"population age bands must reach age {MAX_AGE}")
    return tuple(
        (lower, min(upper, MAX_AGE))
        for lower, upper in bands
        if lower <= MAX_AGE
    )


@dataclass(frozen=True)
class SelectUltimateTable:
    """Probabilities by select age and duration, then by attained age.

    ``select[sex, select_age - 16, duration]`` covers durations 0-9 (NaN
    where Actuarial Study No. 118 shows no value).  ``ultimate[sex, age]``
    covers ten or more years since selection by attained age.
    """

    select: np.ndarray
    ultimate: np.ndarray
    first_select_age: int = 16
    last_select_age: int = 64

    def lookup(
        self,
        sex_index: np.ndarray,
        select_age: np.ndarray,
        duration: np.ndarray,
        attained_age: np.ndarray,
    ) -> np.ndarray:
        """Return one probability per row; NaN only if no value exists."""
        sex_index = np.asarray(sex_index, dtype=np.int64)
        select_row = (
            np.clip(
                np.asarray(select_age, dtype=np.int64),
                self.first_select_age,
                self.last_select_age,
            )
            - self.first_select_age
        )
        duration = np.asarray(duration, dtype=np.int64)
        if (duration < 0).any():
            raise ValueError("durations must be non-negative")
        attained = np.clip(
            np.asarray(attained_age, dtype=np.int64), 0, MAX_AGE
        )
        out = self.ultimate[sex_index, attained].copy()
        in_select = duration < self.select.shape[2]
        if in_select.any():
            rows = np.flatnonzero(in_select)
            out[rows] = self.select[
                sex_index[rows], select_row[rows], duration[rows]
            ]
        return out

    def scaled(self, factor: float) -> SelectUltimateTable:
        return SelectUltimateTable(
            select=self.select * factor,
            ultimate=self.ultimate * factor,
            first_select_age=self.first_select_age,
            last_select_age=self.last_select_age,
        )


@dataclass(frozen=True)
class DIEntitlementRates:
    """Annual probabilities for the DI entitlement adapter, with provenance."""

    spec: DIEntitlementSpec
    incidence: np.ndarray
    recovery_attained: np.ndarray
    death_attained: np.ndarray
    population_reference_death: np.ndarray
    recovery_select: SelectUltimateTable | None
    death_select: SelectUltimateTable | None
    recovery_level_factor: float
    death_level_factor: float
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        shape = (len(SEXES), MAX_AGE + 1)
        for name in (
            "incidence",
            "recovery_attained",
            "death_attained",
            "population_reference_death",
        ):
            values = np.asarray(getattr(self, name), dtype=np.float64)
            if values.shape != shape:
                raise ValueError(f"{name} must have shape {shape}")
            if not np.isfinite(values).all():
                raise ValueError(f"{name} contains non-finite values")
            if ((values < 0) | (values > 1)).any():
                raise ValueError(f"{name} probabilities must lie in [0, 1]")
        if (self.population_reference_death <= 0).any():
            raise ValueError("population reference mortality must be > 0")
        if self.spec.termination_basis == "select_and_ultimate" and (
            self.recovery_select is None or self.death_select is None
        ):
            raise ValueError("select-and-ultimate basis needs select tables")

    @staticmethod
    def _age_index(age: np.ndarray) -> np.ndarray:
        values = np.asarray(age, dtype=np.int64)
        if (values < 0).any():
            raise ValueError("ages must be non-negative")
        return np.minimum(values, MAX_AGE)

    def incidence_probability(
        self, start_age: np.ndarray, sex_index: np.ndarray
    ) -> np.ndarray:
        """Annual award probability for a non-entitled person."""
        return self.incidence[
            np.asarray(sex_index, dtype=np.int64), self._age_index(start_age)
        ]

    def recovery_probability(
        self,
        start_age: np.ndarray,
        sex_index: np.ndarray,
        *,
        select_age: np.ndarray | None = None,
        duration: np.ndarray | None = None,
    ) -> np.ndarray:
        """Annual recovery-termination probability for an entitled worker."""
        sex_index = np.asarray(sex_index, dtype=np.int64)
        ages = self._age_index(start_age)
        if self.spec.termination_basis == "attained_age":
            return self.recovery_attained[sex_index, ages]
        assert self.recovery_select is not None
        if select_age is None or duration is None:
            raise ValueError("select-and-ultimate recovery needs award years")
        values = self.recovery_select.lookup(
            sex_index, select_age, duration, ages
        )
        # Tables 14A-14B leave every cell past attained age 64 blank, select
        # and ultimate alike ("Recovery is not considered beyond normal
        # retirement age", then 65), so a worker with a higher FRA gets zero
        # recovery there on this basis at any duration.
        return np.nan_to_num(values, nan=0.0)

    def reference_death_probability(
        self,
        start_age: np.ndarray,
        sex_index: np.ndarray,
        *,
        select_age: np.ndarray | None = None,
        duration: np.ndarray | None = None,
    ) -> np.ndarray:
        """Disabled-worker-origin death probability before any multiplier."""
        sex_index = np.asarray(sex_index, dtype=np.int64)
        ages = self._age_index(start_age)
        if self.spec.termination_basis == "attained_age":
            return self.death_attained[sex_index, ages]
        assert self.death_select is not None
        if select_age is None or duration is None:
            raise ValueError("select-and-ultimate death needs award years")
        values = self.death_select.lookup(
            sex_index, select_age, duration, ages
        )
        if np.isnan(values).any():
            raise ValueError("select-and-ultimate death table has a gap")
        return values

    def population_reference_probability(
        self,
        start_age: np.ndarray,
        sex_index: np.ndarray,
        *,
        age_bands: Sequence[tuple[int, int]],
    ) -> np.ndarray:
        """NCHS 2000 death probability at a population model's resolution.

        The multiplier base must have the same age resolution as the
        population mortality it divides; otherwise, for example, a 10-year
        band probability divided by single-age NCHS probabilities would
        inflate disabled-worker mortality at the bottom of each band and
        deflate it at the top.  Each person's base is the mean of the NCHS
        2000 probabilities over the ages of the band containing the person,
        weighted by the reference table's own survivorship from the band's
        first age (the stationary population ``l_x``).  For a single-age
        band the base is exactly that age's probability.
        """
        by_age = self._banded_population_reference(age_bands)
        return by_age[
            np.asarray(sex_index, dtype=np.int64), self._age_index(start_age)
        ]

    def _banded_population_reference(
        self, age_bands: Sequence[tuple[int, int]]
    ) -> np.ndarray:
        bands = validate_age_bands(age_bands)
        reference = np.asarray(self.population_reference_death, np.float64)
        out = np.empty_like(reference)
        for lower, upper in bands:
            if lower == upper:
                out[:, lower] = reference[:, lower]
                continue
            q = reference[:, lower : upper + 1]
            survivorship = np.ones_like(q)
            survivorship[:, 1:] = np.cumprod(1.0 - q[:, :-1], axis=1)
            weight = survivorship / survivorship.sum(axis=1, keepdims=True)
            out[:, lower : upper + 1] = (weight * q).sum(axis=1)[:, None]
        return out

    def summary(self) -> dict[str, Any]:
        """JSON-ready rate tables for reports and pinning tests."""
        bands = []
        for lower, upper, label in INCIDENCE_BANDS:
            bands.append(
                {
                    "band": label,
                    "start_ages": [lower, upper],
                    "female": float(self.incidence[0, lower]),
                    "male": float(self.incidence[1, lower]),
                }
            )
        ages = list(range(18, 67))
        return {
            "spec": self.spec.as_dict(),
            "incidence_by_band": bands,
            "recovery_attained": {
                sex: [float(self.recovery_attained[i, a]) for a in ages]
                for i, sex in enumerate(SEXES)
            },
            "death_attained": {
                sex: [float(self.death_attained[i, a]) for a in ages]
                for i, sex in enumerate(SEXES)
            },
            "attained_ages": ages,
            "recovery_level_factor": self.recovery_level_factor,
            "death_level_factor": self.death_level_factor,
            "diagnostics": dict(self.diagnostics),
            "provenance": dict(self.provenance),
        }


def _validate_inputs(inputs: Mapping[str, Any]) -> None:
    if inputs.get("schema_version") != INPUTS_SCHEMA_VERSION:
        raise ValueError(
            "DI entitlement inputs have schema "
            f"{inputs.get('schema_version')!r}, not {INPUTS_SCHEMA_VERSION!r}"
        )
    boundary = int(inputs.get("information_boundary_year", 10_000))
    if boundary > INFORMATION_BOUNDARY_YEAR:
        raise ValueError(
            f"inputs declare information boundary {boundary}, after "
            f"{INFORMATION_BOUNDARY_YEAR}"
        )
    for source_id, source in inputs.get("sources", {}).items():
        last_year = int(str(source["data_year"]).split("-")[-1])
        if last_year > INFORMATION_BOUNDARY_YEAR:
            raise ValueError(
                f"source {source_id} has data year {source['data_year']}, "
                f"after {INFORMATION_BOUNDARY_YEAR}"
            )
    for key in ("asr", "census_resident_population_july1", "as118"):
        if key not in inputs:
            raise ValueError(f"DI entitlement inputs are missing {key!r}")


def _fit_years(spec: DIEntitlementSpec) -> tuple[str, ...]:
    return {
        "2008": ("2008",),
        "2007": ("2007",),
        "2007-2008": ("2007", "2008"),
    }[spec.fit_year]


def _by_group(table: Mapping[str, Any], sex: str) -> dict[str, float]:
    labels = [_GROUP_ALIASES.get(g, g) for g in table["age_groups"]]
    if sorted(labels) != sorted(_GROUP_AGES):
        raise ValueError(f"unexpected ASR age groups {table['age_groups']}")
    return {
        label: float(value)
        for label, value in zip(labels, table[sex], strict=True)
    }


def _population_by_group(
    census: Mapping[str, Any], sex: str
) -> dict[str, float]:
    ages = list(census["ages"])
    counts = dict(zip(ages, census[sex], strict=True))
    return {
        label: float(sum(counts[a] for a in range(lower, upper + 1)))
        for label, (lower, upper) in _GROUP_AGES.items()
    }


def _series(
    ages: Sequence[int], values: Sequence[float | None], *, fill: str
) -> np.ndarray:
    """Place a published age series on ``0..MAX_AGE`` holding edge values."""
    out = np.full(MAX_AGE + 1, np.nan)
    for age, value in zip(ages, values, strict=True):
        if value is not None:
            out[int(age)] = float(value)
    known = np.flatnonzero(~np.isnan(out))
    if not len(known):
        raise ValueError("empty age series")
    if fill != "hold":
        raise ValueError(f"unknown fill rule {fill!r}")
    out[: known[0]] = out[known[0]]
    out[known[-1] + 1 :] = out[known[-1]]
    gaps = np.isnan(out)
    if gaps.any():
        out[gaps] = np.interp(np.flatnonzero(gaps), known, out[known])
    return out


def _select_table(
    tables: Mapping[str, Any],
    old_age: Mapping[str, Any] | None,
    *,
    blank_after_last: bool = False,
) -> SelectUltimateTable:
    """Select cells and the ultimate column on ``0..MAX_AGE``.

    Blank published cells stay NaN.  The ultimate column holds its edge
    values, except that with ``blank_after_last`` the attained ages after
    the last published ultimate value stay NaN, like the blank select cells
    at the same attained ages (the recovery tables, which stop at 64).
    """
    select = np.full((len(SEXES), 49, 10), np.nan)
    ultimate = np.full((len(SEXES), MAX_AGE + 1), np.nan)
    for sex_index, sex in enumerate(SEXES):
        table = tables[sex]
        if list(table["select_ages"]) != list(range(16, 65)):
            raise ValueError("unexpected select ages")
        for row, values in enumerate(table["select"]):
            select[sex_index, row] = [
                np.nan if value is None else float(value) for value in values
            ]
        ages = list(table["ultimate_attained_ages"])
        values = list(table["ultimate"])
        if old_age is not None:
            ages += list(old_age["ages"])
            values += list(old_age[sex])
        ultimate[sex_index] = _series(ages, values, fill="hold")
        if blank_after_last:
            last = max(
                int(age)
                for age, value in zip(ages, values, strict=True)
                if value is not None
            )
            ultimate[sex_index, last + 1 :] = np.nan
    return SelectUltimateTable(select=select, ultimate=ultimate)


def _exposure_scale(
    distribution: Mapping[str, Any], year: str, sex: str
) -> float:
    """Average-year exposure over the December stock, from ASR Table 19."""
    section = distribution["men" if sex == "male" else "women"]
    prior = float(section[str(int(year) - 1)]["number_thousands"])
    current = float(section[year]["number_thousands"])
    return (prior + current) / (2.0 * current)


def _group_mean(series: np.ndarray, sex_index: int, label: str) -> float:
    lower, upper = _GROUP_AGES[label]
    return float(series[sex_index, lower : upper + 1].mean())


def fit_di_entitlement_rates(
    inputs: Mapping[str, Any],
    nchs_2000: Mapping[str, Any],
    spec: DIEntitlementSpec | None = None,
) -> DIEntitlementRates:
    """Fit the DI entitlement rates from extracted <=2008 inputs."""
    spec = spec or DIEntitlementSpec()
    _validate_inputs(inputs)
    if spec.incidence_basis != "per_population_non_entitled":
        raise ValueError(
            "per-insured incidence needs rates per disability-insured person "
            "and an insured-status column; neither is captured (Actuarial "
            "Study No. 118 Table 4 would be the source)"
        )
    if int(nchs_2000.get("vintage_year", 0)) != 2000:
        raise ValueError("the multiplier base must be the NCHS 2000 table")
    years = _fit_years(spec)
    asr = inputs["asr"]
    census = inputs["census_resident_population_july1"]
    for year in years:
        if year not in asr or year not in census:
            raise ValueError(f"fit year {year} is missing from the inputs")

    # --- award incidence per non-entitled population -------------------
    incidence = np.zeros((len(SEXES), MAX_AGE + 1))
    incidence_rows: list[dict[str, Any]] = []
    for sex_index, sex in enumerate(SEXES):
        awards = {label: 0.0 for label in _GROUP_AGES}
        exposed = {label: 0.0 for label in _GROUP_AGES}
        population = {label: 0.0 for label in _GROUP_AGES}
        stock = {label: 0.0 for label in _GROUP_AGES}
        for year in years:
            year_awards = _by_group(asr[year]["awards_workers"], sex)
            year_stock = _by_group(asr[year]["stock_workers_december"], sex)
            year_population = _population_by_group(census[year], sex)
            for label in _GROUP_AGES:
                awards[label] += year_awards[label]
                stock[label] += year_stock[label]
                population[label] += year_population[label]
                exposed[label] += year_population[label] - year_stock[label]
        for lower, upper, label in INCIDENCE_BANDS:
            if exposed[label] <= 0:
                raise ValueError(f"non-positive exposure for {label} {sex}")
            rate = awards[label] / exposed[label]
            incidence[sex_index, lower : upper + 1] = rate
            incidence_rows.append(
                {
                    "sex": sex,
                    "band": label,
                    "awards": awards[label],
                    "population_july1": population[label],
                    "stock_december": stock[label],
                    "non_entitled_population": exposed[label],
                    "annual_probability": rate,
                }
            )
    incidence[:, : spec.min_award_age] = 0.0

    # --- Actuarial Study No. 118 reference profiles ---------------------
    as118 = inputs["as118"]
    death_tables = as118["death"]
    recovery_tables = as118["recovery"]
    death_attained = np.zeros((len(SEXES), MAX_AGE + 1))
    recovery_attained = np.zeros((len(SEXES), MAX_AGE + 1))
    for sex_index, sex in enumerate(SEXES):
        aggregate = death_tables["aggregate_by_attained_age"]
        old = death_tables["ultimate_75_plus"]
        death_attained[sex_index] = _series(
            [*aggregate["ages"], *old["ages"]],
            [*aggregate[sex], *old[sex]],
            fill="hold",
        )
        recovery = recovery_tables["aggregate_by_attained_age"]
        recovery_attained[sex_index] = _series(
            recovery["ages"], recovery[sex], fill="hold"
        )
    death_select = _select_table(
        death_tables["select_ultimate"], death_tables["ultimate_75_plus"]
    )
    # Tables 14A-14B show no recovery past attained age 64 in either the
    # select cells or the ultimate column ("Recovery is not considered
    # beyond normal retirement age"), so neither is extended past 64.
    recovery_select = _select_table(
        recovery_tables["select_ultimate"], None, blank_after_last=True
    )

    # --- level diagnostics and fits on the fit year's exposure ----------
    observed_recoveries = 0.0
    observed_deaths = 0.0
    expected_recoveries = 0.0
    expected_deaths = 0.0
    exposure_total = 0.0
    for year in years:
        terminations = asr[year]["terminations_workers_by_reason"]
        observed_recoveries += float(
            terminations["does_not_meet_medical_standards"]
        )
        observed_deaths += float(terminations["death"])
        distribution = asr[year]["stock_distribution"]
        for sex_index, sex in enumerate(SEXES):
            scale = _exposure_scale(distribution, year, sex)
            stock = _by_group(asr[year]["stock_workers_december"], sex)
            for label, count in stock.items():
                exposure = count * scale
                exposure_total += exposure
                expected_recoveries += exposure * _group_mean(
                    recovery_attained, sex_index, label
                )
                expected_deaths += exposure * _group_mean(
                    death_attained, sex_index, label
                )
    recovery_factor_fitted = observed_recoveries / expected_recoveries
    death_factor_fitted = observed_deaths / expected_deaths
    recovery_factor = (
        recovery_factor_fitted if spec.recovery_level == "asr_fitted" else 1.0
    )
    death_factor = (
        death_factor_fitted
        if spec.death_mode == "explicit" and spec.death_level == "asr_fitted"
        else 1.0
    )
    recovery_attained = np.clip(recovery_attained * recovery_factor, 0, 1)
    death_attained = np.clip(death_attained * death_factor, 0, 1)
    recovery_select = recovery_select.scaled(recovery_factor)
    death_select = death_select.scaled(death_factor)

    # --- NCHS 2000 population reference (multiplier base) ---------------
    population_reference = np.zeros((len(SEXES), MAX_AGE + 1))
    for sex_index, sex in enumerate(SEXES):
        rows = nchs_2000["tables"][sex]
        # Age 100 is the open "100 and over" interval (q = 1); hold age 99.
        rows = [row for row in rows if int(row["age"]) < 100]
        population_reference[sex_index] = _series(
            [row["age"] for row in rows],
            [row["qx"] for row in rows],
            fill="hold",
        )

    diagnostics = {
        "fit_years": list(years),
        "incidence": incidence_rows,
        "recovery_level": {
            "observed_asr_table50_does_not_meet_medical_standards": (
                observed_recoveries
            ),
            "expected_under_as118_table19": expected_recoveries,
            "fitted_factor": recovery_factor_fitted,
            "applied_factor": recovery_factor,
        },
        "death_level": {
            "observed_asr_table50_deaths": observed_deaths,
            "expected_under_as118_table12_7c": expected_deaths,
            "fitted_factor": death_factor_fitted,
            "applied_factor": death_factor,
        },
        "average_exposure_workers": exposure_total,
        "exposure_rule": (
            "December ASR Table 20 stock by age group and sex, scaled by "
            "the ASR Table 19 average of the prior and current December "
            "totals; group rates are simple means of single-age rates over "
            "the ages in _GROUP_AGES"
        ),
    }
    # Exactly the extracted sections read above, by their source ids (ASR
    # Tables 35, 49, and 57 are extracted for diagnostics and never read).
    read_sections = [
        section
        for year in years
        for section in (
            asr[year]["awards_workers"],
            asr[year]["stock_workers_december"],
            asr[year]["stock_distribution"],
            asr[year]["terminations_workers_by_reason"],
            census[year],
        )
    ] + [death_tables, recovery_tables]
    sources_used = sorted(
        {
            str(section["source"])
            for section in read_sections
            if section.get("source") is not None
        }
    )
    undeclared = sorted(set(sources_used) - set(inputs.get("sources", {})))
    if undeclared:
        raise ValueError(
            f"DI entitlement inputs read undeclared sources {undeclared}"
        )
    provenance = {
        "information_boundary_year": INFORMATION_BOUNDARY_YEAR,
        "inputs_schema": INPUTS_SCHEMA_VERSION,
        "sources_used": sources_used,
        "population_reference": "NCHS United States Life Tables, 2000",
    }
    return DIEntitlementRates(
        spec=spec,
        incidence=incidence,
        recovery_attained=recovery_attained,
        death_attained=death_attained,
        population_reference_death=population_reference,
        recovery_select=recovery_select,
        death_select=death_select,
        recovery_level_factor=float(recovery_factor),
        death_level_factor=float(death_factor),
        diagnostics=diagnostics,
        provenance=provenance,
    )


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], str]:
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"{label} not found at {path}; the DI entitlement component "
            "refuses to run without its <=2008 inputs"
        ) from error
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def load_di_entitlement_rates(
    spec: DIEntitlementSpec | None = None,
    *,
    inputs_path: Path = DEFAULT_INPUTS_PATH,
    nchs_path: Path = NCHS_2000_PATH,
) -> DIEntitlementRates:
    """Load the committed inputs and fit the rates for ``spec``."""
    inputs, inputs_sha = _read_json(inputs_path, "DI entitlement inputs")
    nchs, nchs_sha = _read_json(nchs_path, "NCHS 2000 life table")
    rates = fit_di_entitlement_rates(inputs, nchs, spec)
    provenance = dict(rates.provenance)
    provenance["inputs_sha256"] = inputs_sha
    provenance["nchs_2000_sha256"] = nchs_sha
    return DIEntitlementRates(
        spec=rates.spec,
        incidence=rates.incidence,
        recovery_attained=rates.recovery_attained,
        death_attained=rates.death_attained,
        population_reference_death=rates.population_reference_death,
        recovery_select=rates.recovery_select,
        death_select=rates.death_select,
        recovery_level_factor=rates.recovery_level_factor,
        death_level_factor=rates.death_level_factor,
        diagnostics=rates.diagnostics,
        provenance=provenance,
    )
