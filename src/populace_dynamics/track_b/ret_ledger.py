"""R2 part (a): an exact, single-record calendar-year RET ledger.

Verification class: statutory conformance. Admitted scope: retirement
earnings-test mechanics on invented cases and published statutory examples;
no population, behavioral, or forecast claim. Authority: Act 203(b), (f),
(h); 20 CFR 404.415, .428-.441; POMS RS 02501.021-.155. Captured sources
and exact worked examples are pinned in tests/data/track_b/ret_ledger_sources.

Annual limits and exact rates always come from R1. G supplies monthly dime
rates after the maximum, age and dual-entitlement reductions, and ORIGINAL
rates before those reductions for partial-payment shares (RS 02501.110).
Actual deductions and estimated full-month suspensions are separate runs.
Net due is exact BEFORE 215(g); payment is its whole-dollar floor. Rounding
loss is consequently not an additional work deduction or crediting month.

Worker protections apply to that worker's excess, not another worker's
excess charged against their benefit (Act 203(f)(1); RS 02501.140). In
particular a deemed-entitled CDB recipient can be charged the NH's excess.
Auxiliary work that would free binding family-maximum room is refused for
part (b), as are other deduction events. No unsupported row is dropped
from an outcome denominator or silently computed as a single worker.
Every raw month-set element must be an integer month before deduplication;
malformed input raises before a coverage refusal can become an outcome.

Monthly limits are exact annual/12, including the fractional amounts in
Act 203(f)(8)(D)(v)-(vi) for 2000/2001. The chart ceiling is an explicitly
nonstatutory operational sensitivity, never the default. CFR .440 and POMS
.110 require stopping reapportionment when capped overflow is below $1:
retain the last shares, cap beneficiaries at their rates, and disclose the
unpaid residual separately. Final deductions equal excess charged plus
that residual; the residual is neither excess charged nor a crediting
event by itself. Complete redistribution is unavailable.

R2 result values and outcomes share the package-private provenance seal
with G and R3. Only computation builds them; consumption and pickle restore
validate their identities and nested seals. RET refusals bind exactly
RETUnsupportedReason while retaining FamilyConfigurationUnsupported as the
shared catch type. The common denominator counts every layer's sealed rows;
RET money aggregation accepts only RETOutcome and RETLedger values.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from math import ceil, floor
from types import MappingProxyType

from populace_dynamics.track_b._provenance import (
    _check_refusal,
    _check_seal,
    _checked_result,
    _computed,
    _sealed_refusal,
    _sealed_result,
    _SealedOutcome,
    _SealedResult,
)
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    FamilyDenominator,
    FamilyTargetBlocked,
    InvalidFamilyInput,
    _check_evaluation_inputs,
    count_family_outcomes,
    whole_dollars,
)
from populace_dynamics.track_b.ret_grace import (
    DISABILITY_TYPES,
    BenefitType,
    GraceYearDecision,
)
from populace_dynamics.track_b.ret_params import (
    RETParameters,
    load_ret_parameters,
)


class RETUnsupportedReason(Enum):
    YEAR_BEFORE_2000 = "payment_year_before_2000"
    FISCAL_YEAR = "fiscal_taxable_year"
    SHORT_TAXABLE_YEAR = "short_taxable_year"
    PRORATED_SUSPENSION = "prorated_work_suspension"
    DEFERRED_SUSPENSION = "deferred_work_suspension"
    PROTEST_PARTIAL_SUSPENSION = "protested_partial_work_suspension"
    DEDUCTION_BEFORE_REDUCTION = "deduction_before_reduction_part_b"
    TWO_RECORD_EARNINGS = "excess_earnings_on_two_records"
    FOREIGN_WORK = "noncovered_foreign_work"
    VOCATIONAL_REHABILITATION = "vocational_rehabilitation_refusal"
    OTHER_DEDUCTION = "other_deduction_event"
    DEEMED_ENTITLEMENT_BASIS = "deemed_entitlement_marriage_basis"


# Preserve the R2 module's original import name.
UnsupportedReason = RETUnsupportedReason


@_sealed_refusal(RETUnsupportedReason)
class RETConfigurationUnsupported(FamilyConfigurationUnsupported):
    """A retained coverage refusal with an R2-specific reason."""


class RecordKind(Enum):
    RETIREMENT = "retirement"
    DISABILITY = "disability"
    DECEASED = "deceased"


class SuspensionMethod(Enum):
    FULL_MONTH = "full_month"
    PRORATED = "prorated"
    DEFERRED = "deferred"
    PROTEST_PARTIAL = "protest_partial"


class MonthlyLimitPolicy(Enum):
    """Statutory twelfth or explicitly nonstatutory chart sensitivity."""

    EXACT_TWELFTH = "exact_twelfth"
    NONSTATUTORY_CHART_CEILING = "nonstatutory_chart_ceiling"


class NESEProrationPolicy(Enum):
    FLOOR = "floor"
    DROP_CENTS = "drop_cents"


def _exact(value: object, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(
        value, (int, str, Decimal, Fraction)
    ):
        raise InvalidFamilyInput(f"{label} requires an exact number")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise InvalidFamilyInput(f"Invalid {label}") from error


def _sequence(values: Iterable[object], label: str) -> tuple:
    if isinstance(values, (str, bytes, Mapping)):
        raise InvalidFamilyInput(f"{label} must be a sequence")
    try:
        return tuple(values)
    except TypeError as error:
        raise InvalidFamilyInput(f"{label} must be a sequence") from error


def _months(values: Iterable[int], label: str) -> frozenset[int]:
    try:
        raw = tuple(values)
    except TypeError as error:
        raise InvalidFamilyInput(f"{label} must contain months") from error
    if any(type(m) is not int or not 1 <= m <= 12 for m in raw):
        raise InvalidFamilyInput(f"{label} must contain months 1 through 12")
    return frozenset(raw)


def _fra(month: int | None) -> None:
    if month is not None and (type(month) is not int or not 0 <= month <= 12):
        raise InvalidFamilyInput("FRA month must be None or 0 through 12")


def _rates(values: Iterable[object], label: str) -> tuple[Fraction, ...]:
    result = tuple(_exact(v, label) for v in _sequence(values, label))
    if len(result) != 12 or any(
        v < 0 or (v * 10).denominator != 1 for v in result
    ):
        raise InvalidFamilyInput(
            f"{label} needs twelve nonnegative dime rates"
        )
    return result


@dataclass(frozen=True)
class WorkEarnings:
    """RET-countable wages earned, annual NESE, and service-month facts.

    Wages already exclude items outside RS 02505.005; substantial services
    are an explicit RS 02505.065 input, not an inferred income threshold.
    NESE may be a loss. A nonzero NESE needs its months of self-employment.
    """

    wages: tuple[Fraction, ...] = (Fraction(0),) * 12
    nese: Fraction = Fraction(0)
    self_employment_months: frozenset[int] = field(default_factory=frozenset)
    substantial_service_months: frozenset[int] = field(
        default_factory=frozenset
    )

    def __post_init__(self):
        wages = tuple(
            _exact(v, "Wages") for v in _sequence(self.wages, "Wages")
        )
        nese = _exact(self.nese, "NESE")
        se = _months(self.self_employment_months, "Self-employment months")
        services = _months(
            self.substantial_service_months, "Substantial services"
        )
        if len(wages) != 12 or any(w < 0 for w in wages):
            raise InvalidFamilyInput("Supply twelve nonnegative monthly wages")
        if (nese and not se) or not services <= se:
            raise InvalidFamilyInput(
                "NESE and services require self-employment months"
            )
        object.__setattr__(self, "wages", wages)
        object.__setattr__(self, "nese", nese)
        object.__setattr__(self, "self_employment_months", se)
        object.__setattr__(self, "substantial_service_months", services)


@dataclass(frozen=True)
class RETBeneficiary:
    """One person's monthly G rates and dated entitlement/work facts.

    ``fra_month=0`` means FRA before this year, ``None`` means after it.
    Survivors use the RIB FRA. ``divorced_months`` lists months with at
    least two years since divorce; prior NH RIB entitlement is the other
    Act 203(b)(2) exception. ``deemed_entitled`` and
    ``deemed_married_to_nh`` assert the married recipient in Act 203(b)(1)
    / CFR .420. An ordinary child's Act 203(b)(1) age facts need explicit
    ``deemed_child_age_18_months``; that Act/CFR coverage difference is
    refused pending judgment. Broader unmarried-child wording in
    RS 02501.140 is also refused. Own two-record excess is still refused.
    ``own_work_exempt_months`` supplies other Act
    203(f)(1)(C)-(D) protections (entitled child who has attained 18 /
    widow(er) entitled before 60). It defaults to empty under the CFR's
    disability-type wording. Selecting this Act-clause alternative
    asserts lawful entitlement, age facts and any 202(s) condition; the
    ledger does not infer those facts or adjudicate that condition.
    """

    beneficiary_id: str
    benefit_types: tuple[BenefitType, ...]
    entitled_months: frozenset[int]
    gross_rates: tuple[Fraction, ...]
    original_rates: tuple[Fraction, ...]
    earnings: WorkEarnings = field(default_factory=WorkEarnings)
    estimated_earnings: WorkEarnings | None = None
    fra_month: int | None = None
    grace: GraceYearDecision | None = None
    estimated_grace: GraceYearDecision | None = None
    divorced_months: frozenset[int] = field(default_factory=frozenset)
    nh_entitled_before_divorce: bool = False
    deemed_entitled: bool = False
    deemed_married_to_nh: bool = False
    deemed_child_age_18_months: frozenset[int] = field(
        default_factory=frozenset
    )
    death_month: int | None = None
    own_work_exempt_months: frozenset[int] = field(default_factory=frozenset)
    two_record_entitlement: bool = False

    def __post_init__(self):
        if (
            not isinstance(self.beneficiary_id, str)
            or not self.beneficiary_id.strip()
        ):
            raise InvalidFamilyInput("A beneficiary needs a nonempty identity")
        types = _sequence(self.benefit_types, "Benefit types")
        if len(types) != 12 or any(
            not isinstance(t, BenefitType) for t in types
        ):
            raise InvalidFamilyInput("Supply twelve BenefitType values")
        entitled = _months(self.entitled_months, "Entitled months")
        gross = _rates(self.gross_rates, "Gross rates")
        original = _rates(self.original_rates, "Original rates")
        for name in (
            "divorced_months",
            "own_work_exempt_months",
            "deemed_child_age_18_months",
        ):
            object.__setattr__(self, name, _months(getattr(self, name), name))
        for name in (
            "nh_entitled_before_divorce",
            "deemed_entitled",
            "deemed_married_to_nh",
            "two_record_entitlement",
        ):
            if type(getattr(self, name)) is not bool:
                raise InvalidFamilyInput(f"{name} must be boolean")
        _fra(self.fra_month)
        if not isinstance(self.earnings, WorkEarnings) or (
            self.estimated_earnings is not None
            and not isinstance(self.estimated_earnings, WorkEarnings)
        ):
            raise InvalidFamilyInput("Supply explicit WorkEarnings")
        for decision in (self.grace, self.estimated_grace):
            if decision is not None:
                _checked_result(decision, GraceYearDecision, "grace decision")
        if self.death_month is not None:
            _months((self.death_month,), "Death month")
            if any(m >= self.death_month for m in entitled):
                raise InvalidFamilyInput(
                    "No own entitlement in or after death month"
                )
            for work in (self.earnings, self.estimated_earnings):
                if work is not None and (
                    any(work.wages[self.death_month :])
                    or any(
                        m > self.death_month
                        for m in work.self_employment_months
                    )
                ):
                    raise InvalidFamilyInput(
                        "No work earned after the death month"
                    )
        if any(gross[m - 1] and m not in entitled for m in range(1, 13)):
            raise InvalidFamilyInput("Nonzero gross requires entitlement")
        if any(gross[m - 1] and not original[m - 1] for m in entitled):
            raise InvalidFamilyInput(
                "A positive gross needs a positive original share"
            )
        if any(
            types[m - 1] is not BenefitType.DIVORCED_SPOUSE
            for m in self.divorced_months
        ):
            raise InvalidFamilyInput(
                "Divorce exception months need divorced-spouse benefits"
            )
        if any(
            types[m - 1] not in (BenefitType.CHILD, BenefitType.WIDOW)
            for m in self.own_work_exempt_months
        ):
            raise InvalidFamilyInput(
                "Child or widow benefits are required for other own-work exemptions"
            )
        if self.deemed_entitled:
            if any(
                types[m - 1]
                not in (
                    BenefitType.CHILD,
                    BenefitType.CDB,
                    BenefitType.MOTHER_FATHER,
                )
                for m in entitled
            ):
                raise InvalidFamilyInput(
                    "Deemed entitlement requires child or mother/father benefits"
                )
            if any(
                types[m - 1] is BenefitType.CHILD
                and m not in self.deemed_child_age_18_months
                for m in entitled
            ):
                raise InvalidFamilyInput(
                    "Deemed child's age 18 facts must be explicit"
                )
        object.__setattr__(self, "benefit_types", types)
        object.__setattr__(self, "entitled_months", entitled)
        object.__setattr__(self, "gross_rates", gross)
        object.__setattr__(self, "original_rates", original)


@dataclass(frozen=True)
class RecordYear:
    year: int
    nh_id: str
    kind: RecordKind = RecordKind.RETIREMENT
    beneficiaries: tuple[RETBeneficiary, ...] = ()
    family_maximum_binding_months: frozenset[int] = field(
        default_factory=frozenset
    )
    other_deduction_months: frozenset[int] = field(default_factory=frozenset)
    fiscal_year: bool = False
    short_taxable_year: bool = False
    suspension_method: SuspensionMethod = SuspensionMethod.FULL_MONTH
    foreign_work: bool = False
    vocational_rehabilitation_refusal: bool = False

    def __post_init__(self):
        if type(self.year) is not int or self.year < 1:
            raise InvalidFamilyInput("Payment year must be positive")
        if not isinstance(self.nh_id, str) or not self.nh_id.strip():
            raise InvalidFamilyInput("Supply a number-holder identity")
        if not isinstance(self.kind, RecordKind) or not isinstance(
            self.suspension_method, SuspensionMethod
        ):
            raise InvalidFamilyInput(
                "Use explicit record and suspension kinds"
            )
        beneficiaries = _sequence(self.beneficiaries, "Beneficiaries")
        if not beneficiaries or any(
            not isinstance(b, RETBeneficiary) for b in beneficiaries
        ):
            raise InvalidFamilyInput("A record needs explicit beneficiaries")
        ids = [b.beneficiary_id for b in beneficiaries]
        if len(ids) != len(set(ids)):
            raise InvalidFamilyInput("Duplicate beneficiary identity")
        if (self.nh_id in ids) == (self.kind is RecordKind.DECEASED):
            raise InvalidFamilyInput(
                "Living NH must be present; deceased NH must be absent"
            )
        for name in (
            "fiscal_year",
            "short_taxable_year",
            "foreign_work",
            "vocational_rehabilitation_refusal",
        ):
            if type(getattr(self, name)) is not bool:
                raise InvalidFamilyInput(f"{name} must be boolean")
        for name in (
            "family_maximum_binding_months",
            "other_deduction_months",
        ):
            object.__setattr__(self, name, _months(getattr(self, name), name))
        for b in beneficiaries:
            if b.deemed_entitled and (
                b.beneficiary_id == self.nh_id
                or self.kind is not RecordKind.RETIREMENT
            ):
                raise InvalidFamilyInput(
                    "Deemed entitlement requires a different living RIB NH"
                )
            if b.deemed_entitled:
                nh = beneficiaries[ids.index(self.nh_id)]
                if any(
                    m not in nh.entitled_months
                    or nh.benefit_types[m - 1] is not BenefitType.RIB
                    for m in b.entitled_months
                ):
                    raise InvalidFamilyInput(
                        "Deemed entitlement requires the NH's RIB entitlement"
                    )
            for decision in (b.grace, b.estimated_grace):
                if decision is None:
                    continue
                _checked_result(decision, GraceYearDecision, "grace decision")
                if decision.next_state.last_processed_year != self.year:
                    raise InvalidFamilyInput(
                        "Grace evidence must belong to the payment year"
                    )
                if not decision.met_eligible_months <= b.entitled_months:
                    raise InvalidFamilyInput(
                        "Grace eligibility requires entitlement"
                    )
            if b.beneficiary_id == self.nh_id:
                if any(
                    b.benefit_types[m - 1]
                    not in (BenefitType.RIB, BenefitType.DIB)
                    for m in b.entitled_months
                ):
                    raise InvalidFamilyInput("A living NH receives RIB or DIB")
        object.__setattr__(self, "beneficiaries", beneficiaries)


def calculated_excess(earnings: object, exempt: object, rate: object) -> int:
    """Act 203(f)(3); POMS .080: exact multiplication, then dollar floor.

    Scalar primitive also reproduces historical examples outside the
    ledger's supported payment years. Ledger callers never supply a rate.
    """
    income = _exact(earnings, "Earnings")
    amount = _exact(exempt, "Exempt amount")
    fraction = _exact(rate, "Withholding rate")
    if amount < 0 or fraction not in (Fraction(1, 2), Fraction(1, 3)):
        raise InvalidFamilyInput(
            "Use a nonnegative exempt amount and statutory rate"
        )
    return floor(max(Fraction(0), income - amount) * fraction)


def countable_earnings(
    earnings: WorkEarnings,
    fra_month: int | None,
    *,
    nese_proration_policy: NESEProrationPolicy = NESEProrationPolicy.FLOOR,
) -> Fraction:
    """RS .080B.2: pre-FRA wages plus monthly dollar-floored NESE.

    Losses use mathematical floor, the literal 'round down' instruction;
    truncation toward zero is an explicit judgment item in the design note.
    NESE is not prorated/rounded outside an FRA-attainment year.
    """
    if not isinstance(earnings, WorkEarnings):
        raise InvalidFamilyInput("Supply explicit WorkEarnings")
    if not isinstance(nese_proration_policy, NESEProrationPolicy):
        raise InvalidFamilyInput("Use an explicit NESE proration policy")
    _fra(fra_month)
    if fra_month == 0:
        return Fraction(0)
    if fra_month is None:
        return sum(earnings.wages, earnings.nese)
    before = fra_month - 1
    nese = Fraction(0)
    if earnings.self_employment_months:
        quotient = earnings.nese / len(earnings.self_employment_months)
        monthly = (
            floor(quotient)
            # Source conflict us:oasdi-ret-negative-nese-proration
            if nese_proration_policy is NESEProrationPolicy.FLOOR
            else int(quotient)
        )
        nese = Fraction(
            monthly
            * sum(m < fra_month for m in earnings.self_employment_months)
        )
    return sum(earnings.wages[:before], nese)


@_sealed_result
@dataclass(frozen=True, eq=False)
class PartialPaymentAllocation(_SealedResult, Mapping[str, Fraction]):
    """Exact net shares and the unpaid CFR .440 sub-dollar residual.

    Mapping operations refer to shares only. Shares plus the residual
    conserve the partial pool; 215(g)'s check floor is applied afterward.
    Each allocation's residual is in [0, $1), independently of check loss.
    """

    shares: Mapping[str, Fraction]
    undistributed_subdollar_residual: Fraction = Fraction(0)

    def __post_init__(self):
        if not isinstance(self.shares, Mapping):
            raise InvalidFamilyInput("Partial shares require a mapping")
        shares = {
            k: _exact(v, "Partial share") for k, v in self.shares.items()
        }
        residual = _exact(self.undistributed_subdollar_residual, "Residual")
        if (
            any(value < 0 for value in shares.values())
            or not 0 <= residual < 1
        ):
            raise InvalidFamilyInput("Invalid partial shares or residual")
        object.__setattr__(
            self, "shares", MappingProxyType(dict(sorted(shares.items())))
        )
        object.__setattr__(self, "undistributed_subdollar_residual", residual)

    def __getitem__(self, key: str) -> Fraction:
        _check_seal(self)
        return self.shares[key]

    def __iter__(self):
        _check_seal(self)
        return iter(self.shares)

    def __len__(self) -> int:
        _check_seal(self)
        return len(self.shares)


def partial_payments(
    total: object,
    rates: Mapping[str, object],
    original_rates: Mapping[str, object],
) -> PartialPaymentAllocation:
    """RS .110; CFR .439-.440: capped original-rate apportionment.

    Returns exact net amounts before 215(g), with no intermediate rounding.
    For three or more beneficiaries, stop when capped overflow is below $1
    and retain the last uncapped shares. Record that unpaid overflow apart
    from excess charged. The two-beneficiary rule pays the exact balance.
    """
    if not isinstance(rates, Mapping) or not isinstance(
        original_rates, Mapping
    ):
        raise InvalidFamilyInput("Partial rates require explicit mappings")
    amount = _exact(total, "Partial family benefit")
    caps = {k: _exact(v, "Rate") for k, v in rates.items()}
    weights = {
        k: _exact(v, "Original rate") for k, v in original_rates.items()
    }
    if (
        set(caps) != set(weights)
        or any(v < 0 for v in caps.values())
        or any(v <= 0 for v in weights.values())
    ):
        raise InvalidFamilyInput(
            "Positive original shares must match nonnegative caps"
        )
    if amount < 0 or amount > sum(caps.values(), Fraction(0)):
        raise InvalidFamilyInput(
            "Partial total must be bounded by available rates"
        )
    remaining = amount
    active = set(caps)
    result: dict[str, Fraction] = {}
    while active:
        weight = sum((weights[k] for k in active), Fraction(0))
        shares = {k: remaining * weights[k] / weight for k in active}
        capped = {k for k in active if shares[k] > caps[k]}
        if not capped:
            result.update(shares)
            break
        overflow = sum((shares[k] - caps[k] for k in capped), Fraction(0))
        if len(caps) >= 3 and overflow < 1:
            result.update({k: min(shares[k], caps[k]) for k in active})
            return _computed(
                PartialPaymentAllocation,
                result,
                undistributed_subdollar_residual=overflow,
            )
        for k in capped:
            result[k] = caps[k]
            remaining -= caps[k]
        active -= capped
    return _computed(PartialPaymentAllocation, result)


@_sealed_result
@dataclass(frozen=True)
class BeneficiaryMonth(_SealedResult):
    beneficiary_id: str
    month: int
    gross: Fraction
    net_due: Fraction
    deduction: Fraction
    payment: int
    provisional_net: Fraction
    provisional_deduction: Fraction
    provisional_payment: int
    nh_deduction: Fraction
    own_deduction: Fraction

    def __post_init__(self):
        if (
            not isinstance(self.beneficiary_id, str)
            or not self.beneficiary_id.strip()
        ):
            raise InvalidFamilyInput("A monthly result needs a beneficiary")
        _months((self.month,), "Result month")
        for name in (
            "gross",
            "net_due",
            "deduction",
            "provisional_net",
            "provisional_deduction",
            "nh_deduction",
            "own_deduction",
        ):
            value = _exact(getattr(self, name), name)
            if value < 0:
                raise InvalidFamilyInput(
                    "Monthly result amounts must be nonnegative"
                )
            object.__setattr__(self, name, value)
        if (
            self.gross != self.net_due + self.deduction
            or self.gross != self.provisional_net + self.provisional_deduction
            or self.deduction != self.nh_deduction + self.own_deduction
            or (self.gross * 10).denominator != 1
        ):
            raise InvalidFamilyInput(
                "Monthly gross, net and deductions do not reconcile"
            )
        for amount, payment in (
            (self.net_due, self.payment),
            (self.provisional_net, self.provisional_payment),
        ):
            if type(payment) is not int or payment != whole_dollars(amount):
                raise InvalidFamilyInput(
                    "Monthly check must floor its exact net amount"
                )


@_sealed_result
@dataclass(frozen=True)
class WorkerLedger(_SealedResult):
    """Excess charged and the separate unpaid allocation residual.

    Final deductions attributable to this worker are ``charged`` plus
    ``undistributed_subdollar_residual``; ``charged + uncharged = excess``.
    Provisional withholding uses full months and has no allocation residual.
    """

    beneficiary_id: str
    annual_exempt: Fraction
    monthly_exempt: Fraction
    withholding_rate: Fraction
    countable_earnings: Fraction
    excess: int
    charged: Fraction
    uncharged: Fraction
    estimated_excess: int
    provisional_withheld: Fraction
    undistributed_subdollar_residual: Fraction

    def __post_init__(self):
        if (
            not isinstance(self.beneficiary_id, str)
            or not self.beneficiary_id.strip()
        ):
            raise InvalidFamilyInput("A worker result needs a beneficiary")
        for name in (
            "annual_exempt",
            "monthly_exempt",
            "withholding_rate",
            "countable_earnings",
            "charged",
            "uncharged",
            "provisional_withheld",
            "undistributed_subdollar_residual",
        ):
            value = _exact(getattr(self, name), name)
            if name != "countable_earnings" and value < 0:
                raise InvalidFamilyInput(
                    "Worker result amounts must be nonnegative"
                )
            object.__setattr__(self, name, value)
        for name in ("excess", "estimated_excess"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise InvalidFamilyInput(
                    "Worker excess must be a nonnegative integer"
                )
        if (
            self.excess
            != calculated_excess(
                self.countable_earnings,
                self.annual_exempt,
                self.withholding_rate,
            )
            or self.charged + self.uncharged != self.excess
            or self.monthly_exempt
            not in (
                self.annual_exempt / 12,
                Fraction(ceil(self.annual_exempt / 12)),
            )
            or self.undistributed_subdollar_residual >= 1
        ):
            raise InvalidFamilyInput(
                "Worker excess, charges and limits do not reconcile"
            )


@_sealed_result
@dataclass(frozen=True)
class RETLedger(_SealedResult):
    year: int
    months: tuple[BeneficiaryMonth, ...]
    workers: tuple[WorkerLedger, ...]
    crediting_months: Mapping[str, frozenset[int]]
    reconciliation: Mapping[str, int]

    def __post_init__(self):
        if type(self.year) is not int or self.year < 2000:
            raise InvalidFamilyInput(
                "RET results require a supported calendar year"
            )
        months = tuple(
            _checked_result(row, BeneficiaryMonth, "monthly result")
            for row in _sequence(self.months, "Monthly results")
        )
        workers = tuple(
            _checked_result(row, WorkerLedger, "worker result")
            for row in _sequence(self.workers, "Worker results")
        )
        ids = tuple(row.beneficiary_id for row in workers)
        if (
            not ids
            or len(set(ids)) != len(ids)
            or {(row.beneficiary_id, row.month) for row in months}
            != {(key, month) for key in ids for month in range(1, 13)}
            or len(months) != 12 * len(ids)
        ):
            raise InvalidFamilyInput(
                "RET results need every beneficiary month exactly once"
            )
        if not isinstance(self.crediting_months, Mapping) or not isinstance(
            self.reconciliation, Mapping
        ):
            raise InvalidFamilyInput(
                "RET credits and reconciliation require mappings"
            )
        credits = {
            key: frozenset(
                row.month
                for row in months
                if row.beneficiary_id == key and row.deduction > 0
            )
            for key in ids
        }
        reconciliation = {
            key: sum(
                row.payment - row.provisional_payment
                for row in months
                if row.beneficiary_id == key
            )
            for key in ids
        }
        if (
            dict(self.crediting_months) != credits
            or any(
                type(month) is not int
                for values in self.crediting_months.values()
                for month in values
            )
            or dict(self.reconciliation) != reconciliation
            or any(
                type(amount) is not int
                for amount in self.reconciliation.values()
            )
            or sum(row.deduction for row in months)
            != sum(
                row.charged + row.undistributed_subdollar_residual
                for row in workers
            )
            or sum(row.provisional_deduction for row in months)
            != sum(row.provisional_withheld for row in workers)
        ):
            raise InvalidFamilyInput(
                "RET credits, reconciliation and deductions do not reconcile"
            )
        object.__setattr__(self, "months", months)
        object.__setattr__(self, "workers", workers)
        object.__setattr__(self, "crediting_months", MappingProxyType(credits))
        object.__setattr__(
            self, "reconciliation", MappingProxyType(reconciliation)
        )

    def for_beneficiary(
        self, beneficiary_id: str
    ) -> tuple[BeneficiaryMonth, ...]:
        _check_seal(self)
        return tuple(
            m for m in self.months if m.beneficiary_id == beneficiary_id
        )


def _protected(
    b: RETBeneficiary,
    month: int,
    wages: WorkEarnings,
    monthly: Fraction,
    *,
    provisional: bool = False,
) -> bool:
    grace = (
        b.estimated_grace
        if provisional and b.estimated_grace is not None
        else b.grace
    )
    return (
        month not in b.entitled_months
        or (b.fra_month is not None and month >= b.fra_month)
        # Source conflict us:oasdi-ret-own-work-age-exemptions
        or b.benefit_types[month - 1] in DISABILITY_TYPES
        or month in b.own_work_exempt_months
        or (
            grace is not None
            and grace.applies
            and month in grace.met_eligible_months
            and wages.wages[month - 1] <= monthly
            and month not in wages.substantial_service_months
        )
    )


def _divorced_excluded(b: RETBeneficiary, month: int) -> bool:
    return b.benefit_types[month - 1] is BenefitType.DIVORCED_SPOUSE and (
        b.nh_entitled_before_divorce or month in b.divorced_months
    )


def apply_ret_year(
    record: RecordYear,
    parameters: RETParameters | None = None,
    *,
    monthly_limit_policy: MonthlyLimitPolicy = MonthlyLimitPolicy.EXACT_TWELFTH,
    nese_proration_policy: NESEProrationPolicy = NESEProrationPolicy.FLOOR,
) -> RETLedger:
    """Apply NH excess first, then each person's own, without year carry.

    The result covers all twelve months, including zero-rate unentitled
    months. Uncharged excess is disclosed and expires; it is never an input
    to the next year's computation. Death preserves the full annual limit.
    """
    if not isinstance(record, RecordYear):
        raise InvalidFamilyInput("Supply explicit RecordYear")
    for beneficiary in record.beneficiaries:
        for decision in (beneficiary.grace, beneficiary.estimated_grace):
            if decision is not None:
                _checked_result(decision, GraceYearDecision, "grace decision")
    if not isinstance(monthly_limit_policy, MonthlyLimitPolicy):
        raise InvalidFamilyInput("Use an explicit monthly limit policy")
    if not isinstance(nese_proration_policy, NESEProrationPolicy):
        raise InvalidFamilyInput("Use an explicit NESE proration policy")
    if parameters is not None and not isinstance(parameters, RETParameters):
        raise InvalidFamilyInput("Use R1 RETParameters")
    if record.year < 2000:
        raise _computed(
            RETConfigurationUnsupported,
            UnsupportedReason.YEAR_BEFORE_2000,
            "FRA-year rules in this form start in 2000",
        )
    year = (
        parameters if parameters is not None else load_ret_parameters()
    ).for_year(record.year)
    refusals = (
        (record.fiscal_year, UnsupportedReason.FISCAL_YEAR),
        (record.short_taxable_year, UnsupportedReason.SHORT_TAXABLE_YEAR),
        (
            record.suspension_method is SuspensionMethod.PRORATED,
            UnsupportedReason.PRORATED_SUSPENSION,
        ),
        (
            record.suspension_method is SuspensionMethod.DEFERRED,
            UnsupportedReason.DEFERRED_SUSPENSION,
        ),
        (
            record.suspension_method is SuspensionMethod.PROTEST_PARTIAL,
            UnsupportedReason.PROTEST_PARTIAL_SUSPENSION,
        ),
        (record.foreign_work, UnsupportedReason.FOREIGN_WORK),
        (
            record.vocational_rehabilitation_refusal,
            UnsupportedReason.VOCATIONAL_REHABILITATION,
        ),
        (
            bool(record.other_deduction_months),
            UnsupportedReason.OTHER_DEDUCTION,
        ),
    )
    for condition, reason in refusals:
        if condition:
            raise _computed(
                RETConfigurationUnsupported,
                reason,
                "Outside R2 part (a)'s admitted scope",
            )
    for b in record.beneficiaries:
        # Source conflict us:oasdi-ret-deemed-entitlement-basis
        if b.deemed_entitled and not b.deemed_married_to_nh:
            raise _computed(
                RETConfigurationUnsupported,
                UnsupportedReason.DEEMED_ENTITLEMENT_BASIS,
                "Unmarried deemed entitlement: RS .140 is broader than Act 203(b)(1) / CFR .420",
                beneficiary_id=b.beneficiary_id,
            )
        # Source conflict us:oasdi-ret-deemed-entitlement-basis
        if b.deemed_entitled and any(
            b.benefit_types[m - 1] is BenefitType.CHILD
            for m in b.entitled_months
        ):
            raise _computed(
                RETConfigurationUnsupported,
                UnsupportedReason.DEEMED_ENTITLEMENT_BASIS,
                "Act adult-child basis versus CFR .420 disability basis needs judgment",
                beneficiary_id=b.beneficiary_id,
            )
    people = {
        b.beneficiary_id: b
        for b in sorted(record.beneficiaries, key=lambda b: b.beneficiary_id)
    }
    facts = {}
    for key, b in people.items():
        higher = b.fra_month is not None and b.fra_month > 0
        exempt = (
            year.higher_exempt_amount if higher else year.lower_exempt_amount
        ).value
        rate = (
            year.higher_withholding_rate
            if higher
            else year.lower_withholding_rate
        ).value
        monthly = exempt / 12
        if (
            monthly_limit_policy
            is MonthlyLimitPolicy.NONSTATUTORY_CHART_CEILING
        ):
            monthly = Fraction(ceil(monthly))
        actual = countable_earnings(
            b.earnings,
            b.fra_month,
            nese_proration_policy=nese_proration_policy,
        )
        estimated = b.estimated_earnings or b.earnings
        excess = calculated_excess(actual, exempt, rate)
        estimate = calculated_excess(
            countable_earnings(
                estimated,
                b.fra_month,
                nese_proration_policy=nese_proration_policy,
            ),
            exempt,
            rate,
        )
        if b.two_record_entitlement and (excess or estimate):
            raise _computed(
                RETConfigurationUnsupported,
                UnsupportedReason.TWO_RECORD_EARNINGS,
                "RS .145-.150 need coordinated records",
                beneficiary_id=key,
            )
        facts[key] = (
            exempt,
            monthly,
            rate,
            actual,
            excess,
            estimate,
            estimated,
        )

    def charge(provisional: bool):
        net = {
            (k, m): b.gross_rates[m - 1]
            for k, b in people.items()
            for m in range(1, 13)
        }
        nh_deductions = {km: Fraction(0) for km in net}
        own_deductions = dict(nh_deductions)
        charged = {k: Fraction(0) for k in people}
        residuals = dict(charged)
        # Statutory priority is independent of caller order or identity sort.
        order = ([record.nh_id] if record.nh_id in people else []) + [
            k for k in people if k != record.nh_id
        ]
        for key in order:
            b = people[key]
            _, monthly, _, _, excess, estimate, estimated = facts[key]
            remaining = Fraction(estimate if provisional else excess)
            earnings = estimated if provisional else b.earnings
            for m in range(1, 13):
                if not remaining or _protected(
                    b, m, earnings, monthly, provisional=provisional
                ):
                    continue
                is_nh = key == record.nh_id
                targets = (
                    [k for k in people if not _divorced_excluded(people[k], m)]
                    if is_nh
                    else [key]
                )
                # Original entitlement shares include an entitled person
                # whose payable rate is zero after G's reductions.
                caps = {
                    k: net[k, m]
                    for k in targets
                    if m in people[k].entitled_months
                    and people[k].original_rates[m - 1] > 0
                }
                total = sum(caps.values(), Fraction(0))
                if not total:
                    continue
                if (
                    not is_nh
                    and m in record.family_maximum_binding_months
                    and any(
                        m in other.entitled_months
                        and other.original_rates[m - 1] > 0
                        for k, other in people.items()
                        if k != key
                    )
                ):
                    raise _computed(
                        RETConfigurationUnsupported,
                        UnsupportedReason.DEDUCTION_BEFORE_REDUCTION,
                        "Auxiliary work frees binding maximum room; part (b) readjustment required",
                        beneficiary_id=key,
                    )
                taken = min(remaining, total)
                if provisional or taken == total:
                    payments = {k: Fraction(0) for k in caps}
                else:
                    payments = partial_payments(
                        total - taken,
                        caps,
                        {k: people[k].original_rates[m - 1] for k in caps},
                    )
                    residuals[key] += payments.undistributed_subdollar_residual
                for k, cap in caps.items():
                    deducted = cap - payments[k]
                    net[k, m] = payments[k]
                    (nh_deductions if is_nh else own_deductions)[
                        k, m
                    ] += deducted
                    if provisional:
                        charged[key] += deducted
                if not provisional:
                    charged[key] += taken
                remaining -= taken
        return net, nh_deductions, own_deductions, charged, residuals

    final, nh, own, charged, residuals = charge(False)
    provisional, _, _, suspended, _ = charge(True)
    rows = tuple(
        _computed(
            BeneficiaryMonth,
            k,
            m,
            b.gross_rates[m - 1],
            final[k, m],
            b.gross_rates[m - 1] - final[k, m],
            whole_dollars(final[k, m]),
            provisional[k, m],
            b.gross_rates[m - 1] - provisional[k, m],
            whole_dollars(provisional[k, m]),
            nh[k, m],
            own[k, m],
        )
        for k, b in people.items()
        for m in range(1, 13)
    )
    workers = tuple(
        _computed(
            WorkerLedger,
            k,
            *facts[k][:5],
            charged[k],
            Fraction(facts[k][4]) - charged[k],
            facts[k][5],
            suspended[k],
            residuals[k],
        )
        for k in people
    )
    credits = {
        k: frozenset(
            row.month
            for row in rows
            if row.beneficiary_id == k and row.deduction > 0
        )
        for k in people
    }
    reconciliation = {
        k: sum(
            row.payment - row.provisional_payment
            for row in rows
            if row.beneficiary_id == k
        )
        for k in people
    }
    return _computed(
        RETLedger,
        record.year,
        rows,
        workers,
        MappingProxyType(credits),
        MappingProxyType(reconciliation),
    )


@_sealed_result
@dataclass(frozen=True)
class RETOutcome(_SealedOutcome):
    key: str
    weight: Fraction
    ledger: RETLedger | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _check_evaluation_inputs(self.key, self.weight, lambda: None)
        if self.ledger is not None:
            _checked_result(self.ledger, RETLedger, "ledger")
        if self.unsupported is not None:
            _check_refusal(self.unsupported)
        weight = _exact(self.weight, "Outcome weight")
        if weight < 0 or (self.ledger is None) == (self.unsupported is None):
            raise InvalidFamilyInput(
                "One ledger/refusal and nonnegative weight required"
            )
        object.__setattr__(self, "weight", weight)

    @property
    def supported(self) -> bool:
        _check_seal(self)
        return self.ledger is not None


def evaluate_ret(
    key: str, weight: object, compute: Callable[[], RETLedger]
) -> RETOutcome:
    """Retain shared coverage refusals; accept only computed R2 ledgers."""
    weight = _exact(weight, "Outcome weight")
    _check_evaluation_inputs(key, weight, compute)
    try:
        ledger = compute()
    except FamilyConfigurationUnsupported as error:
        return _computed(RETOutcome, key, weight, None, error)
    _checked_result(ledger, RETLedger, "ledger")
    return _computed(RETOutcome, key, weight, ledger, None)


RETDenominator = FamilyDenominator


def count_ret_outcomes(outcomes: Iterable[_SealedOutcome]) -> RETDenominator:
    """Use Track B's single denominator for every registered layer."""
    return count_family_outcomes(outcomes)


def weighted_ret_total(outcomes: Iterable[RETOutcome]) -> Fraction:
    rows = tuple(
        _checked_result(outcome, RETOutcome, "RET outcome")
        for outcome in outcomes
    )
    denominator = count_ret_outcomes(rows)
    if denominator.unsupported_rows:
        raise FamilyTargetBlocked(
            f"{denominator.unsupported_rows} of {denominator.rows} RET rows refused; total needs every row"
        )
    return sum(
        (o.weight * sum(m.payment for m in o.ledger.months) for o in rows),
        Fraction(0),
    )
