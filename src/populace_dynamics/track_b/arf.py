"""R3: record-specific adjustment of the reduction factor (ARF).

Verification class: statutory conformance. This module admits ARF credits
and benefit arithmetic for the supported invented or published cases only;
it admits no population, behavioral, or forecast claim.

42 U.S.C. 402(q)(6)-(9), 20 CFR 404.409-.412 and POMS RS 00615.480-.598
govern the reduction window, excluded months, timing and rounding. R2
supplies final full/partial work-deduction months separately for each
benefit record. Prorated provisional suspensions are not that input.
The current unreduced benefit is already COLA-increased and, for an
auxiliary, already reduced for the family maximum. G's exact Fraction
reduction functions, ceil_dime, floor_dime and whole_dollars are reused.

An ARF always starts from the original reduction window. Applying a
result again therefore cannot credit the same month twice. Widow(er)
credits are applied at age 62 and at widow(er) FRA; the age-62 adjustment
persists, without new credits, until FRA (RS 00615.582; CFR 404.412(b)).
The month of age attainment precedes the birth month for a first-day
birthday; a January 1 birth also uses the preceding FRA cohort.

Collection inputs are snapshotted into immutable tuples or frozensets at
construction, including one-shot iterators. Repeated original-claim
evaluation preserves both dollar amounts and coverage refusals. Contents
are validated before coverage is decided, without consuming caller state.
Pre-FRA spouse reentitlement is refused because RS 00615.201A.1 and
.491A conflict on when termination months leave the reduction factor.

Unsupported configurations raise ARFConfigurationUnsupported, in the shared
FamilyConfigurationUnsupported family, with exactly ARFUnsupportedReason.
A package-private capability seals results, refusals and outcomes. Direct
construction, replacement and copying are invalid; pickle restoration
revalidates identities. Evaluators and apply_arf require unchanged ARF
results, while the common denominator admits every sealed layer outcome.
Invalid inputs, including G's statutory rate bundle,
are checked before coverage and benefit arithmetic. Non-finite numeric
rates, benefit shares and brackets are rejected locally before G's
statutory comparison. Parameter ValueErrors propagate through evaluate_arf
and lazy count_arf_outcomes; only valid coverage refusals enter the weighted
denominator.
This module does not assemble payments, deductions, or event histories.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from fractions import Fraction

from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    FamilyDenominator,
    InvalidFamilyInput,
    YearMonth,
    _check_evaluation_inputs,
    _outcome_weight,
    ceil_dime,
    count_family_outcomes,
    floor_dime,
    spouse_reduction_fraction,
    statutory_rates,
    survivor_reduction_fraction,
    whole_dollars,
    widow_reduction_period_months,
    worker_reduction_fraction,
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

ARF_VERSION = "track-b-r3-arf-v1"
MonthInput = YearMonth | tuple[int, int]
_CREDIT_FIELDS = (
    "full_work_deduction_months",
    "partial_work_deduction_months",
    "child_in_care_months",
    "nonentitlement_months",
    "simultaneous_dib_months",
    "mother_father_rate_months",
)


class ARFBenefitKind(Enum):
    RIB = "rib"
    SPOUSE = "spouse"
    WIDOW = "widow"


class ARFUnsupportedReason(Enum):
    INITIAL_ENTITLEMENT_BEFORE_1978 = "arf_initial_entitlement_before_1978"
    PAYMENT_BEFORE_1983 = "arf_payment_before_1983"
    SPOUSE_REENTITLEMENT_BEFORE_FRA = "arf_spouse_reentitlement_before_fra"
    DISABLED_WIDOW = "arf_disabled_widow"
    WIDOW_DUAL_DIB = "arf_widow_dual_dib"
    WIDOW_DUAL_RIB = "arf_widow_dual_rib"
    WIDOW_RIB_LIMIT = "arf_widow_rib_limit"
    WIDOW_FRA_BEFORE_1911 = "arf_widow_fra_before_1911"
    HISTORICAL_WIDOW_FRA_CONFLICT = "arf_historical_widow_fra_conflict"
    WIDOW_CHILD_CARE_WITHOUT_RATE_INCREASE = (
        "arf_widow_child_care_without_rate_increase"
    )
    SPOUSE_OWN_AFTER_SPOUSE_BEFORE_ARF = (
        "arf_spouse_own_after_spouse_before_arf"
    )
    OTHER_SUSPENSION = "arf_other_suspension"


@_sealed_refusal(ARFUnsupportedReason)
class ARFConfigurationUnsupported(FamilyConfigurationUnsupported):
    """A sealed ARF coverage refusal with exactly an ARF reason."""


class SpouseOwnSequence(Enum):
    """The supported RS 00615.500 sequencing, and one named refusal."""

    CONCURRENT_OR_PRECEDING = "concurrent_or_preceding"
    AFTER_SPOUSE_ARF = "after_spouse_arf"
    AFTER_SPOUSE_BEFORE_ARF = "after_spouse_before_arf"


def _month(value: MonthInput, label: str) -> YearMonth:
    if type(value) is YearMonth:
        try:
            result = YearMonth(value.year, value.month)
        except (AttributeError, TypeError, ValueError) as error:
            raise InvalidFamilyInput(f"{label}: {error}") from error
    elif isinstance(value, tuple) and len(value) == 2:
        try:
            result = YearMonth(*value)
        except (TypeError, ValueError) as error:
            raise InvalidFamilyInput(f"{label}: {error}") from error
    else:
        raise InvalidFamilyInput(
            f"{label} must be a YearMonth or (year, month)"
        )
    if result.year < 1:
        raise InvalidFamilyInput(f"{label} year must be positive")
    return result


def _month_set(
    values: Iterable[MonthInput], label: str
) -> frozenset[YearMonth]:
    try:
        return frozenset(_month(value, label) for value in values)
    except TypeError as error:
        raise InvalidFamilyInput(
            f"{label} must be an iterable of months"
        ) from error


def _amount(value: object, label: str) -> Fraction:
    """Use exact inputs, with explicit zeros; do not accept binary floats."""
    if isinstance(value, (bool, float)):
        raise InvalidFamilyInput(f"{label} must be an exact amount")
    try:
        result = Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError) as error:
        raise InvalidFamilyInput(f"{label} must be an exact amount") from error
    if result < 0 or (result * 10).denominator != 1:
        raise InvalidFamilyInput(f"{label} must be nonnegative whole dimes")
    return result


def _index(month: YearMonth) -> int:
    return month.year * 12 + month.month - 1


def _from_index(index: int) -> YearMonth:
    year, month = divmod(index, 12)
    return YearMonth(year, month + 1)


def age_attainment_month(birth_date: date, age_months: int) -> YearMonth:
    """SSA day-before-birthday month (RS 00615.004/.015).

    The throughout-the-month requirement for initial RIB at 62 is a
    different rule and is not imposed on FRA attainment.
    """
    if type(birth_date) is not date:
        raise InvalidFamilyInput("birth_date must be a datetime.date")
    if type(age_months) is not int or age_months < 0:
        raise InvalidFamilyInput("age_months must be a nonnegative integer")
    index = birth_date.year * 12 + birth_date.month - 1 + age_months
    return _from_index(index - (birth_date.day == 1))


def _fra_month_for_input_validation(
    birth_date: date, kind: ARFBenefitKind, params: SSAParameters
) -> YearMonth:
    """Validate dates against POMS FRA; the disputed cohort is then refused.

    The POMS age-65 reading gives the wider legal input window for the
    1911 cohort. This helper does not authorize payment under that reading.
    """
    if type(birth_date) is not date or not isinstance(kind, ARFBenefitKind):
        raise InvalidFamilyInput("birth_date and benefit kind must be valid")
    if kind is ARFBenefitKind.WIDOW:
        # RS 00615.003B.1's historical FRA 62 is outside G's 60-84-month
        # survivor interpolation surface, and is refused by apply_arf.
        months = (
            744
            if birth_date < date(1911, 1, 2)
            else 720 + widow_reduction_period_months(birth_date)
        )
    else:
        cohort = birth_date.year - (
            birth_date.month == 1 and birth_date.day == 1
        )
        months = params.fra_months(cohort)
    return age_attainment_month(birth_date, months)


def full_retirement_age_month(
    birth_date: date, kind: ARFBenefitKind, params: SSAParameters
) -> YearMonth:
    """Record-specific FRA; refuse the disputed historic survivor cohort."""
    result = _fra_month_for_input_validation(birth_date, kind, params)
    if kind is ARFBenefitKind.WIDOW and date(1911, 1, 2) <= birth_date <= date(
        1912, 1, 1
    ):
        # Source conflict us:oasdi-survivor-fra-1911-births
        _refuse(
            ARFUnsupportedReason.HISTORICAL_WIDOW_FRA_CONFLICT,
            "RS 00615.003 gives FRA 65 but 20 CFR 404.409 gives FRA 62",
        )
    return result


@dataclass(frozen=True)
class SpouseOwnBenefit:
    """Own RIB/DIB amounts supplied after their independent adjustment.

    CONCURRENT_OR_PRECEDING reduces the spouse excess over own PIA.
    AFTER_SPOUSE_ARF preserves the single-entitlement spouse reduction
    and offsets the independently computed own payment (.500A.1).
    This component does not recompute the own benefit or its ARF credits.
    """

    pia: Fraction
    payable: Fraction
    sequence: SpouseOwnSequence


@dataclass(frozen=True)
class ARFClaim:
    """An original reduction window and explicit record-specific credits.

    first_reduction_month is the effective reduced-spouse election month
    for a spouse. For ordinary RIB or WIB it is the first entitlement
    month. Nonentitlement months mean termination under 402(q)(7)(C)/(E),
    not missing records. Mother/father-rate months mean (q)(5)(D) actually
    determined the widow(er)'s benefit, rather than every caregiving month.
    All month and condition iterables are copied at construction. Tuple
    snapshots retain malformed contents for the complete validation that
    precedes coverage checks, while never retaining a mutable collection
    or a one-shot iterator as claim state.
    """

    kind: ARFBenefitKind
    birth_date: date
    first_reduction_month: MonthInput
    unreduced_benefit: Fraction
    full_work_deduction_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    partial_work_deduction_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    child_in_care_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    nonentitlement_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    simultaneous_dib_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    mother_father_rate_months: Iterable[MonthInput] = field(
        default_factory=frozenset
    )
    death_date: date | None = None
    spouse_own: SpouseOwnBenefit | None = None
    conditions: Iterable[ARFUnsupportedReason] = field(
        default_factory=frozenset
    )

    def __post_init__(self):
        for name in (*_CREDIT_FIELDS, "conditions"):
            try:
                values = getattr(self, name)
                snapshot = (
                    values if isinstance(values, frozenset) else tuple(values)
                )
            except TypeError as error:
                raise InvalidFamilyInput(
                    f"{name} must be an iterable"
                ) from error
            object.__setattr__(self, name, snapshot)


@_sealed_result
@dataclass(frozen=True)
class ARFResult(_SealedResult):
    """Benefit component after ARF and, when supplied, the own offset.

    factor is the nominal age factor before dime rounding or own offset.
    An own RIB/DIB payment is separate from benefit, and is not rounded
    together with it. A deceased worker result is a hypothetical RIB for
    the survivor limit, never an instruction to pay the deceased.
    """

    claim: ARFClaim
    payment_month: YearMonth
    fra_month: YearMonth
    effective_adjustment_month: YearMonth | None
    original_reduction_months: int
    adjusted_reduction_months: int
    crediting_months: frozenset[YearMonth]
    factor: Fraction
    reduction: Fraction
    benefit: Fraction
    whole_dollar_benefit: int

    def __post_init__(self):
        object.__setattr__(
            self,
            "crediting_months",
            _month_set(self.crediting_months, "crediting_months"),
        )
        if type(self.claim) is not ARFClaim:
            raise InvalidFamilyInput("ARF result requires its original claim")
        payment = _month(self.payment_month, "payment_month")
        fra = _month(self.fra_month, "fra_month")
        claim = _check_claim(self.claim, None, result_fra=fra)
        object.__setattr__(self, "claim", claim)
        first = claim.first_reduction_month
        own = claim.spouse_own
        if payment < first or (
            own is not None
            and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_ARF
            and payment < fra
        ):
            raise InvalidFamilyInput(
                "ARF result contradicts its entitlement window"
            )
        if (
            claim.conditions
            or first < YearMonth(1978, 1)
            or payment < YearMonth(1983, 1)
            or (
                claim.kind is ARFBenefitKind.WIDOW
                and claim.birth_date < date(1912, 1, 2)
            )
            or (
                own is not None
                and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_BEFORE_ARF
            )
            or (
                claim.kind is ARFBenefitKind.SPOUSE
                and payment < fra
                and any(
                    first <= month < payment
                    for month in claim.nonentitlement_months
                )
            )
        ):
            raise InvalidFamilyInput(
                "ARF result cannot contain a refused original claim"
            )
        if claim.kind is ARFBenefitKind.WIDOW and fra != age_attainment_month(
            claim.birth_date,
            720 + widow_reduction_period_months(claim.birth_date),
        ):
            raise InvalidFamilyInput(
                "ARF widow FRA disagrees with original cohort"
            )
        original = _index(fra) - _index(first)
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.original_reduction_months,
                    self.adjusted_reduction_months,
                )
            )
            or self.original_reduction_months != original
        ):
            raise InvalidFamilyInput("ARF original reduction window disagrees")
        effective = fra if payment >= fra else None
        age62 = age_attainment_month(claim.birth_date, 744)
        if (
            claim.kind is ARFBenefitKind.WIDOW
            and first <= age62 <= payment < fra
        ):
            effective = age62
        if self.effective_adjustment_month != effective:
            raise InvalidFamilyInput(
                "ARF effective adjustment month disagrees"
            )
        limit = effective
        if limit is not None and claim.death_date is not None:
            limit = min(
                limit, YearMonth(claim.death_date.year, claim.death_date.month)
            )
        eligible = frozenset().union(
            *(
                _month_set(getattr(claim, field), field)
                for field in _CREDIT_FIELDS
            )
        )
        expected = frozenset(
            month
            for month in eligible
            if limit is not None and first <= month < limit
        )
        if self.crediting_months != expected:
            raise InvalidFamilyInput(
                "ARF credited months disagree with original window"
            )
        adjusted = original - len(expected)
        if self.adjusted_reduction_months != adjusted:
            raise InvalidFamilyInput(
                "ARF adjusted months plus credits must equal original"
            )
        if claim.kind is ARFBenefitKind.RIB:
            reduction_fraction = min(adjusted, 36) * Fraction(1, 180) + max(
                0, adjusted - 36
            ) * Fraction(1, 240)
        elif claim.kind is ARFBenefitKind.SPOUSE:
            reduction_fraction = min(adjusted, 36) * Fraction(1, 144) + max(
                0, adjusted - 36
            ) * Fraction(1, 240)
        elif claim.kind is ARFBenefitKind.WIDOW:
            reduction_fraction = (
                Fraction(57, 200)
                * adjusted
                / widow_reduction_period_months(claim.birth_date)
            )
        else:
            raise InvalidFamilyInput("ARF result requires its benefit kind")
        if self.factor != 1 - reduction_fraction or not 0 <= self.factor <= 1:
            raise InvalidFamilyInput(
                "ARF nominal factor disagrees with adjusted months"
            )
        base = _amount(claim.unreduced_benefit, "unreduced_benefit")
        own = claim.spouse_own
        if (
            own is not None
            and own.sequence is SpouseOwnSequence.CONCURRENT_OR_PRECEDING
        ):
            base = max(Fraction(0), base - own.pia)
        reduction = ceil_dime(base * reduction_fraction)
        benefit = floor_dime(base - reduction)
        if (
            own is not None
            and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_ARF
        ):
            benefit = max(Fraction(0), benefit - own.payable)
        if (
            _amount(self.reduction, "reduction") != reduction
            or _amount(self.benefit, "benefit") != benefit
            or type(self.whole_dollar_benefit) is not int
            or self.whole_dollar_benefit != whole_dollars(benefit)
        ):
            raise InvalidFamilyInput(
                "ARF reduction and payable identities disagree"
            )


@_sealed_result
@dataclass(frozen=True)
class ARFOutcome(_SealedOutcome):
    """One sealed ARF result or shared-family refusal, with its full weight."""

    key: str
    weight: Fraction
    benefits: ARFResult | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _check_evaluation_inputs(self.key, self.weight, lambda: None)
        if (self.benefits is None) == (self.unsupported is None):
            raise InvalidFamilyInput("exactly one result/refusal is required")
        if self.benefits is not None:
            _checked_result(self.benefits, ARFResult, "ARF benefits")
        if self.unsupported is not None:
            _check_refusal(self.unsupported)
        object.__setattr__(self, "weight", _outcome_weight(self.weight))

    @property
    def supported(self) -> bool:
        _check_seal(self)
        return self.benefits is not None


def _check_finite_statutory_parameters(params: SSAParameters) -> None:
    """Reject non-finite bundle values before G's rate comparisons.

    Check the full shared statutory bundle for every ARF record kind.
    Finite mismatches still use G's existing statutory_rates errors.
    """
    fields = [
        (f"{name}[{index}]", value)
        for name in ("early_monthly_rates", "spousal_early_monthly_rates")
        for index, value in enumerate(getattr(params, name))
    ]
    fields.extend(
        (name, getattr(params, name))
        for name in (
            "early_first_bracket_months",
            "spousal_early_first_bracket_months",
            "survivor_reduction_floor",
            "rib_lim_pia_share",
            "spousal_pia_share",
            "survivor_pia_share",
        )
    )
    for label, value in fields:
        if not math.isfinite(float(value)):
            raise ValueError(
                f"Parameter bundle {label}={value!r} must be finite; "
                "refusing to compute ARF."
            )


def _check_claim(
    claim: ARFClaim,
    params: SSAParameters | None,
    *,
    result_fra: YearMonth | None = None,
) -> ARFClaim:
    """Validate declarations before money, or when restoring a sealed result.

    Computation supplies its statutory bundle. Result restoration retains
    the computed FRA and revalidates all claim fields and available window
    identities without a parameter bundle or a new FRA schedule choice.
    """
    if not isinstance(claim, ARFClaim):
        raise InvalidFamilyInput("claim must be an ARFClaim")
    if not isinstance(claim.kind, ARFBenefitKind):
        raise InvalidFamilyInput("kind must be an ARFBenefitKind")
    if type(claim.birth_date) is not date:
        raise InvalidFamilyInput("birth_date must be a datetime.date")
    first = _month(claim.first_reduction_month, "first_reduction_month")
    amount = _amount(claim.unreduced_benefit, "unreduced_benefit")
    try:
        conditions = frozenset(claim.conditions)
    except TypeError as error:
        raise InvalidFamilyInput("conditions must be an iterable") from error
    if any(not isinstance(c, ARFUnsupportedReason) for c in conditions):
        raise InvalidFamilyInput(
            "conditions must contain ARFUnsupportedReason"
        )
    values = {}
    for name in _CREDIT_FIELDS:
        values[name] = _month_set(getattr(claim, name), name)
    if (
        values["child_in_care_months"]
        and claim.kind is not ARFBenefitKind.SPOUSE
    ):
        raise InvalidFamilyInput(
            "child_in_care_months are spouse credits only"
        )
    if values["nonentitlement_months"] and claim.kind is ARFBenefitKind.RIB:
        raise InvalidFamilyInput(
            "RIB nonentitlement months are not ARF credits"
        )
    if (
        values["simultaneous_dib_months"]
        and claim.kind is not ARFBenefitKind.RIB
    ):
        raise InvalidFamilyInput(
            "simultaneous_dib_months are RIB credits only"
        )
    if (
        values["mother_father_rate_months"]
        and claim.kind is not ARFBenefitKind.WIDOW
    ):
        raise InvalidFamilyInput(
            "mother_father_rate_months are widow credits only"
        )
    if claim.death_date is not None:
        if (
            type(claim.death_date) is not date
            or claim.death_date < claim.birth_date
        ):
            raise InvalidFamilyInput("death_date must be a date after birth")
        if claim.kind is not ARFBenefitKind.RIB:
            raise InvalidFamilyInput(
                "death_date applies to the deceased RIB only"
            )
        if YearMonth(claim.death_date.year, claim.death_date.month) < first:
            raise InvalidFamilyInput(
                "death cannot precede first reduction month"
            )
    own = claim.spouse_own
    if own is not None:
        if claim.kind is not ARFBenefitKind.SPOUSE or not isinstance(
            own, SpouseOwnBenefit
        ):
            raise InvalidFamilyInput(
                "spouse_own requires a spouse own benefit"
            )
        if not isinstance(own.sequence, SpouseOwnSequence):
            raise InvalidFamilyInput("invalid spouse own entitlement sequence")
        own = SpouseOwnBenefit(
            _amount(own.pia, "own PIA"),
            _amount(own.payable, "own payable"),
            own.sequence,
        )
    if params is None:
        fra = _month(result_fra, "result_fra")
    else:
        _check_finite_statutory_parameters(params)
        statutory_rates(params)
        fra = _fra_month_for_input_validation(
            claim.birth_date, claim.kind, params
        )
    if claim.kind is ARFBenefitKind.WIDOW:
        minimum_age = (
            600 if ARFUnsupportedReason.DISABLED_WIDOW in conditions else 720
        )
    else:
        minimum_age = 744
    earliest = age_attainment_month(claim.birth_date, minimum_age)
    if claim.kind is ARFBenefitKind.RIB and claim.birth_date.day != 2:
        earliest = _from_index(_index(earliest) + 1)
    if first < earliest:
        raise InvalidFamilyInput(
            "first reduction month precedes the minimum age"
        )
    if first > fra:
        raise InvalidFamilyInput("first reduction month must not follow FRA")
    return ARFClaim(
        claim.kind,
        claim.birth_date,
        first,
        amount,
        **values,
        death_date=claim.death_date,
        spouse_own=own,
        conditions=conditions,
    )


def _refuse(reason: ARFUnsupportedReason, detail: str) -> None:
    raise _computed(ARFConfigurationUnsupported, reason, detail)


def apply_arf(
    claim: ARFClaim | ARFResult,
    *,
    payment_month: MonthInput,
    params: SSAParameters,
) -> ARFResult:
    """Apply record-specific credits at FRA (widow(er) also at age 62).

    Reapplying an ARFResult uses its original claim, not its adjusted
    months. Crediting inputs outside the original window do not count.
    Zero credits leave the benefit exactly as G would compute it.
    """
    if isinstance(claim, ARFResult):
        claim = _checked_result(claim, ARFResult, "claim").claim
    claim = _check_claim(claim, params)
    payment = _month(payment_month, "payment_month")
    fra = _fra_month_for_input_validation(claim.birth_date, claim.kind, params)
    first = claim.first_reduction_month
    if payment < first:
        raise InvalidFamilyInput(
            "payment_month precedes the first reduction month"
        )
    own = claim.spouse_own
    if (
        own is not None
        and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_ARF
        and payment < fra
    ):
        raise InvalidFamilyInput(
            "own entitlement after spouse ARF cannot precede FRA"
        )
    if claim.kind is ARFBenefitKind.WIDOW and date(
        1911, 1, 2
    ) <= claim.birth_date <= date(1912, 1, 1):
        # Source conflict us:oasdi-survivor-fra-1911-births
        _refuse(
            ARFUnsupportedReason.HISTORICAL_WIDOW_FRA_CONFLICT,
            "RS 00615.003 gives FRA 65 but 20 CFR 404.409 gives FRA 62",
        )
    if first < YearMonth(1978, 1):
        _refuse(
            ARFUnsupportedReason.INITIAL_ENTITLEMENT_BEFORE_1978,
            "RS 00615.490B.2 requires the historical money-reduction ratio",
        )
    if payment < YearMonth(1983, 1):
        _refuse(
            ARFUnsupportedReason.PAYMENT_BEFORE_1983,
            "G's shared dime-rounding surface begins January 1983",
        )
    if claim.kind is ARFBenefitKind.WIDOW and claim.birth_date < date(
        1911, 1, 2
    ):
        _refuse(
            ARFUnsupportedReason.WIDOW_FRA_BEFORE_1911,
            "RS 00615.003B.1's historical FRA 62 is outside G's widow period",
        )
    # Source conflict us:oasdi-arf-widow-child-in-care-credits
    # Declared nonbinding care is refused; actual rate months count below.
    if claim.conditions:
        reason = sorted(claim.conditions, key=lambda c: c.value)[0]
        _refuse(
            reason, "this exceptional ARF history requires a separate rule"
        )
    if (
        claim.kind is ARFBenefitKind.SPOUSE
        and payment < fra
        and any(
            first <= month < payment for month in claim.nonentitlement_months
        )
    ):
        # Source conflict us:oasdi-arf-spouse-reentitlement-credits
        _refuse(
            ARFUnsupportedReason.SPOUSE_REENTITLEMENT_BEFORE_FRA,
            "RS 00615.201A.1 and .491A conflict on pre-FRA reentitlement timing; "
            "this module supports the final FRA adjustment only",
        )
    if (
        own is not None
        and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_BEFORE_ARF
    ):
        _refuse(
            ARFUnsupportedReason.SPOUSE_OWN_AFTER_SPOUSE_BEFORE_ARF,
            "RS 00615.500 does not supply this entitlement sequence's procedure",
        )
    age62 = age_attainment_month(claim.birth_date, 744)
    effective = fra if payment >= fra else None
    if claim.kind is ARFBenefitKind.WIDOW and first <= age62 <= payment < fra:
        effective = age62
    limit = effective
    if claim.death_date is not None:
        death_month = YearMonth(claim.death_date.year, claim.death_date.month)
        # Final RIB work deductions precede the death month: the worker
        # has no RIB benefit in the month of death. RS 00615.598 permits
        # the hypothetical adjustment only at would-have-been FRA.
        if limit is not None:
            limit = min(limit, death_month)
    original = _index(fra) - _index(first)
    eligible = (
        claim.full_work_deduction_months
        | claim.partial_work_deduction_months
        | claim.child_in_care_months
        | claim.nonentitlement_months
        | claim.simultaneous_dib_months
        # Source conflict us:oasdi-arf-widow-child-in-care-credits
        | claim.mother_father_rate_months
    )
    credits = frozenset(
        month
        for month in eligible
        if limit is not None and first <= month < limit
    )
    adjusted = original - len(credits)
    if claim.kind is ARFBenefitKind.RIB:
        reduction_fraction = worker_reduction_fraction(adjusted, params)
    elif claim.kind is ARFBenefitKind.SPOUSE:
        reduction_fraction = spouse_reduction_fraction(adjusted, params)
    else:
        reduction_fraction = survivor_reduction_fraction(
            adjusted, widow_reduction_period_months(claim.birth_date), params
        )
    base = claim.unreduced_benefit
    if (
        own is not None
        and own.sequence is SpouseOwnSequence.CONCURRENT_OR_PRECEDING
    ):
        base = max(Fraction(0), base - own.pia)
    reduction = ceil_dime(base * reduction_fraction)
    benefit = floor_dime(base - reduction)
    if own is not None and own.sequence is SpouseOwnSequence.AFTER_SPOUSE_ARF:
        benefit = max(Fraction(0), benefit - own.payable)
    return _computed(
        ARFResult,
        claim,
        payment,
        fra,
        effective,
        original,
        adjusted,
        credits,
        1 - reduction_fraction,
        reduction,
        benefit,
        whole_dollars(benefit),
    )


def evaluate_arf(
    key: str, weight: object, compute: Callable[[], ARFResult]
) -> ARFOutcome:
    """Keep sealed ARF results and shared-family refusals in one denominator.

    Metadata errors precede computation. Only unchanged results produced
    by apply_arf may enter supported rows; G money consumers remain G-only.
    """
    _check_evaluation_inputs(key, weight, compute)
    try:
        result = compute()
    except FamilyConfigurationUnsupported as error:
        return _computed(ARFOutcome, key, weight, None, _check_refusal(error))
    _checked_result(result, ARFResult, "ARF result")
    return _computed(ARFOutcome, key, weight, result, None)


def count_arf_outcomes(
    outcomes: Iterable[_SealedOutcome],
) -> FamilyDenominator:
    """Reuse the shared denominator, retaining every row and refused weight."""
    return count_family_outcomes(outcomes)
