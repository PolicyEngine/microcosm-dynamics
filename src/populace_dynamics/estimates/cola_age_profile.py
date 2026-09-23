"""Frozen-statistic tabulation for DynaSim scorecard exercise 1.

Exercise 1 is the change in average Social Security benefits by age group
in the reference year (2030) when every annual COLA from the first reformed
increase is one percentage point lower.  This module is Track A plan item A7
(``critical-path-cola-20260922.md`` section 4): the tabulation only.  It
takes per-person-per-draw rows for the reference period that already carry
both scenarios' benefits and reduces them to the five-group age profile,
per draw, with the mean and sample standard deviation over draws and a
person-disjoint half-split noise floor.  It does not project a population,
compute or index a benefit, read a comparator value, apply an acceptance
rule, or write an artifact.

The specification is NOT frozen until A1 is ratified (plan section 6 item
4).  Every convention that awaits that ratification is an explicit field of
:class:`ColaAgeProfileConfig` whose default is the plan's proposed primary;
:data:`PENDING_RULINGS` lists them and every result records the values used
and whether each equals the proposed primary.  (Max ruled the plan's
section 6 items 1-3 on 2026-09-23; none of them is a tabulation field.)

Input rows
----------
One row per ``(draw, person_id)`` with the columns in
:data:`REQUIRED_COLUMNS` (extra columns are ignored and listed; a DataFrame
with repeated column names is refused):

``draw``
    Non-negative integer draw index ``k`` (the engine's ``5200 + k`` seed
    convention); the set of draws must equal ``config.draw_indices``.
``person_id``
    Integer or string person key, one type for all rows.
``family_unit_id``
    Integer or string key of the person's family unit in the opening wave
    (A1 section 16: the 2011 interview number ER34101 for the 2011-wave
    population, the 2009 interview number ER34001 for the 2009-wave
    population), one type for all rows.  The default half-split floor
    partitions on it (``floor_split_unit``), so every draw of every member
    of a family unit falls on one side.  A person_id whose family unit
    differs between draws is refused.
``weight``
    Finite, non-negative person weight, shared by both scenarios.  Each
    draw uses its own rows' weights; persons whose weight differs between
    draws are counted in the input summary, not refused.
``birth_year``
    Integer birth year; the age rule turns it into the reporting age.  A
    person_id whose birth year differs between draws is refused.
``beneficiary_base`` / ``beneficiary_reform``
    Booleans: the person is a beneficiary in the reference period in that
    scenario.  A row with a false flag and a positive benefit is refused.
``benefit_base`` / ``benefit_reform``
    Finite, non-negative reference-period benefit totals.
``benefit_components``
    Mapping from a component name in :data:`COMPONENT_VOCABULARY` to
    ``{"base": amount, "reform": amount}``.  All components present must sum
    to the totals (within :data:`COMPONENT_SUM_REL_TOL` /
    :data:`COMPONENT_SUM_ABS_TOL`).  Unknown names are refused.  The
    statistic uses the benefit summed over ``config.components`` only.

Statistics (per draw ``k`` and age group ``g``)
-----------------------------------------------
With scenario memberships ``S_base``, ``S_reform`` (see
:data:`MEMBERSHIP_BASIS_DEFINITIONS`), selected benefit ``B_s,i`` and
weight ``w_i``::

    mu_s = sum_{i in S_s} w_i B_s,i / sum_{i in S_s} w_i
    ratio_of_scenario_means   = 100 * (mu_reform / mu_base - 1)
    mean_of_individual_ratios = 100 * (sum_{i in S_alt} w_i B_reform,i /
                                       B_base,i / sum_{i in S_alt} w_i - 1)

Both are percent changes of the reform relative to the baseline (negative is
a reduction; percent-of-scheduled is ``100 + value``).  Under identical
membership, which the default configuration requires, ``mu_reform / mu_base``
equals the ratio of weighted totals.

Undefined cells (A1 section 7): a cell with no members, zero total weight
or a non-positive baseline mean has no statistic in that draw.  It is
reported as undefined with its reason and never imputed.  A group's draw
summary requires every draw to be defined; otherwise its mean and SD are
null and the result lists the number of defined draws and each undefined
draw's reason.  The other groups and statistics are reported as usual, so
one undefined cell never withholds the rest of the profile.

Uncertainty
-----------
The reported value per group and statistic is the mean over draws of the
per-draw statistic (``math.fsum``), with the ``ddof=1`` sample standard
deviation, the formula of ``estimates.first_report._numeric_aggregate``
for K >= 2; for one draw the SD is null (that helper would divide by
zero).  A non-finite value anywhere (float64 overflow), including the
half-sample means and floor summaries, is refused with
:class:`ColaTabulationError`, so every number in a result is
JSON-finite.  The noise floor follows
``runs/replication_mermin_rows_v1.json`` ``conventions.floor`` as computed
by ``scripts/replication_mermin_rows.py``, with the split unit of A1
section 16: for each of five seeds (0-4),
:func:`populace_dynamics.harness.panel.split_panel_by_person` with
``fraction=0.5`` splits the opening-wave family units (``family_unit_id``)
into two disjoint halves, so each family unit's persons fall on one side;
the reported estimator is recomputed on each half; the floor is the
summary (mean, sd with ``ddof=1``, min, max, n_seeds, values) of
``|side_a - side_b|`` over the seeds where both halves are defined.
Floors are at half sample and are not rescaled.  Two documented
deviations from the ``_summary`` helper those scripts import (A1 section
16): with fewer than two usable seeds the floor's summary fields are null
instead of a zero summary (no seed) or a zero SD (one seed), so an
undefined floor cannot read as a zero floor; and the Mermin-row split was
by person, not family unit.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.harness.panel import split_panel_by_person

__all__ = [
    "AGE_RULE_DEFINITIONS",
    "BASELINE_RECIPIENTS",
    "BENEFIT_PERIOD_DEFINITIONS",
    "COMMON_RECIPIENTS",
    "COMPONENT_VOCABULARY",
    "DEFAULT_AGE_GROUPS",
    "DEFAULT_DRAW_INDICES",
    "DEFAULT_FLOOR_SEEDS",
    "FAMILY_UNIT",
    "FLAGGED_RECIPIENT_INCLUDING_ZERO",
    "FLOOR_FRACTION",
    "FLOOR_SPLIT_UNITS",
    "INVENTED",
    "MEAN_OF_INDIVIDUAL_RATIOS",
    "MEMBERSHIP_BASIS_DEFINITIONS",
    "MIN_FLOOR_SEEDS",
    "PENDING_RULINGS",
    "PERSON",
    "POSITIVE_BENEFIT",
    "PRIMARY_COMPONENTS",
    "RATIO_OF_SCENARIO_MEANS",
    "RECIPIENT_RULE_DEFINITIONS",
    "REGISTERED_REAL",
    "REQUIRED_COLUMNS",
    "SCENARIO_SPECIFIC",
    "SCHEMA_VERSION",
    "STATISTICS",
    "WORKERS_ONLY_COMPONENTS",
    "AgeGroup",
    "ColaAgeProfileConfig",
    "ColaTabulationError",
    "MembershipDifferenceError",
    "tabulate_cola_age_profile",
]

SCHEMA_VERSION = "populace_dynamics.cola_age_profile.v1"
STATISTIC_ID = "dynasim_exercise1_cola_minus_1pp_reference_year_age_profile"

REQUIRED_COLUMNS = (
    "draw",
    "person_id",
    "family_unit_id",
    "weight",
    "birth_year",
    "beneficiary_base",
    "beneficiary_reform",
    "benefit_base",
    "benefit_reform",
    "benefit_components",
)

# ---- statistics -----------------------------------------------------------
RATIO_OF_SCENARIO_MEANS = "ratio_of_scenario_means"
MEAN_OF_INDIVIDUAL_RATIOS = "mean_of_individual_ratios"
STATISTICS = (RATIO_OF_SCENARIO_MEANS, MEAN_OF_INDIVIDUAL_RATIOS)
STATISTIC_DEFINITIONS = {
    RATIO_OF_SCENARIO_MEANS: (
        "100 * (mu_reform / mu_base - 1), mu_s = sum_{i in S_s} w_i B_s,i "
        "/ sum_{i in S_s} w_i (weighted ratio of scenario means)"
    ),
    MEAN_OF_INDIVIDUAL_RATIOS: (
        "100 * (sum_{i in S_alt} w_i (B_reform,i / B_base,i) / "
        "sum_{i in S_alt} w_i - 1) (weighted mean of individual ratios)"
    ),
}

# ---- membership -----------------------------------------------------------
POSITIVE_BENEFIT = "positive_benefit"
FLAGGED_RECIPIENT_INCLUDING_ZERO = "flagged_recipient_including_zero"
RECIPIENT_RULE_DEFINITIONS = {
    POSITIVE_BENEFIT: (
        "recipient in scenario s iff beneficiary_s is true and the "
        "selected-component benefit B_s is > 0"
    ),
    FLAGGED_RECIPIENT_INCLUDING_ZERO: (
        "recipient in scenario s iff beneficiary_s is true and the row "
        "carries at least one selected component; a zero selected benefit "
        "is kept and enters the scenario mean as zero"
    ),
}

SCENARIO_SPECIFIC = "scenario_specific"
BASELINE_RECIPIENTS = "baseline_recipients"
COMMON_RECIPIENTS = "common_recipients"
MEMBERSHIP_BASIS_DEFINITIONS = {
    SCENARIO_SPECIFIC: (
        "S_base = baseline recipients; S_reform = reform recipients; "
        "S_alt = recipients in both scenarios with B_base > 0"
    ),
    BASELINE_RECIPIENTS: (
        "S_base = S_reform = baseline recipients; S_alt = baseline "
        "recipients with B_base > 0"
    ),
    COMMON_RECIPIENTS: (
        "S_base = S_reform = recipients in both scenarios; S_alt = the "
        "same set with B_base > 0"
    ),
}

# ---- age ------------------------------------------------------------------
AGE_RULE_OFFSETS = {
    "reference_year_minus_birth_year": 0,
    "reference_year_minus_birth_year_minus_one": -1,
}
AGE_RULE_DEFINITIONS = {
    "reference_year_minus_birth_year": "age = reference_year - birth_year",
    "reference_year_minus_birth_year_minus_one": (
        "age = reference_year - birth_year - 1 (completed age at the start "
        "of the reference year)"
    ),
}

# ---- benefit period (declared, not observable from the rows) --------------
BENEFIT_PERIOD_DEFINITIONS = {
    "calendar_year_payments": (
        "benefit amounts are payments during the reference calendar year "
        "(annual model)"
    ),
    "december_monthly_amount": (
        "benefit amounts are the December reference-year monthly amount"
    ),
}

# ---- components -----------------------------------------------------------
COMPONENT_VOCABULARY = (
    "retired_worker",
    "disabled_worker",
    "spouse",
    "aged_widow",
    "disabled_widow",
)
PRIMARY_COMPONENTS = COMPONENT_VOCABULARY
WORKERS_ONLY_COMPONENTS = ("retired_worker", "disabled_worker")
COMPONENT_SUM_REL_TOL = 1e-9
COMPONENT_SUM_ABS_TOL = 1e-6

# ---- provenance interlock -------------------------------------------------
INVENTED = "invented"
REGISTERED_REAL = "registered_real"
DATA_PROVENANCES = (INVENTED, REGISTERED_REAL)
INVENTED_DATA_LABEL = (
    "INVENTED DATA: development or test input, not a model result"
)

# ---- draws and floors -----------------------------------------------------
DEFAULT_REFERENCE_YEAR = 2030
#: K = 20 registered draws (the ``estimates.ledgers.DRAW_INDICES`` value).
DEFAULT_DRAW_INDICES = tuple(range(20))
#: The five floor seeds of ``scripts/replication_r7_sharing.SEEDS``.
DEFAULT_FLOOR_SEEDS = (0, 1, 2, 3, 4)
FLOOR_FRACTION = 0.5
#: A1 section 16: with fewer usable seeds the floor is undefined.
MIN_FLOOR_SEEDS = 2
#: Half-split units: A1 section 16's opening-wave family unit, or the
#: person (the Mermin-row precedent; not registered).
FAMILY_UNIT = "family_unit_id"
PERSON = "person_id"
FLOOR_SPLIT_UNITS = (FAMILY_UNIT, PERSON)
FLOOR_SPLIT_UNIT_DEFINITIONS = {
    FAMILY_UNIT: (
        "the opening-wave family unit (family_unit_id): every member of a "
        "family unit falls on one side (A1 section 16)"
    ),
    PERSON: (
        "the person (person_id): the Mermin-row precedent, not registered "
        "for exercise 1"
    ),
}

_UNDEFINED_REASONS = {
    "empty_baseline_membership": (
        "no baseline members, or zero total baseline weight"
    ),
    "empty_reform_membership": (
        "no reform members, or zero total reform weight"
    ),
    "nonpositive_baseline_mean": "weighted baseline mean is <= 0",
    "empty_alternative_membership": (
        "no members in S_alt, or zero total S_alt weight"
    ),
}


class ColaTabulationError(ValueError):
    """The rows or configuration cannot yield the frozen statistic."""


class MembershipDifferenceError(ColaTabulationError):
    """Scenario memberships differ and the configuration forbids it."""


# =========================================================================
# Scalar validation
# =========================================================================
def _is_bool(value: Any) -> bool:
    return isinstance(value, bool | np.bool_)


def _int_value(value: Any, label: str) -> int:
    if _is_bool(value) or not isinstance(value, Integral):
        raise ColaTabulationError(f"{label} must be an integer")
    return int(value)


def _real_value(value: Any, label: str) -> float:
    if _is_bool(value) or not isinstance(value, Real):
        raise ColaTabulationError(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ColaTabulationError(f"{label} must be finite")
    return number


def _nonnegative(value: Any, label: str) -> float:
    number = _real_value(value, label)
    if number < 0.0:
        raise ColaTabulationError(f"{label} must be non-negative")
    return number


def _bool_value(value: Any, label: str) -> bool:
    if not _is_bool(value):
        raise ColaTabulationError(f"{label} must be a bool")
    return bool(value)


def _choice(value: Any, allowed: Iterable[str], label: str) -> None:
    allowed = tuple(allowed)
    if value not in allowed:
        raise ColaTabulationError(
            f"{label} must be one of {list(allowed)}; got {value!r}"
        )


def _canonical_indices(values: Any, label: str) -> tuple[int, ...]:
    items = tuple(values)
    if not items:
        raise ColaTabulationError(f"{label} must not be empty")
    ints = [_int_value(v, label) for v in items]
    if any(v < 0 for v in ints):
        raise ColaTabulationError(f"{label} must be non-negative")
    if len(set(ints)) != len(ints):
        raise ColaTabulationError(f"{label} must be unique")
    return tuple(sorted(ints))


@dataclass(frozen=True)
class AgeGroup:
    """An inclusive reporting-age band; ``upper=None`` is open-ended."""

    label: str
    lower: int
    upper: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ColaTabulationError("age-group label must be a string")
        _int_value(self.lower, f"age group {self.label} lower bound")
        if self.upper is not None:
            _int_value(self.upper, f"age group {self.label} upper bound")
            if self.upper < self.lower:
                raise ColaTabulationError(
                    f"age group {self.label} has upper < lower"
                )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "lower": int(self.lower),
            "upper": None if self.upper is None else int(self.upper),
        }


DEFAULT_AGE_GROUPS = (
    AgeGroup("50-61", 50, 61),
    AgeGroup("62-64", 62, 64),
    AgeGroup("65-69", 65, 69),
    AgeGroup("70-79", 70, 79),
    AgeGroup("80+", 80, None),
)


@dataclass(frozen=True)
class ColaAgeProfileConfig:
    """Every tabulation convention, with the plan's proposed primaries.

    ``reference_year`` and ``age_groups`` are the exercise's target
    definition.  The other fields are listed in :data:`PENDING_RULINGS`.
    ``components``, ``draw_indices`` and ``floor_seeds`` are stored in
    canonical order.
    """

    reference_year: int = DEFAULT_REFERENCE_YEAR
    age_rule: str = "reference_year_minus_birth_year"
    age_groups: tuple[AgeGroup, ...] = DEFAULT_AGE_GROUPS
    recipient_rule: str = POSITIVE_BENEFIT
    allow_membership_difference: bool = False
    membership_basis: str = SCENARIO_SPECIFIC
    components: tuple[str, ...] = PRIMARY_COMPONENTS
    benefit_period: str = "calendar_year_payments"
    headline_statistic: str = RATIO_OF_SCENARIO_MEANS
    draw_indices: tuple[int, ...] = DEFAULT_DRAW_INDICES
    floor_seeds: tuple[int, ...] = DEFAULT_FLOOR_SEEDS
    floor_split_unit: str = FAMILY_UNIT

    def __post_init__(self) -> None:
        _int_value(self.reference_year, "reference_year")
        _choice(self.age_rule, AGE_RULE_OFFSETS, "age_rule")
        _choice(
            self.recipient_rule, RECIPIENT_RULE_DEFINITIONS, "recipient_rule"
        )
        _choice(
            self.membership_basis,
            MEMBERSHIP_BASIS_DEFINITIONS,
            "membership_basis",
        )
        _choice(
            self.benefit_period, BENEFIT_PERIOD_DEFINITIONS, "benefit_period"
        )
        _choice(self.headline_statistic, STATISTICS, "headline_statistic")
        _choice(self.floor_split_unit, FLOOR_SPLIT_UNITS, "floor_split_unit")
        if not isinstance(self.allow_membership_difference, bool):
            raise ColaTabulationError(
                "allow_membership_difference must be a bool"
            )
        self._validate_age_groups()
        object.__setattr__(self, "components", self._canonical_components())
        object.__setattr__(
            self,
            "draw_indices",
            _canonical_indices(self.draw_indices, "draw_indices"),
        )
        object.__setattr__(
            self,
            "floor_seeds",
            _canonical_indices(self.floor_seeds, "floor_seeds"),
        )

    def _validate_age_groups(self) -> None:
        groups = tuple(self.age_groups)
        if not groups or not all(isinstance(g, AgeGroup) for g in groups):
            raise ColaTabulationError(
                "age_groups must be a non-empty tuple of AgeGroup"
            )
        labels = [g.label for g in groups]
        if len(set(labels)) != len(labels):
            raise ColaTabulationError("age-group labels must be unique")
        for earlier, later in zip(groups, groups[1:], strict=False):
            if earlier.upper is None:
                raise ColaTabulationError(
                    "only the last age group may be open-ended"
                )
            if later.lower <= earlier.upper:
                raise ColaTabulationError(
                    "age groups must be ascending and non-overlapping"
                )
        object.__setattr__(self, "age_groups", groups)

    def _canonical_components(self) -> tuple[str, ...]:
        chosen = tuple(self.components)
        if not chosen:
            raise ColaTabulationError("components must not be empty")
        if len(set(chosen)) != len(chosen):
            raise ColaTabulationError("components must be unique")
        unknown = [c for c in chosen if c not in COMPONENT_VOCABULARY]
        if unknown:
            raise ColaTabulationError(
                f"unknown components {unknown}; vocabulary "
                f"{list(COMPONENT_VOCABULARY)}"
            )
        return tuple(c for c in COMPONENT_VOCABULARY if c in chosen)

    @property
    def age_offset(self) -> int:
        return AGE_RULE_OFFSETS[self.age_rule]

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_year": int(self.reference_year),
            "age_rule": self.age_rule,
            "age_groups": [g.as_dict() for g in self.age_groups],
            "recipient_rule": self.recipient_rule,
            "allow_membership_difference": self.allow_membership_difference,
            "membership_basis": self.membership_basis,
            "components": list(self.components),
            "benefit_period": self.benefit_period,
            "headline_statistic": self.headline_statistic,
            "draw_indices": list(self.draw_indices),
            "floor_seeds": list(self.floor_seeds),
            "floor_split_unit": self.floor_split_unit,
        }


_SPEC_RATIFICATION = (
    "A1 specification ratification (critical-path-cola-20260922.md "
    "section 6 item 4)"
)

#: The conventions awaiting A1 ratification (Max's rulings of 2026-09-23
#: covered none of them), with the plan's proposed primary (the
#: configuration default) and its registered alternatives.
PENDING_RULINGS: tuple[dict[str, Any], ...] = (
    {
        "parameter": "headline_statistic",
        "plan_field": "Statistic",
        "proposed_primary": RATIO_OF_SCENARIO_MEANS,
        "registered_alternatives": [MEAN_OF_INDIVIDUAL_RATIOS],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "both statistics are always computed; this sets which one is "
            "labelled primary"
        ),
    },
    {
        "parameter": "recipient_rule",
        "plan_field": "Membership",
        "proposed_primary": POSITIVE_BENEFIT,
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "zero-benefit treatment is an unresolved specification field; "
            f"{FLAGGED_RECIPIENT_INCLUDING_ZERO} is available, not "
            "registered"
        ),
    },
    {
        "parameter": "allow_membership_difference",
        "plan_field": "Membership",
        "proposed_primary": False,
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "the proposal requires identical membership in both scenarios "
            "under fixed paths; differing memberships are refused"
        ),
    },
    {
        "parameter": "membership_basis",
        "plan_field": "Membership",
        "proposed_primary": SCENARIO_SPECIFIC,
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "operative only when allow_membership_difference is true and "
            "memberships differ; under identical membership every basis "
            "gives the same sets"
        ),
    },
    {
        "parameter": "age_rule",
        "plan_field": "Age",
        "proposed_primary": "reference_year_minus_birth_year",
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": "within-year age assignment is unresolved in the spec",
    },
    {
        "parameter": "benefit_period",
        "plan_field": "Benefit period",
        "proposed_primary": "calendar_year_payments",
        "registered_alternatives": ["december_monthly_amount"],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "declared label only: the input amounts must already measure "
            "the declared period; the tabulation cannot check it"
        ),
    },
    {
        "parameter": "components",
        "plan_field": "Components",
        "proposed_primary": list(PRIMARY_COMPONENTS),
        "registered_alternatives": [list(WORKERS_ONLY_COMPONENTS)],
        "awaiting": (
            f"{_SPEC_RATIFICATION}; section 6 item 2(b) was ruled by Max "
            "on 2026-09-23 (DI benefit levels enter as a disclosed oracle "
            "approximation)"
        ),
        "note": "component vocabulary is closed; unknown names are refused",
    },
    {
        "parameter": "draw_indices",
        "plan_field": "Uncertainty",
        "proposed_primary": list(DEFAULT_DRAW_INDICES),
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": "K = 20 draws, mean and sample SD over draws",
    },
    {
        "parameter": "floor_seeds",
        "plan_field": "Uncertainty",
        "proposed_primary": list(DEFAULT_FLOOR_SEEDS),
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": "five-seed family-unit-disjoint half-split floor",
    },
    {
        "parameter": "floor_split_unit",
        "plan_field": "Uncertainty",
        "proposed_primary": FAMILY_UNIT,
        "registered_alternatives": [],
        "awaiting": _SPEC_RATIFICATION,
        "note": (
            "A1 section 16 keeps each opening-wave family unit on one side "
            "(A1 referee question 2); person_id, the Mermin-row "
            "precedent, is available and not registered"
        ),
    },
)


# =========================================================================
# Row normalization
# =========================================================================
@dataclass(frozen=True, eq=False)
class _Rows:
    draw: np.ndarray
    person_id: np.ndarray
    family_unit_id: np.ndarray
    weight: np.ndarray
    birth_year: np.ndarray
    age: np.ndarray
    group: np.ndarray
    selected_base: np.ndarray
    selected_reform: np.ndarray
    recipient_base: np.ndarray
    recipient_reform: np.ndarray
    flagged_zero_base: int
    flagged_zero_reform: int
    n_persons_weight_varies: int
    extra_columns: tuple[str, ...]

    @property
    def n(self) -> int:
        return int(self.draw.size)


def _records(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    if isinstance(rows, pd.DataFrame):
        if not rows.columns.is_unique:
            # DataFrame.to_dict("records") keeps only the last of repeated
            # column names (with a warning), which would silently drop data.
            repeated = sorted(
                {str(c) for c in rows.columns[rows.columns.duplicated()]}
            )
            raise ColaTabulationError(
                f"rows have repeated column names {repeated}"
            )
        missing = [c for c in REQUIRED_COLUMNS if c not in rows.columns]
        if missing:
            raise ColaTabulationError(f"rows lack columns {missing}")
        extras = tuple(
            sorted(str(c) for c in rows.columns if c not in REQUIRED_COLUMNS)
        )
        return rows.to_dict("records"), extras
    if isinstance(rows, Mapping | str | bytes):
        raise ColaTabulationError(
            "rows must be a DataFrame or an iterable of row mappings"
        )
    records = list(rows)
    extras: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ColaTabulationError(f"row {index} is not a mapping")
        missing = [c for c in REQUIRED_COLUMNS if c not in record]
        if missing:
            raise ColaTabulationError(f"row {index} lacks {missing}")
        extras.update(str(k) for k in record if k not in REQUIRED_COLUMNS)
    return records, tuple(sorted(extras))


def _key(value: Any, index: int, column: str) -> int | str:
    # Normalize to the builtin type (numpy.str_ -> str, numpy integer ->
    # int) so the one-type check compares key types, not container types.
    if isinstance(value, str) and value:
        return str(value)
    if not _is_bool(value) and isinstance(value, Integral):
        return int(value)
    raise ColaTabulationError(
        f"row {index}: {column} must be an integer or a non-empty string"
    )


def _person_key(value: Any, index: int) -> int | str:
    return _key(value, index, "person_id")


def _parse_components(
    value: Any, index: int
) -> dict[str, tuple[float, float]]:
    if not isinstance(value, Mapping):
        raise ColaTabulationError(
            f"row {index}: benefit_components must map component name to "
            "{'base': amount, 'reform': amount}"
        )
    parsed: dict[str, tuple[float, float]] = {}
    for name, amounts in value.items():
        if name not in COMPONENT_VOCABULARY:
            raise ColaTabulationError(
                f"row {index}: unknown benefit component {name!r}; "
                f"vocabulary {list(COMPONENT_VOCABULARY)}"
            )
        if not isinstance(amounts, Mapping) or set(amounts) != {
            "base",
            "reform",
        }:
            raise ColaTabulationError(
                f"row {index}: component {name} must be "
                "{'base': amount, 'reform': amount}"
            )
        parsed[name] = (
            _nonnegative(amounts["base"], f"row {index} {name} base"),
            _nonnegative(amounts["reform"], f"row {index} {name} reform"),
        )
    return parsed


def _check_component_sum(
    parsed: dict[str, tuple[float, float]],
    total: float,
    position: int,
    scenario: str,
    index: int,
) -> None:
    component_sum = math.fsum(amounts[position] for amounts in parsed.values())
    if not math.isclose(
        component_sum,
        total,
        rel_tol=COMPONENT_SUM_REL_TOL,
        abs_tol=COMPONENT_SUM_ABS_TOL,
    ):
        raise ColaTabulationError(
            f"row {index}: {scenario} components sum to {component_sum!r} "
            f"but benefit_{scenario} is {total!r}"
        )


def _group_index(age: int, groups: Sequence[AgeGroup]) -> int:
    for position, group in enumerate(groups):
        if age >= group.lower and (group.upper is None or age <= group.upper):
            return position
    return -1


def _normalize(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
    config: ColaAgeProfileConfig,
) -> _Rows:
    records, extras = _records(rows)
    if not records:
        raise ColaTabulationError("rows must not be empty")
    n = len(records)
    draw = np.empty(n, dtype=np.int64)
    weight = np.empty(n, dtype=np.float64)
    birth_year = np.empty(n, dtype=np.int64)
    selected = np.empty((n, 2), dtype=np.float64)
    recipient = np.empty((n, 2), dtype=bool)
    person_ids: list[int | str] = []
    family_ids: list[int | str] = []
    seen: set[tuple[int, int | str]] = set()
    person_birth_year: dict[int | str, int] = {}
    person_family: dict[int | str, int | str] = {}
    person_weights: dict[int | str, set[float]] = {}
    flagged_zero = [0, 0]
    chosen = config.components

    for index, record in enumerate(records):
        draw[index] = _int_value(record["draw"], f"row {index} draw")
        person = _person_key(record["person_id"], index)
        key = (int(draw[index]), person)
        if key in seen:
            raise ColaTabulationError(
                f"duplicate (draw, person_id) {key!r} at row {index}"
            )
        seen.add(key)
        person_ids.append(person)
        family = _key(record["family_unit_id"], index, "family_unit_id")
        family_ids.append(family)
        # The family-unit split keeps a person on one side only if the
        # person's family unit is the same in every draw.
        known_family = person_family.setdefault(person, family)
        if known_family != family:
            raise ColaTabulationError(
                f"row {index}: person_id {person!r} has family_unit_id "
                f"{family!r} but {known_family!r} in another draw; a "
                "person's opening-wave family unit must be the same in "
                "every draw"
            )
        weight[index] = _nonnegative(record["weight"], f"row {index} weight")
        person_weights.setdefault(person, set()).add(float(weight[index]))
        birth_year[index] = _int_value(
            record["birth_year"], f"row {index} birth_year"
        )
        # A person's birth year fixes their age group in every draw, and the
        # half-split floor treats a person_id as one person across draws, so
        # a person_id whose birth year differs between draws is refused.
        known = person_birth_year.setdefault(person, int(birth_year[index]))
        if known != int(birth_year[index]):
            raise ColaTabulationError(
                f"row {index}: person_id {person!r} has birth_year "
                f"{int(birth_year[index])} but {known} in another draw; a "
                "person's birth year must be the same in every draw"
            )
        parsed = _parse_components(record["benefit_components"], index)
        has_selected = any(name in parsed for name in chosen)
        for position, scenario in enumerate(("base", "reform")):
            flag = _bool_value(
                record[f"beneficiary_{scenario}"],
                f"row {index} beneficiary_{scenario}",
            )
            total = _nonnegative(
                record[f"benefit_{scenario}"],
                f"row {index} benefit_{scenario}",
            )
            _check_component_sum(parsed, total, position, scenario, index)
            if not flag and total > 0.0:
                raise ColaTabulationError(
                    f"row {index}: beneficiary_{scenario} is false but "
                    f"benefit_{scenario} is positive"
                )
            amount = math.fsum(
                parsed[name][position] for name in chosen if name in parsed
            )
            selected[index, position] = amount
            if config.recipient_rule == POSITIVE_BENEFIT:
                is_recipient = flag and amount > 0.0
            else:
                is_recipient = flag and has_selected
            recipient[index, position] = is_recipient
            if flag and amount == 0.0:
                flagged_zero[position] += 1

    for column, keys in (
        ("person_id", person_ids),
        ("family_unit_id", family_ids),
    ):
        if len({type(value) for value in keys}) > 1:
            raise ColaTabulationError(
                f"{column} values must all be integers or all be strings"
            )
    present = set(int(d) for d in np.unique(draw))
    expected = set(config.draw_indices)
    if present != expected:
        raise ColaTabulationError(
            f"draws present {sorted(present)} differ from the configured "
            f"draw_indices {sorted(expected)}"
        )
    age = config.reference_year - birth_year + config.age_offset
    group = np.array(
        [_group_index(int(a), config.age_groups) for a in age],
        dtype=np.int64,
    )
    person_array = np.empty(n, dtype=object)
    person_array[:] = person_ids
    family_array = np.empty(n, dtype=object)
    family_array[:] = family_ids
    return _Rows(
        draw=draw,
        person_id=person_array,
        family_unit_id=family_array,
        weight=weight,
        birth_year=birth_year,
        age=age,
        group=group,
        selected_base=selected[:, 0].copy(),
        selected_reform=selected[:, 1].copy(),
        recipient_base=recipient[:, 0].copy(),
        recipient_reform=recipient[:, 1].copy(),
        flagged_zero_base=flagged_zero[0],
        flagged_zero_reform=flagged_zero[1],
        n_persons_weight_varies=sum(
            1 for values in person_weights.values() if len(values) > 1
        ),
        extra_columns=extras,
    )


# =========================================================================
# Cell arithmetic
# =========================================================================
def _membership_masks(
    rows: _Rows, basis: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base = rows.recipient_base
    reform = rows.recipient_reform
    if basis == SCENARIO_SPECIFIC:
        s_base, s_reform, s_both = base, reform, base & reform
    elif basis == BASELINE_RECIPIENTS:
        s_base = s_reform = s_both = base
    else:
        s_base = s_reform = s_both = base & reform
    s_alt = s_both & (rows.selected_base > 0.0)
    return s_base, s_reform, s_alt


def _finite(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ColaTabulationError(
            f"{label} is not finite (float64 overflow); rescale the weights "
            "or benefits"
        )
    return value


def _fsum(values: np.ndarray) -> float:
    try:
        total = math.fsum(values.tolist())
    except OverflowError as error:
        raise ColaTabulationError(
            "a weighted sum overflows float64; rescale the weights or "
            "benefits"
        ) from error
    return _finite(total, "a weighted sum")


def _cell(
    rows: _Rows,
    in_cell: np.ndarray,
    masks: tuple[np.ndarray, np.ndarray, np.ndarray],
    draw: int,
) -> dict[str, Any]:
    # Products that overflow become inf and are refused by _fsum/_finite,
    # so a result can never carry a non-finite (non-JSON) number.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return _cell_values(rows, in_cell, masks, draw)


def _cell_values(
    rows: _Rows,
    in_cell: np.ndarray,
    masks: tuple[np.ndarray, np.ndarray, np.ndarray],
    draw: int,
) -> dict[str, Any]:
    s_base, s_reform, s_alt = (in_cell & mask for mask in masks)
    w = rows.weight
    weight_base = _fsum(w[s_base])
    weight_reform = _fsum(w[s_reform])
    weight_alt = _fsum(w[s_alt])
    reasons: dict[str, str] = {}
    mean_base = mean_reform = None
    if weight_base > 0.0:
        mean_base = _finite(
            _fsum(w[s_base] * rows.selected_base[s_base]) / weight_base,
            "the weighted baseline mean",
        )
    if weight_reform > 0.0:
        mean_reform = _finite(
            _fsum(w[s_reform] * rows.selected_reform[s_reform])
            / weight_reform,
            "the weighted reform mean",
        )
    primary = None
    if mean_base is None:
        reasons[RATIO_OF_SCENARIO_MEANS] = "empty_baseline_membership"
    elif mean_reform is None:
        reasons[RATIO_OF_SCENARIO_MEANS] = "empty_reform_membership"
    elif mean_base <= 0.0:
        reasons[RATIO_OF_SCENARIO_MEANS] = "nonpositive_baseline_mean"
    else:
        primary = _finite(
            100.0 * (mean_reform / mean_base - 1.0), RATIO_OF_SCENARIO_MEANS
        )
    alternative = None
    if weight_alt > 0.0:
        ratios = rows.selected_reform[s_alt] / rows.selected_base[s_alt]
        alternative = _finite(
            100.0 * (_fsum(w[s_alt] * ratios) / weight_alt - 1.0),
            MEAN_OF_INDIVIDUAL_RATIOS,
        )
    else:
        reasons[MEAN_OF_INDIVIDUAL_RATIOS] = "empty_alternative_membership"
    return {
        "draw": int(draw),
        RATIO_OF_SCENARIO_MEANS: primary,
        MEAN_OF_INDIVIDUAL_RATIOS: alternative,
        "undefined_reasons": reasons,
        "n_base": int(np.count_nonzero(s_base)),
        "n_reform": int(np.count_nonzero(s_reform)),
        "n_alternative": int(np.count_nonzero(s_alt)),
        "weight_base": weight_base,
        "weight_reform": weight_reform,
        "weight_alternative": weight_alt,
        "mean_benefit_base": mean_base,
        "mean_benefit_reform": mean_reform,
    }


def _profile(
    rows: _Rows,
    config: ColaAgeProfileConfig,
    subset: np.ndarray,
) -> list[list[dict[str, Any]]]:
    """Per age group (config order), the per-draw cells on ``subset``."""
    masks = _membership_masks(rows, config.membership_basis)
    by_draw = {d: subset & (rows.draw == d) for d in config.draw_indices}
    profile = []
    for position in range(len(config.age_groups)):
        in_group = rows.group == position
        profile.append(
            [
                _cell(rows, by_draw[d] & in_group, masks, d)
                for d in config.draw_indices
            ]
        )
    return profile


def _draw_summary(
    cells: list[dict[str, Any]], statistic: str
) -> dict[str, Any]:
    """Mean and sample SD over draws; undefined unless every draw is.

    A1 section 7: if any draw's cell is undefined, the mean and SD are
    reported as undefined together with the number of defined draws and
    each undefined draw's reason.
    """

    values = [cell[statistic] for cell in cells]
    undefined = [
        {"draw": cell["draw"], "reason": cell["undefined_reasons"][statistic]}
        for cell in cells
        if cell[statistic] is None
    ]
    if undefined:
        return {
            "defined": False,
            "per_draw": [None if v is None else float(v) for v in values],
            "mean": None,
            "sample_sd": None,
            "n_draws": len(values),
            "n_defined_draws": len(values) - len(undefined),
            "undefined_draws": undefined,
        }
    return {
        "defined": True,
        **_defined_draw_summary(values),
        "n_defined_draws": len(values),
        "undefined_draws": [],
    }


def _defined_draw_summary(values: list[float]) -> dict[str, Any]:
    k = len(values)
    try:
        mean = _finite(math.fsum(values) / k, "the mean over draws")
        sample_sd = (
            _finite(
                math.sqrt(
                    math.fsum((v - mean) ** 2 for v in values) / (k - 1)
                ),
                "the sample SD over draws",
            )
            if k > 1
            else None
        )
    except OverflowError as error:
        raise ColaTabulationError(
            "the draw summary overflows float64"
        ) from error
    return {
        "per_draw": [float(v) for v in values],
        "mean": mean,
        "sample_sd": sample_sd,
        "n_draws": k,
    }


def _floor_summary(values: list[float]) -> dict[str, Any]:
    """The floor over usable seeds; undefined with fewer than two.

    A1 section 16: "With fewer than two usable seeds the floor is
    undefined, never zero."  The per-seed gaps are still listed.
    """

    gaps = [_finite(float(v), "a floor gap") for v in values]
    if len(gaps) < MIN_FLOOR_SEEDS:
        return {
            "defined": False,
            "undefined_reason": (
                "no usable seed"
                if not gaps
                else f"fewer than {MIN_FLOOR_SEEDS} usable seeds"
            ),
            "mean": None,
            "sd": None,
            "min": None,
            "max": None,
            "n_seeds": len(gaps),
            "values": gaps,
        }
    arr = np.array(gaps, dtype=np.float64)
    # The numpy mean/std of the committed-floor convention; an overflow
    # (inf or nan) is refused, never reported.
    with np.errstate(over="ignore", invalid="ignore"):
        mean = float(arr.mean())
        sd = float(arr.std(ddof=1))
    return {
        "defined": True,
        "undefined_reason": None,
        "mean": _finite(mean, "the floor mean"),
        "sd": _finite(sd, "the floor sd"),
        "min": _finite(float(arr.min()), "the floor min"),
        "max": _finite(float(arr.max()), "the floor max"),
        "n_seeds": int(arr.size),
        "values": gaps,
    }


def _side_mean(values: list[float]) -> float:
    try:
        total = math.fsum(values)
    except OverflowError as error:
        raise ColaTabulationError(
            "a half-sample mean over draws overflows float64; rescale the "
            "weights or benefits"
        ) from error
    return _finite(total / len(values), "a half-sample mean over draws")


def _side_values(
    rows: _Rows, config: ColaAgeProfileConfig, subset: np.ndarray
) -> dict[str, Any]:
    profile = _profile(rows, config, subset)
    groups: dict[str, dict[str, Any]] = {}
    for group, cells in zip(config.age_groups, profile, strict=True):
        entry: dict[str, Any] = {}
        for statistic in STATISTICS:
            values = [cell[statistic] for cell in cells]
            if any(v is None for v in values):
                entry[statistic] = None
                entry[f"{statistic}_undefined_draws"] = [
                    cell["draw"] for cell in cells if cell[statistic] is None
                ]
            else:
                entry[statistic] = _side_mean(values)
        groups[group.label] = entry
    return {
        "n_persons": int(len(set(rows.person_id[subset].tolist()))),
        "n_family_units": int(len(set(rows.family_unit_id[subset].tolist()))),
        "n_rows": int(np.count_nonzero(subset)),
        "groups": groups,
    }


def _floors(
    rows: _Rows, config: ColaAgeProfileConfig
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    unit = config.floor_split_unit
    unit_values = (
        rows.family_unit_id if unit == FAMILY_UNIT else rows.person_id
    )
    unit_frame = pd.DataFrame({unit: unit_values.tolist()})
    per_seed = []
    for seed in config.floor_seeds:
        side_a_frame, _side_b_frame = split_panel_by_person(
            unit_frame, unit, fraction=FLOOR_FRACTION, seed=seed
        )
        in_a = np.zeros(rows.n, dtype=bool)
        in_a[side_a_frame.index.to_numpy()] = True
        per_seed.append(
            {
                "seed": int(seed),
                "split_unit": unit,
                "side_a": _side_values(rows, config, in_a),
                "side_b": _side_values(rows, config, ~in_a),
            }
        )
    floors: dict[str, dict[str, Any]] = {}
    for group in config.age_groups:
        entry: dict[str, Any] = {}
        for statistic in STATISTICS:
            gaps = []
            dropped = []
            for row in per_seed:
                a = row["side_a"]["groups"][group.label][statistic]
                b = row["side_b"]["groups"][group.label][statistic]
                if a is None or b is None:
                    dropped.append(row["seed"])
                else:
                    gaps.append(abs(a - b))
            entry[statistic] = {
                **_floor_summary(gaps),
                "dropped_seeds": dropped,
            }
        floors[group.label] = entry
    return per_seed, floors


# =========================================================================
# Public entry point
# =========================================================================
def _validate_provenance(
    data_provenance: Any,
    registration_pointer: Any,
    labels: Sequence[str],
) -> None:
    _choice(data_provenance, DATA_PROVENANCES, "data_provenance")
    if registration_pointer is not None and (
        not isinstance(registration_pointer, str)
        or not registration_pointer.strip()
    ):
        raise ColaTabulationError(
            "registration_pointer must be a non-empty string or None"
        )
    if data_provenance == REGISTERED_REAL:
        if registration_pointer is None:
            raise ColaTabulationError(
                "real-data tabulation requires the registration pointer "
                "(the issue #42 comment) to exist before the run"
            )
        if not labels:
            raise ColaTabulationError(
                "real-data tabulation requires the output labels"
            )
        # Labels copied from an invented dry run would mark a real result
        # as invented data; the two provenances cannot share that label.
        if INVENTED_DATA_LABEL in labels:
            raise ColaTabulationError(
                "a registered_real result cannot carry the invented-data "
                "label"
            )


def _json_scalar_mapping(
    value: Mapping[str, Any] | None, label: str
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ColaTabulationError(f"{label} must be a mapping")
    out: dict[str, Any] = {}
    for key in sorted(value):
        if not isinstance(key, str):
            raise ColaTabulationError(f"{label} keys must be strings")
        item = value[key]
        if item is None or isinstance(item, str | bool | int):
            out[key] = item
        elif isinstance(item, float) and math.isfinite(item):
            out[key] = item
        else:
            raise ColaTabulationError(
                f"{label}[{key!r}] must be a JSON scalar"
            )
    return out


def _conventions(config: ColaAgeProfileConfig) -> dict[str, Any]:
    alternative = next(s for s in STATISTICS if s != config.headline_statistic)
    return {
        "reference_year": int(config.reference_year),
        "age": {
            "rule": config.age_rule,
            "definition": AGE_RULE_DEFINITIONS[config.age_rule],
            "groups": [g.as_dict() for g in config.age_groups],
            "bounds": "inclusive; upper null means open-ended",
            "outside_groups": (
                "rows whose age falls in no group enter no cell and are "
                "counted in input_summary"
            ),
        },
        "benefit_period": {
            "label": config.benefit_period,
            "definition": BENEFIT_PERIOD_DEFINITIONS[config.benefit_period],
            "enforced_by_tabulation": False,
        },
        "components": {
            "vocabulary": list(COMPONENT_VOCABULARY),
            "selected": list(config.components),
            "selected_benefit": (
                "B_s,i = sum of the scenario-s amounts of the selected "
                "components present in the row"
            ),
            "sum_check": (
                "all components present must sum to benefit_base and "
                "benefit_reform (math.isclose)"
            ),
            "sum_check_rel_tol": COMPONENT_SUM_REL_TOL,
            "sum_check_abs_tol": COMPONENT_SUM_ABS_TOL,
        },
        "membership": {
            "recipient_rule": config.recipient_rule,
            "recipient_rule_definition": RECIPIENT_RULE_DEFINITIONS[
                config.recipient_rule
            ],
            "identical_membership_required": (
                not config.allow_membership_difference
            ),
            "allow_membership_difference": (
                config.allow_membership_difference
            ),
            # Record the identity check only when it was applied, so a
            # result never lists a check that did not run.
            "identity_check_scope": (
                "not applied: allow_membership_difference is true, so rows "
                "that are recipients in only one scenario are tabulated "
                "under membership_basis"
                if config.allow_membership_difference
                else "every input row, including rows outside the age "
                "groups: recipient_base must equal recipient_reform"
            ),
            "membership_basis": config.membership_basis,
            "membership_basis_definition": MEMBERSHIP_BASIS_DEFINITIONS[
                config.membership_basis
            ],
            "flag_consistency": (
                "a row with beneficiary_s false and a positive benefit_s "
                "is refused"
            ),
            "decedents": (
                "not observable here: the supplied reference-period "
                "benefit decides membership"
            ),
        },
        "weights": ("the row weight, shared by both scenarios; finite, >= 0"),
        "statistics": dict(STATISTIC_DEFINITIONS),
        "statistic_roles": {
            "primary": config.headline_statistic,
            "registered_alternative": alternative,
        },
        "unit": (
            "percent change of the reform relative to the baseline "
            "(negative = reduction); percent-of-scheduled = 100 + value"
        ),
        "undefined_cells": {
            "full_sample": (
                "reported, never imputed (A1 section 7): a draw's cell with "
                "no members, zero total weight or a non-positive baseline "
                "mean has a null value and a reason; a group's draw summary "
                "for a statistic is defined only when every draw is, and "
                "otherwise has a null mean and SD with n_defined_draws and "
                "each undefined draw's reason; every other group and "
                "statistic is reported as usual"
            ),
            "reasons": dict(_UNDEFINED_REASONS),
        },
        "draws": {
            "indices": list(config.draw_indices),
            "reported_value": "mean over draws of the per-draw statistic",
            "aggregation": (
                "mean = fsum(values) / K; sample_sd = sqrt(fsum((v - "
                "mean)^2) / (K - 1)) (ddof=1), the "
                "estimates.first_report._numeric_aggregate formula for "
                "K >= 2; sample_sd is null when K = 1"
            ),
            "scenario_pairing": (
                "each row carries both scenarios for one (draw, person); "
                "fixed paths and shared draws are upstream properties, "
                "checked here only through membership identity"
            ),
        },
        "floor": {
            "method": f"{config.floor_split_unit}-disjoint half-split",
            "split_unit": config.floor_split_unit,
            "split_unit_definition": FLOOR_SPLIT_UNIT_DEFINITIONS[
                config.floor_split_unit
            ],
            "splitter": (
                "populace_dynamics.harness.panel.split_panel_by_person("
                f"rows, {config.floor_split_unit!r}, fraction=0.5, "
                "seed=seed) on the per-person-per-draw rows, so every draw "
                "of every person in a split unit falls on one side"
            ),
            "seeds": list(config.floor_seeds),
            "fraction": FLOOR_FRACTION,
            "estimator_per_side": (
                "the reported value recomputed on the side: mean over all "
                "draws of the per-draw statistic; null if any draw's cell "
                "is undefined on that side"
            ),
            "floor": (
                "summary of |side_a - side_b| across the seeds where both "
                "sides are defined: mean, sd (numpy ddof=1), min, max, "
                "n_seeds, values; undefined seeds are listed in "
                f"dropped_seeds; with fewer than {MIN_FLOOR_SEEDS} usable "
                "seeds the floor is undefined (null summary fields, "
                "defined false, undefined_reason), never zero"
            ),
            "source_convention": (
                "runs/replication_mermin_rows_v1.json conventions.floor, "
                "computed by scripts/replication_mermin_rows.py "
                "(seed_half_metrics, build_floors, reform_delta_diagnostic."
                "_summary)"
            ),
            "scale": "half sample; not rescaled to the full sample",
            "deviation": (
                "A1 section 16: fewer than two usable seeds yield null "
                "summary fields, not the zero summary (no seed) or zero SD "
                "(one seed) of reform_delta_diagnostic._summary; and the "
                "split unit is the opening-wave family unit, not the "
                "Mermin-row person"
            ),
        },
        "acceptance_rule": None,
        "acceptance_rule_note": (
            "none applied: the tabulation reports values only; Max ruled "
            "on 2026-09-23 that there is no numerical acceptance threshold "
            "(plan section 6 item 3)"
        ),
    }


def _pending_rulings(config: ColaAgeProfileConfig) -> list[dict[str, Any]]:
    chosen = config.as_dict()
    out = []
    for ruling in PENDING_RULINGS:
        value = chosen[ruling["parameter"]]
        out.append(
            {
                **copy.deepcopy(ruling),
                "chosen": value,
                "is_proposed_primary": value == ruling["proposed_primary"],
            }
        )
    return out


def _input_summary(
    rows: _Rows, config: ColaAgeProfileConfig
) -> dict[str, Any]:
    person_sets = [
        frozenset(rows.person_id[rows.draw == d].tolist())
        for d in config.draw_indices
    ]
    differs = rows.recipient_base != rows.recipient_reform
    in_scope = rows.group >= 0
    return {
        "n_rows": rows.n,
        "n_persons": int(len(set(rows.person_id.tolist()))),
        "n_family_units": int(len(set(rows.family_unit_id.tolist()))),
        "n_rows_per_draw": {
            str(d): int(np.count_nonzero(rows.draw == d))
            for d in config.draw_indices
        },
        "person_sets_identical_across_draws": all(
            s == person_sets[0] for s in person_sets
        ),
        # Reported, not refused: each draw's statistic uses that draw's
        # weights, so a draw-varying weight is well defined, but a fixed
        # person weight is the expected input.
        "n_persons_weight_varies_across_draws": rows.n_persons_weight_varies,
        "extra_columns_ignored": list(rows.extra_columns),
        "n_rows_by_age_group": {
            g.label: int(np.count_nonzero(rows.group == i))
            for i, g in enumerate(config.age_groups)
        },
        "n_rows_outside_age_groups": int(np.count_nonzero(~in_scope)),
        "n_recipient_rows": {
            "base": int(np.count_nonzero(rows.recipient_base)),
            "reform": int(np.count_nonzero(rows.recipient_reform)),
        },
        "n_rows_membership_differs": int(np.count_nonzero(differs)),
        "n_rows_membership_differs_in_age_groups": int(
            np.count_nonzero(differs & in_scope)
        ),
        "memberships_identical": not bool(differs.any()),
        "n_flagged_rows_with_zero_selected_benefit": {
            "base": rows.flagged_zero_base,
            "reform": rows.flagged_zero_reform,
        },
    }


def tabulate_cola_age_profile(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    data_provenance: str,
    config: ColaAgeProfileConfig | None = None,
    registration_pointer: str | None = None,
    labels: Sequence[str] = (),
    upstream_conventions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Tabulate the exercise-1 age profile from per-person-per-draw rows.

    ``data_provenance`` is ``"invented"`` for development and tests.
    ``"registered_real"`` requires a ``registration_pointer`` (the issue #42
    comment that must precede any real-data run) and non-empty ``labels``
    without the invented-data label; the pointer is recorded, not verified.
    ``upstream_conventions`` (JSON scalars, e.g. the first-application or
    exposure-clock row that produced the benefits) is recorded verbatim.

    Returns a JSON-serializable mapping.  Raises
    :class:`MembershipDifferenceError` when scenario memberships differ and
    ``config.allow_membership_difference`` is false.  An undefined cell is
    reported (A1 section 7), never raised: its statistic is null with a
    reason, and ``undefined_cells`` lists every group and statistic whose
    draw summary is undefined.
    """
    config = ColaAgeProfileConfig() if config is None else config
    if not isinstance(config, ColaAgeProfileConfig):
        raise ColaTabulationError("config must be a ColaAgeProfileConfig")
    if isinstance(labels, str):
        raise ColaTabulationError("labels must be a sequence of strings")
    labels = tuple(labels)
    if not all(isinstance(label, str) and label for label in labels):
        raise ColaTabulationError("labels must be non-empty strings")
    _validate_provenance(data_provenance, registration_pointer, labels)
    recorded_upstream = _json_scalar_mapping(
        upstream_conventions, "upstream_conventions"
    )

    rows_ = _normalize(rows, config)
    differs = rows_.recipient_base != rows_.recipient_reform
    if differs.any() and not config.allow_membership_difference:
        first = int(np.flatnonzero(differs)[0])
        raise MembershipDifferenceError(
            f"{int(np.count_nonzero(differs))} rows are recipients in only "
            f"one scenario (first: draw {int(rows_.draw[first])}, person "
            f"{rows_.person_id[first]!r}); set allow_membership_difference "
            "to tabulate them under membership_basis"
        )

    profile = _profile(rows_, config, np.ones(rows_.n, dtype=bool))
    per_seed, floors = _floors(rows_, config)
    groups = []
    undefined_cells = []
    for group, cells in zip(config.age_groups, profile, strict=True):
        entry: dict[str, Any] = dict(group.as_dict())
        for statistic in STATISTICS:
            summary = _draw_summary(cells, statistic)
            entry[statistic] = {
                **summary,
                "floor": floors[group.label][statistic],
            }
            if not summary["defined"]:
                undefined_cells.append(
                    {
                        "group": group.label,
                        "statistic": statistic,
                        "n_defined_draws": summary["n_defined_draws"],
                        "undefined_draws": summary["undefined_draws"],
                    }
                )
        entry["cells"] = cells
        groups.append(entry)

    output_labels = [label for label in labels if label != INVENTED_DATA_LABEL]
    if data_provenance == INVENTED:
        output_labels.insert(0, INVENTED_DATA_LABEL)
    return {
        "schema_version": SCHEMA_VERSION,
        "statistic_id": STATISTIC_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": output_labels,
        "config": config.as_dict(),
        "conventions": _conventions(config),
        "pending_rulings": _pending_rulings(config),
        "upstream_conventions": recorded_upstream,
        "input_summary": _input_summary(rows_, config),
        "groups": groups,
        "undefined_cells": undefined_cells,
        "floor_per_seed": per_seed,
    }
