"""Track B insured status, version track-b-insured-v1.

Verification class: statutory conformance. Admitted scope: declared invented
histories and captured statutory examples only; no population, behavioral,
or forecast claim. Act 213, 214, 216(i), 223(c); 20 CFR 404 subpart B
and 404.315/.320/.321;
POMS RS 00301. Every year is declared, including zero and unknown years.
Medical onset declares continuous disability through the query month,
subject to an established historical period's ending under 404.321(b); it
never establishes an administrative period of disability. An established
period ends no later than the month before full retirement age; an unknown
ending includes every candidate end quarter from insured start through
query/cap and permitted continuation. The cap never establishes the end.
The alternate test's 20/40 exclusion uses only quarters beginning before
the FRA month, whether or not a period is declared established. For an
established period, the exclusion witness must also begin by the declared
end or continuity month minus two, clamped at onset, or onset when neither
date is known. This earliest-completion bound also applies to FRA/death
endings without inferring recovery from them. For ordinary validity only,
a historical recovery ending supplies the latest disabled month, two months
before the end. Endings from February 1981, FRA endings and death endings
imply no recovery month. Prior periods are all used or all disregarded in
the alternate continuous-QC clock, retaining credited endpoints. UNKNOWN
establishment before FRA uses onset too: an established completion can end
before a later DISABILITY witness. FULLY and CURRENTLY retain favorable
disregard of the period. Declared absence keeps the ordinary result. Where
the literal and period-covered readings of RS00301.480 A differ, the
alternate route retains its named refusal.
Dated continuity restricts possible endings without establishing an end;
a date beyond the query quarter makes that quarter interior to the period.
Disability tests
scan onset and later quarters; period establishment and section 214(c)
applicability carry explicit provenance. A declaration is rejected only
when every ordinary and possible specialist completion is impossible;
assignment-independent minimum-QC proofs precede boundary complexity, skip
unknown prior histories and stop at six QCs for blindness. Foreign credits
preserve an unmodeled route before every credit-count proof; no totalization
minimum or eligibility rule is claimed here. Fully-insured-only flags cannot
bypass a failed recent-rule scan under upper credits, but retain a possible
pre1956 alternate. Blindness removes the recent-credit requirement;
UNKNOWN prior history skips the known-history scan.
After the stronger minimum proof, every route within the declared credit
envelope requires six QCs feasible by the immutable start horizon, except
blindness with a fully-insured-only flag. UNKNOWN prior history cannot
remove this floor. An established period's alternate witness must use a
single start that also clears prior-period overlap and the 1955 date limit;
credited endpoints remain eligible for its continuous clock.
UNKNOWN prior history also obeys a joint optimistic-clock proof: even
deleting every removable uncredited quarter cannot rescue a declaration
whose same credits fail the current route. Past blindness is allowed as
an unresolved prior basis, including in the earliest-prior emptiness proof.
Known-history fully-route scans fix the first start only when ordinary
insurance holds for that filling and prior treatment. A flag's first
fully insured quarter is unknown, including for blindness. When a clear
first start depends on annual placement or prior treatment after a favorable
overlapping start, construction retains a named refusal rather than
selecting a filling that could change another returned status.
The declared pre1956 flag adds no route beyond the automatic alternate.
Flag-specific conditions remain declared facts rather than adjudicated rules.
Short DIB-entitled prior periods remain possible. Observable specialist credit
alternatives cannot silently produce ordinary-only uninsured answers. The
query month is a hypothetical entitlement month, not medical or
administrative adjudication. Annual QC assignment is favorable and
retrospective; callers must supply only information available at their
decision time. Each test returns its own assignment witness.

All public declarations use the shared exact-type schema. Ordered sequences
retain multiplicity; conditions are membership collections. Computed values,
refusals and evaluator rows use the common Track B provenance seal. Public
calls validate once before coverage decisions. Persist inputs and recompute.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum
from fractions import Fraction
from itertools import combinations, product
from math import prod
from types import MappingProxyType

from populace_dynamics.track_b._insured_status_qc import (
    _allowed_quarters,
    _assign_qcs,
    _assignment_candidates,
    _post1977_qc_count,
    _pre1978_qc_credits,
    _qc_amount_from_nawi,
    _UnsupportedQC,
)
from populace_dynamics.track_b._provenance import (
    _check_refusal,
    _check_seal,
    _checked_result,
    _computed,
    _declared_input,
    _sealed_refusal,
    _sealed_result,
    _SealedOutcome,
    _SealedResult,
    _validated_entry,
)
from populace_dynamics.track_b.gross_benefits import (
    FamilyConfigurationUnsupported,
    InvalidFamilyInput,
    _check_evaluation_inputs,
)

VERSION = "track-b-insured-v1"


class EarningsProvenance(Enum):
    OBSERVED = "observed"
    CONVENTION_FILLED = "convention_filled"
    UNKNOWN = "unknown"


class Sex(Enum):
    MALE = "male"
    FEMALE = "female"


class InsuredTest(Enum):
    ALL = "all"
    FULLY = "fully"
    CURRENTLY = "currently"
    DISABILITY = "disability"


class CoverageCondition(Enum):
    DEEMED_FULLY_INSURED = "deemed_fully_insured"
    TRANSITIONAL_INSURED = "transitional_insured"
    RAILROAD_CREDITS = "railroad_credits"
    MILITARY_CREDITS = "military_credits"
    MEDICARE_GOVERNMENT_EMPLOYMENT = "medicare_government_employment"
    EARNED_BASIS = "earned_basis"
    DISABILITY_BEFORE_1956 = "disability_before_1956"
    FISCAL_TAXABLE_YEAR = "fiscal_taxable_year"
    SHORT_TAXABLE_YEAR = "short_taxable_year"
    SIMPLIFIED_PRE1951 = "simplified_pre1951"


_FULLY_INSURED_ROUTE_CONDITIONS = frozenset(
    {
        CoverageCondition.DEEMED_FULLY_INSURED,
        CoverageCondition.TRANSITIONAL_INSURED,
        CoverageCondition.EARNED_BASIS,
        CoverageCondition.SIMPLIFIED_PRE1951,
    }
)
_RAW_EARNINGS_CONDITIONS = frozenset(
    {
        CoverageCondition.RAILROAD_CREDITS,
        CoverageCondition.FISCAL_TAXABLE_YEAR,
        CoverageCondition.SHORT_TAXABLE_YEAR,
    }
)
_CREDIT_ROUTE_CONDITIONS = frozenset(
    {
        CoverageCondition.MILITARY_CREDITS,
        CoverageCondition.MEDICARE_GOVERNMENT_EMPLOYMENT,
    }
)


class InsuredUnsupportedReason(Enum):
    UNKNOWN_EARNINGS = "unknown_earnings_years_decide_status"
    UNKNOWN_PERIODS = "unknown_prior_disability_periods_decide_status"
    UNKNOWN_CURRENT_PERIOD = "unknown_current_disability_period_decides_status"
    UNKNOWN_SSPA211 = "sspa211_applicability_unknown"
    CURRENT_PERIOD_HISTORY = "current_disability_period_requires_history"
    CURRENT_PERIOD_DLI = "ongoing_disability_period_dli_horizon_unsupported"
    CURRENT_PERIOD_END = "ongoing_disability_period_end_decides_status"
    TOTALIZATION = "totalization_credits_unsupported"
    DEEMED_FULLY_INSURED = "deemed_fully_insured_unsupported"
    TRANSITIONAL_INSURED = "transitional_insured_unsupported"
    ALIEN_WORKER = "alien_worker_sspa211_unsupported"
    RAILROAD_CREDITS = "railroad_credits_unsupported"
    MILITARY_CREDITS = "military_credits_unsupported"
    MEDICARE_GOVERNMENT_EMPLOYMENT = (
        "medicare_government_employment_unsupported"
    )
    EARNED_BASIS = "earned_basis_unsupported"
    DISABILITY_BEFORE_1956 = "disability_before_1956_unsupported"
    FISCAL_TAXABLE_YEAR = "fiscal_taxable_year_unsupported"
    SHORT_TAXABLE_YEAR = "short_taxable_year_unsupported"
    SIMPLIFIED_PRE1951 = "simplified_pre1951_unsupported"
    PRE1955_AGRICULTURE = "pre1955_agricultural_allocation_unsupported"
    PRE1951_SELF_EMPLOYMENT = "pre1951_self_employment_unsupported"
    EARNINGS_1937 = "1937_earnings_allocation_unsupported"
    QC_YEAR = "qc_amount_year_unsupported"
    HISTORICAL_ENTITLEMENT = "entitlement_before_1968_unsupported"
    HISTORICAL_BLINDNESS = "blindness_before_1973_unsupported"
    HISTORICAL_SUBSEQUENT = "subsequent_special_before_1983_unsupported"
    SUBSEQUENT_LONG_PERIOD = "subsequent_special_long_period_unsupported"
    ASSIGNMENT_COMPLEXITY = "disability_boundary_assignments_unsupported"


@_sealed_refusal(InsuredUnsupportedReason)
class InsuredConfigurationUnsupported(FamilyConfigurationUnsupported):
    """A retained insured-status refusal bound to this module's reason enum."""


def _refuse(reason, detail):
    raise _computed(InsuredConfigurationUnsupported, reason, detail)


def _month(value, label):
    if value.day != 1:
        raise InvalidFamilyInput(f"{label} must be the first day of a month")


def _qid(value):
    return value.year * 4 + (value.month - 1) // 3


def _qdate(qid):
    year, quarter = divmod(qid, 4)
    return date(year, quarter * 3 + 1, 1)


def _qend(qid):
    year, quarter = divmod(qid, 4)
    month = quarter * 3 + 3
    return date(year, month, calendar.monthrange(year, month)[1])


def _attain(birth, age):
    year = birth.year + age
    day = min(birth.day, calendar.monthrange(year, birth.month)[1])
    return date(year, birth.month, day) - timedelta(days=1)


def _two_months_before(value):
    """First day of the calendar month two months before a dated fact."""
    index = value.year * 12 + value.month - 1 - 2
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def _historical_recovery_month(person):
    """Infer recovery only when 404.321(b) leaves no other ending cause."""
    # Source conflict us:oasdi-insured-historical-end-recovery-month
    end = person.current_disability_period_end
    # February 1981 is the first possible paragraph (c) ending. Infer
    # nothing about recovery for an ending governed by that paragraph.
    if end is None or end >= date(1981, 2, 1):
        return None
    ending_month = end.replace(day=1)
    fra_end = _fra_date(person).replace(day=1) - timedelta(days=1)
    if ending_month >= fra_end.replace(day=1):
        return None
    if (
        person.death_date is not None
        and ending_month >= person.death_date.replace(day=1)
    ):
        return None
    return _two_months_before(end)


def _fact_provenance(provenance, convention_id, label):
    convention = provenance is EarningsProvenance.CONVENTION_FILLED
    if convention != (convention_id is not None):
        raise InvalidFamilyInput(f"Only convention-filled {label} needs an id")
    if convention and not convention_id.strip():
        raise InvalidFamilyInput("Convention identifier must be nonempty")


def _sspa211_applicability(person):
    # RS00301.102 B.1/B.3: pre2004 assignments are exempt. Later or absent
    # true-identity assignments ordinarily trigger Section 211, but B.3.b's
    # wrong-number SS-5 exception allows an adjudicated exemption when the
    # worker could legitimately have been assigned an SSN before 2004. A
    # worker born in 2004 or later cannot meet that exception's date limit.
    legacy = None
    if person.alien_worker:
        if person.ssn_never_assigned:
            legacy = True
        elif person.ssn_assignment_date is not None:
            legacy = person.ssn_assignment_date >= date(2004, 1, 1)
    if person.sspa211_applies is not None:
        if (legacy is False and person.sspa211_applies) or (
            person.alien_worker
            and person.birth_date >= date(2004, 1, 1)
            and not person.sspa211_applies
        ):
            raise InvalidFamilyInput("Conflicting SSPA211 applicability facts")
        return person.sspa211_applies
    return legacy


@_declared_input
@dataclass(frozen=True)
class CoverageYear:
    provenance: EarningsProvenance
    convention_id: str | None = None
    wages: Fraction | None = None
    self_employment: Fraction | None = None
    quarterly_wages: tuple[Fraction, ...] | None = None
    agricultural_wages: Fraction | None = None
    qc_count: int | None = None
    qc_quarters: tuple[bool, ...] | None = None

    def __post_init__(self):
        convention = self.provenance is EarningsProvenance.CONVENTION_FILLED
        if convention != (self.convention_id is not None):
            raise InvalidFamilyInput("Only convention-filled years need an id")
        if convention and not self.convention_id.strip():
            raise InvalidFamilyInput("Convention identifier must be nonempty")
        amounts = (self.wages, self.self_employment, self.agricultural_wages)
        for amount in amounts:
            if amount is not None and amount < 0:
                raise InvalidFamilyInput("Covered earnings cannot be negative")
        if self.quarterly_wages is not None:
            if len(self.quarterly_wages) != 4 or any(
                value < 0 for value in self.quarterly_wages
            ):
                raise InvalidFamilyInput(
                    "Four nonnegative wage quarters needed"
                )
        if self.qc_count is not None and not 0 <= self.qc_count <= 4:
            raise InvalidFamilyInput(
                "Annual QC count must be between zero and four"
            )
        if self.qc_quarters is not None and len(self.qc_quarters) != 4:
            raise InvalidFamilyInput("Four quarterly QC flags needed")
        earnings = any(value is not None for value in amounts) or (
            self.quarterly_wages is not None
        )
        direct = self.qc_count is not None or self.qc_quarters is not None
        if self.provenance is EarningsProvenance.UNKNOWN:
            if earnings or direct:
                raise InvalidFamilyInput("Unknown years cannot contain values")
        elif earnings == direct:
            raise InvalidFamilyInput(
                "Declare either earnings or QCs, never both"
            )
        if self.qc_count is not None and self.qc_quarters is not None:
            raise InvalidFamilyInput(
                "Declare count or quarterly flags, not both"
            )


@_declared_input
@dataclass(frozen=True)
class DisabilityPeriod:
    start: date
    end: date
    special_insured: bool = False

    def __post_init__(self):
        if self.end < self.start:
            raise InvalidFamilyInput("Disability period ends before it starts")


@_declared_input
@dataclass(frozen=True)
class Person:
    birth_date: date
    sex: Sex | None = None
    death_date: date | None = None
    disability_onset: date | None = None
    prior_disability_periods: tuple[DisabilityPeriod, ...] = ()
    statutory_blindness: bool = False
    conditions: frozenset[CoverageCondition] = frozenset()
    alien_worker: bool = False
    ssn_assignment_date: date | None = None
    ssn_never_assigned: bool = False
    rib_entitlement_month: date | None = None
    dib_entitlement_month: date | None = None
    prior_disability_periods_provenance: EarningsProvenance = (
        EarningsProvenance.UNKNOWN
    )
    prior_disability_periods_convention_id: str | None = None
    current_disability_period_established: bool | None = None
    current_disability_period_provenance: EarningsProvenance | None = None
    current_disability_period_convention_id: str | None = None
    sspa211_applies: bool | None = None
    sspa211_provenance: EarningsProvenance = EarningsProvenance.UNKNOWN
    sspa211_convention_id: str | None = None
    current_disability_period_end: date | None = None
    current_disability_period_end_provenance: EarningsProvenance = (
        EarningsProvenance.UNKNOWN
    )
    current_disability_period_end_convention_id: str | None = None
    current_disability_period_continues_through: date | None = None
    current_disability_period_continues_through_provenance: (
        EarningsProvenance
    ) = EarningsProvenance.UNKNOWN
    current_disability_period_continues_through_convention_id: str | None = (
        None
    )

    def __post_init__(self):
        _fact_provenance(
            self.prior_disability_periods_provenance,
            self.prior_disability_periods_convention_id,
            "prior disability periods",
        )
        if (
            self.prior_disability_periods_provenance
            is EarningsProvenance.UNKNOWN
            and self.prior_disability_periods
        ):
            raise InvalidFamilyInput(
                "Unknown prior periods cannot contain values"
            )
        for value, provenance, convention, label in (
            (
                self.current_disability_period_established,
                self.current_disability_period_provenance,
                self.current_disability_period_convention_id,
                "current disability period",
            ),
            (
                self.sspa211_applies,
                self.sspa211_provenance,
                self.sspa211_convention_id,
                "SSPA211 applicability",
            ),
        ):
            _fact_provenance(provenance, convention, label)
            if (
                provenance is None or provenance is EarningsProvenance.UNKNOWN
            ) != (value is None):
                raise InvalidFamilyInput(
                    f"{label} value must match provenance"
                )
        if (
            self.current_disability_period_established
            and self.disability_onset is None
        ):
            raise InvalidFamilyInput(
                "Current established period requires medical onset"
            )
        _fact_provenance(
            self.current_disability_period_end_provenance,
            self.current_disability_period_end_convention_id,
            "current disability period end",
        )
        if (
            self.current_disability_period_end_provenance
            is EarningsProvenance.UNKNOWN
        ) != (self.current_disability_period_end is None):
            raise InvalidFamilyInput(
                "Current period end must match provenance"
            )
        if self.current_disability_period_end is not None:
            if not self.current_disability_period_established:
                raise InvalidFamilyInput(
                    "Period end requires established period"
                )
            end = self.current_disability_period_end
            if end.day != calendar.monthrange(end.year, end.month)[1]:
                raise InvalidFamilyInput(
                    "Period end must close a calendar month"
                )
        if not 1870 <= self.birth_date.year <= 9900:
            raise InvalidFamilyInput("Birth year outside supported calendar")
        if self.birth_date < date(1913, 1, 2) and self.sex is None:
            raise InvalidFamilyInput("Pre-1913 cohorts require declared sex")
        for value in (self.death_date, self.disability_onset):
            if value is not None and value < self.birth_date:
                raise InvalidFamilyInput("Event precedes birth")
        if (
            self.death_date is not None
            and self.disability_onset is not None
            and self.disability_onset > self.death_date
        ):
            raise InvalidFamilyInput("Disability onset follows death")
        fra = _fra_date(self)
        if (
            self.current_disability_period_end is not None
            and self.current_disability_period_end < self.disability_onset
        ):
            raise InvalidFamilyInput("Current period ends before onset")
        recovery = _historical_recovery_month(self)
        if recovery is not None and recovery < self.disability_onset.replace(
            day=1
        ):
            raise InvalidFamilyInput("Current period recovery precedes onset")
        if (
            self.current_disability_period_established
            and self.disability_onset >= fra.replace(day=1)
        ):
            raise InvalidFamilyInput(
                "Established period begins after its statutory FRA end"
            )
        fra_end = fra.replace(day=1) - timedelta(days=1)
        _fact_provenance(
            self.current_disability_period_continues_through_provenance,
            self.current_disability_period_continues_through_convention_id,
            "current disability period continuity",
        )
        through = self.current_disability_period_continues_through
        if (
            self.current_disability_period_continues_through_provenance
            is EarningsProvenance.UNKNOWN
        ) != (through is None):
            raise InvalidFamilyInput(
                "Current period continuity must match provenance"
            )
        if through is not None:
            if not self.current_disability_period_established:
                raise InvalidFamilyInput(
                    "Period continuity requires established period"
                )
            if through < self.disability_onset or through > fra_end:
                raise InvalidFamilyInput(
                    "Period continuity outside onset and statutory FRA end"
                )
            if (
                self.current_disability_period_end is not None
                and through > self.current_disability_period_end
            ) or (self.death_date is not None and through > self.death_date):
                raise InvalidFamilyInput("Period continuity follows its end")
        periods = sorted(
            (
                replace(p, end=min(p.end, fra_end)) if p.start < fra else p
                for p in self.prior_disability_periods
            ),
            key=lambda p: p.start,
        )
        for i, period in enumerate(periods):
            if period.start >= fra or period.start > fra_end:
                raise InvalidFamilyInput(
                    "Disability period begins at or after FRA"
                )
            if period.start < self.birth_date or (
                self.death_date is not None and period.end > self.death_date
            ):
                raise InvalidFamilyInput("Disability period outside lifetime")
            if i and _qid(period.start) <= _qid(periods[i - 1].end):
                raise InvalidFamilyInput("Disability periods overlap quarters")
            if period.special_insured and _qid(period.start) >= _qid(
                _attain(self.birth_date, 31)
            ):
                raise InvalidFamilyInput(
                    "Prior special onset must precede age31"
                )
        if self.ssn_never_assigned and self.ssn_assignment_date is not None:
            raise InvalidFamilyInput(
                "Unassigned SSN cannot have assignment date"
            )
        if (
            self.ssn_assignment_date is not None
            and self.ssn_assignment_date < self.birth_date
        ):
            raise InvalidFamilyInput("SSN assignment precedes birth")
        for event in (self.rib_entitlement_month, self.dib_entitlement_month):
            if event is not None:
                _month(event, "entitlement month")
                if event < self.birth_date.replace(day=1) or (
                    self.death_date is not None
                    and event > self.death_date.replace(day=1)
                ):
                    raise InvalidFamilyInput("Entitlement outside lifetime")
        object.__setattr__(self, "prior_disability_periods", tuple(periods))


@_sealed_result
@dataclass(frozen=True)
class StatusDecision(_SealedResult):
    insured: bool
    qc_count_lower: int
    qc_count_upper: int
    required: int
    window: tuple[int, ...]
    assigned_quarters: tuple[int, ...]
    rule: str
    upper_required: int
    upper_window: tuple[int, ...]
    upper_assigned_quarters: tuple[int, ...]
    upper_rule: str
    fully_required: int
    upper_fully_required: int
    fully_qc_count_lower: int
    fully_qc_count_upper: int
    qualifying_quarter: date | None
    upper_qualifying_quarter: date | None


@_sealed_result
@dataclass(frozen=True)
class DLIRange(_SealedResult):
    lower: date | None
    upper: date | None
    right_censored: bool


@_sealed_result
@dataclass(frozen=True)
class InsuredStatus(_SealedResult):
    version: str
    month: date
    fully: StatusDecision | None
    currently: StatusDecision | None
    disability: StatusDecision | None
    dli: DLIRange | None
    qcs_by_year: Mapping[int, tuple[int, int]]
    assigned_quarters: Mapping[int, tuple[int, ...]]
    unknown_years: tuple[int, ...]
    convention_years: Mapping[int, str]
    decided_despite_unknowns: bool
    current_disability_period_start: date | None
    unknown_facts: tuple[str, ...]
    convention_facts: Mapping[str, str]


def _requirement(person, at, periods=(), *, onset=True, for_disability=False):
    start = max(1951, _attain(person.birth_date, 21).year + 1)
    end = min(at.year, _attain(person.birth_date, 62).year)
    if person.sex is Sex.MALE and person.birth_date < date(1913, 1, 2):
        end = min(
            at.year,
            (
                _attain(person.birth_date, 65).year
                if person.birth_date < date(1911, 1, 2) and not for_disability
                else 1975
            ),
        )
    if person.death_date is not None:
        end = min(end, person.death_date.year)
    elapsed = sum(
        not any(a.year <= year <= b.year for a, b in periods)
        for year in range(start, end)
    )
    return min(40, max(6, elapsed))


@_validated_entry
def fully_insured_requirement(person: Person, month: date) -> int:
    """One QC per elapsed year, bounded by six and forty (214(a))."""
    _month(month, "month")
    if (
        person.disability_onset is not None
        and person.current_disability_period_provenance is None
    ):
        raise InvalidFamilyInput(
            "Declare current disability period establishment"
        )
    if month < person.birth_date.replace(day=1):
        raise InvalidFamilyInput("Query precedes birth")
    if (
        person.disability_onset is not None
        and person.disability_onset.replace(day=1) > month
    ):
        raise InvalidFamilyInput("Disability onset follows query month")
    if any(p.end >= month for p in person.prior_disability_periods):
        raise InvalidFamilyInput("Prior disability period follows query month")
    if (
        person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
    ):
        _refuse(
            InsuredUnsupportedReason.UNKNOWN_PERIODS,
            "Requirement depends on established periods",
        )
    if (
        person.disability_onset is not None
        and person.disability_onset < _fra_date(person).replace(day=1)
        and person.current_disability_period_established is not False
    ):
        _refuse(
            InsuredUnsupportedReason.CURRENT_PERIOD_HISTORY,
            "Deriving the current period start requires coverage history",
        )
    periods = tuple((p.start, p.end) for p in person.prior_disability_periods)
    return _requirement(person, month, periods)


@_validated_entry
def qc_amount_from_nawi(nawi: Fraction, prior_amount: int) -> int:
    """213(d): exact indexed amount, nearest $10 with $5 ties upward."""
    if nawi <= 0 or prior_amount < 250 or prior_amount % 10:
        raise InvalidFamilyInput(
            "Positive NAWI and prior statutory increment needed"
        )
    return _qc_amount_from_nawi(nawi, prior_amount)


def _validate_history(person, years, month, coverage_end_month, credits):
    _month(month, "month")
    if (
        person.disability_onset is not None
        and person.current_disability_period_provenance is None
    ):
        raise InvalidFamilyInput(
            "Declare current disability period establishment"
        )
    _sspa211_applicability(person)
    if month.year > 9990 or month < person.birth_date.replace(day=1):
        raise InvalidFamilyInput("Query outside person's calendar")
    if (
        person.disability_onset is not None
        and person.disability_onset.replace(day=1) > month
    ):
        raise InvalidFamilyInput("Disability onset follows query month")
    if any(
        event is not None and event > month
        for event in (
            person.rib_entitlement_month,
            person.dib_entitlement_month,
        )
    ):
        raise InvalidFamilyInput("Entitlement follows query month")
    if coverage_end_month is not None:
        _month(coverage_end_month, "coverage_end_month")
        if coverage_end_month < person.birth_date.replace(day=1):
            raise InvalidFamilyInput("Coverage end precedes birth")
    if any(not credit.strip() for credit in credits):
        raise InvalidFamilyInput(
            "Totalization credit identifiers must be nonempty"
        )
    end = min(
        month.year,
        (
            coverage_end_month.year
            if coverage_end_month is not None
            else month.year
        ),
        (
            person.death_date.year
            if person.death_date is not None
            else month.year
        ),
    )
    expected = set(range(max(1937, person.birth_date.year), end + 1))
    if set(years) != expected:
        raise InvalidFamilyInput(
            "Every coverage year must be declared; missing="
            f"{sorted(expected - set(years))}, extra={sorted(set(years) - expected)}"
        )
    for period in person.prior_disability_periods:
        if period.end >= month or (
            person.disability_onset is not None
            and period.end >= person.disability_onset
        ):
            raise InvalidFamilyInput(
                "Prior disability period must precede current event"
            )
    for year, row in years.items():
        if year < 1978:
            if row.qc_count is not None or row.wages is not None:
                raise InvalidFamilyInput(
                    "Pre1978 needs quarterly wages or QC flags"
                )
        elif row.qc_quarters is not None or row.quarterly_wages is not None:
            raise InvalidFamilyInput(
                "Post1977 uses annual earnings or QC count"
            )
        if year >= 1978 and row.agricultural_wages is not None:
            raise InvalidFamilyInput(
                "Post1977 agricultural wages belong in wages"
            )
        cutoff = min(
            _qid(month),
            _qid(person.death_date) if person.death_date else _qid(month),
            _qid(coverage_end_month) if coverage_end_month else _qid(month),
        )
        if row.qc_quarters is not None:
            if any(
                flag and not _qid(person.birth_date) <= year * 4 + i <= cutoff
                for i, flag in enumerate(row.qc_quarters)
            ):
                raise InvalidFamilyInput(
                    "Quarterly QCs declared after coverage ends"
                )
        if row.quarterly_wages is not None:
            if any(
                value and not _qid(person.birth_date) <= year * 4 + i <= cutoff
                for i, value in enumerate(row.quarterly_wages)
            ):
                raise InvalidFamilyInput(
                    "Quarterly earnings declared after coverage ends"
                )


def _coverage_checks(person, years, month, credits):
    if credits:
        _refuse(
            InsuredUnsupportedReason.TOTALIZATION,
            "Foreign coverage is not implemented",
        )
    for condition in sorted(person.conditions, key=lambda c: c.value):
        _refuse(InsuredUnsupportedReason[condition.name], condition.value)
    if month < date(1968, 1, 1):
        _refuse(
            InsuredUnsupportedReason.HISTORICAL_ENTITLEMENT,
            "Historical entitlement amendments",
        )
    if person.statutory_blindness and month < date(1973, 1, 1):
        _refuse(
            InsuredUnsupportedReason.HISTORICAL_BLINDNESS,
            "Pre1973 blindness tests",
        )
    if any(
        p.special_insured for p in person.prior_disability_periods
    ) and month < date(1983, 5, 1):
        _refuse(
            InsuredUnsupportedReason.HISTORICAL_SUBSEQUENT,
            "Pre1983 subsequent-period amendments",
        )
    for year, row in years.items():
        if (
            year > 2027
            and row.provenance is not EarningsProvenance.UNKNOWN
            and row.qc_count is None
        ):
            _refuse(
                InsuredUnsupportedReason.QC_YEAR,
                f"No captured QC increment for {year}",
            )


def _current_period_establishment_unknown(person):
    """Whether a missing establishment fact admits a pre-FRA completion."""
    return (
        person.disability_onset is not None
        and person.disability_onset < _fra_date(person).replace(day=1)
        and person.current_disability_period_provenance
        is EarningsProvenance.UNKNOWN
    )


def _pre1951_aggregate_possible(
    person, years, credits, at, exit_month, required
):
    """Bound Act 213(c)'s aggregate against one fully insured requirement.

    Post1950 upper credits are counted without period exclusions, and
    unresolved history or establishment lowers the requirement to six.
    This can only preserve a route; it never credits a deemed quarter.
    """
    before1951 = {year: row for year, row in years.items() if year < 1951}
    if not before1951:
        return False
    wages = sum(
        (
            sum(row.quarterly_wages)
            for row in before1951.values()
            if row.quarterly_wages is not None
        ),
        Fraction(0),
    )
    unknown_wages = any(
        row.provenance is EarningsProvenance.UNKNOWN
        for row in before1951.values()
    )
    rows, _ = _world(person, credits, _qid(at), exit_month, False)
    post1950 = sum(
        len(_assign_qcs(*row)) for year, row in rows.items() if year >= 1951
    )
    if (
        person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
        or person.disability_onset is not None
        and person.disability_onset < _fra_date(person).replace(day=1)
        and person.current_disability_period_provenance
        is EarningsProvenance.UNKNOWN
    ):
        required = 6
    # Source conflict us:oasdi-insured-pre1951-seven-elapsed-years
    return unknown_wages or (
        wages >= 400 and wages // 400 + post1950 >= required
    )


def _aggregate_could_insure(
    person, years, credits, at, exit_month, *, onset=True
):
    """Whether only the aggregate could be missing for insurance at ``at``.

    Act 223(c)(1)(A) and 216(i)(3)(A) require a "fully insured individual"
    under section 214, the section Act 213(c) names, and 404.132 applies
    404.110 with only a different end to the elapsed years. RS 00301.315
    B.1 alone excludes disability claims. Filing facts stay unmodeled, so
    a decisive aggregate refuses by name and is never rejected or answered
    false. Simplified credits never count toward the recent rule.
    """
    # Source conflict us:oasdi-insured-simplified-pre1951-disability-scope
    if not (
        person.statutory_blindness
        or _witness(
            person,
            credits,
            at,
            exit_month,
            InsuredTest.DISABILITY,
            onset=onset,
            ignore_fully_insured=True,
        )[0]
    ):
        return False
    periods = tuple(
        (period.start, period.end)
        for period in person.prior_disability_periods
    )
    return _pre1951_aggregate_possible(
        person,
        years,
        credits,
        at,
        exit_month,
        _requirement(person, at, periods, onset=onset, for_disability=True),
    )


def _aggregate_establishment_possible(
    person, years, credits, horizon, exit_month
):
    """Possibility bound: earliest requirement, credits through horizon."""
    periods = tuple(
        (period.start, period.end)
        for period in person.prior_disability_periods
    )
    return _pre1951_aggregate_possible(
        person,
        years,
        credits,
        horizon,
        exit_month,
        _requirement(
            person, person.disability_onset, periods, for_disability=True
        ),
    )


def _observable_coverage_paths(
    person, years, month, exit_month, kind, lo, quarter, upper, lower
):
    """Refuse favorable specialist paths revealed by ordinary declarations.

    Act 213(c), 404.110(d), and RS 00301.315 make the pre1951 aggregate
    method available independently of an optional specialist flag. Its
    application, retroactivity and section227 conditions are not declared.
    DISABILITY compares the recent rule at each event with the same
    bound; a true ordinary status stays computed.
    RS .315 B.1.a describes the 1967 seven-EY condition; B.1.b removes
    it under the 1990 amendments. 404.110(d)(1)(ii) supplies a June1992
    application exception with section227 conditions. A potentially
    decisive path is refused without fabricating these filing facts.
    Direct QC declarations supply credited quarters, not raw wage totals.
    RS 00301.480 likewise reveals a possible pre1956 alternate disability
    path from onset and earnings; its application facts remain unmodeled.
    """
    # A successful witness at or after FRA cannot resolve an earlier
    # alternate route requiring a freeze or DIB month before FRA. UNKNOWN
    # establishment also admits a period ending before a later witness.
    if lo[0] and (
        kind is not InsuredTest.DISABILITY
        or quarter < _fra_date(person).replace(day=1)
        and not _current_period_establishment_unknown(person)
    ):
        return
    if kind is InsuredTest.FULLY:
        periods = tuple(
            (period.start, period.end)
            for period in person.prior_disability_periods
        )
        # The favorable ordinary witness may disregard a freeze whose
        # lower prerequisite would favor the simplified aggregate instead.
        # Use every known period, including a derived current period, and
        # the universal six-QC lower bound for unresolved applicability.
        if _pre1951_aggregate_possible(
            person,
            years,
            upper,
            month,
            exit_month,
            min(lo[6], _requirement(person, month, periods)),
        ):
            _refuse(
                InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                "Pre1951 wages may establish fully insured status under "
                "Act213(c); filing and retroactivity facts are unmodeled",
            )
    elif kind is InsuredTest.DISABILITY:
        if _pre1956_alternate_possible(
            person, upper, month, exit_month, lower_credits=lower
        ):
            _refuse(
                InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
                "Onset and QCs allow the RS00301.480 alternate test; "
                "application conditions are unmodeled",
            )
        if not lo[0] and any(
            _aggregate_could_insure(person, years, upper, event, exit_month)
            for event in _events(person, month, kind)
        ):
            _refuse(
                InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                "Pre1951 wages may supply the disability fully insured "
                "prerequisite; filing facts are unmodeled",
            )


def _pre1956_alternate_possible(
    person, credits, month, exit_month, *, lower_credits=None
):
    """RS00301.480 possibility, without guessing filing eligibility."""
    if person.disability_onset is None or person.disability_onset >= date(
        1956, 1, 1
    ):
        return False
    # RS00301.480 A excludes anyone with 20/40 in any disabled quarter
    # before October 1960. Only the lower filling can exclude every
    # completion. Use the ordinary disability window, including favorable
    # consideration or disregard of all prior periods (404.130(f)).
    # A witness must allow a freeze or DIB before FRA (Act 216(i)(2)(D),
    # 404.315(a), 404.321(a)-(b)), regardless of declared establishment.
    last = min(month, _fra_date(person).replace(day=1) - timedelta(days=1))
    if (
        person.current_disability_period_established
        or _current_period_establishment_unknown(person)
    ):
        # 404.321(b): the earliest recovery compatible with either dated
        # period fact is two months earlier, including FRA/death endings.
        # This is a universal-exclusion bound, not a recovery inference.
        # UNKNOWN establishment admits an early end and cannot supply
        # either an end or continuity date, so only onset is shared.
        dated = (
            person.current_disability_period_end
            or person.current_disability_period_continues_through
        )
        covered = (
            max(
                person.disability_onset.replace(day=1),
                _two_months_before(dated),
            )
            if dated is not None
            else person.disability_onset
        )
        last = min(last, covered)
    lower = credits if lower_credits is None else lower_credits
    # Source conflict us:oasdi-insured-pre1956-alternate-any-quarter-scan
    for quarter in range(
        _qid(person.disability_onset), min(_qid(last), 1960 * 4 + 2) + 1
    ):
        for use_periods in (
            (True, False) if person.prior_disability_periods else (True,)
        ):
            rows, periods = _world(
                person, lower, quarter, exit_month, use_periods
            )
            for boundary in _boundary_variants(rows, periods):
                window = _window(quarter, 40, periods, boundary)
                if (
                    len(set(_assignment(rows, window, boundary)) & set(window))
                    >= 20
                ):
                    return False
    if person.current_disability_period_established:
        # RS00301.480 B.1: a freeze cannot begin before 1952-07-01.
        # An independent alternate route still must start before the
        # declared ending or known continuity observation.
        month = _current_period_start_horizon(person, month)
    first = max(_qid(person.disability_onset), 1952 * 4 + 2)
    last = min(_qid(month), 1955 * 4 + 3)
    for quarter in range(first, last + 1):
        # One start must satisfy both the alternate and fixed chronology.
        if person.current_disability_period_established and not (
            _outside_prior_periods(person, quarter)
        ):
            continue
        # RS00301.132 B.2/C.2: all prior periods are used or disregarded
        # for the continuous clock too; credited endpoints stay eligible.
        for use_periods in (
            (True, False) if person.prior_disability_periods else (True,)
        ):
            rows, periods = _world(
                person, credits, quarter, exit_month, use_periods
            )
            target = tuple(range(1951 * 4, quarter))
            for boundary in _boundary_variants(rows, periods):
                assigned = set(_assignment(rows, target, boundary))
                continuous = tuple(
                    q
                    for q in target
                    if not any(
                        a <= q <= b and q not in assigned for a, b in periods
                    )
                )
                if (
                    len(assigned) >= 20
                    and len(continuous) >= 6
                    and set(continuous) <= assigned
                ):
                    return True
    return False


def _credits(year, row, upper):
    if row.provenance is EarningsProvenance.UNKNOWN:
        return (), 4 if upper else 0
    if row.qc_count is not None:
        return (), row.qc_count
    if row.qc_quarters is not None:
        return (
            tuple(
                year * 4 + i for i, flag in enumerate(row.qc_quarters) if flag
            ),
            0,
        )
    if year >= 1978:
        if year > 2027:
            _refuse(
                InsuredUnsupportedReason.QC_YEAR,
                f"No captured QC increment for {year}",
            )
        return (), _post1977_qc_count(
            year, row.wages or Fraction(0), row.self_employment or Fraction(0)
        )
    try:
        return _pre1978_qc_credits(
            year,
            row.quarterly_wages or (Fraction(0),) * 4,
            row.self_employment or Fraction(0),
            row.agricultural_wages or Fraction(0),
        )
    except _UnsupportedQC as error:
        _refuse(InsuredUnsupportedReason(error.reason), str(error))


def _deferred_credit_bounds(year, row):
    """Possibility-only bounds; never replace a refused ordinary result."""
    if year > 2027:
        # Act 213(d)(2): an increment cannot fall below captured 2027's.
        return ((), 0), (
            (),
            _post1977_qc_count(
                2027,
                row.wages or Fraction(0),
                row.self_employment or Fraction(0),
            ),
        )
    if year == 1937:
        # Act 213(b)'s half-year allocation prevents fixing raw wage slots.
        return ((), 0), ((), 4)
    # Unsupported annual AG/SE allocation cannot remove independently
    # credited ordinary wages or supported calendar-year SE quarters.
    fixed, flexible = _pre1978_qc_credits(
        year,
        row.quarterly_wages or (Fraction(0),) * 4,
        (row.self_employment or Fraction(0)) if year >= 1951 else Fraction(0),
        Fraction(0),
    )
    return (fixed, flexible), (fixed, 4 - len(fixed))


def _world(
    person,
    credits,
    qid,
    exit_month,
    use_periods,
    *,
    include_zero=False,
    prior_before=None,
):
    periods = (
        tuple(
            (_qid(p.start), _qid(p.end))
            for p in person.prior_disability_periods
            if prior_before is None or p.end < prior_before
        )
        if use_periods
        else ()
    )
    rows = {}
    for year, (fixed, flexible) in credits.items():
        if not include_zero and not fixed and not flexible:
            continue
        allowed = _allowed_quarters(
            year,
            through_quarter=qid,
            death_quarter=(
                _qid(person.death_date) if person.death_date else None
            ),
            coverage_end_quarter=_qid(exit_month) if exit_month else None,
            disability_periods=periods,
        )
        allowed = tuple(q for q in allowed if q >= _qid(person.birth_date))
        rows[year] = (fixed, flexible, allowed)
    return rows, periods


def _boundary_variants(rows, periods):
    years = sorted({q // 4 for pair in periods for q in pair} & rows.keys())
    # Canonical ties keep diagnostic witnesses independent of enumeration.
    options = [tuple(sorted(_assignment_candidates(*rows[y]))) for y in years]
    if prod(map(len, options)) > 4096:
        _refuse(
            InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
            "More than 4096 boundary assignments",
        )
    for choices in product(*options):
        yield dict(zip(years, choices, strict=True))


def _window(end, length, periods, boundary):
    chosen = {q for quarters in boundary.values() for q in quarters}
    answer = []
    qid = end
    while len(answer) < length:
        if not any(a <= qid <= b and qid not in chosen for a, b in periods):
            answer.append(qid)
        qid -= 1
    return tuple(reversed(answer))


def _assignment(rows, window, boundary):
    return tuple(
        sorted(
            q
            for year, row in rows.items()
            for q in (
                boundary[year]
                if year in boundary
                else _assign_qcs(*row, window=window)
            )
        )
    )


def _witness(
    person,
    credits,
    at,
    exit_month,
    kind,
    *,
    onset=True,
    ignore_fully_insured=False,
    use_periods_only=None,
    ordinary_only=False,
    under31_route=True,
):
    end = _qid(at)
    best = None
    long_period = False
    # Source conflict us:oasdi-insured-prior-disability-favorable-disregard
    # CFR404.130(f): consider all prior periods or disregard all, favorably.
    for use_periods in (
        (use_periods_only,)
        if use_periods_only is not None
        else (True, False) if person.prior_disability_periods else (True,)
    ):
        prior_before = None
        rows, periods = _world(
            person,
            credits,
            end,
            exit_month,
            use_periods,
            prior_before=prior_before,
        )
        dates = (
            tuple(
                (p.start, p.end)
                for p in person.prior_disability_periods
                if prior_before is None or p.end < prior_before
            )
            if use_periods
            else ()
        )
        fully_required = _requirement(
            person,
            at,
            dates,
            onset=onset,
            for_disability=kind is InsuredTest.DISABILITY,
        )
        for boundary in _boundary_variants(rows, periods):
            full_assignment = _assignment(rows, (), boundary)
            fully = len(full_assignment) >= fully_required
            if (
                kind is InsuredTest.FULLY
                or person.statutory_blindness
                and kind is InsuredTest.DISABILITY
            ):
                candidates = [
                    (
                        tuple(
                            range(
                                max(1937, person.birth_date.year) * 4, end + 1
                            )
                        ),
                        fully_required,
                        (
                            "fully"
                            if kind is InsuredTest.FULLY
                            else "blindness_fully_only"
                        ),
                    )
                ]
            elif kind is InsuredTest.CURRENTLY:
                candidates = [
                    (
                        _window(end, 13, periods, boundary),
                        6,
                        "currently_6_of_13",
                    )
                ]
            else:
                candidates = [
                    (
                        _window(end, 40, periods, boundary),
                        20,
                        "disability_20_of_40",
                    )
                ]
                young = end < _qid(_attain(person.birth_date, 31))
                subsequent = any(
                    p.special_insured for p in person.prior_disability_periods
                )
                # A flag records a prior "for which you were only insured
                # under paragraph (c)" (404.130(d)(1)), so 404.130(c) can't
                # begin an unflagged prior alone.
                if not ordinary_only and (
                    young and under31_route or subsequent and not young
                ):
                    first = max(
                        1937 * 4, _qid(_attain(person.birth_date, 21)) + 1
                    )
                    chosen = set(full_assignment)
                    elapsed = tuple(
                        q
                        for q in range(first, end + 1)
                        if not any(
                            a <= q <= b and q not in chosen for a, b in periods
                        )
                    )
                    if len(elapsed) < 12:
                        window, required = (
                            _window(end, 12, periods, boundary),
                            6,
                        )
                    elif len(elapsed) > 40:
                        window, required = elapsed[-40:], 20
                        # Source conflict us:oasdi-insured-subsequent-special-long-period
                        # Half of over 40 quarters clears the fully count.
                        long_period = long_period or (
                            len(
                                set(_assignment(rows, elapsed, boundary))
                                & set(elapsed)
                            )
                            >= len(elapsed) // 2
                        )
                    else:
                        window, required = elapsed, max(6, len(elapsed) // 2)
                    candidates.append(
                        (
                            window,
                            required,
                            (
                                "subsequent_special"
                                if subsequent and not young
                                else "under31_special"
                            ),
                        )
                    )
            for window, required, rule in candidates:
                assignment = _assignment(rows, window, boundary)
                count = len(set(assignment) & set(window))
                insured = count >= required and (
                    (fully or ignore_fully_insured)
                    if kind is InsuredTest.DISABILITY
                    else True
                )
                score = (insured, count - required, count, rule)
                candidate = (
                    insured,
                    count,
                    required,
                    window,
                    assignment,
                    rule,
                    fully_required,
                    len(full_assignment),
                )
                if best is None or score > best[0]:
                    best = score, candidate
    # Clause (iii) of Act 223(c)(1)(B) and 216(i)(3)(B) counts the whole period
    # after age 21. 404.130(d)(2) caps it at "20 QCs out of 40 calendar
    # quarters", and each 404.130 period ends with the tested quarter, so the
    # cap repeats the 40-quarter rule.
    if long_period and not best[1][0]:
        _refuse(
            InsuredUnsupportedReason.SUBSEQUENT_LONG_PERIOD,
            "Readings of the subsequent-special cap differ on a period "
            "of more than 40 quarters",
        )
    return best[1]


def _unknown_prior_history_is_empty(
    person, credits, month, exit_month, *, lower_credits=None
):
    """Prove infeasibility of the earliest nonempty prior period only.

    The earliest period must begin insured without any earlier exclusions
    (404.320(b)(2), 404.321(a)), and fit before onset and FRA. Act216(i)
    (2)(A) also permits a single DIB-entitled month; 404.315(a)(4) waives
    waiting in specified cases. No five-month premise is safe here.
    Historical blindness is possible regardless of current blindness
    (404.130(e)); every earliest-prior witness therefore permits it.
    Upper-credit witnesses deliberately overapproximate possibility. A
    surviving quarter proves no actual history; it only prevents an
    invalid-input conclusion.
    """
    if person.disability_onset is None:
        return False
    latest_end = min(
        person.disability_onset - timedelta(days=1),
        _fra_date(person).replace(day=1) - timedelta(days=1),
    )
    if latest_end < person.birth_date:
        return True
    positive_years = [
        year
        for year, (fixed, flexible) in credits.items()
        if fixed or flexible
    ]
    if not positive_years:
        return True
    first = max(_qid(person.birth_date), min(positive_years) * 4)
    plain = replace(
        person,
        prior_disability_periods=(),
        prior_disability_periods_provenance=EarningsProvenance.OBSERVED,
        prior_disability_periods_convention_id=None,
    )
    for quarter in range(first, _qid(latest_end) + 1):
        start = max(person.birth_date, _qdate(quarter))
        if start >= _fra_date(person):
            break
        # A one-month DIB-entitled period may start and end this month.
        # Overapproximate partial months too; this never establishes one.
        possible_prior = replace(
            plain,
            disability_onset=start,
            current_disability_period_established=False,
            current_disability_period_end=None,
            current_disability_period_end_provenance=EarningsProvenance.UNKNOWN,
            current_disability_period_end_convention_id=None,
            current_disability_period_continues_through=None,
            current_disability_period_continues_through_provenance=(
                EarningsProvenance.UNKNOWN
            ),
            current_disability_period_continues_through_convention_id=None,
        )
        if _pre1956_alternate_possible(
            possible_prior,
            credits,
            start,
            exit_month,
            lower_credits=lower_credits,
        ):
            return False
        if _witness(
            replace(plain, statutory_blindness=True),
            credits,
            start,
            exit_month,
            InsuredTest.DISABILITY,
            onset=False,
        )[0]:
            return False
    return True


def _fra_date(person):
    cohort = (person.birth_date - timedelta(days=1)).year
    months = 780
    if 1938 <= cohort <= 1942:
        months += (cohort - 1937) * 2
    elif 1943 <= cohort <= 1954:
        months = 792
    elif 1955 <= cohort <= 1959:
        months = 792 + (cohort - 1954) * 2
    elif cohort >= 1960:
        months = 804
    index = person.birth_date.year * 12 + person.birth_date.month - 1 + months
    year, month = divmod(index, 12)
    day = min(person.birth_date.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day) - timedelta(days=1)


def _fra_quarter(person):
    return _qid(_fra_date(person))


def _last_insured(person, credits, month, exit_month, *, years=None):
    last = None
    # Every nonblind route needs six ordinary QCs in its own window. Below
    # six, only a blind person's aggregate can still supply a historical DLI.
    if sum(len(fixed) + flexible for fixed, flexible in credits.values()) < 6:
        if years is None or not person.statutory_blindness:
            return None, False
    cap = min(_qid(month), _fra_quarter(person) - 1)
    if person.death_date is not None:
        cap = min(cap, _qid(person.death_date))
    # Without an exit declaration future work is not assumed zero. This is
    # a last-insured-through-query value, with explicit right censoring.
    if exit_month is not None and exit_month <= month:
        cap = _fra_quarter(person) - 1
        if person.death_date is not None:
            cap = min(cap, _qid(person.death_date))
    credited_years = [
        y for y, (fixed, flex) in credits.items() if fixed or flex
    ]
    start = max(min(credited_years, default=1937) * 4, _qid(person.birth_date))
    if not person.statutory_blindness and not person.prior_disability_periods:
        cap = min(cap, max(credited_years) * 4 + 3 + 39)
    for qid in range(cap, start - 1, -1):
        at = _qdate(qid)
        # DLI asks potential onset in each quarter, not the declared onset.
        if _witness(
            person,
            credits,
            at,
            exit_month,
            InsuredTest.DISABILITY,
            onset=False,
        )[0]:
            last = _qend(qid)
            break
        if years is not None and _aggregate_could_insure(
            person, years, credits, at, exit_month, onset=False
        ):
            _refuse(
                InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                "Pre1951 wages may extend the date last insured; "
                "filing facts are unmodeled",
            )
    censored = (
        (exit_month is None or exit_month > month)
        and cap == _qid(month)
        and last == _qend(cap)
    )
    return last, censored


def _events(person, month, kind):
    if kind is InsuredTest.DISABILITY and person.disability_onset is not None:
        # 404.131(a): onset quarter OR a later quarter while disabled.
        last = _qid(month)
        if person.current_disability_period_established:
            last = min(last, _fra_quarter(person))
        return tuple(
            _qdate(q) for q in range(_qid(person.disability_onset), last + 1)
        )
    if kind is InsuredTest.CURRENTLY:
        return tuple(
            event
            for event in (
                person.death_date,
                person.rib_entitlement_month,
                person.dib_entitlement_month,
            )
            if event is not None and event.replace(day=1) <= month
        ) or (month,)
    return (month,)


def _decision_witness(
    person, credits, month, exit_month, kind, *, use_periods_only=None
):
    best, qualifying = None, None
    for event in _events(person, month, kind):
        witness = _witness(
            person,
            credits,
            event,
            exit_month,
            kind,
            use_periods_only=use_periods_only,
        )
        if witness[0] and kind is InsuredTest.DISABILITY:
            return witness, _qdate(_qid(event))
        if best is None or (witness[0], witness[1]) > (best[0], best[1]):
            best = witness
            qualifying = _qdate(_qid(event)) if witness[0] else None
    return best, qualifying


def _period_end_unknown(person, month):
    return (
        person.current_disability_period_established
        and person.current_disability_period_end is None
    )


def _with_current_period(
    person, credits, month, exit_month, *, use_periods_only=None
):
    if not person.current_disability_period_established:
        return person, None
    fra = _fra_date(person)
    horizon = min(month, fra.replace(day=1))
    witness, quarter = _decision_witness(
        person,
        credits,
        horizon,
        exit_month,
        InsuredTest.DISABILITY,
        use_periods_only=use_periods_only,
    )
    if not witness[0]:
        raise InvalidFamilyInput(
            "Established current period has no insured disabled quarter"
        )
    if use_periods_only is None and not _outside_prior_periods(
        person, _qid(quarter)
    ):
        # A clear first start proves possibility, not a status shared by
        # every filling. Keep the row when annual placement or treatment
        # changes that start (404.321(a); RS00301.230).
        rows, _ = _world(person, credits, _qid(horizon), exit_month, False)
        options = [_assignment_candidates(*row) for row in rows.values()]
        if prod(map(len, options)) > 4096:
            _refuse(
                InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
                "More than 4096 first-start annual placements",
            )
        for choices in product(*options):
            filling = {
                year: (choice, 0)
                for year, choice in zip(rows, choices, strict=True)
            }
            for treatment in (True, False):
                try:
                    _with_current_period(
                        person,
                        filling,
                        month,
                        exit_month,
                        use_periods_only=treatment,
                    )
                except InvalidFamilyInput:
                    continue
                _refuse(
                    InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
                    "First insured start depends on annual placement "
                    "or prior treatment",
                )
    return _complete_current_period(person, quarter)


def _complete_current_period(person, quarter):
    fra = _fra_date(person)
    # 416(i)(2)(C), 404.321(a): onset day if insured then, otherwise
    # first day of the first later insured quarter. Application/duration
    # are administrative facts declared by the caller, never inferred.
    start = (
        person.disability_onset
        if _qid(quarter) == _qid(person.disability_onset)
        else quarter
    )
    # 416(i)(2)(B)/(D), 404.321: the query is an observation cut-off,
    # never an ending fact. This is the latest possible completion; the
    # caller separately enumerates earlier unknown administrative endings.
    end = fra.replace(day=1) - timedelta(days=1)
    if start >= fra or start > end:
        raise InvalidFamilyInput("Established period begins at or after FRA")
    if person.current_disability_period_end is not None:
        end = min(end, person.current_disability_period_end)
    if person.death_date is not None:
        end = min(end, person.death_date)
    if end < start:
        raise InvalidFamilyInput("Current period ends before insured start")
    recovery = _historical_recovery_month(person)
    if recovery is not None and start.replace(day=1) > recovery:
        raise InvalidFamilyInput("Current period starts after recovery month")
    if (
        person.current_disability_period_continues_through is not None
        and person.current_disability_period_continues_through < start
    ):
        raise InvalidFamilyInput("Period continuity precedes insured start")
    period = DisabilityPeriod(start, end)
    completed = replace(
        person,
        prior_disability_periods=person.prior_disability_periods + (period,),
        prior_disability_periods_provenance=EarningsProvenance.OBSERVED,
        prior_disability_periods_convention_id=None,
    )
    return completed, start


def _every_placement_passes(
    person, credits, at, month, exit_month, kind, **options
):
    """Whether every annual placement passes a test at one quarter.

    With no period in force every window is a suffix ending at the tested
    quarter. Placing annual QCs as early as possible before that quarter's
    year and as late as possible in it is therefore the worst filling, for
    every window at once. It is also a filling, so the answer is exact. The
    caller passes a person with no period listed.
    """
    rows, _ = _world(person, credits, _qid(month), exit_month, False)
    worst = dict(credits)
    for year, (fixed, count, allowed) in rows.items():
        if count:
            vacant = sorted(q for q in allowed if q not in fixed)
            chosen = vacant[-count:] if year == at.year else vacant[:count]
            worst[year] = (tuple(sorted((*fixed, *chosen))), 0)
    return _witness(person, worst, at, exit_month, kind, **options)[0]


def _start_fixed(person, credits, start, month, exit_month):
    """Whether every annual placement insures the favorable first start.

    If even the worst filling is insured, no filling starts later, and the
    favorable start already precedes none. Prior periods retain credited
    endpoints, so no single worst filling exists and the caller enumerates.
    """
    return not person.prior_disability_periods and _every_placement_passes(
        person, credits, start, month, exit_month, InsuredTest.DISABILITY
    )


def _prior_passes(person, credits, index, exit_month, *, blind, **options):
    """Whether a route insures a listed prior's start, with earlier priors.

    ``blind`` reads the holder as blind then, which asks only for fully
    insured status (404.130(e)). Only a flagged prior can begin on 404.130(c)
    alone, and an unflagged one rests on 404.130(b), or on 404.130(d) after a
    flagged prior.
    """
    period = person.prior_disability_periods[index]
    earlier = replace(
        person,
        statutory_blindness=blind,
        prior_disability_periods=person.prior_disability_periods[:index],
    )
    return _witness(
        earlier,
        credits,
        period.start,
        exit_month,
        InsuredTest.DISABILITY,
        under31_route=period.special_insured,
        **options,
    )[0]


def _keeps_priors(person, filling, binding, exit_month):
    """Whether one filling lets each binding prior begin on its basis.

    A flagged prior's holder "were only insured under paragraph (c)"
    (404.130(d)(1)), so that holder passes a special route and not 404.130(b).
    """
    return all(
        _prior_passes(person, filling, index, exit_month, blind=blind)
        and not (
            person.prior_disability_periods[index].special_insured
            and _prior_passes(
                person,
                filling,
                index,
                exit_month,
                blind=False,
                ordinary_only=True,
            )
        )
        for index, blind in binding
    )


def _every_placement_begins(
    person, lower, index, month, exit_month, *, blind, **options
):
    """Whether every annual placement insures a listed prior's start.

    Lower credits speak for every completion of an UNKNOWN year. This drops
    earlier priors, so a later prior resting on one fails here, and the search
    that follows then keeps the fillings it holds on.
    """
    period = person.prior_disability_periods[index]
    return _every_placement_passes(
        replace(
            person, statutory_blindness=blind, prior_disability_periods=()
        ),
        lower,
        period.start,
        month,
        exit_month,
        InsuredTest.DISABILITY,
        under31_route=period.special_insured,
        **options,
    )


def _prior_basis(person, lower, upper, index, month, exit_month):
    """Whether past blindness alone can support a listed prior's start.

    A period begins in a quarter its holder was insured (404.320(b)(2),
    404.321(a)). A flag records a prior "for which you were only insured under
    paragraph (c)" (404.130(d)(1)), so no placement supports a flagged prior
    if none passes a route or all of them pass 404.130(b), and 404.130(c)
    can't begin an unflagged prior alone. The record doesn't say whether an
    unflagged prior rested on past blindness, which asks only for fully
    insured status (404.130(e)), or on 404.130(b), or (d) after a flagged
    prior, which ask for that and more. A result has to stand on each basis some placement
    allows. Every placement 404.130(b) or (d) allows also passes 404.130(e),
    so a filling that keeps the prior on them speaks for both, and they hold
    the prior wherever a placement meets them. A prior no placement supports
    rests on credits or facts this record omits, and those could move other
    results, so the rule refuses it by name. Upper credits bound every
    completion of an UNKNOWN year.
    """
    if person.prior_disability_periods[index].special_insured:
        if _prior_passes(
            person, upper, index, exit_month, blind=False
        ) and not _every_placement_begins(
            person,
            lower,
            index,
            month,
            exit_month,
            blind=False,
            ordinary_only=True,
        ):
            return False
    else:
        for blind in (False, True):
            if _prior_passes(person, upper, index, exit_month, blind=blind):
                return blind
    _refuse(
        InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
        "No annual placement supports a listed prior's first insured quarter",
    )


def _prior_start_binds(person, lower, upper, index, month, exit_month, blind):
    """Whether annual placement decides a listed prior's start on its basis.

    A prior that holds on every placement leaves them all open, and otherwise
    it picks among them. A flagged prior that every placement carries on its
    route, short of 404.130(b), holds on every placement.
    """
    every = _every_placement_begins(
        person, lower, index, month, exit_month, blind=blind
    )
    if not person.prior_disability_periods[index].special_insured:
        return not every
    return not every or _prior_passes(
        person, upper, index, exit_month, blind=False, ordinary_only=True
    )


def _start_sensitive_years(person, start, horizon):
    """Years whose annual placement can change a first insured quarter.

    A year wholly inside every tested window, and untouched by a period,
    adds its full count wherever its QCs fall. Only the window's back
    edges, the onset-to-horizon years and prior-period years can differ.
    The 12-quarter and age-21 edges belong to 404.130(c) and (d). Recent-rule
    windows want a back-edge QC late, but an entitlement month can end a
    CURRENTLY window in that year and want it early, so placement stays
    enumerated there.
    """
    onset = _qid(start)
    last = _qid(horizon)
    excluded = sum(
        _qid(period.end) - _qid(period.start) + 1
        for period in person.prior_disability_periods
    )
    quarters = set(range(onset - 39 - excluded, last - 38))
    quarters.update(range(onset, last + 1))
    quarters.update(range(onset - 11 - excluded, last - 10))
    quarters.add(_qid(_attain(person.birth_date, 21)) + 1)
    for period in person.prior_disability_periods:
        quarters.update(range(_qid(period.start), _qid(period.end) + 1))
    return {quarter // 4 for quarter in quarters}


def _prior_sensitive_years(person, binding):
    """Years whose annual placement can change a binding prior's start."""
    return {
        year
        for index, _ in binding
        for year in _start_sensitive_years(
            person,
            person.prior_disability_periods[index].start,
            person.prior_disability_periods[index].start,
        )
    }


def _placements(person, credits, sensitive, month, exit_month, rank):
    """Each annual placement of the sensitive years, best ``rank`` first."""
    rows, _ = _world(person, credits, _qid(month), exit_month, False)
    options = {
        year: sorted(_assignment_candidates(*row), key=rank)
        for year, row in rows.items()
        if year in sensitive and row[1]
    }
    for index, choices in enumerate(product(*options.values())):
        if index == 4096:
            _refuse(
                InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
                "More than 4096 first-start annual placements",
            )
        filling = dict(credits)
        filling.update(
            (year, (choice, 0))
            for year, choice in zip(options, choices, strict=True)
        )
        yield filling


def _period_outcomes(
    person, completed, start, credits, month, exit_month, kinds, dated
):
    """Statuses, date last insured and witnesses for each ending.

    Establishment can't rest on its own exclusion, so DISABILITY reads
    ``person`` (see the decisions in ``insured_status``).
    """
    for option in _current_period_completions(person, completed, start, month):
        witnesses = tuple(
            _decision_witness(
                person if kind is InsuredTest.DISABILITY else option,
                credits,
                month,
                exit_month,
                kind,
            )
            for kind in kinds
        )
        last = (
            _last_insured(option, credits, month, exit_month)[0]
            if dated
            else None
        )
        yield tuple(found[0][0] for found in witnesses), last, witnesses


def _witness_rank(entry):
    """Order a status's witnesses the way ``_witness`` scores them."""
    witness = entry[0]
    return witness[0], witness[1] - witness[2], witness[1]


def _witness_ranks(table):
    return [[_witness_rank(entry) for entry in row] for row in table]


def _keep_favorable(kept, outcomes):
    """Each status's best witness so far, for each period ending."""
    found = tuple(zip(*(outcome[2] for outcome in outcomes), strict=True))
    if kept is None:
        return found
    return tuple(
        tuple(
            max(entries, key=_witness_rank)
            for entries in zip(*pair, strict=True)
        )
        for pair in zip(kept, found, strict=True)
    )


def _improves(outcome, returned, last_insured):
    statuses, last, _ = outcome
    return any(
        found and not kept
        for found, kept in zip(statuses, returned, strict=True)
    ) or (last or date.min) > (last_insured or date.min)


def _fillings_keeping_start(
    person, credits, start, month, exit_month, favored, binding
):
    """Each placement and treatment keeping the start and binding priors.

    Whether a filling keeps the start turns only on quarters through it
    (404.321(a)), so no later year can move it. Those years stay flexible,
    and each status places them favorably (RS00301.230).
    """
    witness = set(
        _witness(person, credits, start, exit_month, InsuredTest.DISABILITY)[4]
    )
    sensitive = _start_sensitive_years(
        person, person.disability_onset, start
    ) | _prior_sensitive_years(person, binding)

    def rank(choice):
        return len(set(choice) - witness), len(set(choice) - favored), choice

    for filling in _placements(
        person, credits, sensitive, month, exit_month, rank
    ):
        if not _keeps_priors(person, filling, binding, exit_month):
            continue
        for treatment in (
            (True, False) if person.prior_disability_periods else (None,)
        ):
            try:
                completed, own_start = _with_current_period(
                    person,
                    filling,
                    month,
                    exit_month,
                    use_periods_only=treatment,
                )
            except InvalidFamilyInput:
                continue
            if own_start == start:
                yield filling, completed


def _settle_first_start(
    person,
    credits,
    start,
    month,
    exit_month,
    kinds,
    returned,
    *,
    dated,
    last_insured,
    reported,
    favored,
    binding,
):
    """Refuse a result no filling and its own first start can support.

    Each status above places annual QCs favorably for its own window, and
    the established start does the same (RS00301.230). The two can rest on
    different placements. 404.321(a) gives one record one start, and the
    period's exclusions then shape FULLY, CURRENTLY and the date last
    insured. When placement or prior treatment can move the start, the
    result stands only if one filling attains it with the reported start
    as its own and no filling can improve on it. Flexible credits bound
    every filling at each possible start, so a bound that allows an
    improvement refuses by name. Otherwise the search begins at the filling
    that insures the start and varies the latest years first until a filling
    attains the result. Ties go to ``favored``, the quarters the excluded
    world credits, so the returned filling keeps a year's credits where it
    can. A year that cannot move the start stays flexible, so each status
    still places it favorably.

    The same limit binds what a status reports. Its favorable count and
    assignment can rest on a placement that would move the start, so
    ``reported`` holds each status's witness for each period ending, and
    the search continues past that filling until every one is attained with
    the reported start or the placements run out. It returns the filling
    that attained the result, with the best witnesses the reported start
    allows. It returns ``(None, ())`` when any filling keeps the start, or
    when ``reported`` is None because unknown years leave only an envelope.
    The search holds ``binding`` priors too, so their years count as start
    years.
    """
    # Source conflict us:oasdi-insured-one-filling-first-start
    if _start_fixed(person, credits, start, month, exit_month):
        return None, ()
    horizon = _current_period_start_horizon(person, month)
    for quarter in range(_qid(start), _qid(horizon) + 1):
        try:
            completed, own_start = _complete_current_period(
                person, _qdate(quarter)
            )
        except InvalidFamilyInput:
            continue
        if any(
            _improves(outcome, returned, last_insured)
            for outcome in _period_outcomes(
                person,
                completed,
                own_start,
                credits,
                month,
                exit_month,
                kinds,
                dated,
            )
        ):
            _refuse(
                InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
                "First insured start depends on annual placement "
                "or prior treatment",
            )
    return _settle_fillings(
        person,
        _fillings_keeping_start(
            person, credits, start, month, exit_month, favored, binding
        ),
        start,
        month,
        exit_month,
        kinds,
        returned,
        dated=dated,
        last_insured=last_insured,
        reported=reported,
        detail="First insured start depends on annual placement "
        "or prior treatment",
    )


def _settle_listed_priors(
    person,
    credits,
    month,
    exit_month,
    kinds,
    returned,
    *,
    dated,
    last_insured,
    reported,
    favored,
    binding,
):
    """Refuse a result no placement keeping the listed priors attains.

    The first-start reading applies to a prior's start with no current period
    to date: one filling of the years that can move that start must attain
    the result, and other years stay flexible for each status.
    """
    # Source conflict us:oasdi-insured-one-filling-first-start
    return _settle_fillings(
        person,
        (
            (filling, person)
            for filling in _placements(
                person,
                credits,
                _prior_sensitive_years(person, binding),
                month,
                exit_month,
                lambda choice: (len(set(choice) - favored), choice),
            )
            if _keeps_priors(person, filling, binding, exit_month)
        ),
        None,
        month,
        exit_month,
        kinds,
        returned,
        dated=dated,
        last_insured=last_insured,
        reported=reported,
        detail="Annual placement decides a listed prior's first insured "
        "quarter",
    )


def _settle_fillings(
    person,
    fillings,
    start,
    month,
    exit_month,
    kinds,
    returned,
    *,
    dated,
    last_insured,
    reported,
    detail,
):
    """Find one filling that attains a result, with its best witnesses."""
    joint = kept = None
    for filling, completed in fillings:
        outcomes = tuple(
            _period_outcomes(
                person,
                completed,
                start,
                filling,
                month,
                exit_month,
                kinds,
                dated,
            )
        )
        if joint is None and any(
            outcome[:2] == (returned, last_insured) for outcome in outcomes
        ):
            joint = filling
        if joint is not None and reported is None:
            return None, ()
        if reported is not None:
            kept = _keep_favorable(kept, outcomes)
        if joint is not None and _witness_ranks(kept) == _witness_ranks(
            reported
        ):
            return joint, kept
    # Every ending must still agree once each keeps the reported start.
    if joint is None or any(
        entry[0][0] != insured
        for entries, insured in zip(kept, returned, strict=True)
        for entry in entries
    ):
        _refuse(InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY, detail)
    return joint, kept


def _settle_lower_date(
    person, credits, start, month, exit_month, lowest, favored, binding
):
    """Refuse a lower date that some period ending cannot reach.

    Each ending's favorable date can rest on a placement that moves the
    reported start (404.321(a), RS00301.230). A lower bound speaks for every
    ending, so each needs a filling that keeps the start and reaches it.
    """
    # Source conflict us:oasdi-insured-one-filling-first-start
    if _start_fixed(person, credits, start, month, exit_month):
        return
    reached = None
    for filling, completed in _fillings_keeping_start(
        person, credits, start, month, exit_month, favored, binding
    ):
        found = tuple(
            last or date.min
            for _, last, _ in _period_outcomes(
                person,
                completed,
                start,
                filling,
                month,
                exit_month,
                (),
                True,
            )
        )
        reached = found if reached is None else tuple(map(max, reached, found))
        if min(reached) >= lowest:
            return
    _refuse(
        InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
        "A period ending cannot reach the lower date last insured "
        "with the reported first start",
    )


def _settle_every_history(person, credits, month, exit_month, decisions, dli):
    """Refuse a result some annual placement doesn't attain.

    UNKNOWN priors stand for every prior history, and UNKNOWN establishment
    for a period no one has placed. Each such period must begin in a quarter
    its holder was insured (404.320(b)(2), 404.321(a)), and that can force an
    annual QC into one quarter, so no placement chosen here speaks for every
    completion. Disregarding all periods stays open on any placement
    (404.130(f), RS00301.120). A result that every placement attains with no
    period in force therefore holds on every completion, and it needs no
    search of histories. ``credits`` are the lower credits, which speak for
    every completion of an UNKNOWN year.
    """
    # Source conflict us:oasdi-insured-one-filling-first-start
    bare = replace(person, prior_disability_periods=())
    for kind, decision in decisions.items():
        if (
            decision is not None
            and decision.insured
            and not _every_placement_passes(
                bare,
                credits,
                decision.qualifying_quarter,
                month,
                exit_month,
                kind,
            )
        ):
            _refuse(
                InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
                f"Annual placement decides {kind.value} "
                "across the unknown periods",
            )
    if (
        dli is not None
        and dli.lower is not None
        and not _every_placement_passes(
            bare,
            credits,
            _qdate(_qid(dli.lower)),
            month,
            exit_month,
            InsuredTest.DISABILITY,
            onset=False,
        )
    ):
        _refuse(
            InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
            "Annual placement decides the lower date last insured "
            "across the unknown periods",
        )


def _current_period_completions(person, completed, start, month):
    """Every possible end quarter through query, plus continuation.

    416(i)(2)(D) and 404.321(c) give alternative administrative endings.
    FRA/death cap the range; neither establishes its actual ending.
    End days within one quarter have identical insurance semantics.
    A continuity observation removes earlier endings; it never supplies
    an ending, including when observed later than the query.
    Historical candidates may include an ending invalid under the recovery
    offset. Over-inclusion can only prevent agreement and retain a refusal;
    it cannot certify a status that fails a valid completion.
    """
    if (
        start is None
        or person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
        or not _period_end_unknown(person, month)
    ):
        return (completed,)
    cap = completed.prior_disability_periods[-1].end
    last = min(_qid(month), _qid(cap))
    endings = [
        min(_qend(quarter), cap) for quarter in range(_qid(start), last + 1)
    ]
    if _qid(cap) > _qid(month):
        endings.append(cap)
    through = person.current_disability_period_continues_through
    if through is not None:
        endings = [end for end in endings if end >= through]
    return tuple(
        replace(
            completed,
            prior_disability_periods=person.prior_disability_periods
            + (DisabilityPeriod(start, end),),
        )
        for end in endings
    )


def _current_period_start_horizon(person, month):
    """Latest possible insured start under immutable period facts."""
    horizon = min(month, _fra_date(person).replace(day=1) - timedelta(days=1))
    for fixed_bound in (
        _historical_recovery_month(person)
        or person.current_disability_period_end,
        person.current_disability_period_continues_through,
        person.death_date,
    ):
        if fixed_bound is not None:
            horizon = min(horizon, fixed_bound.replace(day=1))
    return horizon


def _flagged_establishment_possible(person, years):
    """Preserve flags that can add credits outside the declared envelope.

    Fully-route flags change only the fully insured prerequisite, leaving
    404.130's independent recent-credit rule standing (404.110-.112;
    RS00301.101/.106/.470/.475; Act 213(c)). They are handled after that
    numerical proof. Except for blindness under 404.130(e), they retain
    the six-QC recent floor by the start horizon, including UNKNOWN prior
    history. UNKNOWN histories also face the joint optimistic-clock proof.
    With known history they additionally need a first insured start clear
    of prior quarters, or the automatic pre1956 alternate. A flag's start
    is unknown: only ordinary insurance for one filling and treatment
    fixes an overlapping first start, including with blindness. The
    pre1956 flag adds
    no route beyond the automatic alternate (RS00301.480 A/B.1); that
    alternate still requires twenty QCs. No flag's own conditions are
    adjudicated here.

    Raw-earnings flags affect compensation or SEI allocation (404.142/.144;
    RS00301.220/.340/.350). Final direct QC declarations already supply
    their credits, and unknown rows permit four; the I9 direct-credit
    contract therefore bounds them. Credit-route flags can add credits
    outside those rows: military credits may be freeze-only (404.133;
    RS00301.131), and government QCs combine for Medicare (RS00301.160).
    """
    for condition in person.conditions:
        if condition in _RAW_EARNINGS_CONDITIONS and all(
            row.qc_count is not None
            or row.qc_quarters is not None
            or row.provenance is EarningsProvenance.UNKNOWN
            for row in years.values()
        ):
            continue
        if (
            condition in _RAW_EARNINGS_CONDITIONS
            or condition in _CREDIT_ROUTE_CONDITIONS
        ):
            return True
    return False


def _minimum_current_period_qcs(person):
    """Lower bound across ordinary and alternate establishment routes.

    404.130(b)(2) and RS00301.480 require twenty QCs. The under31 and
    subsequent-special rules may require fewer (404.130(c)/(d)). Their
    elapsed-quarter count is smallest at onset with every prior-period
    quarter removed, including credited endpoints. Actual treatments can
    only restore quarters, and later starts can only increase elapsed
    quarters. Ignoring fully insured prerequisites further lowers the
    bound; this helper proves impossibility, never insurance.

    Blindness and unknown prior histories are excluded by the caller:
    blindness needs only fully insured status, while missing prior
    periods may supply additional exclusions or special eligibility.
    """
    end = _qid(person.disability_onset)
    young = end < _qid(_attain(person.birth_date, 31))
    subsequent = any(
        p.special_insured for p in person.prior_disability_periods
    )
    if not (young or subsequent):
        return 20
    first = max(1937 * 4, _qid(_attain(person.birth_date, 21)) + 1)
    elapsed = sum(
        not any(
            _qid(period.start) <= quarter <= _qid(period.end)
            for period in person.prior_disability_periods
        )
        for quarter in range(first, end + 1)
    )
    return min(20, max(6, elapsed // 2))


def _outside_prior_periods(person, quarter):
    """A candidate start must not overlap any declared prior quarter."""
    return all(
        not _qid(period.start) <= quarter <= _qid(period.end)
        for period in person.prior_disability_periods
    )


def _recent_rule_possible(
    person, credits, horizon, exit_month, *, lower_credits=None
):
    """404.130(b)-(d) possibility, relaxing only the fully prerequisite.

    For one filling and treatment, an overlapping quarter fixes the first
    start only if ordinary disability insurance holds without a flag
    (404.321(a)). A recent-only witness cannot date a flag's unknown fully
    insured status. Blindness has no recent test (404.130(e)). Enumerate
    annual placements and unresolved lower fillings, retaining favorable
    prior treatment. Complexity cannot disprove a specialist declaration;
    this deliberately permits loose refusals rather than losing lawful rows.
    """
    try:
        candidates = range(_qid(person.disability_onset), _qid(horizon) + 1)
        if all(
            _outside_prior_periods(person, quarter) for quarter in candidates
        ):
            if person.statutory_blindness:
                return True
            return any(
                _witness(
                    person,
                    credits,
                    _qdate(quarter),
                    exit_month,
                    InsuredTest.DISABILITY,
                    ignore_fully_insured=True,
                )[0]
                for quarter in candidates
            )
        rows, _ = _world(person, credits, _qid(horizon), exit_month, False)
        options = []
        for year, row in rows.items():
            high = _assignment_candidates(*row)
            if (
                lower_credits is not None
                and lower_credits[year] != credits[year]
            ):
                fixed = tuple(q for q in lower_credits[year][0] if q in row[2])
                vacant = tuple(q for q in row[2] if q not in fixed)
                minimum = min(lower_credits[year][1], len(vacant))
                maximum = max(map(len, high)) - len(fixed)
                high = tuple(
                    tuple(sorted((*fixed, *choice)))
                    for count in range(minimum, maximum + 1)
                    for choice in combinations(vacant, count)
                )
            options.append(high)
        if prod(map(len, options)) > 4096:
            return True
        for choices in product(*options):
            filling = {
                year: (choice, 0)
                for year, choice in zip(rows, choices, strict=True)
            }
            for treatment in (True, False):
                for quarter in range(
                    _qid(person.disability_onset), _qid(horizon) + 1
                ):
                    ordinary = _witness(
                        person,
                        filling,
                        _qdate(quarter),
                        exit_month,
                        InsuredTest.DISABILITY,
                        use_periods_only=treatment,
                    )[0]
                    # Source conflict us:oasdi-insured-flag-first-insured-quarter
                    rule_met = (
                        person.statutory_blindness
                        or ordinary
                        or _witness(
                            person,
                            filling,
                            _qdate(quarter),
                            exit_month,
                            InsuredTest.DISABILITY,
                            ignore_fully_insured=True,
                            use_periods_only=treatment,
                        )[0]
                    )
                    if rule_met and _outside_prior_periods(person, quarter):
                        return True
                    if ordinary:
                        break
    except InsuredConfigurationUnsupported:
        return True
    return False


def _unknown_prior_joint_shortfall(person, rows, horizon, fully_route):
    """Disprove joint prior/current insurance on an optimistic clock.

    Every earliest prior needs fully insured status (404.130(a), (e)).
    Allow historical blindness even when current blindness is false.
    After its earliest possible start, delete every uncredited quarter
    before the current start while retaining every QC, even interiors.
    This relaxation dominates any number of real prior periods, whose
    endpoints cannot delete credited quarters without also losing QCs.
    An extra QC cannot hurt either a half-elapsed or a 20/40 test on this
    clock. Upper-credit placements therefore bound every lower filling.
    A special prior must itself have six QCs before age 31 (404.130(d)).

    Search at most 4096 annual placements; a larger space proves nothing.
    This is only a necessary-condition proof, never a concrete witness.
    The historical alternate is handled separately by the caller.
    """
    # Source conflict us:oasdi-insured-unknown-prior-historical-blindness
    options = [_assignment_candidates(*row) for row in rows.values()]
    if prod(map(len, options)) > 4096:
        return False
    first = max(1937 * 4, _qid(_attain(person.birth_date, 21)) + 1)
    age31 = _qid(_attain(person.birth_date, 31))
    onset = _qid(person.disability_onset)
    last = _qid(horizon)
    for choices in product(*options):
        assigned = {q for annual in choices for q in annual}
        earliest = None
        if fully_route:
            earliest = _qid(person.birth_date)
        elif assigned:
            # This is the earliest possible period of any medical type.
            # No earlier period can supply exclusions for this test.
            for quarter in range(min(assigned), min(onset, last) + 1):
                if sum(q <= quarter for q in assigned) >= _requirement(
                    person, _qdate(quarter), for_disability=True
                ):
                    earliest = quarter
                    break

        clock_first = min(first - 40, min(assigned, default=first))

        def clock(
            quarter,
            clock_first=clock_first,
            earliest=earliest,
            assigned=assigned,
        ):
            # The candidate itself cannot be excluded. Before the first
            # possible prior, every elapsed quarter remains unavoidable.
            return tuple(
                q
                for q in range(clock_first, quarter + 1)
                if earliest is None
                or q < earliest
                or q == quarter
                or q in assigned
            )

        def special_recent(quarter, clock=clock, assigned=assigned):
            counted = clock(quarter)
            elapsed = tuple(q for q in counted if q >= first)
            if len(elapsed) < 12:
                window, required = counted[-12:], 6
            else:
                # Source conflict us:oasdi-insured-subsequent-special-long-period
                window, required = elapsed, max(6, len(elapsed) // 2)
            return len(set(window) & assigned) >= required

        # Optimistically permit every prior-special start, including a
        # blindness prefix, but never credits earned at/after age 31.
        special = earliest is not None and any(
            special_recent(quarter)
            for quarter in range(
                max(clock_first, earliest),
                min(
                    age31,
                    _qid(person.disability_onset - timedelta(days=1)) + 1,
                    last,
                ),
            )
        )
        for quarter in range(onset, last + 1):
            if len(set(clock(quarter)[-40:]) & assigned) >= 20:
                return False
            if (quarter < age31 or special) and special_recent(quarter):
                return False
    return True


def _could_establish_current_period(
    person,
    years,
    credits,
    month,
    exit_month,
    maximum_qcs,
    *,
    lower_credits=None,
    deferred_years=(),
    totalization_credits=(),
):
    """Reject only a declaration impossible under every possible route.

    A fixed ending or continuity observation bounds the insured start.
    Upper credits decide ordinary insurance by that bound, but a derived
    prior-quarter overlap must be cleared by that same concrete filling.
    Calendar/schema contradictions have already been rejected. Ordinary
    premises cannot exclude a specialist route or a short DIB-entitled
    prior period. Fixed quarter overlap is checked before searching.
    Unresolved prior histories and more than 4096 overlap fillings that
    survive that check remain outside the exact ordinary predicate.
    The stronger known-history minimum proof stays first. Except for
    blindness with a fully-route flag, six QCs must then be feasible by
    the immutable horizon before UNKNOWN prior history can preserve a
    route. The alternate's start must itself clear prior-period overlap.
    UNKNOWN prior histories face an optimistic joint clock that permits
    past blindness and dominates every number of real prior periods.
    A fully-route flag's starting quarter is unknown. Only ordinary
    insurance for one filling and treatment fixes an overlapping first
    start, including with blindness (404.321(a)). A construction refusal
    preserves possibility until later validation has checked input errors.
    A decisive pre1951 aggregate is an automatic fully route, with or
    without its flag; it never counts toward the recent rule.
    """
    if not person.current_disability_period_established:
        return True
    horizon = _current_period_start_horizon(person, month)
    if person.prior_disability_periods and not any(
        _outside_prior_periods(person, quarter)
        for quarter in range(_qid(person.disability_onset), _qid(horizon) + 1)
    ):
        return False
    # Fixed chronology is independent of the unmodeled foreign route;
    # no own-credit count proves impossibility on that route here.
    if totalization_credits:
        return True
    if _flagged_establishment_possible(person, years):
        return True
    # This proof must precede the alternate's boundary enumeration and
    # unknown-prior feasibility search: either can otherwise refuse before
    # an assignment-independent impossibility has been established.
    if (
        not person.statutory_blindness
        and person.prior_disability_periods_provenance
        is not EarningsProvenance.UNKNOWN
        and maximum_qcs < _minimum_current_period_qcs(person)
    ):
        return False
    fully_route = bool(
        person.conditions & _FULLY_INSURED_ROUTE_CONDITIONS
    ) or _aggregate_establishment_possible(
        person, years, credits, horizon, exit_month
    )
    if fully_route and person.statutory_blindness:
        return _recent_rule_possible(
            person, credits, horizon, exit_month, lower_credits=lower_credits
        )
    # 404.130(b)-(d) and RS00301.480 retain at least six QCs even
    # when UNKNOWN prior history changes the window or special route.
    rows, _ = _world(person, credits, _qid(horizon), exit_month, False)
    horizon_qcs = sum(len(_assign_qcs(*row)) for row in rows.values())
    if horizon_qcs < 6:
        return False
    if (
        6 <= horizon_qcs
        and not person.statutory_blindness
        and person.disability_onset >= date(1956, 1, 1)
        and person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
        and _unknown_prior_joint_shortfall(person, rows, horizon, fully_route)
    ):
        return False
    if (
        fully_route
        and person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
    ):
        return True
    if fully_route and _recent_rule_possible(
        person, credits, horizon, exit_month, lower_credits=lower_credits
    ):
        return True
    if _pre1956_alternate_possible(
        person, credits, month, exit_month, lower_credits=lower_credits
    ):
        return True
    if fully_route:
        return False
    if (
        person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
        and not _unknown_prior_history_is_empty(
            person, credits, month, exit_month, lower_credits=lower_credits
        )
    ):
        return True
    plain = replace(
        person,
        prior_disability_periods_provenance=EarningsProvenance.OBSERVED,
        prior_disability_periods_convention_id=None,
    )
    try:
        _with_current_period(plain, credits, horizon, exit_month)
    except InsuredConfigurationUnsupported:
        return True
    except InvalidFamilyInput:
        pass
    else:
        return True
    # Ordinary insurance by a fixed date is monotone in credited quarters.
    # An upper-credit failure here therefore disproves every ordinary
    # filling, even if the same record first qualifies after the ending.
    if not _decision_witness(
        plain, credits, horizon, exit_month, InsuredTest.DISABILITY
    )[0][0]:
        return False
    unknown = tuple(
        year
        for year, row in sorted(years.items())
        if (
            row.provenance is EarningsProvenance.UNKNOWN
            or year in deferred_years
        )
        and year <= horizon.year
    )
    if not unknown:
        return False
    lower = dict(credits if lower_credits is None else lower_credits)
    if lower_credits is None:
        lower.update({year: ((), 0) for year in unknown})
    try:
        _with_current_period(plain, lower, horizon, exit_month)
    except InsuredConfigurationUnsupported:
        return True
    except InvalidFamilyInput:
        pass
    else:
        return True
    # A later witness alone does not suffice: the first insured quarter
    # must both avoid the represented prior period and precede the fixed
    # bound. Enumerate complete fillings only in this nonmonotone corner.
    options = []
    for year in unknown:
        allowed = rows.get(year, ((), 0, ()))[2]
        if year < 1978:
            fixed = tuple(q for q in lower[year][0] if q in allowed)
            vacant = tuple(q for q in allowed if q not in fixed)
            options.append(
                tuple(
                    (
                        tuple(
                            sorted(
                                fixed
                                + tuple(
                                    q
                                    for q, flag in zip(
                                        vacant, flags, strict=True
                                    )
                                    if flag
                                )
                            )
                        ),
                        0,
                    )
                    for flags in product((False, True), repeat=len(vacant))
                )
            )
        else:
            options.append(
                tuple(
                    ((), count)
                    for count in range(min(len(allowed), credits[year][1]) + 1)
                )
            )
    if prod(map(len, options)) > 4096:
        _refuse(
            InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
            "More than 4096 current-period overlap fillings; "
            "ordinary establishment validity is unresolved",
        )
    for choices in product(*options):
        filling = dict(credits)
        filling.update(zip(unknown, choices, strict=True))
        try:
            _with_current_period(plain, filling, horizon, exit_month)
        except InsuredConfigurationUnsupported:
            return True
        except InvalidFamilyInput:
            continue
        return True
    return False


def _status_decision(lo_candidates, hi_candidates, envelope=None):
    """One status from its candidates; ``envelope`` widens unsure counts."""
    lo, lo_quarter = lo_candidates[-1]
    hi, hi_quarter = hi_candidates[0]
    witnesses = [value for value, _ in (*lo_candidates, *hi_candidates)]
    count_lo, count_hi, full_lo, full_hi = (
        (0, envelope, 0, envelope)
        if envelope is not None
        else (
            min(w[1] for w in witnesses),
            max(w[1] for w in witnesses),
            min(w[7] for w in witnesses),
            max(w[7] for w in witnesses),
        )
    )
    return _computed(
        StatusDecision,
        lo[0],
        count_lo,
        count_hi,
        lo[2],
        lo[3],
        lo[4],
        lo[5],
        hi[2],
        hi[3],
        hi[4],
        hi[5],
        lo[6],
        hi[6],
        full_lo,
        full_hi,
        lo_quarter,
        hi_quarter,
    )


def _dli_cap(person, month, exit_month):
    cap = min(_qid(month), _fra_quarter(person) - 1)
    if exit_month is not None and exit_month <= month:
        cap = _fra_quarter(person) - 1
    if person.death_date is not None:
        cap = min(cap, _qid(person.death_date))
    return _qend(cap)


@_validated_entry
def insured_status(
    person: Person,
    years: Mapping[int, CoverageYear],
    month: date,
    *,
    test: InsuredTest = InsuredTest.ALL,
    coverage_end_month: date | None = None,
    totalization_credits: tuple[str, ...] = (),
) -> InsuredStatus:
    """Decide declared insurance, retaining coverage refusals in denominators.

    Medical onset means continuously disabled through this query, subject
    to an established historical period's ending under 404.321(b), and
    never establishes a period. Declare establishment, prior-period provenance,
    and section 214(c) applicability; UNKNOWN never silently means none.
    Declare an administrative ending with its provenance when known. An
    observed continues-through date instead excludes earlier endings and
    may be later than the query; it does not declare an endpoint. An
    ongoing period is bounded by possible endings, with a named refusal if
    the ending changes a requested status, and is always capped before FRA.
    Each disability window ends at its tested quarter, from onset through
    query, and the first insured quarter supplies the witness (404.131).
    An alternate for disability before 1956 is excluded only by 20/40 in a
    quarter beginning before the FRA month, independently of establishment.
    For established periods it must also begin by every completion's
    disabled month: the declared end or continuity month minus two, clamped
    at onset, or otherwise onset. Validity instead uses the latest possible
    disabled month: a historical recovery end minus two, without inferring
    recovery from FRA, death, or paragraph (c) endings. The alternate's
    continuous clock uses all prior periods or disregards all of them.
    UNKNOWN establishment before FRA uses onset for the same bound and
    cannot bypass the alternate with a later positive DISABILITY witness.
    FULLY and CURRENTLY retain true favorable-disregard witnesses; declared
    absence and onset at or after FRA admit no established completion.
    Disagreement with the literal any-quarter reading retains the named
    alternate refusal; post-1980 endings can differ under 404.321(c).
    Establishment is an input error only if no ordinary, observable, or
    flagged specialist route could validate any completion of the facts.
    Foreign credits preserve an unmodeled route before credit-count proofs;
    no totalization minimum or eligibility rule is claimed. A conservative
    minimum-QC proof precedes fully-insured-only flags and boundary
    complexity, except for blindness and unknown prior history. A separate
    six-QC floor uses credits feasible by the immutable start horizon;
    only blindness with a fully-route flag bypasses it. UNKNOWN prior
    history changes windows or special eligibility, never this floor.
    With known nonblind history, fully-route flags must retain a recent
    first insured start outside prior quarters, or automatic pre1956
    alternate. A pre1951 aggregate that could supply a failed fully insured
    prerequisite is such a route without a flag, and DISABILITY, the
    start and the date last insured refuse by name when it decides them.
    UNKNOWN history also faces a joint optimistic-clock proof
    permitting past blindness; survival never claims a concrete history.
    A fully-route flag's start is unknown, including with blindness;
    only ordinary insurance for the same filling and treatment fixes an
    overlapping first quarter. The alternate must use one
    start clearing fixed overlap, the horizon and its 1955 date limit;
    its prior-period clock and credited endpoints remain unchanged.
    If a clear first start depends on annual placement or prior treatment
    after a favorable overlapping start, retain a named boundary refusal.
    A first successful filling cannot settle the other requested statuses:
    wherever placement or treatment can move the start, one filling with
    its own start must attain the returned result and none may beat it.
    Each status then reports the best count and assignment that start
    allows, and the year counts and top-level assignment describe the
    returned filling. An UNKNOWN fact keeps its envelope instead.
    The pre1956 flag adds no route beyond the automatic alternate. A flag's
    own conditions remain declared facts and are not tested.
    History validation runs first. Uncomputable QC rows use bounded
    unknown credits only for this proof; a possible declaration retains
    its original conversion refusal, including its reason and detail.
    No entry date, imputation, or pre-entry zero convention exists.
    """
    _validate_history(
        person, years, month, coverage_end_month, totalization_credits
    )
    lower, upper, deferred = {}, {}, {}
    for year, row in sorted(years.items()):
        try:
            lower[year] = _credits(year, row, False)
            upper[year] = _credits(year, row, True)
        except InsuredConfigurationUnsupported as error:
            deferred[year] = error
            lower[year], upper[year] = _deferred_credit_bounds(year, row)
    unknown = tuple(
        y
        for y, row in sorted(years.items())
        if row.provenance is EarningsProvenance.UNKNOWN
    )
    prior_unknown = (
        person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
    )
    current_unknown = _current_period_establishment_unknown(person)
    end_unknown = _period_end_unknown(person, month)
    max_rows, _ = _world(
        person,
        upper,
        _qid(month),
        coverage_end_month,
        False,
        include_zero=True,
    )
    maximum_qcs = sum(len(_assign_qcs(*row)) for row in max_rows.values())
    try:
        possible = _could_establish_current_period(
            person,
            years,
            upper,
            month,
            coverage_end_month,
            maximum_qcs,
            lower_credits=lower,
            deferred_years=tuple(deferred),
            totalization_credits=totalization_credits,
        )
    except InsuredConfigurationUnsupported:
        if deferred:
            raise next(iter(deferred.values())) from None
        raise
    if not possible:
        raise InvalidFamilyInput(
            "Established current period has no possible insured disabled quarter"
        )
    if deferred:
        raise next(iter(deferred.values()))
    _coverage_checks(person, years, month, totalization_credits)
    if (
        person.current_disability_period_established
        and _pre1956_alternate_possible(
            person, upper, month, coverage_end_month, lower_credits=lower
        )
    ):
        _refuse(
            InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
            "RS00301.480 may establish the declared current period; "
            "application conditions are unmodeled",
        )
    applicability = _sspa211_applicability(person)
    # Known applicable cases require unimplemented work-authorization/visa
    # adjudication. Unknown applicability can decide a QC-only false result.
    if applicability is True:
        _refuse(
            InsuredUnsupportedReason.ALIEN_WORKER,
            "SSPA211 additional alien-worker facts",
        )
    # Favorable disregard is a treatment, not a claim that a known
    # established period never existed (404.320(a),404.130(f)). Unknown
    # prior periods cannot be mixed selectively with the current period.
    uncertain_current_start = False
    if prior_unknown:
        lo_person = hi_person = person
        lo_start = hi_start = None
        if person.current_disability_period_established:
            # A history can force any placement, so only a start that every
            # placement insures speaks for every history.
            if _start_fixed(
                person,
                lower,
                person.disability_onset,
                month,
                coverage_end_month,
            ):
                lo_start = hi_start = person.disability_onset
            else:
                uncertain_current_start = True
    else:
        try:
            lo_person, lo_start = _with_current_period(
                person,
                lower,
                month,
                coverage_end_month,
            )
            hi_person, hi_start = (
                _with_current_period(
                    person,
                    upper,
                    month,
                    coverage_end_month,
                )
                if unknown
                else (lo_person, lo_start)
            )
        except InvalidFamilyInput:
            if unknown:
                _refuse(
                    InsuredUnsupportedReason.UNKNOWN_EARNINGS,
                    "Unknown earnings decide a valid established current period",
                )
            # Only an automatic aggregate route can reach this point with
            # known credits and no ordinary start.
            if _aggregate_establishment_possible(
                person,
                years,
                upper,
                _current_period_start_horizon(person, month),
                coverage_end_month,
            ):
                _refuse(
                    InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                    "Pre1951 wages may supply the current period's fully "
                    "insured prerequisite; filing facts are unmodeled",
                )
            # With known credits the shared possibility predicate already
            # validated this identical construction before any refusal.
            raise
        # An aggregate could insure an earlier quarter than the ordinary
        # first start, and 404.321(a) then moves the period's start.
        if lo_start is not None and any(
            _aggregate_could_insure(
                person, years, upper, _qdate(quarter), coverage_end_month
            )
            for quarter in range(_qid(person.disability_onset), _qid(lo_start))
        ):
            _refuse(
                InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                "Pre1951 wages may move the first insured start; "
                "filing facts are unmodeled",
            )
    if lo_start != hi_start:
        _refuse(
            InsuredUnsupportedReason.UNKNOWN_EARNINGS,
            "Unknown earnings decide established current period start",
        )
    lo_completions = _current_period_completions(
        person, lo_person, lo_start, month
    )
    hi_completions = _current_period_completions(
        person, hi_person, hi_start, month
    )
    # The current disability is known only through the query. A frozen-exit
    # future DLI would require its unobserved recovery/end date.
    if (
        person.current_disability_period_established
        and not prior_unknown
        and end_unknown
        and coverage_end_month is not None
        and coverage_end_month <= month
        and _dli_cap(person, month, coverage_end_month) > _qend(_qid(month))
        and test in (InsuredTest.ALL, InsuredTest.DISABILITY)
    ):
        _refuse(
            InsuredUnsupportedReason.CURRENT_PERIOD_DLI,
            "Current period end beyond query is unobserved",
        )
    decisions, candidates = {}, {}
    for kind in (
        InsuredTest.FULLY,
        InsuredTest.CURRENTLY,
        InsuredTest.DISABILITY,
    ):
        decisions[kind] = None
        if test not in (InsuredTest.ALL, kind):
            continue
        # Establishment follows the first insured quarter; using its own
        # exclusion to prove that quarter would be circular. Subsequent
        # hypothetical-onset DLI quarters can use the established period.
        decision_lo_people = (
            (person,) if kind is InsuredTest.DISABILITY else lo_completions
        )
        decision_hi_people = (
            (person,) if kind is InsuredTest.DISABILITY else hi_completions
        )
        lo_candidates = [
            _decision_witness(
                p,
                lower,
                month,
                coverage_end_month,
                kind,
            )
            for p in decision_lo_people
        ]
        hi_candidates = (
            [
                _decision_witness(
                    p,
                    upper,
                    month,
                    coverage_end_month,
                    kind,
                )
                for p in decision_hi_people
            ]
            if unknown
            else lo_candidates
        )
        lo, lo_quarter = lo_candidates[-1]
        hi, hi_quarter = hi_candidates[0]
        if end_unknown:
            if any(witness[0] != lo[0] for witness, _ in lo_candidates) or any(
                witness[0] != hi[0] for witness, _ in hi_candidates
            ):
                _refuse(
                    InsuredUnsupportedReason.CURRENT_PERIOD_END,
                    f"Unobserved statutory period end decides {kind.value}",
                )
        for p, (witness, quarter) in zip(
            decision_lo_people, lo_candidates, strict=True
        ):
            _observable_coverage_paths(
                p,
                years,
                month,
                coverage_end_month,
                kind,
                witness,
                quarter,
                upper,
                lower,
            )
        if lo[0] != hi[0]:
            _refuse(
                InsuredUnsupportedReason.UNKNOWN_EARNINGS,
                f"{kind.value} differs across unknown years {unknown}",
            )
        # Six lifetime QCs is a universal prerequisite. Otherwise an
        # unknown period could supply exclusions or earlier special status.
        if (
            (
                prior_unknown
                or current_unknown
                and kind is not InsuredTest.DISABILITY
            )
            and not lo[0]
            and maximum_qcs >= 6
        ):
            _refuse(
                (
                    InsuredUnsupportedReason.UNKNOWN_PERIODS
                    if prior_unknown
                    else InsuredUnsupportedReason.UNKNOWN_CURRENT_PERIOD
                ),
                f"Unknown established periods may change {kind.value}",
            )
        if applicability is None and lo[0]:
            _refuse(
                InsuredUnsupportedReason.UNKNOWN_SSPA211,
                f"SSPA211 applicability may change {kind.value}",
            )
        # A selected witness can switch as credits rise; its count is not
        # monotone. With uncertain credits and treatment/witness choices,
        # use the universal envelope: every assignment has 0..maximum_qcs.
        broad = (
            prior_unknown
            or current_unknown
            or end_unknown
            and bool(unknown)
            or bool(unknown)
            and (
                bool(person.prior_disability_periods)
                or person.disability_onset is not None
                or kind is InsuredTest.CURRENTLY
                and len(_events(person, month, kind)) > 1
            )
        )
        candidates[kind] = lo_candidates
        decisions[kind] = _status_decision(
            lo_candidates, hi_candidates, maximum_qcs if broad else None
        )
    dli = None
    if test in (InsuredTest.ALL, InsuredTest.DISABILITY):
        lower_dates = [
            _last_insured(p, lower, month, coverage_end_month, years=years)
            for p in lo_completions
        ]
        upper_dates = (
            [
                _last_insured(p, upper, month, coverage_end_month, years=years)
                for p in hi_completions
            ]
            if unknown
            else lower_dates
        )
        lo_date = min((d for d, _ in lower_dates), key=lambda d: d or date.min)
        hi_date = max((d for d, _ in upper_dates), key=lambda d: d or date.min)
        lo_censored = any(c for _, c in lower_dates)
        hi_censored = any(c for _, c in upper_dates)
        if (prior_unknown or current_unknown) and maximum_qcs >= 6:
            hi_date = _dli_cap(person, month, coverage_end_month)
            hi_censored = (
                coverage_end_month is None or coverage_end_month > month
            ) and _qid(hi_date) == _qid(month)
        if applicability is None:
            # A guaranteed historical fully insured witness also needs
            # resolved section 214(c) facts. Keep the QC-only upper date;
            # false current status cannot prove a positive DLI lower date.
            lo_date = None
        dli = _computed(DLIRange, lo_date, hi_date, lo_censored or hi_censored)
    if prior_unknown or current_unknown:
        _settle_every_history(
            person, lower, month, coverage_end_month, decisions, dli
        )
    bases = tuple(
        _prior_basis(person, lower, upper, index, month, coverage_end_month)
        for index in range(len(person.prior_disability_periods))
    )
    # Every placement attains what the proof above passes, so a prior that
    # picks among them can't move it.
    binding = tuple(
        (index, blind)
        for index, blind in enumerate(bases)
        if not current_unknown
        and _prior_start_binds(
            person, lower, upper, index, month, coverage_end_month, blind
        )
    )
    if binding and unknown:
        _refuse(
            InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
            "Annual placement decides a listed prior's first insured quarter",
        )
    placement = None
    if lo_start is not None or binding:
        favored_rows, _ = _world(
            lo_person,
            upper,
            _qid(month),
            coverage_end_month,
            True,
            include_zero=True,
        )
        favored = frozenset(
            quarter
            for row in favored_rows.values()
            for quarter in _assign_qcs(*row)
        )
        kinds = tuple(
            kind
            for kind in (
                InsuredTest.FULLY,
                InsuredTest.CURRENTLY,
                *((InsuredTest.DISABILITY,) if binding else ()),
            )
            if decisions[kind] is not None
        )
        search = {
            "dated": dli is not None,
            "last_insured": dli.upper if dli is not None else None,
            "reported": (
                None if unknown else tuple(candidates[kind] for kind in kinds)
            ),
            "favored": favored,
            "binding": binding,
        }
        returned = tuple(decisions[kind].insured for kind in kinds)
        placement, settled = (
            _settle_first_start(
                person,
                upper,
                hi_start,
                month,
                coverage_end_month,
                kinds,
                returned,
                **search,
            )
            if lo_start is not None
            else _settle_listed_priors(
                person,
                upper,
                month,
                coverage_end_month,
                kinds,
                returned,
                **search,
            )
        )
        for kind, witnesses in zip(kinds, settled, strict=False):
            decisions[kind] = _status_decision(witnesses, witnesses)
        if lo_start is not None and dli is not None and dli.lower is not None:
            _settle_lower_date(
                person,
                lower,
                lo_start,
                month,
                coverage_end_month,
                dli.lower,
                favored,
                binding,
            )
    lo_rows, _ = _world(
        lo_person,
        placement or lower,
        _qid(month),
        coverage_end_month,
        True,
        include_zero=True,
    )
    hi_rows, _ = _world(
        hi_person,
        upper,
        _qid(month),
        coverage_end_month,
        True,
        include_zero=True,
    )
    assigned = {y: _assign_qcs(*row) for y, row in lo_rows.items()}
    completion_rows = [
        _world(
            p,
            credits,
            _qid(month),
            coverage_end_month,
            True,
            include_zero=True,
        )[0]
        for people, credits in (
            (lo_completions, placement or lower),
            (hi_completions, placement or upper),
        )
        for p in people
    ]
    unknown_facts = tuple(
        name
        for name, missing in (
            ("prior_disability_periods", prior_unknown),
            ("current_disability_period", current_unknown),
            ("current_disability_period_start", uncertain_current_start),
            ("current_disability_period_end", end_unknown),
            ("sspa211_applicability", applicability is None),
        )
        if missing
    )
    conventions = {
        name: identifier
        for name, identifier in (
            (
                "prior_disability_periods",
                person.prior_disability_periods_convention_id,
            ),
            (
                "current_disability_period",
                person.current_disability_period_convention_id,
            ),
            (
                "current_disability_period_end",
                person.current_disability_period_end_convention_id,
            ),
            (
                "current_disability_period_continues_through",
                person.current_disability_period_continues_through_convention_id,
            ),
            ("sspa211_applicability", person.sspa211_convention_id),
        )
        if identifier is not None
    }
    return _computed(
        InsuredStatus,
        VERSION,
        month,
        decisions[InsuredTest.FULLY],
        decisions[InsuredTest.CURRENTLY],
        decisions[InsuredTest.DISABILITY],
        dli,
        MappingProxyType(
            {
                y: (
                    (
                        0
                        if prior_unknown or current_unknown
                        else min(
                            len(_assign_qcs(*rows[y]))
                            for rows in completion_rows
                        )
                    ),
                    (
                        len(_assign_qcs(*max_rows[y]))
                        if prior_unknown or current_unknown
                        else max(
                            len(_assign_qcs(*rows[y]))
                            for rows in completion_rows
                        )
                    ),
                )
                for y in lo_rows
            }
        ),
        MappingProxyType(assigned),
        unknown,
        MappingProxyType(
            {
                y: row.convention_id
                for y, row in sorted(years.items())
                if row.provenance is EarningsProvenance.CONVENTION_FILLED
            }
        ),
        bool(unknown or unknown_facts),
        lo_start,
        unknown_facts,
        MappingProxyType(conventions),
    )


@_sealed_result
@dataclass(frozen=True)
class InsuredOutcome(_SealedOutcome):
    key: str
    weight: Fraction
    result: InsuredStatus | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        _check_evaluation_inputs(self.key, self.weight, lambda: None)
        if self.result is not None:
            _checked_result(self.result, InsuredStatus)
        if self.unsupported is not None:
            _check_refusal(self.unsupported)
        if (self.result is None) == (self.unsupported is None):
            raise InvalidFamilyInput(
                "Exactly one insured result/refusal required"
            )

    @property
    def supported(self) -> bool:
        _check_seal(self)
        return self.result is not None


@_validated_entry
def evaluate_insured_status(
    key: str, weight: Fraction, compute: Callable[[], InsuredStatus]
) -> InsuredOutcome:
    """Keep every coverage refusal in count_family_outcomes' denominator."""
    _check_evaluation_inputs(key, weight, compute)
    try:
        result = compute()
    except FamilyConfigurationUnsupported as error:
        return _computed(InsuredOutcome, key, weight, None, error)
    _checked_result(result, InsuredStatus)
    return _computed(InsuredOutcome, key, weight, result, None)
