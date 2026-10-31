"""Track B insured status, version track-b-insured-v1.

Verification class: statutory conformance. Admitted scope: declared invented
histories and captured statutory examples only; no population, behavioral,
or forecast claim. Act 213, 214, 216(i), 223(c); 20 CFR 404 subpart B
and 404.315/.320/.321;
POMS RS 00301. Every year is declared, including zero and unknown years.
Medical onset declares continuous disability through the query month; it
never establishes an administrative period of disability. An established
period ends no later than the month before full retirement age; an unknown
ending is bounded rather than fabricated at the query. Disability tests
scan onset and later quarters; period establishment and section 214(c)
applicability carry explicit provenance. Impossible UNKNOWN histories are
rejected before any coverage refusal. Observable specialist credit
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
from itertools import product
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


def _fact_provenance(provenance, convention_id, label):
    convention = provenance is EarningsProvenance.CONVENTION_FILLED
    if convention != (convention_id is not None):
        raise InvalidFamilyInput(f"Only convention-filled {label} needs an id")
    if convention and not convention_id.strip():
        raise InvalidFamilyInput("Convention identifier must be nonempty")


def _sspa211_applicability(person):
    # RS00301.102 B.1/B.3: pre2004 assignments are exempt; an alien
    # without a true-identity SSN is subject to the additional requirement.
    legacy = None
    if person.alien_worker:
        if person.ssn_never_assigned:
            legacy = True
        elif person.ssn_assignment_date is not None:
            legacy = person.ssn_assignment_date >= date(2004, 1, 1)
    if person.sspa211_applies is not None:
        if legacy is not None and legacy != person.sspa211_applies:
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
            if end < self.disability_onset:
                raise InvalidFamilyInput("Current period ends before onset")
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
            self.current_disability_period_established
            and self.disability_onset >= fra.replace(day=1)
        ):
            raise InvalidFamilyInput(
                "Established period begins after its statutory FRA end"
            )
        fra_end = fra.replace(day=1) - timedelta(days=1)
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


def _observable_coverage_paths(
    person, years, month, exit_month, kind, lo, upper
):
    """Refuse favorable specialist paths revealed by ordinary declarations.

    Act 213(c), 404.110(d), and RS 00301.315 make the pre1951 aggregate
    method available independently of an optional specialist flag. Its
    application, retroactivity and section227 conditions are not declared.
    Act213(c) has no seven-EY limitation, unlike 404.110(d) and RS .315;
    a potentially decisive path is refused without deciding that conflict.
    Direct QC declarations supply credited quarters, not raw wage totals.
    RS 00301.480 likewise reveals a possible pre1956 alternate disability
    path from onset and earnings; its application facts remain unmodeled.
    """
    if lo[0]:
        return
    if kind is InsuredTest.FULLY:
        before1951 = {year: row for year, row in years.items() if year < 1951}
        if not before1951:
            return
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
        rows, _ = _world(person, upper, _qid(month), exit_month, False)
        post1950 = sum(
            len(_assign_qcs(*row))
            for year, row in rows.items()
            if year >= 1951
        )
        periods = tuple(
            (period.start, period.end)
            for period in person.prior_disability_periods
        )
        # The favorable ordinary witness may disregard a freeze whose
        # lower prerequisite would favor the simplified aggregate instead.
        # Use every known period, including a derived current period, and
        # the universal six-QC lower bound for unresolved applicability.
        required = min(lo[6], _requirement(person, month, periods))
        if (
            person.prior_disability_periods_provenance
            is EarningsProvenance.UNKNOWN
            or person.disability_onset is not None
            and person.disability_onset < _fra_date(person).replace(day=1)
            and person.current_disability_period_provenance
            is EarningsProvenance.UNKNOWN
        ):
            required = 6
        if unknown_wages or (
            wages >= 400 and wages // 400 + post1950 >= required
        ):
            _refuse(
                InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
                "Pre1951 wages may establish fully insured status under "
                "Act213(c); filing and retroactivity facts are unmodeled",
            )
    elif (
        kind is InsuredTest.DISABILITY
        and person.disability_onset is not None
        and person.disability_onset < date(1956, 1, 1)
    ):
        first = max(_qid(person.disability_onset), 1952 * 4 + 2)
        last = min(_qid(month), 1955 * 4 + 3)
        for quarter in range(first, last + 1):
            rows, _ = _world(person, upper, quarter, exit_month, False)
            continuous = tuple(range(1951 * 4, quarter))
            assigned = {
                qc
                for row in rows.values()
                for qc in _assign_qcs(*row, window=continuous)
            }
            if (
                len(assigned) >= 20
                and len(continuous) >= 6
                and set(continuous) <= assigned
            ):
                _refuse(
                    InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
                    "Onset and QCs allow the RS00301.480 alternate test; "
                    "application conditions are unmodeled",
                )


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
    options = [_assignment_candidates(*rows[y]) for y in years]
    if prod(map(len, options)) > 4096:
        _refuse(
            InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
            "More than4096 boundary assignments",
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


def _witness(person, credits, at, exit_month, kind, *, onset=True):
    end = _qid(at)
    best = None
    # Source conflict us:oasdi-insured-prior-disability-favorable-disregard
    # CFR404.130(f): consider all prior periods or disregard all, favorably.
    for use_periods in (
        (True, False) if person.prior_disability_periods else (True,)
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
                if young or subsequent:
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
                    fully if kind is InsuredTest.DISABILITY else True
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
    return best[1]


def _unknown_prior_history_is_empty(person, credits, month, exit_month):
    """Prove infeasibility of the earliest nonempty prior period only.

    The earliest period must begin insured without any earlier exclusions
    (404.320(b)(2), 404.321(a)), fit before onset and FRA, and leave five
    months before its ending month (404.320(b)(4)). Upper-credit witnesses
    deliberately overapproximate possibility. A surviving quarter proves
    no actual history; it only prevents an invalid-input conclusion.
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
    last_month = latest_end.year * 12 + latest_end.month - 1
    for quarter in range(first, _qid(latest_end) + 1):
        start = max(person.birth_date, _qdate(quarter))
        if start >= _fra_date(person):
            break
        # Permissive about partial first/last months: only use this bound
        # to prove impossibility, never to establish a period or its dates.
        if start.year * 12 + start.month - 1 + 5 > last_month:
            break
        if _witness(
            plain,
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


def _last_insured(person, credits, month, exit_month):
    last = None
    if sum(len(fixed) + flexible for fixed, flexible in credits.values()) < 6:
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
    start = max(min(credited_years) * 4, _qid(person.birth_date))
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


def _decision_witness(person, credits, month, exit_month, kind):
    best, qualifying = None, None
    for event in _events(person, month, kind):
        witness = _witness(person, credits, event, exit_month, kind)
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
        and month < _fra_date(person).replace(day=1)
        and (
            person.death_date is None
            or person.death_date.replace(day=1) > month
        )
    )


def _with_current_period(
    person, credits, month, exit_month, *, earliest_end=False
):
    if not person.current_disability_period_established:
        return person, None
    fra = _fra_date(person)
    horizon = min(month, fra.replace(day=1))
    witness, quarter = _decision_witness(
        person, credits, horizon, exit_month, InsuredTest.DISABILITY
    )
    if not witness[0]:
        raise InvalidFamilyInput(
            "Established current period has no insured disabled quarter"
        )
    # 416(i)(2)(C), 404.321(a): onset day if insured then, otherwise
    # first day of the first later insured quarter. Application/duration
    # are administrative facts declared by the caller, never inferred.
    start = (
        person.disability_onset
        if _qid(quarter) == _qid(person.disability_onset)
        else quarter
    )
    # 416(i)(2)(B)/(D), 404.321: the query is an observation cut-off,
    # never an ending fact. Without an end declaration, compare completion
    # in this quarter with continuation to the statutory FRA boundary.
    end = fra.replace(day=1) - timedelta(days=1)
    if start >= fra or start > end:
        raise InvalidFamilyInput("Established period begins at or after FRA")
    if person.current_disability_period_end is not None:
        end = min(end, person.current_disability_period_end)
    elif earliest_end:
        end = min(
            end,
            date(
                month.year,
                month.month,
                calendar.monthrange(month.year, month.month)[1],
            ),
        )
    if person.death_date is not None:
        end = min(end, person.death_date)
    if end < start:
        raise InvalidFamilyInput("Current period ends before insured start")
    period = DisabilityPeriod(start, end)
    return (
        replace(
            person,
            prior_disability_periods=person.prior_disability_periods
            + (period,),
            prior_disability_periods_provenance=EarningsProvenance.OBSERVED,
            prior_disability_periods_convention_id=None,
        ),
        start,
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

    Medical onset means continuously disabled through this query and never
    establishes a period. Declare establishment, prior-period provenance,
    and section214(c) applicability; UNKNOWN never silently means none.
    Declare an administrative ending with its provenance when known. An
    ongoing period is bounded by possible endings, with a named refusal if
    the ending changes a requested status, and is always capped before FRA.
    Each disability window ends at its tested quarter, from onset through
    query, and the first insured quarter supplies the witness (404.131).
    Impossible establishment is an input error even with UNKNOWN history.
    No entry date, imputation, or pre-entry zero convention exists.
    """
    _validate_history(
        person, years, month, coverage_end_month, totalization_credits
    )
    lower = {y: _credits(y, row, False) for y, row in sorted(years.items())}
    upper = {y: _credits(y, row, True) for y, row in sorted(years.items())}
    unknown = tuple(
        y
        for y, row in sorted(years.items())
        if row.provenance is EarningsProvenance.UNKNOWN
    )
    prior_unknown = (
        person.prior_disability_periods_provenance
        is EarningsProvenance.UNKNOWN
    )
    current_unknown = (
        person.disability_onset is not None
        and person.disability_onset < _fra_date(person).replace(day=1)
        and person.current_disability_period_provenance
        is EarningsProvenance.UNKNOWN
    )
    end_unknown = _period_end_unknown(person, month) and not prior_unknown
    max_rows, _ = _world(
        person,
        upper,
        _qid(month),
        coverage_end_month,
        False,
        include_zero=True,
    )
    maximum_qcs = sum(len(_assign_qcs(*row)) for row in max_rows.values())
    if person.current_disability_period_established and maximum_qcs < 6:
        raise InvalidFamilyInput(
            "Established current period requires at least six lifetime QCs"
        )
    if (
        person.current_disability_period_established
        and prior_unknown
        and _unknown_prior_history_is_empty(
            person, upper, month, coverage_end_month
        )
    ):
        # Empty is the only possible prior history. Validate establishment
        # in that concrete world before retaining any coverage refusal.
        # Keep the caller's UNKNOWN provenance and conservative output
        # envelope if it is valid; no observed fact is invented here.
        plain = replace(
            person,
            prior_disability_periods_provenance=EarningsProvenance.OBSERVED,
            prior_disability_periods_convention_id=None,
        )
        _with_current_period(plain, upper, month, coverage_end_month)
    if person.current_disability_period_established and not prior_unknown:
        # Even the most favorable earnings completion must supply a legal
        # insured start before FRA. Input errors precede coverage refusals.
        _with_current_period(person, upper, month, coverage_end_month)
    _coverage_checks(person, years, month, totalization_credits)
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
            onset_witness = _witness(
                person,
                lower,
                person.disability_onset,
                coverage_end_month,
                InsuredTest.DISABILITY,
            )
            if onset_witness[0]:
                lo_start = hi_start = person.disability_onset
            else:
                uncertain_current_start = True
    else:
        if person.current_disability_period_established:
            initial_lo, _ = _decision_witness(
                person,
                lower,
                month,
                coverage_end_month,
                InsuredTest.DISABILITY,
            )
            if not initial_lo[0] and unknown:
                initial_hi, _ = _decision_witness(
                    person,
                    upper,
                    month,
                    coverage_end_month,
                    InsuredTest.DISABILITY,
                )
                if initial_hi[0]:
                    _refuse(
                        InsuredUnsupportedReason.UNKNOWN_EARNINGS,
                        "Unknown facts decide the established current insured start",
                    )
        lo_person, lo_start = _with_current_period(
            person, lower, month, coverage_end_month
        )
        hi_person, hi_start = (
            _with_current_period(
                person,
                upper,
                month,
                coverage_end_month,
                earliest_end=end_unknown,
            )
            if unknown or end_unknown
            else (lo_person, lo_start)
        )
    if lo_start != hi_start:
        _refuse(
            InsuredUnsupportedReason.UNKNOWN_EARNINGS,
            "Unknown earnings decide established current period start",
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
    decisions = {}
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
        decision_lo_person = (
            person if kind is InsuredTest.DISABILITY else lo_person
        )
        decision_hi_person = (
            person if kind is InsuredTest.DISABILITY else hi_person
        )
        lo, lo_quarter = _decision_witness(
            decision_lo_person, lower, month, coverage_end_month, kind
        )
        hi, hi_quarter = (
            _decision_witness(
                decision_hi_person, upper, month, coverage_end_month, kind
            )
            if unknown or end_unknown
            else (lo, lo_quarter)
        )
        if end_unknown:
            same_earnings_end, _ = _decision_witness(
                (
                    person
                    if kind is InsuredTest.DISABILITY
                    else _with_current_period(
                        person,
                        lower,
                        month,
                        coverage_end_month,
                        earliest_end=True,
                    )[0]
                ),
                lower,
                month,
                coverage_end_month,
                kind,
            )
            if lo[0] != same_earnings_end[0]:
                _refuse(
                    InsuredUnsupportedReason.CURRENT_PERIOD_END,
                    f"Unobserved statutory period end decides {kind.value}",
                )
        _observable_coverage_paths(
            decision_lo_person,
            years,
            month,
            coverage_end_month,
            kind,
            lo,
            upper,
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
        count_lo, count_hi = (
            (0, maximum_qcs)
            if broad
            else (min(lo[1], hi[1]), max(lo[1], hi[1]))
        )
        full_lo, full_hi = (
            (0, maximum_qcs)
            if broad
            else (min(lo[7], hi[7]), max(lo[7], hi[7]))
        )
        decisions[kind] = _computed(
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
    dli = None
    if test in (InsuredTest.ALL, InsuredTest.DISABILITY):
        lo_date, lo_censored = _last_insured(
            lo_person, lower, month, coverage_end_month
        )
        hi_date, hi_censored = (
            _last_insured(hi_person, upper, month, coverage_end_month)
            if unknown or end_unknown
            else (lo_date, lo_censored)
        )
        if (prior_unknown or current_unknown) and maximum_qcs >= 6:
            hi_date = _dli_cap(person, month, coverage_end_month)
            hi_censored = (
                coverage_end_month is None or coverage_end_month > month
            ) and _qid(hi_date) == _qid(month)
        if applicability is None:
            # A guaranteed historical fully insured witness also needs
            # resolved section214(c) facts. Keep the QC-only upper date;
            # false current status cannot prove a positive DLI lower date.
            lo_date = None
        dli = _computed(DLIRange, lo_date, hi_date, lo_censored or hi_censored)
    lo_rows, _ = _world(
        lo_person,
        lower,
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
                        else len(assigned[y])
                    ),
                    (
                        len(_assign_qcs(*max_rows[y]))
                        if prior_unknown or current_unknown
                        else len(_assign_qcs(*hi_rows[y]))
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
