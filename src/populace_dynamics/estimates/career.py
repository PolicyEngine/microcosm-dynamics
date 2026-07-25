"""Career construction and claimant inclusion for the first estimates.

This module is the pure implementation of sections 3--6 of
``docs/design/first_estimates_report.md``.  It consumes materialized frames;
it neither runs nor modifies the projection engine.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.engine.steps import ClaimingSchedule

OBSERVED_START_YEAR = 1968
OBSERVED_END_YEAR = 2012
BOUNDARY_YEAR = 2014
PROJECTED_START_YEAR = 2015
PROJECTED_END_YEAR = 2022
MIN_ELIGIBILITY_YEAR = 1979
COVERAGE_THRESHOLD = 0.80
COMPUTATION_YEARS = 35

_STRUCTURAL_GAP_YEARS = tuple(range(1997, 2013, 2))
_KNOWN_PROVENANCE = frozenset(
    {
        "observed",
        "gap_imputed",
        "boundary_2014",
        "projected",
    }
)
_DI_COUNT_KEYS = {
    "di_conversion": "excluded_di_conversion",
    "di_unknown": "excluded_di_unknown",
}
_EXCLUSION_REASONS = (
    "excluded_domain_incomplete",
    "excluded_pre1979_eligibility",
    "excluded_empty_span",
    "excluded_chronology_inconsistent",
    "excluded_low_coverage",
)


class BirthSource(str, Enum):
    """Frozen birth-year source precedence classes."""

    EXACT_MARRIAGE = "exact_marriage"
    INFERRED_PERIOD_AGE = "inferred_period_age"
    SYNTHETIC_NATIVE = "synthetic_native"


class CareerProvenance(str, Enum):
    """The exhaustive per-career-year provenance enum."""

    OBSERVED = "observed"
    GAP_IMPUTED = "gap_imputed"
    BOUNDARY_2014 = "boundary_2014"
    PROJECTED = "projected"
    UNKNOWN = "unknown"


class DIClass(str, Enum):
    """Whole-trajectory disability-conversion partition."""

    DI_CONVERSION = "di_conversion"
    DI_UNKNOWN = "di_unknown"
    NON_DI = "non_di"


class NonClaimantPath(str, Enum):
    """The two diagnostic paths into the single nonclaimant class."""

    DRAWN_NEVER_CLAIMED = "drawn_never_claimed"
    NEVER_DRAWN = "never_drawn"


class ClaimOrigin(str, Enum):
    """The disjoint non-DI claimant origin classes."""

    MODELED_AWARD = "modeled_award"
    OPENING_BACKFILL = "opening_backfill"


@dataclass(frozen=True)
class WeightedCount:
    """An unweighted count and its fixed-weight analogue."""

    key: str
    unweighted: int
    weighted: float

    def as_dict(self) -> dict[str, int | float | str]:
        return {
            "key": self.key,
            "unweighted": self.unweighted,
            "weighted": self.weighted,
        }


@dataclass(frozen=True)
class WeightedShare:
    """A named weighted numerator share with its denominator exposed."""

    key: str
    numerator_weight: float
    denominator_weight: float
    share: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "key": self.key,
            "numerator_weight": self.numerator_weight,
            "denominator_weight": self.denominator_weight,
            "share": self.share,
        }


@dataclass(frozen=True)
class EntrantDiagnostic:
    """Nonoperative explicit-row entrant diagnostic from section 10."""

    person_ids: tuple[int, ...]
    count: WeightedCount
    source_income_years: tuple[int, int] = (2016, 2018)
    may_overlap_inclusion_classes: bool = True
    operative_exclusion_rule: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "person_ids": list(self.person_ids),
            "count": self.count.as_dict(),
            "source_income_years": list(self.source_income_years),
            "may_overlap_inclusion_classes": (
                self.may_overlap_inclusion_classes
            ),
            "operative_exclusion_rule": self.operative_exclusion_rule,
        }


@dataclass(frozen=True)
class BirthYearRecord:
    """Resolved report birth year for one person."""

    person_id: int
    birth_year: int
    source: BirthSource

    @property
    def inferred(self) -> bool:
        return self.source is BirthSource.INFERRED_PERIOD_AGE

    def as_dict(self) -> dict[str, int | str | bool]:
        return {
            "person_id": self.person_id,
            "birth_year": self.birth_year,
            "source": self.source.value,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class CareerYear:
    """One nominal earnings year and its sole provenance class."""

    year: int
    earnings: float
    provenance: CareerProvenance

    @property
    def projected_odd_year_carry(self) -> bool:
        return (
            self.provenance is CareerProvenance.PROJECTED
            and self.year >= PROJECTED_START_YEAR
            and self.year % 2 == 1
        )

    def as_dict(self) -> dict[str, int | float | str | bool]:
        return {
            "year": self.year,
            "earnings": self.earnings,
            "provenance": self.provenance.value,
            "projected_odd_year_carry": self.projected_odd_year_carry,
        }


@dataclass(frozen=True)
class CareerRecord:
    """As-of-claim career and its coverage diagnostics."""

    person_id: int
    claim_year: int
    coverage_start_year: int
    coverage_end_year: int
    coverage_ratio: float
    imputed_year_share: float
    years: tuple[CareerYear, ...]
    pre_career_years_zeroed: tuple[int, ...]
    pre_1968_top35_zero_years: tuple[int, ...]

    @property
    def top35_reaches_pre_1968(self) -> bool:
        return bool(self.pre_1968_top35_zero_years)

    @property
    def provenance_counts(self) -> dict[str, int]:
        counts = Counter(year.provenance.value for year in self.years)
        return {
            provenance.value: int(counts.get(provenance.value, 0))
            for provenance in CareerProvenance
        }

    @property
    def coverage_provenance_counts(self) -> dict[str, int]:
        """Provenance mix on the registered inclusive coverage span."""
        return self.provenance_counts

    @property
    def affected_odd_year_share(self) -> float:
        in_span = [
            year
            for year in self.years
            if self.coverage_start_year <= year.year <= self.coverage_end_year
        ]
        if not in_span:
            return 0.0
        affected = sum(year.projected_odd_year_carry for year in in_span)
        return affected / len(in_span)

    def earnings_history(self) -> dict[int, float]:
        """Return a fresh AIME-ready nominal history."""
        return {year.year: year.earnings for year in self.years}

    def as_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "claim_year": self.claim_year,
            "coverage_start_year": self.coverage_start_year,
            "coverage_end_year": self.coverage_end_year,
            "coverage_ratio": self.coverage_ratio,
            "imputed_year_share": self.imputed_year_share,
            "affected_odd_year_share": self.affected_odd_year_share,
            "provenance_counts": self.provenance_counts,
            "coverage_provenance_counts": (self.coverage_provenance_counts),
            "pre_career_years_zeroed": list(self.pre_career_years_zeroed),
            "pre_1968_top35_zero_years": list(self.pre_1968_top35_zero_years),
            "top35_reaches_pre_1968": self.top35_reaches_pre_1968,
            "years": [year.as_dict() for year in self.years],
        }


@dataclass(frozen=True)
class DIRecord:
    """Stage-A classification for one population member."""

    person_id: int
    classification: DIClass

    def as_dict(self) -> dict[str, int | str]:
        return {
            "person_id": self.person_id,
            "classification": self.classification.value,
        }


@dataclass(frozen=True)
class NonClaimantRecord:
    """A Stage-B nonclaimant and its diagnostic entry path."""

    person_id: int
    path: NonClaimantPath

    def as_dict(self) -> dict[str, int | str]:
        return {"person_id": self.person_id, "path": self.path.value}


@dataclass(frozen=True)
class CandidateOriginRecord:
    """Stage-C origin and operative claim coordinates."""

    person_id: int
    origin: ClaimOrigin
    first_exposure_year: int
    first_exposure_age: int
    engine_claim_age: int
    engine_claim_year: int
    operative_claim_age: int
    operative_claim_year: int
    schedule_year: int | None
    schedule_snap: str | None

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            "person_id": self.person_id,
            "origin": self.origin.value,
            "first_exposure_year": self.first_exposure_year,
            "first_exposure_age": self.first_exposure_age,
            "engine_claim_age": self.engine_claim_age,
            "engine_claim_year": self.engine_claim_year,
            "operative_claim_age": self.operative_claim_age,
            "operative_claim_year": self.operative_claim_year,
            "schedule_year": self.schedule_year,
            "schedule_snap": self.schedule_snap,
        }


@dataclass(frozen=True)
class ExclusionRecord:
    """A candidate's single first-failing Stage-D reason."""

    person_id: int
    reason: str
    coverage_ratio: float | None

    def as_dict(self) -> dict[str, int | float | str | None]:
        return {
            "person_id": self.person_id,
            "reason": self.reason,
            "coverage_ratio": self.coverage_ratio,
        }


@dataclass(frozen=True)
class IncludedClaimant:
    """Ledger-ready included claimant with only operative claim state."""

    person_id: int
    birth_year: int
    birth_source: BirthSource
    sex: str
    weight: float
    origin: ClaimOrigin
    claim_age: int
    claim_year: int
    first_exposure_year: int
    first_exposure_age: int
    presence_years: tuple[int, ...]
    last_present_year: int
    career: CareerRecord
    post_claim_earnings: tuple[tuple[int, float], ...]

    @property
    def claim_origin(self) -> str:
        """String-valued origin adapter for the statutory ledgers."""
        return self.origin.value

    @property
    def earnings_by_year(self) -> dict[int, float]:
        """Fresh nominal career mapping for the statutory ledgers."""
        return self.career.earnings_history()

    @property
    def provenance_by_year(self) -> dict[int, str]:
        """Fresh year-to-provenance adapter for the statutory ledgers."""
        return {year.year: year.provenance.value for year in self.career.years}

    @property
    def odd_year_carried_years(self) -> frozenset[int]:
        """Projected odd years affected by the engine's carry law."""
        return frozenset(
            year.year
            for year in self.career.years
            if year.projected_odd_year_carry
        )

    @property
    def post_claim_earnings_by_year(self) -> dict[int, float]:
        """Fresh diagnostic mapping; never enters the award computation."""
        return dict(self.post_claim_earnings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "birth_year": self.birth_year,
            "birth_source": self.birth_source.value,
            "birth_year_inferred": (
                self.birth_source is BirthSource.INFERRED_PERIOD_AGE
            ),
            "sex": self.sex,
            "weight": self.weight,
            "origin": self.origin.value,
            "claim_age": self.claim_age,
            "claim_year": self.claim_year,
            "first_exposure_year": self.first_exposure_year,
            "first_exposure_age": self.first_exposure_age,
            "presence_years": list(self.presence_years),
            "last_present_year": self.last_present_year,
            "career": self.career.as_dict(),
            "post_claim_earnings_by_year": dict(self.post_claim_earnings),
        }


@dataclass(frozen=True)
class InclusionResult:
    """Frozen, JSON-ready output of the canonical four-stage law."""

    births: tuple[BirthYearRecord, ...]
    di_partition: tuple[DIRecord, ...]
    nonclaimants: tuple[NonClaimantRecord, ...]
    origins: tuple[CandidateOriginRecord, ...]
    exclusions: tuple[ExclusionRecord, ...]
    included: tuple[IncludedClaimant, ...]
    counts: tuple[WeightedCount, ...]
    birth_source_counts: tuple[WeightedCount, ...]
    opening_stock_snap_counts: tuple[WeightedCount, ...]
    opening_stock_snap_denominator: WeightedCount
    opening_stock_snap_weighted_shares: tuple[WeightedShare, ...]
    entrant_diagnostic: EntrantDiagnostic

    def as_dict(self) -> dict[str, Any]:
        return {
            "births": [record.as_dict() for record in self.births],
            "di_partition": [record.as_dict() for record in self.di_partition],
            "nonclaimants": [record.as_dict() for record in self.nonclaimants],
            "origins": [record.as_dict() for record in self.origins],
            "exclusions": [record.as_dict() for record in self.exclusions],
            "included": [record.as_dict() for record in self.included],
            "counts": {
                record.key: {
                    "unweighted": record.unweighted,
                    "weighted": record.weighted,
                }
                for record in self.counts
            },
            "birth_source_counts": {
                record.key: {
                    "unweighted": record.unweighted,
                    "weighted": record.weighted,
                }
                for record in self.birth_source_counts
            },
            "opening_stock_snap_counts": {
                record.key: {
                    "unweighted": record.unweighted,
                    "weighted": record.weighted,
                }
                for record in self.opening_stock_snap_counts
            },
            "opening_stock_snap_denominator": (
                self.opening_stock_snap_denominator.as_dict()
            ),
            "opening_stock_snap_weighted_shares": {
                record.key: record.as_dict()
                for record in self.opening_stock_snap_weighted_shares
            },
            "entrant_diagnostic": self.entrant_diagnostic.as_dict(),
        }

    def included_frame(self) -> pd.DataFrame:
        """Return one flat row per included claimant."""
        columns = (
            "person_id",
            "birth_year",
            "birth_source",
            "birth_year_inferred",
            "sex",
            "weight",
            "origin",
            "claim_age",
            "claim_year",
            "first_exposure_year",
            "first_exposure_age",
            "presence_years",
            "last_present_year",
            "coverage_ratio",
            "imputed_year_share",
            "affected_odd_year_share",
            "top35_reaches_pre_1968",
        )
        rows = []
        for claimant in self.included:
            value = claimant.as_dict()
            career = value.pop("career")
            value.update(
                {
                    "coverage_ratio": career["coverage_ratio"],
                    "imputed_year_share": career["imputed_year_share"],
                    "affected_odd_year_share": career[
                        "affected_odd_year_share"
                    ],
                    "top35_reaches_pre_1968": career["top35_reaches_pre_1968"],
                }
            )
            rows.append(value)
        return pd.DataFrame(rows, columns=columns)

    def career_frame(self) -> pd.DataFrame:
        """Return the long person-year career frame."""
        rows = []
        for claimant in self.included:
            for year in claimant.career.years:
                rows.append(
                    {
                        "person_id": claimant.person_id,
                        **year.as_dict(),
                    }
                )
        return pd.DataFrame(
            rows,
            columns=(
                "person_id",
                "year",
                "earnings",
                "provenance",
                "projected_odd_year_carry",
            ),
        )


def _require_columns(
    frame: pd.DataFrame, columns: Collection[str], label: str
) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing columns {sorted(missing)}")


def _as_int(value: Any, label: str) -> int:
    if pd.isna(value):
        raise ValueError(f"{label} is missing")
    number = float(value)
    if not np.isfinite(number) or not number.is_integer():
        raise ValueError(f"{label} must be a finite integer, got {value!r}")
    return int(number)


def _optional_int(value: Any, label: str) -> int | None:
    return None if pd.isna(value) else _as_int(value, label)


def _person_values(
    frame: pd.DataFrame, column: str, person_id: int
) -> tuple[int, ...]:
    values = {
        _as_int(value, f"{column} for person {person_id}")
        for value in frame[column]
        if not pd.isna(value)
    }
    return tuple(sorted(values))


def derive_birth_years(
    marriage_history: pd.DataFrame,
    observed_earnings: pd.DataFrame,
    synthetic_birth_years: Mapping[int, int] | None = None,
    *,
    required_person_ids: Collection[int] | None = None,
) -> tuple[BirthYearRecord, ...]:
    """Resolve birth years under the exact registered precedence.

    Marriage-history birth year wins.  Otherwise the source is the rounded
    median of ``period - age`` over the same age-14--90 support used by
    ``person_earnings_histories``.  Native synthetic birth years are last.
    Conflicting exact years fail closed rather than silently selecting one.
    When ``required_person_ids`` is ``None``, that law applies to every
    person.  When supplied, required conflicts still fail closed and
    conflicting nonmembers receive no birth-year record from any source.
    """
    _require_columns(
        marriage_history,
        {"person_id", "birth_year"},
        "marriage history",
    )
    _require_columns(
        observed_earnings,
        {"person_id", "period", "age"},
        "observed earnings",
    )
    synthetic = {
        _as_int(person_id, "synthetic person_id"): _as_int(
            year, f"synthetic birth year for person {person_id}"
        )
        for person_id, year in (synthetic_birth_years or {}).items()
    }
    required = (
        None
        if required_person_ids is None
        else {
            _as_int(person_id, "required person_id")
            for person_id in required_person_ids
        }
    )

    exact: dict[int, int] = {}
    excluded_conflicts: set[int] = set()
    for raw_person_id, rows in marriage_history.groupby(
        "person_id", sort=False
    ):
        person_id = _as_int(raw_person_id, "marriage person_id")
        years = _person_values(rows, "birth_year", person_id)
        if len(years) > 1:
            if required is None or person_id in required:
                raise ValueError(
                    f"conflicting exact birth years for person {person_id}: "
                    f"{list(years)}"
                )
            excluded_conflicts.add(person_id)
            continue
        if years:
            exact[person_id] = years[0]

    support = observed_earnings[
        observed_earnings["age"].between(14, 90, inclusive="both")
    ].copy()
    support["_implied_birth_year"] = pd.to_numeric(
        support["period"], errors="coerce"
    ) - pd.to_numeric(support["age"], errors="coerce")
    inferred: dict[int, int] = {}
    for raw_person_id, rows in support.groupby("person_id", sort=False):
        person_id = _as_int(raw_person_id, "earnings person_id")
        values = rows["_implied_birth_year"].dropna()
        if len(values):
            median = float(values.median())
            if not np.isfinite(median):
                raise ValueError(
                    f"invalid inferred birth year for person {person_id}"
                )
            inferred[person_id] = int(round(median))

    people = sorted(
        (set(exact) | set(inferred) | set(synthetic)) - excluded_conflicts
    )
    records = []
    for person_id in people:
        if person_id in exact:
            year = exact[person_id]
            source = BirthSource.EXACT_MARRIAGE
        elif person_id in inferred:
            year = inferred[person_id]
            source = BirthSource.INFERRED_PERIOD_AGE
        else:
            year = synthetic[person_id]
            source = BirthSource.SYNTHETIC_NATIVE
        records.append(BirthYearRecord(person_id, year, source))
    return tuple(records)


def classify_di_trajectory(
    trajectory: pd.DataFrame,
    *,
    projection_start_year: int = BOUNDARY_YEAR,
    population_ids: Collection[int] | None = None,
) -> tuple[DIRecord, ...]:
    """Apply the whole-trajectory Stage-A precedence partition.

    Only extant rows are observations.  Missing person-years are never
    manufactured, so mortality absence cannot become ``di_unknown``.
    """
    _require_columns(trajectory, {"person_id", "year"}, "trajectory")
    values = (
        trajectory["di_converted"]
        if "di_converted" in trajectory
        else pd.Series(pd.NA, index=trajectory.index, dtype="boolean")
    )
    work = trajectory[["person_id", "year"]].copy()
    work["di_converted"] = values
    classified: dict[int, DIClass] = {}
    for raw_person_id, rows in work.groupby("person_id", sort=True):
        person_id = _as_int(raw_person_id, "trajectory person_id")
        concrete = rows["di_converted"].dropna()
        invalid = [
            value
            for value in concrete
            if not isinstance(value, (bool, np.bool_))
            and value not in (0, 1, 0.0, 1.0)
        ]
        if invalid:
            raise ValueError(
                f"invalid di_converted value for person {person_id}: "
                f"{invalid[0]!r}"
            )
        ever_true = any(bool(value) for value in concrete)
        post_start = rows[
            pd.to_numeric(rows["year"], errors="coerce")
            > projection_start_year
        ]
        if ever_true:
            classification = DIClass.DI_CONVERSION
        elif post_start["di_converted"].isna().any():
            classification = DIClass.DI_UNKNOWN
        else:
            classification = DIClass.NON_DI
        classified[person_id] = classification
    universe = (
        set(classified)
        if population_ids is None
        else {
            _as_int(person_id, "population person_id")
            for person_id in population_ids
        }
    )
    unknown_people = set(classified) - universe
    if unknown_people:
        raise ValueError(
            "DI trajectory contains persons outside the population: "
            f"{sorted(unknown_people)[:10]}"
        )
    return tuple(
        DIRecord(
            person_id,
            classified.get(person_id, DIClass.NON_DI),
        )
        for person_id in sorted(universe)
    )


def build_population_roster(
    initial_slice: pd.DataFrame,
    scheduled_entries_by_year: Mapping[int, pd.DataFrame],
    trajectory: pd.DataFrame,
) -> pd.DataFrame:
    """Build the all-person report roster from projection inputs and output.

    Initial and scheduled frames retain people who die before producing a
    returned projection slice.  The trajectory contributes synthetic people
    born during projection.  Seed rows are population metadata, not invented
    DI observations.
    """
    required = {"person_id", "weight", "sex"}
    _require_columns(initial_slice, required, "initial population slice")
    frames = [initial_slice.copy()]
    for raw_year, frame in sorted(
        scheduled_entries_by_year.items(), key=lambda item: int(item[0])
    ):
        _as_int(raw_year, "scheduled entry year")
        _require_columns(frame, required, "scheduled population slice")
        frames.append(frame.copy())
    _require_columns(trajectory, required, "trajectory")
    frames.append(trajectory.copy())
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["_source_order"] = np.arange(len(combined), dtype=np.int64)
    roster_rows = []
    for raw_person_id, rows in combined.groupby("person_id", sort=True):
        person_id = _as_int(raw_person_id, "population person_id")
        first = rows.sort_values("_source_order", kind="stable").iloc[0]
        weight = float(_fixed_person_value(rows, "weight", person_id))
        sex = str(_fixed_person_value(rows, "sex", person_id))
        record: dict[str, Any] = {
            "person_id": person_id,
            "weight": weight,
            "sex": sex,
        }
        if "birth_year" in rows:
            native_births = rows["birth_year"].dropna().unique().tolist()
            if len(native_births) > 1:
                raise ValueError(
                    f"person {person_id} has conflicting native birth years"
                )
            if native_births:
                record["birth_year"] = _as_int(
                    native_births[0],
                    f"native birth year for person {person_id}",
                )
        if "year" in rows and pd.notna(first.get("year")):
            record["seed_year"] = _as_int(
                first["year"], f"seed year for person {person_id}"
            )
        roster_rows.append(record)
    return (
        pd.DataFrame(roster_rows)
        .sort_values("person_id", kind="stable")
        .reset_index(drop=True)
    )


def _known_year(
    year: int,
    sources: Mapping[int, tuple[float, CareerProvenance]],
) -> tuple[float, CareerProvenance] | None:
    value = sources.get(year)
    if value is None or not np.isfinite(value[0]):
        return None
    return value


def _impute_gap(
    year: int,
    sources: Mapping[int, tuple[float, CareerProvenance]],
) -> tuple[float, CareerProvenance] | None:
    left = _known_year(year - 1, sources)
    right = _known_year(year + 1, sources)
    if left is not None and right is not None:
        earnings = (left[0] + right[0]) / 2.0
    elif left is not None:
        earnings = left[0]
    elif right is not None:
        earnings = right[0]
    else:
        return None
    return earnings, CareerProvenance.GAP_IMPUTED


def build_career(
    *,
    person_id: int,
    birth_year: int,
    claim_year: int,
    observed_earnings: pd.DataFrame,
    trajectory: pd.DataFrame,
) -> CareerRecord:
    """Build one annual career after applying the as-of cutoff first."""
    _require_columns(
        observed_earnings,
        {"person_id", "period", "earnings"},
        "observed earnings",
    )
    _require_columns(
        trajectory,
        {"person_id", "year", "earnings"},
        "trajectory",
    )
    person_id = _as_int(person_id, "person_id")
    birth_year = _as_int(birth_year, f"birth year for person {person_id}")
    claim_year = _as_int(claim_year, f"claim year for person {person_id}")
    end_year = min(claim_year, PROJECTED_END_YEAR)
    coverage_start = max(OBSERVED_START_YEAR, birth_year + 22)

    observed = observed_earnings[
        observed_earnings["person_id"] == person_id
    ].copy()
    observed["_period"] = pd.to_numeric(observed["period"], errors="coerce")
    observed = observed[
        observed["_period"].between(
            OBSERVED_START_YEAR, OBSERVED_END_YEAR, inclusive="both"
        )
        & (observed["_period"] <= claim_year)
    ]
    observed_by_year = observed.groupby("_period", sort=False)["earnings"].sum(
        min_count=1
    )

    projected = trajectory[trajectory["person_id"] == person_id].copy()
    projected["_year"] = pd.to_numeric(projected["year"], errors="coerce")
    projected = projected[projected["_year"] <= claim_year]

    sources: dict[int, tuple[float, CareerProvenance]] = {}
    for raw_year, raw_earnings in observed_by_year.items():
        year = _as_int(raw_year, f"observed year for person {person_id}")
        if pd.notna(raw_earnings):
            sources[year] = (
                float(raw_earnings),
                CareerProvenance.OBSERVED,
            )
    for raw_year, earnings in projected[["_year", "earnings"]].itertuples(
        index=False, name=None
    ):
        year = _as_int(raw_year, f"trajectory year for person {person_id}")
        if pd.isna(earnings):
            continue
        if year == BOUNDARY_YEAR:
            sources[year] = (
                float(earnings),
                CareerProvenance.BOUNDARY_2014,
            )
        elif PROJECTED_START_YEAR <= year <= PROJECTED_END_YEAR:
            sources[year] = (
                float(earnings),
                CareerProvenance.PROJECTED,
            )

    # Structural observed-panel odd years only.  The source restriction above
    # happened first, so a post-claim right neighbor cannot enter a gap.
    for year in _STRUCTURAL_GAP_YEARS:
        if year > claim_year or year in sources:
            continue
        imputed = _impute_gap(year, sources)
        if imputed is not None:
            sources[year] = imputed

    # The corrected 2013/2014 seam uses the same immediate-neighbor law.
    if claim_year >= 2013 and 2013 not in sources:
        imputed = _impute_gap(2013, sources)
        if imputed is not None:
            sources[2013] = imputed

    pre_career = tuple(
        range(
            OBSERVED_START_YEAR,
            min(end_year + 1, max(OBSERVED_START_YEAR, birth_year + 22)),
        )
    )
    years = [
        CareerYear(
            year,
            float(sources.get(year, (0.0, CareerProvenance.UNKNOWN))[0]),
            sources.get(year, (0.0, CareerProvenance.UNKNOWN))[1],
        )
        for year in range(coverage_start, end_year + 1)
    ]
    coverage_years = years
    if not coverage_years:
        raise ValueError(
            f"person {person_id} has an empty career coverage span"
        )
    known_count = sum(
        year.provenance.value in _KNOWN_PROVENANCE for year in coverage_years
    )
    coverage_ratio = known_count / len(coverage_years)
    if not 0.0 <= coverage_ratio <= 1.0:
        raise AssertionError("coverage ratio lies outside [0, 1]")
    imputed_count = sum(
        year.provenance is CareerProvenance.GAP_IMPUTED
        for year in coverage_years
    )

    pre_1968_available = max(0, OBSERVED_START_YEAR - (birth_year + 22))
    post_1968_span = max(0, end_year - OBSERVED_START_YEAR + 1)
    n_pre_1968_top35 = min(
        pre_1968_available,
        max(0, COMPUTATION_YEARS - post_1968_span),
    )
    pre_1968_end = OBSERVED_START_YEAR
    pre_1968_start = pre_1968_end - n_pre_1968_top35

    return CareerRecord(
        person_id=person_id,
        claim_year=claim_year,
        coverage_start_year=coverage_start,
        coverage_end_year=end_year,
        coverage_ratio=coverage_ratio,
        imputed_year_share=imputed_count / len(coverage_years),
        years=tuple(years),
        pre_career_years_zeroed=pre_career,
        pre_1968_top35_zero_years=tuple(range(pre_1968_start, pre_1968_end)),
    )


def _stable_person_rng(root_seed: int, person_id: int) -> np.random.Generator:
    root_seed = _as_int(root_seed, "stock imputation root seed")
    if root_seed < 0:
        raise ValueError("stock imputation root seed must be non-negative")
    identity = f"first_estimates.opening_stock.person.v1|{person_id}".encode()
    words = np.frombuffer(hashlib.sha256(identity).digest(), dtype="<u4")
    sequence = np.random.SeedSequence([root_seed, *map(int, words)])
    return np.random.default_rng(sequence)


def _opening_stock_draw(
    *,
    person_id: int,
    birth_year: int,
    sex: str,
    exposure_age: int,
    schedule: ClaimingSchedule,
    root_seed: int,
) -> tuple[int, int, str | None]:
    requested_year = birth_year + 62
    available = sorted(
        int(year)
        for schedule_sex, year in schedule.pmf
        if str(schedule_sex) == sex
    )
    if not available:
        raise KeyError(f"no claiming distribution for sex {sex!r}")
    schedule_year = min(
        available, key=lambda candidate: abs(candidate - requested_year)
    )
    if requested_year < available[0]:
        snap = "lower"
    elif requested_year > available[-1]:
        snap = "upper"
    else:
        snap = None
    ages, probability = schedule.distribution(sex, requested_year)
    keep = ages < exposure_age
    truncated_ages = ages[keep]
    truncated_probability = probability[keep]
    mass = float(truncated_probability.sum())
    if not len(truncated_ages) or not np.isfinite(mass) or mass <= 0.0:
        raise ValueError(
            "empty strictly-below exposure-age claiming mass for "
            f"person {person_id}"
        )
    probability = truncated_probability / mass
    chosen = _stable_person_rng(root_seed, person_id).choice(
        truncated_ages, p=probability
    )
    return int(chosen), schedule_year, snap


def _fixed_person_value(
    rows: pd.DataFrame,
    column: str,
    person_id: int,
    *,
    integer: bool = False,
) -> int | float | str:
    values = rows[column].dropna().unique().tolist()
    if not values:
        raise ValueError(f"person {person_id} has no {column}")
    if len(values) > 1:
        raise ValueError(
            f"person {person_id} has conflicting {column}: {values}"
        )
    if integer:
        return _as_int(values[0], f"{column} for person {person_id}")
    return values[0]


def _weighted_counts(
    keyed_people: Collection[tuple[str, int]],
    weights: Mapping[int, float],
    *,
    all_keys: Collection[str] = (),
) -> tuple[WeightedCount, ...]:
    by_key: dict[str, list[int]] = {key: [] for key in all_keys}
    for key, person_id in keyed_people:
        by_key.setdefault(key, []).append(person_id)
    return tuple(
        WeightedCount(
            key=key,
            unweighted=len(person_ids),
            weighted=float(
                sum(weights[person_id] for person_id in person_ids)
            ),
        )
        for key, person_ids in sorted(by_key.items())
    )


def build_career_inclusion(
    trajectory: pd.DataFrame,
    population_roster: pd.DataFrame,
    observed_earnings: pd.DataFrame,
    marriage_history: pd.DataFrame,
    synthetic_birth_years: Mapping[int, int],
    claiming_schedule: ClaimingSchedule,
    earnings_domain_ids: Collection[int],
    *,
    stock_imputation_root_seed: int,
    projection_start_year: int = BOUNDARY_YEAR,
) -> InclusionResult:
    """Run the canonical Stage A--D benefit-inclusion law."""
    _require_columns(
        trajectory,
        {
            "person_id",
            "year",
            "age",
            "sex",
            "weight",
            "earnings",
            "claim_age",
            "claim_year",
        },
        "trajectory",
    )
    _require_columns(
        population_roster,
        {"person_id", "weight", "sex"},
        "population roster",
    )
    if trajectory.duplicated(["person_id", "year"]).any():
        raise ValueError("trajectory has duplicate person-year rows")
    if population_roster["person_id"].duplicated().any():
        raise ValueError("population roster has duplicate person rows")
    people = tuple(
        sorted(
            {
                *(
                    _as_int(person_id, "trajectory person_id")
                    for person_id in trajectory["person_id"].unique()
                ),
                *(
                    _as_int(person_id, "population person_id")
                    for person_id in population_roster["person_id"].unique()
                ),
            }
        )
    )
    if not people:
        zero = WeightedCount(
            key="included_opening_backfill",
            unweighted=0,
            weighted=0.0,
        )
        shares = tuple(
            WeightedShare(key, 0.0, 0.0, 0.0)
            for key in ("lower_endpoint", "upper_endpoint")
        )
        entrant = EntrantDiagnostic(
            (),
            WeightedCount(
                key="explicit_2016_2018_row_entrant",
                unweighted=0,
                weighted=0.0,
            ),
        )
        return InclusionResult(
            (), (), (), (), (), (), (), (), (), zero, shares, entrant
        )

    work = trajectory.copy()
    work["person_id"] = work["person_id"].map(
        lambda value: _as_int(value, "trajectory person_id")
    )
    work["year"] = work["year"].map(
        lambda value: _as_int(value, "trajectory year")
    )
    rows_by_person = {
        int(person_id): rows.sort_values("year", kind="stable")
        for person_id, rows in work.groupby("person_id", sort=True)
    }
    roster = population_roster.copy()
    roster["person_id"] = roster["person_id"].map(
        lambda value: _as_int(value, "population person_id")
    )
    roster_by_person = {
        int(row["person_id"]): row for _, row in roster.iterrows()
    }
    weights: dict[int, float] = {}
    sexes: dict[int, str] = {}
    presence: dict[int, tuple[int, ...]] = {}
    for person_id in people:
        rows = rows_by_person.get(person_id)
        roster_row = roster_by_person.get(person_id)
        if roster_row is not None:
            raw_weight = roster_row["weight"]
            raw_sex = roster_row["sex"]
        elif rows is not None:
            raw_weight = _fixed_person_value(rows, "weight", person_id)
            raw_sex = _fixed_person_value(rows, "sex", person_id)
        else:
            raise AssertionError("population member has no metadata")
        weight = float(raw_weight)
        if not np.isfinite(weight) or weight <= 0.0:
            raise ValueError(f"invalid weight for person {person_id}")
        weights[person_id] = weight
        if pd.isna(raw_sex):
            raise ValueError(f"person {person_id} has no sex")
        sexes[person_id] = str(raw_sex)
        presence[person_id] = (
            () if rows is None else tuple(int(year) for year in rows["year"])
        )

    resolved_birth_records = derive_birth_years(
        marriage_history,
        observed_earnings,
        synthetic_birth_years,
        required_person_ids=people,
    )
    population_set = set(people)
    birth_records = tuple(
        record
        for record in resolved_birth_records
        if record.person_id in population_set
    )
    births = {record.person_id: record for record in birth_records}
    di_records = classify_di_trajectory(
        work,
        projection_start_year=projection_start_year,
        population_ids=people,
    )
    di_by_person = {
        record.person_id: record.classification for record in di_records
    }
    if set(di_by_person) != set(people):
        raise AssertionError("DI partition is incomplete")

    nonclaimants: list[NonClaimantRecord] = []
    candidate_people: list[int] = []
    for person_id in people:
        if di_by_person[person_id] is not DIClass.NON_DI:
            continue
        rows = rows_by_person.get(person_id)
        if rows is None:
            nonclaimants.append(
                NonClaimantRecord(person_id, NonClaimantPath.NEVER_DRAWN)
            )
            continue
        if rows["claim_year"].notna().any():
            candidate_people.append(person_id)
        elif rows["claim_age"].notna().any():
            nonclaimants.append(
                NonClaimantRecord(
                    person_id,
                    NonClaimantPath.DRAWN_NEVER_CLAIMED,
                )
            )
        else:
            nonclaimants.append(
                NonClaimantRecord(person_id, NonClaimantPath.NEVER_DRAWN)
            )

    missing_births = sorted(set(candidate_people) - set(births))
    if missing_births:
        raise ValueError(
            "candidate birth year is unavailable for persons "
            f"{missing_births[:10]}"
        )
    missing_population_births = sorted(population_set - set(births))
    if missing_population_births:
        raise ValueError(
            "report-population birth year is unavailable for persons "
            f"{missing_population_births[:10]}"
        )

    origins: list[CandidateOriginRecord] = []
    for person_id in candidate_people:
        rows = rows_by_person[person_id]
        post_start = rows[
            (rows["year"] > projection_start_year) & rows["claim_age"].notna()
        ]
        if post_start.empty:
            raise ValueError(
                f"candidate {person_id} has no post-start claim-age exposure"
            )
        claim_ages = _person_values(rows, "claim_age", person_id)
        claim_years = _person_values(rows, "claim_year", person_id)
        if len(claim_ages) != 1 or len(claim_years) != 1:
            raise ValueError(
                f"candidate {person_id} has non-constant claim state"
            )
        exposure = post_start.iloc[0]
        first_exposure_year = int(exposure["year"])
        first_exposure_age = _as_int(
            exposure["age"], f"first exposure age for person {person_id}"
        )
        engine_claim_age = claim_ages[0]
        engine_claim_year = claim_years[0]
        if engine_claim_age >= first_exposure_age:
            origin = ClaimOrigin.MODELED_AWARD
            operative_age = engine_claim_age
            operative_year = engine_claim_year
            schedule_year = None
            schedule_snap = None
        else:
            origin = ClaimOrigin.OPENING_BACKFILL
            operative_age, schedule_year, schedule_snap = _opening_stock_draw(
                person_id=person_id,
                birth_year=births[person_id].birth_year,
                sex=sexes[person_id],
                exposure_age=first_exposure_age,
                schedule=claiming_schedule,
                root_seed=stock_imputation_root_seed,
            )
            operative_year = births[person_id].birth_year + operative_age
        origins.append(
            CandidateOriginRecord(
                person_id=person_id,
                origin=origin,
                first_exposure_year=first_exposure_year,
                first_exposure_age=first_exposure_age,
                engine_claim_age=engine_claim_age,
                engine_claim_year=engine_claim_year,
                operative_claim_age=operative_age,
                operative_claim_year=operative_year,
                schedule_year=schedule_year,
                schedule_snap=schedule_snap,
            )
        )
    if {record.person_id for record in origins} != set(candidate_people):
        raise AssertionError("origin partition is incomplete")

    domain = {
        _as_int(person_id, "earnings-domain person_id")
        for person_id in earnings_domain_ids
    }
    exclusions: list[ExclusionRecord] = []
    included: list[IncludedClaimant] = []
    for origin in origins:
        person_id = origin.person_id
        birth = births[person_id]
        eligibility_year = birth.birth_year + 62
        coverage_start = max(OBSERVED_START_YEAR, birth.birth_year + 22)
        coverage_end = min(origin.operative_claim_year, PROJECTED_END_YEAR)
        career = None
        reason = None
        coverage_ratio = None
        if person_id not in domain:
            reason = "excluded_domain_incomplete"
        elif eligibility_year < MIN_ELIGIBILITY_YEAR:
            reason = "excluded_pre1979_eligibility"
        elif coverage_start > coverage_end:
            reason = "excluded_empty_span"
        elif eligibility_year > origin.operative_claim_year:
            reason = "excluded_chronology_inconsistent"
        else:
            career = build_career(
                person_id=person_id,
                birth_year=birth.birth_year,
                claim_year=origin.operative_claim_year,
                observed_earnings=observed_earnings,
                trajectory=work,
            )
            coverage_ratio = career.coverage_ratio
            if coverage_ratio < COVERAGE_THRESHOLD:
                reason = "excluded_low_coverage"
        if reason is not None:
            exclusions.append(
                ExclusionRecord(person_id, reason, coverage_ratio)
            )
            continue
        if career is None:
            raise AssertionError("included claimant has no career")
        full_career = build_career(
            person_id=person_id,
            birth_year=birth.birth_year,
            claim_year=PROJECTED_END_YEAR,
            observed_earnings=observed_earnings,
            trajectory=work,
        )
        post_claim_earnings = tuple(
            (year.year, year.earnings)
            for year in full_career.years
            if year.year > origin.operative_claim_year
        )
        included.append(
            IncludedClaimant(
                person_id=person_id,
                birth_year=birth.birth_year,
                birth_source=birth.source,
                sex=sexes[person_id],
                weight=weights[person_id],
                origin=origin.origin,
                claim_age=origin.operative_claim_age,
                claim_year=origin.operative_claim_year,
                first_exposure_year=origin.first_exposure_year,
                first_exposure_age=origin.first_exposure_age,
                presence_years=presence[person_id],
                last_present_year=max(presence[person_id]),
                career=career,
                post_claim_earnings=post_claim_earnings,
            )
        )

    stage_keys: list[tuple[str, int]] = []
    for record in di_records:
        if record.classification is not DIClass.NON_DI:
            stage_keys.append(
                (_DI_COUNT_KEYS[record.classification.value], record.person_id)
            )
    stage_keys.extend(("nonclaimant", row.person_id) for row in nonclaimants)
    stage_keys.extend((row.reason, row.person_id) for row in exclusions)
    stage_keys.extend(("included", row.person_id) for row in included)
    counts = _weighted_counts(
        stage_keys,
        weights,
        all_keys=(
            "excluded_di_conversion",
            "excluded_di_unknown",
            "nonclaimant",
            *_EXCLUSION_REASONS,
            "included",
        ),
    )
    if sum(record.unweighted for record in counts) != len(people):
        raise AssertionError("population inclusion counts do not reconcile")

    nonclaimant_path_counts = _weighted_counts(
        [(row.path.value, row.person_id) for row in nonclaimants],
        weights,
        all_keys=tuple(path.value for path in NonClaimantPath),
    )
    origin_counts = _weighted_counts(
        [(f"origin_{row.origin.value}", row.person_id) for row in origins],
        weights,
        all_keys=tuple(f"origin_{origin.value}" for origin in ClaimOrigin),
    )
    counts = tuple((*counts, *nonclaimant_path_counts, *origin_counts))

    birth_source_counts = _weighted_counts(
        [(record.source.value, record.person_id) for record in birth_records],
        weights,
        all_keys=tuple(source.value for source in BirthSource),
    )
    if sum(record.unweighted for record in birth_source_counts) != len(people):
        raise AssertionError("birth-source counts do not reconcile population")
    included_ids = {record.person_id for record in included}
    snap_counts = _weighted_counts(
        [
            (f"{record.schedule_snap}_endpoint", record.person_id)
            for record in origins
            if record.person_id in included_ids
            and record.origin is ClaimOrigin.OPENING_BACKFILL
            and record.schedule_snap is not None
        ],
        weights,
        all_keys=("lower_endpoint", "upper_endpoint"),
    )
    included_opening_ids = [
        record.person_id
        for record in origins
        if record.person_id in included_ids
        and record.origin is ClaimOrigin.OPENING_BACKFILL
    ]
    snap_denominator = WeightedCount(
        key="included_opening_backfill",
        unweighted=len(included_opening_ids),
        weighted=float(
            sum(weights[person_id] for person_id in included_opening_ids)
        ),
    )
    snap_by_key = {record.key: record for record in snap_counts}
    snap_shares = tuple(
        WeightedShare(
            key=key,
            numerator_weight=snap_by_key[key].weighted,
            denominator_weight=snap_denominator.weighted,
            share=(
                snap_by_key[key].weighted / snap_denominator.weighted
                if snap_denominator.weighted > 0.0
                else 0.0
            ),
        )
        for key in ("lower_endpoint", "upper_endpoint")
    )

    _require_columns(
        observed_earnings,
        {"person_id", "period"},
        "observed earnings",
    )
    explicit_period = pd.to_numeric(
        observed_earnings["period"], errors="coerce"
    )
    explicit_people = {
        _as_int(person_id, "explicit earnings-row person_id")
        for person_id in observed_earnings.loc[
            explicit_period.isin((2016, 2018)), "person_id"
        ].unique()
    }
    entrant_ids = tuple(sorted((explicit_people & set(people)) - domain))
    entrant_diagnostic = EntrantDiagnostic(
        person_ids=entrant_ids,
        count=WeightedCount(
            key="explicit_2016_2018_row_entrant",
            unweighted=len(entrant_ids),
            weighted=float(
                sum(weights[person_id] for person_id in entrant_ids)
            ),
        ),
    )

    return InclusionResult(
        births=tuple(birth_records),
        di_partition=tuple(di_records),
        nonclaimants=tuple(nonclaimants),
        origins=tuple(origins),
        exclusions=tuple(exclusions),
        included=tuple(included),
        counts=counts,
        birth_source_counts=birth_source_counts,
        opening_stock_snap_counts=snap_counts,
        opening_stock_snap_denominator=snap_denominator,
        opening_stock_snap_weighted_shares=snap_shares,
        entrant_diagnostic=entrant_diagnostic,
    )
