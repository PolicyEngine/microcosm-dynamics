"""R2 grace-year statutory conformance; invented/source cases, no real data."""

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from populace_dynamics.track_b.ret_grace import (
    DISABILITY_TYPES,
    GraceMonth,
    GraceYearDecision,
    GraceYearState,
    TerminationEvent,
    grace_year,
)
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
    TerminationReason as T,
)
from tests.track_b_ret_ledger_support import source_text


def month(kind=B.RIB, *, nonservice=True, entitled=None):
    return GraceMonth(
        entitled_types=frozenset({kind} if entitled is None else entitled),
        received_types=frozenset({kind}),
        nonservice=nonservice,
    )


EMPTY = GraceMonth()
RIB = month()


def prior(year=2010, kind=B.RIB, *, gap=False):
    return GraceYearState(
        last_met_year=year,
        previous_entitled_types=frozenset({kind}),
        had_entitlement=True,
        gap_since_entitlement=gap,
        last_processed_year=year,
    )


RULE_QUOTES = (
    "A beneficiary's initial grace year is the first TY they have an NSM:",
    "in or after the month of entitlement to a retirement, survivor, or auxiliary benefit,",
    "before the month of FRA.",
    "there is a break in entitlement of at least 1 month; and",
    "a TY of entitlement to a different type of benefit includes a NSM.",
    "The auxiliary beneficiary's entitlement ends with the month before the termination month.",
    "Failure to have an entitled “child-in-care” does not qualify the mother or father, young wife or husband to a termination grace year since not having a “child-in-care” causes a suspension of benefits rather than termination.",
    "A grace year does not apply to a disabled beneficiary in any year if entitled solely to DIB, disabled widow(er)'s (DWB), or childhood disability benefits (CDB).",
    "Count NSMs for any month the RIB applies.",
    "Do not annotate the LMETY field if the only reason to apply the MET is the termination grace year or all months of entitlement are in the month of FRA or later.",
)


@pytest.mark.parametrize("quote", RULE_QUOTES)
def test_rule_text_is_quoted_from_the_captures(quote):
    assert quote in source_text("poms_rs_02501_030")


WORKED_EXAMPLE_QUOTES = (
    "A beneficiary becomes entitled to benefits 01/11. They will attain FRA in 08/11. They states they are working but will not earn over the monthly exempt amount for 06/11 and 07/11. Since 06/11 and 07/11 are NSMs, the initial grace year is 2011.",
    "A beneficiary becomes entitled to mother's benefits in 2010 and has a NSM that year. Their initial grace year is 2010. Their mother's benefits terminate in 06/10. In 2011, they become entitled to a retirement insurance benefit (RIB) on their own earnings record (ER).",
    "A beneficiary's date of birth is 01/20/92 and attains age 18 in 01/10. If the beneficiary is neither a student nor disabled, their benefit terminates in 01/10. Since entitlement ends in 12/09, which is the month before the termination month, their termination grace year is 2009.",
    "A beneficiary entitled to child's benefits in 2008 at age 16 has a NSM in the same year, which becomes their initial grace year. The benefits terminate in 03/10 after attaining age 18 making 2010 a termination grace year. The beneficiary becomes entitled to child's benefits beginning 09/10 when they return to school as a full-time student, which does not eliminate 2010 as a termination grace year. Their benefits terminate again 04/11 because they are no longer a full-time student. The year 2011 is another termination grace year.",
    "The beneficiary becomes entitled to RIB and DIB simultaneously in 06/10 at age 62. They elect to receive the reduced RIB benefit amount. The ET applies to any month they receive a RIB benefit. Their initial grace year is 2010 with NSMs of 06/10 through 12/10.",
    "They then elect to receive DIB instead of RIB in 01/11. The ET does not apply beginning 2011 since they receive DIB, although the RIB entitlement technically continues. Effective 01/12 they elect to receive RIB benefits with the ET applying for that year. However, their initial grace year was in 2010 and the MET will not apply to any other year.",
    "A beneficiary who works for wages becomes entitled to benefits beginning 02/11. They earned $40,000 in 2011 but did not earn over the monthly exempt amount in June and July. Therefore, June and July are NSMs.",
    "A beneficiary becomes entitled to DIB in 2009. They did not work any month after 2008. In 02/11, they attain FRA, their DIB terminates, and they become entitled to RIB.",
    "A beneficiary's entitlement begins in 2010 and yearly work deductions apply since their entitlement began. The beneficiary attains FRA in September 2011. However, in March 2011 the beneficiary stops working and NSMs apply beginning March 2011. In this situation, the initial grace year is 2011, which we enter in the LMETY field.",
    "A beneficiary receives widow's benefits and has a LMETY of 2010. In 2011, the beneficiary elects RIB and is still subject to the earnings test. The beneficiary does not receive a new LMETY. The LMETY will remain as 2010 on their RIB benefits.",
)


@pytest.mark.parametrize("quote", WORKED_EXAMPLE_QUOTES)
def test_worked_example_figures_are_quoted_from_the_captures(quote):
    assert quote in source_text("poms_rs_02501_030")


def test_initial_grace_2011_before_august_fra():
    months = [month(nonservice=index in (6, 7)) for index in range(1, 13)]
    result = grace_year(2011, GraceYearState(), months, fra_month=8)
    assert result.kinds == {K.INITIAL}
    assert result.protected_months == {6, 7}
    assert result.next_state.last_met_year == 2011


def test_mother_2010_break_then_rib_2011_has_another_grace():
    first = grace_year(
        2010,
        GraceYearState(),
        [month(B.MOTHER_FATHER)] * 5 + [EMPTY] * 7,
        termination_events=[TerminationEvent(5, B.MOTHER_FATHER)],
    )
    assert first.kinds == {K.INITIAL, K.TERMINATION}
    next_year = grace_year(2011, first.next_state, [RIB] * 12)
    assert next_year.kinds == {K.AFTER_BREAK}
    assert next_year.next_state.last_met_year == 2011


def test_january_2010_child_termination_belongs_to_2009():
    result = grace_year(
        2009,
        prior(2008, B.CHILD),
        [month(B.CHILD)] * 12,
        termination_events=[TerminationEvent(12, B.CHILD)],
    )
    assert result.kinds == {K.TERMINATION}
    assert result.next_state.last_met_year == 2008


def test_child_reentitlement_retains_2010_and_2011_termination_graces():
    initial = grace_year(2008, GraceYearState(), [month(B.CHILD)] * 12)
    y2009 = grace_year(2009, initial.next_state, [month(B.CHILD)] * 12)
    assert not y2009.applies
    y2010 = grace_year(
        2010,
        y2009.next_state,
        [month(B.CHILD)] * 2 + [EMPTY] * 6 + [month(B.CHILD)] * 4,
        termination_events=[TerminationEvent(2, B.CHILD)],
    )
    assert y2010.kinds == {K.TERMINATION}
    assert y2010.protected_months == {1, 2, 9, 10, 11, 12}
    y2011 = grace_year(
        2011,
        y2010.next_state,
        [month(B.CHILD)] * 3 + [EMPTY] * 9,
        termination_events=[TerminationEvent(3, B.CHILD)],
    )
    assert y2011.kinds == {K.TERMINATION}
    assert y2011.protected_months == {1, 2, 3}
    assert y2011.next_state.last_met_year == 2008


def test_simultaneous_rib_dib_elections_preserve_2010_lmety():
    types = {B.RIB, B.DIB}
    first = grace_year(
        2010,
        GraceYearState(),
        [EMPTY] * 5 + [month(B.RIB, entitled=types)] * 7,
        disability_reading=D.POMS_RIB_ELECTION,
    )
    assert first.kinds == {K.INITIAL}
    assert first.protected_months == set(range(6, 13))
    dib = grace_year(
        2011,
        first.next_state,
        [month(B.DIB, entitled=types)] * 12,
        disability_reading=D.POMS_RIB_ELECTION,
    )
    assert not dib.applies and not dib.protected_months
    rib = grace_year(
        2012,
        dib.next_state,
        [month(B.RIB, entitled=types)] * 12,
        disability_reading=D.POMS_RIB_ELECTION,
    )
    assert not rib.applies and not rib.protected_months
    assert rib.next_state.last_met_year == 2010


def test_simultaneous_disability_cfr_default_and_poms_alternative_are_explicit():
    months = [EMPTY] * 5 + [month(B.RIB, entitled={B.RIB, B.DIB})] * 7
    conservative = grace_year(2026, GraceYearState(), months)
    poms = grace_year(
        2026,
        GraceYearState(),
        months,
        disability_reading=D.POMS_RIB_ELECTION,
    )
    assert not conservative.applies
    assert not conservative.met_eligible_months
    assert poms.kinds == {K.INITIAL}
    assert poms.met_eligible_months == set(range(6, 13))
    assert poms.protected_months == set(range(6, 13))
    assert (
        "For purposes of determining whether a given year is a beneficiary's grace year, we will not count as a non-service month, a month that occurred while the beneficiary was entitled to disability benefits"
        in source_text("ecfr_20cfr404_subpart_e")
    )
    assert (
        "If the beneficiary becomes simultaneously entitled to RIB and DIB benefits, the earnings test (ET) applies to any month they elect to receive RIB."
        in source_text("poms_rs_02501_030")
    )


def test_cfr_404435_don_april_retirement_initial_may_through_december():
    result = grace_year(
        2026,
        GraceYearState(),
        [month(nonservice=False)] * 4 + [RIB] * 8,
    )
    assert result.kinds == {K.INITIAL}
    assert result.protected_months == set(range(5, 13))
    assert (
        "Don, age 62, will retire from his regular job in April of next year. Although he will have earned $15,000 for January-April of that year"
        in source_text("ecfr_20cfr404_subpart_e")
    )


def test_cfr_404435_marion_termination_2000_widow_2001_after_gap():
    # The example states an actual termination. Child-in-care suspension
    # alone is excluded separately under RS 02501.030B.3.b.
    initial = grace_year(1998, GraceYearState(), [month(B.MOTHER_FATHER)] * 12)
    next_year = grace_year(
        1999, initial.next_state, [month(B.MOTHER_FATHER)] * 12
    )
    terminated = grace_year(
        2000,
        next_year.next_state,
        [month(B.MOTHER_FATHER)] * 4 + [EMPTY] * 8,
        termination_events=[TerminationEvent(4, B.MOTHER_FATHER)],
    )
    assert terminated.kinds == {K.TERMINATION}
    assert terminated.next_state.last_met_year == 1998
    assert terminated.protected_months == {1, 2, 3, 4}
    widow = grace_year(
        2001,
        terminated.next_state,
        [EMPTY] + [month(B.WIDOW)] * 11,
    )
    assert widow.kinds == {K.AFTER_BREAK}
    assert widow.protected_months == set(range(2, 13))
    assert (
        "Marion was entitled to mother's insurance benefits from 1998 because she had a child in her care. Because she had a non-service month in 1998, 1998 was her initial grace year."
        in source_text("ecfr_20cfr404_subpart_e")
    )
    assert (
        "She applied for and became entitled to widow's insurance benefits effective February 2001."
        in source_text("ecfr_20cfr404_subpart_e")
    )


def test_retirement_2011_40000_earnings_june_july_nonservice():
    result = grace_year(
        2011,
        GraceYearState(),
        [EMPTY] + [month(nonservice=i in (6, 7)) for i in range(2, 13)],
    )
    assert result.protected_months == {6, 7}


def test_dib_2009_through_january_2011_then_fra_rib_creates_no_nsm():
    first = grace_year(2009, GraceYearState(), [month(B.DIB)] * 12)
    second = grace_year(2010, first.next_state, [month(B.DIB)] * 12)
    third = grace_year(
        2011,
        second.next_state,
        [month(B.DIB)] + [RIB] * 11,
        fra_month=2,
    )
    assert not third.applies and not third.protected_months
    assert third.next_state.last_met_year is None


def test_initial_year_2011_after_full_year_work_2010():
    first = grace_year(2010, GraceYearState(), [month(nonservice=False)] * 12)
    assert first.next_state.last_met_year is None
    second = grace_year(
        2011,
        first.next_state,
        [month(nonservice=False)] * 2 + [RIB] * 10,
        fra_month=9,
    )
    assert second.kinds == {K.INITIAL}
    assert second.protected_months == set(range(3, 9))


def test_widow_to_rib_without_break_transfers_2010_lmety():
    result = grace_year(2011, prior(2010, B.WIDOW), [RIB] * 12)
    assert not result.applies
    assert result.next_state.last_met_year == 2010


@pytest.mark.parametrize("kind", [B.DIB, B.DWB, B.CDB])
def test_disability_only_year_has_no_grace(kind):
    result = grace_year(2026, GraceYearState(), [month(kind)] * 12)
    assert not result.applies
    assert result.next_state.last_met_year is None


@settings(max_examples=150, deadline=None)
@given(
    child_months=st.integers(1, 11),
    cdb_months=st.integers(1, 11),
    nonservice=st.lists(st.booleans(), min_size=12, max_size=12),
    fra=st.one_of(st.none(), st.integers(1, 12)),
    lmety=st.integers(2000, 2025),
)
def test_property_mixed_child_cdb_termination_protects_only_child_nsms(
    child_months, cdb_months, nonservice, fra, lmety
):
    cdb_months = min(cdb_months, 12 - child_months)
    last_month = child_months + cdb_months
    state = replace(prior(2025, B.CHILD), last_met_year=lmety)
    months = (
        [month(B.CHILD, nonservice=nonservice[i]) for i in range(child_months)]
        + [month(B.CDB)] * cdb_months
        + [EMPTY] * (12 - last_month)
    )
    events = [TerminationEvent(last_month, B.CDB)]
    decision = grace_year(
        2026, state, months, fra_month=fra, termination_events=events
    )
    eligible = {
        i for i in range(1, child_months + 1) if fra is None or i < fra
    }
    assert decision.kinds == {K.TERMINATION}
    assert decision.met_eligible_months == eligible
    assert decision.protected_months == {
        i for i in eligible if nonservice[i - 1]
    }
    assert decision.next_state.last_met_year == lmety
    assert (
        grace_year(
            2026, state, months, fra_month=fra, termination_events=events
        )
        == decision
    )


@settings(max_examples=150, deadline=None)
@given(
    last_month=st.integers(1, 12),
    kinds=st.lists(
        st.sampled_from([B.DIB, B.DWB, B.CDB]), min_size=12, max_size=12
    ),
    lmety=st.one_of(st.none(), st.integers(2000, 2025)),
)
def test_property_disability_only_cdb_termination_has_no_grace(
    last_month, kinds, lmety
):
    months = [month(kind) for kind in kinds[:last_month]]
    months[-1] = month(B.CDB)
    months += [EMPTY] * (12 - last_month)
    state = replace(prior(2025, B.CDB), last_met_year=lmety)
    decision = grace_year(
        2026,
        state,
        months,
        termination_events=[TerminationEvent(last_month, B.CDB)],
    )
    assert not decision.applies
    assert not decision.kinds
    assert not decision.met_eligible_months
    assert not decision.protected_months
    assert decision.next_state.last_met_year == lmety


@settings(max_examples=150, deadline=None)
@given(
    reason=st.sampled_from(list(T)),
    next_kind=st.one_of(
        st.none(), st.sampled_from([kind for kind in B if kind is not B.CDB])
    ),
)
def test_property_cdb_termination_keeps_cause_and_next_month_exclusions(
    reason, next_kind
):
    months = [month(B.CHILD), month(B.CDB), EMPTY] + [EMPTY] * 9
    if next_kind is not None:
        months[2] = month(next_kind)
    decision = grace_year(
        2026,
        prior(2025, B.CHILD),
        months,
        termination_events=[TerminationEvent(2, B.CDB, reason=reason)],
    )
    applies = reason is T.NORMAL and next_kind is None
    assert decision.applies == applies
    assert decision.kinds == ({K.TERMINATION} if applies else set())
    assert decision.protected_months == ({1} if applies else set())
    assert decision.next_state.last_met_year == 2025


@pytest.mark.parametrize("reason", list(T)[1:])
def test_termination_excluded_causes_do_not_grant_grace(reason):
    result = grace_year(
        2011,
        prior(2010, B.MOTHER_FATHER),
        [month(B.MOTHER_FATHER)] * 6 + [EMPTY] * 6,
        termination_events=[
            TerminationEvent(6, B.MOTHER_FATHER, reason=reason)
        ],
    )
    assert not result.applies


def test_only_young_spouse_termination_qualifies():
    kwargs = dict(
        year=2011,
        state=prior(2010, B.SPOUSE),
        months=[month(B.SPOUSE)] * 6 + [EMPTY] * 6,
    )
    aged = grace_year(
        **kwargs, termination_events=[TerminationEvent(6, B.SPOUSE)]
    )
    young = grace_year(
        **kwargs,
        termination_events=[TerminationEvent(6, B.SPOUSE, young_spouse=True)],
    )
    assert not aged.applies
    assert young.kinds == {K.TERMINATION}


def test_normal_termination_still_excludes_next_month_other_benefit():
    result = grace_year(
        2011,
        prior(2010, B.CHILD),
        [month(B.CHILD)] * 6 + [month(B.RIB)] * 6,
        termination_events=[TerminationEvent(6, B.CHILD)],
    )
    assert not result.applies


def test_changed_type_after_break_pending_until_later_year_nsm():
    first = grace_year(
        2011,
        prior(2010, B.MOTHER_FATHER, gap=True),
        [month(nonservice=False)] * 12,
    )
    assert first.next_state.pending_after_break
    second = grace_year(2012, first.next_state, [RIB] * 12)
    assert second.kinds == {K.AFTER_BREAK}
    assert second.next_state.last_met_year == 2012


@pytest.mark.parametrize("later_nonservice_months", [1, 10])
def test_same_type_gap_does_not_erase_pending_grace(later_nonservice_months):
    state = GraceYearState(
        last_met_year=2000,
        previous_entitled_types={B.CHILD},
        had_entitlement=True,
        gap_since_entitlement=True,
        last_processed_year=2025,
    )
    months = (
        [month(B.SPOUSE, nonservice=False), EMPTY]
        + [month(B.SPOUSE)] * later_nonservice_months
        + [EMPTY] * (10 - later_nonservice_months)
    )
    result = grace_year(2026, state, months)
    assert result.kinds == {K.AFTER_BREAK}
    assert result.protected_months == set(
        range(3, 3 + later_nonservice_months)
    )
    assert result.next_state.last_met_year == 2026
    assert not result.next_state.pending_after_break
    assert (
        "a TY of entitlement to a different type of benefit includes a NSM."
        in source_text("poms_rs_02501_030")
    )


@settings(max_examples=150, deadline=None)
@given(
    st.sampled_from(
        [B.RIB, B.SPOUSE, B.DIVORCED_SPOUSE, B.WIDOW, B.MOTHER_FATHER]
    ),
    st.integers(2, 11),
    st.integers(2000, 2025),
)
def test_property_pending_grace_survives_another_same_type_gap(
    kind, gap_month, lmety
):
    state = GraceYearState(
        last_met_year=lmety,
        previous_entitled_types={B.CHILD},
        had_entitlement=True,
        gap_since_entitlement=True,
        last_processed_year=2025,
    )
    contiguous = [month(kind, nonservice=False)] * 11 + [month(kind)]
    interrupted = list(contiguous)
    interrupted[gap_month - 1] = EMPTY
    with_gap = grace_year(2026, state, interrupted)
    without_gap = grace_year(2026, state, contiguous)
    assert with_gap.kinds == without_gap.kinds == {K.AFTER_BREAK}
    assert with_gap.protected_months == without_gap.protected_months == {12}
    assert with_gap.next_state == without_gap.next_state
    assert with_gap.next_state.last_met_year == 2026


def test_same_spouse_type_after_divorce_and_gap_does_not_grant_fresh_grace():
    result = grace_year(
        2011,
        prior(2010, B.SPOUSE, gap=True),
        [month(B.DIVORCED_SPOUSE)] * 12,
    )
    assert not result.applies


@settings(max_examples=150, deadline=None)
@given(st.sampled_from([B.DIB, B.DWB, B.CDB]), st.integers(1, 12))
def test_property_disability_reentry_after_break_cannot_create_pending_grace(
    kind, month_of_rib
):
    first = grace_year(
        2011,
        prior(2010, B.WIDOW, gap=True),
        [month(kind)] * 12,
    )
    assert not first.next_state.pending_after_break
    second = grace_year(
        2012,
        first.next_state,
        [month(kind)] * (month_of_rib - 1) + [RIB] * (13 - month_of_rib),
    )
    assert not second.applies
    assert second.next_state.last_met_year == 2010


@pytest.mark.parametrize(
    "construct",
    [
        lambda: GraceMonth(received_types={B.RIB}),
        lambda: GraceMonth(entitled_types={"rib"}),
        lambda: GraceMonth(nonservice=1),
        lambda: GraceYearState(gap_since_entitlement=True),
        lambda: GraceYearState(last_met_year=2010),
        lambda: GraceYearState(previous_entitled_types={B.RIB}),
        lambda: TerminationEvent(0, B.CHILD),
        lambda: TerminationEvent(3, B.CHILD, young_spouse=True),
        lambda: TerminationEvent(3, B.CHILD, reason="normal"),
        lambda: grace_year(True, GraceYearState(), [RIB] * 12),
        lambda: grace_year(2026, GraceYearState(), [RIB] * 11),
        lambda: grace_year(2026, GraceYearState(), None),
        lambda: grace_year(2026, GraceYearState(), [RIB] * 12, fra_month=13),
        lambda: grace_year(2026, prior(2020), [RIB] * 12),
        lambda: grace_year(
            2026,
            GraceYearState(),
            [RIB] * 12,
            termination_events=[TerminationEvent(4, B.CHILD)],
        ),
        lambda: grace_year(
            2026,
            GraceYearState(),
            [month(B.CHILD)] * 12,
            termination_events=[TerminationEvent(4, B.CHILD)],
        ),
    ],
)
def test_invalid_input_is_an_input_error(construct):
    with pytest.raises(InvalidFamilyInput):
        construct()


@pytest.mark.parametrize(
    "values",
    [
        {"applies": 1},
        {"kinds": {"initial"}},
        {"kinds": set()},
        {"met_eligible_months": {0}},
        {"met_eligible_months": {True}},
        {"protected_months": {13}},
        {"protected_months": {2}, "met_eligible_months": {1}},
        {"applies": False, "kinds": set()},
        {"next_state": None},
    ],
)
def test_invalid_external_grace_decision_is_an_input_error(values):
    kwargs = dict(
        applies=True,
        kinds={K.INITIAL},
        met_eligible_months={1},
        protected_months={1},
        next_state=GraceYearState(),
    )
    kwargs.update(values)
    with pytest.raises(InvalidFamilyInput):
        GraceYearDecision(**kwargs)


@st.composite
def arbitrary_month(draw):
    types = draw(st.sets(st.sampled_from(list(B))))
    received = (
        draw(st.sets(st.sampled_from(sorted(types, key=lambda b: b.value))))
        if types
        else set()
    )
    return GraceMonth(
        entitled_types=types,
        received_types=received,
        nonservice=draw(st.booleans()),
    )


@settings(max_examples=200, deadline=None)
@given(
    st.lists(arbitrary_month(), min_size=12, max_size=12), st.integers(1, 12)
)
def test_property_only_entitled_nondisability_prefra_nonservice_months_protected(
    months, fra
):
    result = grace_year(2026, GraceYearState(), months, fra_month=fra)
    expected = {
        i
        for i, value in enumerate(months, 1)
        if i < fra
        and value.nonservice
        and value.received_types - DISABILITY_TYPES
        and not value.entitled_types & DISABILITY_TYPES
    }
    assert result.protected_months == expected
    assert result.met_eligible_months == {
        i
        for i, value in enumerate(months, 1)
        if i < fra
        and value.received_types - DISABILITY_TYPES
        and not value.entitled_types & DISABILITY_TYPES
    }
    assert result.applies == bool(expected)
    assert (result.next_state.last_met_year == 2026) == bool(expected)


@settings(max_examples=200, deadline=None)
@given(st.lists(arbitrary_month(), min_size=12, max_size=12))
def test_property_determinism_and_type_order_independence(months):
    first = grace_year(2026, GraceYearState(), months)
    reversed_sets = [
        replace(
            m,
            entitled_types=list(
                reversed(sorted(m.entitled_types, key=lambda b: b.value))
            ),
            received_types=list(
                reversed(sorted(m.received_types, key=lambda b: b.value))
            ),
        )
        for m in months
    ]
    assert grace_year(2026, GraceYearState(), months) == first
    assert grace_year(2026, GraceYearState(), reversed_sets) == first


@settings(max_examples=150, deadline=None)
@given(
    st.sampled_from([B.RIB, B.SPOUSE, B.CHILD, B.WIDOW, B.MOTHER_FATHER]),
    st.integers(1, 12),
)
def test_property_continuous_entitlement_cannot_create_second_grace(
    kind, first_nsm
):
    result = grace_year(
        2011,
        prior(2010, kind),
        [month(kind, nonservice=i >= first_nsm) for i in range(1, 13)],
    )
    assert not result.applies
    assert result.next_state.last_met_year == 2010


@settings(max_examples=150, deadline=None)
@given(st.integers(1, 10), st.integers(1, 2), st.booleans())
def test_property_new_type_requires_gap_but_same_type_never_renews(
    before, gap_length, different
):
    next_type = B.RIB if different else B.MOTHER_FATHER
    months = (
        [month(B.MOTHER_FATHER)] * before
        + [EMPTY] * gap_length
        + [month(next_type)] * (12 - before - gap_length)
    )
    result = grace_year(2011, prior(2010, B.MOTHER_FATHER), months)
    expected = different and before + gap_length < 12
    assert result.applies == expected
    assert result.next_state.last_met_year == (2011 if expected else 2010)


@settings(max_examples=150, deadline=None)
@given(
    st.integers(1, 12),
    st.sampled_from([B.CHILD, B.MOTHER_FATHER]),
    st.booleans(),
)
def test_property_termination_only_never_changes_lmety(
    last_month, kind, work_condition
):
    result = grace_year(
        2011,
        prior(2010, kind),
        [month(kind, nonservice=work_condition)] * last_month
        + [EMPTY] * (12 - last_month),
        termination_events=[TerminationEvent(last_month, kind)],
    )
    assert result.kinds == {K.TERMINATION}
    assert result.next_state.last_met_year == 2010
    assert result.protected_months == (
        set(range(1, last_month + 1)) if work_condition else set()
    )


@settings(max_examples=150, deadline=None)
@given(st.integers(1, 12), st.sampled_from([B.CHILD, B.CDB]))
def test_property_termination_event_order_independence(last_month, child_type):
    both = GraceMonth(
        {child_type, B.MOTHER_FATHER}, {child_type, B.MOTHER_FATHER}, True
    )
    events = [
        TerminationEvent(last_month, child_type),
        TerminationEvent(last_month, B.MOTHER_FATHER),
    ]
    months = [both] * last_month + [EMPTY] * (12 - last_month)
    assert grace_year(
        2011, prior(2010, B.CHILD), months, termination_events=events
    ) == grace_year(
        2011,
        prior(2010, B.CHILD),
        months,
        termination_events=list(reversed(events)),
    )


@settings(max_examples=150, deadline=None)
@given(
    st.lists(st.booleans(), min_size=12, max_size=12),
    st.lists(st.booleans(), min_size=12, max_size=12),
    st.integers(1, 12),
)
def test_property_poms_rib_election_separates_entitlement_from_receipt(
    elect_rib, work_conditions, fra
):
    months = [
        month(
            B.RIB if elect else B.DIB,
            nonservice=work,
            entitled={B.RIB, B.DIB},
        )
        for elect, work in zip(elect_rib, work_conditions, strict=True)
    ]
    poms = grace_year(
        2026,
        GraceYearState(),
        months,
        fra_month=fra,
        disability_reading=D.POMS_RIB_ELECTION,
    )
    eligible = {i for i, elect in enumerate(elect_rib, 1) if elect and i < fra}
    expected = {i for i in eligible if work_conditions[i - 1]}
    assert poms.met_eligible_months == eligible
    assert poms.protected_months == expected
    assert poms.applies == bool(expected)
    conservative = grace_year(2026, GraceYearState(), months, fra_month=fra)
    assert not conservative.applies
    assert not conservative.met_eligible_months


@settings(max_examples=150, deadline=None)
@given(st.integers(2000, 2500), st.integers(1, 12))
def test_property_state_advances_exactly_one_year_without_hidden_mutation(
    year, first_nsm
):
    state = GraceYearState()
    first_months = tuple(
        month(nonservice=i >= first_nsm) for i in range(1, 13)
    )
    first = grace_year(year, state, first_months)
    assert state == GraceYearState()
    assert first.next_state.last_processed_year == year
    assert first.next_state.last_met_year == year
    second = grace_year(year + 1, first.next_state, [EMPTY] * 12)
    assert second.next_state.last_processed_year == year + 1
    assert second.next_state.last_met_year == year
    assert not second.applies
    assert second.next_state.gap_since_entitlement


@settings(max_examples=150, deadline=None)
@given(st.integers(1, 12))
def test_property_after_break_eligibility_survives_year_without_nonservice(
    first_nsm,
):
    first = grace_year(
        2011,
        prior(2010, B.MOTHER_FATHER, gap=True),
        [month(nonservice=False)] * 12,
    )
    assert not first.applies
    assert first.next_state.pending_after_break
    second = grace_year(
        2012,
        first.next_state,
        [month(nonservice=i >= first_nsm) for i in range(1, 13)],
    )
    assert second.kinds == {K.AFTER_BREAK}
    assert second.next_state.last_met_year == 2012
    assert not second.next_state.pending_after_break
