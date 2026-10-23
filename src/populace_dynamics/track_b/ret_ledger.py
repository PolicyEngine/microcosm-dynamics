"""R2: an exact, single-record calendar-year RET ledger.

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
Auxiliary work readjusts binding family-maximum rates through G when the
caller supplies the monthly statutory and household facts. Other deduction
events remain refused. No unsupported row is dropped
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
with G and R3. Only computation builds them; consumption validates their
identities and nested seals. Serialization is an input error: persist
declared inputs and recompute. Public entries validate declared schemas
once, then compute with owned snapshots and built-in fractions. RET
refusals bind exactly RETUnsupportedReason while retaining
FamilyConfigurationUnsupported as the shared catch type. The common
denominator counts every layer's sealed rows;
RET money aggregation accepts only RETOutcome and RETLedger values.
Beneficiary identities and partial-payment keys are nonempty built-in
strings, so caller-defined hashing cannot change sealed ledger lookups.
Ordered monthly arrays and outcome collections admit tuple/list only and
become tuples without dropping elements. Month memberships become
frozensets. Evaluators check provenance, layer and integrity, not freshness
or family attribution. A callback may return an earlier genuine result or
re-raise a genuine refusal; attribution, key and weight remain declarations.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from math import ceil, floor
from types import MappingProxyType

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b._provenance import (
    _check_refusal,
    _check_seal,
    _checked_result,
    _computed,
    _construct_declared,
    _declared_input,
    _detached_result,
    _exact_number,
    _sealed_refusal,
    _sealed_result,
    _SealedOutcome,
    _SealedResult,
    _validated_entry,
)
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    FamilyDenominator,
    FamilyTargetBlocked,
    InvalidFamilyInput,
    _check_evaluation_inputs,
    _count_family_outcomes_validated,
    _whole_dollars_validated,
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
    FAMILY_CONTEXT_REQUIRED = "deduction_readjustment_requires_family_context"
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
    if isinstance(value, float):
        raise InvalidFamilyInput(f"{label} requires an exact number")
    return _exact_number(value, label)


def _identity(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise InvalidFamilyInput(f"{label} needs a nonempty built-in identity")
    return value


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


@_declared_input
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


@_declared_input
@dataclass(frozen=True)
class RETBeneficiary:
    """One person's monthly G rates and dated entitlement/work facts.

    ``fra_month=0`` means FRA before this year, ``None`` means after it.
    Survivors use the RIB FRA. ``divorced_months`` lists months with at
    least two years since divorce; prior NH RIB entitlement is the other
    Act 203(b)(2) exception. ``deemed_entitled`` and
    ``deemed_married_to_nh`` assert the married recipient in Act 203(b)(1)
    / CFR .420; both require the marriage, so an unmarried deemed recipient
    (RS 02501.140's broader wording) is an input error: that person is not
    on this NH's ledger. An ordinary child's Act 203(b)(1) age facts need
    explicit ``deemed_child_age_18_months``; such a married non-disabled
    child is entitled only if 402(d)(5) kept the benefit through a marriage
    in whose month, or in the third month before which, the child was
    under a disability (402(s)(2)); recovery may come before or after the
    marriage. CFR .420 omits that residual case, so it stays refused. Own
    two-record excess is still refused.
    ``own_work_exempt_months`` must stay empty: Act 203(f)(1)(C) reaches
    only a child under a disability that month or three months before
    (202(s)(3)), and (D)'s widow(er) entitled before 60 is a disabled
    widow(er) whose entitlement ends at the termination month (402(e)(1)),
    so every month the Act exempts is a CDB or DWB month, which the ledger
    exempts automatically.
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
        _identity(self.beneficiary_id, "A beneficiary")
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
        if self.own_work_exempt_months:
            raise InvalidFamilyInput(
                "Act 203(f)(1)(C)-(D) exempt only disability-based months "
                "(202(s)(3); 402(e)(1)); declare them as CDB or DWB"
            )
        if self.deemed_entitled:
            # Act 203(b)(1) and 20 CFR 404.420 deem only a recipient married
            # to the NH; RS 02501.140's broader wording yields to them.
            # Source conflict us:oasdi-ret-deemed-entitlement-basis
            if not self.deemed_married_to_nh:
                raise InvalidFamilyInput(
                    "Deemed entitlement requires marriage to the NH "
                    "(Act 203(b)(1); 20 CFR 404.420)"
                )
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


@_declared_input
@dataclass(frozen=True)
class RETFamilyMonth:
    """G's declared monthly inputs, including household memberships.

    Ordered beneficiaries accept tuple/list; household keys and values are
    nonempty built-in strings. These are the same dated inputs used to
    compute the RET beneficiary's gross/original rates, not inferred from
    those rates. Household membership is the caller's GN 02603.090 fact.
    """

    state: g.RecordState
    beneficiaries: tuple[g.Beneficiary, ...]
    params: g.SSAParameters
    households: Mapping[str, str]
    standalone: bool = True

    def __post_init__(self):
        ids = tuple(b.beneficiary_id for b in self.beneficiaries)
        if len(set(ids)) != len(ids):
            raise InvalidFamilyInput("Duplicate monthly family beneficiary")
        if set(self.households) != set(ids):
            raise InvalidFamilyInput(
                "Households must identify every monthly family beneficiary"
            )
        for key, household in self.households.items():
            _identity(key, "Household beneficiary")
            _identity(household, "Household")
        object.__setattr__(self, "households", dict(self.households))


@_declared_input
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
    family_months: Mapping[int, RETFamilyMonth] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.year) is not int or self.year < 1:
            raise InvalidFamilyInput("Payment year must be positive")
        _identity(self.nh_id, "The number holder")
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
        _months(self.family_months, "Family context months")
        expected_kind = {
            RecordKind.RETIREMENT: g.FamilyKind.RETIREMENT,
            RecordKind.DISABILITY: g.FamilyKind.DISABILITY,
            RecordKind.DECEASED: g.FamilyKind.SURVIVOR,
        }[self.kind]
        for month, context in self.family_months.items():
            if context.state.kind is not expected_kind:
                raise InvalidFamilyInput("G and RET record kinds differ")
            auxiliary_ids = {
                b.beneficiary_id
                for b in beneficiaries
                if b.beneficiary_id != self.nh_id
                and month in b.entitled_months
            }
            if {
                b.beneficiary_id for b in context.beneficiaries
            } != auxiliary_ids:
                raise InvalidFamilyInput(
                    "G context must include every entitled RET auxiliary"
                )
            role_types = {
                g.Role.SPOUSE: (BenefitType.SPOUSE,),
                g.Role.SPOUSE_CHILD_IN_CARE: (BenefitType.SPOUSE,),
                g.Role.DIVORCED_SPOUSE: (BenefitType.DIVORCED_SPOUSE,),
                g.Role.CHILD: (BenefitType.CHILD, BenefitType.CDB),
                g.Role.WIDOW: (BenefitType.WIDOW,),
                g.Role.SURVIVING_DIVORCED_SPOUSE: (BenefitType.WIDOW,),
                g.Role.MOTHER_FATHER: (BenefitType.MOTHER_FATHER,),
                g.Role.DISABLED_WIDOW: (BenefitType.DWB,),
            }
            ret_people = {b.beneficiary_id: b for b in beneficiaries}
            for auxiliary in context.beneficiaries:
                if ret_people[auxiliary.beneficiary_id].benefit_types[
                    month - 1
                ] not in role_types.get(auxiliary.role, ()):
                    raise InvalidFamilyInput("G and RET benefit types differ")
        object.__setattr__(self, "family_months", dict(self.family_months))


@_validated_entry
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


@_validated_entry
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
    if type(earnings) is not WorkEarnings:
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
            _identity(k, "Partial shares"): _exact(v, "Partial share")
            for k, v in self.shares.items()
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
        return self.shares[_identity(key, "Partial-share lookup")]

    def __iter__(self):
        _check_seal(self)
        return iter(self.shares)

    def __len__(self) -> int:
        _check_seal(self)
        return len(self.shares)


@_validated_entry
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
    caps = {
        _identity(k, "Partial rates"): _exact(v, "Rate")
        for k, v in rates.items()
    }
    weights = {
        _identity(k, "Original rates"): _exact(v, "Original rate")
        for k, v in original_rates.items()
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
        _identity(self.beneficiary_id, "A monthly result")
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
            if type(payment) is not int or payment != _whole_dollars_validated(
                amount
            ):
                raise InvalidFamilyInput(
                    "Monthly check must floor its exact net amount"
                )


@_sealed_result
@dataclass(frozen=True)
class RedistributedBeneficiaryMonth(_SealedResult):
    """A month with separately determined final and provisional gross.

    GN 02603.050C/D and RS 02501.160 can give different final and
    provisional gross rates. Delay of a household increase is not a work
    deduction. NH partial shares can also make the reconstructed gross an
    exact fraction of a dime. This separate sealed result preserves the
    original BeneficiaryMonth serialization for previously supported rows.
    """

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
    provisional_gross: Fraction

    def __post_init__(self):
        _identity(self.beneficiary_id, "A monthly result")
        _months((self.month,), "Result month")
        for name in (
            "gross",
            "net_due",
            "deduction",
            "provisional_gross",
            "provisional_net",
            "provisional_deduction",
            "nh_deduction",
            "own_deduction",
        ):
            value = _exact(getattr(self, name), name)
            if value < 0:
                raise InvalidFamilyInput("Monthly amounts must be nonnegative")
            object.__setattr__(self, name, value)
        if (
            self.gross != self.net_due + self.deduction
            or self.provisional_gross
            != self.provisional_net + self.provisional_deduction
            or self.deduction != self.nh_deduction + self.own_deduction
        ):
            raise InvalidFamilyInput(
                "Readjusted gross, net and deductions do not reconcile"
            )
        for amount, payment in (
            (self.net_due, self.payment),
            (self.provisional_net, self.provisional_payment),
        ):
            if type(payment) is not int or payment != _whole_dollars_validated(
                amount
            ):
                raise InvalidFamilyInput(
                    "Monthly check must floor its exact net amount"
                )


def _checked_month(row):
    if type(row) not in (BeneficiaryMonth, RedistributedBeneficiaryMonth):
        raise InvalidFamilyInput("Expected a sealed RET monthly result")
    _check_seal(row)
    return row


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
        _identity(self.beneficiary_id, "A worker result")
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
            != _calculated_excess_validated(
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
    months: tuple[BeneficiaryMonth | RedistributedBeneficiaryMonth, ...]
    workers: tuple[WorkerLedger, ...]
    crediting_months: Mapping[str, frozenset[int]]
    reconciliation: Mapping[str, int]

    def __post_init__(self):
        if type(self.year) is not int or self.year < 2000:
            raise InvalidFamilyInput(
                "RET results require a supported calendar year"
            )
        months = tuple(
            _checked_month(row)
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

    @_validated_entry
    def for_beneficiary(
        self, beneficiary_id: str
    ) -> tuple[BeneficiaryMonth | RedistributedBeneficiaryMonth, ...]:
        _check_seal(self)
        _identity(beneficiary_id, "Beneficiary lookup")
        return tuple(
            _detached_result(m)
            for m in self.months
            if m.beneficiary_id == beneficiary_id
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


@_validated_entry
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
    if type(record) is not RecordYear:
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
    # Retain the G facts needed for money-changing readjustment. A caller's
    # reduced rates cannot identify age reductions or dual entitlement.
    held_family_refusals = []
    for month, context in sorted(record.family_months.items()):
        try:
            baseline = g._family_benefits_validated(
                context.state,
                context.beneficiaries,
                payment_month=_construct_declared(
                    g.YearMonth, record.year, month
                ),
                params=context.params,
                standalone=context.standalone,
            )
        except FamilyConfigurationUnsupported as error:
            held_family_refusals.append(error)
            continue
        baseline_rows = {b.beneficiary_id: b for b in baseline.beneficiaries}
        if record.kind is not RecordKind.DECEASED:
            nh = next(
                b
                for b in record.beneficiaries
                if b.beneficiary_id == record.nh_id
            )
            if (baseline.worker_benefit is not None) != (
                month in nh.entitled_months
            ):
                raise InvalidFamilyInput(
                    "G and RET NH entitlement facts differ"
                )
        if baseline.family_maximum_binding != (
            month in record.family_maximum_binding_months
        ):
            raise InvalidFamilyInput("G and RET binding maximum facts differ")
        for beneficiary in record.beneficiaries:
            key = beneficiary.beneficiary_id
            if month not in beneficiary.entitled_months:
                continue
            if key == record.nh_id:
                gross = baseline.worker_benefit
                original = baseline.pia
            else:
                if not baseline_rows[key].entitled:
                    raise InvalidFamilyInput(
                        "G and RET auxiliary entitlement facts differ"
                    )
                gross = baseline_rows[key].auxiliary_payable
                original = baseline_rows[key].original_benefit
            if (
                gross != beneficiary.gross_rates[month - 1]
                or original != beneficiary.original_rates[month - 1]
            ):
                raise InvalidFamilyInput("G context does not match RET rates")
    if held_family_refusals:
        raise held_family_refusals[0]
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
        # Source conflict us:oasdi-ret-other-deductee-scope
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
                "Outside R2's admitted scope",
            )
    for b in record.beneficiaries:
        # Source conflict us:oasdi-ret-deemed-entitlement-basis
        if b.deemed_entitled and any(
            b.benefit_types[m - 1] is BenefitType.CHILD
            for m in b.entitled_months
        ):
            raise _computed(
                RETConfigurationUnsupported,
                UnsupportedReason.DEEMED_ENTITLEMENT_BASIS,
                "A married non-disabled adult child keeps CIB only through "
                "402(d)(5) and 402(s)(2); CFR .420 omits that residual case",
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
        actual = _countable_earnings_validated(
            b.earnings,
            b.fra_month,
            nese_proration_policy=nese_proration_policy,
        )
        estimated = b.estimated_earnings or b.earnings
        excess = _calculated_excess_validated(actual, exempt, rate)
        estimate = _calculated_excess_validated(
            _countable_earnings_validated(
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
                taken = min(remaining, total)
                if provisional or taken == total:
                    payments = {k: Fraction(0) for k in caps}
                else:
                    payments = _partial_payments_validated(
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
        gross = {
            (k, m): b.gross_rates[m - 1]
            for k, b in people.items()
            for m in range(1, 13)
        }
        # RS 02501.155A.2: charge every worker against their own adjusted
        # rate first. Redistribute only after all that month's workers have
        # been charged, so changing beneficiary order cannot change excess.
        for m in sorted(record.family_maximum_binding_months):
            deductees = {
                k: net[k, m]
                for k in people
                if k != record.nh_id and own_deductions[k, m] > 0
            }
            if not deductees:
                continue
            if not any(
                m in b.entitled_months and b.original_rates[m - 1] > 0
                for k, b in people.items()
                if k not in deductees
            ):
                continue
            if m not in record.family_months:
                raise _computed(
                    RETConfigurationUnsupported,
                    UnsupportedReason.FAMILY_CONTEXT_REQUIRED,
                    "Deduction readjustment needs G age, dual-entitlement, "
                    "maximum and household facts for this month",
                )
            context = record.family_months[m]
            events = {
                k: _construct_declared(
                    g.BenefitDeduction,
                    g.DeductionReason.OWN_EARNINGS_TEST,
                    payable,
                    not provisional,
                )
                for k, payable in deductees.items()
            }
            worker_deductions = {
                b.beneficiary_id: nh_deductions[b.beneficiary_id, m]
                for b in context.beneficiaries
                if nh_deductions[b.beneficiary_id, m]
            }
            adjusted = g._family_benefits_after_deductions_validated(
                context.state,
                context.beneficiaries,
                payment_month=_construct_declared(g.YearMonth, record.year, m),
                params=context.params,
                deductions=events,
                households=context.households,
                standalone=context.standalone,
                worker_deductions=worker_deductions,
            )
            for row in adjusted.beneficiaries:
                k = row.beneficiary_id
                net[k, m] = row.auxiliary_payable
                gross[k, m] = (
                    net[k, m] + nh_deductions[k, m] + own_deductions[k, m]
                )
        return net, nh_deductions, own_deductions, charged, residuals, gross

    final, nh, own, charged, residuals, gross = charge(False)
    (
        provisional,
        provisional_nh,
        provisional_own,
        suspended,
        _,
        provisional_gross,
    ) = charge(True)

    def monthly_row(k, m):
        values = (
            k,
            m,
            gross[k, m],
            final[k, m],
            nh[k, m] + own[k, m],
            _whole_dollars_validated(final[k, m]),
            provisional[k, m],
            provisional_nh[k, m] + provisional_own[k, m],
            _whole_dollars_validated(provisional[k, m]),
            nh[k, m],
            own[k, m],
        )
        if (
            gross[k, m] != provisional_gross[k, m]
            or (gross[k, m] * 10).denominator != 1
        ):
            return _computed(
                RedistributedBeneficiaryMonth,
                *values,
                provisional_gross[k, m],
            )
        return _computed(BeneficiaryMonth, *values)

    rows = tuple(monthly_row(k, m) for k in people for m in range(1, 13))
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


@_validated_entry
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


@_validated_entry
def count_ret_outcomes(outcomes: Sequence[_SealedOutcome]) -> RETDenominator:
    """Use Track B's single denominator for every registered layer."""
    return _count_family_outcomes_validated(outcomes)


@_validated_entry
def weighted_ret_total(outcomes: Sequence[RETOutcome]) -> Fraction:
    rows = tuple(
        _checked_result(outcome, RETOutcome, "RET outcome")
        for outcome in outcomes
    )
    denominator = _count_ret_outcomes_validated(rows)
    if denominator.unsupported_rows:
        raise FamilyTargetBlocked(
            f"{denominator.unsupported_rows} of {denominator.rows} RET rows refused; total needs every row"
        )
    return sum(
        (o.weight * sum(m.payment for m in o.ledger.months) for o in rows),
        Fraction(0),
    )


# Internal calls consume the snapshot owned by the public boundary.
_apply_ret_year_validated = apply_ret_year.__wrapped__
_calculated_excess_validated = calculated_excess.__wrapped__
_count_ret_outcomes_validated = count_ret_outcomes.__wrapped__
_countable_earnings_validated = countable_earnings.__wrapped__
_evaluate_ret_validated = evaluate_ret.__wrapped__
_partial_payments_validated = partial_payments.__wrapped__
_weighted_ret_total_validated = weighted_ret_total.__wrapped__
