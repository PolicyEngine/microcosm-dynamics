"""Parent and IEDS statutory conformance on invented reference families.

Verification class: statutory conformance. These tests admit gross benefits
for the supported parent and independently entitled divorced-spouse cases,
with no population, behavioral or forecast claim. Parent entitlement and
payments follow 402(h), 402(k)(3)(A), RS 00209.001 and RS 00209.015. IEDS
follows 402(b)(4)(A)/(c)(4)(A), RS 00202.005 and RS 00202.100; WEP ceases
after December 2023 under the captured RS 00605.360 repeal instruction.

The parent/IEDS captures supply no monetary worked example. Hand references
at PIA 1000: one parent 825, two parents 750 each; own RIB 1000 reduced for
36 months is 800, leaving a solo-parent excess of 25. At maximum 1500,
two parents and one child share 500 each. A parent with own DIB 600 remains
technically entitled with payment zero, so the other parent and child are
redistributed 750 each. Own DIB 100 instead leaves 400 and redistributes
550 to each other beneficiary. IEDS OB is 500, reduced to 375 for 36 months.
With own PIA 200 reduced to 160, method C pays (500 - 200) * .75 = 225;
method B pays 500 * .75 - 160 = 215. Each figure is invented arithmetic,
not a claim that SSA published a monetary example.
"""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)


def _family(state, members, month=NOW):
    return g.family_benefits(
        state,
        members,
        payment_month=month,
        params=PARAMS,
        standalone=True,
    )


def _survivor(pia=F(1000), maximum=F(1750)):
    # Invented families have no protected May 1978 survivor entitlement.
    return g.RecordState(
        g.FamilyKind.SURVIVOR, pia, maximum, widow_drc_savings_clause=False
    )


def _parent(bid="p", **kwargs):
    return g.Beneficiary(bid, g.Role.PARENT, **kwargs)


def _ieds(pia=F(1000), maximum=F(1750), *, worker=None, conditions=()):
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        maximum,
        worker=worker,
        conditions={g.RecordCondition.WORKER_NOT_ENTITLED, *conditions},
    )


def _divorce(bid="d", **kwargs):
    return g.Beneficiary(bid, g.Role.DIVORCED_SPOUSE, **kwargs)


def _rows(result):
    return {row.beneficiary_id: row for row in result.beneficiaries}


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (
            "poms_rs_00209_015",
            "Benefit rate equals 82 1/2% of the worker's primary "
            "insurance amount (PIA).",
        ),
        (
            "poms_rs_00209_015",
            "Benefit rate equals 75% of the worker's PIA for each "
            "month both are entitled.",
        ),
        (
            "poms_rs_00202_005",
            "No benefits are payable under this provision prior to "
            "January 1985.",
        ),
    ],
)
def test_parent_and_ieds_rules_are_quoted_from_captures(source_id, quote):
    assert quote in source_text(source_id)


@pytest.mark.parametrize("count", [1, 2])
def test_parent_hand_reference_one_or_two_entitled_parents(count):
    result = _family(_survivor(), [_parent(f"p{i}") for i in range(count)])
    amount = F(825 if count == 1 else 750)
    for row in result.beneficiaries:
        assert row.entitled and row.subject_to_family_maximum
        assert row.original_benefit == row.age_adjusted_rate == amount
        assert row.auxiliary_payable == amount
        assert row.whole_dollar_auxiliary == int(amount)
    assert result.record_total == amount * count


def test_parent_hand_reference_single_parent_and_child_maximum():
    result = _family(
        _survivor(maximum=F(1500)),
        [_parent(), g.Beneficiary("c", g.Role.CHILD)],
    )
    rows = _rows(result)
    assert rows["p"].original_benefit == F(825)
    assert rows["c"].original_benefit == F(750)
    assert rows["p"].auxiliary_payable == F("785.7")
    assert rows["c"].auxiliary_payable == F("714.2")
    assert result.record_total == F("1499.9")
    assert result.record_total_whole_dollars == 1499


@pytest.mark.parametrize(
    ("own_dib", "parent_pay", "other_pay"),
    [(600, F(0), F(750)), (1000, F(0), F(750)), (100, F(400), F(550))],
)
def test_parent_hand_reference_dib_retains_technical_entitlement(
    own_dib, parent_pay, other_pay
):
    result = _family(
        _survivor(maximum=F(1500)),
        [
            _parent(
                "p1",
                own_benefit=g.OwnBenefit(
                    g.OwnBenefitKind.DISABILITY, F(own_dib)
                ),
            ),
            _parent("p2"),
            g.Beneficiary("c", g.Role.CHILD),
        ],
    )
    rows = _rows(result)
    assert rows["p1"].entitled
    assert rows["p1"].original_benefit == rows["p2"].original_benefit == F(750)
    assert rows["p1"].standard_rate == rows["p2"].standard_rate == F(500)
    assert rows["p1"].auxiliary_payable == parent_pay
    assert (
        rows["p2"].auxiliary_payable
        == rows["c"].auxiliary_payable
        == other_pay
    )
    assert result.record_total == F(1500)


def test_parent_entitlement_compares_the_reduced_rib_not_its_pia():
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE, F(1000), reduction_months=36, birth_year=1935
    )
    row = _family(_survivor(), [_parent(own_benefit=own)]).beneficiaries[0]
    assert row.entitled
    assert row.own_benefit == F(800)
    assert row.original_benefit == F(825)
    assert row.auxiliary_payable == F(25)


def test_parent_entitlement_threshold_is_the_dime_rounded_original_benefit():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(825))
    result = _family(
        _survivor(F("1000.1"), F(1750)),
        [_parent("high", own_benefit=own), _parent("other")],
    )
    rows = _rows(result)
    assert not rows["high"].entitled
    assert rows["high"].auxiliary_payable == 0
    assert rows["other"].original_benefit == F(825)
    assert rows["other"].auxiliary_payable == F(825)


@given(st.integers(0, 1_000_000), st.integers(1, 2))
@settings(deadline=None)
def test_parent_original_benefit_uses_the_entitled_count_and_dime_floor(
    dimes, count
):
    pia = F(dimes, 10)
    expected = F(dimes * (825 if count == 1 else 750) // 1000, 10)
    assert (
        g.original_benefit(
            g.Role.PARENT, g.FamilyKind.SURVIVOR, pia, parent_count=count
        )
        == expected
    )
    result = _family(
        _survivor(pia, pia * 2), [_parent(f"p{i}") for i in range(count)]
    )
    assert all(
        row.auxiliary_payable == expected for row in result.beneficiaries
    )


@given(st.integers(100, 1_000_000), st.integers(0, 100))
@settings(deadline=None)
def test_two_potential_parents_refuse_the_own_rib_entitlement_cycle(
    dimes, position
):
    low, high = dimes * 750 // 1000, dimes * 825 // 1000
    own_dimes = low + (high - low - 1) * position // 100
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(own_dimes, 10))
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(
            _survivor(F(dimes, 10), F(dimes, 5)),
            [_parent("p1", own_benefit=own), _parent("p2")],
        )
    assert caught.value.reason is g.UnsupportedReason.PARENT_BENEFIT


@given(st.integers(100, 1_000_000))
@settings(deadline=None)
def test_parent_own_rib_outside_the_ambiguity_band_has_decided_entitlement(
    dimes,
):
    pia = F(dimes, 10)
    low, high = dimes * 750 // 1000, dimes * 825 // 1000
    state = _survivor(pia, pia * 2)
    below = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(low - 1, 10))
    high_rib = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(high, 10))
    two = _rows(
        _family(state, [_parent("p1", own_benefit=below), _parent("p2")])
    )
    assert two["p1"].entitled and two["p2"].entitled
    assert two["p2"].original_benefit == F(low, 10)
    one = _rows(
        _family(state, [_parent("p1", own_benefit=high_rib), _parent("p2")])
    )
    assert not one["p1"].entitled and one["p2"].entitled
    assert one["p2"].original_benefit == F(high, 10)


@given(st.integers(0, 100_000), st.integers(1, 2), st.integers(0, 5))
@settings(deadline=None)
def test_parent_maximum_bounds_proportions_dimes_and_order(
    dimes, parents, children
):
    pia = F(dimes, 10)
    maximum = g.floor_dime(pia * F(3, 2))
    state = _survivor(pia, maximum)
    members = [_parent(f"p{i}") for i in range(parents)] + [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    forward, reverse = _family(state, members), _family(state, members[::-1])
    assert _rows(forward) == _rows(reverse)
    assert forward.record_total == reverse.record_total <= maximum
    total_ob = sum(
        (row.original_benefit for row in forward.beneficiaries), F(0)
    )
    for row in forward.beneficiaries:
        assert row.subject_to_family_maximum
        assert (
            row.auxiliary_payable
            == row.age_adjusted_rate
            == row.family_maximum_rate
        )
        assert (row.auxiliary_payable * 10).denominator == 1
        assert row.whole_dollar_auxiliary == int(row.auxiliary_payable)
        if total_ob:
            exact = min(
                row.original_benefit, row.original_benefit * maximum / total_ob
            )
            assert exact - F(1, 10) < row.family_maximum_rate <= exact
    added = _family(state, [*members, g.Beneficiary("added", g.Role.CHILD)])
    for bid, row in _rows(forward).items():
        assert _rows(added)[bid].auxiliary_payable <= row.auxiliary_payable


@given(st.integers(0, 100_000), st.integers(0, 5))
@settings(deadline=None)
def test_adding_a_second_parent_never_raises_existing_rates(dimes, children):
    pia = F(dimes, 10)
    state = _survivor(pia, g.floor_dime(pia * F(3, 2)))
    members = [_parent()] + [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    before, after = _family(state, members), _family(
        state, [*members, _parent("second")]
    )
    for bid, row in _rows(before).items():
        assert _rows(after)[bid].auxiliary_payable <= row.auxiliary_payable


@given(
    st.integers(0, 100_000),
    st.integers(0, 100_000),
    st.sampled_from(list(g.OwnBenefitKind)),
    st.integers(0, 3),
)
@settings(deadline=None)
def test_parent_dual_entitlement_never_goes_below_the_own_benefit(
    dimes, own_dimes, own_kind, children
):
    pia = F(dimes, 10)
    own = g.OwnBenefit(own_kind, F(own_dimes, 10))
    members = [_parent(own_benefit=own)] + [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    result = _family(_survivor(pia, g.floor_dime(pia * F(3, 2))), members)
    row = result.beneficiaries[0]
    if own_kind is g.OwnBenefitKind.DISABILITY:
        assert row.entitled
    assert row.auxiliary_payable >= 0
    assert row.own_benefit + row.auxiliary_payable == max(
        row.own_benefit, row.age_adjusted_rate
    )
    assert (
        sum((b.counted_against_maximum for b in result.beneficiaries), F(0))
        <= result.family_maximum
    )


def test_more_than_two_parent_candidates_is_a_coverage_refusal():
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(_survivor(), [_parent(f"p{i}") for i in range(3)])
    assert caught.value.reason is g.UnsupportedReason.PARENT_BENEFIT


def test_parent_input_errors_precede_the_entitlement_ambiguity():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(780))
    p = _parent("p1", own_benefit=own)
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        _family(_survivor(), [p, p, _parent("p2")])
    with pytest.raises(g.InvalidFamilyInput):
        _parent(reduction_months=1)


@pytest.mark.parametrize("months,expected", [(0, F(500)), (36, F(375))])
def test_ieds_hand_reference_has_no_worker_payment(months, expected):
    result = _family(_ieds(), [_divorce(reduction_months=months)])
    row = result.beneficiaries[0]
    assert result.worker_benefit is None
    assert result.whole_dollar_worker is None
    assert row.original_benefit == F(500)
    assert not row.subject_to_family_maximum
    assert row.counted_against_maximum == 0
    assert row.auxiliary_payable == result.record_total == expected


def test_ieds_four_divorced_spouses_are_outside_a_binding_maximum():
    """Invented: four half-PIA benefits sum to 2000, outside the 1500 max."""
    result = _family(
        _ieds(maximum=F(1500)), [_divorce(f"d{i}") for i in range(4)]
    )
    assert not result.family_maximum_binding
    assert result.record_total == F(2000)
    assert all(
        row.auxiliary_payable == F(500)
        and not row.subject_to_family_maximum
        and row.counted_against_maximum == 0
        for row in result.beneficiaries
    )


@pytest.mark.parametrize(
    "own_first,expected", [(True, F(225)), (False, F(215))]
)
def test_ieds_hand_reference_dual_entitlement_uses_the_spouse_method(
    own_first, expected
):
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(200), reduction_months=36)
    result = _family(
        _ieds(),
        [
            _divorce(
                reduction_months=36,
                own_benefit=own,
                own_benefit_first=own_first,
            )
        ],
    )
    row = result.beneficiaries[0]
    assert row.own_benefit == F(160)
    assert row.auxiliary_payable == result.record_total == expected


@given(st.integers(0, 100_000), st.integers(0, 60), st.integers(0, 60))
@settings(deadline=None)
def test_ieds_is_outside_the_maximum_and_other_divorced_spouses(
    dimes, months, other_months
):
    pia = F(dimes, 10)
    state = _ieds(pia, g.floor_dime(pia * F(3, 2)))
    other_maximum = _ieds(pia, g.floor_dime(pia * F(7, 4)))
    person = _divorce(reduction_months=months)
    first = _family(state, [person])
    second = _family(
        other_maximum,
        [person, _divorce("other", reduction_months=other_months)],
    )
    assert _rows(first)["d"] == _rows(second)["d"]
    assert (
        not first.family_maximum_binding and not second.family_maximum_binding
    )
    assert first.worker_benefit is second.worker_benefit is None
    assert all(
        not row.subject_to_family_maximum for row in second.beneficiaries
    )


@given(
    st.integers(0, 100_000),
    st.integers(0, 100_000),
    st.integers(0, 60),
    st.integers(0, 60),
    st.booleans(),
)
@settings(deadline=None)
def test_ieds_auxiliary_rates_match_the_entitled_worker_path_exactly(
    dimes, own_dimes, months, own_months, own_first
):
    """Zero tolerance: existing divorced-spouse rules govern both paths."""
    pia = F(dimes, 10)
    maximum = g.floor_dime(pia * F(3, 2))
    person = _divorce(
        reduction_months=months,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(own_dimes, 10),
            reduction_months=own_months,
        ),
        own_benefit_first=own_first,
    )
    entitled = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        maximum,
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
    )
    reference = _family(entitled, [person])
    actual = _family(_ieds(pia, maximum), [person])
    assert _rows(actual) == _rows(reference)
    assert actual.worker_benefit is None


@given(st.integers(0, 100_000))
@settings(deadline=None)
def test_ieds_january_1985_payment_boundary(dimes):
    pia = F(dimes, 10)
    state = _ieds(pia, pia * 2)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, [_divorce()], g.YearMonth(1984, 12))
    assert (
        caught.value.reason is g.UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE
    )
    assert _family(
        state, [_divorce()], g.YearMonth(1985, 1)
    ).record_total == g.floor_dime(pia / 2)


@given(st.integers(0, 100_000))
@settings(deadline=None)
def test_ieds_worker_wep_december_2023_january_2024_boundary(dimes):
    pia = F(dimes, 10)
    state = _ieds(
        pia,
        pia * 2,
        conditions={g.RecordCondition.WINDFALL_ELIMINATION_PROVISION},
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, [_divorce()], g.YearMonth(2023, 12))
    assert (
        caught.value.reason is g.UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE
    )
    result = _family(state, [_divorce()], g.YearMonth(2024, 1))
    assert result.record_total == g.floor_dime(pia / 2)


@pytest.mark.parametrize(
    "month", [g.YearMonth(2023, 12), g.YearMonth(2024, 1)]
)
def test_ordinary_record_wep_pia_is_the_callers_responsibility(month):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(700),
        F(1050),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(700)),
        conditions={g.RecordCondition.WINDFALL_ELIMINATION_PROVISION},
    )
    result = _family(state, [g.Beneficiary("c", g.Role.CHILD)], month)
    assert result.worker_benefit == F(700)
    assert result.beneficiaries[0].auxiliary_payable == F(350)


@pytest.mark.parametrize(
    "role", [g.Role.CHILD, g.Role.SPOUSE, g.Role.SPOUSE_CHILD_IN_CARE]
)
def test_ieds_only_accepts_divorced_spouse_beneficiaries(role):
    with pytest.raises(g.InvalidFamilyInput):
        _family(
            _ieds(),
            [g.Beneficiary("not-divorced", role)],
            g.YearMonth(1984, 12),
        )


@pytest.mark.parametrize(
    "kind", [g.FamilyKind.SURVIVOR, g.FamilyKind.DISABILITY]
)
def test_ieds_only_accepts_retirement_records(kind):
    state = g.RecordState(
        kind,
        F(1000),
        F(1750),
        widow_drc_savings_clause=False,
        conditions={g.RecordCondition.WORKER_NOT_ENTITLED},
    )
    with pytest.raises(g.InvalidFamilyInput):
        _family(state, [g.Beneficiary("c", g.Role.CHILD)])


@pytest.mark.parametrize("hypothetical_worker", [False, True])
def test_household_unclaimed_worker_can_receive_parent_benefits_elsewhere(
    hypothetical_worker,
):
    worker = (
        g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000))
        if hypothetical_worker
        else None
    )
    records = {
        "unclaimed": g.HouseholdRecord(
            "p", _ieds(worker=worker), [_divorce()]
        ),
        "dead-child": g.HouseholdRecord("dead", _survivor(), [_parent("p")]),
    }
    result = g.household_benefits(records, payment_month=NOW, params=PARAMS)
    assert result.records["unclaimed"].worker_benefit is None
    assert result.records["unclaimed"].record_total == F(500)
    assert result.records["dead-child"].record_total == F(825)
    assert result.record_total == F(1325)


def test_household_parent_own_rib_is_counted_once():
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE, F(1000), reduction_months=36, birth_year=1935
    )
    records = {
        "own": g.HouseholdRecord(
            "p",
            g.RecordState(
                g.FamilyKind.RETIREMENT, F(1000), F(1750), worker=own
            ),
        ),
        "dead-child": g.HouseholdRecord(
            "dead", _survivor(), [_parent(own_benefit=own)]
        ),
    }
    result = g.household_benefits(records, payment_month=NOW, params=PARAMS)
    assert result.records["own"].record_total == F(800)
    assert result.records["dead-child"].record_total == F(25)
    assert result.record_total == F(825)


def test_parent_and_ieds_refusals_remain_in_the_denominator():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(780))
    outcomes = [
        g.evaluate_family(
            "parent-cycle",
            2,
            lambda: _family(
                _survivor(), [_parent(own_benefit=own), _parent("p2")]
            ),
        ),
        g.evaluate_family(
            "ieds-old",
            3,
            lambda: _family(_ieds(), [_divorce()], g.YearMonth(1984, 12)),
        ),
        g.evaluate_family(
            "parent-supported", 4, lambda: _family(_survivor(), [_parent()])
        ),
    ]
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.unsupported_rows, counts.supported_rows) == (
        3,
        2,
        1,
    )
    assert counts.weight == F(9)
    assert counts.unsupported_by_reason[
        g.UnsupportedReason.PARENT_BENEFIT
    ] == (1, F(2))
    assert counts.unsupported_by_reason[
        g.UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE
    ] == (1, F(3))
