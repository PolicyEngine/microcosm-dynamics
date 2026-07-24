"""Statutory benefit and payroll-revenue ledgers for first estimates.

This module is deliberately downstream of projection and career assembly.  It
does not alter engine state, draw survival expectations, or reconstruct
earnings.  Benefit awards consume only already-included career records.
Revenue consumes every row of the unsplit projection's realized 2015-2022
slices.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from numbers import Integral, Real
from typing import Any

import pandas as pd

from populace_dynamics import claiming
from populace_dynamics.estimates.parameters import (
    COLASeries,
    ReportParameters,
)
from populace_dynamics.ss import benefits

__all__ = [
    "BENEFIT_MEASURE_LABEL",
    "DRAW_INDICES",
    "EVIDENCE_LABELS",
    "ODD_YEAR_CARRY_DISCLOSURE",
    "REPORT_YEARS",
    "AcrossDrawLedgers",
    "AcrossDrawMetric",
    "AcrossDrawTableRow",
    "BenefitAnnualRow",
    "BenefitBiennialRow",
    "BenefitClaimant",
    "BenefitLedger",
    "BenefitPersonLedger",
    "RevenueAnnualRow",
    "RevenueBiennialRow",
    "RevenueLedger",
    "aggregate_benefit_draws",
    "aggregate_revenue_draws",
    "build_benefit_ledger",
    "build_revenue_ledger",
    "floor_to_dime",
]

REPORT_YEARS = tuple(range(2015, 2023))
DRAW_INDICES = tuple(range(20))
BENEFIT_ORIGINS = ("modeled_award", "opening_backfill")
EVIDENCE_LABELS = (
    "frame-relative",
    "pre-alignment",
    "labor-income proxy",
)
BENEFIT_MEASURE_LABEL = (
    "annualized statutory benefit, eligibility-PIA with COLA, "
    "no recomputation"
)
ODD_YEAR_CARRY_DISCLOSURE = (
    "The engine draws even-year earnings and carries the prior even-year "
    "value into odd years (2015 repeats 2014, 2017 repeats 2016, and so on)."
)
CAREER_PROVENANCE_CLASSES = (
    "observed",
    "gap_imputed",
    "boundary_2014",
    "projected",
    "unknown",
)
_BIENNIAL_END_YEARS = (2016, 2018, 2020, 2022)
_BENEFIT_ROW_METRICS = (
    "unweighted_award_count",
    "weighted_award_count",
    "average_monthly_benefit_at_award",
    "unweighted_beneficiary_count",
    "weighted_beneficiary_count",
    "frame_annualized_benefit",
)
_REVENUE_ROW_METRICS = (
    "unweighted_person_year_count",
    "weighted_person_year_count",
    "unweighted_covered_earner_count",
    "weighted_covered_earner_count",
    "weighted_taxable_payroll",
    "employee_contributions",
    "employer_contributions",
    "combined_contributions",
)


@dataclass(frozen=True)
class BenefitClaimant:
    """Normalized input for one claimant that passed all inclusion stages."""

    person_id: int | str
    birth_year: int
    claim_age: int
    claim_year: int
    claim_origin: str
    weight: float
    earnings_by_year: Mapping[int, float]
    presence_years: frozenset[int]
    provenance_by_year: Mapping[int, str] = field(default_factory=dict)
    odd_year_carried_years: frozenset[int] = frozenset()
    post_claim_earnings_by_year: Mapping[int, float] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class BenefitPersonLedger:
    """Auditable, once-computed award and realized payment years."""

    person_id: int | str
    birth_year: int
    eligibility_year: int
    claim_age: int
    claim_year: int
    claim_origin: str
    weight: float
    aime: float
    eligibility_pia: float
    claim_age_factor: float
    adjusted_pia_at_eligibility: float
    monthly_benefit_at_award: float
    aime_history_years: tuple[int, ...]
    payment_monthly_by_year: Mapping[int, float]
    positive_post_claim_earnings: bool
    post_claim_earnings_years_examined: tuple[int, ...]
    career_provenance_counts: Mapping[str, int]
    career_provenance_shares: Mapping[str, float]
    odd_year_carried_year_share: float
    award_formula_computation_count: int = 1
    post_claim_recomputation_count: int = 0


@dataclass(frozen=True)
class BenefitAnnualRow:
    """One origin-by-calendar-year benefit table row."""

    claim_origin: str
    year: int
    unweighted_award_count: int
    weighted_award_count: float
    average_monthly_benefit_at_award: float | None
    unweighted_beneficiary_count: int
    weighted_beneficiary_count: float
    frame_annualized_benefit: float


@dataclass(frozen=True)
class BenefitBiennialRow:
    """Two-year companion to annual benefit presentation."""

    claim_origin: str
    end_year: int
    component_years: tuple[int, int]
    unweighted_award_count: int
    weighted_award_count: float
    average_monthly_benefit_at_award: float | None
    unweighted_beneficiary_count: int
    weighted_beneficiary_count: float
    frame_annualized_benefit: float
    odd_year_carry_disclosure: str = ODD_YEAR_CARRY_DISCLOSURE


@dataclass(frozen=True)
class BenefitLedger:
    """Benefit output for one registered projection draw."""

    draw_index: int
    people: tuple[BenefitPersonLedger, ...]
    annual_rows: tuple[BenefitAnnualRow, ...]
    biennial_rows: tuple[BenefitBiennialRow, ...]
    diagnostics: Mapping[str, float]
    evidence_labels: tuple[str, str, str] = EVIDENCE_LABELS
    measure_label: str = BENEFIT_MEASURE_LABEL
    odd_year_carry_disclosure: str = ODD_YEAR_CARRY_DISCLOSURE


@dataclass(frozen=True)
class RevenueAnnualRow:
    """One realized calendar-year payroll-contribution row."""

    year: int
    unweighted_person_year_count: int
    weighted_person_year_count: float
    unweighted_covered_earner_count: int
    weighted_covered_earner_count: float
    weighted_taxable_payroll: float
    employee_contributions: float
    employer_contributions: float
    combined_contributions: float
    odd_year_carry_affected: bool


@dataclass(frozen=True)
class RevenueBiennialRow:
    """Paired odd/even-year revenue companion."""

    end_year: int
    component_years: tuple[int, int]
    unweighted_person_year_count: int
    weighted_person_year_count: float
    unweighted_covered_earner_count: int
    weighted_covered_earner_count: float
    weighted_taxable_payroll: float
    employee_contributions: float
    employer_contributions: float
    combined_contributions: float
    odd_year_carry_pair_interpretation: str
    odd_year_carry_disclosure: str = ODD_YEAR_CARRY_DISCLOSURE


@dataclass(frozen=True)
class RevenueLedger:
    """Revenue output for every projected person-year in one draw."""

    draw_index: int
    annual_rows: tuple[RevenueAnnualRow, ...]
    biennial_rows: tuple[RevenueBiennialRow, ...]
    diagnostics: Mapping[str, float]
    evidence_labels: tuple[str, str, str] = EVIDENCE_LABELS
    earnings_measure_label: str = "labor-income proxy"
    dollar_basis: str = "nominal"
    population_basis: str = "unsplit projection.slices"
    odd_year_carry_disclosure: str = ODD_YEAR_CARRY_DISCLOSURE


@dataclass(frozen=True)
class AcrossDrawMetric:
    """Mean and sample SD over registered draws for one scalar."""

    n_draws: int
    n_observations: int
    mean: float | None
    sample_sd: float | None


@dataclass(frozen=True)
class AcrossDrawTableRow:
    """Dimensions and across-draw summaries for one table row."""

    dimensions: Mapping[str, int | str | tuple[int, int]]
    metrics: Mapping[str, AcrossDrawMetric]


@dataclass(frozen=True)
class AcrossDrawLedgers:
    """Across-draw summaries for annual, biennial, and diagnostic tables."""

    draw_indices: tuple[int, ...]
    annual_rows: tuple[AcrossDrawTableRow, ...]
    biennial_rows: tuple[AcrossDrawTableRow, ...]
    diagnostics: Mapping[str, AcrossDrawMetric]


def floor_to_dime(value: float) -> float:
    """Round a finite nonnegative amount down to the next lower dime."""

    amount = _finite_number(value, "amount")
    if amount < 0:
        raise ValueError("A benefit amount cannot be negative.")
    return math.floor(amount * 10.0 + 1e-9) / 10.0


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _whole_number(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{label} must be an integer.")
    return int(value)


def _person_id(value: Any) -> int | str:
    if isinstance(value, bool):
        raise TypeError("person_id cannot be boolean.")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, str) and value:
        return value
    raise TypeError("person_id must be an integer or nonempty string.")


def _value(record: Any, *names: str) -> Any:
    if isinstance(record, Mapping):
        for name in names:
            if name in record:
                return record[name]
    else:
        for name in names:
            if hasattr(record, name):
                return getattr(record, name)
    joined = ", ".join(names)
    raise TypeError(f"record lacks required field (one of: {joined}).")


def _career_earnings(raw: Any) -> Mapping[int, float]:
    if not isinstance(raw, Mapping):
        earnings_history = getattr(raw, "earnings_history", None)
        if callable(earnings_history):
            raw = earnings_history()
        for name in ("earnings_by_year", "values_by_year", "career"):
            if hasattr(raw, name):
                raw = getattr(raw, name)
                break
    if not isinstance(raw, Mapping):
        raise TypeError("career earnings must be a year-keyed mapping.")

    result: dict[int, float] = {}
    for raw_year, raw_entry in raw.items():
        year = _whole_number(raw_year, "career year")
        if isinstance(raw_entry, Mapping):
            amount = _value(raw_entry, "earnings", "value", "amount")
        elif any(
            hasattr(raw_entry, name)
            for name in ("earnings", "value", "amount")
        ):
            amount = _value(raw_entry, "earnings", "value", "amount")
        else:
            amount = raw_entry
        if year in result:
            raise ValueError(f"duplicate career year {year}.")
        result[year] = _finite_number(amount, f"earnings for {year}")
    return dict(sorted(result.items()))


def _career_provenance(raw: Any) -> Mapping[int, str]:
    if not isinstance(raw, Mapping):
        career_years = getattr(raw, "years", None)
        if career_years is not None:
            raw = {
                entry.year: getattr(
                    entry.provenance, "value", entry.provenance
                )
                for entry in career_years
            }
        for name in ("provenance_by_year", "career_provenance"):
            if hasattr(raw, name):
                raw = getattr(raw, name)
                break
    if not isinstance(raw, Mapping):
        return {}

    result: dict[int, str] = {}
    for raw_year, raw_entry in raw.items():
        if isinstance(raw_entry, str):
            provenance = str(getattr(raw_entry, "value", raw_entry))
        elif isinstance(raw_entry, Mapping) and "provenance" in raw_entry:
            provenance = str(raw_entry["provenance"])
        elif hasattr(raw_entry, "provenance"):
            provenance = str(
                getattr(raw_entry.provenance, "value", raw_entry.provenance)
            )
        else:
            continue
        year = _whole_number(raw_year, "career provenance year")
        if provenance not in CAREER_PROVENANCE_CLASSES:
            raise ValueError(
                f"Career year {year} has invalid provenance {provenance!r}."
            )
        result[year] = provenance
    return dict(sorted(result.items()))


def _optional_value(record: Any, *names: str, default: Any) -> Any:
    try:
        return _value(record, *names)
    except TypeError:
        return default


def _presence_years(raw: Any) -> frozenset[int]:
    if isinstance(raw, Mapping):
        raw = [year for year, present in raw.items() if bool(present)]
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Iterable):
        raise TypeError("presence_years must be an iterable of years.")
    years = frozenset(_whole_number(year, "presence year") for year in raw)
    return years


def _normalize_claimant(record: Any) -> BenefitClaimant:
    if isinstance(record, BenefitClaimant):
        claimant = record
    else:
        raw_career = _value(record, "earnings_by_year", "career")
        raw_provenance = _optional_value(
            record,
            "provenance_by_year",
            "career_provenance",
            default=raw_career,
        )
        provenance_by_year = _career_provenance(raw_provenance)
        raw_odd_years = _optional_value(
            record,
            "odd_year_carried_years",
            default=(
                year
                for year, provenance in provenance_by_year.items()
                if provenance == "projected" and year % 2 == 1
            ),
        )
        raw_origin = _value(record, "claim_origin", "origin")
        claimant = BenefitClaimant(
            person_id=_person_id(_value(record, "person_id")),
            birth_year=_whole_number(
                _value(record, "birth_year"), "birth_year"
            ),
            claim_age=_whole_number(
                _value(record, "claim_age", "operative_claim_age"),
                "claim_age",
            ),
            claim_year=_whole_number(
                _value(record, "claim_year", "operative_claim_year"),
                "claim_year",
            ),
            claim_origin=str(getattr(raw_origin, "value", raw_origin)),
            weight=_finite_number(
                _value(record, "weight", "start_wave_weight"), "weight"
            ),
            earnings_by_year=_career_earnings(raw_career),
            presence_years=_presence_years(
                _value(record, "presence_years", "actual_presence_years")
            ),
            provenance_by_year=provenance_by_year,
            odd_year_carried_years=_presence_years(raw_odd_years),
            post_claim_earnings_by_year=_career_earnings(
                _optional_value(
                    record,
                    "post_claim_earnings_by_year",
                    default={},
                )
            ),
        )

    if claimant.claim_origin not in BENEFIT_ORIGINS:
        raise ValueError(
            f"Unknown benefit claim origin {claimant.claim_origin!r}."
        )
    if claimant.weight <= 0:
        raise ValueError("Benefit claimant weight must be positive.")
    eligibility_year = claimant.birth_year + 62
    if eligibility_year < 1979:
        raise ValueError(
            "Included claimant violates the 1979 eligibility era."
        )
    if claimant.claim_year < eligibility_year:
        raise ValueError("Included claimant violates claim chronology.")
    if claimant.claim_year > REPORT_YEARS[-1]:
        raise ValueError("Claim year lies beyond the report window.")
    if (
        claimant.claim_origin == "modeled_award"
        and claimant.claim_year not in REPORT_YEARS
    ):
        raise ValueError("A modeled award must have an in-window claim year.")
    provenance_by_year = _career_provenance(claimant.provenance_by_year)
    odd_year_carried_years = _presence_years(claimant.odd_year_carried_years)
    if not odd_year_carried_years:
        odd_year_carried_years = frozenset(
            year
            for year, provenance in provenance_by_year.items()
            if provenance == "projected" and year % 2 == 1
        )
    invalid_odd_years = {
        year
        for year in odd_year_carried_years
        if year not in REPORT_YEARS or year % 2 != 1
    }
    if invalid_odd_years:
        raise ValueError(
            "Odd-year carry diagnostics contain invalid years "
            f"{sorted(invalid_odd_years)}."
        )
    return BenefitClaimant(
        person_id=_person_id(claimant.person_id),
        birth_year=_whole_number(claimant.birth_year, "birth_year"),
        claim_age=_whole_number(claimant.claim_age, "claim_age"),
        claim_year=_whole_number(claimant.claim_year, "claim_year"),
        claim_origin=claimant.claim_origin,
        weight=_finite_number(claimant.weight, "weight"),
        earnings_by_year=_career_earnings(claimant.earnings_by_year),
        presence_years=_presence_years(claimant.presence_years),
        provenance_by_year=provenance_by_year,
        odd_year_carried_years=odd_year_carried_years,
        post_claim_earnings_by_year=_career_earnings(
            claimant.post_claim_earnings_by_year
        ),
    )


def _monthly_benefit_path(
    *,
    adjusted_pia: float,
    eligibility_year: int,
    cola: COLASeries,
) -> dict[int, float]:
    """Apply determination-year COLAs through each payment year.

    The caller has already dime-floored the claim-age-adjusted
    eligibility-year PIA.  Each subsequent COLA operation is independently
    dime-floored.  The loader performs the explicit determination-to-payment
    year conversion around the 1983 transition.
    """

    amount = floor_to_dime(adjusted_pia)
    result = {eligibility_year: amount}
    for payment_year in range(eligibility_year + 1, REPORT_YEARS[-1] + 1):
        determination_year = payment_year - 1
        rate = cola.rate_for_determination_year(determination_year)
        amount = floor_to_dime(amount * (1.0 + rate))
        result[payment_year] = amount
    return result


def _compute_benefit_person(
    claimant: BenefitClaimant,
    parameters: ReportParameters,
) -> BenefitPersonLedger:
    history = {
        year: amount
        for year, amount in claimant.earnings_by_year.items()
        if year <= claimant.claim_year
    }
    aime_value = benefits.aime(history, claimant.birth_year, parameters.ssa)
    eligibility_year = claimant.birth_year + 62
    pia_value = benefits.pia(
        aime_value,
        eligibility_year,
        parameters.ssa,
    )
    factor = claiming.benefit_factor(
        claimant.claim_age * 12,
        claimant.birth_year,
        parameters.ssa,
    )
    adjusted_pia = floor_to_dime(pia_value * factor)
    monthly_path = _monthly_benefit_path(
        adjusted_pia=adjusted_pia,
        eligibility_year=eligibility_year,
        cola=parameters.cola,
    )
    monthly_at_award = monthly_path[claimant.claim_year]
    payments = {
        year: monthly_path[year]
        for year in REPORT_YEARS
        if year >= claimant.claim_year and year in claimant.presence_years
    }
    post_claim_earnings = {
        year: amount
        for source in (
            claimant.earnings_by_year,
            claimant.post_claim_earnings_by_year,
        )
        for year, amount in source.items()
        if year > claimant.claim_year
    }
    positive_post_claim = any(
        amount > 0 for amount in post_claim_earnings.values()
    )
    provenance_counts = {
        provenance: sum(
            value == provenance
            for value in claimant.provenance_by_year.values()
        )
        for provenance in CAREER_PROVENANCE_CLASSES
    }
    provenance_denominator = sum(provenance_counts.values())
    provenance_shares = {
        provenance: (
            count / provenance_denominator
            if provenance_denominator > 0
            else 0.0
        )
        for provenance, count in provenance_counts.items()
    }
    coverage_start = max(1968, claimant.birth_year + 22)
    coverage_end = min(claimant.claim_year, REPORT_YEARS[-1])
    coverage_years = {
        year
        for year in claimant.provenance_by_year
        if coverage_start <= year <= coverage_end
    }
    odd_year_share = (
        len(claimant.odd_year_carried_years & coverage_years)
        / len(coverage_years)
        if coverage_years
        else 0.0
    )
    return BenefitPersonLedger(
        person_id=claimant.person_id,
        birth_year=claimant.birth_year,
        eligibility_year=eligibility_year,
        claim_age=claimant.claim_age,
        claim_year=claimant.claim_year,
        claim_origin=claimant.claim_origin,
        weight=claimant.weight,
        aime=aime_value,
        eligibility_pia=pia_value,
        claim_age_factor=factor,
        adjusted_pia_at_eligibility=adjusted_pia,
        monthly_benefit_at_award=monthly_at_award,
        aime_history_years=tuple(sorted(history)),
        payment_monthly_by_year=payments,
        positive_post_claim_earnings=positive_post_claim,
        post_claim_earnings_years_examined=tuple(sorted(post_claim_earnings)),
        career_provenance_counts=provenance_counts,
        career_provenance_shares=provenance_shares,
        odd_year_carried_year_share=odd_year_share,
    )


def _benefit_row(
    people: Sequence[BenefitPersonLedger],
    origin: str,
    year: int,
) -> BenefitAnnualRow:
    origin_people = [row for row in people if row.claim_origin == origin]
    awards = [
        row
        for row in origin_people
        if origin == "modeled_award" and row.claim_year == year
    ]
    payments = [
        row for row in origin_people if year in row.payment_monthly_by_year
    ]
    award_weight = math.fsum(row.weight for row in awards)
    average_award = _weighted_award_mean(awards, award_weight)
    return BenefitAnnualRow(
        claim_origin=origin,
        year=year,
        unweighted_award_count=len(awards),
        weighted_award_count=award_weight,
        average_monthly_benefit_at_award=average_award,
        unweighted_beneficiary_count=len(payments),
        weighted_beneficiary_count=math.fsum(row.weight for row in payments),
        frame_annualized_benefit=math.fsum(
            12.0 * row.weight * row.payment_monthly_by_year[year]
            for row in payments
        ),
    )


def _benefit_biennial_row(
    people: Sequence[BenefitPersonLedger],
    origin: str,
    end_year: int,
) -> BenefitBiennialRow:
    component_years = (end_year - 1, end_year)
    origin_people = [row for row in people if row.claim_origin == origin]
    awards = [
        row
        for row in origin_people
        if origin == "modeled_award" and row.claim_year in component_years
    ]
    award_weight = math.fsum(row.weight for row in awards)
    annual = {
        row.year: row
        for row in (
            _benefit_row(people, origin, component_years[0]),
            _benefit_row(people, origin, component_years[1]),
        )
    }
    return BenefitBiennialRow(
        claim_origin=origin,
        end_year=end_year,
        component_years=component_years,
        unweighted_award_count=sum(
            annual[year].unweighted_award_count for year in component_years
        ),
        weighted_award_count=award_weight,
        average_monthly_benefit_at_award=_weighted_award_mean(
            awards,
            award_weight,
        ),
        unweighted_beneficiary_count=sum(
            annual[year].unweighted_beneficiary_count
            for year in component_years
        ),
        weighted_beneficiary_count=math.fsum(
            annual[year].weighted_beneficiary_count for year in component_years
        ),
        frame_annualized_benefit=math.fsum(
            annual[year].frame_annualized_benefit for year in component_years
        ),
    )


def _weighted_award_mean(
    awards: Sequence[BenefitPersonLedger],
    total_weight: float,
) -> float | None:
    if not awards:
        return None
    reference = awards[0].monthly_benefit_at_award
    return (
        reference
        + math.fsum(
            row.weight * (row.monthly_benefit_at_award - reference)
            for row in awards
        )
        / total_weight
    )


def build_benefit_ledger(
    included_claimants: Iterable[Any],
    parameters: ReportParameters,
    *,
    draw_index: int,
) -> BenefitLedger:
    """Compute one draw's benefits from Stage-D-included claimants only."""

    draw = _whole_number(draw_index, "draw_index")
    if draw not in DRAW_INDICES:
        raise ValueError(f"draw_index must be one of {DRAW_INDICES}.")
    normalized = tuple(_normalize_claimant(row) for row in included_claimants)
    person_ids = [row.person_id for row in normalized]
    if len(person_ids) != len(set(person_ids)):
        raise ValueError("Benefit claimant input contains duplicate people.")
    people = tuple(
        _compute_benefit_person(row, parameters) for row in normalized
    )
    annual_rows = tuple(
        _benefit_row(people, origin, year)
        for origin in BENEFIT_ORIGINS
        for year in REPORT_YEARS
    )
    biennial_rows = tuple(
        _benefit_biennial_row(people, origin, end_year)
        for origin in BENEFIT_ORIGINS
        for end_year in _BIENNIAL_END_YEARS
    )
    positive = [row for row in people if row.positive_post_claim_earnings]
    diagnostics = {
        "included_claimants_unweighted": float(len(people)),
        "included_claimants_weighted": math.fsum(row.weight for row in people),
        "modeled_award_claimants_unweighted": float(
            sum(row.claim_origin == "modeled_award" for row in people)
        ),
        "modeled_award_claimants_weighted": math.fsum(
            row.weight for row in people if row.claim_origin == "modeled_award"
        ),
        "opening_backfill_claimants_unweighted": float(
            sum(row.claim_origin == "opening_backfill" for row in people)
        ),
        "opening_backfill_claimants_weighted": math.fsum(
            row.weight
            for row in people
            if row.claim_origin == "opening_backfill"
        ),
        "positive_post_claim_earnings_unweighted": float(len(positive)),
        "positive_post_claim_earnings_weighted": math.fsum(
            row.weight for row in positive
        ),
        "award_formula_computation_count": float(
            sum(row.award_formula_computation_count for row in people)
        ),
        "post_claim_recomputation_count": float(
            sum(row.post_claim_recomputation_count for row in people)
        ),
        "realized_payment_person_years_unweighted": float(
            sum(len(row.payment_monthly_by_year) for row in people)
        ),
        "realized_payment_person_years_weighted": math.fsum(
            row.weight * len(row.payment_monthly_by_year) for row in people
        ),
    }
    total_weight = diagnostics["included_claimants_weighted"]
    for provenance in CAREER_PROVENANCE_CLASSES:
        diagnostics[f"career_{provenance}_years_unweighted"] = float(
            sum(row.career_provenance_counts[provenance] for row in people)
        )
        diagnostics[f"career_{provenance}_share_mean_unweighted"] = (
            math.fsum(
                row.career_provenance_shares[provenance] for row in people
            )
            / len(people)
            if people
            else 0.0
        )
        diagnostics[f"career_{provenance}_share_mean_weighted"] = (
            math.fsum(
                row.weight * row.career_provenance_shares[provenance]
                for row in people
            )
            / total_weight
            if total_weight > 0
            else 0.0
        )
    diagnostics["odd_year_carried_share_mean_unweighted"] = (
        math.fsum(row.odd_year_carried_year_share for row in people)
        / len(people)
        if people
        else 0.0
    )
    diagnostics["odd_year_carried_share_mean_weighted"] = (
        math.fsum(
            row.weight * row.odd_year_carried_year_share for row in people
        )
        / total_weight
        if total_weight > 0
        else 0.0
    )
    if diagnostics["post_claim_recomputation_count"] != 0:
        raise AssertionError("Post-claim benefit recomputation is forbidden.")
    return BenefitLedger(
        draw_index=draw,
        people=people,
        annual_rows=annual_rows,
        biennial_rows=biennial_rows,
        diagnostics=diagnostics,
    )


def _projection_person_years(
    projection: Any,
) -> tuple[int, list[dict[str, Any]], Mapping[str, float]]:
    try:
        slices = tuple(projection.slices)
        draw_index = _whole_number(projection.draw_index, "draw_index")
    except AttributeError as error:
        raise TypeError(
            "Revenue production input must be a ProjectionResult-like object "
            "with slices and draw_index; inclusion-filtered rows are not "
            "accepted."
        ) from error
    if draw_index not in DRAW_INDICES:
        raise ValueError(f"draw_index must be one of {DRAW_INDICES}.")
    expected_slice_years = tuple(range(2014, 2023))
    if len(slices) != len(expected_slice_years):
        raise ValueError(
            "Revenue requires the complete 2014-2022 projection slices."
        )

    records: list[dict[str, Any]] = []
    weights_by_person: dict[int | str, float] = {}
    missing_earnings_count = 0
    missing_earnings_weight = 0.0
    for expected_year, frame in zip(
        expected_slice_years,
        slices,
        strict=True,
    ):
        required = {"person_id", "year", "earnings", "weight"}
        columns = set(getattr(frame, "columns", ()))
        missing = required - columns
        if missing:
            raise ValueError(
                f"Projection slice {expected_year} lacks {sorted(missing)}."
            )
        if bool(frame["person_id"].duplicated().any()):
            raise ValueError(
                f"Projection slice {expected_year} has duplicate people."
            )
        if not frame.empty:
            observed_years = {
                _whole_number(value, "projection year")
                for value in frame["year"].tolist()
            }
            if observed_years != {expected_year}:
                raise ValueError(
                    f"Projection slice {expected_year} carries years "
                    f"{sorted(observed_years)}."
                )
        for raw in frame.loc[
            :, ["person_id", "year", "earnings", "weight"]
        ].to_dict("records"):
            person_id = _person_id(raw["person_id"])
            year = _whole_number(raw["year"], "projection year")
            weight = _finite_number(raw["weight"], "projection weight")
            if weight <= 0:
                raise ValueError("Projection weights must be positive.")
            prior_weight = weights_by_person.setdefault(person_id, weight)
            if not math.isclose(
                prior_weight,
                weight,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"Person {person_id!r} does not retain a fixed weight."
                )
            if bool(pd.isna(raw["earnings"])):
                if year in REPORT_YEARS:
                    missing_earnings_count += 1
                    missing_earnings_weight += weight
                continue
            earnings = _finite_number(raw["earnings"], "projected earnings")
            if year in REPORT_YEARS:
                records.append(
                    {
                        "person_id": person_id,
                        "year": year,
                        "earnings": earnings,
                        "weight": weight,
                    }
                )
    return (
        draw_index,
        records,
        {
            "projection_rows_missing_earnings_unweighted": float(
                missing_earnings_count
            ),
            "projection_rows_missing_earnings_weighted": (
                missing_earnings_weight
            ),
        },
    )


def _revenue_annual_row(
    records: Sequence[Mapping[str, Any]],
    year: int,
    parameters: ReportParameters,
) -> RevenueAnnualRow:
    rows = [row for row in records if row["year"] == year]
    wage_base = parameters.ssa.wage_base_for(year)
    employee_rate = parameters.rates.employee_for(year)
    employer_rate = parameters.rates.employer_for(year)
    combined_rate = parameters.rates.combined_for(year)
    if not math.isclose(
        employee_rate + employer_rate,
        combined_rate,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise AssertionError("The OASDI rate legs do not add to combined.")

    weighted_taxable = []
    employee = []
    employer = []
    combined = []
    for row in rows:
        taxable = min(float(row["earnings"]), wage_base)
        weighted = float(row["weight"]) * taxable
        weighted_taxable.append(weighted)
        employee.append(weighted * employee_rate)
        employer.append(weighted * employer_rate)
        combined.append(weighted * combined_rate)
    return RevenueAnnualRow(
        year=year,
        unweighted_person_year_count=len(rows),
        weighted_person_year_count=math.fsum(
            float(row["weight"]) for row in rows
        ),
        unweighted_covered_earner_count=sum(
            float(row["earnings"]) > 0 for row in rows
        ),
        weighted_covered_earner_count=math.fsum(
            float(row["weight"]) for row in rows if float(row["earnings"]) > 0
        ),
        weighted_taxable_payroll=math.fsum(weighted_taxable),
        employee_contributions=math.fsum(employee),
        employer_contributions=math.fsum(employer),
        combined_contributions=math.fsum(combined),
        odd_year_carry_affected=year % 2 == 1,
    )


def _revenue_biennial_row(
    annual_by_year: Mapping[int, RevenueAnnualRow],
    end_year: int,
) -> RevenueBiennialRow:
    component_years = (end_year - 1, end_year)
    first, second = (annual_by_year[year] for year in component_years)
    return RevenueBiennialRow(
        end_year=end_year,
        component_years=component_years,
        unweighted_person_year_count=(
            first.unweighted_person_year_count
            + second.unweighted_person_year_count
        ),
        weighted_person_year_count=(
            first.weighted_person_year_count
            + second.weighted_person_year_count
        ),
        unweighted_covered_earner_count=(
            first.unweighted_covered_earner_count
            + second.unweighted_covered_earner_count
        ),
        weighted_covered_earner_count=(
            first.weighted_covered_earner_count
            + second.weighted_covered_earner_count
        ),
        weighted_taxable_payroll=(
            first.weighted_taxable_payroll + second.weighted_taxable_payroll
        ),
        employee_contributions=(
            first.employee_contributions + second.employee_contributions
        ),
        employer_contributions=(
            first.employer_contributions + second.employer_contributions
        ),
        combined_contributions=(
            first.combined_contributions + second.combined_contributions
        ),
        odd_year_carry_pair_interpretation=(
            f"{component_years[0]} carries "
            f"{component_years[0] - 1} earnings; "
            f"{component_years[1]} is the newly drawn even year."
        ),
    )


def _safe_share(numerator: float, denominator: float) -> float:
    if denominator == 0:
        if numerator != 0:
            raise AssertionError("A zero total cannot have a nonzero part.")
        return 0.0
    return numerator / denominator


def build_revenue_ledger(
    projection: Any,
    parameters: ReportParameters,
) -> RevenueLedger:
    """Compute nominal revenue over all unsplit projected person-years."""

    draw_index, records, missing_diagnostics = _projection_person_years(
        projection
    )
    annual_rows = tuple(
        _revenue_annual_row(records, year, parameters) for year in REPORT_YEARS
    )
    annual_by_year = {row.year: row for row in annual_rows}
    biennial_rows = tuple(
        _revenue_biennial_row(annual_by_year, end_year)
        for end_year in _BIENNIAL_END_YEARS
    )

    totals = {
        metric: math.fsum(float(getattr(row, metric)) for row in annual_rows)
        for metric in _REVENUE_ROW_METRICS
    }
    odd_totals = {
        metric: math.fsum(
            float(getattr(row, metric))
            for row in annual_rows
            if row.odd_year_carry_affected
        )
        for metric in _REVENUE_ROW_METRICS
    }
    diagnostics: dict[str, float] = {
        "explicit_earnings_person_years_unweighted": totals[
            "unweighted_person_year_count"
        ],
        "explicit_earnings_person_years_weighted": totals[
            "weighted_person_year_count"
        ],
        **missing_diagnostics,
    }
    for metric in _REVENUE_ROW_METRICS:
        diagnostics[f"odd_year_carry_share__{metric}"] = _safe_share(
            odd_totals[metric],
            totals[metric],
        )
    return RevenueLedger(
        draw_index=draw_index,
        annual_rows=annual_rows,
        biennial_rows=biennial_rows,
        diagnostics=diagnostics,
    )


def _summary(values: Sequence[float | None]) -> AcrossDrawMetric:
    observed = [
        _finite_number(value, "across-draw value")
        for value in values
        if value is not None
    ]
    if not observed:
        return AcrossDrawMetric(
            n_draws=len(values),
            n_observations=0,
            mean=None,
            sample_sd=None,
        )
    mean = math.fsum(observed) / len(observed)
    sample_sd = None
    if len(observed) >= 2:
        sample_sd = math.sqrt(
            math.fsum((value - mean) ** 2 for value in observed)
            / (len(observed) - 1)
        )
    return AcrossDrawMetric(
        n_draws=len(values),
        n_observations=len(observed),
        mean=mean,
        sample_sd=sample_sd,
    )


def _validate_draw_set(ledgers: Sequence[Any]) -> tuple[Any, ...]:
    rows = tuple(ledgers)
    observed = tuple(sorted(row.draw_index for row in rows))
    if observed != DRAW_INDICES:
        raise ValueError(
            f"Across-draw aggregation requires draw indices {DRAW_INDICES}; "
            f"received {observed}."
        )
    return tuple(sorted(rows, key=lambda row: row.draw_index))


def _aggregate_rows(
    draws: Sequence[Any],
    *,
    row_attribute: str,
    dimension_fields: tuple[str, ...],
    metric_fields: tuple[str, ...],
) -> tuple[AcrossDrawTableRow, ...]:
    indexed: list[dict[tuple[Any, ...], Any]] = []
    for draw in draws:
        by_key: dict[tuple[Any, ...], Any] = {}
        for row in getattr(draw, row_attribute):
            key = tuple(getattr(row, name) for name in dimension_fields)
            if key in by_key:
                raise ValueError(f"Duplicate table row dimensions {key!r}.")
            by_key[key] = row
        indexed.append(by_key)
    expected_keys = set(indexed[0])
    if any(set(rows) != expected_keys for rows in indexed[1:]):
        raise ValueError(
            f"{row_attribute} dimension grids differ across draws."
        )

    result = []
    for key in sorted(expected_keys):
        dimensions = dict(zip(dimension_fields, key, strict=True))
        metrics = {
            metric: _summary([getattr(rows[key], metric) for rows in indexed])
            for metric in metric_fields
        }
        result.append(
            AcrossDrawTableRow(dimensions=dimensions, metrics=metrics)
        )
    return tuple(result)


def _aggregate_diagnostics(
    draws: Sequence[Any],
) -> Mapping[str, AcrossDrawMetric]:
    expected = set(draws[0].diagnostics)
    if any(set(draw.diagnostics) != expected for draw in draws[1:]):
        raise ValueError("Diagnostic keys differ across draws.")
    return {
        key: _summary([draw.diagnostics[key] for draw in draws])
        for key in sorted(expected)
    }


def aggregate_benefit_draws(
    ledgers: Sequence[BenefitLedger],
) -> AcrossDrawLedgers:
    """Aggregate the exact registered 20 benefit draws using sample SD."""

    draws = _validate_draw_set(ledgers)
    return AcrossDrawLedgers(
        draw_indices=DRAW_INDICES,
        annual_rows=_aggregate_rows(
            draws,
            row_attribute="annual_rows",
            dimension_fields=("claim_origin", "year"),
            metric_fields=_BENEFIT_ROW_METRICS,
        ),
        biennial_rows=_aggregate_rows(
            draws,
            row_attribute="biennial_rows",
            dimension_fields=("claim_origin", "end_year", "component_years"),
            metric_fields=_BENEFIT_ROW_METRICS,
        ),
        diagnostics=_aggregate_diagnostics(draws),
    )


def aggregate_revenue_draws(
    ledgers: Sequence[RevenueLedger],
) -> AcrossDrawLedgers:
    """Aggregate the exact registered 20 revenue draws using sample SD."""

    draws = _validate_draw_set(ledgers)
    return AcrossDrawLedgers(
        draw_indices=DRAW_INDICES,
        annual_rows=_aggregate_rows(
            draws,
            row_attribute="annual_rows",
            dimension_fields=("year",),
            metric_fields=_REVENUE_ROW_METRICS,
        ),
        biennial_rows=_aggregate_rows(
            draws,
            row_attribute="biennial_rows",
            dimension_fields=("end_year", "component_years"),
            metric_fields=_REVENUE_ROW_METRICS,
        ),
        diagnostics=_aggregate_diagnostics(draws),
    )


# Keep dataclass field declarations and aggregation metric lists synchronized.
if tuple(field.name for field in fields(BenefitAnnualRow))[2:] != (
    _BENEFIT_ROW_METRICS
):
    raise AssertionError("Benefit annual aggregation metrics drifted.")
if tuple(field.name for field in fields(RevenueAnnualRow))[1:-1] != (
    _REVENUE_ROW_METRICS
):
    raise AssertionError("Revenue annual aggregation metrics drifted.")
