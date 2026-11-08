"""R2 Hypothesis invariants over invented record-years only.

Verification class: statutory conformance. Conservation includes the explicit
undistributed sub-dollar residual required by CFR .440's reapportionment
stop; 215(g)'s subsequent whole-dollar check floor is asserted separately.
Every fractional allocation uses that statutory stop. These tests admit no
population, behavioral, or forecast claim.
The cap-boundary fixtures cover both simultaneous first-apportionment caps
and a child cap reached only after the spouse's overflow is reapportioned.
"""

from __future__ import annotations

import dataclasses
import pickle
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b._provenance import _computed, _result_values
from populace_dynamics.track_b.ret_grace import (
    BenefitType,
    GraceMonth,
    GraceYearState,
    grace_year,
)
from populace_dynamics.track_b.ret_params import RETParameters
from tests.test_track_b_ret_ledger import (
    MONTHS,
    PARAMS,
    YEAR,
    beneficiary,
    by_month,
    earnings,
    grace_work,
    higher_earnings_for_excess,
    lower_earnings_for_excess,
    record,
    worker,
)
from tests.track_b_ret_ledger_support import source_text

DIME_RATES = st.integers(1, 30_000).map(lambda value: F(value, 10))
EXCESSES = st.integers(0, 50_000)
PROTECTED = st.frozensets(st.integers(1, 12), max_size=12)
SUPPORTED_YEARS = tuple(year for year in PARAMS.years if year >= 2000)


def _apply(record_year, parameters=PARAMS):
    return r.apply_ret_year(record_year, parameters)


def _annual_deduction(result, beneficiary_id):
    return sum(
        (row.deduction for row in result.for_beneficiary(beneficiary_id)), F(0)
    )


@st.composite
def record_years(draw):
    """RET-covered NH and children with varying rates and entitlement."""
    excess = draw(EXCESSES)
    entitled = draw(PROTECTED)
    protected = draw(PROTECTED)
    nh_rates = tuple(draw(st.lists(DIME_RATES, min_size=12, max_size=12)))
    grace, work = grace_work(
        lower_earnings_for_excess(excess), protected, entitled=entitled
    )
    members = [
        beneficiary(
            rate=nh_rates,
            entitled=entitled,
            original_rate=max(nh_rates),
            grace=grace,
            work=work,
        )
    ]
    for index in range(draw(st.integers(0, 4))):
        rates = tuple(draw(st.lists(DIME_RATES, min_size=12, max_size=12)))
        members.append(
            beneficiary(
                f"child{index}",
                rate=rates,
                original_rate=max(rates),
                entitled=draw(PROTECTED),
                benefit_type=BenefitType.CHILD,
            )
        )
    return record(*members)


@settings(max_examples=200, deadline=None)
@given(record_years())
def test_every_month_conserves_exact_money_and_checks_are_floored(case):
    result = _apply(case)
    assert len(result.months) == 12 * len(case.beneficiaries)
    for row in result.months:
        assert row.gross == row.net_due + row.deduction
        assert 0 <= row.deduction <= row.gross
        assert 0 <= row.net_due <= row.gross
        assert row.deduction == row.nh_deduction + row.own_deduction
        assert row.payment == row.net_due.numerator // row.net_due.denominator
        assert row.provisional_net + row.provisional_deduction == row.gross
        assert row.provisional_payment == int(row.provisional_net)


@settings(max_examples=150, deadline=None)
@given(record_years())
def test_exact_final_charges_are_excess_capped_by_chargeable_benefits(case):
    result = _apply(case)
    nh = next(b for b in case.beneficiaries if b.beneficiary_id == "nh")
    chargeable = sum(
        (
            b.gross_rates[month - 1]
            for b in case.beneficiaries
            for month in b.entitled_months
            if month in nh.entitled_months
            and month not in nh.grace.protected_months
        ),
        F(0),
    )
    excess = worker(result).excess
    assert worker(result).charged == min(F(excess), chargeable)
    assert (
        sum(row.nh_deduction for row in result.months)
        == worker(result).charged
        + worker(result).undistributed_subdollar_residual
    )
    assert worker(result).charged + worker(result).uncharged == excess
    assert 0 <= worker(result).charged <= excess
    assert 0 <= worker(result).undistributed_subdollar_residual < 1


@settings(max_examples=150, deadline=None)
@given(record_years())
def test_earlier_chargeable_months_are_exhausted_before_later_months(case):
    result = _apply(case)
    nh = next(b for b in case.beneficiaries if b.beneficiary_id == "nh")
    unexhausted_month_seen = False
    for month in range(1, 13):
        rows = [row for row in result.months if row.month == month]
        available = sum(
            (
                row.gross
                for row in rows
                if month in nh.entitled_months
                and month not in nh.grace.protected_months
            ),
            F(0),
        )
        deducted = sum(row.nh_deduction for row in rows)
        if not available:
            assert deducted == 0
            continue
        if unexhausted_month_seen:
            assert deducted == 0
        if deducted < available:
            unexhausted_month_seen = True


@settings(max_examples=150, deadline=None)
@given(record_years())
def test_crediting_months_come_from_actual_full_or_partial_deductions(case):
    result = _apply(case)
    for b in case.beneficiaries:
        rows = result.for_beneficiary(b.beneficiary_id)
        assert result.crediting_months[b.beneficiary_id] == frozenset(
            row.month for row in rows if row.deduction > 0
        )
        assert result.reconciliation[b.beneficiary_id] == sum(
            row.payment - row.provisional_payment for row in rows
        )


@settings(max_examples=150, deadline=None)
@given(record_years())
def test_equal_estimate_provisional_suspensions_are_full_and_cover_final(case):
    result = _apply(case)
    assert all(
        row.provisional_deduction in (0, row.gross) for row in result.months
    )
    assert sum(row.provisional_deduction for row in result.months) >= sum(
        row.deduction for row in result.months
    )
    assert all(value >= 0 for value in result.reconciliation.values())


@settings(max_examples=150, deadline=None)
@given(record_years(), st.randoms(use_true_random=False))
def test_determinism_and_beneficiary_order_independence(case, rng):
    original = _apply(case)
    assert _apply(case) == original
    shuffled = list(case.beneficiaries)
    rng.shuffle(shuffled)
    reordered = _apply(
        dataclasses.replace(case, beneficiaries=tuple(shuffled))
    )
    assert sorted(
        reordered.months, key=lambda row: (row.beneficiary_id, row.month)
    ) == sorted(
        original.months, key=lambda row: (row.beneficiary_id, row.month)
    )
    assert sorted(
        reordered.workers, key=lambda row: row.beneficiary_id
    ) == sorted(original.workers, key=lambda row: row.beneficiary_id)
    assert reordered.crediting_months == original.crediting_months
    assert reordered.reconciliation == original.reconciliation


@settings(max_examples=150, deadline=None)
@given(DIME_RATES, DIME_RATES, st.integers(0, 10), EXCESSES)
def test_number_holders_excess_is_charged_before_auxiliarys_own(
    nh_rate,
    aux_rate,
    full_months,
    aux_excess,
):
    # Require exact whole-dollar family month totals, so the NH cannot have
    # a simultaneous partial deduction needing part (b)'s readjustment.
    nh_rate = F(int(nh_rate) + 1)
    aux_rate = F(int(aux_rate) + 1)
    nh_excess = (nh_rate + aux_rate) * full_months
    result = _apply(
        record(
            beneficiary(
                rate=nh_rate,
                work=earnings(lower_earnings_for_excess(nh_excess)),
            ),
            beneficiary(
                "spouse",
                rate=aux_rate,
                benefit_type=BenefitType.SPOUSE,
                work=earnings(lower_earnings_for_excess(aux_excess)),
            ),
        )
    )
    nh_rows = by_month(result)
    aux_rows = by_month(result, "spouse")
    for month in range(1, full_months + 1):
        assert nh_rows[month].nh_deduction == nh_rate
        assert aux_rows[month].nh_deduction == aux_rate
        assert aux_rows[month].own_deduction == 0
    for month in range(full_months + 1, 13):
        assert nh_rows[month].deduction == 0
        assert aux_rows[month].nh_deduction == 0
    assert worker(result, "spouse").charged == min(
        F(aux_excess), aux_rate * (12 - full_months)
    )


@settings(max_examples=150, deadline=None)
@given(DIME_RATES, DIME_RATES, DIME_RATES, EXCESSES)
def test_auxiliarys_own_excess_cannot_reduce_any_other_beneficiary(
    nh_rate,
    aux_rate,
    child_rate,
    excess,
):
    nh = beneficiary(rate=nh_rate)
    child = beneficiary(
        "child", rate=child_rate, benefit_type=BenefitType.CHILD
    )
    before = beneficiary(
        "spouse", rate=aux_rate, benefit_type=BenefitType.SPOUSE
    )
    after = dataclasses.replace(
        before, earnings=earnings(lower_earnings_for_excess(excess))
    )
    base = _apply(record(nh, before, child))
    worked = _apply(record(nh, after, child))
    assert worked.for_beneficiary("nh") == base.for_beneficiary("nh")
    assert worked.for_beneficiary("child") == base.for_beneficiary("child")
    assert worker(worked, "spouse").charged == min(F(excess), 12 * aux_rate)


@settings(max_examples=150, deadline=None)
@given(record_years(), DIME_RATES, st.booleans())
def test_excluded_divorced_spouse_leaves_every_existing_deduction_unchanged(
    case,
    divorced_rate,
    prior_rib,
):
    divorced = beneficiary(
        "divorced",
        rate=divorced_rate,
        benefit_type=BenefitType.DIVORCED_SPOUSE,
        nh_entitled_before_divorce=prior_rib,
        divorced_months=frozenset() if prior_rib else MONTHS,
    )
    before = _apply(case)
    after = _apply(
        dataclasses.replace(
            case, beneficiaries=(*case.beneficiaries, divorced)
        )
    )
    for b in case.beneficiaries:
        assert after.for_beneficiary(
            b.beneficiary_id
        ) == before.for_beneficiary(b.beneficiary_id)
    assert all(row.deduction == 0 for row in after.for_beneficiary("divorced"))
    assert worker(after).charged == worker(before).charged


@settings(max_examples=150, deadline=None)
@given(record_years(), EXCESSES, EXCESSES)
def test_each_annual_deduction_is_nondecreasing_in_number_holders_earnings(
    case,
    excess_a,
    excess_b,
):
    low, high = sorted((excess_a, excess_b))
    results = []
    for excess in (low, high):
        members = tuple(
            (
                dataclasses.replace(
                    b,
                    earnings=dataclasses.replace(
                        b.earnings,
                        nese=F(lower_earnings_for_excess(excess)),
                    ),
                )
                if b.beneficiary_id == "nh"
                else b
            )
            for b in case.beneficiaries
        )
        results.append(
            _apply(dataclasses.replace(case, beneficiaries=members))
        )
    for b in case.beneficiaries:
        assert _annual_deduction(
            results[0], b.beneficiary_id
        ) <= _annual_deduction(results[1], b.beneficiary_id)


@settings(max_examples=150, deadline=None)
@given(record_years(), st.integers(1, 50_000), st.integers(1, 50_000))
def test_each_annual_deduction_is_nonincreasing_in_exempt_amount(case, a, b):
    low, high = sorted((a, b))
    original = PARAMS.for_year(YEAR)
    results = []
    for exempt in (low, high):
        changed = dataclasses.replace(
            original,
            lower_exempt_amount=dataclasses.replace(
                original.lower_exempt_amount, value=exempt
            ),
        )
        results.append(
            _apply(
                case, RETParameters({YEAR: changed}, PARAMS.parameter_sha256)
            )
        )
    for member in case.beneficiaries:
        assert _annual_deduction(
            results[0], member.beneficiary_id
        ) >= _annual_deduction(results[1], member.beneficiary_id)


@settings(max_examples=150, deadline=None)
@given(
    DIME_RATES,
    EXCESSES,
    st.integers(1, 12),
    st.lists(st.integers(0, 1_000_000), min_size=12, max_size=12),
)
def test_fra_month_and_later_wages_change_nothing(
    rate, excess, fra, later_wages
):
    before = [F(0)] * 12
    if fra > 1:
        before[0] = higher_earnings_for_excess(excess)
    after = list(before)
    for month in range(fra, 13):
        after[month - 1] = later_wages[month - 1]
    one = _apply(
        record(
            beneficiary(
                rate=rate,
                fra_month=fra,
                work=r.WorkEarnings(wages=tuple(before)),
            )
        )
    )
    two = _apply(
        record(
            beneficiary(
                rate=rate,
                fra_month=fra,
                work=r.WorkEarnings(wages=tuple(after)),
            )
        )
    )
    assert two == one
    assert all(row.deduction == 0 for row in one.months if row.month >= fra)


@settings(max_examples=150, deadline=None)
@given(DIME_RATES, EXCESSES, st.frozensets(st.integers(2, 12), max_size=11))
def test_grace_year_nonservice_months_are_never_charged(
    rate, excess, nonservice
):
    work = earnings(
        lower_earnings_for_excess(excess),
        self_employment_months=MONTHS,
        substantial_service_months=MONTHS - nonservice,
    )
    months = tuple(
        GraceMonth(
            entitled_types=frozenset({BenefitType.RIB}),
            received_types=frozenset({BenefitType.RIB}),
            nonservice=month in nonservice,
        )
        for month in range(1, 13)
    )
    grace = grace_year(YEAR, GraceYearState(), months)
    result = _apply(record(beneficiary(rate=rate, work=work, grace=grace)))
    for row in result.months:
        if row.month in nonservice:
            assert row.deduction == row.provisional_deduction == 0
    chargeable = rate * (12 - len(nonservice))
    assert worker(result).charged == min(F(excess), chargeable)


@settings(max_examples=150, deadline=None)
@given(
    DIME_RATES,
    EXCESSES,
    st.lists(
        st.sampled_from([BenefitType.RIB, BenefitType.DIB]),
        min_size=12,
        max_size=12,
    ),
)
def test_disability_months_are_exempt_but_elected_rib_months_are_tested(
    rate, excess, types
):
    nh = dataclasses.replace(
        beneficiary(
            rate=rate, work=earnings(lower_earnings_for_excess(excess))
        ),
        benefit_types=tuple(types),
    )
    result = _apply(record(nh))
    for row, benefit_type in zip(
        result.for_beneficiary("nh"), types, strict=True
    ):
        if benefit_type is BenefitType.DIB:
            assert row.deduction == row.provisional_deduction == 0
    assert worker(result).charged == min(
        F(excess), rate * types.count(BenefitType.RIB)
    )


@settings(max_examples=150, deadline=None)
@given(
    DIME_RATES, EXCESSES, st.sampled_from([BenefitType.DWB, BenefitType.CDB])
)
def test_disabled_auxiliarys_own_excess_never_reduces_disabled_benefit(
    rate, excess, benefit_type
):
    case = record(
        beneficiary(),
        beneficiary(
            "disabled",
            rate=rate,
            benefit_type=benefit_type,
            work=earnings(lower_earnings_for_excess(excess)),
        ),
    )
    result = _apply(case)
    assert all(
        row.deduction == 0 for row in result.for_beneficiary("disabled")
    )
    assert worker(result, "disabled").charged == 0


@settings(max_examples=100, deadline=None)
@given(DIME_RATES, st.integers(0, 100_000), st.sampled_from(SUPPORTED_YEARS))
def test_excess_is_year_local_and_cannot_change_a_clean_later_year(
    rate, excess, year
):
    current = _apply(
        record(
            beneficiary(
                rate=rate,
                work=earnings(lower_earnings_for_excess(excess, year)),
            ),
            year=year,
        )
    )
    assert worker(current).uncharged == max(F(0), excess - 12 * rate)
    clean = _apply(record(beneficiary(rate=rate), year=YEAR))
    replay = _apply(record(beneficiary(rate=rate), year=YEAR))
    assert clean == replay
    assert all(row.deduction == 0 for row in clean.months)


@pytest.mark.parametrize("year", SUPPORTED_YEARS)
@pytest.mark.parametrize("fra", [None, 6])
def test_r1_differential_matches_every_supported_year_exactly(year, fra):
    expected = PARAMS.for_year(year)
    nh = beneficiary(fra_month=fra)
    result = _apply(record(nh, year=year))
    observed = worker(result)
    if fra is None:
        amount = expected.lower_exempt_amount.value
        rate = expected.lower_withholding_rate.value
    else:
        amount = expected.higher_exempt_amount.value
        rate = expected.higher_withholding_rate.value
    assert observed.annual_exempt == amount
    assert observed.withholding_rate == rate
    assert observed.monthly_exempt == amount / 12


@settings(deadline=None)
@given(st.sampled_from(SUPPORTED_YEARS), st.booleans())
def test_r1_differential_statutory_default_is_exactly_one_twelfth(
    year, higher
):
    result = r.apply_ret_year(
        record(beneficiary(fra_month=6 if higher else None), year=year),
        PARAMS,
    )
    amount = PARAMS.for_year(year)
    expected = (
        amount.higher_exempt_amount.value
        if higher
        else amount.lower_exempt_amount.value
    )
    expected_rate = (
        amount.higher_withholding_rate.value
        if higher
        else amount.lower_withholding_rate.value
    )
    assert worker(result).annual_exempt == expected
    assert worker(result).withholding_rate == expected_rate
    assert worker(result).monthly_exempt == expected / 12


@settings(deadline=None)
@given(st.sampled_from(SUPPORTED_YEARS))
def test_r1_differential_missing_year_raises_without_substitution(year):
    remaining = {
        key: value for key, value in PARAMS.years.items() if key != year
    }
    parameters = RETParameters(remaining, PARAMS.parameter_sha256)
    with pytest.raises(KeyError, match=f"year {year}"):
        _apply(record(year=year), parameters)


@st.composite
def partial_families(draw):
    size = draw(st.integers(1, 6))
    rates = {f"b{index}": draw(DIME_RATES) for index in range(size)}
    originals = {key: draw(DIME_RATES) for key in rates}
    total_dimes = int(sum(rates.values()) * 10)
    payable = F(draw(st.integers(0, total_dimes)), 10)
    return payable, rates, originals


@settings(max_examples=200, deadline=None)
@given(partial_families())
def test_partial_payments_preserve_total_with_residual_and_caps_and_proportions(
    case,
):
    payable, rates, originals = case
    result = r.partial_payments(payable, rates, originals)
    assert sum(result.values()) + result.undistributed_subdollar_residual == (
        payable
    )
    assert 0 <= result.undistributed_subdollar_residual < 1
    assert set(result) == set(rates)
    uncapped_ratios = set()
    for key, amount in result.items():
        assert 0 <= amount <= rates[key]
        if amount < rates[key]:
            uncapped_ratios.add(amount / originals[key])
    assert len(uncapped_ratios) <= 1
    if uncapped_ratios:
        common_ratio = uncapped_ratios.pop()
        for key in result:
            if result[key] == rates[key]:
                assert rates[key] / originals[key] <= common_ratio


@settings(max_examples=150, deadline=None)
@given(partial_families(), st.randoms(use_true_random=False))
def test_partial_reapportionment_is_deterministic_and_order_independent(
    case, rng
):
    payable, rates, originals = case
    keys = list(rates)
    rng.shuffle(keys)
    first = r.partial_payments(payable, rates, originals)
    shuffled = r.partial_payments(
        payable,
        {key: rates[key] for key in keys},
        {key: originals[key] for key in keys},
    )
    assert shuffled == first
    assert shuffled.undistributed_subdollar_residual == (
        first.undistributed_subdollar_residual
    )
    repeated = r.partial_payments(payable, rates, originals)
    assert repeated == first
    assert repeated.undistributed_subdollar_residual == (
        first.undistributed_subdollar_residual
    )


@settings(max_examples=150, deadline=None)
@given(
    st.integers(1, 100),
    st.integers(1, 99),
    st.integers(1, 99),
)
def test_subdollar_stop_keeps_exact_last_uncapped_shares_and_capped_rate(
    pool_dollars, overflow_cents, quarter_weight
):
    # Any positive overflow below $1 must stop immediately, even if another
    # redistribution would cross a whole-dollar payment boundary.
    payable = F(pool_dollars + 4)
    weights = {
        "nh": F(100 - quarter_weight),
        "capped": F(100),
        "child": F(quarter_weight),
    }
    first = {
        key: payable * weight / sum(weights.values())
        for key, weight in weights.items()
    }
    overflow = F(overflow_cents, 100)
    rates = {
        "nh": payable,
        "capped": first["capped"] - overflow,
        "child": payable,
    }
    result = r.partial_payments(payable, rates, weights)
    assert dict(result) == {
        "nh": first["nh"],
        "capped": rates["capped"],
        "child": first["child"],
    }
    assert result.undistributed_subdollar_residual == overflow
    assert sum(result.values()) + overflow == payable


@settings(max_examples=100, deadline=None)
@given(st.integers(1, 100), st.integers(1, 99))
@example(scale=1, overflow_cents=66)
@example(scale=1, overflow_cents=67)
@example(scale=1, overflow_cents=68)
def test_stop_threshold_and_later_iteration_keep_original_participant_count(
    scale, overflow_cents
):
    """RS 02501.110B.2 permits one or more caps in the first apportionment."""
    pool = F(8 * scale)
    weights = {"nh": 2, "spouse": 1, "child": 1}
    # The first overflow is at least $1, so it must be reapportioned.
    threshold = r.partial_payments(
        pool, {"nh": pool, "spouse": scale, "child": pool}, weights
    )
    assert threshold == {
        "nh": F(14 * scale, 3),
        "spouse": F(scale),
        "child": F(7 * scale, 3),
    }
    assert threshold.undistributed_subdollar_residual == 0
    # A child cap at least pool/4 binds only after the spouse releases
    # $2*scale. Below that initial share, both cap in the first iteration
    # and their combined overflow is reapportioned to the NH.
    overflow = F(overflow_cents, 100)
    child_cap = pool / 3 - overflow
    stopped = r.partial_payments(
        pool, {"nh": pool, "spouse": 0, "child": child_cap}, weights
    )
    if child_cap >= pool / 4:
        expected_nh = 2 * pool / 3
        expected_residual = overflow
    else:
        expected_nh = pool - child_cap
        expected_residual = F(0)
    assert stopped == {"nh": expected_nh, "spouse": F(0), "child": child_cap}
    assert stopped.undistributed_subdollar_residual == expected_residual
    assert sum(stopped.values()) + expected_residual == pool


def test_simultaneous_initial_caps_reapportion_combined_overflow():
    """Invented RS 02501.110B.2 regression from the minimized review case."""
    assert (
        "the first apportionment yields an amount for one or more of them"
        in source_text("poms_rs_02501_110")
    )
    pool = F(8)
    caps = {"nh": pool, "spouse": F(0), "child": F(599, 300)}
    weights = {"nh": F(2), "spouse": F(1), "child": F(1)}
    initial = {key: pool * weight / 4 for key, weight in weights.items()}
    assert initial == {"nh": F(4), "spouse": F(2), "child": F(2)}
    assert initial["spouse"] - caps["spouse"] == 2
    assert initial["child"] - caps["child"] == F(1, 300)
    combined_overflow = sum(
        (initial[key] - caps[key] for key in ("spouse", "child")), F(0)
    )
    assert combined_overflow == F(601, 300) >= 1

    result = r.partial_payments(pool, caps, weights)
    assert dict(result) == {
        "nh": F(1801, 300),
        "spouse": F(0),
        "child": F(599, 300),
    }
    assert result.undistributed_subdollar_residual == 0
    assert sum(result.values()) + result.undistributed_subdollar_residual == (
        pool
    )
    assert all(0 <= result[key] <= caps[key] for key in caps)
    assert {
        key: amount.numerator // amount.denominator
        for key, amount in result.items()
    } == {
        "nh": 6,
        "spouse": 0,
        "child": 1,
    }


@settings(max_examples=150, deadline=None)
@given(
    st.integers(10, 30_000),
    st.integers(10, 30_000),
    st.integers(1, 20),
)
def test_zero_cap_participants_preserve_total_and_trigger_source_stop(
    nh_dimes,
    child_dimes,
    denominator,
):
    rates = {"nh": F(nh_dimes, 10), "child": F(child_dimes, 10), "zero": F(0)}
    originals = {"nh": F(2), "child": F(1), "zero": F(1)}
    payable = F(1, denominator)
    result = r.partial_payments(payable, rates, originals)
    assert dict(result) == {
        "nh": payable / 2,
        "child": payable / 4,
        "zero": F(0),
    }
    assert result.undistributed_subdollar_residual == payable / 4
    assert sum(result.values()) + result.undistributed_subdollar_residual == (
        payable
    )
    assert set(result) == set(rates)


@settings(max_examples=100, deadline=None)
@given(st.lists(st.tuples(st.booleans(), st.integers(1, 10_000)), max_size=15))
def test_coverage_denominators_keep_every_supported_or_refused_row(cases):
    outcomes = []
    for index, (refused, weight) in enumerate(cases):
        outcomes.append(
            r.evaluate_ret(
                f"r{index}",
                weight,
                lambda flag=refused: _apply(record(fiscal_year=flag)),
            )
        )
    totals = r.count_ret_outcomes(outcomes)
    assert totals.rows == len(cases)
    assert totals.unsupported_rows == sum(refused for refused, _ in cases)
    assert totals.supported_rows + totals.unsupported_rows == len(cases)
    assert totals.weight == sum(weight for _, weight in cases)
    assert totals.unsupported_weight == sum(
        weight for refused, weight in cases if refused
    )
    if any(refused for refused, _ in cases):
        with pytest.raises(r.FamilyTargetBlocked):
            r.weighted_ret_total(outcomes)
    # Malformed earnings propagate even when the same record also asks
    # for an unsupported fiscal year; they cannot become an outcome row.
    invalid_wage = -max(1, sum(weight for _, weight in cases))
    with pytest.raises(r.InvalidFamilyInput):
        r.evaluate_ret(
            "invalid",
            1,
            lambda: _apply(
                record(
                    beneficiary(work=earnings(invalid_wage)),
                    fiscal_year=True,
                )
            ),
        )


MONTH_SET_FIELDS = (
    "self_employment_months",
    "substantial_service_months",
    "entitled_months",
    "divorced_months",
    "deemed_child_age_18_months",
    "own_work_exempt_months",
    "family_maximum_binding_months",
    "other_deduction_months",
)
INVALID_MONTH_COLLISIONS = st.one_of(
    st.just((1, True)),
    st.integers(1, 12).map(lambda month: (month, float(month))),
)


def _month_set_case(field, values, month):
    """Otherwise-valid inputs exposing every public ledger month set."""
    if field == "self_employment_months":
        return r.WorkEarnings(nese=1, self_employment_months=values)
    if field == "substantial_service_months":
        return r.WorkEarnings(
            nese=1,
            self_employment_months=MONTHS,
            substantial_service_months=values,
        )
    if field in (
        "family_maximum_binding_months",
        "other_deduction_months",
    ):
        return record(**{field: values})
    benefit_type = (
        BenefitType.DIVORCED_SPOUSE
        if field == "divorced_months"
        else BenefitType.CHILD
    )
    return dataclasses.replace(
        beneficiary(benefit_type=benefit_type, entitled={month}),
        **{field: values},
    )


@pytest.mark.parametrize("field", MONTH_SET_FIELDS)
@settings(max_examples=30, deadline=None)
@given(INVALID_MONTH_COLLISIONS)
@example((1, True))
@example((1, 1.0))
def test_every_raw_month_set_element_is_validated_before_deduplication(
    field, collision
):
    month = collision[0]
    for values in (collision, collision[::-1]):
        with pytest.raises(r.InvalidFamilyInput):
            _month_set_case(field, values, month)


# Any non-empty own_work_exempt_months is an input error (202(s)(3)).
VALID_MONTH_SET_FIELDS = tuple(
    field for field in MONTH_SET_FIELDS if field != "own_work_exempt_months"
)


@pytest.mark.parametrize("field", VALID_MONTH_SET_FIELDS)
@settings(max_examples=30, deadline=None)
@given(st.lists(st.integers(1, 12), min_size=1, max_size=30))
def test_valid_month_set_duplicates_and_order_preserve_the_same_months(
    field, months
):
    case = _month_set_case(field, tuple(months), months[0])
    reverse = _month_set_case(field, tuple(reversed(months)), months[0])
    assert getattr(case, field) == getattr(reverse, field) == frozenset(months)


@settings(max_examples=150, deadline=None)
@given(DIME_RATES, EXCESSES, EXCESSES, PROTECTED)
def test_auxiliary_own_deductions_are_monotone_with_protected_months_fixed(
    rate,
    a,
    b,
    protected,
):
    low, high = sorted((a, b))
    results = []
    for excess in (low, high):
        grace, work = grace_work(
            lower_earnings_for_excess(excess),
            protected,
            benefit_type=BenefitType.SPOUSE,
        )
        results.append(
            _apply(
                record(
                    beneficiary(),
                    beneficiary(
                        "spouse",
                        rate=rate,
                        benefit_type=BenefitType.SPOUSE,
                        grace=grace,
                        work=work,
                    ),
                )
            )
        )
    assert _annual_deduction(results[0], "spouse") <= _annual_deduction(
        results[1], "spouse"
    )
    for result, excess in zip(results, (low, high), strict=True):
        own = worker(result, "spouse")
        assert own.charged == min(F(excess), rate * (12 - len(protected)))
        assert own.charged + own.uncharged == own.excess == excess
        assert 0 <= own.charged <= own.excess
        assert all(
            row.deduction == 0
            for row in result.for_beneficiary("spouse")
            if row.month in protected
        )


@settings(max_examples=150, deadline=None)
@given(DIME_RATES, EXCESSES, PROTECTED, PROTECTED)
def test_auxiliary_own_excess_uses_earliest_entitled_unprotected_months(
    rate,
    excess,
    entitled,
    protected,
):
    grace, work = grace_work(
        lower_earnings_for_excess(excess),
        protected,
        benefit_type=BenefitType.SPOUSE,
        entitled=entitled,
    )
    result = _apply(
        record(
            beneficiary(),
            beneficiary(
                "spouse",
                rate=rate,
                benefit_type=BenefitType.SPOUSE,
                entitled=entitled,
                grace=grace,
                work=work,
            ),
        )
    )
    chargeable_months = sorted(entitled - protected)
    assert worker(result, "spouse").charged == min(
        F(excess), rate * len(chargeable_months)
    )
    unexhausted_seen = False
    for row in result.for_beneficiary("spouse"):
        assert row.gross == row.net_due + row.deduction
        assert row.payment == int(row.net_due)
        if row.month not in chargeable_months:
            assert row.deduction == 0
            continue
        if unexhausted_seen:
            assert row.deduction == 0
        if row.deduction < row.gross:
            unexhausted_seen = True


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 10000), st.integers(0, 10000), st.booleans())
def test_ret_seals_pickle_and_common_denominator_preserve_rows(
    weight, rate, refused
):
    outcome = r.evaluate_ret(
        "record",
        weight,
        lambda: _apply(record(beneficiary(rate=rate), fiscal_year=refused)),
    )
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(r.InvalidFamilyInput):
            pickle.dumps(outcome, protocol=protocol)
    restored = outcome
    expected = r.count_ret_outcomes([outcome])
    assert r.count_ret_outcomes([restored]) == expected
    assert g.count_family_outcomes([restored]) == expected
    assert expected.rows == 1
    assert expected.weight == weight
    assert expected.unsupported_rows == int(refused)
    assert expected.unsupported_weight == weight * refused
    with pytest.raises(r.InvalidFamilyInput):
        dataclasses.replace(restored)
    object.__setattr__(restored, "weight", F(weight + 1))
    with pytest.raises(r.InvalidFamilyInput):
        r.count_ret_outcomes([restored])


@settings(max_examples=40, deadline=None)
@given(DIME_RATES, st.integers(1, 12), st.integers(1, 100))
def test_ret_evaluator_rejects_every_altered_month(rate, month, increment):
    result = _apply(record(beneficiary(rate=rate)))
    row = result.months[month - 1]
    object.__setattr__(row, "payment", row.payment + increment)
    with pytest.raises(r.InvalidFamilyInput):
        r.evaluate_ret("altered", 1, lambda: result)


@settings(max_examples=40, deadline=None)
@given(DIME_RATES, st.integers(1, 100))
def test_ret_private_capability_preserves_month_and_worker_accounting(
    rate, delta
):
    result = _apply(record(beneficiary(rate=rate)))
    for target, field in (
        (result.months[0], "net_due"),
        (result.months[0], "payment"),
        (result.months[0], "provisional_payment"),
        (result.workers[0], "charged"),
        (result.workers[0], "excess"),
    ):
        # Private capability exercises seal-time validation; persistence is forbidden.
        cls, fields = type(target), _result_values(target)
        fields[field] += delta
        with pytest.raises(r.InvalidFamilyInput):
            _computed(cls, **fields)


@settings(max_examples=30, deadline=None)
@given(DIME_RATES, st.booleans(), st.integers(1, 100))
def test_partial_payments_reject_altered_allocation_money_inputs(
    rate, use_as_original, delta
):
    allocation = r.partial_payments(rate, {"nh": rate * 2}, {"nh": rate * 2})
    object.__setattr__(allocation, "shares", {"nh": rate + delta})
    with pytest.raises(r.InvalidFamilyInput):
        r.partial_payments(
            rate,
            {"nh": rate * 2} if use_as_original else allocation,
            allocation if use_as_original else {"nh": rate * 2},
        )
