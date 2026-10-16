"""R3 automatic earnings recomputation: a Python statutory reference.

Verification class: statutory conformance. Admitted scope: ordinary AIME
retirement recomputations for eligibility from 1983, including death-year
earnings after FRA, over invented cases and captured SSA examples. There
is no population, behavioral, forecast, administrative-payment-date or
family-payment claim. Monthly assembly must independently apply G and
R2 to the resulting PIA and retain refusals in every denominator.

42 U.S.C. 415(f)(2)(B)-(C) freezes the original indexing year, computation
year count and benefit formula. Base years extend through the earnings
year, and later earnings cannot enter an earlier recomputation. The AIME
adapter calls ss.statutory_aime.aime_with_computation_years, after requiring
every base year's earnings explicitly, including explicit zeros. Because
that oracle casts earnings to binary floats, the adapter also checks its
floor against exact Fraction indexing and corrects a binary boundary
disagreement; no formula or year-selection convention is changed.

PIA arithmetic is exact 90/32/15 percent, dime-floored (415(a)(1), (i)).
Each COLA is dime-floored using G's helper. RS 00605.501A settles the $1
rule of 415(f)(4): compare the actual PIAs AFTER every COLA through the
effective month, never whole-dollar benefits or eligibility-year PIAs.
Ordinary effectiveness is January following the earnings year; death-year
earnings take effect in the month of death (415(f)(2)(D), CFR 404.282).
The December processing described in Publication 05-10069 is not an
effective date and is outside this module.

The caller supplies the established original basis, the eligibility-level
PIA then in force, complete earnings and COLA histories, and entitlement
and death/FRA months. Original insured status and entitlement are supplied
and assumed; this arithmetic does not establish insured status or quarters
of coverage. A chronological sequence is a fold: a sub-$1
candidate never replaces the PIA of record; later years compare against
the last accepted PIA. A year without earnings cannot trigger a delayed
sub-$1 recomputation (RS 00605.501A).

Unsupported configurations raise RecomputationConfigurationUnsupported,
within the shared FamilyConfigurationUnsupported family, with exactly
RecomputationUnsupportedReason. A package-private capability seals decisions,
results, refusals and outcomes; direct construction, replacement and copying
are invalid, and pickle restoration repeats identity validation. Evaluators
and PIA aggregates require unchanged recomputation results. The shared
counter admits every sealed layer outcome and keeps all refused weights.
Invalid inputs are validated before coverage refusals.
History and required-parameter validation precede every coverage check;
ordinary AIME indexing, selection and PIA arithmetic run only after it.
Pre-1983 eligibility, other PIA formulas, DIB/freeze/prior DIB, WEP before
2024, administrative finality, waived/disadvantageous recomputations,
special credits and death before FRA under 415(f)(5) are explicitly
refused. No unavailable year is silently treated as zero.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction

from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import aime_with_computation_years
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    FamilyTargetBlocked,
    InvalidFamilyInput,
    YearMonth,
    _check_evaluation_inputs,
    _outcome_weight,
    count_family_outcomes,
    floor_dime,
    increase_by_colas,
)

from ._provenance import (
    _check_refusal,
    _check_seal,
    _checked_result,
    _computed,
    _sealed_refusal,
    _sealed_result,
    _SealedOutcome,
    _SealedResult,
)

__all__ = [
    "UNAVAILABLE",
    "PIAFormula",
    "RecomputationBasis",
    "RecomputationCondition",
    "RecomputationConfigurationUnsupported",
    "RecomputationDecision",
    "RecomputationResult",
    "RecomputationOutcome",
    "RecomputationUnsupportedReason",
    "annual_recomputation",
    "earnings_aime",
    "evaluate_recomputation",
    "eligibility_bend_points",
    "exact_pia",
    "recomputation_decision",
    "recompute_sequence",
    "weighted_recomputed_pia",
]


class EarningsAvailability(Enum):
    """An unavailable amount is distinct from an explicitly observed zero."""

    UNAVAILABLE = "unavailable"


UNAVAILABLE = EarningsAvailability.UNAVAILABLE


class PIAFormula(str, Enum):
    AIME = "aime"
    AMW = "average_monthly_wage"
    OLD_START = "old_start"
    SPECIAL_MINIMUM = "special_minimum"
    FROZEN_MINIMUM = "frozen_minimum"
    GUARANTEE = "guarantee"


class RecomputationCondition(str, Enum):
    DISABILITY_ENTITLEMENT = "disability_entitlement"
    DISABILITY_FREEZE = "disability_freeze"
    PRIOR_DISABILITY = "prior_disability"
    WEP_BEFORE_2024 = "wep_before_2024"
    ADMINISTRATIVE_FINALITY = "administrative_finality"
    WAIVED_OR_DISADVANTAGEOUS = "waived_or_disadvantageous"
    SPECIAL_EARNINGS_CREDITS = "special_earnings_credits"


class RecomputationUnsupportedReason(str, Enum):
    ELIGIBILITY_BEFORE_1983 = "recompute_eligibility_before_1983"
    NON_AIME_FORMULA_PIA = "recompute_non_aime_formula_pia"
    DISABILITY_ENTITLEMENT = "recompute_disability_entitlement"
    DISABILITY_FREEZE = "recompute_disability_freeze"
    PRIOR_DISABILITY = "recompute_prior_disability"
    WEP_BEFORE_2024 = "recompute_wep_before_2024"
    ADMINISTRATIVE_FINALITY = "recompute_administrative_finality"
    WAIVED_OR_DISADVANTAGEOUS = "recompute_waived_or_disadvantageous"
    SPECIAL_EARNINGS_CREDITS = "recompute_special_earnings_credits"
    DEATH_BEFORE_FRA = "recompute_death_before_fra_415f5"


@_sealed_refusal(RecomputationUnsupportedReason)
class RecomputationConfigurationUnsupported(FamilyConfigurationUnsupported):
    """A sealed recomputation refusal with exactly its layer's reason enum."""


def _year(value: object, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 9999:
        raise InvalidFamilyInput(f"{label} must be an integer year 1-9999")
    return value


def _exact(value: object, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(
        value, (int, str, Decimal, Fraction)
    ):
        raise InvalidFamilyInput(f"{label} requires an exact number")
    try:
        amount = Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise InvalidFamilyInput(f"{label} requires a finite number") from exc
    if amount < 0:
        raise InvalidFamilyInput(f"{label} must be nonnegative")
    return amount


def _dimes(value: object, label: str) -> Fraction:
    amount = _exact(value, label)
    if (amount * 10).denominator != 1:
        raise InvalidFamilyInput(f"{label} must be a multiple of $0.10")
    return amount


def _month(value: object, label: str) -> YearMonth:
    if type(value) is not YearMonth:
        raise InvalidFamilyInput(f"{label} must be a YearMonth")
    try:
        return YearMonth(value.year, value.month)
    except (AttributeError, TypeError, ValueError) as error:
        raise InvalidFamilyInput(f"{label}: {error}") from error


def _bend_points(values: object) -> tuple[int, int]:
    if not isinstance(values, tuple) or len(values) != 2:
        raise InvalidFamilyInput("bend_points must be a pair")
    first, second = values
    if (
        type(first) is not int
        or type(second) is not int
        or not 0 < first < second
    ):
        raise InvalidFamilyInput(
            "bend points must be increasing whole dollars"
        )
    return first, second


@dataclass(frozen=True)
class RecomputationBasis:
    """Original, established 415 computation factors; never derived anew.

    ``first_base_year`` is 1951 for the ordinary AIME cases supported here.
    Every year through the earnings cutoff must be explicitly reported.
    The entitlement window is continuous; interruption cases require
    their own adapter. Conditions are frozen once at construction,
    including when supplied as a one-shot iterator.
    """

    eligibility_year: int
    indexing_year: int
    computation_years: int
    bend_points: tuple[int, int]
    entitlement_month: YearMonth
    first_base_year: int = 1951
    entitlement_end_month: YearMonth | None = None
    formula: PIAFormula = PIAFormula.AIME
    conditions: frozenset[RecomputationCondition] = frozenset()

    def __post_init__(self):
        _year(self.eligibility_year, "eligibility_year")
        _year(self.indexing_year, "indexing_year")
        _year(self.first_base_year, "first_base_year")
        if self.first_base_year != 1951:
            raise InvalidFamilyInput("ordinary AIME base years begin in 1951")
        if self.indexing_year != self.eligibility_year - 2:
            raise InvalidFamilyInput("original indexing year must be ELY - 2")
        if (
            type(self.computation_years) is not int
            or not 2 <= self.computation_years <= 35
        ):
            raise InvalidFamilyInput("computation_years must be 2-35")
        _bend_points(self.bend_points)
        _month(self.entitlement_month, "entitlement_month")
        if self.entitlement_month.year < self.eligibility_year:
            raise InvalidFamilyInput("entitlement cannot precede eligibility")
        if self.first_base_year >= self.entitlement_month.year:
            raise InvalidFamilyInput(
                "original base period must precede entitlement"
            )
        if self.computation_years > self.entitlement_month.year - 1951:
            raise InvalidFamilyInput(
                "computation count exceeds original base period"
            )
        if self.entitlement_end_month is not None:
            _month(self.entitlement_end_month, "entitlement_end_month")
            if self.entitlement_end_month < self.entitlement_month:
                raise InvalidFamilyInput(
                    "entitlement end precedes entitlement"
                )
        if not isinstance(self.formula, PIAFormula):
            raise InvalidFamilyInput("formula must be a PIAFormula")
        try:
            conditions = frozenset(self.conditions)
        except TypeError as exc:
            raise InvalidFamilyInput(
                "conditions must be a collection"
            ) from exc
        if any(not isinstance(c, RecomputationCondition) for c in conditions):
            raise InvalidFamilyInput("unknown recomputation condition")
        object.__setattr__(self, "conditions", conditions)


@_sealed_result
@dataclass(frozen=True)
class RecomputationDecision(_SealedResult):
    """Threshold comparison at the effective-month PIA level, not checks."""

    pia_of_record: Fraction
    candidate_pia: Fraction
    increase: Fraction
    applied: bool
    pia_in_force: Fraction
    has_earnings: bool = True

    def __post_init__(self):
        old = _dimes(self.pia_of_record, "PIA of record")
        candidate = _dimes(self.candidate_pia, "candidate PIA")
        if (
            type(self.has_earnings) is not bool
            or type(self.applied) is not bool
        ):
            raise InvalidFamilyInput(
                "recomputation decision flags must be bools"
            )
        increase = candidate - old
        applied = self.has_earnings and increase >= 1
        if (
            self.increase != increase
            or self.applied != applied
            or _dimes(self.pia_in_force, "PIA in force")
            != (candidate if applied else old)
        ):
            raise InvalidFamilyInput(
                "recomputation threshold identities disagree"
            )


@_sealed_result
@dataclass(frozen=True)
class RecomputationResult(_SealedResult):
    earnings_year: int
    effective_month: YearMonth
    aime: int
    candidate_eligibility_pia: Fraction
    eligibility_pia_in_force: Fraction
    decision: RecomputationDecision

    def __post_init__(self):
        _year(self.earnings_year, "earnings_year")
        effective = _month(self.effective_month, "effective_month")
        if not (
            effective.year == self.earnings_year
            or effective == YearMonth(self.earnings_year + 1, 1)
        ):
            raise InvalidFamilyInput(
                "recomputation effective month disagrees with earnings year"
            )
        if type(self.aime) is not int or self.aime < 0:
            raise InvalidFamilyInput("AIME must be nonnegative whole dollars")
        candidate = _dimes(
            self.candidate_eligibility_pia, "candidate eligibility PIA"
        )
        current = _dimes(
            self.eligibility_pia_in_force, "eligibility PIA in force"
        )
        decision = _checked_result(
            self.decision, RecomputationDecision, "decision"
        )
        if decision.applied and candidate != current:
            raise InvalidFamilyInput(
                "accepted eligibility PIA differs from candidate"
            )
        if (
            candidate > decision.candidate_pia
            or current > decision.pia_in_force
        ):
            raise InvalidFamilyInput(
                "nonnegative COLAs cannot lower eligibility PIAs"
            )


@_sealed_result
@dataclass(frozen=True)
class RecomputationOutcome(_SealedOutcome):
    """An earnings-year row retained for G's common denominator counter."""

    key: str
    weight: Fraction
    result: RecomputationResult | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _check_evaluation_inputs(self.key, self.weight, lambda: None)
        if (self.result is None) == (self.unsupported is None):
            raise InvalidFamilyInput("exactly one result/refusal is required")
        if self.result is not None:
            _checked_result(
                self.result, RecomputationResult, "recomputation result"
            )
        if self.unsupported is not None:
            _check_refusal(self.unsupported)
        object.__setattr__(self, "weight", _outcome_weight(self.weight))

    @property
    def supported(self) -> bool:
        _check_seal(self)
        return self.result is not None


def evaluate_recomputation(
    key: str,
    weight: object,
    compute: Callable[[], RecomputationResult],
) -> RecomputationOutcome:
    """Catch coverage only; input errors never become denominator gaps."""
    _check_evaluation_inputs(key, weight, compute)
    checked_weight = _outcome_weight(weight)
    try:
        result = compute()
    except FamilyConfigurationUnsupported as error:
        return _computed(
            RecomputationOutcome,
            key,
            checked_weight,
            None,
            _check_refusal(error),
        )
    _checked_result(result, RecomputationResult, "recomputation result")
    return _computed(RecomputationOutcome, key, checked_weight, result, None)


def weighted_recomputed_pia(
    outcomes: Iterable[RecomputationOutcome],
) -> Fraction:
    """PIA aggregate over all rows, blocked when any row was refused."""
    rows = tuple(outcomes)
    for row in rows:
        _checked_result(row, RecomputationOutcome, "recomputation outcome")
    counts = count_family_outcomes(rows)
    if counts.unsupported_rows:
        raise FamilyTargetBlocked(
            f"{counts.unsupported_rows} of {counts.rows} recomputations are "
            "FAMILY_CONFIG_UNSUPPORTED; the PIA target requires them"
        )
    return sum(
        (row.weight * row.result.decision.pia_in_force for row in rows),
        Fraction(0),
    )


def eligibility_bend_points(
    eligibility_year: int, params: SSAParameters
) -> tuple[int, int]:
    """415(a)(1)(B): NAWI-scaled $180/$1,085, $0.50 ties upward.

    Call once when constructing the original basis. Oracle bend_points
    uses Python's ties-to-even ``round``; the statutory half-dollar case
    is an intended divergence, pinned explicitly by a test.
    """
    _year(eligibility_year, "eligibility_year")
    try:
        index = Fraction(str(params.nawi[eligibility_year - 2]))
        base = Fraction(str(params.nawi[1977]))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        raise InvalidFamilyInput("required NAWI is unavailable") from exc
    if index <= 0 or base <= 0:
        raise InvalidFamilyInput("NAWI must be positive")
    return tuple(
        math.floor(v * index / base + Fraction(1, 2)) for v in (180, 1085)
    )


def exact_pia(aime: int, bend_points: tuple[int, int]) -> Fraction:
    """415(a)(1): original 90/32/15 formula, dime-floored exactly."""
    if type(aime) is not int or aime < 0:
        raise InvalidFamilyInput("AIME must be nonnegative whole dollars")
    first, second = _bend_points(bend_points)
    amount = (
        Fraction(9, 10) * min(aime, first)
        + Fraction(8, 25) * max(0, min(aime, second) - first)
        + Fraction(3, 20) * max(0, aime - second)
    )
    return floor_dime(amount)


def _history_prefix(
    history: Mapping[int, object], basis: RecomputationBasis, year: int
) -> dict[int, Fraction]:
    if not isinstance(history, Mapping):
        raise InvalidFamilyInput("earnings history must be a mapping")
    for key in history:
        _year(key, "earnings year")
    values = {}
    for base_year in range(basis.first_base_year, year + 1):
        if base_year not in history or history[base_year] is UNAVAILABLE:
            raise InvalidFamilyInput(f"earnings unavailable for {base_year}")
        values[base_year] = _exact(history[base_year], f"earnings {base_year}")
    return values


def _aime_parameters(
    prefix: Mapping[int, Fraction],
    basis: RecomputationBasis,
    params: SSAParameters,
) -> tuple[dict[int, Fraction], dict[int, Fraction]]:
    """Check availability and positivity without computing any earnings."""
    try:
        nawi = {
            basis.indexing_year: Fraction(
                str(params.nawi[basis.indexing_year])
            )
        }
        if nawi[basis.indexing_year] <= 0:
            raise InvalidFamilyInput("NAWI must be positive")
        wage_base = {}
        for year in prefix:
            wage_base[year] = Fraction(str(params.wage_base_for(year)))
            if wage_base[year] <= 0:
                raise InvalidFamilyInput("wage base must be positive")
            if year < basis.indexing_year:
                nawi[year] = Fraction(str(params.nawi[year]))
                if nawi[year] <= 0:
                    raise InvalidFamilyInput("NAWI must be positive")
    except (
        KeyError,
        TypeError,
        ValueError,
        ZeroDivisionError,
        OverflowError,
    ) as exc:
        raise InvalidFamilyInput(
            "required AIME parameter is unavailable or invalid"
        ) from exc
    return nawi, wage_base


def _aime_from_prefix(
    prefix: Mapping[int, Fraction],
    basis: RecomputationBasis,
    params: SSAParameters,
    checked_parameters: tuple[dict[int, Fraction], dict[int, Fraction]],
) -> int:
    """Reuse statutory AIME, guarding the float oracle's integer boundary."""
    nawi, wage_base = checked_parameters
    try:
        indexed = []
        capped = {}
        for year, earnings in prefix.items():
            amount = min(earnings, wage_base[year])
            capped[year] = amount
            if year < basis.indexing_year:
                amount *= nawi[basis.indexing_year] / nawi[year]
            indexed.append(amount)
        top = sorted(indexed, reverse=True)[: basis.computation_years]
        exact = math.floor(sum(top) / (12 * basis.computation_years))
        # Cap exactly before the float adapter: even a finite Fraction
        # above float range must receive the statutory contribution cap.
        reference = aime_with_computation_years(
            capped,
            basis.computation_years,
            params,
            indexing_year=basis.indexing_year,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        ZeroDivisionError,
        OverflowError,
    ) as exc:
        raise InvalidFamilyInput(
            "required AIME parameter is unavailable or invalid"
        ) from exc
    return reference if reference == exact else exact


def earnings_aime(
    history: Mapping[int, object],
    basis: RecomputationBasis,
    earnings_year: int,
    params: SSAParameters,
) -> int:
    """Complete explicit prefix to AIME, retaining original index/count."""
    _year(earnings_year, "earnings_year")
    if not isinstance(basis, RecomputationBasis):
        raise InvalidFamilyInput("basis must be a RecomputationBasis")
    if earnings_year < basis.first_base_year:
        raise InvalidFamilyInput("earnings cutoff precedes the base period")
    prefix = _history_prefix(history, basis, earnings_year)
    return _aime_from_prefix(
        prefix, basis, params, _aime_parameters(prefix, basis, params)
    )


def recomputation_decision(
    pia_of_record: object, candidate_pia: object, *, has_earnings: bool = True
) -> RecomputationDecision:
    """RS 00605.501A: at least $1 AFTER COLAs and only with earnings."""
    old = _dimes(pia_of_record, "PIA of record")
    candidate = _dimes(candidate_pia, "candidate PIA")
    if type(has_earnings) is not bool:
        raise InvalidFamilyInput("has_earnings must be a bool")
    increase = candidate - old
    applied = has_earnings and increase >= 1
    return _computed(
        RecomputationDecision,
        old,
        candidate,
        increase,
        applied,
        candidate if applied else old,
        has_earnings,
    )


def _colas(
    history: Mapping[int, object], eligibility_year: int, month: YearMonth
) -> tuple[Fraction, ...]:
    if not isinstance(history, Mapping):
        raise InvalidFamilyInput("COLA history must be a mapping")
    for key in history:
        _year(key, "COLA year")
    last = month.year - (month.month != 12)
    values = []
    for year in range(eligibility_year, last + 1):
        if year not in history or history[year] is UNAVAILABLE:
            raise InvalidFamilyInput(f"COLA unavailable for December {year}")
        values.append(_exact(history[year], f"COLA {year}"))
    return tuple(values)


def _require_coverage(
    basis: RecomputationBasis,
    death_month: YearMonth | None,
    fra_month: YearMonth | None,
) -> None:
    reason = None
    if basis.eligibility_year < 1983:
        reason = RecomputationUnsupportedReason.ELIGIBILITY_BEFORE_1983
    elif basis.formula is not PIAFormula.AIME:
        reason = RecomputationUnsupportedReason.NON_AIME_FORMULA_PIA
    elif basis.conditions:
        condition = sorted(basis.conditions, key=lambda c: c.value)[0]
        reason = RecomputationUnsupportedReason[condition.name]
    elif death_month is not None and death_month < fra_month:
        reason = RecomputationUnsupportedReason.DEATH_BEFORE_FRA
    if reason is not None:
        raise _computed(
            RecomputationConfigurationUnsupported,
            reason,
            "Original AIME RIB recomputation only; see R3 coverage table",
        )


def _validate_original_computation_count(basis: RecomputationBasis) -> None:
    """415(b)(2): ordinary RIB's original count follows eligibility."""
    # 415(b)(2)(A), (B)(iii): elapsed years start after1950 (or age21),
    # end before age62; deduct5, with40 elapsed/35 computed at most.
    # ELY1956 is1951+5. Prior-DIB exceptions require their own basis.
    if (
        basis.eligibility_year >= 1983
        and basis.formula is PIAFormula.AIME
        and not basis.conditions
        and basis.computation_years
        != max(2, min(35, basis.eligibility_year - 1956))
    ):
        raise InvalidFamilyInput(
            "original ordinary RIB computation count disagrees with eligibility year"
        )


def annual_recomputation(
    basis: RecomputationBasis,
    history: Mapping[int, object],
    earnings_year: int,
    eligibility_pia_of_record: object,
    params: SSAParameters,
    december_cola_percent: Mapping[int, object],
    *,
    death_month: YearMonth | None = None,
    fra_month: YearMonth | None = None,
) -> RecomputationResult:
    """415(f)(2): one earnings year; January next year or death month.

    ``eligibility_pia_of_record`` is the eligibility-level amount last
    accepted, before COLAs. Complete history and parameter validation
    precede coverage refusal; no ordinary AIME or PIA is calculated for
    refused cases.
    Death-year input requires FRA so 415(f)(5) cannot be bypassed.
    """
    if not isinstance(basis, RecomputationBasis):
        raise InvalidFamilyInput("basis must be a RecomputationBasis")
    year = _year(earnings_year, "earnings_year")
    old_base = _dimes(eligibility_pia_of_record, "eligibility PIA of record")
    if year < basis.entitlement_month.year:
        raise InvalidFamilyInput(
            "recomputation year must be within entitlement"
        )
    if (
        basis.entitlement_end_month is not None
        and year > basis.entitlement_end_month.year
    ):
        raise InvalidFamilyInput("no entitlement in recomputation year")
    if year == 9999:
        raise InvalidFamilyInput(
            "next-year effective month is unrepresentable"
        )
    if fra_month is not None:
        _month(fra_month, "fra_month")
        if fra_month.year < basis.eligibility_year:
            raise InvalidFamilyInput("FRA precedes eligibility")
    if death_month is not None:
        _month(death_month, "death_month")
        if death_month < basis.entitlement_month or year > death_month.year:
            raise InvalidFamilyInput(
                "death or earnings year contradicts entitlement"
            )
        if fra_month is None:
            raise InvalidFamilyInput(
                "death-year processing requires FRA month"
            )
    effective = (
        death_month
        if death_month is not None and death_month.year == year
        else YearMonth(year + 1, 1)
    )
    prefix = _history_prefix(history, basis, year)
    colas = _colas(december_cola_percent, basis.eligibility_year, effective)
    checked_parameters = _aime_parameters(prefix, basis, params)
    _validate_original_computation_count(basis)
    _require_coverage(
        basis,
        (
            death_month
            if death_month is not None and death_month.year == year
            else None
        ),
        fra_month,
    )
    aime = _aime_from_prefix(prefix, basis, params, checked_parameters)
    candidate_base = exact_pia(aime, basis.bend_points)
    decision = recomputation_decision(
        increase_by_colas(old_base, colas),
        increase_by_colas(candidate_base, colas),
        has_earnings=prefix[year] > 0,
    )
    return _computed(
        RecomputationResult,
        year,
        effective,
        aime,
        candidate_base,
        candidate_base if decision.applied else old_base,
        decision,
    )


def recompute_sequence(
    basis: RecomputationBasis,
    history: Mapping[int, object],
    earnings_years: Sequence[int],
    eligibility_pia_of_record: object,
    params: SSAParameters,
    december_cola_percent: Mapping[int, object],
    *,
    death_month: YearMonth | None = None,
    fra_month: YearMonth | None = None,
) -> tuple[RecomputationResult, ...]:
    """Chronological annual fold, carrying only an accepted base PIA.

    Validate all required earnings, COLAs and parameters before entering
    a fold that can refuse coverage, so a later input error is never
    counted as a gap. Validation performs no ordinary AIME or PIA
    calculation. A refusal in any required earnings year blocks the
    entire sequence before its first arithmetic step.
    """
    if not isinstance(basis, RecomputationBasis):
        raise InvalidFamilyInput("basis must be a RecomputationBasis")
    try:
        years = tuple(earnings_years)
    except TypeError as exc:
        raise InvalidFamilyInput("earnings_years must be a sequence") from exc
    for year in years:
        _year(year, "earnings_year")
    if years != tuple(sorted(set(years))):
        raise InvalidFamilyInput("recomputation years must increase strictly")
    current = _dimes(eligibility_pia_of_record, "eligibility PIA of record")
    for year in years:
        if year < basis.entitlement_month.year or year == 9999:
            raise InvalidFamilyInput("invalid recomputation year in fold")
        if (
            basis.entitlement_end_month is not None
            and year > basis.entitlement_end_month.year
        ):
            raise InvalidFamilyInput("no entitlement in recomputation year")
    if fra_month is not None:
        _month(fra_month, "fra_month")
        if fra_month.year < basis.eligibility_year:
            raise InvalidFamilyInput("FRA precedes eligibility")
    if death_month is not None:
        _month(death_month, "death_month")
        if death_month < basis.entitlement_month or (
            years and years[-1] > death_month.year
        ):
            raise InvalidFamilyInput(
                "death or earnings year contradicts entitlement"
            )
        if fra_month is None:
            raise InvalidFamilyInput(
                "death-year processing requires FRA month"
            )
    if years:
        prefix = _history_prefix(history, basis, years[-1])
        _aime_parameters(prefix, basis, params)
        final_month = (
            death_month
            if death_month is not None and death_month.year == years[-1]
            else YearMonth(years[-1] + 1, 1)
        )
        _month(final_month, "final effective month")
        _colas(december_cola_percent, basis.eligibility_year, final_month)
        _validate_original_computation_count(basis)
        _require_coverage(
            basis,
            (
                death_month
                if death_month is not None and death_month.year == years[-1]
                else None
            ),
            fra_month,
        )
    results = []
    for year in years:
        result = annual_recomputation(
            basis,
            history,
            year,
            current,
            params,
            december_cola_percent,
            death_month=death_month,
            fra_month=fra_month,
        )
        results.append(result)
        current = result.eligibility_pia_in_force
    return tuple(results)
