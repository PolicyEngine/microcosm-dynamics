"""Independent R2 grace reference; statutory conformance on invented histories.

No population, behavioral, or forecast claim is admitted. This test-only model
reads the complete calendar-month history rather than carrying production's
transition state. Authority is captured Act 203(f)(1)(E)-(F), 20 CFR
404.435(b), and POMS RS 02501.030B-D. It imports only the public input enums
and dataclasses; it never calls production's grace algorithm or helpers.

The construction follows the sources: find the first post-1977 NSM, identify
termination years, then find different-section-202-type entries after gaps
and their first subsequent NSMs. Each opportunity is an independent search
over the full history, so there is no mutable previous-type/gap/pending
state machine. CDB and DWB are section 202 child and widow(er) types; DIB is
section 223 and is absent from the section-202 timeline. Disability still
separately excludes NSMs. The explicit POMS RIB/DIB election reading is
supported alongside the conservative CFR default, preserving d1418.
"""

from __future__ import annotations

from dataclasses import dataclass

from populace_dynamics.track_b.ret_grace import (
    BenefitType,
    DisabilityGraceReading,
    GraceKind,
    GraceMonth,
    TerminationEvent,
    TerminationReason,
)


@dataclass(frozen=True)
class HistoryYear:
    """One calendar year of explicitly supplied entitlement and work facts."""

    year: int
    months: tuple[GraceMonth, ...]
    terminations: tuple[TerminationEvent, ...] = ()
    fra_month: int | None = None


@dataclass(frozen=True)
class ReferenceDecision:
    """Observable annual decisions, independently derived from the history."""

    kinds: frozenset[GraceKind]
    eligible: frozenset[int]
    protected: frozenset[int]
    last_met_year: int | None
    pending_after_break: bool


# Statutory subsections, not production benefit labels. The public API groups
# sex-specific types, so b/c and e/f are correspondingly grouped here.
SECTION_202 = {
    BenefitType.RIB: "a",
    BenefitType.SPOUSE: "b/c",
    BenefitType.DIVORCED_SPOUSE: "b/c",
    BenefitType.CHILD: "d",
    BenefitType.CDB: "d",
    BenefitType.WIDOW: "e/f",
    BenefitType.DWB: "e/f",
    BenefitType.MOTHER_FATHER: "g",
}
DISABLED = {BenefitType.DIB, BenefitType.DWB, BenefitType.CDB}


def _eligible(
    month: GraceMonth,
    before_fra: bool,
    reading: DisabilityGraceReading,
) -> bool:
    """404.435(b)(3); the named .030B.4 RIB-election exception is explicit."""
    if not before_fra or not (month.received_types - DISABLED):
        return False
    disability = month.entitled_types & DISABLED
    if not disability:
        return True
    return (
        reading is DisabilityGraceReading.POMS_RIB_ELECTION
        and disability == {BenefitType.DIB}
        and BenefitType.RIB in month.received_types
    )


def reference_grace_history(
    history: tuple[HistoryYear, ...],
    reading: DisabilityGraceReading = (
        DisabilityGraceReading.POMS_RIB_ELECTION
    ),
) -> tuple[ReferenceDecision, ...]:
    """Find every year's grace decisions directly from the entire timeline.

    Histories begin with no prior entitlement and contain consecutive complete
    years. December termination causes explicitly account for next January,
    as required by the production annual input contract. NSM eligibility is
    independent of whether a year is eventually designated a grace year.
    """
    assert history
    assert all(len(year.months) == 12 for year in history)
    assert all(
        later.year == earlier.year + 1
        for earlier, later in zip(history, history[1:], strict=False)
    )
    months = tuple(month for year in history for month in year.months)
    eligible = {
        year_index * 12 + month_index
        for year_index, year in enumerate(history)
        for month_index, month in enumerate(year.months)
        if _eligible(
            month,
            year.fra_month is None or month_index + 1 < year.fra_month,
            reading,
        )
    }
    nsms = sorted(index for index in eligible if months[index].nonservice)

    # Act 203(f)(1)(E): first qualifying month AFTER December 1977.
    post_1977_nsms = [
        index for index in nsms if history[index // 12].year >= 1978
    ]
    initial = post_1977_nsms[0] if post_1977_nsms else None
    categories = [set() for _ in history]
    if initial is not None:
        categories[initial // 12].add(GraceKind.INITIAL)

    # Act 203(f)(1)(F), CFR .435(b)(4), POMS .030B.3: the last entitled
    # month's year; any Title-II entitlement next month bars this grace.
    for year_index, year in enumerate(history):
        if not any(month.entitled_types - DISABLED for month in year.months):
            continue  # .030B.4: a disability-only year has no grace.
        for event in year.terminations:
            auxiliary = event.benefit_type in {
                BenefitType.CHILD,
                BenefitType.CDB,
                BenefitType.MOTHER_FATHER,
            } or (
                event.young_spouse
                and event.benefit_type
                in {BenefitType.SPOUSE, BenefitType.DIVORCED_SPOUSE}
            )
            next_index = year_index * 12 + event.last_entitled_month
            next_entitlement = next_index < len(months) and bool(
                months[next_index].entitled_types
            )
            if (
                auxiliary
                and event.reason is TerminationReason.NORMAL
                and not next_entitlement
            ):
                categories[year_index].add(GraceKind.TERMINATION)

    # CFR .435(b)(2), POMS .030B.2: compare consecutive section-202
    # entitled months in the full history. A missing month proves a break;
    # DIB neither appears here nor changes the prior section-202 type.
    section_202_months = [
        (
            index,
            frozenset(
                SECTION_202[kind]
                for kind in month.entitled_types
                if kind in SECTION_202
            ),
        )
        for index, month in enumerate(months)
        if any(kind in SECTION_202 for kind in month.entitled_types)
    ]
    entries = [
        current_index
        for (previous_index, previous_types), (
            current_index,
            current_types,
        ) in zip(section_202_months, section_202_months[1:], strict=False)
        if current_index > previous_index + 1
        and current_types - previous_types
    ]
    completions = {
        entry: next(
            (index for index in post_1977_nsms if index >= entry), None
        )
        for entry in entries
    }
    for completion in completions.values():
        if completion is not None and completion != initial:
            categories[completion // 12].add(GraceKind.AFTER_BREAK)

    result = []
    for year_index in range(len(history)):
        end = (year_index + 1) * 12
        kinds = frozenset(categories[year_index])
        met_years = [
            history[index].year
            for index in range(year_index + 1)
            if categories[index] & {GraceKind.INITIAL, GraceKind.AFTER_BREAK}
        ]
        result.append(
            ReferenceDecision(
                kinds=kinds,
                eligible=frozenset(
                    index % 12 + 1
                    for index in eligible
                    if index // 12 == year_index
                ),
                protected=frozenset(
                    index % 12 + 1
                    for index in nsms
                    if index // 12 == year_index and kinds
                ),
                last_met_year=max(met_years, default=None),
                pending_after_break=any(
                    entry < end and (completion is None or completion >= end)
                    for entry, completion in completions.items()
                ),
            )
        )
    return tuple(result)
