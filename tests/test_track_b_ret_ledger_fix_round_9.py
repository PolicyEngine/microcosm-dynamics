"""Round 9: the child-in-care minimum under a month's deductions.

Also the PIA cap on a RIB before 1983. Every record is invented or built from
a captured SSA rule. Nothing here admits a population, behavioral or forecast
claim.
"""

from __future__ import annotations

from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.test_track_b_ret_ledger_fix_round_7 import (
    OWN_HISTORY,
    RC,
    UR,
    _assert_invalid,
    _assert_refusal,
    _outcome,
    _rib_record,
)
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
RET_PARAMS = load_ret_parameters()
MONTH = g.YearMonth(2026, 1)
OWN_WORK = g.DeductionReason.OWN_EARNINGS_TEST
CAPTURES = Path(__file__).parent / "data/track_b/arf_recompute_sources"
ONE_HOUSEHOLD = {"w": "one", "c1": "one", "c2": "one"}
TWO_HOUSEHOLDS = {"w": "one", "c1": "one", "c2": "two"}


def _state(pia, maximum):
    return g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(pia),
        F(maximum),
        eligibility_year=2026,
        widow_drc_savings_clause=False,
    )


def _caregiver(role, months=60, period=60, *, care="c1", own=None):
    if role is g.Role.DISABLED_WIDOW:
        return g.Beneficiary("w", role, child_in_care=care, own_benefit=own)
    return g.Beneficiary(
        "w",
        role,
        reduction_months=months,
        reduction_period_months=period,
        child_in_care=care,
        own_benefit=own,
    )


def _mother(own=None):
    return g.Beneficiary("w", g.Role.MOTHER_FATHER, own_benefit=own)


def _family(caregiver):
    return (
        caregiver,
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
    )


def _after(state, members, events, households=ONE_HOUSEHOLD):
    return g.family_benefits_after_deductions(
        state,
        members,
        payment_month=MONTH,
        params=PARAMS,
        deductions=events,
        households=households,
        standalone=True,
    )


def _ordinary(state, members):
    return g.family_benefits(
        state, members, payment_month=MONTH, params=PARAMS, standalone=True
    )


def _full(permanent=True):
    return g.BenefitDeduction(OWN_WORK, F(0), permanent)


def _partial(payable, permanent=True):
    return g.BenefitDeduction(OWN_WORK, F(payable), permanent)


def _refuses(reason, action):
    with pytest.raises(g.FamilyConfigurationUnsupported) as error:
        action()
    assert error.value.reason is reason


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def test_the_captures_carry_each_quoted_rule():
    statute = " ".join(
        (CAPTURES / "lii_usc_402q_415f_excerpts.txt").read_text().split()
    )
    assert (
        "had he or she been entitled for such month to mother's or father's"
        " insurance benefits" in statute
    )
    regulation = " ".join(
        (CAPTURES / "ecfr_20cfr_404_410.xml").read_text().split()
    )
    assert (
        "the benefit amount you would receive as a mother or father for any"
        " month" in regulation
    )
    assert (
        "they cannot receive less than the amount a mother and father would"
        " receive" in source_text("poms_rs_00615_340")
    )
    assert (
        "disregard that beneficiary when distributing the family maximum"
        in source_text("poms_gn_02603_050")
    )
    assert "not subject to a deduction" in source_text("poms_gn_02603_050")
    assert (
        "Round the result down to the next dime for benefits after 5/82 and"
        " up to the next dime for benefits prior to 6/82"
        in source_text("poms_rs_00615_101")
    )
    assert (
        "The new money amount of reduction is subtracted from the new PIA"
        in source_text("poms_rs_00615_005")
    )


# ---------------------------------------------------------------------------
# G: the minimum reads this month's events
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("pia", "maximum", "months", "before", "after", "whole"),
    [
        ("1.40", "2.10", 60, "0.80", "1", 1),
        ("4", "6", 60, "2.40", "3", 3),
        ("1000", "1500", 60, "612.80", "750", 750),
        ("0.30", "0.40", 1, "0.10", "0.20", 0),
    ],
)
def test_a_full_deduction_raises_the_care_minimum(
    pia, maximum, months, before, after, whole
):
    state = _state(pia, maximum)
    members = _family(_caregiver(g.Role.WIDOW, months))
    events = {"c2": _full()}
    result = _after(state, members, events)
    row = result.by_id()["w"]
    assert row.age_adjusted_rate == row.auxiliary_payable == F(after)
    assert row.whole_dollar_auxiliary == whole
    unfloored = _after(
        state, _family(_caregiver(g.Role.WIDOW, months, care=False)), events
    )
    assert unfloored.by_id()["w"].auxiliary_payable == F(before)


def test_the_minimum_moves_only_the_caregivers_own_money():
    state = _state(1000, 1500)
    events = {"c2": _full()}
    result = _after(state, _family(_caregiver(g.Role.WIDOW)), events)
    plain = _after(
        state, _family(_caregiver(g.Role.WIDOW, care=False)), events
    )
    for key in ("c1", "c2"):
        assert result.by_id()[key] == plain.by_id()[key]
    raised, rate = result.by_id()["w"], plain.by_id()["w"]
    assert raised.family_maximum_rate == rate.family_maximum_rate
    assert raised.counted_against_maximum == rate.counted_against_maximum
    assert result.subject_total == plain.subject_total
    assert result.record_total - plain.record_total == (
        raised.auxiliary_payable - rate.auxiliary_payable
    )


def test_a_temporary_deduction_reaches_only_its_own_household():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    same = _after(state, members, {"c2": _full(False)})
    assert same.by_id()["w"].auxiliary_payable == 750
    other = _after(state, members, {"c2": _full(False)}, TWO_HOUSEHOLDS)
    assert other.by_id()["w"].auxiliary_payable == 500
    assert other.by_id()["w"] == _ordinary(state, members).by_id()["w"]


def test_a_divorced_caregiver_outside_the_maximum_keeps_the_minimum():
    # The actual family never binds, and only the comparison family does.
    state = _state("2.70", "4.10")
    members = _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE))
    assert not _ordinary(state, members).family_maximum_binding
    assert _ordinary(state, members).by_id()["w"].auxiliary_payable == F(
        "1.90"
    )
    result = _after(state, members, {"c2": _full()})
    row = result.by_id()["w"]
    assert row.auxiliary_payable == 2
    assert row.whole_dollar_auxiliary == 2
    assert not row.subject_to_family_maximum
    assert result.record_total == 2 + 2


def test_a_disabled_widow_reaches_the_same_minimum():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.DISABLED_WIDOW))
    assert _after(state, members, {"c2": _full()}).by_id()[
        "w"
    ].auxiliary_payable == F(750)


def test_a_deducted_caregiver_keeps_the_ordinary_minimum():
    # GN 02603.050B.3 redistributes only to people not subject to a deduction,
    # in the actual family and in the comparison alike.
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    ordinary = _ordinary(state, members).by_id()["w"]
    result = _after(
        state, members, {"w": _partial(400), "c2": _full()}
    ).by_id()["w"]
    assert result.auxiliary_payable == 400
    assert result.age_adjusted_rate == ordinary.age_adjusted_rate


def test_each_caregiver_compares_alone():
    state = _state(1000, 1800)
    members = (
        _caregiver(g.Role.WIDOW),
        g.Beneficiary(
            "s",
            g.Role.SURVIVING_DIVORCED_SPOUSE,
            reduction_months=60,
            reduction_period_months=60,
            child_in_care="c1",
        ),
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
    )
    households = {"w": "one", "s": "one", "c1": "one", "c2": "one"}
    events = {"c2": _full()}
    result = _after(state, members, events, households)

    def alone(key, first):
        other = "s" if key == "w" else "w"
        comparison = tuple(
            (
                first
                if m.beneficiary_id == key
                else (
                    g.Beneficiary(
                        other,
                        m.role,
                        reduction_months=60,
                        reduction_period_months=60,
                        child_in_care=False,
                    )
                    if m.beneficiary_id == other
                    else m
                )
            )
            for m in members
        )
        return _after(state, comparison, events, households)

    widow = alone("w", _mother()).by_id()["w"].auxiliary_payable
    divorced = (
        alone("s", g.Beneficiary("s", g.Role.MOTHER_FATHER))
        .by_id()["s"]
        .auxiliary_payable
    )
    # The widow's comparison leaves the divorced spouse outside the maximum,
    # so the mother takes her full 750. The divorced spouse's comparison counts
    # the widow, and 1,800 / 2,500 of her 750 gives 540.
    assert (widow, divorced) == (750, 540)
    # 71.5% of 1,000 gives each of them 715 before the minimum.
    assert result.by_id()["w"].age_adjusted_rate == 750
    assert result.by_id()["s"].age_adjusted_rate == 715


def test_a_deduction_on_one_caregiver_raises_the_others_minimum():
    state = _state(1000, 1500)
    members = (
        _caregiver(g.Role.WIDOW),
        g.Beneficiary(
            "s",
            g.Role.SURVIVING_DIVORCED_SPOUSE,
            reduction_months=60,
            reduction_period_months=60,
            child_in_care="c1",
        ),
        g.Beneficiary("c1", g.Role.CHILD),
    )
    households = {"w": "one", "s": "one", "c1": "one"}
    # With the widow counted, 1,500 / 2,500 of the mother's 750 gives 450, and
    # 715 stands. Her full deduction leaves the comparison 750.
    assert (
        _after(state, members, {}, households).by_id()["s"].age_adjusted_rate
        == 715
    )
    result = _after(state, members, {"w": _full()}, households).by_id()
    assert result["w"].auxiliary_payable == 0
    assert result["s"].age_adjusted_rate == 750
    assert result["s"].auxiliary_payable == 750


def test_a_dual_caregiver_takes_the_offset_after_the_minimum():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(100), birth_year=1960)
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW, 60, 80, own=own))
    events = {"c2": _full()}
    result = _after(state, members, events).by_id()["w"]
    mother = _after(state, _family(_mother(own)), events).by_id()["w"]
    plain = _after(
        state,
        _family(_caregiver(g.Role.WIDOW, 60, 80, care=False, own=own)),
        events,
    ).by_id()["w"]
    assert result.age_adjusted_rate == max(
        plain.age_adjusted_rate, mother.age_adjusted_rate
    )
    assert result.auxiliary_payable == max(
        F(0), result.age_adjusted_rate - result.own_benefit
    )


@pytest.mark.parametrize(
    "own, maximum, rate, payable",
    [
        # With room under the maximum G's minimum already raised 715 to 750,
        # and the offset follows it.
        (100, 3000, 750, 650),
        # A dual rate takes no redistribution in either family, so the
        # comparison stays below 715 under a binding maximum.
        (100, 1500, 715, 615),
        # A RIB at three-quarters of the PIA fails the mother's test, so the
        # minimum stays out, and the offset stops at zero.
        (800, 1500, 715, 0),
    ],
)
def test_a_dual_caregiver_outside_the_maximum_takes_the_same_offset(
    own, maximum, rate, payable
):
    benefit = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(own), birth_year=1960)
    members = _family(
        _caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, 80, 80, own=benefit)
    )
    result = _after(_state(1000, maximum), members, {"c2": _full()}).by_id()[
        "w"
    ]
    assert result.age_adjusted_rate == rate
    assert result.auxiliary_payable == payable


def test_a_family_with_no_events_keeps_its_ordinary_result():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    assert _after(state, members, {}) == _ordinary(state, members)


# ---------------------------------------------------------------------------
# G: a partial event
# ---------------------------------------------------------------------------
def test_a_partial_deduction_refuses_where_it_can_move_the_rate():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    _refuses(
        g.UnsupportedReason.CARE_MINIMUM_PARTIAL_DEDUCTION,
        lambda: _after(state, members, {"c2": _partial(350)}),
    )


def test_a_partial_deduction_refuses_outside_the_maximum_too():
    state = _state("2.70", "4.10")
    members = _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE))
    _refuses(
        g.UnsupportedReason.CARE_MINIMUM_PARTIAL_DEDUCTION,
        lambda: _after(state, members, {"c2": _partial("1")}),
    )


def test_a_partial_deduction_computes_where_the_minimum_cannot_reach():
    state = _state(1000, 2400)
    members = _family(_caregiver(g.Role.WIDOW, 1))
    events = {"c2": _partial(700)}
    result = _after(state, members, events).by_id()["w"]
    plain = _after(
        state, _family(_caregiver(g.Role.WIDOW, 1, care=False)), events
    ).by_id()["w"]
    assert result.auxiliary_payable == plain.auxiliary_payable > 750


def test_a_partial_deduction_keeps_a_minimum_it_cannot_change():
    # Another household's temporary event moves no comparison rate.
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    result = _after(
        state, members, {"c2": _partial(350, False)}, TWO_HOUSEHOLDS
    )
    assert result.by_id()["w"].auxiliary_payable == 500


def test_a_full_and_a_partial_event_share_the_partial_refusal():
    state = _state(1000, 1800)
    members = (
        _caregiver(g.Role.WIDOW),
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
        g.Beneficiary("c3", g.Role.CHILD),
    )
    households = {"w": "one", "c1": "one", "c2": "one", "c3": "one"}
    _refuses(
        g.UnsupportedReason.CARE_MINIMUM_PARTIAL_DEDUCTION,
        lambda: _after(
            state,
            members,
            {"c2": _full(), "c3": _partial(100)},
            households,
        ),
    )


def test_the_refusal_keeps_the_input_checks_first():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.WIDOW))
    with pytest.raises(g.InvalidFamilyInput):
        _after(state, members, {"c2": _partial(4000)})


def test_nh_reservations_refuse_on_a_comparison():
    state = _state(1000, 1500)
    members = _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE))
    _refuses(
        g.UnsupportedReason.DEDUCTION_AGE_WORK_INTERACTION,
        lambda: g.family_benefits_after_deductions(
            state,
            members,
            payment_month=MONTH,
            params=PARAMS,
            deductions={"c2": _full()},
            households=ONE_HOUSEHOLD,
            worker_deductions={"c1": F(100)},
            standalone=True,
        ),
    )


def _with_nh_reservation(state, members, events):
    return g.family_benefits_after_deductions(
        state,
        members,
        payment_month=MONTH,
        params=PARAMS,
        deductions=events,
        households=ONE_HOUSEHOLD,
        worker_deductions={"c1": F(100)},
        standalone=True,
    )


def test_a_deducted_caregiver_reaches_no_comparison():
    # The refusal above needs a comparison, and this month's only caregiver
    # keeps G's ordinary minimum.
    members = _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE))
    result = _with_nh_reservation(
        _state(1000, 1500), members, {"w": _full()}
    ).by_id()
    assert result["w"].auxiliary_payable == 0
    assert result["c1"].reserved_work_deduction == 100


def test_an_unentitled_caregiver_reaches_no_comparison():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1200), birth_year=1960)
    members = _family(
        _caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, 60, 80, own=own)
    )
    result = _with_nh_reservation(
        _state(1000, 1500), members, {"c2": _full()}
    ).by_id()
    assert result["w"].entitled is False
    assert result["w"].auxiliary_payable == 0


def test_a_living_workers_divorced_spouse_has_no_care_minimum():
    # 402(q)(5)(D) names a widow's or widower's benefit, and a divorced spouse
    # of a living worker can still declare a child in care.
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        F(1500),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000)),
    )
    members = (
        g.Beneficiary("w", g.Role.DIVORCED_SPOUSE, child_in_care="c1"),
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
    )
    ordinary = _ordinary(state, members).by_id()["w"]
    result = _after(state, members, {"c2": _full()}).by_id()["w"]
    assert result.auxiliary_payable == ordinary.auxiliary_payable


# ---------------------------------------------------------------------------
# G: invariants over random families, through the public API
# ---------------------------------------------------------------------------
ROLES = st.sampled_from(
    (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE, g.Role.DISABLED_WIDOW)
)
families = st.tuples(
    st.integers(3, 30_000).map(lambda n: F(n, 10)),
    st.integers(100, 190),
    ROLES,
    st.sampled_from((1, 12, 30, 60)),
)


def _maximum(pia, percent):
    return g.floor_dime(pia * F(percent, 100))


@given(family=families, permanent=st.booleans(), same=st.booleans())
@example(family=(F("1.40"), 150, g.Role.WIDOW, 60), permanent=True, same=True)
@example(
    family=(F("2.70"), 152, g.Role.SURVIVING_DIVORCED_SPOUSE, 60),
    permanent=True,
    same=True,
)
@settings(max_examples=250, deadline=None)
def test_the_minimum_equals_the_better_of_the_two_public_families(
    family, permanent, same
):
    pia, percent, role, months = family
    state = _state(pia, _maximum(pia, percent))
    households = ONE_HOUSEHOLD if same else TWO_HOUSEHOLDS
    events = {"c2": _full(permanent)}
    care = _family(_caregiver(role, months))
    plain = _family(_caregiver(role, months, care=False))
    mother = _family(_mother())
    # An own-work event must withhold something in each family.
    assume(_ordinary(state, plain).by_id()["c2"].auxiliary_payable > 0)
    assume(_ordinary(state, mother).by_id()["c2"].auxiliary_payable > 0)
    actual = _after(state, care, events, households).by_id()
    without = _after(state, plain, events, households).by_id()
    comparison = _after(state, mother, events, households).by_id()
    assert actual["w"].age_adjusted_rate == max(
        without["w"].age_adjusted_rate, comparison["w"].auxiliary_payable
    )
    assert actual["c1"] == without["c1"]
    assert actual["c2"] == without["c2"]


@given(
    family=families,
    permanent=st.booleans(),
    same=st.booleans(),
    second=st.booleans(),
    share=st.fractions(0, 1),
)
@settings(max_examples=250, deadline=None)
def test_any_partial_amount_stays_between_the_two_bounds(
    family, permanent, same, second, share
):
    pia, percent, _, _ = family
    state = _state(pia, _maximum(pia, percent))
    households = ONE_HOUSEHOLD if same else TWO_HOUSEHOLDS
    mother = _family(_mother())
    ordinary = _ordinary(state, mother).by_id()
    gross = ordinary["c2"].auxiliary_payable
    assume(gross >= F(2, 10))
    assume(ordinary["c1"].auxiliary_payable > 0)
    payable = min(g.floor_dime(gross * share), gross - F(1, 10))
    extra = {"c1": _full(permanent)} if second else {}
    filled = _after(
        state,
        mother,
        {"c2": _partial(payable, permanent), **extra},
        households,
    ).by_id()["w"]
    highest = _after(
        state, mother, {"c2": _full(permanent), **extra}, households
    ).by_id()["w"]
    low = ordinary["w"].age_adjusted_rate
    assert low <= filled.age_adjusted_rate <= highest.age_adjusted_rate


@given(family=families, payable_share=st.fractions(0, 1))
@settings(max_examples=250, deadline=None)
def test_a_partial_deduction_computes_or_refuses_within_bounds(
    family, payable_share
):
    pia, percent, role, months = family
    state = _state(pia, _maximum(pia, percent))
    care = _family(_caregiver(role, months))
    plain = _family(_caregiver(role, months, care=False))
    mother = _family(_mother())
    gross = _ordinary(state, care).by_id()["c2"].auxiliary_payable
    assume(gross >= F(2, 10))
    assume(_ordinary(state, mother).by_id()["c2"].auxiliary_payable > 0)
    payable = min(g.floor_dime(gross * payable_share), gross - F(1, 10))
    assume(payable > 0)
    events = {"c2": _partial(payable)}
    without = _after(state, plain, events).by_id()["w"].age_adjusted_rate
    ordinary = _ordinary(state, mother).by_id()["w"].age_adjusted_rate
    highest = _after(state, mother, {"c2": _full()}).by_id()["w"]
    try:
        actual = _after(state, care, events).by_id()["w"].age_adjusted_rate
    except g.FamilyConfigurationUnsupported as error:
        assert (
            error.reason is g.UnsupportedReason.CARE_MINIMUM_PARTIAL_DEDUCTION
        )
        assert highest.age_adjusted_rate > max(without, ordinary)
    else:
        assert highest.age_adjusted_rate <= max(without, ordinary)
        assert actual == max(without, ordinary)


# ---------------------------------------------------------------------------
# RET: the ledger reads the same minimum
# ---------------------------------------------------------------------------
def _wages(excess):
    return RET_PARAMS.for_year(2026).lower_exempt_amount.value + 2 * excess


def _ret_case(
    state, members, excess, *, households=ONE_HOUSEHOLD, context=True
):
    baseline = _ordinary(state, members)
    people = []
    for row in baseline.beneficiaries:
        kind = T.CHILD if row.role is g.Role.CHILD else T.WIDOW
        wages = (
            _wages(excess[row.beneficiary_id])
            if (row.beneficiary_id in excess)
            else F(0)
        )
        people.append(
            r.RETBeneficiary(
                row.beneficiary_id,
                (kind,) * 12,
                {1},
                (row.auxiliary_payable,) + (F(0),) * 11,
                (row.original_benefit,) * 12,
                earnings=r.WorkEarnings((wages,) + (F(0),) * 11),
                fra_month=(
                    0
                    if kind is T.WIDOW and row.beneficiary_id not in excess
                    else None
                ),
            )
        )
    return r.RecordYear(
        2026,
        "nh",
        r.RecordKind.DECEASED,
        tuple(people),
        family_maximum_binding_months=(
            frozenset({1}) if baseline.family_maximum_binding else frozenset()
        ),
        family_months=(
            {1: r.RETFamilyMonth(state, members, PARAMS, households)}
            if context
            else {}
        ),
    )


def _ret(case):
    return r.evaluate_ret(
        "round9", F(1), lambda: r.apply_ret_year(case, RET_PARAMS)
    )


def _january(outcome, key):
    return next(
        row for row in outcome.ledger.for_beneficiary(key) if row.month == 1
    )


def test_ret_pays_the_minimum_on_a_binding_month():
    case = _ret_case(
        _state("1.40", "2.10"),
        _family(_caregiver(g.Role.WIDOW)),
        {"c2": 1},
    )
    assert case.family_maximum_binding_months == {1}
    outcome = _ret(case)
    assert outcome.supported
    row = _january(outcome, "w")
    assert row.net_due == 1
    assert row.payment == 1
    assert row.deduction == 0


def test_ret_pays_the_minimum_on_a_month_with_no_binding_maximum():
    case = _ret_case(
        _state("2.70", "4.10"),
        _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE)),
        {"c2": 2},
    )
    assert not case.family_maximum_binding_months
    outcome = _ret(case)
    assert outcome.supported
    row = _january(outcome, "w")
    assert row.net_due == 2
    assert row.payment == 2


def test_ret_leaves_a_family_with_no_care_alone():
    case = _ret_case(
        _state("2.70", "4.10"),
        _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, care=False)),
        {"c2": 2},
    )
    outcome = _ret(case)
    assert outcome.supported
    assert _january(outcome, "w").net_due == F("1.90")


def test_ret_refuses_a_partial_month_the_minimum_turns_on():
    case = _ret_case(
        _state(1000, 1500), _family(_caregiver(g.Role.WIDOW)), {"c2": 100}
    )
    outcome = _ret(case)
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is g.UnsupportedReason.CARE_MINIMUM_PARTIAL_DEDUCTION
    )
    counts = r.count_ret_outcomes([outcome])
    assert (counts.rows, counts.unsupported_weight) == (1, 1)


def test_ret_needs_the_family_facts_where_a_minimum_can_move():
    case = _ret_case(
        _state("2.70", "4.10"),
        _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE)),
        {"c2": 2},
        context=False,
    )
    outcome = _ret(case)
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is r.UnsupportedReason.FAMILY_CONTEXT_REQUIRED
    )


def test_an_unreduced_survivor_needs_no_family_facts():
    state = _state("2.70", "4.10")
    case = _ret_case(
        state,
        _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, 0, None)),
        {"c2": 2},
        context=False,
    )
    assert _ret(case).supported


def test_a_deduction_on_a_survivor_alone_needs_no_family_facts():
    state = _state("2.70", "4.10")
    members = (_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, care=None),)
    case = _ret_case(state, members, {"w": 1}, context=False)
    outcome = _ret(case)
    assert outcome.supported
    assert _january(outcome, "w").deduction == 1


def _beneficiary(key, kind, gross, original, excess, months):
    rate = F(gross) if 1 in months else F(0)
    wages = _wages(excess) if excess else F(0)
    return r.RETBeneficiary(
        key,
        (kind,) * 12,
        months,
        (rate,) + (F(0),) * 11,
        (F(original),) * 12,
        earnings=r.WorkEarnings((wages,) + (F(0),) * 11),
        fra_month=None if kind is T.CHILD or excess else 0,
    )


def _deceased(*people):
    return r.RecordYear(
        2026,
        "nh",
        r.RecordKind.DECEASED,
        tuple(_beneficiary(*person) for person in people),
    )


CHILD = ("c1", T.CHILD, 500, 500, 0, {1})
WORKING_CHILD = ("c2", T.CHILD, 500, 500, 100, {1})


@pytest.mark.parametrize("kind", [T.WIDOW, T.DWB])
def test_a_reduced_survivor_beside_a_child_needs_the_family_facts(kind):
    outcome = _ret(
        _deceased(("w", kind, 715, 1000, 0, {1}), CHILD, WORKING_CHILD)
    )
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is r.UnsupportedReason.FAMILY_CONTEXT_REQUIRED
    )


@pytest.mark.parametrize(
    "people",
    [
        pytest.param(
            (
                ("w", T.WIDOW, 715, 1000, 0, {1}),
                ("s", T.WIDOW, 715, 1000, 100, {1}),
            ),
            id="no child",
        ),
        pytest.param(
            (
                ("w", T.WIDOW, 715, 1000, 0, {1}),
                ("s", T.WIDOW, 715, 1000, 100, {1}),
                ("c1", T.CHILD, 500, 500, 0, {2}),
            ),
            id="child outside the month",
        ),
        pytest.param(
            (("w", T.WIDOW, 715, 1000, 100, {1}), CHILD),
            id="the only reduced survivor takes the deduction",
        ),
        pytest.param(
            (("w", T.WIDOW, 715, 1000, 0, {2}), CHILD, WORKING_CHILD),
            id="survivor outside the month",
        ),
        pytest.param(
            (("m", T.MOTHER_FATHER, 700, 750, 0, {1}), CHILD, WORKING_CHILD),
            id="a mother has no minimum",
        ),
    ],
)
def test_no_minimum_can_move_on_these_records(people):
    outcome = _ret(_deceased(*people))
    assert outcome.supported
    working = [person[0] for person in people if person[4]]
    assert working
    for key in working:
        assert _january(outcome, key).deduction > 0


def test_a_living_workers_record_has_no_care_minimum():
    record = r.RecordYear(
        2026,
        "n",
        r.RecordKind.RETIREMENT,
        (
            _beneficiary("n", T.RIB, 1000, 1000, 0, {1}),
            _beneficiary("w", T.WIDOW, 715, 1000, 0, {1}),
            _beneficiary(*WORKING_CHILD),
        ),
    )
    assert _ret(record).supported


# The ledger skips G on these months. A mutation that always reaches G changes
# no outcome, and this differential holds the two answers together.
@given(
    pia=st.integers(10, 30_000).map(lambda n: F(n, 10)),
    percent=st.integers(150, 190),
    excess=st.integers(1, 3000),
)
@settings(max_examples=60, deadline=None)
def test_with_no_caregiver_an_unbound_month_matches_g(pia, percent, excess):
    state = _state(pia, _maximum(pia, percent))
    members = _family(_caregiver(g.Role.SURVIVING_DIVORCED_SPOUSE, care=False))
    baseline = _ordinary(state, members)
    assume(not baseline.family_maximum_binding)
    assume(baseline.by_id()["c2"].auxiliary_payable > 0)
    case = _ret_case(state, members, {"c2": excess})
    outcome = _ret(case)
    assert outcome.supported
    direct = _after(
        state, members, {"c2": _partial(_january(outcome, "c2").net_due)}
    )
    for row in direct.beneficiaries:
        assert (
            _january(outcome, row.beneficiary_id).net_due
            == row.auxiliary_payable
        )


# ---------------------------------------------------------------------------
# The PIA cap before 1983
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("year", [1981, 1982])
@pytest.mark.parametrize(
    ("pia", "gross"),
    [("0.10", "0.20"), ("400", "400.10"), ("1000", "1000.10")],
)
@pytest.mark.parametrize("months", [0, 8])
def test_a_rib_above_its_pia_is_an_input_error_before_1983(
    year, pia, gross, months
):
    _assert_invalid(_rib_record(F(pia), F(gross), months=months, year=year))


def test_money_history_keeps_the_same_cap_before_1983():
    pia = F("333.30")
    _assert_invalid(
        _rib_record(
            pia, pia + F(1, 10), reason=OWN_HISTORY, cohort=1915, year=1982
        )
    )


def test_delayed_credits_keep_the_refusal_before_1983():
    pia = F("333.30")
    _assert_refusal(
        _rib_record(
            pia,
            pia + F(1, 10),
            reason=OWN_HISTORY,
            cohort=1915,
            credits=12,
            year=1982,
        ),
        OWN_HISTORY,
    )


def test_a_rate_at_or_below_the_pia_keeps_the_refusal_before_1983():
    pia = F("333.30")
    for gross in (pia, pia - F(1, 10), F(1)):
        _assert_refusal(
            _rib_record(pia, gross, year=1982), UR.PAYMENT_MONTH_BEFORE_1983
        )


def test_finality_keeps_its_refusal_before_1983():
    # RS 00615.754A.3 protects a rate above the correct PIA.
    pia = F("333.30")
    _assert_refusal(
        _rib_record(
            pia,
            pia + F(1, 10),
            conditions=(RC.ADMINISTRATIVE_FINALITY,),
            year=1982,
        ),
        UR.ADMINISTRATIVE_FINALITY,
    )
    assert _outcome(_rib_record(pia, pia, year=1982)).unsupported is not None
