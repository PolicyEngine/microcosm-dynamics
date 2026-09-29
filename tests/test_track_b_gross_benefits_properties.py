"""Track B milestone G: property-based invariants over invented families.

Families are invented by Hypothesis: records from the statutory maximum
(SSA-published NAWI, eligibility 1983-2026, random COLAs), with random
spouses, children, widow(er)s, mother/fathers and divorced beneficiaries,
reductions and dual entitlement. Each property is stated in the PR and in
``docs/design/track_b_g_gross_benefits.md``.

Intended violations are labelled: adding a *dually entitled* auxiliary can
raise another auxiliary's benefit under POMS RS 00615.768 (the Parisi
rule), so the "adding an auxiliary never raises another's benefit" property
is asserted for auxiliaries that are not dually entitled, and the minimized
counterexample for the dual case is pinned as intended behavior.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction as F

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits as oracle
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
MONTH = g.YearMonth(2026, 1)
OLD_AGE = g.OwnBenefitKind.OLD_AGE
DISABILITY = g.OwnBenefitKind.DISABILITY
DIME = F(1, 10)

dimes = st.integers(min_value=1, max_value=45_000).map(lambda d: F(d, 10))
years = st.integers(min_value=1983, max_value=2026)
cola_lists = st.lists(
    st.integers(min_value=0, max_value=90).map(lambda t: F(t, 10)),
    max_size=6,
)


@st.composite
def records(draw, kind=None):
    kind = kind or draw(st.sampled_from(list(g.FamilyKind)))
    year = draw(years)
    pia = draw(dimes)
    extra = {}
    if kind is g.FamilyKind.DISABILITY:
        extra["aime"] = draw(st.integers(min_value=0, max_value=20_000))
        extra["first_dib_entitlement"] = g.YearMonth(year, 1)
    if kind is g.FamilyKind.RETIREMENT and draw(st.booleans()):
        if draw(st.booleans()):
            extra["worker_reduction_months"] = draw(st.integers(0, 60))
        else:
            extra["worker_delayed_credit_months"] = draw(st.integers(0, 48))
            extra["worker_birth_year"] = draw(st.integers(1925, 1990))
    record = g.WorkerRecord(
        kind, year, pia, cola_percents=tuple(draw(cola_lists)), **extra
    )
    return g.record_state(record, PARAMS)


def _own_benefits(draw, *, plain):
    if draw(st.integers(0, 2)) == 0:
        return None
    pia = draw(dimes)
    if plain:
        return g.OwnBenefit(OLD_AGE, pia)
    kind = draw(st.sampled_from([OLD_AGE, DISABILITY]))
    if kind is DISABILITY:
        return g.OwnBenefit(DISABILITY, pia)
    return g.OwnBenefit(
        OLD_AGE, pia, reduction_months=draw(st.integers(0, 60))
    )


@st.composite
def beneficiaries(draw, kind, index, *, dual=True):
    bid = f"b{index}"
    if kind is g.FamilyKind.SURVIVOR:
        role = draw(
            st.sampled_from(
                [
                    g.Role.WIDOW,
                    g.Role.SURVIVING_DIVORCED_SPOUSE,
                    g.Role.MOTHER_FATHER,
                    g.Role.CHILD,
                    g.Role.CHILD,
                ]
            )
        )
    else:
        role = draw(
            st.sampled_from(
                [
                    g.Role.SPOUSE,
                    g.Role.SPOUSE_CHILD_IN_CARE,
                    g.Role.DIVORCED_SPOUSE,
                    g.Role.CHILD,
                    g.Role.CHILD,
                ]
            )
        )
    fields = {}
    if role in (g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE):
        fields["reduction_months"] = draw(st.integers(0, 60))
    if role in (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE):
        period = draw(st.integers(60, 84))
        fields["reduction_period_months"] = period
        fields["reduction_months"] = draw(st.integers(0, period))
        fields["birth_year"] = draw(st.integers(1929, 1995))
    own = (
        _own_benefits(draw, plain=role is g.Role.WIDOW)
        if dual and role is not g.Role.CHILD or dual and draw(st.booleans())
        else None
    )
    if own is not None and role is g.Role.WIDOW and own.kind is DISABILITY:
        own = None
    if own is not None and role is g.Role.SURVIVING_DIVORCED_SPOUSE:
        own = g.OwnBenefit(OLD_AGE, own.pia, own.reduction_months)
    return g.Beneficiary(bid, role, own_benefit=own, **fields)


@st.composite
def families(draw, kind=None, *, dual=True, max_size=6):
    state = draw(records(kind))
    size = draw(st.integers(0, max_size))
    members = [
        draw(beneficiaries(state.kind, index, dual=dual))
        for index in range(size)
    ]
    return state, members


def _compute(state, members, month=MONTH):
    return g.family_benefits(
        state, members, payment_month=month, params=PARAMS
    )


def _supported(state, members):
    try:
        return _compute(state, members)
    except g.FamilyConfigurationUnsupported:
        assume(False)


# ===========================================================================
# I1. The family maximum caps what the maximum governs
# ===========================================================================
@settings(max_examples=400, deadline=None)
@given(families())
def test_family_total_never_exceeds_the_maximum(family):
    state, members = family
    result = _supported(state, members)
    worker_share = F(0) if state.kind is g.FamilyKind.SURVIVOR else state.pia
    subject = [b for b in result.beneficiaries if b.subject_to_family_maximum]
    assert result.subject_total == worker_share + sum(
        (b.counted_against_maximum for b in subject), F(0)
    )
    assert result.subject_total <= state.family_maximum
    # What is paid on the record to people the maximum governs, plus the
    # worker's PIA, never exceeds it either. The statute's exceptions are
    # the worker's own delayed credits (RS 00615.695) and the divorced
    # beneficiaries paid outside the maximum (403(a)(3)(C)).
    paid = sum((b.auxiliary_payable for b in subject), F(0))
    assert worker_share + paid <= state.family_maximum
    for row in result.beneficiaries:
        assert 0 <= row.auxiliary_payable
        assert row.family_maximum_rate <= row.original_benefit
        assert row.standard_rate <= row.original_benefit
        if row.entitled and row.own_benefit is None:
            assert row.auxiliary_payable == row.age_adjusted_rate
            assert row.age_adjusted_rate <= row.family_maximum_rate


@settings(max_examples=300, deadline=None)
@given(families(kind=g.FamilyKind.RETIREMENT))
def test_worker_benefit_is_never_reduced_by_the_maximum(family):
    state, members = family
    result = _supported(state, members)
    alone = _compute(state, [])
    expected = g.own_monthly_benefit(state.worker, PARAMS)[1]
    assert result.worker_benefit == alone.worker_benefit == expected


# ===========================================================================
# I2. Auxiliaries' shares stay proportional
# ===========================================================================
@settings(max_examples=400, deadline=None)
@given(families())
def test_shares_are_proportional_to_original_benefits(family):
    state, members = family
    result = _supported(state, members)
    subject = [b for b in result.beneficiaries if b.subject_to_family_maximum]
    total = sum((b.original_benefit for b in subject), F(0))
    available = result.available_for_auxiliaries
    for row in subject:
        if total <= available:
            assert row.standard_rate == row.original_benefit
        else:
            exact = row.original_benefit * available / total
            assert exact - DIME < row.standard_rate <= exact
    if result.redistribution_applied:
        dual = [b for b in subject if b.own_benefit is not None]
        others = [b for b in subject if b.own_benefit is None]
        pool = available - sum((b.counted_against_maximum for b in dual), 0)
        others_total = sum((b.original_benefit for b in others), F(0))
        for row in others:
            exact = min(
                row.original_benefit,
                row.original_benefit * pool / others_total,
            )
            assert exact - DIME < row.family_maximum_rate <= exact
            assert row.family_maximum_rate >= row.standard_rate


# ===========================================================================
# I3. Raising the PIA never lowers the family maximum
# ===========================================================================
@given(years, dimes, dimes, cola_lists)
def test_family_maximum_is_monotone_in_the_pia(year, a, b, colas):
    low, high = sorted((a, b))
    fm = g.retirement_survivor_family_maximum
    assert fm(low, year, PARAMS) <= fm(high, year, PARAMS)
    assert g.increase_by_colas(fm(low, year, PARAMS), colas) <= (
        g.increase_by_colas(fm(high, year, PARAMS), colas)
    )
    assert fm(low, year, PARAMS) >= F(3, 2) * low - DIME


@given(dimes, dimes, st.integers(0, 20_000), st.integers(0, 20_000))
def test_disability_maximum_is_monotone(a, b, aime_a, aime_b):
    low, high = sorted((a, b))
    lo_aime, hi_aime = sorted((aime_a, aime_b))
    dmax = g.disability_family_maximum
    assert dmax(low, lo_aime) <= dmax(high, lo_aime)
    assert dmax(low, lo_aime) <= dmax(low, hi_aime)
    assert low <= dmax(low, lo_aime) <= F(3, 2) * low


# ===========================================================================
# I4. Adding an auxiliary never raises any other auxiliary's benefit
# ===========================================================================
@settings(max_examples=400, deadline=None)
@given(families(), st.data())
def test_adding_a_non_dual_auxiliary_never_raises_another(family, data):
    state, members = family
    extra = data.draw(beneficiaries(state.kind, 99, dual=False))
    before = _supported(state, members)
    try:
        after = _compute(state, [*members, extra])
    except g.FamilyConfigurationUnsupported:
        assume(False)
    after_rows = after.by_id()
    for row in before.beneficiaries:
        later = after_rows[row.beneficiary_id]
        assert later.family_maximum_rate <= row.family_maximum_rate
        assert later.auxiliary_payable <= row.auxiliary_payable
        assert later.total_received <= row.total_received
    if extra.role in (
        g.Role.DIVORCED_SPOUSE,
        g.Role.SURVIVING_DIVORCED_SPOUSE,
    ):
        # 403(a)(3)(C): others are computed as if the divorced spouse were
        # not entitled.
        for row in before.beneficiaries:
            assert after_rows[row.beneficiary_id] == row


def test_adding_a_dually_entitled_auxiliary_can_raise_another_intended():
    """Minimized counterexample, labelled intended (RS 00615.768E).

    With $300 left for auxiliaries, a dually entitled spouse (own PIA $100)
    and a child each get $150; the spouse is paid $50 and the child $250.
    Add a second dually entitled auxiliary: the standard shares fall to
    $100, neither dual beneficiary is paid anything, and the child now
    receives the whole $300. "Any benefit withheld from one beneficiary
    because of that person's dual entitlement will cause an increase in
    the benefits payable to the other auxiliaries."
    """
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(600),
        F(900),
        worker=g.OwnBenefit(OLD_AGE, F(600)),
    )
    own = g.OwnBenefit(OLD_AGE, F(100))
    spouse = g.Beneficiary("spouse", g.Role.SPOUSE, own_benefit=own)
    child = g.Beneficiary("child", g.Role.CHILD)
    second = g.Beneficiary("adult child", g.Role.CHILD, own_benefit=own)
    before = _compute(state, [spouse, child]).by_id()
    after = _compute(state, [spouse, child, second]).by_id()
    assert before["spouse"].auxiliary_payable == F(50)
    assert before["child"].auxiliary_payable == F(250)
    assert after["spouse"].auxiliary_payable == 0
    assert after["child"].auxiliary_payable == F(300)


# ===========================================================================
# I5. Dual entitlement never leaves a person below their own benefit
# ===========================================================================
@settings(max_examples=400, deadline=None)
@given(families())
def test_dual_entitlement_never_goes_below_the_own_benefit(family):
    state, members = family
    result = _supported(state, members)
    for row in result.beneficiaries:
        if row.own_benefit is None:
            continue
        assert row.auxiliary_payable >= 0
        assert row.total_received >= row.own_benefit
        if row.entitled and row.role is not g.Role.SPOUSE:
            # 402(k)(3)(A) for method-B and unreduced auxiliaries: the
            # person receives the larger of the two benefits.
            assert row.total_received == max(
                row.own_benefit, row.age_adjusted_rate
            )


# ===========================================================================
# I6. Unsupported configurations always raise, and stay in denominators
# ===========================================================================
UNSUPPORTED_MEMBERS = [
    g.Beneficiary("parent", g.Role.PARENT),
    g.Beneficiary("dwb", g.Role.DISABLED_WIDOW),
    g.Beneficiary(
        "gpo",
        g.Role.CHILD,
        conditions={g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET},
    ),
    g.Beneficiary(
        "cfm",
        g.Role.CHILD,
        conditions={g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD},
    ),
    g.Beneficiary(
        "final",
        g.Role.CHILD,
        conditions={g.BeneficiaryCondition.RATE_PROTECTED_BY_FINALITY},
    ),
]


@settings(max_examples=300, deadline=None)
@given(
    st.sampled_from(UNSUPPORTED_MEMBERS),
    st.integers(0, 6),
    st.sampled_from(list(g.RecordCondition) + [None]),
    st.data(),
)
def test_unsupported_configurations_always_raise(
    member, position, record_condition, data
):
    survivor_only = member.role in (g.Role.PARENT, g.Role.DISABLED_WIDOW)
    kind = g.FamilyKind.SURVIVOR if survivor_only else None
    state, members = data.draw(families(kind=kind))
    injected = list(members)
    injected.insert(min(position, len(injected)), member)
    if record_condition is not None:
        state = dataclasses.replace(state, conditions={record_condition})
    try:
        _compute(state, injected)
    except g.FamilyConfigurationUnsupported as error:
        assert error.code == "FAMILY_CONFIG_UNSUPPORTED"
    else:
        raise AssertionError("an unsupported family returned benefits")
    outcome = g.evaluate_family("row", 1, lambda: _compute(state, injected))
    denominator = g.count_family_outcomes([outcome])
    assert (denominator.rows, denominator.unsupported_rows) == (1, 1)


@given(st.lists(st.tuples(families(), st.booleans()), max_size=8))
def test_denominators_keep_every_row(rows):
    outcomes = []
    for index, ((state, members), poison) in enumerate(rows):
        injected = [*members, UNSUPPORTED_MEMBERS[2]] if poison else members
        outcomes.append(
            g.evaluate_family(
                f"r{index}",
                index + 1,
                lambda s=state, m=injected: _compute(s, m),
            )
        )
    denominator = g.count_family_outcomes(outcomes)
    assert denominator.rows == len(rows)
    assert denominator.supported_rows + denominator.unsupported_rows == len(
        rows
    )
    assert denominator.weight == sum(range(1, len(rows) + 1))
    assert denominator.unsupported_rows >= sum(p for _, p in rows)


# ===========================================================================
# I7. Determinism, order invariance and rounding
# ===========================================================================
@settings(max_examples=200, deadline=None)
@given(families(), st.randoms(use_true_random=False))
def test_results_do_not_depend_on_beneficiary_order(family, rng):
    state, members = family
    result = _supported(state, members)
    shuffled = list(members)
    rng.shuffle(shuffled)
    again = _compute(state, shuffled)
    assert again.by_id() == result.by_id()
    assert again.record_total == result.record_total


@settings(max_examples=300, deadline=None)
@given(families())
def test_amounts_are_dimes_and_payments_whole_dollars(family):
    state, members = family
    result = _supported(state, members)
    amounts = [result.family_maximum, result.pia, result.record_total]
    if result.worker_benefit is not None:
        amounts.append(result.worker_benefit)
        assert result.whole_dollar_worker == int(result.worker_benefit)
    for row in result.beneficiaries:
        amounts += [
            row.original_benefit,
            row.standard_rate,
            row.family_maximum_rate,
            row.age_adjusted_rate,
            row.auxiliary_payable,
        ]
        assert row.whole_dollar_auxiliary == int(row.auxiliary_payable)
    for amount in amounts:
        assert (amount * 10).denominator == 1
    assert result.record_total_whole_dollars <= result.record_total


# ===========================================================================
# Differential: the existing float oracle (ss/benefits.py) where it overlaps
# ===========================================================================
@given(st.integers(0, 60), st.integers(0, 60), st.integers(0, 84))
def test_reduction_fractions_match_the_float_oracle(months, spouse, widow):
    # policyengine-us stores 5/9 of 1 percent as 0.00555556, so the worker
    # fraction agrees only to the stored precision; the spouse and widow
    # rates are exact fractions in the bundle.
    worker = g.worker_reduction_fraction(months, PARAMS)
    assert abs(float(worker) - oracle.early_reduction(months, PARAMS)) < 1e-6
    assert worker == F(min(months, 36), 180) + F(max(0, months - 36), 240)
    spouse_exact = g.spouse_reduction_fraction(spouse, PARAMS)
    assert (
        abs(
            float(spouse_exact)
            - oracle.spousal_early_reduction(spouse, PARAMS)
        )
        < 1e-12
    )
    survivor = g.survivor_reduction_fraction(widow, 84, PARAMS)
    assert abs(float(survivor) - oracle.survivor_reduction(widow, PARAMS)) < (
        1e-12
    )


@given(dimes, st.integers(0, 10**6), st.integers(0, 60), st.integers(0, 60))
def test_spouse_benefit_matches_the_oracle_within_one_dime(
    worker_pia, own_draw, months, own_months
):
    """``spousal_benefit`` is method C with the offset before the reduction.

    Where no family maximum binds (a lone spouse), G's payable excess is
    the oracle's float amount floored to the dime (up to float error).
    """
    # An own PIA below one-half of the worker's, so the spouse is entitled.
    own_pia = F(own_draw % max(1, int(worker_pia * 5)), 10)
    assume(own_pia * 2 < worker_pia)
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        worker_pia,
        g.floor_dime(F(3, 2) * worker_pia),
        worker=g.OwnBenefit(OLD_AGE, worker_pia),
    )
    spouse = g.Beneficiary(
        "s",
        g.Role.SPOUSE,
        reduction_months=months,
        own_benefit=g.OwnBenefit(
            OLD_AGE, own_pia, reduction_months=own_months
        ),
    )
    row = _compute(state, [spouse]).by_id()["s"]
    # The oracle takes one-half of the PIA unrounded; the statute's OB is
    # dime-floored first, so compare against the floored OB.
    ob = g.floor_dime(worker_pia / 2)
    expected = oracle.spousal_benefit(
        float(own_pia), float(ob * 2), months, PARAMS
    )
    assert F(repr(expected)) - DIME - F(1, 10**6) < row.auxiliary_payable
    assert row.auxiliary_payable <= F(repr(expected)) + F(1, 10**6)


@given(dimes, dimes, st.integers(0, 84), st.integers(0, 36))
def test_widow_benefit_matches_the_oracle_within_rounding(
    deceased_pia, own_pia, months, deceased_early
):
    """``widow_benefit``: survivor ramp, RIB-LIM, larger of own or WIB.

    G rounds the reduction up and the RIB-LIM floor down to the dime; the
    oracle rounds nothing, so G may be lower by at most two dimes (and
    the deceased's reduced benefit is given to G already dime-floored).
    """
    params_84 = PARAMS
    factor = 1 - g.worker_reduction_fraction(deceased_early, params_84)
    deceased_rib = g.floor_dime(deceased_pia * factor)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        deceased_pia,
        g.floor_dime(F(188, 100) * deceased_pia),
        rib_lim_benefit=deceased_rib if deceased_early else None,
    )
    widow = g.Beneficiary(
        "w",
        g.Role.WIDOW,
        reduction_months=months,
        reduction_period_months=84,
        own_benefit=g.OwnBenefit(OLD_AGE, own_pia),
        birth_year=1962,
    )
    row = _compute(state, [widow]).by_id()["w"]
    oracle_factor = float(deceased_rib / deceased_pia) if deceased_early else 1
    expected = F(
        repr(
            oracle.widow_benefit(
                float(own_pia),
                float(deceased_pia),
                months,
                oracle_factor,
                params_84,
            )
        )
    )
    assert expected - 2 * DIME - F(1, 10**6) <= row.total_received
    assert row.total_received <= expected + F(1, 10**6)
