"""Track B insured status, version track-b-insured-v1.

Verification class: statutory conformance. Admitted scope: declared invented
histories and captured statutory examples only; no population, behavioral,
or forecast claim. Act 213, 214, 216(i), 223(c); 20 CFR 404 subpart B;
POMS RS 00301. Every year is declared, including zero and unknown years.
The query month is a hypothetical entitlement/onset month, not a finding of
medical disability or administrative entitlement. Annual QC assignment is
favorable and retrospective; callers must supply only information available
at their decision time. Each test returns its own assignment witness.

All public declarations use the shared exact-type schema. Ordered sequences
retain multiplicity; conditions are membership collections. Computed values,
refusals and evaluator rows use the common Track B provenance seal. Public
calls validate once before coverage decisions. Persist inputs and recompute.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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

    def __post_init__(self):
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
        periods = sorted(self.prior_disability_periods, key=lambda p: p.start)
        for i, period in enumerate(periods):
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
        if (
            self.alien_worker
            and self.ssn_assignment_date is None
            and not self.ssn_never_assigned
        ):
            raise InvalidFamilyInput(
                "Alien worker requires assignment date or explicit never-assigned fact"
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
    if (
        onset
        and person.disability_onset is not None
        and not person.statutory_blindness
    ):
        end = min(end, person.disability_onset.year)
    elapsed = sum(
        not any(a.year <= year <= b.year for a, b in periods)
        for year in range(start, end)
    )
    return min(40, max(6, elapsed))


@_validated_entry
def fully_insured_requirement(person: Person, month: date) -> int:
    """One QC per elapsed year, bounded by six and forty (214(a))."""
    _month(month, "month")
    if month < person.birth_date.replace(day=1):
        raise InvalidFamilyInput("Query precedes birth")
    if (
        person.disability_onset is not None
        and person.disability_onset.replace(day=1) > month
    ):
        raise InvalidFamilyInput("Disability onset follows query month")
    if any(p.end >= month for p in person.prior_disability_periods):
        raise InvalidFamilyInput("Prior disability period follows query month")
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
    if person.alien_worker and (
        person.ssn_never_assigned
        or person.ssn_assignment_date >= date(2004, 1, 1)
    ):
        _refuse(
            InsuredUnsupportedReason.ALIEN_WORKER,
            "SSPA211 additional alien-worker facts",
        )
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
    # CFR404.130(f): consider all prior periods or disregard all, favorably.
    for use_periods in (
        (True, False) if person.prior_disability_periods else (True,)
    ):
        prior_before = at if kind is InsuredTest.CURRENTLY else None
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


def _fra_quarter(person):
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
    return _qid(date(year, month + 1, day) - timedelta(days=1))


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
    """Decide a declared person-month; uncertain status is a retained refusal.

    B6a calls with test=FULLY. OP8(d)/OP12 use the same declaration and
    optional exit month. No entry date, imputation, or zero default exists.
    DLI is through this query, explicitly censored, unless exit freezes work.
    """
    _validate_history(
        person, years, month, coverage_end_month, totalization_credits
    )
    _coverage_checks(person, years, month, totalization_credits)
    lower = {y: _credits(y, row, False) for y, row in sorted(years.items())}
    upper = {y: _credits(y, row, True) for y, row in sorted(years.items())}
    unknown = tuple(
        y
        for y, row in sorted(years.items())
        if row.provenance is EarningsProvenance.UNKNOWN
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
        at = month
        if (
            kind is InsuredTest.DISABILITY
            and person.disability_onset is not None
            and not person.statutory_blindness
        ):
            at = person.disability_onset
        events = [at]
        if kind is InsuredTest.CURRENTLY:
            events = [
                event
                for event in (
                    person.death_date,
                    person.rib_entitlement_month,
                    person.dib_entitlement_month,
                )
                if event is not None and event.replace(day=1) <= month
            ] or [month]
        lo = max(
            (
                _witness(person, lower, event, coverage_end_month, kind)
                for event in events
            ),
            key=lambda witness: (witness[0], witness[1]),
        )
        hi = (
            max(
                (
                    _witness(person, upper, event, coverage_end_month, kind)
                    for event in events
                ),
                key=lambda witness: (witness[0], witness[1]),
            )
            if unknown
            else lo
        )
        if lo[0] != hi[0]:
            _refuse(
                InsuredUnsupportedReason.UNKNOWN_EARNINGS,
                f"{kind.value} differs across unknown years {unknown}",
            )
        decisions[kind] = _computed(
            StatusDecision,
            lo[0],
            lo[1],
            hi[1],
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
            lo[7],
            hi[7],
        )
    dli = None
    if test in (InsuredTest.ALL, InsuredTest.DISABILITY):
        lo_date, lo_censored = _last_insured(
            person, lower, month, coverage_end_month
        )
        hi_date, hi_censored = (
            _last_insured(person, upper, month, coverage_end_month)
            if unknown
            else (lo_date, lo_censored)
        )
        dli = _computed(DLIRange, lo_date, hi_date, lo_censored or hi_censored)
    lo_rows, _ = _world(
        person, lower, _qid(month), coverage_end_month, True, include_zero=True
    )
    hi_rows, _ = _world(
        person, upper, _qid(month), coverage_end_month, True, include_zero=True
    )
    assigned = {y: _assign_qcs(*row) for y, row in lo_rows.items()}
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
                y: (len(assigned[y]), len(_assign_qcs(*hi_rows[y])))
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
        bool(unknown),
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
