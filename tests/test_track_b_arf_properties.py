"""R3 ARF Hypothesis invariants and exact shared-surface differentials.

Verification class: statutory conformance. All histories are invented.
G and ARF share exact age-reduction semantics, so tolerance is zero.
Widow(er)'s age-62 adjustment is the intended exception to FRA-only timing.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_arf import months, rib_claim
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
kinds = st.sampled_from(list(a.ARFBenefitKind))
amounts = st.integers(0, 45000).map(lambda cents: F(cents, 10))


def claim_for(kind, amount=F(1300)):
    return a.ARFClaim(
        kind,
        date(1962, 1, 2),
        g.YearMonth(2022 if kind is a.ARFBenefitKind.WIDOW else 2024, 1),
        amount,
    )


def at_fra(claim):
    return a.apply_arf(
        claim,
        payment_month=a.full_retirement_age_month(
            claim.birth_date, claim.kind, PARAMS
        ),
        params=PARAMS,
    )


@settings(deadline=None)
@given(kinds, amounts, st.integers(0, 84))
def test_arf_is_idempotent_deterministic_and_preserves_original_claim(
    kind, amount, count
):
    claim = claim_for(kind, amount)
    original = at_fra(claim).original_reduction_months
    claim = replace(
        claim,
        full_work_deduction_months=months(
            claim.first_reduction_month, min(count, original)
        ),
    )
    result = at_fra(claim)
    twice = a.apply_arf(
        result, payment_month=result.payment_month, params=PARAMS
    )
    assert twice == result == at_fra(claim)
    assert result.claim.first_reduction_month == claim.first_reduction_month
    assert result.original_reduction_months == original


@settings(deadline=None)
@example(a.ARFBenefitKind.RIB, F(1300), [0], [])
@example(
    a.ARFBenefitKind.RIB,
    F(1300),
    [],
    [a.ARFUnsupportedReason.OTHER_SUSPENSION],
)
@given(
    kinds,
    amounts,
    st.lists(st.integers(-20, 110), max_size=100),
    st.lists(st.sampled_from(list(a.ARFUnsupportedReason)), max_size=5),
)
def test_iterator_claim_evaluation_preserves_results_and_refusals(
    kind, amount, offsets, conditions
):
    """Every supported or refused iterator claim has stable meaning."""
    base_claim = claim_for(kind, amount)
    base = base_claim.first_reduction_month.year * 12
    supplied = [
        g.YearMonth((base + i) // 12, (base + i) % 12 + 1) for i in offsets
    ]
    category = {
        a.ARFBenefitKind.RIB: "simultaneous_dib_months",
        a.ARFBenefitKind.SPOUSE: "child_in_care_months",
        a.ARFBenefitKind.WIDOW: "mother_father_rate_months",
    }[kind]
    claim = replace(
        base_claim,
        full_work_deduction_months=iter(supplied),
        partial_work_deduction_months=iter(supplied),
        **{category: iter(supplied)},
        nonentitlement_months=iter(
            supplied if kind is not a.ARFBenefitKind.RIB else []
        ),
        conditions=iter(conditions),
    )
    canonical = replace(
        base_claim,
        full_work_deduction_months=frozenset(supplied),
        partial_work_deduction_months=frozenset(supplied),
        **{category: frozenset(supplied)},
        nonentitlement_months=frozenset(
            supplied if kind is not a.ARFBenefitKind.RIB else []
        ),
        conditions=frozenset(conditions),
    )
    outcomes = [
        a.evaluate_arf(str(index), F(1), lambda value=value: at_fra(value))
        for index, value in enumerate((claim, claim, canonical))
    ]
    first, second, expected = outcomes
    assert first.supported == second.supported == expected.supported
    if first.supported:
        assert first.benefits == second.benefits == expected.benefits
        snapshotted_result = replace(
            first.benefits,
            crediting_months=iter(first.benefits.crediting_months),
        )
        assert snapshotted_result == first.benefits
        assert (
            frozenset(snapshotted_result.crediting_months)
            == frozenset(snapshotted_result.crediting_months)
            == first.benefits.crediting_months
        )
    else:
        assert (
            first.unsupported.reason
            is second.unsupported.reason
            is expected.unsupported.reason
        )
        assert first.unsupported.detail == second.unsupported.detail
    counts = a.count_arf_outcomes(outcomes[:2])
    assert counts.rows == counts.weight == 2
    assert (
        counts.unsupported_rows
        == counts.unsupported_weight
        == (0 if first.supported else 2)
    )


@settings(deadline=None)
@given(kinds, st.lists(st.integers(-20, 110), max_size=100))
def test_credit_bounds_window_and_order_independence(kind, offsets):
    claim = claim_for(kind)
    original = at_fra(claim).original_reduction_months
    first = claim.first_reduction_month
    base = first.year * 12 + first.month - 1
    supplied = [
        g.YearMonth((base + i) // 12, (base + i) % 12 + 1) for i in offsets
    ]
    result = at_fra(replace(claim, full_work_deduction_months=supplied))
    reversed_result = at_fra(
        replace(claim, full_work_deduction_months=list(reversed(supplied)))
    )
    assert result == reversed_result
    assert len(result.crediting_months) == len(
        {i for i in offsets if 0 <= i < original}
    )
    assert 0 <= len(result.crediting_months) <= original
    assert (
        result.adjusted_reduction_months + len(result.crediting_months)
        == original
    )
    assert 0 <= result.adjusted_reduction_months <= original


@settings(deadline=None)
@given(kinds, amounts, st.integers(0, 84), st.integers(0, 84))
def test_more_credits_never_lower_benefit_or_nominal_factor(
    kind, amount, left, right
):
    claim = claim_for(kind, amount)
    original = at_fra(claim).original_reduction_months
    low, high = sorted((min(left, original), min(right, original)))
    fewer = at_fra(
        replace(
            claim,
            full_work_deduction_months=months(
                claim.first_reduction_month, low
            ),
        )
    )
    more = at_fra(
        replace(
            claim,
            full_work_deduction_months=months(
                claim.first_reduction_month, high
            ),
        )
    )
    assert more.benefit >= fewer.benefit
    assert more.whole_dollar_benefit >= fewer.whole_dollar_benefit
    assert more.factor >= fewer.factor
    assert more.adjusted_reduction_months <= fewer.adjusted_reduction_months


@settings(deadline=None)
@given(kinds, amounts, st.integers(0, 84))
def test_partial_deduction_equals_full_credit_and_duplicate_categories_do_not_add(
    kind, amount, count
):
    claim = claim_for(kind, amount)
    original = at_fra(claim).original_reduction_months
    credited = months(claim.first_reduction_month, min(count, original))
    full = at_fra(replace(claim, full_work_deduction_months=credited))
    partial = at_fra(replace(claim, partial_work_deduction_months=credited))
    both = at_fra(
        replace(
            claim,
            full_work_deduction_months=credited,
            partial_work_deduction_months=credited,
        )
    )
    assert full.benefit == partial.benefit == both.benefit
    assert (
        full.adjusted_reduction_months
        == partial.adjusted_reduction_months
        == both.adjusted_reduction_months
    )
    assert (
        full.crediting_months
        == partial.crediting_months
        == both.crediting_months
    )
    if kind is a.ARFBenefitKind.RIB:
        simultaneous_dib = at_fra(
            replace(claim, simultaneous_dib_months=credited)
        )
        assert simultaneous_dib.benefit == full.benefit
        assert simultaneous_dib.crediting_months == full.crediting_months
        assert (
            simultaneous_dib.adjusted_reduction_months
            == full.adjusted_reduction_months
        )


@settings(deadline=None)
@given(
    st.sampled_from([a.ARFBenefitKind.RIB, a.ARFBenefitKind.SPOUSE]),
    amounts,
    st.integers(0, 59),
)
def test_no_rib_or_spouse_adjustment_before_fra(kind, amount, offset):
    claim = claim_for(kind, amount)
    claim = replace(
        claim,
        full_work_deduction_months=months(claim.first_reduction_month, 60),
    )
    base = (
        claim.first_reduction_month.year * 12
        + claim.first_reduction_month.month
        - 1
    )
    payment = g.YearMonth((base + offset) // 12, (base + offset) % 12 + 1)
    result = a.apply_arf(claim, payment_month=payment, params=PARAMS)
    assert result.crediting_months == frozenset()
    assert result.effective_adjustment_month is None
    assert (
        result.adjusted_reduction_months
        == result.original_reduction_months
        == 60
    )


@settings(deadline=None)
@given(amounts, st.integers(0, 23), st.integers(24, 83))
def test_widow_age62_freezes_credits_until_fra(amount, early, later):
    claim = claim_for(a.ARFBenefitKind.WIDOW, amount)
    base = 2022 * 12
    credited = {
        g.YearMonth((base + i) // 12, (base + i) % 12 + 1)
        for i in (early, later)
    }
    claim = replace(claim, partial_work_deduction_months=credited)
    at62 = a.apply_arf(claim, payment_month=(2024, 1), params=PARAMS)
    before_fra = a.apply_arf(claim, payment_month=(2028, 12), params=PARAMS)
    fra = at_fra(claim)
    assert at62.crediting_months == before_fra.crediting_months
    assert len(at62.crediting_months) == 1
    assert at62.benefit == before_fra.benefit <= fra.benefit
    assert len(fra.crediting_months) == 2


@settings(deadline=None)
@given(kinds, amounts, st.integers(0, 84))
def test_zero_credits_matches_g_exactly_and_remaining_months_differential(
    kind, amount, count
):
    claim = claim_for(kind, amount)
    original = at_fra(claim).original_reduction_months
    claim = replace(
        claim,
        full_work_deduction_months=months(
            claim.first_reduction_month, min(count, original)
        ),
    )
    result = at_fra(claim)
    rf = result.adjusted_reduction_months
    if kind is a.ARFBenefitKind.RIB:
        expected = g.worker_age_adjusted(amount, rf, 0, None, PARAMS)[0]
    elif kind is a.ARFBenefitKind.SPOUSE:
        expected = g.spouse_age_reduced(amount, rf, PARAMS)
    else:
        expected = g.survivor_age_reduced(
            amount,
            rf,
            g.widow_reduction_period_months(claim.birth_date),
            PARAMS,
        )
    assert result.benefit == expected  # tolerance zero, exact Fractions
    assert result.whole_dollar_benefit == g.whole_dollars(expected)
    assert 0 <= result.benefit <= amount
    assert 0 <= result.factor <= 1
    assert (result.benefit * 10).denominator == 1
    no_credits = at_fra(replace(claim, full_work_deduction_months=frozenset()))
    assert no_credits.adjusted_reduction_months == original
    assert no_credits.crediting_months == frozenset()


@settings(deadline=None)
@given(st.dates(min_value=date(1938, 1, 1), max_value=date(2000, 12, 31)))
def test_fra_calendar_differential_with_original_cohort_schedule(birth):
    """Independent month assembly; same R1/G parameter schedule, zero tolerance."""
    cohort = birth.year - int(birth.month == 1 and birth.day == 1)
    age = PARAMS.fra_months(cohort)
    total = birth.year * 12 + birth.month - 1 + age
    expected = g.YearMonth(total // 12, total % 12 + 1)
    if birth.day == 1:
        total -= 1
        expected = g.YearMonth(total // 12, total % 12 + 1)
    assert (
        a.full_retirement_age_month(birth, a.ARFBenefitKind.RIB, PARAMS)
        == expected
    )
    assert (
        a.full_retirement_age_month(birth, a.ARFBenefitKind.SPOUSE, PARAMS)
        == expected
    )


@settings(deadline=None)
@given(st.integers(0, 100), st.integers(0, 100))
def test_refusal_denominator_keeps_every_weight(
    supported_weight, unsupported_weight
):
    supported = a.evaluate_arf(
        "supported", F(supported_weight), lambda: at_fra(rib_claim())
    )
    refused = a.evaluate_arf(
        "refused",
        F(unsupported_weight),
        lambda: at_fra(
            rib_claim(conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION})
        ),
    )
    denominator = a.count_arf_outcomes([supported, refused])
    assert (
        denominator.rows
        == denominator.supported_rows + denominator.unsupported_rows
        == 2
    )
    assert denominator.weight == F(supported_weight + unsupported_weight)
    assert (
        denominator.weight
        == denominator.supported_weight + denominator.unsupported_weight
    )


@settings(deadline=None)
@given(kinds, st.integers(1, 120))
def test_invalid_age_precedes_any_disabled_widow_coverage_refusal(
    kind, months_too_early
):
    birth = date(1960, 1, 2)
    minimum = 600 if kind is a.ARFBenefitKind.WIDOW else 744
    first_index = 1960 * 12 + minimum - months_too_early
    first = g.YearMonth(first_index // 12, first_index % 12 + 1)
    claim = a.ARFClaim(
        kind,
        birth,
        first,
        F(1000),
        conditions={a.ARFUnsupportedReason.DISABLED_WIDOW},
    )
    with pytest.raises(g.InvalidFamilyInput):
        a.apply_arf(claim, payment_month=(2027, 1), params=PARAMS)
