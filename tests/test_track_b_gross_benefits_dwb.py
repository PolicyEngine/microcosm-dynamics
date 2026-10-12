"""DWB statutory conformance on invented exact reference families.

Verification class: statutory conformance. These cases admit gross rates
for the supported disabled-widow configurations, with no population,
behavioral or forecast claim. RS 00615.310B.1/B.3 fix the reduction at
28.5 percent from January 1984, including earlier entitlements. The
reduction is rounded up to a dime under 402(q)(8) and RS 00615.301.

The captures contain no numerical DWB worked example. Hand references:
1000 - 285 = 715; 1000.10 - ceil_dime(285.0285) = 715.00. With a PIA of
1000, maximum 1875, and two children, original rates 1000/750/750 share
the maximum as 750/562.50/562.50. DWB is 750 - ceil_dime(213.75) =
536.20; the record total is 1661.20 and the whole-dollar total is 1660.
For an OB basis of 1400, the age-reduced rate is 1001; a RIB-LIM of
max(800, .825 * 1000) subsequently limits payment to 825.
"""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

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


def _survivor(pia=F(1000), maximum=F(1750), **kwargs):
    return g.RecordState(g.FamilyKind.SURVIVOR, pia, maximum, **kwargs)


def _dwb(**kwargs):
    return g.Beneficiary("w", g.Role.DISABLED_WIDOW, **kwargs)


def _fixed_reduced_dimes(rate_dimes):
    """Independent integer reference: ceiling of .285 times OB in dimes."""
    return rate_dimes - (rate_dimes * 285 + 999) // 1000


@pytest.mark.parametrize(
    ("basis", "expected", "whole"),
    [
        (F(1000), F(715), 715),
        (F("1000.1"), F(715), 715),
        (F("1000.2"), F("715.1"), 715),
    ],
)
def test_dwb_hand_reference_and_round_up(basis, expected, whole):
    result = _family(_survivor(), [_dwb(original_benefit_basis=basis)])
    row = result.beneficiaries[0]
    assert row.original_benefit == basis
    assert row.family_maximum_rate == basis
    assert row.age_adjusted_rate == row.auxiliary_payable == expected
    assert row.whole_dollar_auxiliary == whole
    assert result.record_total == expected
    assert result.record_total_whole_dollars == whole


def test_dwb_hand_reference_reduces_the_maximum_share():
    result = _family(
        _survivor(maximum=F(1875)),
        [
            _dwb(),
            g.Beneficiary("c1", g.Role.CHILD),
            g.Beneficiary("c2", g.Role.CHILD),
        ],
    )
    rows = {row.beneficiary_id: row for row in result.beneficiaries}
    assert result.family_maximum_binding
    assert rows["w"].original_benefit == F(1000)
    assert rows["w"].family_maximum_rate == F(750)
    assert rows["w"].auxiliary_payable == F("536.2")
    for child in ("c1", "c2"):
        assert rows[child].original_benefit == F(750)
        assert rows[child].auxiliary_payable == F("562.5")
    assert result.record_total == F("1661.2")
    assert result.record_total_whole_dollars == 1660


def test_dwb_hand_reference_rib_lim_follows_the_age_reduction():
    state = _survivor(rib_lim_benefit=F(800))
    result = _family(state, [_dwb(original_benefit_basis=F(1400))])
    row = result.beneficiaries[0]
    assert row.family_maximum_rate == F(1400)
    assert _fixed_reduced_dimes(14_000) == 10_010
    assert row.age_adjusted_rate == row.auxiliary_payable == F(825)
    # An ordinary OB yields 715, so the same 825 limit has no effect.
    assert _family(state, [_dwb()]).record_total == F(715)


@given(st.integers(0, 1_000_000))
@settings(deadline=None)
def test_dwb_fixed_reduction_bounds_dimes_and_whole_dollars(dimes):
    pia = F(dimes, 10)
    result = _family(_survivor(pia, pia * 2), [_dwb()])
    row = result.beneficiaries[0]
    expected = F(_fixed_reduced_dimes(dimes), 10)
    assert row.auxiliary_payable == expected
    reduction = pia - row.auxiliary_payable
    assert pia * F(285, 1000) <= reduction < pia * F(285, 1000) + F(1, 10)
    assert 0 <= row.auxiliary_payable <= row.family_maximum_rate
    assert (row.auxiliary_payable * 10).denominator == 1
    assert row.whole_dollar_auxiliary == _fixed_reduced_dimes(dimes) // 10


@given(st.integers(0, 1_000_000), st.integers(0, 1_000_000))
@settings(deadline=None)
def test_dwb_fixed_rate_is_monotone_in_the_original_benefit(a, b):
    low, high = sorted((F(a, 10), F(b, 10)))
    lower = _family(_survivor(low, low * 2), [_dwb()])
    higher = _family(_survivor(high, high * 2), [_dwb()])
    assert lower.record_total <= higher.record_total


@given(st.integers(0, 1_000_000), st.integers(50, 59))
@settings(deadline=None)
def test_dwb_has_no_additional_reduction_for_pre_60_months(dimes, age):
    pia = F(dimes, 10)
    state = _survivor(pia, pia * 2)
    at_50 = _family(state, [_dwb(birth_year=1980)], g.YearMonth(2030, 12))
    other = _family(
        state, [_dwb(birth_year=2030 - age)], g.YearMonth(2030, 12)
    )
    assert at_50.record_total == other.record_total


@given(
    st.integers(0, 1_000_000),
    st.integers(60, 84),
)
@settings(deadline=None)
def test_dwb_matches_the_full_period_widow_reduction_exactly(dimes, period):
    """Zero tolerance: both semantics reduce OB by exactly 28.5 percent."""
    pia = F(dimes, 10)
    result = _family(_survivor(pia, pia * 2), [_dwb()])
    assert result.record_total == g.survivor_age_reduced(
        pia, period, period, PARAMS
    )


@given(st.integers(0, 100_000), st.integers(0, 7), st.booleans())
@settings(deadline=None)
def test_dwb_family_maximum_proportions_and_order(dimes, children, reverse):
    pia = F(dimes, 10)
    maximum = g.floor_dime(pia * F(7, 4))
    state = _survivor(pia, maximum)
    members = [_dwb()] + [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    ordered = _family(state, members)
    permuted = _family(state, list(reversed(members)) if reverse else members)

    def as_rows(result):
        return {row.beneficiary_id: row for row in result.beneficiaries}

    assert as_rows(ordered) == as_rows(permuted)
    assert ordered.record_total == permuted.record_total
    assert (
        sum(
            (row.counted_against_maximum for row in ordered.beneficiaries),
            F(0),
        )
        <= maximum
    )
    assert ordered.record_total <= maximum
    total_ob = sum(
        (row.original_benefit for row in ordered.beneficiaries), F(0)
    )
    for row in ordered.beneficiaries:
        assert row.subject_to_family_maximum
        assert 0 <= row.auxiliary_payable <= row.family_maximum_rate
        if total_ob:
            exact_share = min(
                row.original_benefit, row.original_benefit * maximum / total_ob
            )
            assert (
                exact_share - F(1, 10) < row.family_maximum_rate <= exact_share
            )
        if row.role is g.Role.DISABLED_WIDOW:
            rate_dimes = int(row.family_maximum_rate * 10)
            assert row.auxiliary_payable == F(
                _fixed_reduced_dimes(rate_dimes), 10
            )


@given(st.integers(0, 100_000), st.integers(0, 7))
@settings(deadline=None)
def test_adding_a_child_never_raises_the_dwb_rate(dimes, children):
    pia = F(dimes, 10)
    state = _survivor(pia, g.floor_dime(pia * F(7, 4)))
    members = [_dwb()] + [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    before = _family(state, members).beneficiaries[0]
    after = _family(
        state, members + [g.Beneficiary("added", g.Role.CHILD)]
    ).beneficiaries[0]
    assert after.family_maximum_rate <= before.family_maximum_rate
    assert after.auxiliary_payable <= before.auxiliary_payable
    assert after.whole_dollar_auxiliary <= before.whole_dollar_auxiliary


@given(st.integers(0, 100_000), st.integers(0, 200_000))
@settings(deadline=None)
def test_dwb_rib_lim_is_applied_after_fixed_reduction(dimes, limit_dimes):
    pia, basis = F(dimes, 10), F(dimes, 5)
    limit = F(limit_dimes, 10)
    state = _survivor(pia, basis, rib_lim_benefit=limit)
    result = _family(state, [_dwb(original_benefit_basis=basis)])
    age_reduced = F(_fixed_reduced_dimes(dimes * 2), 10)
    limit_floor = F(dimes * 825 // 1000, 10)
    assert result.record_total == min(age_reduced, max(limit, limit_floor))


@given(st.integers(0, 100_000))
@settings(deadline=None)
def test_dwb_december_1983_refusal_and_january_1984_payment(dimes):
    pia = F(dimes, 10)
    state = _survivor(pia, pia * 2)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, [_dwb()], g.YearMonth(1983, 12))
    assert caught.value.reason is g.UnsupportedReason.DISABLED_WIDOW_UNDER_60
    assert caught.value.reason.value == "disabled_widow_before_1984"
    result = _family(state, [_dwb()], g.YearMonth(1984, 1))
    assert result.record_total == F(_fixed_reduced_dimes(dimes), 10)


@pytest.mark.parametrize("kind", list(g.OwnBenefitKind))
def test_dwb_own_rib_and_dib_sequences_remain_refused(kind):
    own = g.OwnBenefit(kind, F(100), birth_year=1960)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(_survivor(), [_dwb(own_benefit=own, birth_year=1960)])
    assert caught.value.reason is g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE


@pytest.mark.parametrize("month", [g.YearMonth(1983, 12), NOW])
def test_dwb_input_errors_precede_the_historical_refusal(month):
    member = _dwb()
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        _family(_survivor(), [member, member], month)


@pytest.mark.parametrize(
    "kwargs", [{"reduction_months": 1}, {"reduction_period_months": 60}]
)
def test_dwb_does_not_accept_arf_or_extra_reduction_inputs(kwargs):
    with pytest.raises(g.InvalidFamilyInput):
        _dwb(**kwargs)


@pytest.mark.parametrize(
    "kind", [g.FamilyKind.RETIREMENT, g.FamilyKind.DISABILITY]
)
def test_dwb_is_invalid_on_living_worker_records(kind):
    worker = (
        g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000))
        if kind is g.FamilyKind.RETIREMENT
        else None
    )
    state = g.RecordState(kind, F(1000), F(1750), worker=worker)
    with pytest.raises(g.InvalidFamilyInput):
        _family(state, [_dwb()])


def test_dwb_ob_basis_cannot_be_less_than_the_death_pia():
    with pytest.raises(g.InvalidFamilyInput):
        _family(_survivor(), [_dwb(original_benefit_basis=F(999))])


def test_dwb_outcome_keeps_the_historical_refusal_in_the_denominator():
    state = _survivor()
    months = (g.YearMonth(1983, 12), g.YearMonth(1984, 1))
    outcomes = [
        g.evaluate_family(
            str(month),
            1,
            lambda month=month: _family(state, [_dwb()], month),
        )
        for month in months
    ]
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.supported_rows, counts.unsupported_rows) == (
        2,
        1,
        1,
    )
    assert counts.unsupported_by_reason[
        g.UnsupportedReason.DISABLED_WIDOW_UNDER_60
    ] == (1, F(1))
