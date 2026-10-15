"""R2 statutory conformance differential on invented full histories only.

The independent reference computes events from the complete history; the
production helper receives one year and its own carried state at a time.
Equality is exact: categories, eligible/protected months, LMETY, and pending
eligibility contain no rounded numbers and permit no numerical tolerance.
No population, behavioral, or forecast claim is admitted.
"""

from collections import defaultdict

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b.ret_grace import (
    BenefitType as B,
)
from populace_dynamics.track_b.ret_grace import (
    DisabilityGraceReading as D,
)
from populace_dynamics.track_b.ret_grace import (
    GraceKind as K,
)
from populace_dynamics.track_b.ret_grace import (
    GraceMonth,
    GraceYearState,
    TerminationEvent,
    TerminationReason,
    grace_year,
)
from tests.track_b_ret_grace_reference import (
    HistoryYear,
    reference_grace_history,
)
from tests.track_b_ret_ledger_support import source_text


def month(kind, nonservice=True):
    return GraceMonth({kind}, {kind}, nonservice)


EMPTY = GraceMonth()
PROFILES = (
    ((), ()),
    *(((kind,), (kind,)) for kind in B),
    ((B.RIB, B.DIB), (B.RIB,)),
    ((B.RIB, B.DIB), (B.DIB,)),
    ((B.CHILD, B.CDB), (B.CHILD,)),
    ((B.WIDOW, B.DWB), (B.WIDOW,)),
    ((B.RIB, B.SPOUSE), (B.RIB, B.SPOUSE)),
    ((B.RIB, B.WIDOW), (B.RIB, B.WIDOW)),
)


@st.composite
def full_histories(draw):
    """Consecutive 2-56-year histories, with independently drawn spans.

    One FRA date is used throughout a history. Benefit-law entitlement,
    termination causes, and elections are supplied facts, as in production;
    this generator does not infer disability, marriage, or insured status.
    """
    first = draw(st.integers(1975, 2029))
    count = draw(st.integers(2, 2031 - first))
    length = count * 12
    spans = draw(
        st.lists(
            st.tuples(
                st.sampled_from(PROFILES),
                st.integers(1, min(length, 48)),
                st.booleans(),
            ),
            min_size=1,
            max_size=36,
        )
    )
    months = []
    for (entitled, received), duration, nonservice in spans:
        months.extend([GraceMonth(entitled, received, nonservice)] * duration)
    months = (months + [EMPTY] * length)[:length]
    fra_index = draw(st.one_of(st.none(), st.integers(0, length - 1)))
    candidates = [
        (index, kind)
        for index, value in enumerate(months)
        for kind in sorted(value.entitled_types, key=lambda value: value.value)
        if index + 1 == length or kind not in months[index + 1].entitled_types
    ]
    events = defaultdict(list)
    selected = (
        draw(
            st.lists(
                st.sampled_from(candidates),
                max_size=min(10, len(candidates)),
                unique=True,
            )
        )
        if candidates
        else ()
    )
    for index, kind in selected:
        reason = draw(st.sampled_from(list(TerminationReason)))
        # The annual API cannot inspect next January. Supply its conversion
        # exclusion explicitly rather than hiding known future entitlement.
        if (
            index % 12 == 11
            and index + 1 < length
            and months[index + 1].entitled_types
            and reason is TerminationReason.NORMAL
        ):
            reason = TerminationReason.CONTIGUOUS_CONVERSION
        young = (
            draw(st.booleans())
            if kind in {B.SPOUSE, B.DIVORCED_SPOUSE}
            else False
        )
        events[index // 12].append(
            TerminationEvent(index % 12 + 1, kind, young, reason)
        )
    return tuple(
        HistoryYear(
            first + index,
            tuple(months[index * 12 : (index + 1) * 12]),
            tuple(events[index]),
            (
                None
                if fra_index is None or fra_index >= (index + 1) * 12
                else max(1, fra_index - index * 12 + 1)
            ),
        )
        for index in range(count)
    )


PRE_1978_HISTORY = tuple(
    HistoryYear(
        year,
        tuple(month(B.MOTHER_FATHER, year in {1977, 2000}) for _ in range(12)),
    )
    for year in range(1975, 2001)
)
DIB_BRIDGE_HISTORY = (
    HistoryYear(2024, (month(B.SPOUSE),) * 12),
    HistoryYear(2025, (EMPTY,) + (month(B.DIB),) * 11),
    HistoryYear(2026, (month(B.WIDOW),) * 12),
)
FULL_DATE_RANGE_HISTORY = tuple(
    HistoryYear(
        year,
        (month(tuple(B)[(year - 1975) % len(B)]),) * 11 + (EMPTY,),
    )
    for year in range(1975, 2031)
)


@settings(max_examples=600, deadline=None, database=None, derandomize=True)
@given(full_histories(), st.sampled_from(list(D)))
@example(PRE_1978_HISTORY, D.CFR_ENTITLEMENT_EXCLUSION)
@example(DIB_BRIDGE_HISTORY, D.CFR_ENTITLEMENT_EXCLUSION)
@example(FULL_DATE_RANGE_HISTORY, D.CFR_ENTITLEMENT_EXCLUSION)
def test_property_carried_grace_equals_independent_full_history(
    history, reading
):
    reference = reference_grace_history(history, reading)
    state = GraceYearState()
    for year, expected in zip(history, reference, strict=True):
        result = grace_year(
            year.year,
            state,
            year.months,
            termination_events=year.terminations,
            fra_month=year.fra_month,
            disability_reading=reading,
        )
        actual = (
            result.kinds,
            result.met_eligible_months,
            result.protected_months,
            result.next_state.last_met_year,
            result.next_state.pending_after_break,
        )
        wanted = (
            expected.kinds,
            expected.eligible,
            expected.protected,
            expected.last_met_year,
            expected.pending_after_break,
        )
        assert result.applies == bool(expected.kinds), year.year
        assert actual == wanted, (year.year, actual, wanted)
        state = result.next_state


@pytest.mark.parametrize(
    "source, quote",
    [
        (
            "ssa_act_203",
            "the first month after December 1977 that is both",
        ),
        (
            "ssa_act_203",
            "entitled to benefits under subsection (a), (b), (c), (d), "
            "(e), (f), (g), or (h) of section 202 (without having been "
            "entitled for the preceding month to a benefit under any "
            "other of such subsections)",
        ),
        (
            "ecfr_20cfr404_subpart_e",
            "The new grace year would then be the taxable year in which "
            "the first non-service month occurs after the break in "
            "entitlement.",
        ),
        (
            "ecfr_20cfr404_subpart_e",
            "This provision does not apply if the termination is because "
            "of death or if the beneficiary is entitled to a Social "
            "Security benefit for the month following the month in "
            "which the entitlement ended.",
        ),
        (
            "poms_rs_02501_030",
            "A grace year does not apply to a disabled beneficiary in "
            "any year if entitled solely to DIB, disabled widow(er)'s "
            "(DWB), or childhood disability benefits (CDB).",
        ),
    ],
)
def test_reference_rules_are_verbatim_in_manifest_captures(source, quote):
    assert quote in source_text(source)


def test_reference_reviewer_histories_have_expected_grace_years():
    old = reference_grace_history(PRE_1978_HISTORY)
    assert all(not year.kinds for year in old[:-1])
    assert old[-1].kinds == {K.INITIAL}
    assert old[-1].last_met_year == 2000
    bridge = reference_grace_history(DIB_BRIDGE_HISTORY)
    assert bridge[-1].kinds == {K.AFTER_BREAK}
    assert bridge[-1].protected == set(range(1, 13))
    assert bridge[-1].last_met_year == 2026


def test_reference_next_month_dib_blocks_termination_but_is_section_202_gap():
    history = (
        HistoryYear(2024, (month(B.CHILD),) * 12),
        HistoryYear(
            2025,
            (month(B.CHILD),) + (month(B.DIB),) * 11,
            (TerminationEvent(1, B.CHILD),),
        ),
        HistoryYear(2026, (month(B.WIDOW),) * 12),
    )
    decisions = reference_grace_history(history)
    assert not decisions[1].kinds
    assert decisions[2].kinds == {K.AFTER_BREAK}


def test_reference_termination_status_does_not_require_an_eligible_nsm():
    # Minimized differential counterexample: the initial oracle confused
    # "no eligible NSM" with .030B.4's "entitled solely" to disability.
    # The ordinary child's entitlement keeps this outside the latter rule.
    simultaneous = GraceMonth({B.CHILD, B.CDB}, {B.CHILD}, False)
    history = (
        HistoryYear(
            1975,
            (simultaneous,) + (EMPTY,) * 11,
            (TerminationEvent(1, B.CDB),),
        ),
        HistoryYear(1976, (EMPTY,) * 12),
    )
    result = reference_grace_history(history)[0]
    assert result.kinds == {K.TERMINATION}
    assert not result.eligible
    assert not result.protected
    assert result.last_met_year is None
