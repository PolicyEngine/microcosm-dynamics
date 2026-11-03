"""Round 10: a caregiver keeps its care facts in another's comparison.

Also the bound on RET's request for family facts. Every record is invented or
built from a captured SSA rule. Nothing here admits a population, behavioral
or forecast claim.
"""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from tests.test_track_b_ret_ledger_fix_round_9 import (
    MONTH,
    OWN_WORK,
    PARAMS,
    RET_PARAMS,
    _january,
    _ret,
)

HOUSEHOLD = {"former": "one", "spouse": "one", "child": "one"}
SPOUSE_WORKS = {"spouse": g.BenefitDeduction(OWN_WORK, F(0), False)}
DUAL_OWN = g.OwnBenefit(
    g.OwnBenefitKind.OLD_AGE, F(100), reduction_months=24, birth_year=1960
)


def _state(pia, maximum):
    return g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(pia),
        F(maximum),
        eligibility_year=2026,
        widow_drc_savings_clause=False,
    )


def _carer(key, role, birth, months, *, period=None, care="child", own=None):
    return g.Beneficiary(
        key,
        role,
        birth_year=birth,
        reduction_months=months,
        reduction_period_months=months if period is None else period,
        child_in_care=care,
        own_benefit=own,
    )


def _pair(birth=1966, months=84, *, own=None):
    return (
        _carer("former", g.Role.SURVIVING_DIVORCED_SPOUSE, birth, months),
        _carer("spouse", g.Role.WIDOW, birth, months, own=own),
        g.Beneficiary("child", g.Role.CHILD),
    )


def _after(state, members, events, households=HOUSEHOLD):
    return g.family_benefits_after_deductions(
        state,
        members,
        payment_month=MONTH,
        params=PARAMS,
        deductions=events,
        households=households,
        standalone=True,
    )


def _household(state, members, events, households=HOUSEHOLD):
    return g.household_benefits_after_deductions(
        {"r": g.HouseholdRecord("nh", state, members)},
        payment_month=MONTH,
        params=PARAMS,
        deductions=events,
        households=households,
    ).records["r"]


def _ordinary(state, members):
    return g.family_benefits(
        state, members, payment_month=MONTH, params=PARAMS, standalone=True
    )


def _replaced(members, key):
    """402(q)(5)(D)'s family: only ``key`` turns into a mother or father."""
    return tuple(
        (
            g.Beneficiary(
                key,
                g.Role.MOTHER_FATHER,
                birth_year=member.birth_year,
                own_benefit=member.own_benefit,
            )
            if member.beneficiary_id == key
            else member
        )
        for member in members
    )


def _without_care(members, key):
    return tuple(
        (
            g.Beneficiary(
                key,
                member.role,
                birth_year=member.birth_year,
                reduction_months=member.reduction_months,
                reduction_period_months=member.reduction_period_months,
                child_in_care=False,
                own_benefit=member.own_benefit,
            )
            if member.beneficiary_id == key
            else member
        )
        for member in members
    )


# ---------------------------------------------------------------------------
# G: another caregiver keeps its care facts in the comparison
# ---------------------------------------------------------------------------
def test_another_deducted_caregiver_keeps_its_minimum():
    state = _state(1800, "2891.50")
    assert g.retirement_survivor_family_maximum(F(1800), 2026, PARAMS) == F(
        "2891.50"
    )
    members = _pair()
    # In the former spouse's comparison the widow keeps her care facts. Her
    # share is 1,156.60 and her minimum pays 963.80, so her deduction leaves
    # 192.80 counted against the maximum (GN 02603.050C). The mother takes
    # 1,350 x (2,891.50 - 192.80) / 2,700 = 1,349.30.
    widow = _ordinary(state, _replaced(members, "former")).by_id()["spouse"]
    assert widow.family_maximum_rate == F("1156.60")
    assert widow.age_adjusted_rate == F("963.80")
    plain = _after(state, _without_care(members, "former"), SPOUSE_WORKS)
    assert plain.by_id()["former"].age_adjusted_rate == 1287
    result = _after(state, members, SPOUSE_WORKS).by_id()
    assert result["former"].age_adjusted_rate == F("1349.30")
    assert result["former"].whole_dollar_auxiliary == 1349
    assert result["spouse"].auxiliary_payable == 0
    assert result["child"].auxiliary_payable == 1350


@pytest.mark.parametrize(
    ("pia", "maximum", "expected"),
    [(1800, "2891.50", F("1349.30")), (1000, 1600, F("746.60"))],
)
def test_a_deducted_disabled_widow_keeps_the_minimum(pia, maximum, expected):
    state = _state(pia, maximum)
    members = (
        _carer("former", g.Role.SURVIVING_DIVORCED_SPOUSE, 1966, 84),
        g.Beneficiary("spouse", g.Role.DISABLED_WIDOW, child_in_care="child"),
        g.Beneficiary("child", g.Role.CHILD),
    )
    former = _after(state, members, SPOUSE_WORKS).by_id()["former"]
    assert former.age_adjusted_rate == expected
    assert (
        former.age_adjusted_rate
        == _after(state, _replaced(members, "former"), SPOUSE_WORKS)
        .by_id()["former"]
        .age_adjusted_rate
    )


def test_a_formula_maximum_moves_a_whole_dollar():
    maximum = g.retirement_survivor_family_maximum(F(1688), 2026, PARAMS)
    assert maximum == F("2586.90")
    state = _state(1688, maximum)
    members = _pair()
    # 1,034.70 less the widow's 862.30 minimum leaves 172.40 counted, and
    # 1,266 x (2,586.90 - 172.40) / 2,532 = 1,207.20.
    widow = _ordinary(state, _replaced(members, "former")).by_id()["spouse"]
    assert (widow.family_maximum_rate, widow.age_adjusted_rate) == (
        F("1034.70"),
        F("862.30"),
    )
    former = _after(state, members, SPOUSE_WORKS).by_id()["former"]
    assert former.age_adjusted_rate == F("1207.20")
    assert former.whole_dollar_auxiliary == 1207


@pytest.mark.parametrize("entry", [_after, _household])
def test_the_family_and_household_entries_agree(entry):
    state = _state("2.70", "4.20")
    members = _pair(1960, 80)
    # The widow's 1.60 share pays her 1.40 minimum and leaves 0.20 counted, so
    # the mother takes 2.00 x (4.20 - 0.20) / 4.00 = 2.00.
    widow = _ordinary(state, _replaced(members, "former")).by_id()["spouse"]
    assert (widow.family_maximum_rate, widow.age_adjusted_rate) == (
        F("1.60"),
        F("1.40"),
    )
    former = entry(state, members, SPOUSE_WORKS).by_id()["former"]
    assert former.age_adjusted_rate == 2
    assert former.whole_dollar_auxiliary == 2


@pytest.mark.parametrize("permanent", [True, False])
@pytest.mark.parametrize(
    ("pia", "maximum", "expected"),
    [(1000, 1600, F("746.60")), (1800, "2891.50", F("1349.30"))],
)
def test_a_dual_deductee_keeps_its_minimum_either_way(
    permanent, pia, maximum, expected
):
    # A dual row counts as permanent (GN 02603.050), so a temporary event on
    # it redistributes as a permanent one does.
    state = _state(pia, maximum)
    members = _pair(1960, 80, own=DUAL_OWN)
    events = {"spouse": g.BenefitDeduction(OWN_WORK, F(0), permanent)}
    former = _after(state, members, events).by_id()["former"]
    assert former.age_adjusted_rate == expected
    assert (
        former.age_adjusted_rate
        == _after(state, _replaced(members, "former"), events)
        .by_id()["former"]
        .age_adjusted_rate
    )


@pytest.mark.parametrize(
    ("permanent", "spouse_home", "expected"),
    [
        pytest.param(False, "one", F("1349.30"), id="temporary, same home"),
        pytest.param(False, "two", F(1287), id="temporary, other home"),
        pytest.param(True, "one", F(1350), id="permanent, same home"),
        pytest.param(True, "two", F(1350), id="permanent, other home"),
    ],
)
def test_each_event_reaches_the_comparison_as_it_reaches_the_family(
    permanent, spouse_home, expected
):
    state = _state(1800, "2891.50")
    members = _pair()
    households = {**HOUSEHOLD, "spouse": spouse_home}
    events = {"spouse": g.BenefitDeduction(OWN_WORK, F(0), permanent)}
    former = _after(state, members, events, households).by_id()["former"]
    comparison = _after(
        state, _replaced(members, "former"), events, households
    ).by_id()["former"]
    plain = _after(
        state, _without_care(members, "former"), events, households
    ).by_id()["former"]
    assert former.age_adjusted_rate == expected
    assert former.age_adjusted_rate == max(
        plain.age_adjusted_rate, comparison.age_adjusted_rate
    )


def test_three_caregivers_each_compare_with_one_entitlement_replaced():
    state = _state(1800, "2891.50")
    members = (
        _carer("former", g.Role.SURVIVING_DIVORCED_SPOUSE, 1966, 84),
        _carer("other", g.Role.SURVIVING_DIVORCED_SPOUSE, 1966, 60, period=84),
        _carer("spouse", g.Role.WIDOW, 1966, 84),
        g.Beneficiary("child", g.Role.CHILD),
    )
    households = {**HOUSEHOLD, "other": "one"}
    result = _after(state, members, SPOUSE_WORKS, households).by_id()
    for key in ("former", "other"):
        comparison = _after(
            state, _replaced(members, key), SPOUSE_WORKS, households
        ).by_id()[key]
        plain = _after(
            state, _without_care(members, key), SPOUSE_WORKS, households
        ).by_id()[key]
        assert result[key].age_adjusted_rate == max(
            plain.age_adjusted_rate, comparison.age_adjusted_rate
        )
    assert result["former"].age_adjusted_rate > 1287


@pytest.mark.parametrize("count", [1, 2, 3, 4])
@pytest.mark.parametrize("events", [{}, SPOUSE_WORKS])
def test_each_comparison_family_runs_once(monkeypatch, count, events):
    # A family is fixed by which caregivers it has turned into mothers, so a
    # call with k caregivers runs at most 2**k families, the actual one
    # included, however the comparisons nest.
    members = (_carer("spouse", g.Role.WIDOW, 1966, 84),) + tuple(
        _carer(f"s{n}", g.Role.SURVIVING_DIVORCED_SPOUSE, 1966, 84)
        for n in range(count - 1)
    )
    members += (g.Beneficiary("child", g.Role.CHILD),)
    households = {member.beneficiary_id: "one" for member in members}
    family = g._family_benefits
    seen = []

    def counted(state, beneficiaries, *args):
        seen.append(tuple(beneficiaries))
        return family(state, beneficiaries, *args)

    monkeypatch.setattr(g, "_family_benefits", counted)
    _after(_state(1800, "2891.50"), members, events, households)
    assert len(seen) == 2**count
    assert len(set(seen)) == len(seen)


def test_the_comparison_cache_ends_with_its_call():
    _after(_state(1800, "2891.50"), _pair(), SPOUSE_WORKS)
    assert g._CARE_COMPARISONS.get() is None


def test_one_scope_keeps_records_households_and_events_apart():
    # The household entry runs its records one after another, each in its own
    # scope. A scope that held several would still keep each family apart.
    members = _pair()
    widow = _state(1800, "2891.50")
    cases = [
        (widow, SPOUSE_WORKS, HOUSEHOLD),
        (_state(1000, 1600), SPOUSE_WORKS, HOUSEHOLD),
        (widow, SPOUSE_WORKS, {**HOUSEHOLD, "spouse": "two"}),
        (
            widow,
            {"spouse": g.BenefitDeduction(OWN_WORK, F(0), True)},
            HOUSEHOLD,
        ),
    ]

    def rates():
        return [
            _after(state, members, events, households)
            .by_id()["former"]
            .age_adjusted_rate
            for state, events, households in cases
        ]

    expected = [F("1349.30"), F("746.60"), F(1287), F(1350)]
    assert rates() == expected
    assert g._care_scope(rates)() == expected


# ---------------------------------------------------------------------------
# G: invariants over random caregiver pairs, through the public API
# ---------------------------------------------------------------------------
ROLES = st.sampled_from(
    (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE, g.Role.DISABLED_WIDOW)
)
MONTHS = st.sampled_from((1, 12, 30, 60))


def _member(key, role, months, care="child"):
    if role is g.Role.DISABLED_WIDOW:
        return g.Beneficiary(key, role, child_in_care=care)
    return g.Beneficiary(
        key,
        role,
        reduction_months=months,
        reduction_period_months=60,
        child_in_care=care,
    )


pairs = st.tuples(
    st.integers(3, 30_000).map(lambda n: F(n, 10)),
    st.integers(150, 188),
    st.tuples(ROLES, MONTHS, ROLES, MONTHS),
    st.booleans(),
)
events = st.dictionaries(
    st.sampled_from(("former", "spouse", "child", "second")),
    st.booleans().map(lambda p: g.BenefitDeduction(OWN_WORK, F(0), p)),
    min_size=1,
    max_size=2,
)
homes = st.fixed_dictionaries(
    {
        key: st.sampled_from(("one", "two"))
        for key in ("former", "spouse", "child", "second")
    }
)


def _random_family(pair):
    pia, percent, (first, months, second, other), two = pair
    state = _state(pia, g.floor_dime(pia * F(percent, 100)))
    members = (
        _member("former", first, months),
        _member("spouse", second, other),
        g.Beneficiary("child", g.Role.CHILD),
    )
    if two:
        members += (g.Beneficiary("second", g.Role.CHILD),)
    return state, members


SOL_PAIR = (
    F(1000),
    160,
    (g.Role.SURVIVING_DIVORCED_SPOUSE, 60, g.Role.WIDOW, 60),
    False,
)


@given(pair=pairs, chosen=events, households=homes)
@example(
    pair=SOL_PAIR,
    chosen={"spouse": g.BenefitDeduction(OWN_WORK, F(0), False)},
    households={k: "one" for k in ("former", "spouse", "child", "second")},
)
@settings(max_examples=250, deadline=None)
def test_each_caregiver_takes_the_better_of_its_rate_and_its_comparison(
    pair, chosen, households
):
    state, members = _random_family(pair)
    keys = {member.beneficiary_id for member in members}
    chosen = {key: event for key, event in chosen.items() if key in keys}
    households = {key: households[key] for key in keys}
    try:
        result = _after(state, members, chosen, households).by_id()
    except (g.InvalidFamilyInput, g.FamilyConfigurationUnsupported):
        return
    for key in ("former", "spouse"):
        if key in chosen or not result[key].entitled:
            continue
        try:
            comparison = _after(
                state, _replaced(members, key), chosen, households
            ).by_id()[key]
            plain = _after(
                state, _without_care(members, key), chosen, households
            ).by_id()[key]
        except g.InvalidFamilyInput:
            # A full own-work event must withhold something in each family,
            # and a mother's share can leave a child nothing to withhold.
            continue
        assert result[key].age_adjusted_rate == max(
            plain.age_adjusted_rate, comparison.age_adjusted_rate
        )
        # No minimum passes a mother's original benefit (402(g)(2)), which
        # bounds RET's request for family facts below.
        mother = g.original_benefit(
            g.Role.MOTHER_FATHER, g.FamilyKind.SURVIVOR, state.pia
        )
        assert comparison.age_adjusted_rate <= mother
        assert result[key].age_adjusted_rate <= max(
            plain.age_adjusted_rate, mother
        )


# ---------------------------------------------------------------------------
# RET: the provisional ledger reads the same minimum
# ---------------------------------------------------------------------------
KINDS = {
    g.Role.CHILD: T.CHILD,
    g.Role.WIDOW: T.WIDOW,
    g.Role.SURVIVING_DIVORCED_SPOUSE: T.WIDOW,
    g.Role.DISABLED_WIDOW: T.DWB,
}


def _ret_record(state, members, households, wages, *, context=True):
    baseline = _ordinary(state, members)
    people = tuple(
        r.RETBeneficiary(
            row.beneficiary_id,
            (KINDS[row.role],) * 12,
            {1},
            (row.auxiliary_payable,) + (F(0),) * 11,
            (row.original_benefit,) * 12,
            earnings=r.WorkEarnings(
                (wages.get(row.beneficiary_id, F(0)),) + (F(0),) * 11
            ),
            fra_month=None,
        )
        for row in baseline.beneficiaries
    )
    return r.RecordYear(
        2026,
        "nh",
        r.RecordKind.DECEASED,
        people,
        family_maximum_binding_months=(
            frozenset({1}) if baseline.family_maximum_binding else frozenset()
        ),
        family_months=(
            {1: r.RETFamilyMonth(state, members, PARAMS, households)}
            if context
            else {}
        ),
    )


def test_ret_pays_the_minimum_on_the_provisional_ledger():
    state = _state(1000, 1600)
    members = _pair()
    lower = RET_PARAMS.for_year(2026).lower_exempt_amount.value
    # 25,980 is 1,500 over the exempt amount, so the widow's 750 goes.
    outcome = _ret(
        _ret_record(state, members, HOUSEHOLD, {"spouse": lower + 1500})
    )
    assert outcome.supported
    former = _january(outcome, "former")
    assert former.provisional_net == F("746.60")
    assert former.provisional_payment == 746
    assert former.net_due == 750
    assert _january(outcome, "spouse").deduction == 750


# ---------------------------------------------------------------------------
# RET: family facts only where a minimum can reach the rate
# ---------------------------------------------------------------------------
def _person(key, kind, gross, original, wages=F(0)):
    return r.RETBeneficiary(
        key,
        (kind,) * 12,
        {1},
        (F(gross),) + (F(0),) * 11,
        (F(original),) * 12,
        earnings=r.WorkEarnings((F(wages),) + (F(0),) * 11),
        fra_month=0 if kind is not T.CHILD else None,
    )


def _deceased(*people, family_months=None):
    return r.RecordYear(
        2026,
        "nh",
        r.RecordKind.DECEASED,
        people,
        family_months=family_months or {},
    )


WORKING_CHILD = ("c", T.CHILD, 750, 750, 25980)


def test_a_rate_past_any_minimum_needs_no_family_facts():
    alone = _ret(
        _deceased(_person("w", T.WIDOW, 905, 1000), _person(*WORKING_CHILD))
    )
    assert alone.supported
    # The same record with G's facts: a 20-of-60 widow beside the child, and
    # a maximum the two OBs exactly reach.
    state = _state(1000, 1750)
    members = (
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            reduction_months=20,
            reduction_period_months=60,
            child_in_care="c",
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )
    assert _ordinary(state, members).by_id()["w"].auxiliary_payable == 905
    context = {
        1: r.RETFamilyMonth(state, members, PARAMS, {"w": "one", "c": "one"})
    }
    told = _ret(
        _deceased(
            _person("w", T.WIDOW, 905, 1000),
            _person(*WORKING_CHILD),
            family_months=context,
        )
    )
    assert told.supported
    for outcome in (alone, told):
        widow = _january(outcome, "w")
        assert (widow.net_due, widow.provisional_net) == (905, 905)
        child = _january(outcome, "c")
        assert (child.deduction, child.provisional_deduction) == (750, 750)


@pytest.mark.parametrize(
    ("gross", "supported"),
    [(F(750), True), (F("749.90"), False), (F(600), False)],
)
@pytest.mark.parametrize("kind", [T.WIDOW, T.DWB])
def test_a_childs_original_rate_bounds_the_request(gross, supported, kind):
    outcome = _ret(
        _deceased(_person("w", kind, gross, 1000), _person(*WORKING_CHILD))
    )
    assert outcome.supported is supported
    if not supported:
        assert (
            outcome.unsupported.reason
            is r.UnsupportedReason.FAMILY_CONTEXT_REQUIRED
        )


def test_the_higher_of_two_declared_child_rates_bounds_the_request():
    # Survivor children's OBs agree under 402(d)(2). Declarations that don't
    # keep the higher bound, the side that asks for facts.
    outcome = _ret(
        _deceased(
            _person("w", T.WIDOW, 700, 1000),
            _person("a", T.CHILD, 600, 600),
            _person(*WORKING_CHILD),
        )
    )
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is r.UnsupportedReason.FAMILY_CONTEXT_REQUIRED
    )


def test_a_widows_own_original_rate_still_bounds_the_request():
    # An unreduced rate has no age reduction for a minimum to undo.
    outcome = _ret(
        _deceased(_person("w", T.WIDOW, 500, 500), _person(*WORKING_CHILD))
    )
    assert outcome.supported


# A skipped month must pay what G pays once RET has the facts.
@given(pair=pairs, excess=st.integers(1, 3000), worker=st.booleans())
@settings(max_examples=120, deadline=None)
def test_a_month_ret_settles_without_family_facts_matches_g(
    pair, excess, worker
):
    state, members = _random_family(pair)
    households = {member.beneficiary_id: "one" for member in members}
    lower = RET_PARAMS.for_year(2026).lower_exempt_amount.value
    earner = "child" if worker else "spouse"
    wages = {earner: lower + 2 * excess}
    try:
        _ordinary(state, members)
        alone = _ret(
            _ret_record(state, members, households, wages, context=False)
        )
    except (g.InvalidFamilyInput, g.FamilyConfigurationUnsupported):
        return
    if not alone.supported:
        return
    told = _ret(_ret_record(state, members, households, wages))
    assert told.supported
    for member in members:
        key = member.beneficiary_id
        a, b = _january(alone, key), _january(told, key)
        assert (a.net_due, a.provisional_net, a.deduction) == (
            b.net_due,
            b.provisional_net,
            b.deduction,
        )
