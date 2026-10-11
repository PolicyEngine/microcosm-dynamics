"""R2 Hypothesis invariants over invented record-years only.

Verification class: statutory conformance. Conservation refers to exact net
entitlements; 215(g)'s subsequent whole-dollar check floor is asserted
separately. Fractional capped allocations explicitly use the complete
reapportionment interpretation, while examples pin the default refusal of
the POMS sub-$1 ambiguity. These tests admit no population or forecast claim.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import ret_ledger as r
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

DIME_RATES = st.integers(1, 30_000).map(lambda value: F(value, 10))
EXCESSES = st.integers(0, 50_000)
PROTECTED = st.frozensets(st.integers(1, 12), max_size=12)
SUPPORTED_YEARS = tuple(year for year in PARAMS.years if year >= 2000)


def _apply(record_year, parameters=PARAMS):
    return r.apply_ret_year(
        record_year,
        parameters,
        subdollar_policy=r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT,
    )


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
    )
    assert worker(result).charged + worker(result).uncharged == excess
    assert 0 <= worker(result).charged <= excess


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
    assert observed.monthly_exempt == -(-amount // 12)


@settings(deadline=None)
@given(st.sampled_from(SUPPORTED_YEARS), st.booleans())
def test_r1_differential_exact_monthly_policy_is_exactly_one_twelfth(
    year, higher
):
    result = r.apply_ret_year(
        record(beneficiary(fra_month=6 if higher else None), year=year),
        PARAMS,
        monthly_limit_policy=r.MonthlyLimitPolicy.EXACT_TWELFTH,
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
def test_partial_payments_preserve_total_and_caps_and_uncapped_proportions(
    case,
):
    payable, rates, originals = case
    result = r.partial_payments(
        payable,
        rates,
        originals,
        subdollar_policy=r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT,
    )
    assert sum(result.values()) == payable
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
    kwargs = {"subdollar_policy": r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT}
    first = r.partial_payments(payable, rates, originals, **kwargs)
    shuffled = r.partial_payments(
        payable,
        {key: rates[key] for key in keys},
        {key: originals[key] for key in keys},
        **kwargs,
    )
    assert shuffled == first
    assert r.partial_payments(payable, rates, originals, **kwargs) == first


@settings(max_examples=150, deadline=None)
@given(partial_families())
def test_default_partial_apportionment_equals_complete_or_explicitly_refuses(
    case,
):
    payable, rates, originals = case
    complete = r.partial_payments(
        payable,
        rates,
        originals,
        subdollar_policy=r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT,
    )
    try:
        conservative = r.partial_payments(payable, rates, originals)
    except r.RETConfigurationUnsupported as error:
        assert error.reason is r.UnsupportedReason.SUBDOLLAR_REAPPORTIONMENT
        assert len(rates) >= 3
    else:
        assert conservative == complete


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
    complete = r.partial_payments(
        payable,
        rates,
        originals,
        subdollar_policy=r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT,
    )
    assert complete == {
        "nh": payable * F(2, 3),
        "child": payable / 3,
        "zero": F(0),
    }
    assert sum(complete.values()) == payable
    assert set(complete) == set(rates)
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.partial_payments(payable, rates, originals)
    assert error.value.reason is r.UnsupportedReason.SUBDOLLAR_REAPPORTIONMENT


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
