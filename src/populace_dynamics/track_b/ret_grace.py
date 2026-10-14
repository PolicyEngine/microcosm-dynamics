"""R2: a pure, explicit-state monthly earnings test grace-year helper.

Verification class: statutory conformance. This module admits grace-year
mechanics for invented cases and POMS/CFR worked examples only; it admits
no population, behavioral, or forecast claim. Authority: Act 203(f)(1),
20 CFR 404.435, and POMS RS 02501.030B-D, RS 02501.021B.5.a.

The caller supplies entitlement separately from benefits actually received.
In particular, continuing technical RIB entitlement while DIB is elected
preserves the entitlement history but cannot create a non-service month.
``nonservice`` supplies the wage/substantial-services condition; this helper
does not calculate earnings or determine disability cessation. Call once
per consecutive calendar year and carry ``next_state`` into the next call.
Termination events use the last entitled month, not the termination month:
a January termination therefore belongs to the preceding year's call.
Ordinary CHILD and CDB both terminate child's benefits under Act 202(d).
In a mixed year, CDB termination can protect earlier non-disability NSMs;
disability months remain ineligible, and a disability-only year has no
grace year (20 CFR 404.435(b)(3)-(4); RS 02501.030B.3-4).
For after-break grace, CDB/CHILD share Act 202(d)'s legal benefit type,
and DWB/WIDOW share Act 202(e)/(f)'s type (RS 02501.030B.2). This
comparison preserves the separate disability-month NSM exclusion.
Externally supplied month sets validate every raw value before deduplication.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput


class BenefitType(Enum):
    """Benefits needed to distinguish RET-covered and disabled months."""

    RIB = "rib"
    SPOUSE = "spouse"
    DIVORCED_SPOUSE = "divorced_spouse"
    CHILD = "child"
    WIDOW = "widow"
    MOTHER_FATHER = "mother_father"
    DIB = "dib"
    DWB = "dwb"
    CDB = "cdb"


DISABILITY_TYPES = frozenset(
    {BenefitType.DIB, BenefitType.DWB, BenefitType.CDB}
)


class GraceKind(Enum):
    """The three grace years in RS 02501.030B."""

    INITIAL = "initial"
    AFTER_BREAK = "after_break"
    TERMINATION = "termination"


class DisabilityGraceReading(Enum):
    """Explicit money-changing CFR/POMS reading for concurrent disability.

    404.435(b)(3) excludes any month entitled to disability benefits; POMS
    RS 02501.030B.4/.021B.5.a explicitly excepts simultaneous RIB/DIB when
    RIB is elected. The default preserves the CFR's conservative exclusion.
    The POMS alternative is necessary to reproduce its election example.
    """

    CFR_ENTITLEMENT_EXCLUSION = "cfr_entitlement_exclusion"
    POMS_RIB_ELECTION = "poms_rib_election"


class TerminationReason(Enum):
    """Explicit facts controlling RS 02501.030B.3.b exclusions."""

    NORMAL = "normal"
    DEATH = "death"
    CONTIGUOUS_CONVERSION = "contiguous_conversion"
    SPOUSE_AGE_CONVERSION = "spouse_age_conversion"
    CHILD_IN_CARE_SUSPENSION = "child_in_care_suspension"


def _types(values: frozenset[BenefitType]) -> frozenset[BenefitType]:
    try:
        result = frozenset(values)
    except TypeError as error:
        raise InvalidFamilyInput("Benefit types must be iterable") from error
    if any(not isinstance(value, BenefitType) for value in result):
        raise InvalidFamilyInput("Use explicit BenefitType values")
    return result


def _year(value: int, label: str) -> None:
    if type(value) is not int or value < 1:
        raise InvalidFamilyInput(f"{label} must be a positive integer")


def _boolean(value: bool, label: str) -> None:
    if type(value) is not bool:
        raise InvalidFamilyInput(f"{label} must be a boolean")


@dataclass(frozen=True)
class GraceMonth:
    """One month's entitlement, elected payments, and work-condition flag.

    ``received_types`` identifies benefit types elected for the month,
    before an earnings-test deduction; a withheld or voluntarily waived RIB
    remains received RIB for this purpose (RS 02501.030C). ``nonservice``
    means wages do not exceed the monthly limit and no substantial
    self-employment services were performed. The
    helper still checks entitlement, disability types, and pre-FRA status.
    """

    entitled_types: frozenset[BenefitType] = field(default_factory=frozenset)
    received_types: frozenset[BenefitType] = field(default_factory=frozenset)
    nonservice: bool = False

    def __post_init__(self):
        entitled = _types(self.entitled_types)
        received = _types(self.received_types)
        _boolean(self.nonservice, "Non-service work-condition flag")
        if not received <= entitled:
            raise InvalidFamilyInput(
                "Received benefit types must be entitled benefit types"
            )
        object.__setattr__(self, "entitled_types", entitled)
        object.__setattr__(self, "received_types", received)


@dataclass(frozen=True)
class GraceYearState:
    """The caller's carried LMETY and complete transition facts.

    ``previous_entitled_types`` is the most recent nonempty entitlement
    set, even after a gap. ``gap_since_entitlement`` records at least one
    entirely unentitled month since that set. ``pending_after_break``
    retains a new entitlement's eligibility until its first NSM, even after
    another gap to that same type or in a later taxable year. No hidden or
    population state is used.
    """

    last_met_year: int | None = None
    previous_entitled_types: frozenset[BenefitType] = field(
        default_factory=frozenset
    )
    had_entitlement: bool = False
    gap_since_entitlement: bool = False
    pending_after_break: bool = False
    last_processed_year: int | None = None

    def __post_init__(self):
        previous = _types(self.previous_entitled_types)
        for name in (
            "had_entitlement",
            "gap_since_entitlement",
            "pending_after_break",
        ):
            _boolean(getattr(self, name), name)
        for name in ("last_met_year", "last_processed_year"):
            if getattr(self, name) is not None:
                _year(getattr(self, name), name)
        if bool(previous) != self.had_entitlement:
            raise InvalidFamilyInput(
                "Entitlement history must include its most recent types"
            )
        if (self.gap_since_entitlement or self.pending_after_break) and not (
            self.had_entitlement
        ):
            raise InvalidFamilyInput("A break requires entitlement history")
        if self.last_met_year is not None and (
            self.last_processed_year is None
            or self.last_met_year > self.last_processed_year
            or not self.had_entitlement
        ):
            raise InvalidFamilyInput(
                "LMETY requires earlier processed entitlement history"
            )
        object.__setattr__(self, "previous_entitled_types", previous)


@dataclass(frozen=True)
class TerminationEvent:
    """A dated entitlement ending and its explicitly supplied cause.

    A young spouse is a spouse entitled under Act 202(b)/(c) before age 62;
    that fact must be supplied since ordinary aged-spouse termination does
    not qualify. Child-in-care failure causes suspension, not termination.
    """

    last_entitled_month: int
    benefit_type: BenefitType
    young_spouse: bool = False
    reason: TerminationReason = TerminationReason.NORMAL

    def __post_init__(self):
        if type(self.last_entitled_month) is not int or not (
            1 <= self.last_entitled_month <= 12
        ):
            raise InvalidFamilyInput(
                "Last entitled month must be 1 through 12"
            )
        if not isinstance(self.benefit_type, BenefitType):
            raise InvalidFamilyInput(
                "Use an explicit termination benefit type"
            )
        if not isinstance(self.reason, TerminationReason):
            raise InvalidFamilyInput("Use an explicit termination reason")
        _boolean(self.young_spouse, "Young spouse flag")
        if self.young_spouse and self.benefit_type not in (
            BenefitType.SPOUSE,
            BenefitType.DIVORCED_SPOUSE,
        ):
            raise InvalidFamilyInput(
                "Young spouse flag requires spouse benefits"
            )


@dataclass(frozen=True)
class GraceYearDecision:
    """Grace categories, actually protected NSMs, and the next carried state."""

    applies: bool
    kinds: frozenset[GraceKind]
    met_eligible_months: frozenset[int]
    protected_months: frozenset[int]
    next_state: GraceYearState

    def __post_init__(self):
        _boolean(self.applies, "Grace applies flag")
        if not isinstance(self.next_state, GraceYearState):
            raise InvalidFamilyInput("A grace decision needs carried state")
        try:
            kinds = frozenset(self.kinds)
            eligible = tuple(self.met_eligible_months)
            protected = tuple(self.protected_months)
        except TypeError as error:
            raise InvalidFamilyInput(
                "Grace decision sets must be iterable"
            ) from error
        if any(not isinstance(kind, GraceKind) for kind in kinds):
            raise InvalidFamilyInput("Use explicit GraceKind values")
        if any(
            type(month) is not int or not 1 <= month <= 12
            for month in (*eligible, *protected)
        ):
            raise InvalidFamilyInput("Protected months must be 1 through 12")
        eligible = frozenset(eligible)
        protected = frozenset(protected)
        if not protected <= eligible:
            raise InvalidFamilyInput("Protected months must be MET eligible")
        if self.applies != bool(kinds) or (protected and not self.applies):
            raise InvalidFamilyInput(
                "Grace decision categories must match its flag"
            )
        object.__setattr__(self, "kinds", kinds)
        object.__setattr__(self, "met_eligible_months", eligible)
        object.__setattr__(self, "protected_months", protected)


def _legal_types(types: frozenset[BenefitType]) -> frozenset[BenefitType]:
    # RS 02501.030B.2 compares Act benefit types, independently of the
    # disability-month exclusion in 404.435(b)(3). Divorced spouse is
    # 202(b)/(c); ordinary/disabled child is 202(d); widow(er) is 202(e)/(f).
    legal_type = {
        BenefitType.DIVORCED_SPOUSE: BenefitType.SPOUSE,
        BenefitType.CDB: BenefitType.CHILD,
        BenefitType.DWB: BenefitType.WIDOW,
    }
    return frozenset(
        legal_type.get(benefit_type, benefit_type) for benefit_type in types
    )


def grace_year(
    year: int,
    state: GraceYearState,
    months: Sequence[GraceMonth],
    *,
    fra_month: int | None = None,
    termination_events: Sequence[TerminationEvent] = (),
    disability_reading: DisabilityGraceReading = (
        DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION
    ),
) -> GraceYearDecision:
    """Apply RS 02501.030B-D for one person's calendar entitlement year.

    ``fra_month=None`` means FRA has not been attained this year; use 1
    when FRA was attained in an earlier year. Survivors supply the RIB FRA
    (RS 02501.021B.3). The state must follow consecutive yearly calls so an
    omitted year cannot silently create or erase a break in entitlement.
    """
    _year(year, "Year")
    if not isinstance(state, GraceYearState):
        raise InvalidFamilyInput("Supply explicit GraceYearState")
    if state.last_processed_year is not None and year != (
        state.last_processed_year + 1
    ):
        raise InvalidFamilyInput("Process consecutive years of entitlement")
    try:
        months = tuple(months)
        events = tuple(termination_events)
    except TypeError as error:
        raise InvalidFamilyInput(
            "Supply iterable month and termination inputs"
        ) from error
    if len(months) != 12 or any(not isinstance(m, GraceMonth) for m in months):
        raise InvalidFamilyInput("Supply twelve explicit GraceMonth inputs")
    if fra_month is not None and (
        type(fra_month) is not int or not 1 <= fra_month <= 12
    ):
        raise InvalidFamilyInput("FRA month must be 1 through 12 or None")
    if any(not isinstance(event, TerminationEvent) for event in events):
        raise InvalidFamilyInput("Supply explicit TerminationEvent inputs")
    if not isinstance(disability_reading, DisabilityGraceReading):
        raise InvalidFamilyInput("Supply an explicit DisabilityGraceReading")
    for event in events:
        if (
            event.benefit_type
            not in months[event.last_entitled_month - 1].entitled_types
        ):
            raise InvalidFamilyInput(
                "Termination requires entitlement in its last entitled month"
            )
        if (
            event.reason is TerminationReason.NORMAL
            and event.last_entitled_month < 12
            and event.benefit_type
            in months[event.last_entitled_month].entitled_types
        ):
            raise InvalidFamilyInput(
                "Normal termination requires entitlement to end"
            )

    met_eligible = frozenset(
        index
        for index, month in enumerate(months, 1)
        if month.received_types - DISABILITY_TYPES
        and (fra_month is None or index < fra_month)
        and (
            # Source conflict us:oasdi-ret-grace-simultaneous-rib-dib
            not month.entitled_types & DISABILITY_TYPES
            or (
                disability_reading is DisabilityGraceReading.POMS_RIB_ELECTION
                and BenefitType.RIB in month.received_types
                and not month.entitled_types
                & {BenefitType.DWB, BenefitType.CDB}
            )
        )
    )
    eligible_nsms = frozenset(
        index for index in met_eligible if months[index - 1].nonservice
    )
    kinds: set[GraceKind] = set()
    last_met = state.last_met_year
    previous = state.previous_entitled_types
    had_entitlement = state.had_entitlement
    gap = state.gap_since_entitlement
    pending = state.pending_after_break
    for index, month in enumerate(months, 1):
        if not month.entitled_types:
            if had_entitlement:
                gap = True
            continue
        if gap:
            # RS 02501.030B.2 requires a gap and a different type to create
            # eligibility. Another same-type gap cannot erase it before
            # the taxable year's first eligible NSM.
            pending = pending or bool(
                _legal_types(month.entitled_types - DISABILITY_TYPES)
                - _legal_types(previous)
            )
        previous = month.entitled_types
        had_entitlement = True
        gap = False
        if index in eligible_nsms:
            if last_met is None:
                kinds.add(GraceKind.INITIAL)
                last_met = year
                pending = False
            elif pending:
                kinds.add(GraceKind.AFTER_BREAK)
                last_met = year
                pending = False

    # RS 02501.030B.4 excludes a year entitled solely to disability benefits.
    disability_only_year = not any(
        month.entitled_types - DISABILITY_TYPES for month in months
    )
    for event in events:
        eligible_type = (
            event.benefit_type
            in (
                BenefitType.CHILD,
                # Act 202(d), 203(f)(1)(F); 404.435(b)(4); RS .030B.3.a.
                BenefitType.CDB,
                BenefitType.MOTHER_FATHER,
            )
            or event.young_spouse
        )
        next_month_entitled = event.last_entitled_month < 12 and bool(
            months[event.last_entitled_month].entitled_types
        )
        if (
            eligible_type
            and not disability_only_year
            and event.reason is TerminationReason.NORMAL
            and not next_month_entitled
        ):
            kinds.add(GraceKind.TERMINATION)
    applies = bool(kinds)
    return GraceYearDecision(
        applies=applies,
        kinds=frozenset(kinds),
        met_eligible_months=met_eligible,
        protected_months=eligible_nsms if applies else frozenset(),
        next_state=GraceYearState(
            last_met_year=last_met,
            previous_entitled_types=previous,
            had_entitlement=had_entitlement,
            gap_since_entitlement=gap,
            pending_after_break=pending,
            last_processed_year=year,
        ),
    )
